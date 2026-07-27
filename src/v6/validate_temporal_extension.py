from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np


KEY_FIELDS = (
    "active",
    "note_id",
    "visible_window",
    "prediction_age_ms",
    "release_phase",
    "pitch_midi",
)


def _manifest(path: Path) -> dict[str, dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        return {row["source_id"]: row for row in csv.DictReader(handle)}


def _npz_path(row: dict[str, str]) -> Path:
    path = Path(row["npz_path"])
    return path if path.is_absolute() else (Path.cwd() / path).resolve()


def _scalar(value: np.ndarray):
    item = np.asarray(value).item()
    return round(float(item), 5) if isinstance(item, float) else int(item)


def _key(data, index: int) -> tuple[object, ...]:
    return tuple(_scalar(data[field][index]) for field in KEY_FIELDS)


def validate_temporal_extension(
    baseline_manifest: Path,
    candidate_manifest: Path,
) -> dict[str, object]:
    baseline = _manifest(baseline_manifest)
    candidate = _manifest(candidate_manifest)
    unknown_sources = sorted(set(candidate) - set(baseline))
    if unknown_sources:
        raise ValueError(f"Sources V6.1 absentes de V6.0: {unknown_sources}")
    baseline = {source_id: baseline[source_id] for source_id in candidate}

    matched = 0
    added_active = 0
    added_release = 0
    added_other = 0
    mismatches: list[dict[str, object]] = []
    by_source: dict[str, dict[str, int]] = {}

    for source_id in sorted(baseline):
        with np.load(_npz_path(baseline[source_id])) as old, np.load(
            _npz_path(candidate[source_id])
        ) as new:
            common_fields = sorted(set(old.files) & set(new.files))
            buckets: dict[tuple[object, ...], list[int]] = defaultdict(list)
            for index in range(len(new["active"])):
                buckets[_key(new, index)].append(index)
            bucket_positions: dict[tuple[object, ...], int] = defaultdict(int)
            matched_indices: list[int] = []
            source_matched = 0
            for old_index in range(len(old["active"])):
                key = _key(old, old_index)
                position = bucket_positions[key]
                candidates = buckets.get(key, [])
                if position >= len(candidates):
                    mismatches.append({
                        "source_id": source_id,
                        "baseline_index": old_index,
                        "key": list(key),
                    })
                    continue
                matched_indices.append(candidates[position])
                bucket_positions[key] += 1
                matched += 1
                source_matched += 1

            if source_matched == len(old["active"]):
                selected = np.asarray(matched_indices, dtype=np.int32)
                for field in common_fields:
                    if not np.array_equal(old[field], new[field][selected]):
                        mismatches.append({
                            "source_id": source_id,
                            "field": field,
                            "baseline_shape": list(old[field].shape),
                            "candidate_shape": list(new[field][selected].shape),
                        })
            used = set(matched_indices)

            source_added_active = 0
            source_added_release = 0
            source_added_other = 0
            for index in range(len(new["active"])):
                if index in used:
                    continue
                if float(new["active"][index]) > 0.5:
                    added_active += 1
                    source_added_active += 1
                elif float(new["release_phase"][index]) > 0.5:
                    added_release += 1
                    source_added_release += 1
                else:
                    added_other += 1
                    source_added_other += 1
            by_source[source_id] = {
                "baseline": int(len(old["active"])),
                "candidate": int(len(new["active"])),
                "matched_bit_exact": source_matched,
                "added_active": source_added_active,
                "added_release": source_added_release,
                "added_other": source_added_other,
            }

    report: dict[str, object] = {
        "baseline_manifest": str(baseline_manifest),
        "candidate_manifest": str(candidate_manifest),
        "sources": len(baseline),
        "baseline_rows_matched_bit_exact": matched,
        "added_active": added_active,
        "added_release": added_release,
        "added_other": added_other,
        "mismatches": mismatches,
        "by_source": by_source,
    }
    if mismatches or added_other:
        raise ValueError(json.dumps(report, indent=2))
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline-manifest", type=Path, required=True)
    parser.add_argument("--candidate-manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = validate_temporal_extension(
        args.baseline_manifest, args.candidate_manifest
    )
    payload = json.dumps(report, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload, encoding="utf-8")
    print(payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
