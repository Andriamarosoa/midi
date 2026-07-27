"""Validate the complete V6.3 continuous-onset dataset contract."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from .onset_continuous_dataset import PHASE_NAMES


def validate_dataset(manifest: Path) -> dict[str, object]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError("Manifest V6.3 vide.")
    if len({row["source_id"] for row in rows}) != len(rows):
        raise ValueError("source_id duplique dans le manifest V6.3.")
    expected_players = {
        "train": {"00", "01", "02", "03"},
        "validation": {"04"},
        "test": {"05"},
    }
    observed_players = {
        split: {row["player_id"] for row in rows if row["split"] == split}
        for split in expected_players
    }
    if observed_players != expected_players:
        raise ValueError(
            f"Split joueur incoherent: {observed_players!r}"
        )

    split_counts: dict[str, Counter[str]] = {
        name: Counter() for name in expected_players
    }
    phase_counts: dict[str, Counter[str]] = {
        name: Counter() for name in expected_players
    }
    invalid: list[str] = []
    for row in rows:
        source_id = row["source_id"]
        path = Path(row["npz_path"])
        try:
            with np.load(path) as data:
                required = {
                    "audio", "onset", "phase", "note_id", "pitch_midi",
                    "frame_end_sample", "attack_age_ms", "harmonic_richness",
                    "polyphony",
                }
                missing = required - set(data.files)
                if missing:
                    raise ValueError(f"arrays absents: {sorted(missing)}")
                count = len(data["onset"])
                if data["audio"].shape != (count, 512):
                    raise ValueError(f"shape audio {data['audio'].shape}")
                if any(len(data[name]) != count for name in required - {"audio"}):
                    raise ValueError("longueurs arrays incoherentes")
                if not np.isfinite(data["audio"]).all():
                    raise ValueError("audio non fini")
                if not np.isfinite(data["harmonic_richness"]).all():
                    raise ValueError("harmonic_richness non fini")
                onset = np.asarray(data["onset"], dtype=np.float32)
                phase = np.asarray(data["phase"], dtype=np.int32)
                positive = onset > 0.5
                if set(np.unique(onset).tolist()) - {0.0, 1.0}:
                    raise ValueError("label onset non binaire")
                if np.any((phase < 0) | (phase >= len(PHASE_NAMES))):
                    raise ValueError("phase hors plage")
                if np.any(positive & (phase != 0)) or np.any((~positive) & (phase == 0)):
                    raise ValueError("phase onset incoherente")
                if np.any(positive & (data["note_id"] < 0)):
                    raise ValueError("note_id onset manquant")
                if np.any(data["frame_end_sample"] % 256 != 0):
                    raise ValueError("trame non alignee sur hop=256")
                if len(np.unique(data["frame_end_sample"])) != count:
                    raise ValueError("trame dupliquee dans un enregistrement")
                positive_age = np.asarray(data["attack_age_ms"])[positive]
                maximum_age_ms = 2 * 256 / 44_100 * 1000.0 + 0.1
                if np.any(positive_age < 0.0) or np.any(positive_age > maximum_age_ms):
                    raise ValueError("age onset hors fenetre causale")
                split = row["split"]
                split_counts[split].update({
                    "recordings": 1,
                    "examples": count,
                    "positive": int(np.sum(positive)),
                    "negative": int(np.sum(~positive)),
                    "polyphonic": int(np.sum(data["polyphony"] > 1)),
                    "harmonic_hard": int(np.sum(
                        (~positive) & (data["harmonic_richness"] >= 0.35)
                    )),
                })
                phase_counts[split].update(
                    PHASE_NAMES[int(value)] for value in phase
                )
        except Exception as error:
            invalid.append(f"{source_id}: {error}")
    if invalid:
        preview = "\n".join(invalid[:10])
        raise ValueError(f"{len(invalid)} fichiers V6.3 invalides:\n{preview}")
    for split, counts in split_counts.items():
        if not counts["positive"] or not counts["negative"]:
            raise ValueError(f"Les deux classes manquent dans {split}.")
        if set(phase_counts[split]) != set(PHASE_NAMES):
            raise ValueError(
                f"Phases incompletes dans {split}: {sorted(phase_counts[split])}"
            )
    return {
        "valid": True,
        "contract": "v6.3_continuous_causal_onset",
        "manifest": str(manifest),
        "sources": len(rows),
        "players": {
            split: sorted(players) for split, players in observed_players.items()
        },
        "splits": {
            split: dict(counts) for split, counts in split_counts.items()
        },
        "phases": {
            split: dict(counts) for split, counts in phase_counts.items()
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/processed/v6_3_continuous_onset/manifest.csv"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/processed/v6_3_continuous_onset/validation_report.json"),
    )
    args = parser.parse_args()
    report = validate_dataset(args.manifest)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
