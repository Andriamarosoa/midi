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

    probabilities = predictions["pitch"]
    targets_pitch = targets["pitch"]
    valid = weights["pitch"] > 0.0
    midi_values = metadata["pitch_midi"]

    print("Pitch accuracy by MIDI note")
    print("-" * 58)

    for midi in sorted(np.unique(midi_values[valid])):
        mask = valid & (midi_values == midi)
        count = int(np.sum(mask))
        top1 = topk_accuracy(probabilities[mask], targets_pitch[mask], 1)
        top3 = topk_accuracy(probabilities[mask], targets_pitch[mask], 3)

        print(
            f"MIDI {int(midi):3d} | "
            f"n={count:4d} | "
            f"top1={top1:.3%} | "
            f"top3={top3:.3%}"
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
