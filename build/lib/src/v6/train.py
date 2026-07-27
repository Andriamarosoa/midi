from __future__ import annotations

import argparse
import json
import platform
from collections import Counter
from datetime import datetime
from pathlib import Path

import numpy as np

from src.v5.cache import NPZRamCache
from src.v5.config import load_config
from src.v5.losses import (
    AmplitudeWeightedHarmonicOffsetLoss,
    MaskedHarmonicAmplitudeLoss,
)
from src.v5.manifest import load_manifest, split_manifest
from src.v5.model import build_pitch_model
from src.v5.train import git_commit, predictions_by_name

from .dataloader import V6Sequence
from .dataset import GlobalSampleIndex
from .evaluate import (
    generate_v6_reports,
    select_f1_threshold,
)


def compute_global_gain(
    cache: NPZRamCache,
    sample_index: GlobalSampleIndex,
    percentile: float,
    target: float,
    max_gain: float,
) -> float:
    """Preserve V5 normalization by estimating gain on active notes only."""
    peaks: list[float] = []
    for (file_index, sample_id), active in zip(
        sample_index.refs, sample_index.active
    ):
        if active <= 0.5:
            continue
        waveform = cache[int(file_index)].arrays["audio"][int(sample_id)]
        peaks.append(float(np.max(np.abs(waveform))))
    reference = float(np.percentile(peaks, percentile)) if peaks else 1.0
    return min(float(max_gain), float(target) / max(reference, 1e-8))


def compute_pitch_class_weights(
    sample_index: GlobalSampleIndex,
    min_pitch: int,
    max_pitch: int,
    max_weight: float,
) -> np.ndarray:
    classes = int(max_pitch) - int(min_pitch) + 1
    labels = sample_index.pitch_midi[sample_index.positive_mask] - int(min_pitch)
    counts = np.bincount(labels, minlength=classes).astype(np.float64)
    present = counts > 0
    weights = np.zeros(classes, dtype=np.float32)
    weights[present] = np.minimum(
        len(labels) / (max(int(np.sum(present)), 1) * counts[present]),
        float(max_weight),
    )
    return weights


def compute_activity_weights(sample_index: GlobalSampleIndex) -> np.ndarray:
    positive = int(np.sum(sample_index.positive_mask))
    negative = int(len(sample_index) - positive)
    if positive == 0 or negative == 0:
        raise ValueError("Les deux classes active sont requises.")
    total = positive + negative
    return np.asarray(
        [total / (2.0 * negative), total / (2.0 * positive)],
        dtype=np.float32,
    )


def compute_onset_weights(sample_index: GlobalSampleIndex) -> np.ndarray:
    positive = int(np.sum(sample_index.onset > 0.5))
    negative = int(len(sample_index) - positive)
    if positive == 0 or negative == 0:
        raise ValueError("Les deux classes onset sont requises.")
    total = positive + negative
    return np.asarray(
        [total / (2.0 * negative), total / (2.0 * positive)],
        dtype=np.float32,
    )


def concatenate_targets(sequence: V6Sequence) -> dict[str, np.ndarray]:
    batches = [sequence[index][1] for index in range(len(sequence))]
    return {
        name: np.concatenate([batch[name] for batch in batches], axis=0)
        for name in batches[0]
    }


def cache_statistics(
    cache: NPZRamCache,
    min_pitch: int,
    max_pitch: int,
) -> dict[str, dict[str, object]]:
    file_counts: Counter[str] = Counter()
    active_counts: Counter[str] = Counter()
    inactive_counts: Counter[str] = Counter()
    pitch_counts: dict[str, Counter[int]] = {}
    for cached in cache.files:
        dataset_id = cached.dataset_id
        file_counts[dataset_id] += 1
        active = np.asarray(cached.arrays["active"], dtype=np.float32) > 0.5
        pitch = np.asarray(cached.arrays["pitch_midi"], dtype=np.int32)
        supported = active & (pitch >= min_pitch) & (pitch <= max_pitch)
        active_counts[dataset_id] += int(np.sum(supported))
        inactive_counts[dataset_id] += int(np.sum(~active))
        pitch_counts.setdefault(dataset_id, Counter()).update(map(int, pitch[supported]))
    return {
        dataset_id: {
            "files": int(file_counts[dataset_id]),
            "active": int(active_counts[dataset_id]),
            "inactive": int(inactive_counts[dataset_id]),
            "samples": int(active_counts[dataset_id] + inactive_counts[dataset_id]),
            "class_distribution": {
                str(midi): int(pitch_counts[dataset_id].get(midi, 0))
                for midi in range(min_pitch, max_pitch + 1)
            },
        }
        for dataset_id in sorted(file_counts)
    }


