from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path

import numpy as np


def _manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return {row["source_id"]: row for row in rows}


def _resolved_npz(row: dict[str, str]) -> Path:
    path = Path(row["npz_path"])
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def validate_dataset(
    baseline_manifest: Path,
    candidate_manifest: Path,
) -> dict[str, object]:
    baseline = _manifest(baseline_manifest)
    candidate = _manifest(candidate_manifest)
    candidate_datasets = {row.get("dataset_id", "") for row in candidate.values()}
    comparable_baseline = {
        source_id: row
        for source_id, row in baseline.items()
        if row.get("dataset_id", "") in candidate_datasets
    }
    if set(comparable_baseline) != set(candidate):
        raise ValueError(
            "Sources differentes entre les datasets comparables V5.3 et V6: "
            f"missing={sorted(set(comparable_baseline) - set(candidate))}, "
            f"extra={sorted(set(candidate) - set(comparable_baseline))}"
        )

    split_counts: dict[str, Counter[str]] = {}
    active_samples = 0
    inactive_samples = 0
    release_samples = 0
    silence_samples = 0
    compared_values = 0
    mismatches: list[dict[str, object]] = []
    invalid_files: list[str] = []

    for source_id in sorted(comparable_baseline):
        base_row = comparable_baseline[source_id]
        candidate_row = candidate[source_id]
        with np.load(_resolved_npz(base_row)) as base, np.load(
            _resolved_npz(candidate_row)
        ) as current:
            active = np.asarray(current["active"], dtype=np.float32) > 0.5
            if int(np.sum(active)) != len(base["active"]):
                mismatches.append({
                    "source_id": source_id,
                    "field": "active_count",
                    "baseline": int(len(base["active"])),
                    "candidate": int(np.sum(active)),
                })
                continue

            common_fields = sorted(set(base.files) & set(current.files))
            for field in common_fields:
                base_values = np.asarray(base[field])
                candidate_values = np.asarray(current[field])[active]
                compared_values += int(base_values.size)
                if not np.array_equal(base_values, candidate_values):
                    mismatches.append({
                        "source_id": source_id,
                        "field": field,
                        "baseline_shape": list(base_values.shape),
                        "candidate_shape": list(candidate_values.shape),
                    })

            onset = np.asarray(current["onset"], dtype=np.float32) > 0.5
            release = np.asarray(current["release_phase"], dtype=np.float32) > 0.5
            pitch = np.asarray(current["pitch_midi"], dtype=np.int32)
            audio = np.asarray(current["audio"], dtype=np.float32)
            if (
                np.any(onset & ~active)
                or np.any(release & active)
                or not np.isfinite(audio).all()
                or np.any(active & ((pitch < 40) | (pitch > 76)))
            ):
                invalid_files.append(source_id)

            positive = int(np.sum(active))
            negative = int(len(active) - positive)
            releases = int(np.sum(release))
            silences = int(np.sum(~active & ~release))
            active_samples += positive
            inactive_samples += negative
            release_samples += releases
            silence_samples += silences
            split = candidate_row.get("split", "")
            counter = split_counts.setdefault(split, Counter())
            counter.update({
                "files": 1,
                "active": positive,
                "inactive": negative,
                "release": releases,
                "silence": silences,
            })

    report: dict[str, object] = {
        "baseline_manifest": str(baseline_manifest),
        "candidate_manifest": str(candidate_manifest),
        "dataset_ids": sorted(candidate_datasets),
        "ignored_non_comparable_baseline_files": len(baseline) - len(comparable_baseline),
        "files": len(candidate),
        "active_samples": active_samples,
        "inactive_samples": inactive_samples,
        "release_samples": release_samples,
        "silence_samples": silence_samples,
        "compared_active_values": compared_values,
        "active_examples_bit_exact": len(mismatches) == 0,
        "mismatches": mismatches,
        "schema_or_label_invalid_files": invalid_files,
        "by_split": {
            split: dict(counter) for split, counter in sorted(split_counts.items())
        },
    }
    if mismatches or invalid_files:
        raise ValueError(json.dumps(report, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-manifest", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_dataset(args.baseline_manifest, args.candidate_manifest)
    payload = json.dumps(report, indent=2)
    if args.output is not None:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
