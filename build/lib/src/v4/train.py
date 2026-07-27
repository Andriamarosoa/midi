from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np

from .config import load_config
from .data import MultiNPZSequence, compute_global_gain
from .evaluate import generate_reports
from .manifest import load_manifest, split_manifest
from .model import build_pitch_model


def make_keras_sequence(sequence: MultiNPZSequence, tf: Any):
    """Wrap MultiNPZSequence as a real tf.keras.utils.Sequence."""

    class KerasSequenceAdapter(tf.keras.utils.Sequence):
        def __init__(self, wrapped: MultiNPZSequence) -> None:
            super().__init__()
            self.wrapped = wrapped

        def __len__(self) -> int:
            return len(self.wrapped)

        def __getitem__(self, index: int):
            return self.wrapped[index]

        def on_epoch_end(self) -> None:
            self.wrapped.on_epoch_end()

    return KerasSequenceAdapter(sequence)


def collect_targets(sequence: MultiNPZSequence) -> np.ndarray:
    """Collect targets from a finite validation/test sequence."""
    batches: list[np.ndarray] = []

    for batch_index in range(len(sequence)):
        _, targets = sequence[batch_index]
        batches.append(np.asarray(targets, dtype=np.int32))

    if not batches:
        return np.empty((0,), dtype=np.int32)

    return np.concatenate(batches, axis=0)


def collect_metadata(
    items,
    min_pitch: int,
    max_pitch: int,
) -> dict[str, np.ndarray]:
    """Rebuild metadata in the same file/example order as MultiNPZSequence."""

    metadata: dict[str, list] = {
        "prediction_age_ms": [],
        "visible_window": [],
        "pitch_midi": [],
        "player_id": [],
        "source_id": [],
        "note_id": [],
        "channel": [],
    }

    for item in items:
        npz_path = Path(item.npz_path)

        with np.load(npz_path) as data:
            pitch_midi = data["pitch_midi"].astype(np.int32)
            active = data["active"] > 0.5

            valid = (
                active
                & (pitch_midi >= min_pitch)
                & (pitch_midi <= max_pitch)
            )

            indices = np.flatnonzero(valid)
            count = len(indices)

            if count == 0:
                continue

            metadata["prediction_age_ms"].extend(
                data["prediction_age_ms"][indices]
                .astype(np.float32)
                .tolist()
            )

            metadata["visible_window"].extend(
                data["visible_window"][indices]
                .astype(np.int32)
                .tolist()
            )

            metadata["pitch_midi"].extend(
                pitch_midi[indices].tolist()
            )

            if "note_id" in data.files:
                metadata["note_id"].extend(
                    data["note_id"][indices]
                    .astype(np.int32)
                    .tolist()
                )
            else:
                metadata["note_id"].extend([-1] * count)

            if "channel" in data.files:
                metadata["channel"].extend(
                    data["channel"][indices]
                    .astype(np.int32)
                    .tolist()
                )
            else:
                metadata["channel"].extend([-1] * count)

            metadata["player_id"].extend(
                [str(item.player_id)] * count
            )

            metadata["source_id"].extend(
                [str(item.source_id)] * count
            )

    return {
        "prediction_age_ms": np.asarray(
            metadata["prediction_age_ms"],
            dtype=np.float32,
        ),
        "visible_window": np.asarray(
            metadata["visible_window"],
            dtype=np.int32,
        ),
        "pitch_midi": np.asarray(
            metadata["pitch_midi"],
            dtype=np.int32,
        ),
        "note_id": np.asarray(
            metadata["note_id"],
            dtype=np.int32,
        ),
        "channel": np.asarray(
            metadata["channel"],
            dtype=np.int32,
        ),
        "player_id": np.asarray(
            metadata["player_id"],
            dtype=str,
        ),
        "source_id": np.asarray(
            metadata["source_id"],
            dtype=str,
        ),
    }


