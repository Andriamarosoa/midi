"""Locked out-of-domain window validation for the shipped monophonic model."""

from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from src.product.tflite_runtime import ProductBundle, TFLitePitchModel


def group_name(row: dict[str, str]) -> str | None:
    dataset = row["dataset_id"]
    if dataset == "guitarset_mono_mix" and row["split"] == "test":
        return "guitarset_player05_reference"
    if dataset == "guitar_techs_mono":
        return f"guitar_techs_{row['capture_id']}"
    if dataset in {"idmt_d1_mono", "idmt_d2_mono"}:
        return dataset
    return None


def select_examples(rows, count: int, seed: int):
    sizes = np.asarray([int(row["examples"]) for row in rows], dtype=np.int64)
    cumulative = np.cumsum(sizes)
    total = int(cumulative[-1])
    rng = np.random.default_rng(seed)
    selected = np.sort(rng.choice(total, size=min(count, total), replace=False))
    grouped: dict[Path, list[int]] = defaultdict(list)
    file_indices = np.searchsorted(cumulative, selected, side="right")
    previous = np.concatenate((np.asarray([0]), cumulative[:-1]))
    for global_index, file_index in zip(selected, file_indices):
        grouped[Path(rows[int(file_index)]["npz_path"])].append(
            int(global_index - previous[int(file_index)])
        )
    return grouped, total


def evaluate(model, selected, total: int) -> dict[str, object]:
    truth_active = []
    probability_active = []
    truth_pitch = []
    prediction_pitch = []
    top3_correct = []
    harmonic_errors = []
    harmonic_count = 0
    for path, indices in selected.items():
        with np.load(path, allow_pickle=False) as arrays:
            for index in indices:
                prediction = model.infer(
                    arrays["audio"][index], int(arrays["visible_window"][index])
                )
                active = bool(arrays["active"][index] >= 0.5)
                midi = int(arrays["pitch_midi"][index])
                truth_active.append(active)
                probability_active.append(prediction.active_probability)
                if active and model.min_pitch <= midi <= model.max_pitch:
                    expected = midi - model.min_pitch
                    predicted = int(np.argmax(prediction.pitch_probability))
                    truth_pitch.append(expected)
                    prediction_pitch.append(predicted)
                    top3_correct.append(expected in np.argpartition(
                        prediction.pitch_probability, -3
                    )[-3:])
                present = np.asarray(arrays["harmonic_present"][index]) >= 0.5
                if np.any(present):
                    target = np.asarray(arrays["harmonic_amplitude"][index])
                    harmonic_errors.extend(np.abs(
                        prediction.harmonic_amplitude[present] - target[present]
                    ).tolist())
                    harmonic_count += int(np.sum(present))
    truth_active = np.asarray(truth_active, dtype=bool)
    predicted_active = np.asarray(probability_active) >= model.active_threshold
    tp = int(np.sum(truth_active & predicted_active))
    fp = int(np.sum(~truth_active & predicted_active))
    fn = int(np.sum(truth_active & ~predicted_active))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    truth_pitch = np.asarray(truth_pitch, dtype=np.int32)
    prediction_pitch = np.asarray(prediction_pitch, dtype=np.int32)
    return {
        "population_examples": total,
        "sampled_examples": int(len(truth_active)),
        "active_f1": 2 * precision * recall / max(precision + recall, 1e-12),
        "active_precision": precision,
        "active_recall": recall,
        "pitch_evaluable": int(len(truth_pitch)),
        "pitch_top1": float(np.mean(truth_pitch == prediction_pitch)) if len(truth_pitch) else None,
        "pitch_top3": float(np.mean(top3_correct)) if top3_correct else None,
        "harmonic_labeled_bins": harmonic_count,
        "harmonic_amplitude_mae": float(np.mean(harmonic_errors)) if harmonic_errors else None,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, default=Path("data/dataset/v5_2/manifest.csv"))
    parser.add_argument("--examples", type=int, default=1500)
    args = parser.parse_args()
    bundle = ProductBundle(args.artifact_dir)
    model = TFLitePitchModel(bundle, threads=1)
    model.min_pitch = int(bundle.metadata["min_pitch"])
    model.max_pitch = int(bundle.metadata["max_pitch"])
    model.active_threshold = float(bundle.metadata["active_threshold"])
    with args.manifest.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    groups: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        name = group_name(row)
        if name:
            groups[name].append(row)
    results = {}
    for number, name in enumerate(sorted(groups)):
        selected, total = select_examples(groups[name], args.examples, 6300 + number)
        results[name] = evaluate(model, selected, total)
        print(name, results[name])
    report = {
        "selection": "deterministic random windows, seed 6300 + sorted group index",
        "model_training_scope": "V6.0 GuitarSet train players 00-03",
        "groups": results,
        "gaps": {
            "available": Path("data/GAPS/gaps_metadata_with_splits.csv").is_file(),
            "included_in_monophonic_metrics": False,
            "reason": (
                "GAPS contient des partitions de guitare classique polyphoniques; "
                "le produit 1.0 a une seule sortie softmax pitch et ne peut pas "
                "representer plusieurs notes simultanees."
            ),
            "required_future_architecture": "multi-label pitch activation per MIDI class",
        },
    }
    output = args.artifact_dir / "external_sources_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    metadata_path = args.artifact_dir / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    metadata["validation"]["external_sources_report"] = output.name
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
