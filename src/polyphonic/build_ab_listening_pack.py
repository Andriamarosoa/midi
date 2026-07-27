"""Build a reproducible, neutral A/B listening pack from one WAV and two MIDIs.

The public manifest deliberately contains only the neutral labels ``A`` and
``B``.  The baseline/candidate identity is written to a separate mapping file
so the listening pack can be shared without revealing the assignment.

No perceptual score is computed: the rendered files are listening artefacts,
not an automatic quality judgement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Sequence

import soundfile as sf

from src.v5.external_data import parse_midi_notes


RENDER_SAMPLE_RATE = 44_100
RENDER_GAIN = 1.0

LISTENING_PROTOCOL = """# Protocole d'écoute aveugle A/B

## Préparation

1. Ne pas ouvrir `mapping.json` avant la fin et l'enregistrement de la fiche.
2. Utiliser le même casque, la même interface et le même lecteur pendant toute
   la session.
3. Choisir un volume d'écoute sûr, puis le garder strictement constant pour la
   source, A et B. Désactiver normalisation automatique, égaliseur et effets du
   lecteur.
4. Définir à l'avance les mêmes bornes de début et de fin pour chaque passage.

## Écoute de chaque passage

1. Écouter le passage dans `source.wav`.
2. Sans changer le volume ni les bornes, écouter le même passage dans `A.wav`,
   puis dans `B.wav`.
3. Faire une seconde passe dans l'ordre source, B, A afin de limiter le biais
   d'ordre.
4. Noter seulement après avoir entendu A et B. Ajouter les instants précis des
   défauts audibles lorsque c'est possible.

## Critères

- **Justesse des hauteurs** : correspondance entre les notes entendues dans la
  source et les hauteurs jouées.
- **Notes fantômes** : notes produites par A ou B qui ne correspondent à aucune
  attaque intentionnelle audible dans la source.
- **Omissions** : attaques ou notes intentionnelles audibles dans la source mais
  absentes du rendu.
- **Timing** : précision des départs et fins de notes, sans retard ou avance
  perceptible.
- **Fragmentation** : note tenue découpée, répétitions artificielles ou
  OFF/ON non intentionnels.
- **Préférence** : A, B, égalité ou aucune décision, après les critères
  détaillés.

