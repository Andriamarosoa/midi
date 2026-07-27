"""Validate harmonic heads on the V5.3 multi-source harmonic labels."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.product.tflite_runtime import ProductBundle, TFLitePitchModel
from src.product.validate_external_windows import group_name, select_examples


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument(
        "--manifest", type=Path,
        default=Path("data/processed/v5_3_harmonics/manifest.csv"),
    )
    parser.add_argument("--examples", type=int, default=300)
    args = parser.parse_args()
    bundle = ProductBundle(args.artifact_dir)
    model = TFLitePitchModel(bundle, threads=1)
    with args.manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups = defaultdict(list)
    for row in rows:
        name = group_name(row)
        if name:
            groups[name].append(row)
    results = {}
    for number, name in enumerate(sorted(groups)):
        selected, population = select_examples(
            groups[name], args.examples, 7300 + number
        )
        amplitude_errors = []
        offset_errors = []
        labeled_bins = 0
        examples = 0
        for path, indices in selected.items():
            # Swap the same relative manifest path to the V5.3 label build.
            harmonic_path = Path(str(path).replace(
                "data\\processed\\v5_2", "data\\processed\\v5_3_harmonics"
            ).replace(
                "data/processed/v5_2", "data/processed/v5_3_harmonics"
            ))
            with np.load(harmonic_path, allow_pickle=False) as arrays:
                for index in indices:
                    prediction = model.infer(
                        arrays["audio"][index],
                        int(arrays["visible_window"][index]),
                    )
                    present = np.asarray(arrays["harmonic_present"][index]) >= 0.5
                    target_amplitude = np.asarray(
                        arrays["harmonic_amplitude"][index], dtype=np.float32
                    )
                    target_offset = np.asarray(
                        arrays["harmonic_offset_cents"][index], dtype=np.float32
                    )
                    amplitude_errors.extend(np.abs(
                        prediction.harmonic_amplitude[present]
                        - target_amplitude[present]
                    ).tolist())
                    offset_errors.extend(np.abs(
                        prediction.harmonic_offset_cents[present]
                        - target_offset[present]
                    ).tolist())
                    labeled_bins += int(np.sum(present))
                    examples += 1
        results[name] = {
            "population_examples": population,
            "sampled_examples": examples,
            "harmonic_labeled_bins": labeled_bins,
            "harmonic_amplitude_mae": float(np.mean(amplitude_errors)),
            "harmonic_offset_cents_mae": float(np.mean(offset_errors)),
        }
        print(name, results[name], flush=True)
    report = {
        "label_build": "V5.3 multi-source harmonic extraction",
        "selection": "deterministic random windows, seed 7300 + sorted group index",
        "groups": results,
    }
    output = args.artifact_dir / "external_harmonics_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    metadata_path = args.artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["validation"]["external_harmonics_report"] = output.name
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
