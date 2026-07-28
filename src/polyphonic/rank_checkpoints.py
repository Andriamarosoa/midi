"""Rank epoch checkpoints on validation without touching locked test data."""

from __future__ import annotations

import argparse
import gc
import json
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    dataset_balanced_validation_refs,
    load_manifest,
    natural_validation_refs,
)
from src.polyphonic.evaluate_frames import binary_metrics, select_threshold
from src.polyphonic.keras_compat import (
    load_polyphonic_checkpoint,
    predict_compat,
)


def pareto_candidates(rows: list[dict[str, object]]) -> list[str]:
    """Return checkpoints not dominated on frame, onset, or harmonics."""
    candidates: list[str] = []
    for row in rows:
        frame = float(row["frame_f1"])
        onset = float(row["onset_f1"])
        amplitude = float(row["harmonic_amplitude_mae"])
        offset = float(row["harmonic_offset_normalized_mae"])
        dominated = any(
            float(other["frame_f1"]) >= frame
            and float(other["onset_f1"]) >= onset
            and float(other["harmonic_amplitude_mae"]) <= amplitude
            and float(other["harmonic_offset_normalized_mae"]) <= offset
            and (
                float(other["frame_f1"]) > frame
                or float(other["onset_f1"]) > onset
                or float(other["harmonic_amplitude_mae"]) < amplitude
                or float(other["harmonic_offset_normalized_mae"]) < offset
            )
            for other in rows
            if other is not row
        )
        if not dominated:
            candidates.append(str(row["checkpoint"]))
    return candidates


def _targets(sequence: PolyphonicSequence) -> dict[str, np.ndarray]:
    parts: dict[str, list[np.ndarray]] = {
        "frame": [], "onset": [], "harmonic_amplitude": [],
        "harmonic_offset_cents": [],
    }
    for batch_index in range(len(sequence)):
        _, outputs = sequence[batch_index]
        for name in parts:
            parts[name].append(outputs[name])
    return {name: np.concatenate(values) for name, values in parts.items()}


def harmonic_metrics(
    targets: dict[str, np.ndarray],
    prediction: dict[str, np.ndarray],
    harmonic_count: int = 20,
    offset_scale_cents: float = 35.0,
) -> dict[str, float | int]:
    amplitude_target = targets["harmonic_amplitude"][..., :harmonic_count]
    valid = targets["harmonic_amplitude"][..., harmonic_count:2 * harmonic_count]
    valid_count = float(np.sum(valid))
    amplitude_error = np.abs(prediction["harmonic_amplitude"] - amplitude_target)
    amplitude_mae = float(np.sum(amplitude_error * valid) / max(valid_count, 1.0))
    offset_target = targets["harmonic_offset_cents"][..., :harmonic_count]
    offset_valid = targets["harmonic_offset_cents"][
        ..., harmonic_count:2 * harmonic_count
    ]
    offset_amplitude = targets["harmonic_offset_cents"][
        ..., 2 * harmonic_count:3 * harmonic_count
    ]
    weights = offset_valid * np.maximum(offset_amplitude, 0.0)
    weight_sum = float(np.sum(weights))
    offset_error = np.abs(
        prediction["harmonic_offset_cents"] - offset_target
    ) / float(offset_scale_cents)
    return {
        "valid_partials": int(round(valid_count)),
        "harmonic_amplitude_mae": amplitude_mae,
        "harmonic_offset_normalized_mae": float(
            np.sum(offset_error * weights) /
            (weight_sum if weight_sum > 0.0 else 1.0)
        ),
    }


def rank(
    run_dir: Path,
    maximum_examples: int = 20_000,
    checkpoint_glob: str = "epochs/*.keras",
) -> dict[str, object]:
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    checkpoints = sorted(run_dir.glob(checkpoint_glob))
    if not checkpoints:
        raise FileNotFoundError(
            f"No checkpoints matching {checkpoint_glob!r} in {run_dir}"
        )
    manifest = Path(config["dataset"]["manifest"])
    items = [item for item in load_manifest(manifest) if item.split == "validation"]
    corpus = PolyphonicCorpus(items)
    seed = int(config["dataset"].get("seed", 42))
    fractions = config["train"].get("validation_dataset_fractions")
    refs = (
        dataset_balanced_validation_refs(
            corpus, maximum_examples, fractions, seed + 29
        )
        if fractions
        else natural_validation_refs(corpus, maximum_examples, seed + 29)
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
    corpus.preload_audio()
    thresholds_root = run_dir / "checkpoint_thresholds"
    thresholds_root.mkdir(exist_ok=True)
    rows: list[dict[str, object]] = []
    try:
        targets = _targets(sequence)
        for checkpoint in checkpoints:
            model = load_polyphonic_checkpoint(checkpoint)
            inference = tf.keras.Model(
                model.inputs,
                {
                    "frame": model.get_layer("frame").output,
                    "onset": model.get_layer("onset").output,
                    "harmonic_amplitude": model.get_layer(
                        "harmonic_amplitude"
                    ).output,
                    "harmonic_offset_cents": model.get_layer(
                        "harmonic_offset_cents"
                    ).output,
                },
            )
            prediction = predict_compat(
                inference, sequence, verbose=0, workers=1
            )
            frame_threshold, frame_metrics = select_threshold(
                targets["frame"], prediction["frame"]
            )
            onset_threshold, onset_metrics = select_threshold(
                targets["onset"], prediction["onset"]
            )
            harmonics = harmonic_metrics(targets, prediction)
            threshold_path = thresholds_root / f"{checkpoint.stem}.json"
            threshold_path.write_text(json.dumps({
                "selected_on": "validation",
                "checkpoint": str(checkpoint),
                "examples": int(len(targets["frame"])),
                "frame": frame_threshold,
                "onset": onset_threshold,
                "frame_selection": frame_metrics,
                "onset_selection": onset_metrics,
            }, indent=2), encoding="utf-8")
            rows.append({
                "checkpoint": str(checkpoint),
                "thresholds": str(threshold_path),
                "frame_threshold": frame_threshold,
                "onset_threshold": onset_threshold,
                "frame_f1": float(frame_metrics["f1"]),
                "frame_precision": float(frame_metrics["precision"]),
                "frame_recall": float(frame_metrics["recall"]),
                "onset_f1": float(onset_metrics["f1"]),
                "onset_precision": float(onset_metrics["precision"]),
                "onset_recall": float(onset_metrics["recall"]),
                **harmonics,
            })
            del prediction, inference, model
            tf.keras.backend.clear_session()
            gc.collect()
    finally:
        corpus.close()
    report = {
        "run_dir": str(run_dir),
        "split": "validation",
        "examples": int(len(refs)),
        "locked_test_used": False,
        "checkpoints": rows,
        "pareto_candidates": pareto_candidates(rows),
        "next_step": (
            "Evaluate Pareto candidates with evaluate_events on validation; "
            "select once before opening either locked test split."
        ),
    }
    (run_dir / "checkpoint_ranking.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--maximum-examples", type=int, default=20_000)
    parser.add_argument("--checkpoint-glob", default="epochs/*.keras")
    args = parser.parse_args()
    report = rank(args.run_dir, args.maximum_examples, args.checkpoint_glob)
    print(json.dumps({
        "examples": report["examples"],
        "checkpoints": report["checkpoints"],
        "pareto_candidates": report["pareto_candidates"],
    }, indent=2))


if __name__ == "__main__":
    main()
