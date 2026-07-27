#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from src.dataset.tf_dataset import DatasetConfig, load_npz_arrays, prepare_subset


def topk_accuracy(probabilities, targets, k):
    topk = np.argpartition(probabilities, -k, axis=1)[:, -k:]
    return float(np.mean(np.any(topk == targets[:, None], axis=1)))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--validation-indices", type=Path, required=True)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--max-pitch", type=int, default=88)
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

    model = tf.keras.models.load_model(args.model)
    predictions = model.predict(inputs, batch_size=32, verbose=0)

    pitch_probabilities = predictions["pitch"]
    pitch_targets = targets["pitch"]
    pitch_valid = weights["pitch"] > 0.0
    visible_windows = metadata["visible_window"]

    print("Pitch accuracy by visible window")
    print("-" * 54)

    for window in sorted(np.unique(visible_windows)):
        mask = (visible_windows == window) & pitch_valid
        count = int(np.sum(mask))
        if count == 0:
            continue

        top1 = topk_accuracy(
            pitch_probabilities[mask],
            pitch_targets[mask],
            1,
        )
        top3 = topk_accuracy(
            pitch_probabilities[mask],
            pitch_targets[mask],
            3,
        )

        print(
            f"{int(window):4d} samples | "
            f"n={count:4d} | "
            f"top1={top1:.3%} | "
            f"top3={top3:.3%}"
        )

    total_mask = pitch_valid
    print("-" * 54)
    print(
        f"ALL          | "
        f"n={int(np.sum(total_mask)):4d} | "
        f"top1={topk_accuracy(pitch_probabilities[total_mask], pitch_targets[total_mask], 1):.3%} | "
        f"top3={topk_accuracy(pitch_probabilities[total_mask], pitch_targets[total_mask], 3):.3%}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