def build_callbacks(
    tf: Any,
    run_dir: Path,
    cfg: Any,
) -> list[Any]:
    return [
        tf.keras.callbacks.ModelCheckpoint(
            filepath=str(run_dir / "best.keras"),
            monitor="val_top1",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_top1",
            mode="max",
            patience=cfg.train.early_stopping_patience,
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=0.5,
            patience=cfg.train.reduce_lr_patience,
            min_lr=cfg.train.min_learning_rate,
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            filename=str(run_dir / "history.csv"),
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Train the V4 multi-file causal pitch model."
    )
    parser.add_argument(
        "--config",
        type=Path,
        required=True,
        help="Path to configs/pitch_v4.yaml",
    )
    args = parser.parse_args()

    import tensorflow as tf

    cfg = load_config(args.config)
    tf.keras.utils.set_random_seed(cfg.data.seed)

    manifest_items = load_manifest(cfg.data.manifest)

    groups = split_manifest(
        manifest_items,
        cfg.data.train_players,
        cfg.data.validation_players,
        cfg.data.test_players,
    )

    if not groups["train"]:
        raise SystemExit("Aucun fichier dans le split train.")
    if not groups["validation"]:
        raise SystemExit("Aucun fichier dans le split validation.")
    if not groups["test"]:
        raise SystemExit("Aucun fichier dans le split test.")

    print("V4 split")
    print(f"  train files      : {len(groups['train'])}")
    print(f"  validation files : {len(groups['validation'])}")
    print(f"  test files       : {len(groups['test'])}")

    gain = compute_global_gain(
        groups["train"],
        cfg.data.min_pitch,
        cfg.data.max_pitch,
        cfg.data.normalization_percentile,
        cfg.data.normalization_target,
        cfg.data.max_gain,
        seed=cfg.data.seed,
    )

    raw_train = MultiNPZSequence(
        groups["train"],
        cfg.train.batch_size,
        cfg.data.min_pitch,
        cfg.data.max_pitch,
        gain,
        cfg.data.cache_files,
        True,
        cfg.data.seed,
    )

    raw_validation = MultiNPZSequence(
        groups["validation"],
        cfg.train.batch_size,
        cfg.data.min_pitch,
        cfg.data.max_pitch,
        gain,
        cfg.data.cache_files,
        False,
        cfg.data.seed,
    )

    raw_test = MultiNPZSequence(
        groups["test"],
        cfg.train.batch_size,
        cfg.data.min_pitch,
        cfg.data.max_pitch,
        gain,
        cfg.data.cache_files,
        False,
        cfg.data.seed,
    )

    train_sequence = make_keras_sequence(raw_train, tf)
    validation_sequence = make_keras_sequence(raw_validation, tf)
    test_sequence = make_keras_sequence(raw_test, tf)

    train_batches = len(raw_train)
    validation_batches = len(raw_validation)
    test_batches = len(raw_test)

    print("V4 batches")
    print(f"  train      : {train_batches}")
    print(f"  validation : {validation_batches}")
    print(f"  test       : {test_batches}")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = (
        Path(cfg.train.output_root)
        / f"{cfg.train.run_name}_{timestamp}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)

    (run_dir / "config.json").write_text(
        json.dumps(cfg.to_dict(), indent=2),
        encoding="utf-8",
    )

    (run_dir / "normalization.json").write_text(
        json.dumps({"gain": float(gain)}, indent=2),
        encoding="utf-8",
    )

    split_report = {
        split_name: [
            {
                "source_id": item.source_id,
                "player_id": item.player_id,
                "npz_path": str(item.npz_path),
            }
            for item in split_items
        ]
        for split_name, split_items in groups.items()
    }

    (run_dir / "split_report.json").write_text(
        json.dumps(split_report, indent=2),
        encoding="utf-8",
    )

    pitch_classes = (
        cfg.data.max_pitch
        - cfg.data.min_pitch
        + 1
    )

    model = build_pitch_model(
        cfg.model,
        pitch_classes,
    )

    model.compile(
        optimizer=tf.keras.optimizers.Adam(
            learning_rate=cfg.train.learning_rate,
        ),
        loss=tf.keras.losses.SparseCategoricalCrossentropy(),
        metrics=[
            tf.keras.metrics.SparseCategoricalAccuracy(
                name="top1",
            ),
            tf.keras.metrics.SparseTopKCategoricalAccuracy(
                k=3,
                name="top3",
            ),
        ],
    )

    callbacks = build_callbacks(
        tf,
        run_dir,
        cfg,
    )

    model.summary()

    fit_kwargs: dict[str, Any] = {
        "x": train_sequence,
        "validation_data": validation_sequence,
        "epochs": cfg.train.epochs,
        "callbacks": callbacks,
        "workers": 1,
        "use_multiprocessing": False,
        "max_queue_size": 2,
        "verbose": 1,
    }

    steps_per_epoch = getattr(
        cfg.train,
        "steps_per_epoch",
        None,
    )

    if steps_per_epoch is not None:
        steps_per_epoch = int(steps_per_epoch)
        if steps_per_epoch <= 0:
            raise ValueError(
                "train.steps_per_epoch doit être positif ou null."
            )
        fit_kwargs["steps_per_epoch"] = min(
            steps_per_epoch,
            len(train_sequence),
        )

    validation_steps = getattr(
        cfg.train,
        "validation_steps",
        None,
    )

    if validation_steps is not None:
        validation_steps = int(validation_steps)
        if validation_steps <= 0:
            raise ValueError(
                "train.validation_steps doit être positif ou null."
            )
        fit_kwargs["validation_steps"] = min(
            validation_steps,
            len(validation_sequence),
        )

    model.fit(**fit_kwargs)

    final_model_path = run_dir / "final.keras"
    model.save(final_model_path)

    probabilities = model.predict(
        test_sequence,
        workers=1,
        use_multiprocessing=False,
        max_queue_size=2,
        verbose=1,
    )

    test_targets = collect_targets(raw_test)

    test_metadata = collect_metadata(
        groups["test"],
        cfg.data.min_pitch,
        cfg.data.max_pitch,
    )

    if len(probabilities) != len(test_targets):
        raise RuntimeError(
            "Nombre de prédictions incohérent : "
            f"{len(probabilities)} prédictions, "
            f"{len(test_targets)} labels."
        )

    metadata_count = len(
        test_metadata["pitch_midi"]
    )

    if metadata_count != len(test_targets):
        raise RuntimeError(
            "Nombre de métadonnées incohérent : "
            f"{metadata_count} métadonnées, "
            f"{len(test_targets)} labels."
        )

    metrics = generate_reports(
        run_dir,
        probabilities,
        test_targets,
        test_metadata,
        cfg.data.min_pitch,
    )

    print("")
    print("V4 complete")
    print(f"  run          : {run_dir}")
    print(f"  gain         : {gain:.6f}")
    print(
        "  files        : "
        f"train={len(groups['train'])} "
        f"validation={len(groups['validation'])} "
        f"test={len(groups['test'])}"
    )
    print(
        "  batches      : "
        f"train={train_batches} "
        f"validation={validation_batches} "
        f"test={test_batches}"
    )
    print(f"  test samples : {len(test_targets)}")
    print(f"  top1         : {metrics['top1']:.3%}")
    print(f"  top3         : {metrics['top3']:.3%}")
    print(f"  best model   : {run_dir / 'best.keras'}")
    print(f"  final model  : {final_model_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())