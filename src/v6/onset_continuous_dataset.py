"""Build the V6.3 causal onset dataset on the real 256-sample stream grid.

The previous V6.2 onset target was attached to one artificial 512-sample
window.  This module instead labels the first two causal hop-aligned frames
after every annotated ``start_s``.  ``note_id`` remains the event identity, so
two consecutive notes with the same MIDI pitch are two positive retriggers.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import zlib
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from src.dataset.build_stream_dataset import load_harmonic_csv
from src.v5.external_data import (
    NoteEvent,
    SourceRecording,
    causal_window,
    discover_guitarset,
    midi_to_hz,
    parse_recording_notes,
    read_recording_audio,
)


PHASE_NAMES = (
    "onset",
    "pre_attack",
    "decay",
    "sustain",
    "release",
    "silence",
    "harmonic_tail",
)
PHASE_TO_ID = {name: index for index, name in enumerate(PHASE_NAMES)}


@dataclass(frozen=True)
class ContinuousOnsetBuildConfig:
    sample_rate: int = 44_100
    hop_size: int = 256
    window_size: int = 512
    positive_hops: int = 2
    min_pitch: int = 40
    max_pitch: int = 76
    silence_per_recording: int = 32
    silence_guard_ms: float = 80.0
    harmonic_tail_threshold: float = 0.35
    seed: int = 42


@dataclass(frozen=True)
class FrameCandidate:
    end_sample: int
    onset: int
    phase: int
    note_id: int
    pitch_midi: int
    attack_age_ms: float
    harmonic_richness: float
    polyphony: int


def first_causal_frame_end(start_sample: int, hop_size: int) -> int:
    """First hop end containing at least one sample at/after the onset."""
    if hop_size <= 0:
        raise ValueError("hop_size doit etre positif.")
    return ((max(0, int(start_sample)) // hop_size) + 1) * hop_size


def onset_frame_ends(
    notes: list[NoteEvent],
    sample_rate: int,
    hop_size: int,
    positive_hops: int,
    audio_samples: int,
    min_pitch: int,
    max_pitch: int,
) -> dict[int, list[NoteEvent]]:
    if positive_hops < 1:
        raise ValueError("positive_hops doit etre positif.")
    result: dict[int, list[NoteEvent]] = {}
    for note in notes:
        if not min_pitch <= note.pitch_midi <= max_pitch:
            continue
        start_sample = int(round(note.start_s * sample_rate))
        first_end = first_causal_frame_end(start_sample, hop_size)
        for offset in range(positive_hops):
            end_sample = first_end + offset * hop_size
            if end_sample <= audio_samples:
                result.setdefault(end_sample, []).append(note)
    return result


def _active_notes(notes: list[NoteEvent], frame_time_s: float) -> list[NoteEvent]:
    return [
        note for note in notes
        if note.start_s <= frame_time_s < note.end_s
    ]


def load_harmonic_richness(
    recording: SourceRecording,
    notes: list[NoteEvent],
    sample_rate: int,
    max_harmonics: int = 20,
) -> dict[int, float]:
    """Load note-level overtone strength only as hard-negative metadata."""
    path = recording.harmonic_csv_path
    if path is None or not path.is_file():
        return {}
    metadata, present, amplitude, _ = load_harmonic_csv(path, max_harmonics)
    tolerance_s = 1.0 / sample_rate + 1e-6
    richness: dict[int, float] = {}
    for note in notes:
        meta = metadata.get(note.note_id)
        if meta is None:
            continue
        timing_matches = (
            abs(float(meta["start_s"]) - note.start_s) <= tolerance_s
            and abs(float(meta["end_s"]) - note.end_s) <= tolerance_s
        )
        expected = midi_to_hz(note.pitch_midi)
        measured = max(float(meta["fundamental_hz"]), 1e-8)
        cents = abs(1200.0 * math.log2(measured / expected))
        if not timing_matches or cents > 50.0:
            continue
        valid = np.asarray(present[note.note_id][1:] > 0.5)
        values = np.asarray(amplitude[note.note_id][1:], dtype=np.float32)
        if np.any(valid):
            # The strongest overtone is deliberately retained instead of a
            # label generated from the current audio frame.  It cannot leak
            # the frame target and identifies resonance-prone note tails.
            richness[note.note_id] = float(np.max(values[valid]))
    return richness


def extract_recording_frames(
    recording: SourceRecording,
    config: ContinuousOnsetBuildConfig,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    audio, source_rate = read_recording_audio(recording)
    source_rate = int(source_rate)
    if source_rate != config.sample_rate:
        divisor = math.gcd(source_rate, config.sample_rate)
        audio = resample_poly(
            audio,
            config.sample_rate // divisor,
            source_rate // divisor,
            axis=0,
        ).astype(np.float32, copy=False)
    waveform = np.mean(audio, axis=1, dtype=np.float32)
    duration_s = len(waveform) / config.sample_rate
    parsed = parse_recording_notes(recording)
    notes = [
        NoteEvent(
            note.note_id,
            note.start_s,
            min(note.end_s, duration_s),
            note.pitch_midi,
            note.expression,
        )
        for note in parsed
        if (
            0.0 <= note.start_s < duration_s
            and note.end_s > note.start_s
            and config.min_pitch <= note.pitch_midi <= config.max_pitch
        )
    ]
    richness = load_harmonic_richness(recording, notes, config.sample_rate)
    positives = onset_frame_ends(
        notes,
        config.sample_rate,
        config.hop_size,
        config.positive_hops,
        len(waveform),
        config.min_pitch,
        config.max_pitch,
    )

    candidates: dict[int, FrameCandidate] = {}
    phase_priority = {
        PHASE_TO_ID["onset"]: 100,
        PHASE_TO_ID["pre_attack"]: 60,
        PHASE_TO_ID["harmonic_tail"]: 50,
        PHASE_TO_ID["decay"]: 40,
        PHASE_TO_ID["sustain"]: 30,
        PHASE_TO_ID["release"]: 20,
        PHASE_TO_ID["silence"]: 10,
    }

    def add_candidate(
        end_sample: int,
        phase_name: str,
        note: NoteEvent | None,
    ) -> None:
        end_sample = int(end_sample)
        if end_sample <= 0 or end_sample > len(waveform):
            return
        positive_notes = positives.get(end_sample, [])
        if positive_notes:
            # When notes overlap, use the most recent attack as metadata.  The
            # binary target still means "at least one intentional onset".
            selected = max(positive_notes, key=lambda item: item.start_s)
            onset = 1
            phase = PHASE_TO_ID["onset"]
            attack_age_ms = (
                end_sample / config.sample_rate - selected.start_s
            ) * 1000.0
            note = selected
        else:
            onset = 0
            phase = PHASE_TO_ID[phase_name]
            attack_age_ms = (
                -1.0 if note is None else
                (end_sample / config.sample_rate - note.start_s) * 1000.0
            )
        frame_time_s = max(0.0, (end_sample - 1) / config.sample_rate)
        active = _active_notes(notes, frame_time_s)
        note_richness = 0.0 if note is None else richness.get(note.note_id, 0.0)
        if active:
            note_richness = max(
                note_richness,
                max(richness.get(item.note_id, 0.0) for item in active),
            )
        current = FrameCandidate(
            end_sample=end_sample,
            onset=onset,
            phase=phase,
            note_id=-1 if note is None else note.note_id,
            pitch_midi=-1 if note is None else note.pitch_midi,
            attack_age_ms=float(attack_age_ms),
            harmonic_richness=float(note_richness),
            polyphony=len(active),
        )
        previous = candidates.get(end_sample)
        if previous is None:
            candidates[end_sample] = current
            return
        if current.onset > previous.onset:
            candidates[end_sample] = current
            return
        if current.onset == previous.onset and (
            phase_priority[current.phase], current.harmonic_richness
        ) > (
            phase_priority[previous.phase], previous.harmonic_richness
        ):
            candidates[end_sample] = current

    # Add all positive targets before hard negatives so collisions can never
    # silently turn a true retrigger into a negative frame.
    for end_sample, positive_notes in positives.items():
        add_candidate(end_sample, "onset", positive_notes[0])

    for note in notes:
        start_sample = int(round(note.start_s * config.sample_rate))
        first_end = first_causal_frame_end(start_sample, config.hop_size)
        add_candidate(first_end - config.hop_size, "pre_attack", note)
        for hop_offset in (2, 4):
            add_candidate(
                first_end + hop_offset * config.hop_size,
                "decay",
                note,
            )
        for age_ms in (120.0, 220.0):
            desired = int(round((note.start_s + age_ms / 1000.0) * config.sample_rate))
            end_sample = first_causal_frame_end(desired, config.hop_size)
            if end_sample / config.sample_rate < note.end_s:
                add_candidate(end_sample, "sustain", note)
        end_sample = first_causal_frame_end(
            int(round(note.end_s * config.sample_rate)), config.hop_size
        )
        add_candidate(end_sample, "release", note)
        add_candidate(end_sample + 3 * config.hop_size, "release", note)
        if richness.get(note.note_id, 0.0) >= config.harmonic_tail_threshold:
            for age_ms in (60.0, 90.0):
                desired = int(round(
                    (note.start_s + age_ms / 1000.0) * config.sample_rate
                ))
                tail_end = first_causal_frame_end(desired, config.hop_size)
                if tail_end / config.sample_rate < note.end_s:
                    add_candidate(tail_end, "harmonic_tail", note)

    stable_seed = (
        int(config.seed) + zlib.crc32(recording.source_id.encode("utf-8"))
    ) & 0xFFFFFFFF
    rng = np.random.default_rng(stable_seed)
    guard_samples = int(round(config.silence_guard_ms / 1000.0 * config.sample_rate))
    boundaries = np.asarray(
        [
            int(round(value * config.sample_rate))
            for note in notes
            for value in (note.start_s, note.end_s)
        ],
        dtype=np.int64,
    )
    max_frame = len(waveform) // config.hop_size
    accepted = 0
    attempts = 0
    while accepted < config.silence_per_recording and attempts < 10_000:
        attempts += 1
        if max_frame < 1:
            break
        end_sample = int(rng.integers(1, max_frame + 1)) * config.hop_size
        frame_time_s = max(0.0, (end_sample - 1) / config.sample_rate)
        if _active_notes(notes, frame_time_s):
            continue
        if len(boundaries) and int(np.min(np.abs(boundaries - end_sample))) < guard_samples:
            continue
        if end_sample in candidates:
            continue
        add_candidate(end_sample, "silence", None)
        accepted += 1

    ordered = [candidates[key] for key in sorted(candidates)]
    count = len(ordered)
    arrays = {
        "audio": np.asarray(
            [causal_window(waveform, item.end_sample, config.window_size) for item in ordered],
            dtype=np.float32,
        ).reshape(count, config.window_size),
        "onset": np.asarray([item.onset for item in ordered], dtype=np.float32),
        "phase": np.asarray([item.phase for item in ordered], dtype=np.int8),
        "note_id": np.asarray([item.note_id for item in ordered], dtype=np.int32),
        "pitch_midi": np.asarray([item.pitch_midi for item in ordered], dtype=np.int16),
        "frame_end_sample": np.asarray(
            [item.end_sample for item in ordered], dtype=np.int64
        ),
        "attack_age_ms": np.asarray(
            [item.attack_age_ms for item in ordered], dtype=np.float32
        ),
        "harmonic_richness": np.asarray(
            [item.harmonic_richness for item in ordered], dtype=np.float32
        ),
        "polyphony": np.asarray([item.polyphony for item in ordered], dtype=np.int8),
    }
    phase_counts = Counter(PHASE_NAMES[item.phase] for item in ordered)
    report: dict[str, object] = {
        "source_id": recording.source_id,
        "dataset_id": recording.dataset_id,
        "player_id": recording.player_id,
        "split": recording.split,
        "source_sample_rate": source_rate,
        "sample_rate": config.sample_rate,
        "duration_s": duration_s,
        "notes_total": len(parsed),
        "notes_in_range": len(notes),
        "unique_positive_notes": len({
            item.note_id for item in ordered if item.onset > 0
        }),
        "examples": count,
        "positive_examples": int(np.sum(arrays["onset"] > 0.5)),
        "negative_examples": int(np.sum(arrays["onset"] <= 0.5)),
        "phase_counts": dict(sorted(phase_counts.items())),
        "harmonic_metadata_notes": len(richness),
        "harmonic_hard_negatives": int(np.sum(
            (arrays["onset"] <= 0.5)
            & (arrays["harmonic_richness"] >= config.harmonic_tail_threshold)
        )),
        "polyphonic_examples": int(np.sum(arrays["polyphony"] > 1)),
    }
    return arrays, report


def build_dataset(
    guitarset_root: Path,
    output_dir: Path,
    config: ContinuousOnsetBuildConfig,
    overwrite: bool = False,
) -> dict[str, object]:
    recordings = discover_guitarset(guitarset_root)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.csv"
    fields = (
        "source_id", "npz_path", "dataset_id", "player_id", "group_id",
        "capture_id", "split", "license_id", "examples",
        "positive_examples", "negative_examples", "notes_in_range",
        "harmonic_hard_negatives", "sample_rate", "hop_size", "window_size",
    )
    rows: list[dict[str, object]] = []
    reports: list[dict[str, object]] = []
    for index, recording in enumerate(recordings, start=1):
        npz_path = output_dir / f"{recording.source_id}.npz"
        report_path = output_dir / f"{recording.source_id}.json"
        if npz_path.exists() and report_path.exists() and not overwrite:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        else:
            arrays, report = extract_recording_frames(recording, config)
            temporary = output_dir / f".{recording.source_id}.tmp.npz"
            np.savez_compressed(temporary, **arrays)
            os.replace(temporary, npz_path)
            report_path.write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
        reports.append(report)
        rows.append({
            "source_id": recording.source_id,
            "npz_path": str(npz_path),
            "dataset_id": recording.dataset_id,
            "player_id": recording.player_id,
            "group_id": recording.group_id,
            "capture_id": recording.capture_id,
            "split": recording.split,
            "license_id": recording.license_id,
            "examples": report["examples"],
            "positive_examples": report["positive_examples"],
            "negative_examples": report["negative_examples"],
            "notes_in_range": report["notes_in_range"],
            "harmonic_hard_negatives": report["harmonic_hard_negatives"],
            "sample_rate": config.sample_rate,
            "hop_size": config.hop_size,
            "window_size": config.window_size,
        })
        if index % 20 == 0 or index == len(recordings):
            print(f"V6.3 dataset: {index}/{len(recordings)} enregistrements")

    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    split_counts: dict[str, dict[str, int]] = {}
    for split in ("train", "validation", "test"):
        selected = [item for item in reports if item["split"] == split]
        split_counts[split] = {
            "recordings": len(selected),
            "examples": sum(int(item["examples"]) for item in selected),
            "positive_examples": sum(int(item["positive_examples"]) for item in selected),
            "negative_examples": sum(int(item["negative_examples"]) for item in selected),
            "notes": sum(int(item["notes_in_range"]) for item in selected),
            "harmonic_hard_negatives": sum(
                int(item["harmonic_hard_negatives"]) for item in selected
            ),
        }
    summary = {
        "contract": "v6.3_continuous_causal_onset",
        "config": asdict(config),
        "phase_names": list(PHASE_NAMES),
        "recordings": len(recordings),
        "splits": split_counts,
    }
    (output_dir / "dataset_report.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--guitarset-root", type=Path, default=Path("data/GuitarSet"))
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/processed/v6_3_continuous_onset"),
    )
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    config = ContinuousOnsetBuildConfig(seed=args.seed)
    report = build_dataset(
        args.guitarset_root, args.output_dir, config, args.overwrite
    )
    print(json.dumps(report["splits"], indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
