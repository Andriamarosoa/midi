#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.dataset.tf_dataset import (
    DatasetConfig,
    compute_pitch_class_weights,
    load_npz_arrays,
    make_tf_dataset,
    prepare_subset,
    split_indices_by_note_id,
)
from src.model.cnn_tcn import ModelConfig, build_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("runs/v1_fixed"))
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--learning-rate", type=float, default=1e-3)
    parser.add_argument("--validation-ratio", type=float, default=0.20)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--max-pitch", type=int, default=88)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--no-pitch-balance", action="store_true")
    args = parser.parse_args()

    import tensorflow as tf

    tf.keras.utils.set_random_seed(args.seed)

    arrays = load_npz_arrays(args.npz)

    train_indices, validation_indices = split_indices_by_note_id(
        arrays,
        validation_ratio=args.validation_ratio,
        seed=args.seed,
    )

    config = DatasetConfig(
        batch_size=args.batch_size,
        seed=args.seed,
        normalize_audio=True,
        min_pitch=args.min_pitch,
        max_pitch=args.max_pitch,
        balance_pitch=not args.no_pitch_balance,
    )

    pitch_class_weights = compute_pitch_class_weights(
        arrays["pitch_midi"][train_indices],
        arrays["active"][train_indices],
        config.min_pitch,
        config.max_pitch,
    )

    train_inputs, train_targets, train_weights, train_meta = prepare_subset(
        arrays,
        train_indices,
        config,
        pitch_class_weights,
    )
    val_inputs, val_targets, val_weights, val_meta = prepare_subset(
        arrays,
        validation_indices,
        config,
        pitch_class_weights,
    )

    train_dataset = make_tf_dataset(
        train_inputs,
        train_targets,
        train_weights,
        batch_size=args.batch_size,
        shuffle=True,
        seed=args.seed,
    )
    validation_dataset = make_tf_dataset(
        val_inputs,
        val_targets,
        val_weights,
        batch_size=args.batch_size,
        shuffle=False,
        seed=args.seed,
    )

    model = build_model(
        ModelConfig(
            input_samples=arrays["audio"].shape[1],
            min_pitch=args.min_pitch,
            max_pitch=args.max_pitch,
        )
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(args.learning_rate),
        loss={
            "onset": tf.keras.losses.BinaryCrossentropy(),
            "attack_phase": tf.keras.losses.BinaryCrossentropy(),
            "active": tf.keras.losses.BinaryCrossentropy(),
            "release_phase": tf.keras.losses.BinaryCrossentropy(),
            "pitch": tf.keras.losses.SparseCategoricalCrossentropy(),
        },
        loss_weights={
            "onset": 1.5,
            "attack_phase": 1.0,
            "active": 1.0,
            "release_phase": 1.0,
            "pitch": 2.0,
        },
        metrics={
            "onset": [tf.keras.metrics.BinaryAccuracy(name="accuracy")],
            "attack_phase": [tf.keras.metrics.BinaryAccuracy(name="accuracy")],
            "active": [tf.keras.metrics.BinaryAccuracy(name="accuracy")],
            "release_phase": [tf.keras.metrics.BinaryAccuracy(name="accuracy")],
        },
        weighted_metrics={
            "pitch": [
                tf.keras.metrics.SparseCategoricalAccuracy(name="top1"),
                tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3"),
            ],
        },
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)

    np.save(args.output_dir / "train_indices.npy", train_indices)
    np.save(args.output_dir / "validation_indices.npy", validation_indices)
    np.save(args.output_dir / "pitch_class_weights.npy", pitch_class_weights)

    split_report = {
        "train_examples": int(len(train_indices)),
        "validation_examples": int(len(validation_indices)),
        "train_note_ids": sorted(np.unique(train_meta["note_id"][train_meta["note_id"] >= 0]).tolist()),
        "validation_note_ids": sorted(np.unique(val_meta["note_id"][val_meta["note_id"] >= 0]).tolist()),
    }
    (args.output_dir / "split_report.json").write_text(
        json.dumps(split_report, indent=2),
        encoding="utf-8",
    )

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(args.output_dir / "best.keras"),
            monitor="val_pitch_top1",
            mode="max",
            save_best_only=True,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_pitch_top1",
            mode="max",
            patience=8,
            restore_best_weights=True,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_pitch_top1",
            mode="max",
            factor=0.5,
            patience=4,
            min_lr=1e-6,
        ),
        tf.keras.callbacks.CSVLogger(
            str(args.output_dir / "history.csv")
        ),
    ]

    model.fit(
        train_dataset,
        validation_data=validation_dataset,
        epochs=args.epochs,
        callbacks=callbacks,
    )

    model.save(args.output_dir / "final.keras")

    print("")
    print("Entraînement terminé")
    print(f"  train examples      : {len(train_indices)}")
    print(f"  validation examples : {len(validation_indices)}")
    print(f"  sortie              : {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
