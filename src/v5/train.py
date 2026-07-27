from __future__ import annotations

import argparse
import json
import platform
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

from .cache import NPZRamCache
from .config import load_config
from .dataloader import V5Sequence
from .dataset import GlobalSampleIndex
from .evaluate import generate_harmonic_reports, generate_reports
from .losses import (
    AmplitudeWeightedHarmonicOffsetLoss,
    MaskedHarmonicAmplitudeLoss,
)
from .manifest import load_manifest, split_manifest
from .model import build_pitch_model


def compute_global_gain(
    cache: NPZRamCache,
    sample_index: GlobalSampleIndex,
    percentile: float,
    target: float,
    max_gain: float,
) -> float:
    peaks = []

    for file_index, sample_id in sample_index.refs:
        waveform = cache[int(file_index)].arrays["audio"][int(sample_id)]
        peaks.append(float(np.max(np.abs(waveform))))

    reference = float(np.percentile(np.asarray(peaks), percentile)) if peaks else 1.0
    return min(float(max_gain), float(target) / max(reference, 1e-8))


def compute_class_weights(
    sample_index: GlobalSampleIndex,
    min_pitch: int,
    max_pitch: int,
    max_weight: float,
) -> np.ndarray:
    """Compute capped balanced weights exclusively from the train split."""
    class_count = int(max_pitch) - int(min_pitch) + 1
    if class_count <= 1:
        raise ValueError("La plage MIDI doit contenir au moins deux classes.")
    if max_weight <= 0.0:
        raise ValueError("max_class_weight doit être strictement positif.")

    labels = sample_index.pitch_midi - int(min_pitch)
    counts = np.bincount(labels, minlength=class_count).astype(np.float64)
    present = counts > 0
    weights = np.zeros(class_count, dtype=np.float32)
    balanced = len(labels) / (np.sum(present) * counts[present])
    weights[present] = np.minimum(balanced, float(max_weight))
    return weights


def cache_statistics_by_dataset(
    cache: NPZRamCache,
    min_pitch: int,
    max_pitch: int,
) -> dict[str, dict[str, object]]:
    file_counts: Counter[str] = Counter()
    sample_counts: Counter[str] = Counter()
    pitch_counts: dict[str, Counter[int]] = {}

    for cached_file in cache.files:
        dataset_id = cached_file.dataset_id
        file_counts[dataset_id] += 1
        pitches = np.asarray(cached_file.arrays["pitch_midi"], dtype=np.int32)
        active = np.asarray(cached_file.arrays["active"], dtype=np.float32) > 0.5
        selected = pitches[active & (pitches >= min_pitch) & (pitches <= max_pitch)]
        sample_counts[dataset_id] += len(selected)
        pitch_counts.setdefault(dataset_id, Counter()).update(map(int, selected))

    return {
        dataset_id: {
            "files": int(file_counts[dataset_id]),
            "samples": int(sample_counts[dataset_id]),
            "class_distribution": {
                str(pitch): int(pitch_counts[dataset_id].get(pitch, 0))
                for pitch in range(min_pitch, max_pitch + 1)
            },
        }
        for dataset_id in sorted(file_counts)
    }


def git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def concatenate_targets(sequence: V5Sequence) -> dict[str, np.ndarray]:
    batches = [sequence[index][1] for index in range(len(sequence))]
    first = batches[0]
    if isinstance(first, dict):
        return {
            name: np.concatenate([batch[name] for batch in batches], axis=0)
            for name in first
        }
    return {"pitch": np.concatenate(batches, axis=0)}


