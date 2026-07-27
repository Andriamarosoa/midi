"""Reproduce and isolate the 96 test frames touched by the old export bug."""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import numpy as np

from src.polyphonic.data import (
    PolyphonicCorpus,
    load_manifest,
    natural_validation_refs,
)


def audit(
    run_dir: Path,
    output: Path,
    examples: int = 96,
) -> dict[str, object]:
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    items = [
        item for item in load_manifest(Path(config["dataset"]["manifest"]))
        if item.split == "test"
    ]
    corpus = PolyphonicCorpus(items)
    try:
        seed = int(config["dataset"]["seed"]) + 99
        refs = natural_validation_refs(corpus, examples, seed)
        recording_counts = Counter(int(value) for value in refs[:, 0])
        touched = [
            {
                "dataset_id": corpus.items[index].dataset_id,
                "source_id": corpus.items[index].source_id,
                "group_id": corpus.items[index].group_id,
                "frames_touched": count,
            }
            for index, count in sorted(recording_counts.items())
        ]
    finally:
        corpus.close()
    report = {
        "reason": (
            "The pre-fix export parity sampler read 96 test frames. No labels, "
            "thresholds or model weights were selected from their results."
        ),
        "reproduction": "natural_validation_refs(test, 96, dataset_seed + 99)",
        "seed": seed,
        "frames": int(len(refs)),
        "references_sha256": hashlib.sha256(
            np.ascontiguousarray(refs).tobytes()
        ).hexdigest(),
        "recordings_touched": len(touched),
        "groups_to_exclude": sorted({row["group_id"] for row in touched}),
        "touched": touched,
        "policy": (
            "Exclude every touched group from all final locked-test reports."
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--examples", type=int, default=96)
    args = parser.parse_args()
    print(json.dumps(audit(args.run_dir, args.output, args.examples), indent=2))


if __name__ == "__main__":
    main()
