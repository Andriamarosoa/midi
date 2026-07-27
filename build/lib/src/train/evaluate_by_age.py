#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from src.dataset.tf_dataset import DatasetConfig, load_npz_arrays, prepare_subset


def topk_accuracy(probabilities: np.ndarray, targets: np.ndarray, k: int) -> float:
    topk = np.argpartition(probabilities, -k, axis=1)[:, -k:]
    return float(np.mean(np.any(topk == targets[:, None], axis=1)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--validation-indices", type=Path, required=True)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--max-pitch", type=int, default=88)
    parser.add_argument(
        "--age-round-decimals",
        type=int,
        default=2,
        help="Nombre de décimales utilisé pour regrouper prediction_age_ms.",
    )
    args = parser.parse_args()

    import tensorflow as tf

    arrays = load_npz_arrays(args.npz)
    indices = np.load(args.validation_indices)

    config = DatasetConfig(
        batch_size=32,
        seed=42,
        normalize_audio=True,
        min_pitch=args.min_pitch,
        max_pitch=args.max_pitch,
        balance_pitch=False,
    )

    inputs, targets, weights, metadata = prepare_subset(
        arrays,
        indices,
        config,
        pitch_class_weights=None,
    )

    if "prediction_age_ms" not in arrays:
        raise SystemExit("La colonne prediction_age_ms est absente du NPZ.")

    ages = arrays["prediction_age_ms"][indices].astype(np.float32)
    valid_pitch = weights["pitch"] > 0.0

    model = tf.keras.models.load_model(args.model)
    predictions = model.predict(inputs, batch_size=32, verbose=0)
    pitch_probabilities = predictions["pitch"]
    pitch_targets = targets["pitch"]

    grouped_ages = np.round(ages, args.age_round_decimals)

    print("Pitch accuracy by prediction age")
    print("-" * 62)

    for age in sorted(np.unique(grouped_ages)):
        mask = (grouped_ages == age) & valid_pitch
        count = int(np.sum(mask))
        if count == 0:
            continue

        top1 = topk_accuracy(pitch_probabilities[mask], pitch_targets[mask], 1)
        top3 = topk_accuracy(pitch_probabilities[mask], pitch_targets[mask], 3)

        print(
            f"{float(age):8.2f} ms | "
            f"n={count:4d} | "
            f"top1={top1:.3%} | "
            f"top3={top3:.3%}"
        )

    print("-" * 62)
    total = valid_pitch
    print(
        f"ALL          | "
        f"n={int(np.sum(total)):4d} | "
        f"top1={topk_accuracy(pitch_probabilities[total], pitch_targets[total], 1):.3%} | "
        f"top3={topk_accuracy(pitch_probabilities[total], pitch_targets[total], 3):.3%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
