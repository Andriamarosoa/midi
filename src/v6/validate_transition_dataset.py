"""Validate the complete V6.3.2 transition-candidate dataset."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np

from src.v6.transition_gate import FEATURE_NAMES


def validate(manifest: Path) -> dict[str, object]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != 180:
        raise ValueError(f"180 solos attendus, trouves: {len(rows)}")
    if len({row["source_id"] for row in rows}) != len(rows):
        raise ValueError("source_id V6.3.2 duplique.")
    expected = {
        "train": {"00", "01", "02", "03"},
        "validation": {"04"},
        "test": {"05"},
    }
    observed = {
        split: {row["player_id"] for row in rows if row["split"] == split}
        for split in expected
    }
    if observed != expected:
        raise ValueError(f"Splits V6.3.2 incoherents: {observed}")
    counts = {split: Counter() for split in expected}
    utility_contract: bool | None = None
    for row in rows:
        if not row["source_id"].endswith("_solo"):
            raise ValueError(f"Source non solo: {row['source_id']}")
        with np.load(Path(row["npz_path"])) as data:
            required = {
                "features", "label", "sample_weight", "frame_index",
                "frame_end_sample", "current_pitch", "candidate_pitch",
                "annotation_support_ratio", "target_note_id",
                "recent_onset_note_id", "harmonic_suspect",
                "csv_harmonic_strength",
            }
            missing = required - set(data.files)
            if missing:
                raise ValueError(
                    f"{row['source_id']}: arrays absents {sorted(missing)}"
                )
            utility_required = {
                "v6_3_2_label", "candidate_utility", "current_utility",
                "utility_margin", "candidate_support_by_horizon",
                "current_support_by_horizon",
            }
            current_utility_contract = utility_required <= set(data.files)
            if utility_contract is None:
                utility_contract = current_utility_contract
            elif utility_contract != current_utility_contract:
                raise ValueError("Contrat utility present seulement sur certaines sources.")
            count = len(data["label"])
            if data["features"].shape != (count, len(FEATURE_NAMES)):
                raise ValueError(f"{row['source_id']}: shape features invalide")
            if any(len(data[name]) != count for name in required - {"features"}):
                raise ValueError(f"{row['source_id']}: longueurs incoherentes")
            if not np.isfinite(data["features"]).all():
                raise ValueError(f"{row['source_id']}: features non finies")
            if set(np.unique(data["label"]).tolist()) - {0.0, 1.0}:
                raise ValueError(f"{row['source_id']}: labels non binaires")
            if np.any(data["sample_weight"] <= 0.0):
                raise ValueError(f"{row['source_id']}: poids non positif")
            if current_utility_contract:
                if data["candidate_support_by_horizon"].shape != (count, 3):
                    raise ValueError(f"{row['source_id']}: horizons candidat invalides")
                if data["current_support_by_horizon"].shape != (count, 3):
                    raise ValueError(f"{row['source_id']}: horizons courant invalides")
                margin = data["candidate_utility"] - data["current_utility"]
                if not np.allclose(margin, data["utility_margin"], atol=1e-6):
                    raise ValueError(f"{row['source_id']}: utility margin incoherente")
                expected_label = (
                    (margin > 0.05)
                    | (
                        (np.abs(margin) <= 0.05)
                        & (data["recent_onset_note_id"] >= 0)
                        & (data["candidate_support_by_horizon"][:, 0] >= 0.5)
                    )
                )
                if not np.array_equal(expected_label, data["label"] > 0.5):
                    raise ValueError(f"{row['source_id']}: labels utility incoherents")
            if np.any(data["frame_end_sample"] % 256 != 0):
                raise ValueError(f"{row['source_id']}: frame hors grille hop")
            if np.any(
                (data["current_pitch"] < 40) | (data["current_pitch"] > 76)
                | (data["candidate_pitch"] < 40) | (data["candidate_pitch"] > 76)
            ):
                raise ValueError(f"{row['source_id']}: pitch hors plage")
            split = row["split"]
            label = np.asarray(data["label"] > 0.5)
            counts[split].update({
                "recordings": 1,
                "candidates": count,
                "allowed": int(np.sum(label)),
                "rejected": int(np.sum(~label)),
                "harmonic_negatives": int(np.sum(
                    (~label) & (data["harmonic_suspect"] > 0)
                )),
                "csv_harmonic_negatives": int(np.sum(
                    (~label) & (data["csv_harmonic_strength"] > 0.0)
                )),
                "recent_onsets": int(np.sum(data["recent_onset_note_id"] >= 0)),
                "changed_from_v6_3_2": int(np.sum(
                    (data["label"] > 0.5) != (data["v6_3_2_label"] > 0.5)
                )) if current_utility_contract else 0,
            })
    for split, current in counts.items():
        if not current["allowed"] or not current["rejected"]:
            raise ValueError(f"Deux classes requises dans {split}.")
    return {
        "valid": True,
        "contract": (
            "v6.3.3_decoder_utility_from_existing_note_annotations"
            if utility_contract else
            "v6.3.2_frozen_v6.0_transition_candidates"
        ),
        "manifest": str(manifest),
        "feature_names": list(FEATURE_NAMES),
        "players": {key: sorted(value) for key, value in observed.items()},
        "splits": {key: dict(value) for key, value in counts.items()},
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/dataset/v6_3_2_transition_gate/manifest.csv"),
    )
    parser.add_argument(
        "--output", type=Path,
        default=Path("data/dataset/v6_3_2_transition_gate/validation_report.json"),
    )
    args = parser.parse_args()
    report = validate(args.manifest)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
