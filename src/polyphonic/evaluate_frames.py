"""Select validation thresholds and evaluate polyphonic frame predictions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    dataset_balanced_validation_refs,
    load_manifest,
    natural_validation_refs,
)
from src.polyphonic.keras_compat import (
    load_polyphonic_checkpoint,
    predict_compat,
)
from src.polyphonic import model as _registered_model_types  # noqa: F401


def binary_metrics(
    truth: np.ndarray,
    probability: np.ndarray,
    threshold: float,
) -> dict[str, float | int]:
    truth_bool = np.asarray(truth > 0.5)
    predicted = np.asarray(probability >= threshold)
    true_positive = int(np.sum(truth_bool & predicted))
    false_positive = int(np.sum(~truth_bool & predicted))
    false_negative = int(np.sum(truth_bool & ~predicted))
    true_negative = int(np.sum(~truth_bool & ~predicted))
    precision = true_positive / max(true_positive + false_positive, 1)
    recall = true_positive / max(true_positive + false_negative, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        "threshold": float(threshold),
        "true_positive": true_positive,
        "false_positive": false_positive,
        "false_negative": false_negative,
        "true_negative": true_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def select_threshold(
    truth: np.ndarray,
    probability: np.ndarray,
    candidates: np.ndarray | None = None,
) -> tuple[float, dict[str, float | int]]:
    if candidates is None:
        candidates = np.linspace(0.05, 0.95, 181)
    scored = [binary_metrics(truth, probability, float(value)) for value in candidates]
    best = max(
        scored,
        key=lambda row: (float(row["f1"]), float(row["precision"]), -float(row["threshold"])),
    )
    return float(best["threshold"]), best


def _per_pitch(
    truth: np.ndarray,
    probability: np.ndarray,
    threshold: float,
    midi_min: int,
) -> dict[str, dict[str, float | int]]:
    return {
        str(midi_min + index): binary_metrics(
            truth[:, index], probability[:, index], threshold
        )
        for index in range(truth.shape[1])
    }


def _subgroup_metrics(
    truth: np.ndarray,
    probability: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    polyphony = np.sum(truth > 0.5, axis=1)
    groups = {
        "silence": polyphony == 0,
        "monophonic": polyphony == 1,
        "polyphonic": polyphony >= 2,
    }
    result: dict[str, object] = {}
    for name, mask in groups.items():
        if not np.any(mask):
            result[name] = None
            continue
        metrics = binary_metrics(truth[mask], probability[mask], threshold)
        predicted_polyphony = np.sum(probability[mask] >= threshold, axis=1)
        result[name] = {
            **metrics,
            "frames": int(np.sum(mask)),
            "true_mean_polyphony": float(np.mean(polyphony[mask])),
            "predicted_mean_polyphony": float(np.mean(predicted_polyphony)),
            "exact_match": float(np.mean(np.all(
                (probability[mask] >= threshold) == (truth[mask] > 0.5),
                axis=1,
            ))),
        }
    return result


def _targets(sequence: PolyphonicSequence) -> tuple[np.ndarray, np.ndarray]:
    frame: list[np.ndarray] = []
    onset: list[np.ndarray] = []
    for index in range(len(sequence)):
        _, batch = sequence[index]
        frame.append(batch["frame"])
        onset.append(batch["onset"])
    return np.concatenate(frame), np.concatenate(onset)


def evaluate(
    run_dir: Path,
    split: str,
    maximum_examples: int | None,
    select_on_validation: bool,
    dataset_id: str | None = None,
    checkpoint_path: Path | None = None,
    thresholds_path: Path | None = None,
    excluded_group_ids: set[str] | None = None,
) -> dict[str, object]:
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    items = [
        item for item in load_manifest(Path(config["dataset"]["manifest"]))
        if item.split == split
        and (dataset_id is None or item.dataset_id == dataset_id)
        and item.group_id not in set(excluded_group_ids or ())
    ]
    corpus = PolyphonicCorpus(items)
    seed = int(config["dataset"].get("seed", 42))
    validation_fractions = config["train"].get("validation_dataset_fractions")
    refs = (
        dataset_balanced_validation_refs(
            corpus, int(maximum_examples), validation_fractions, seed + 10
        )
        if dataset_id is None
        and validation_fractions
        and maximum_examples is not None
        else natural_validation_refs(corpus, maximum_examples, seed + 10)
    )
    sequence = PolyphonicSequence(
        corpus,
        batch_size=int(config["train"]["batch_size"]),
        input_samples=int(config["dataset"]["input_samples"]),
        normalization_gain=float(config["dataset"]["normalization_gain"]),
        seed=seed,
        refs=refs,
        shuffle=False,
    )
    default_checkpoint = (
        run_dir / "selected.keras"
        if (run_dir / "selected.keras").is_file()
        else run_dir / "best.keras"
    )
    checkpoint = checkpoint_path or default_checkpoint
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    model = load_polyphonic_checkpoint(checkpoint)
    inference_model = tf.keras.Model(
        model.inputs,
        {
            "frame": model.get_layer("frame").output,
            "onset": model.get_layer("onset").output,
        },
    )
    corpus.preload_audio()
    try:
        predictions = predict_compat(
            inference_model, sequence, verbose=1, workers=1
        )
        frame_truth, onset_truth = _targets(sequence)
    finally:
        corpus.close()

    threshold_path = thresholds_path or (run_dir / "thresholds.json")
    if select_on_validation:
        frame_threshold, frame_selection = select_threshold(
            frame_truth, predictions["frame"]
        )
        onset_threshold, onset_selection = select_threshold(
            onset_truth, predictions["onset"]
        )
        thresholds = {
            "selected_on": split,
            "frame": frame_threshold,
            "onset": onset_threshold,
            "frame_selection": frame_selection,
            "onset_selection": onset_selection,
        }
        threshold_path.write_text(
            json.dumps(thresholds, indent=2), encoding="utf-8"
        )
    else:
        thresholds = json.loads(threshold_path.read_text(encoding="utf-8"))
        frame_threshold = float(thresholds["frame"])
        onset_threshold = float(thresholds["onset"])

    frame_metrics = binary_metrics(
        frame_truth, predictions["frame"], frame_threshold
    )
    onset_metrics = binary_metrics(
        onset_truth, predictions["onset"], onset_threshold
    )
    predicted = predictions["frame"] >= frame_threshold
    truth_bool = frame_truth > 0.5
    per_pitch = _per_pitch(
        frame_truth, predictions["frame"], frame_threshold, corpus.midi_min
    )
    supported_pitch_f1 = [
        float(row["f1"])
        for row in per_pitch.values()
        if int(row["true_positive"]) + int(row["false_negative"]) > 0
    ]
    report: dict[str, object] = {
        "run_dir": str(run_dir),
        "checkpoint": str(checkpoint),
        "split": split,
        "dataset_id": dataset_id,
        "excluded_group_ids": sorted(excluded_group_ids or ()),
        "thresholds_reselected": bool(select_on_validation),
        "locked_test_opened_after_selection": bool(
            split == "test" and not select_on_validation
        ),
        "examples": len(frame_truth),
        "midi_range": [corpus.midi_min, corpus.midi_max],
        "thresholds": {"frame": frame_threshold, "onset": onset_threshold},
        "frame": {
            **frame_metrics,
            "exact_match": float(np.mean(np.all(predicted == truth_bool, axis=1))),
            "macro_f1_supported_pitches": float(np.mean(supported_pitch_f1)),
        },
        "onset": onset_metrics,
        "subgroups": _subgroup_metrics(
            frame_truth, predictions["frame"], frame_threshold
        ),
        "per_pitch": per_pitch,
    }
    reports = run_dir / "reports"
    reports.mkdir(exist_ok=True)
    checkpoint_suffix = (
        f"_{checkpoint.stem}" if checkpoint_path is not None else ""
    )
    report_name = (
        f"{split}_{dataset_id}_frames{checkpoint_suffix}.json" if dataset_id
        else f"{split}_frames{checkpoint_suffix}.json"
    )
    (reports / report_name).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test"), required=True)
    parser.add_argument("--maximum-examples", type=int, default=60_000)
    parser.add_argument("--select-thresholds", action="store_true")
    parser.add_argument("--dataset-id")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--thresholds", type=Path)
    parser.add_argument("--exclusion-report", type=Path)
    args = parser.parse_args()
    excluded_group_ids: set[str] = set()
    if args.exclusion_report:
        exclusion = json.loads(args.exclusion_report.read_text(encoding="utf-8"))
        excluded_group_ids = set(exclusion["groups_to_exclude"])
    report = evaluate(
        args.run_dir,
        args.split,
        args.maximum_examples if args.maximum_examples > 0 else None,
        args.select_thresholds,
        args.dataset_id,
        args.checkpoint,
        args.thresholds,
        excluded_group_ids,
    )
    print(json.dumps({
        "split": report["split"],
        "examples": report["examples"],
        "thresholds": report["thresholds"],
        "frame": report["frame"],
        "onset": report["onset"],
        "subgroups": report["subgroups"],
    }, indent=2))


if __name__ == "__main__":
    main()
