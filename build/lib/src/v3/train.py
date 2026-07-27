from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import json

import numpy as np

from src.v3.config import load_config
from src.v3.data import (
    make_limited_balanced_sequence,
    active_pitch_indices,
    compute_global_gain,
    load_arrays,
    make_validation_dataset,
    prepare_inputs,
    stratified_group_split,
)
from src.v3.evaluate import generate_reports
from src.v3.model import build_pitch_model


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    import tensorflow as tf

    config = load_config(args.config)
    tf.keras.utils.set_random_seed(config.data.seed)

    # ---------------------------------------------------------
    # Chargement du dataset
    # ---------------------------------------------------------

    arrays = load_arrays(config.data.npz)

    candidates = active_pitch_indices(
        arrays,
        config.data.min_pitch,
        config.data.max_pitch,
    )

    train_indices, val_indices, split_report = stratified_group_split(
        arrays=arrays,
        candidate_indices=candidates,
        validation_ratio=config.data.validation_ratio,
        seed=config.data.seed,
    )

    if len(train_indices) == 0:
        raise SystemExit("Le split ne contient aucun exemple d'entraînement.")

    if len(val_indices) == 0:
        raise SystemExit(
            "Aucune validation possible : ajoute plus de note_id par pitch "
            "ou plusieurs morceaux."
        )

    # ---------------------------------------------------------
    # Normalisation globale calculée uniquement sur le train
    # ---------------------------------------------------------

    gain = compute_global_gain(
        arrays=arrays,
        indices=train_indices,
        percentile=config.data.normalization_percentile,
        target=config.data.normalization_target,
        max_gain=config.data.max_gain,
    )

    train_inputs, train_targets, train_meta = prepare_inputs(
        arrays=arrays,
        indices=train_indices,
        min_pitch=config.data.min_pitch,
        gain=gain,
    )

    val_inputs, val_targets, val_meta = prepare_inputs(
        arrays=arrays,
        indices=val_indices,
        min_pitch=config.data.min_pitch,
        gain=gain,
    )

    # ---------------------------------------------------------
    # Création du dossier d'exécution
    # ---------------------------------------------------------

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    run_dir = (
        Path(config.train.output_root)
        / f"{config.train.run_name}_{timestamp}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "config.json").write_text(
        json.dumps(config.to_dict(), indent=2),
        encoding="utf-8",
    )

    (run_dir / "split_report.json").write_text(
        json.dumps(split_report, indent=2),
        encoding="utf-8",
    )

    (run_dir / "normalization.json").write_text(
        json.dumps({"gain": float(gain)}, indent=2),
        encoding="utf-8",
    )

    np.save(run_dir / "train_indices.npy", train_indices)
    np.save(run_dir / "validation_indices.npy", val_indices)

    # ---------------------------------------------------------
    # Dataset d'entraînement
    # ---------------------------------------------------------

    if config.sampler.enabled:
        train_data = make_limited_balanced_sequence(
            inputs=train_inputs,
            targets=train_targets,
            pitch_midi=train_meta["pitch_midi"],
            batch_size=config.train.batch_size,
            seed=config.data.seed,
            balance_strength=config.sampler.balance_strength,
            max_class_multiplier=config.sampler.max_class_multiplier,
            epoch_multiplier=config.sampler.epoch_multiplier,
        )
    else:
        train_data = (
            tf.data.Dataset.from_tensor_slices(
                (train_inputs, train_targets)
            )
            .shuffle(
                buffer_size=len(train_targets),
                seed=config.data.seed,
                reshuffle_each_iteration=True,
            )
            .batch(config.train.batch_size)
            .prefetch(tf.data.AUTOTUNE)
        )

    val_data = make_validation_dataset(
        val_inputs,
        val_targets,
        config.train.batch_size,
    )

    # ---------------------------------------------------------
    # Modèle
    # ---------------------------------------------------------

    pitch_classes = (
        config.data.max_pitch
        - config.data.min_pitch
        + 1
    )

    model = build_pitch_model(
        config.model,
        pitch_classes,
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=config.train.learning_rate
        ),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[
            tf.keras.metrics.SparseCategoricalAccuracy(
                name="top1"
            ),
            tf.keras.metrics.SparseTopKCategoricalAccuracy(
                k=3,
                name="top3",
            ),
        ],
    )

    # ---------------------------------------------------------
    # Callbacks
    # ---------------------------------------------------------

    history_path = run_dir / "history.csv"
    best_model_path = run_dir / "best.keras"

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(best_model_path),
            monitor="val_top1",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_top1",
            mode="max",
            patience=config.train.early_stopping_patience,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=0.5,
            patience=config.train.reduce_lr_patience,
            min_lr=config.train.min_learning_rate,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            str(history_path)
        ),
    ]

    # ---------------------------------------------------------
    # Entraînement
    # ---------------------------------------------------------

    model.summary()

    model.fit(
        train_data,
        validation_data=val_data,
        epochs=config.train.epochs,
        callbacks=callbacks,
    )

    # EarlyStopping a déjà restauré les meilleurs poids.
    # On sauvegarde donc directement le modèle restauré.
    final_model_path = run_dir / "final.keras"
    model.save(final_model_path)

    # ---------------------------------------------------------
    # Évaluation
    # ---------------------------------------------------------

    # Ne pas recharger best.keras ici.
    # Cela évite le crash provoqué par une Lambda Python non sérialisable.
    probabilities = model.predict(
        val_inputs,
        batch_size=config.train.batch_size,
        verbose=0,
    )

    metrics = generate_reports(
        run_dir=run_dir,
        probabilities=probabilities,
        targets=val_targets,
        metadata=val_meta,
        min_pitch=config.data.min_pitch,
        history_path=history_path,
        split_report=split_report,
        make_plots=config.evaluation.make_plots,
    )

    print("")
    print("V3 complete")
    print(f"  run          : {run_dir}")
    print(f"  gain         : {gain:.6f}")
    print(f"  train        : {len(train_indices)}")
    print(f"  validation   : {len(val_indices)}")
    print(f"  top1         : {metrics['top1']:.3%}")
    print(f"  top3         : {metrics['top3']:.3%}")
    print(f"  best model   : {best_model_path}")
    print(f"  final model  : {final_model_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())