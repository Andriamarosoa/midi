"""Combine compatible polyphonic manifests without crossing split groups."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path


def combine(inputs: list[Path], output: Path) -> dict[str, object]:
    rows: list[dict[str, str]] = []
    fieldnames: list[str] | None = None
    for path in inputs:
        with path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            current_fields = list(reader.fieldnames or [])
            if fieldnames is None:
                fieldnames = current_fields
            elif set(current_fields) != set(fieldnames):
                raise ValueError(f"Manifest schema mismatch: {path}")
            rows.extend(dict(row) for row in reader)
    if not rows or fieldnames is None:
        raise ValueError("No manifest rows to combine.")
    source_keys = [(row["dataset_id"], row["source_id"]) for row in rows]
    if len(source_keys) != len(set(source_keys)):
        raise ValueError("Duplicate dataset/source IDs in combined manifest.")
    group_splits: dict[tuple[str, str], set[str]] = defaultdict(set)
    for row in rows:
        group_splits[(row["dataset_id"], row["group_id"])].add(row["split"])
    leakage = {
        f"{dataset}:{group}": sorted(splits)
        for (dataset, group), splits in group_splits.items()
        if len(splits) > 1
    }
    if leakage:
        raise ValueError(f"Split leakage in {len(leakage)} groups")
    rows.sort(key=lambda row: (row["dataset_id"], row["split"], row["source_id"]))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    counts: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for row in rows:
        counts[row["dataset_id"]][row["split"]] += 1
    report = {
        "inputs": [str(path) for path in inputs],
        "output": str(output),
        "rows": len(rows),
        "counts": {
            dataset: dict(sorted(splits.items()))
            for dataset, splits in sorted(counts.items())
        },
        "leaking_groups": leakage,
        "passed": True,
    }
    (output.parent / "combine_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, action="append", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(combine(args.input, args.output), indent=2))


if __name__ == "__main__":
    main()