def _make_sequence(
    cache: NPZRamCache,
    index: GlobalSampleIndex,
    cfg,
    gain: float,
    shuffle: bool,
    pitch_weights: np.ndarray | None,
    activity_weights: np.ndarray,
    onset_weights: np.ndarray,
) -> V6Sequence:
    return V6Sequence(
        cache,
        index,
        cfg.train.batch_size,
        cfg.dataset.min_pitch,
        gain,
        cfg.dataset.seed,
        shuffle,
        pitch_class_weights=pitch_weights,
        activity_weights=activity_weights,
        onset_targets=cfg.model.onset_auxiliary,
        onset_weights=onset_weights,
        harmonic_targets=cfg.model.harmonic_auxiliary,
        harmonic_count=cfg.model.harmonic_count,
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()

    import tensorflow as tf

    cfg = load_config(args.config)
    if not cfg.model.active_auxiliary:
        raise ValueError("V6.0 requiert model.active_auxiliary=true.")
    if cfg.model.active_loss_weight <= 0.0:
        raise ValueError("active_loss_weight doit etre strictement positif.")
    if cfg.model.onset_auxiliary and cfg.model.onset_loss_weight <= 0.0:
        raise ValueError("onset_loss_weight doit etre strictement positif.")
    tf.keras.utils.set_random_seed(cfg.dataset.seed)

    manifest_items = load_manifest(cfg.dataset.manifest)
    if cfg.dataset.include_datasets:
        requested = set(cfg.dataset.include_datasets)
        available = {item.dataset_id for item in manifest_items}
        unknown = requested - available
        if unknown:
            raise ValueError(f"Datasets absents du manifest: {sorted(unknown)}")
        manifest_items = [
            item for item in manifest_items if item.dataset_id in requested
        ]
    groups = split_manifest(
        manifest_items,
        cfg.dataset.train_players,
        cfg.dataset.validation_players,
        cfg.dataset.test_players,
    )

    print("Chargement cache RAM V6...")
    caches = {
        name: NPZRamCache(items, cfg.cache.validate_schema)
        for name, items in groups.items()
    }
    for cache in caches.values():
        cache.load()
    indices = {
        name: GlobalSampleIndex(
            cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch
        )
        for name, cache in caches.items()
    }

    gain = compute_global_gain(
        caches["train"],
        indices["train"],
        cfg.dataset.normalization_percentile,
        cfg.dataset.normalization_target,
        cfg.dataset.max_gain,
    )
    pitch_weights = (
        compute_pitch_class_weights(
            indices["train"],
            cfg.dataset.min_pitch,
            cfg.dataset.max_pitch,
            cfg.train.max_class_weight,
        )
        if cfg.train.use_class_weights
        else None
    )
    activity_weights = compute_activity_weights(indices["train"])
    onset_weights = (
        compute_onset_weights(indices["train"])
        if cfg.model.onset_auxiliary
        else np.ones(2, dtype=np.float32)
    )
    sequences = {
        "train": _make_sequence(
            caches["train"], indices["train"], cfg, gain, True,
            pitch_weights, activity_weights, onset_weights,
        ),
        "validation": _make_sequence(
            caches["validation"], indices["validation"], cfg, gain, False,
            None, np.ones(2, dtype=np.float32), np.ones(2, dtype=np.float32),
        ),
        "test": _make_sequence(
            caches["test"], indices["test"], cfg, gain, False,
            None, np.ones(2, dtype=np.float32), np.ones(2, dtype=np.float32),
        ),
    }

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = cfg.train.output_root / f"{cfg.train.run_name}_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    runtime = {
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "numpy": np.__version__,
        "git_commit": git_commit(),
        "cache_gib": {name: cache.gib_used for name, cache in caches.items()},
    }
    (run_dir / "config.json").write_text(
        json.dumps(cfg.to_dict(), indent=2), encoding="utf-8"
    )
    (run_dir / "runtime.json").write_text(
        json.dumps(runtime, indent=2), encoding="utf-8"
    )
    (run_dir / "normalization.json").write_text(
        json.dumps({"gain": gain}, indent=2), encoding="utf-8"
    )
    (run_dir / "split_report.json").write_text(
        json.dumps({
            split: [
                {
                    "source_id": item.source_id,
                    "dataset_id": item.dataset_id,
                    "player_id": item.player_id,
                    "group_id": item.group_id,
                    "capture_id": item.capture_id,
                    "npz_path": str(item.npz_path),
                }
                for item in items
            ]
            for split, items in groups.items()
        }, indent=2),
        encoding="utf-8",
    )
    statistics = {
        "files": {name: len(cache) for name, cache in caches.items()},
        "samples": {name: len(index) for name, index in indices.items()},
        "activity_distribution": {
            name: index.activity_distribution() for name, index in indices.items()
        },
        "onset_distribution": {
            name: index.onset_distribution() for name, index in indices.items()
        },
        "class_distribution": {
            name: index.class_distribution() for name, index in indices.items()
        },
        "by_dataset": {
            name: cache_statistics(
                cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch
            )
            for name, cache in caches.items()
        },
        "pitch_class_weights": None if pitch_weights is None else {
            str(midi): float(pitch_weights[midi - cfg.dataset.min_pitch])
            for midi in range(cfg.dataset.min_pitch, cfg.dataset.max_pitch + 1)
        },
        "activity_weights": {
            "inactive": float(activity_weights[0]),
            "active": float(activity_weights[1]),
        },
        "onset_weights": {
            "non_onset": float(onset_weights[0]),
            "onset": float(onset_weights[1]),
        },
    }
    (run_dir / "dataset_statistics.json").write_text(
        json.dumps(statistics, indent=2), encoding="utf-8"
    )

    model = build_pitch_model(
        cfg.model,
        cfg.dataset.max_pitch - cfg.dataset.min_pitch + 1,
        input_samples=cfg.dataset.max_window,
    )
    losses: dict[str, object] = {
        "pitch": tf.keras.losses.SparseCategoricalCrossentropy(),
        "active": tf.keras.losses.BinaryCrossentropy(),
    }
    loss_weights = {
        "pitch": 1.0,
        "active": cfg.model.active_loss_weight,
    }
    if cfg.model.onset_auxiliary:
        losses["onset"] = tf.keras.losses.BinaryCrossentropy()
        loss_weights["onset"] = cfg.model.onset_loss_weight
    if cfg.model.harmonic_auxiliary:
        losses.update({
            "harmonic_amplitude": MaskedHarmonicAmplitudeLoss(
                cfg.model.harmonic_count
            ),
            "harmonic_offset_cents": AmplitudeWeightedHarmonicOffsetLoss(
                cfg.model.harmonic_count,
                cfg.model.harmonic_offset_scale_cents,
            ),
        })
        loss_weights.update({
            "harmonic_amplitude": cfg.model.harmonic_amplitude_loss_weight,
            "harmonic_offset_cents": cfg.model.harmonic_offset_loss_weight,
        })

    model.compile(
        optimizer=tf.keras.optimizers.Adam(cfg.train.learning_rate),
        loss=losses,
        loss_weights=loss_weights,
        metrics={
            "active": [
                tf.keras.metrics.BinaryAccuracy(name="accuracy"),
                tf.keras.metrics.AUC(curve="PR", name="auc_pr"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
            ],
            **({
                "onset": [
                    tf.keras.metrics.BinaryAccuracy(name="accuracy"),
                    tf.keras.metrics.AUC(curve="PR", name="auc_pr"),
                    tf.keras.metrics.Precision(name="precision"),
                    tf.keras.metrics.Recall(name="recall"),
                ],
            } if cfg.model.onset_auxiliary else {}),
        },
        weighted_metrics={
            "pitch": [
                tf.keras.metrics.SparseCategoricalAccuracy(name="top1"),
                tf.keras.metrics.SparseTopKCategoricalAccuracy(k=3, name="top3"),
            ],
        },
    )

    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "best.keras"),
            monitor="val_active_auc_pr",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "best_pitch.keras"),
            monitor="val_pitch_top1",
            mode="max",
            save_best_only=True,
            verbose=0,
        ),
        *([
            tf.keras.callbacks.ModelCheckpoint(
                str(run_dir / "best_onset.keras"),
                monitor="val_onset_auc_pr",
                mode="max",
                save_best_only=True,
                verbose=0,
            ),
        ] if cfg.model.onset_auxiliary else []),
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "last.keras"),
            save_best_only=False,
            verbose=0,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_active_auc_pr",
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
        sequences["train"],
        validation_data=sequences["validation"],
        epochs=cfg.train.epochs,
        callbacks=callbacks,
        workers=cfg.train.workers,
        use_multiprocessing=False,
        max_queue_size=2,
    )
    model.save(run_dir / "final.keras")

    evaluation_model = tf.keras.models.load_model(run_dir / "best.keras", compile=False)
    validation_raw = evaluation_model.predict(
        sequences["validation"],
        workers=cfg.train.workers,
        use_multiprocessing=False,
        max_queue_size=2,
        verbose=1,
    )
    validation_predictions = predictions_by_name(evaluation_model, validation_raw)
    validation_targets = concatenate_targets(sequences["validation"])
    active_threshold, threshold_metrics = select_f1_threshold(
        validation_predictions["active"], validation_targets["active"]
    )
    onset_threshold = None
    if cfg.model.onset_auxiliary:
        onset_threshold, onset_threshold_metrics = select_f1_threshold(
            validation_predictions["onset"], validation_targets["onset"]
        )
        (run_dir / "onset_threshold.json").write_text(
            json.dumps({
                "threshold": onset_threshold,
                "selected_on": "validation",
                "metrics": onset_threshold_metrics,
            }, indent=2),
            encoding="utf-8",
        )
    (run_dir / "active_threshold.json").write_text(
        json.dumps({
            "threshold": active_threshold,
            "selected_on": "validation",
            "metrics": threshold_metrics,
        }, indent=2),
        encoding="utf-8",
    )

    test_raw = evaluation_model.predict(
        sequences["test"],
        workers=cfg.train.workers,
        use_multiprocessing=False,
        max_queue_size=2,
        verbose=1,
    )
    test_predictions = predictions_by_name(evaluation_model, test_raw)
    test_targets = concatenate_targets(sequences["test"])
    test_metadata = sequences["test"].metadata()
    metrics = generate_v6_reports(
        run_dir,
        test_predictions,
        test_targets,
        test_metadata,
        cfg.dataset.min_pitch,
        active_threshold,
        evaluated_checkpoint="best.keras",
        harmonic_count=(
            cfg.model.harmonic_count if cfg.model.harmonic_auxiliary else None
        ),
        onset_threshold=onset_threshold,
    )
    if cfg.evaluation.save_predictions:
        np.savez_compressed(
            run_dir / "reports" / "predictions.npz",
            **{f"prediction_{key}": value for key, value in test_predictions.items()},
            **{f"target_{key}": value for key, value in test_targets.items()},
            **{f"metadata_{key}": value for key, value in test_metadata.items()},
        )

    print("")
    print("V6.0 complete")
    print(f"  run             : {run_dir}")
    print(f"  active threshold: {active_threshold:.6f}")
    print(f"  active F1       : {metrics['active']['f1']:.3%}")
    print(
        "  false positive : "
        f"{metrics['active']['false_positive_rate']:.3%}"
    )
    print(
        "  pitch top1     : "
        f"{metrics['pitch_on_true_active']['top1']:.3%}"
    )
    if metrics.get("onset") is not None:
        print(f"  onset F1        : {metrics['onset']['f1']:.3%}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
