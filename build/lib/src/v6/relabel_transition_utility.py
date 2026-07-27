"""Relabel V6.0 transitions by decoder utility using existing annotations."""

from __future__ import annotations

import argparse
import csv
import json
import os
from collections import Counter
from pathlib import Path

import numpy as np

from src.v5.external_data import NoteEvent, discover_guitarset, parse_recording_notes


HORIZONS_S = (0.05, 0.10, 0.20)
HORIZON_WEIGHTS = np.asarray((0.5, 0.3, 0.2), dtype=np.float32)
UTILITY_EPSILON = 0.05


def pitch_support(
    notes: list[NoteEvent], pitch: int, frame_times: np.ndarray
) -> np.ndarray:
    supported = np.zeros(len(frame_times), dtype=bool)
    for note in notes:
        if int(note.pitch_midi) != int(pitch):
            continue
        supported |= (frame_times >= note.start_s) & (frame_times < note.end_s)
    return supported


def utility_targets(
    frame_end_samples: np.ndarray,
    current_pitch: np.ndarray,
    candidate_pitch: np.ndarray,
    recent_onset_note_id: np.ndarray,
    notes: list[NoteEvent],
    sample_rate: int = 44_100,
    hop_size: int = 256,
) -> dict[str, np.ndarray]:
    """Compare accepting and rejecting each transition on fixed future labels.

    Future annotation is used only to create the offline target. Returned model
    features remain unchanged and causal.
    """
    count = len(frame_end_samples)
    candidate_by_horizon = np.zeros((count, len(HORIZONS_S)), dtype=np.float32)
    current_by_horizon = np.zeros_like(candidate_by_horizon)
    for row in range(count):
        start_sample = int(frame_end_samples[row])
        for column, horizon_s in enumerate(HORIZONS_S):
            frames = max(1, int(np.ceil(horizon_s * sample_rate / hop_size)))
            times = (
                start_sample + np.arange(frames, dtype=np.int64) * hop_size
            ).astype(np.float64) / sample_rate
            candidate_by_horizon[row, column] = float(np.mean(pitch_support(
                notes, int(candidate_pitch[row]), times
            )))
            current_by_horizon[row, column] = float(np.mean(pitch_support(
                notes, int(current_pitch[row]), times
            )))
    candidate_utility = candidate_by_horizon @ HORIZON_WEIGHTS
    current_utility = current_by_horizon @ HORIZON_WEIGHTS
    margin = candidate_utility - current_utility
    recent = np.asarray(recent_onset_note_id) >= 0
    tied_real_onset = (
        np.abs(margin) <= UTILITY_EPSILON
    ) & recent & (candidate_by_horizon[:, 0] >= 0.5)
    label = ((margin > UTILITY_EPSILON) | tied_real_onset).astype(np.float32)
    return {
        "label": label,
        "candidate_utility": candidate_utility.astype(np.float32),
        "current_utility": current_utility.astype(np.float32),
        "utility_margin": margin.astype(np.float32),
        "candidate_support_by_horizon": candidate_by_horizon,
        "current_support_by_horizon": current_by_horizon,
    }


def relabel(
    source_manifest: Path,
    output_dir: Path,
    overwrite: bool = False,
) -> dict[str, object]:
    with source_manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    recordings = {
        value.source_id: value for value in discover_guitarset("data/GuitarSet")
    }
    unknown = {row["source_id"] for row in rows} - set(recordings)
    if unknown:
        raise ValueError(f"Sources GuitarSet inconnues: {sorted(unknown)}")
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    split_counts = {name: Counter() for name in ("train", "validation", "test")}
    for row in rows:
        source_id = row["source_id"]
        destination = output_dir / f"{source_id}.npz"
        report_path = output_dir / f"{source_id}.json"
        if destination.exists() and report_path.exists() and not overwrite:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        else:
            with np.load(Path(row["npz_path"])) as source:
                arrays = {name: np.asarray(source[name]) for name in source.files}
            old_label = arrays["label"].astype(np.float32, copy=True)
            notes = parse_recording_notes(recordings[source_id])
            targets = utility_targets(
                arrays["frame_end_sample"], arrays["current_pitch"],
                arrays["candidate_pitch"], arrays["recent_onset_note_id"], notes,
            )
            arrays["v6_3_2_label"] = old_label
            arrays.update(targets)
            negative = arrays["label"] <= 0.5
            recent = arrays["recent_onset_note_id"] >= 0
            harmonic_strength = np.maximum(
                arrays["harmonic_suspect"].astype(np.float32),
                arrays["csv_harmonic_strength"].astype(np.float32),
            )
            arrays["sample_weight"] = (
                1.0
                + 2.0 * np.abs(arrays["utility_margin"])
                + recent.astype(np.float32)
                + negative.astype(np.float32) * harmonic_strength
            ).astype(np.float32)
            temporary = destination.with_suffix(".tmp.npz")
            np.savez_compressed(temporary, **arrays)
            os.replace(temporary, destination)
            report = {
                "source_id": source_id,
                "split": row["split"],
                "candidates": len(old_label),
                "allowed_labels": int(np.sum(arrays["label"] > 0.5)),
                "rejected_labels": int(np.sum(arrays["label"] <= 0.5)),
                "changed_from_v6_3_2": int(np.sum(arrays["label"] != old_label)),
                "mean_candidate_utility": float(np.mean(
                    arrays["candidate_utility"]
                )) if len(old_label) else 0.0,
                "mean_current_utility": float(np.mean(
                    arrays["current_utility"]
                )) if len(old_label) else 0.0,
            }
            report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
        manifest_row = {
            **row,
            "npz_path": str(destination),
            "allowed_labels": report["allowed_labels"],
            "rejected_labels": report["rejected_labels"],
            "changed_from_v6_3_2": report["changed_from_v6_3_2"],
        }
        manifest_rows.append(manifest_row)
        split_counts[row["split"]].update({
            "recordings": 1,
            "candidates": int(report["candidates"]),
            "allowed": int(report["allowed_labels"]),
            "rejected": int(report["rejected_labels"]),
            "changed_from_v6_3_2": int(report["changed_from_v6_3_2"]),
        })
    fields = list(manifest_rows[0])
    manifest_path = output_dir / "manifest.csv"
    temporary_manifest = output_dir / "manifest.tmp"
    with temporary_manifest.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(manifest_rows)
    os.replace(temporary_manifest, manifest_path)
    report = {
        "contract": "v6.3.3_decoder_utility_from_existing_note_annotations",
        "source_manifest": str(source_manifest),
        "manifest": str(manifest_path),
        "horizons_ms": [value * 1000.0 for value in HORIZONS_S],
        "horizon_weights": HORIZON_WEIGHTS.tolist(),
        "utility_epsilon": UTILITY_EPSILON,
        "feature_contract_unchanged_and_causal": True,
        "future_annotations_used_only_for_offline_targets": True,
        "splits": {name: dict(values) for name, values in split_counts.items()},
    }
    (output_dir / "dataset_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--source-manifest", type=Path,
        default=Path("data/dataset/v6_3_2_transition_gate/manifest.csv"),
    )
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/dataset/v6_3_3_transition_utility"),
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()
    print(json.dumps(relabel(
        args.source_manifest, args.output_dir, args.overwrite
    ), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
