#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
from pathlib import Path

import numpy as np

from src.dataset.tf_dataset import DatasetConfig, load_npz_arrays, prepare_subset


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--validation-indices", type=Path, required=True)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--max-pitch", type=int, default=88)
    parser.add_argument(
        "--output-csv",
        type=Path,
        default=Path("runs/v1_fixed/confusion_matrix.csv"),
    )
    parser.add_argument(
        "--top-confusions",
        type=int,
        default=20,
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

    model = tf.keras.models.load_model(args.model)
    predictions = model.predict(inputs, batch_size=32, verbose=0)

    valid = weights["pitch"] > 0.0
    true_classes = targets["pitch"][valid].astype(np.int32)
    pred_classes = np.argmax(predictions["pitch"][valid], axis=1).astype(np.int32)

    true_midi = true_classes + args.min_pitch
    pred_midi = pred_classes + args.min_pitch

    classes = np.arange(args.min_pitch, args.max_pitch + 1)
    matrix = np.zeros((len(classes), len(classes)), dtype=np.int64)

    for true_value, pred_value in zip(true_midi, pred_midi):
        matrix[true_value - args.min_pitch, pred_value - args.min_pitch] += 1

    args.output_csv.parent.mkdir(parents=True, exist_ok=True)

    with args.output_csv.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true_midi", *[str(v) for v in classes]])
        for row_midi, row in zip(classes, matrix):
            writer.writerow([int(row_midi), *[int(v) for v in row]])

    confusions = []
    for true_index, true_value in enumerate(classes):
        row_total = int(matrix[true_index].sum())
        if row_total == 0:
            continue

        for pred_index, pred_value in enumerate(classes):
            count = int(matrix[true_index, pred_index])
            if count == 0 or true_value == pred_value:
                continue

            confusions.append(
                (
                    count,
                    count / row_total,
                    int(true_value),
                    int(pred_value),
                    int(pred_value - true_value),
                )
            )

    confusions.sort(reverse=True)

    print("Most frequent pitch confusions")
    print("-" * 72)
    for count, ratio, true_midi_value, pred_midi_value, delta in confusions[:args.top_confusions]:
        print(
            f"true={true_midi_value:3d} "
            f"pred={pred_midi_value:3d} "
            f"delta={delta:+3d} semitones "
            f"count={count:3d} "
            f"row_ratio={ratio:.2%}"
        )

    octave_errors = int(np.sum(np.abs(pred_midi - true_midi) == 12))
    semitone_errors = int(np.sum(np.abs(pred_midi - true_midi) == 1))
    exact = int(np.sum(pred_midi == true_midi))
    total = len(true_midi)

    print("")
    print(f"Exact             : {exact}/{total} ({exact / total:.3%})")
    print(f"Semitone errors   : {semitone_errors}/{total} ({semitone_errors / total:.3%})")
    print(f"Octave errors     : {octave_errors}/{total} ({octave_errors / total:.3%})")
    print(f"CSV               : {args.output_csv}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