def predictions_by_name(model, predictions) -> dict[str, np.ndarray]:
    if isinstance(predictions, dict):
        return {
            str(name): np.asarray(values)
            for name, values in predictions.items()
        }
    if isinstance(predictions, (list, tuple)):
        return {
            str(name): np.asarray(values)
            for name, values in zip(model.output_names, predictions)
        }
    return {"pitch": np.asarray(predictions)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    import tensorflow as tf

    cfg = load_config(args.config)
    tf.keras.utils.set_random_seed(cfg.dataset.seed)

    manifest_items = load_manifest(cfg.dataset.manifest)
    if cfg.dataset.include_datasets:
        requested_datasets = set(cfg.dataset.include_datasets)
        available_datasets = {item.dataset_id for item in manifest_items}
        unknown_datasets = requested_datasets - available_datasets
        if unknown_datasets:
            raise ValueError(
                f"Datasets demandés absents du manifest: {sorted(unknown_datasets)}"
            )
        manifest_items = [
            item for item in manifest_items
            if item.dataset_id in requested_datasets
        ]
    groups = split_manifest(
        manifest_items,
        cfg.dataset.train_players,
        cfg.dataset.validation_players,
        cfg.dataset.test_players,
    )

    print("Chargement cache RAM...")
    train_cache = NPZRamCache(groups["train"], cfg.cache.validate_schema)
    validation_cache = NPZRamCache(groups["validation"], cfg.cache.validate_schema)
    test_cache = NPZRamCache(groups["test"], cfg.cache.validate_schema)

    train_cache.load()
    validation_cache.load()
    test_cache.load()

    train_index = GlobalSampleIndex(train_cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch)
    validation_index = GlobalSampleIndex(validation_cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch)
    test_index = GlobalSampleIndex(test_cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch)

    gain = compute_global_gain(
        train_cache,
        train_index,
        cfg.dataset.normalization_percentile,
        cfg.dataset.normalization_target,
        cfg.dataset.max_gain,
    )
    class_weights = compute_class_weights(
        train_index,
        cfg.dataset.min_pitch,
        cfg.dataset.max_pitch,
        cfg.train.max_class_weight,
    ) if cfg.train.use_class_weights else None

    train_data = V5Sequence(
        train_cache,
        train_index,
        cfg.train.batch_size,
        cfg.dataset.min_pitch,
        gain,
        cfg.dataset.seed,
        True,
        class_weights=class_weights,
        harmonic_targets=cfg.model.harmonic_auxiliary,
        harmonic_count=cfg.model.harmonic_count,
    )
    validation_data = V5Sequence(
        validation_cache,
        validation_index,
        cfg.train.batch_size,
        cfg.dataset.min_pitch,
        gain,
        cfg.dataset.seed,
        False,
        harmonic_targets=cfg.model.harmonic_auxiliary,
        harmonic_count=cfg.model.harmonic_count,
    )
    test_data = V5Sequence(
        test_cache,
        test_index,
        cfg.train.batch_size,
        cfg.dataset.min_pitch,
        gain,
        cfg.dataset.seed,
        False,
        harmonic_targets=cfg.model.harmonic_auxiliary,
        harmonic_count=cfg.model.harmonic_count,
    )

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = cfg.train.output_root / f"{cfg.train.run_name}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)

    runtime_info = {
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "numpy": np.__version__,
        "git_commit": git_commit(),
        "cache_gib": {
            "train": train_cache.gib_used,
            "validation": validation_cache.gib_used,
            "test": test_cache.gib_used,
        },
    }

    (run_dir / "config.json").write_text(
        json.dumps(cfg.to_dict(), indent=2),
        encoding="utf-8",
    )
    (run_dir / "runtime.json").write_text(
        json.dumps(runtime_info, indent=2),
        encoding="utf-8",
    )
    (run_dir / "normalization.json").write_text(
        json.dumps({"gain": gain}, indent=2),
        encoding="utf-8",
    )
    split_report = {
        split_name: [
            {
                "source_id": item.source_id,
                "dataset_id": item.dataset_id,
                "player_id": item.player_id,
                "group_id": item.group_id,
                "capture_id": item.capture_id,
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
    dataset_statistics = {
        "files": {
            "train": len(train_cache),
            "validation": len(validation_cache),
            "test": len(test_cache),
        },
        "samples": {
            "train": len(train_index),
            "validation": len(validation_index),
            "test": len(test_index),
        },
        "class_distribution": {
            "train": train_index.class_distribution(),
            "validation": validation_index.class_distribution(),
            "test": test_index.class_distribution(),
        },
        "by_dataset": {
            "train": cache_statistics_by_dataset(
                train_cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch
            ),
            "validation": cache_statistics_by_dataset(
                validation_cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch
            ),
            "test": cache_statistics_by_dataset(
                test_cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch
            ),
        },
        "class_weights": (
            None if class_weights is None else {
                str(midi): float(class_weights[midi - cfg.dataset.min_pitch])
                for midi in range(cfg.dataset.min_pitch, cfg.dataset.max_pitch + 1)
            }
        ),
    }

    (run_dir / "dataset_statistics.json").write_text(
        json.dumps(dataset_statistics, indent=2),
        encoding="utf-8",
    )

    model = build_pitch_model(
        cfg.model,
        cfg.dataset.max_pitch - cfg.dataset.min_pitch + 1,
        input_samples=cfg.dataset.max_window,
    )
    optimizer = tf.keras.optimizers.Adam(cfg.train.learning_rate)
    pitch_metrics = [
        tf.keras.metrics.SparseCategoricalAccuracy(name="top1"),
        tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3"),
    ]
    if cfg.model.harmonic_auxiliary:
        model.compile(
            optimizer=optimizer,
            loss={
                "pitch": tf.keras.losses.SparseCategoricalCrossentropy(),
                "harmonic_amplitude": MaskedHarmonicAmplitudeLoss(
                    cfg.model.harmonic_count
                ),
                "harmonic_offset_cents": AmplitudeWeightedHarmonicOffsetLoss(
                    cfg.model.harmonic_count,
                    cfg.model.harmonic_offset_scale_cents,
                ),
            },
            loss_weights={
                "pitch": 1.0,
                "harmonic_amplitude": cfg.model.harmonic_amplitude_loss_weight,
                "harmonic_offset_cents": cfg.model.harmonic_offset_loss_weight,
            },
            metrics={"pitch": pitch_metrics},
        )
        monitor_metric = "val_pitch_top1"
    else:
        model.compile(
            optimizer=optimizer,
            loss=tf.keras.losses.SparseCategoricalCrossentropy(),
            metrics=pitch_metrics,
        )
        monitor_metric = "val_top1"

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "best.keras"),
            monitor=monitor_metric,
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor=monitor_metric,
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
        tf.keras.callbacks.CSVLogger(str(run_dir / "history.csv")),
        tf.keras.callbacks.TerminateOnNaN(),
    ]

    model.summary()
    model.fit(
        train_data,
        validation_data=validation_data,
        epochs=cfg.train.epochs,
        callbacks=callbacks,
        workers=cfg.train.workers,
        use_multiprocessing=False,
        max_queue_size=2,
    )

    model.save(run_dir / "final.keras")

    # Always evaluate the checkpoint selected by validation, even when the
    # epoch limit is reached before EarlyStopping restores its best weights.
    evaluation_model = tf.keras.models.load_model(run_dir / "best.keras")

    raw_predictions = evaluation_model.predict(
        test_data,
        workers=cfg.train.workers,
        use_multiprocessing=False,
        max_queue_size=2,
        verbose=1,
    )
    predictions = predictions_by_name(evaluation_model, raw_predictions)
    targets = concatenate_targets(test_data)
    metadata = test_data.metadata()

    metrics = generate_reports(
        run_dir,
        predictions["pitch"],
        targets["pitch"],
        metadata,
        cfg.dataset.min_pitch,
        evaluated_checkpoint="best.keras",
    )
    harmonic_metrics = None
    if cfg.model.harmonic_auxiliary:
        harmonic_metrics = generate_harmonic_reports(
            run_dir,
            predictions,
            targets,
            cfg.model.harmonic_count,
        )

    print("")
    print("V5 complete")
    print(f"  run          : {run_dir}")
    print(f"  train samples: {len(train_index)}")
    print(f"  val samples  : {len(validation_index)}")
    print(f"  test samples : {len(test_index)}")
    print(f"  cache RAM    : {runtime_info['cache_gib']}")
    print(f"  top1         : {metrics['top1']:.3%}")
    print(f"  top3         : {metrics['top3']:.3%}")
    if harmonic_metrics is not None:
        print(
            "  harmonic amp : "
            f"MAE {harmonic_metrics['amplitude_mae']:.4f}"
        )
        print(
            "  harmonic off : "
            f"MAE {harmonic_metrics['amplitude_weighted_offset_mae_cents']:.2f} cents"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