Pour la justesse et le timing, 1 signifie très mauvais et 5 excellent. Pour la
sévérité des fantômes, omissions et fragmentations, 0 signifie aucun défaut et
4 un défaut très gênant. Ne jamais déduire l'identité de A ou B pendant la
notation.
"""

RATINGS_TEMPLATE: dict[str, object] = {
    "schema_version": 1,
    "kind": "blind_ab_listening_sheet",
    "listener_id": None,
    "session_id": None,
    "playback": {
        "device": None,
        "fixed_volume_confirmed": None,
        "normalization_disabled_confirmed": None,
    },
    "passages": [
        {
            "passage_id": None,
            "start_s": None,
            "end_s": None,
            "ratings": {
                label: {
                    "pitch_accuracy_1_to_5": None,
                    "ghost_notes_severity_0_to_4": None,
                    "omissions_severity_0_to_4": None,
                    "timing_accuracy_1_to_5": None,
                    "fragmentation_severity_0_to_4": None,
                    "example_timestamps_s": [],
                    "comments": None,
                }
                for label in ("A", "B")
            },
            "preference": None,
            "preference_reason": None,
        }
    ],
    "overall": {
        "preference": None,
        "confidence_1_to_5": None,
        "comments": None,
    },
    "allowed_preference_values": ["A", "B", "equal", "no_decision"],
}

Runner = Callable[..., subprocess.CompletedProcess[str]]


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_file(path: str | Path, description: str) -> Path:
    resolved = Path(path).expanduser().resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"{description} introuvable: {resolved}")
    return resolved


def _wav_info(path: Path) -> dict[str, object]:
    try:
        info = sf.info(str(path))
    except Exception as error:
        raise ValueError(f"WAV invalide ou illisible: {path}") from error
    if info.samplerate <= 0 or info.frames < 0 or info.channels <= 0:
        raise ValueError(f"Metadonnees WAV invalides: {path}")
    return {
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
        "duration_s": info.frames / float(info.samplerate),
        "sample_rate_hz": int(info.samplerate),
        "channels": int(info.channels),
        "format": str(info.format),
        "subtype": str(info.subtype),
    }


def _midi_info(path: Path) -> dict[str, object]:
    data = path.read_bytes()
    if len(data) < 14 or data[:4] != b"MThd":
        raise ValueError(f"En-tete MIDI invalide: {path}")
    try:
        notes = parse_midi_notes(path)
    except Exception as error:
        raise ValueError(f"Fichier MIDI invalide ou non pris en charge: {path}") from error
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "duration_s": max((float(note.end_s) for note in notes), default=0.0),
        "note_count": len(notes),
    }


def _copy_file(source: Path, destination: Path) -> None:
    if source != destination.resolve():
        shutil.copyfile(source, destination)


def _write_json(path: Path, payload: dict[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    temporary.replace(path)


def _write_text(path: Path, value: str) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(value.rstrip() + "\n", encoding="utf-8")
    temporary.replace(path)


def _file_info(path: Path) -> dict[str, object]:
    return {
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": _sha256(path),
    }


def _resolve_fluidsynth(executable: str | Path) -> str:
    value = str(executable)
    candidate = Path(value).expanduser()
    if candidate.parent != Path(".") or candidate.is_absolute():
        resolved = candidate.resolve()
        if not resolved.is_file():
            raise FileNotFoundError(f"Executable FluidSynth introuvable: {resolved}")
        return str(resolved)
    located = shutil.which(value)
    if located is None:
        raise FileNotFoundError(
            f"Executable FluidSynth introuvable dans PATH: {value}"
        )
    return str(Path(located).resolve())


def _render_command(
    executable: str,
    soundfont: Path,
    midi_path: Path,
    wav_path: Path,
) -> list[str]:
    # Keep every option (including -F's output argument) before SoundFont/MIDI.
    return [
        executable,
        "-n",
        "-i",
        "-q",
        "-C",
        "0",
        "-R",
        "0",
        "-r",
        str(RENDER_SAMPLE_RATE),
        "-g",
        f"{RENDER_GAIN:.1f}",
        "-O",
        "s16",
        "-T",
        "wav",
        "-o",
        "synth.cpu-cores=1",
        "-F",
        str(wav_path),
        str(soundfont),
        str(midi_path),
    ]


def _run_render(command: Sequence[str], runner: Runner) -> None:
    result = runner(
        list(command),
        check=False,
        capture_output=True,
        text=True,
    )
    returncode = int(getattr(result, "returncode", 0))
    if returncode:
        stderr = str(getattr(result, "stderr", "") or "").strip()
        detail = f": {stderr}" if stderr else ""
        raise RuntimeError(f"FluidSynth a echoue (code {returncode}){detail}")


def build_ab_listening_pack(
    source_wav: str | Path,
    baseline_midi: str | Path,
    candidate_midi: str | Path,
    output_dir: str | Path,
    *,
    soundfont: str | Path | None = None,
    fluidsynth: str | Path = "fluidsynth",
    no_render: bool = False,
    runner: Runner | None = None,
) -> dict[str, object]:
    """Create an A/B pack and return its public, identity-neutral manifest."""
    source = _require_file(source_wav, "WAV source")
    baseline = _require_file(baseline_midi, "MIDI baseline")
    candidate = _require_file(candidate_midi, "MIDI candidate")

    # Validate original inputs before creating or changing the destination.
    source_original_info = _wav_info(source)
    baseline_original_info = _midi_info(baseline)
    candidate_original_info = _midi_info(candidate)
    assignment_digest = hashlib.sha256(
        (
            "ab-listening-pack-v1:"
            f"{source_original_info['sha256']}:"
            f"{baseline_original_info['sha256']}:"
            f"{candidate_original_info['sha256']}"
        ).encode("ascii")
    ).hexdigest()
    baseline_label = "A" if int(assignment_digest[:2], 16) % 2 == 0 else "B"
    candidate_label = "B" if baseline_label == "A" else "A"
    original_by_label = {
        baseline_label: (baseline, "baseline", baseline_original_info),
        candidate_label: (candidate, "candidate", candidate_original_info),
    }

    soundfont_path: Path | None = None
    executable: str | None = None
    if soundfont is not None:
        soundfont_path = _require_file(soundfont, "SoundFont")
    if not no_render:
        if soundfont_path is None:
            raise ValueError("--soundfont est requis sauf avec --no-render.")
        executable = _resolve_fluidsynth(fluidsynth)

    destination = Path(output_dir).expanduser().resolve()
    destination.mkdir(parents=True, exist_ok=True)
    packed_source = destination / "source.wav"
    packed_midis = {
        "A": destination / "A.mid",
        "B": destination / "B.mid",
    }
    packed_wavs = {
        "A": destination / "A.wav",
        "B": destination / "B.wav",
    }

    _copy_file(source, packed_source)
    for label in ("A", "B"):
        _copy_file(original_by_label[label][0], packed_midis[label])

    source_info = {"file": packed_source.name, **_wav_info(packed_source)}
    item_midis = {
        label: {"file": path.name, **_midi_info(path)}
        for label, path in packed_midis.items()
    }

    commands: list[list[str]] = []
    item_audio: dict[str, dict[str, object] | None] = {"A": None, "B": None}
    if no_render:
        # Prevent an old render from masquerading as part of a new no-render pack.
        for path in packed_wavs.values():
            if path.is_file():
                path.unlink()
    else:
        assert soundfont_path is not None
        assert executable is not None
        invoke = runner or subprocess.run
        for label in ("A", "B"):
            # A successful return without a newly created file must never
            # allow a render from an older pack to pass as current evidence.
            if packed_wavs[label].is_file():
                packed_wavs[label].unlink()
            command = _render_command(
                executable,
                soundfont_path,
                packed_midis[label],
                packed_wavs[label],
            )
            commands.append(command)
            _run_render(command, invoke)
            if not packed_wavs[label].is_file():
                raise RuntimeError(
                    f"FluidSynth n'a pas produit le rendu attendu: "
                    f"{packed_wavs[label]}"
                )
            item_audio[label] = {
                "file": packed_wavs[label].name,
                **_wav_info(packed_wavs[label]),
            }

    mapping = {
        "schema_version": 1,
        "kind": "ab_listening_pack_private_mapping",
        "manifest": "manifest.json",
        "source": {
            "original_path": str(source),
            "packed_file": packed_source.name,
            "sha256": source_info["sha256"],
        },
        "assignments": {
            label: {
                "role": original_by_label[label][1],
                "original_path": str(original_by_label[label][0]),
                "original_filename": original_by_label[label][0].name,
                "packed_file": packed_midis[label].name,
                "sha256": original_by_label[label][2]["sha256"],
            }
            for label in ("A", "B")
        },
        "assignment": {
            "method": "deterministic_sha256_parity",
            "digest": assignment_digest,
        },
    }
    mapping_path = destination / "mapping.json"
    _write_json(mapping_path, mapping)

    protocol_path = destination / "LISTENING_PROTOCOL.md"
    ratings_path = destination / "ratings_template.json"
    _write_text(protocol_path, LISTENING_PROTOCOL)
    _write_json(ratings_path, RATINGS_TEMPLATE)

    soundfont_info: dict[str, object] | None = None
    if soundfont_path is not None:
        soundfont_info = {
            "filename": soundfont_path.name,
            "bytes": soundfont_path.stat().st_size,
            "sha256": _sha256(soundfont_path),
        }
    manifest: dict[str, object] = {
        "schema_version": 1,
        "kind": "blind_ab_listening_pack",
        "blind_labels": ["A", "B"],
        "source": source_info,
        "items": {
            label: {
                "midi": item_midis[label],
                "audio": item_audio[label],
            }
            for label in ("A", "B")
        },
        "rendering": {
            "performed": not no_render,
            "engine": "FluidSynth" if not no_render else None,
            "executable": (
                {
                    "filename": Path(executable).name,
                    "sha256": _sha256(Path(executable)),
                }
                if executable is not None
                else None
            ),
            "sample_rate_hz": RENDER_SAMPLE_RATE,
            "gain": RENDER_GAIN,
            "sample_format": "s16",
            "chorus": False,
            "reverb": False,
            "cpu_cores": 1,
            "soundfont": soundfont_info,
            "commands": commands,
        },
        "private_mapping": {
            "file": mapping_path.name,
            "sha256": _sha256(mapping_path),
        },
        "blind_listening": {
            "protocol": _file_info(protocol_path),
            "ratings_template": _file_info(ratings_path),
        },
        "notice": (
            "Ce paquet ne calcule aucun score perceptuel; A et B doivent etre "
            "ecoutes et juges independamment."
        ),
    }
    _write_json(destination / "manifest.json", manifest)
    return manifest


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source_wav", type=Path)
    parser.add_argument("baseline_midi", type=Path)
    parser.add_argument("candidate_midi", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--soundfont", type=Path)
    parser.add_argument(
        "--fluidsynth",
        default="fluidsynth",
        help="Executable FluidSynth ou nom resolu via PATH.",
    )
    parser.add_argument(
        "--no-render",
        action="store_true",
        help="Construit le paquet et le manifeste sans appeler FluidSynth.",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    try:
        manifest = build_ab_listening_pack(
            args.source_wav,
            args.baseline_midi,
            args.candidate_midi,
            args.output_dir,
            soundfont=args.soundfont,
            fluidsynth=args.fluidsynth,
            no_render=args.no_render,
        )
    except (FileNotFoundError, RuntimeError, ValueError) as error:
        parser.error(str(error))
    output = args.output_dir.expanduser().resolve() / "manifest.json"
    print(json.dumps({
        "manifest": str(output),
        "rendered": bool(manifest["rendering"]["performed"]),
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
