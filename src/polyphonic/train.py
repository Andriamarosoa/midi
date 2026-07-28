"""Train the causal polyphonic Guitar MIDI model."""

from __future__ import annotations

import argparse
import inspect
import json
import platform
from datetime import datetime
from pathlib import Path

import numpy as np
import tensorflow as tf
import yaml

from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    build_dataset_frame_pools,
    build_frame_pools,
    class_counts,
    dataset_balanced_class_counts,
    dataset_balanced_validation_refs,
    load_manifest,
    natural_validation_refs,
    sampler_effective_class_counts,
)
from src.polyphonic.keras_compat import load_polyphonic_checkpoint
from src.polyphonic.model import (
    ClassWeightedBinaryCrossentropy,
    MicroF1,
    PolyphonicHarmonicOffsetLoss,
    PolyphonicMaskedHarmonicAmplitudeLoss,
    build_polyphonic_model,
    transfer_compatible_weights,
)
from src.v5.train import git_commit


def _fit_queue_options(fit, workers: int) -> dict[str, object]:
    """Return only queue options supported by the installed Keras version."""
    supported = inspect.signature(fit).parameters
    candidates: dict[str, object] = {
        "workers": int(workers),
        "use_multiprocessing": False,
        "max_queue_size": 2,
    }
    return {
        name: value for name, value in candidates.items()
        if name in supported
    }


def _weights(
    positives: np.ndarray,
    total: int,
    maximum: float,
    exponent: float = 1.0,
) -> np.ndarray:
    if not 0.0 < exponent <= 1.0:
        raise ValueError("class-weight exponent must be in ]0, 1].")
    negatives = total - positives
    raw = np.divide(
        negatives,
        np.maximum(positives, 1),
        dtype=np.float64,
    )
    # A square-root exponent is a controlled way to retain rare-class
    # ordering without letting category oversampling and inverse-frequency
    # weighting multiply into an extreme positive bias.
    raw = np.power(np.maximum(raw, 1.0), exponent)
    return np.asarray(np.clip(raw, 1.0, maximum), dtype=np.float32)


def _json(path: Path, value: object) -> None:
    path.write_text(json.dumps(value, indent=2), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run one tiny epoch on a few recordings to validate the pipeline.",
    )
    parser.add_argument(
        "--initial-checkpoint", type=Path,
        help="Override initialization.mono_checkpoint (for controlled fine-tuning).",
    )
    parser.add_argument(
        "--resume-run", type=Path,
        help="Resume an interrupted run from last.keras and append its history.",
    )
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    seed = int(config["dataset"].get("seed", 42))
    tf.keras.utils.set_random_seed(seed)

    items = load_manifest(Path(config["dataset"]["manifest"]))
    train_items = [item for item in items if item.split == "train"]
    validation_items = [item for item in items if item.split == "validation"]
    if args.smoke_test:
        datasets = sorted({item.dataset_id for item in items})
        train_items = [
            item for dataset in datasets
            for item in [
                row for row in train_items if row.dataset_id == dataset
            ][:2]
        ]
        validation_items = [
            item for dataset in datasets
            for item in [
                row for row in validation_items if row.dataset_id == dataset
            ][:1]
        ]

    train_corpus = PolyphonicCorpus(train_items)
    validation_corpus = PolyphonicCorpus(validation_items)
    if (
        train_corpus.midi_min != validation_corpus.midi_min
        or train_corpus.midi_max != validation_corpus.midi_max
    ):
        raise ValueError("Train/validation pitch contracts differ.")

    training = config["train"]
    dataset_fractions = training.get("dataset_fractions")
    if dataset_fractions:
        dataset_pools = build_dataset_frame_pools(train_corpus)
        train_pools = None
    else:
        dataset_pools = None
        train_pools = build_frame_pools(train_corpus)
    examples_per_epoch = int(training["examples_per_epoch"])
    validation_examples = int(training["validation_examples"])
    epochs = int(training["epochs"])
    if args.smoke_test:
        examples_per_epoch = 256
        validation_examples = 128
        epochs = 1

    validation_dataset_fractions = training.get("validation_dataset_fractions")
    validation_refs = (
        dataset_balanced_validation_refs(
            validation_corpus, validation_examples,
            validation_dataset_fractions, seed + 1,
        )
        if validation_dataset_fractions
        else natural_validation_refs(
            validation_corpus, validation_examples, seed + 1
        )
    )
    sampling_fractions = training["sampling_fractions"]
    if dataset_fractions:
        natural_frame_positive, natural_frames = dataset_balanced_class_counts(
            train_corpus, "active_bits", dataset_fractions
        )
        natural_onset_positive, _ = dataset_balanced_class_counts(
            train_corpus, "onset_bits", dataset_fractions
        )
        effective_dataset_pools = dataset_pools
        effective_dataset_fractions = dataset_fractions
    else:
        natural_frame_positive, natural_frames = class_counts(
            train_corpus, "active_bits"
        )
        natural_onset_positive, _ = class_counts(train_corpus, "onset_bits")
        assert train_pools is not None
        effective_dataset_pools = {"__all__": train_pools}
        effective_dataset_fractions = {"__all__": 1.0}

    effective_frame_positive, effective_frames = (
        sampler_effective_class_counts(
            train_corpus,
            "active_bits",
            effective_dataset_pools,
            effective_dataset_fractions,
            sampling_fractions,
        )
    )
    effective_onset_positive, _ = sampler_effective_class_counts(
        train_corpus,
        "onset_bits",
        effective_dataset_pools,
        effective_dataset_fractions,
        sampling_fractions,
    )
    class_weight_basis = str(
        training.get("class_weight_basis", "natural")
    ).lower()
    if class_weight_basis == "natural":
        frame_positive = natural_frame_positive
        onset_positive = natural_onset_positive
        class_weight_frames = natural_frames
    elif class_weight_basis == "sampled":
        frame_positive = effective_frame_positive
        onset_positive = effective_onset_positive
        class_weight_frames = effective_frames
    else:
        raise ValueError(
            "train.class_weight_basis must be 'natural' or 'sampled'."
        )
    class_weight_exponent = float(
        training.get("class_weight_exponent", 1.0)
    )
    frame_weights = _weights(
        frame_positive,
        class_weight_frames,
        float(training["maximum_frame_weight"]),
        class_weight_exponent,
    )
    onset_weights = _weights(
        onset_positive,
        class_weight_frames,
        float(training["maximum_onset_weight"]),
        class_weight_exponent,
    )

    if args.resume_run:
        run_dir = args.resume_run.resolve()
        if not run_dir.is_dir() or not (run_dir / "last.keras").is_file():
            raise FileNotFoundError(
                f"Resume run must contain last.keras: {run_dir}"
            )
        history_path = run_dir / "history.csv"
        initial_epoch = max(
            sum(1 for _ in history_path.open(encoding="utf-8")) - 1, 0
        ) if history_path.is_file() else 0
        if initial_epoch >= epochs:
            raise ValueError(
                f"Run already has {initial_epoch} epochs (target={epochs})."
            )
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "_smoke" if args.smoke_test else ""
        run_dir = Path(training["output_root"]) / (
            f"{training['run_name']}{suffix}_{timestamp}"
        )
        run_dir.mkdir(parents=True, exist_ok=False)
        initial_epoch = 0
        _json(run_dir / "config.json", config)
        _json(run_dir / "runtime.json", {
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
            "git_commit": git_commit(),
            "smoke_test": args.smoke_test,
        })
    statistics = {
        "recordings": {
            "train": len(train_items), "validation": len(validation_items),
        },
        "training_pool_sizes": (
            train_pools.sizes if train_pools is not None else {
                dataset: pools.sizes for dataset, pools in dataset_pools.items()
            }
        ),
        "examples_per_epoch": examples_per_epoch,
        "validation_examples": len(validation_refs),
        "class_weight_basis": class_weight_basis,
        "class_weight_exponent": class_weight_exponent,
        "class_weight_total_frames": class_weight_frames,
        "natural_train_frames": natural_frames,
        "effective_sampled_train_frames": effective_frames,
        "class_weight_dataset_fractions": dataset_fractions,
        "class_weight_sampling_fractions": sampling_fractions,
        "natural_frame_positive_counts": natural_frame_positive.tolist(),
        "natural_onset_positive_counts": natural_onset_positive.tolist(),
        "natural_frame_positive_rates": (
            natural_frame_positive / float(natural_frames)
        ).tolist(),
        "natural_onset_positive_rates": (
            natural_onset_positive / float(natural_frames)
        ).tolist(),
        "effective_frame_positive_counts": (
            effective_frame_positive.tolist()
        ),
        "effective_onset_positive_counts": (
            effective_onset_positive.tolist()
        ),
        "effective_frame_positive_rates": (
            effective_frame_positive / float(effective_frames)
        ).tolist(),
        "effective_onset_positive_rates": (
            effective_onset_positive / float(effective_frames)
        ).tolist(),
        "frame_positive_counts": frame_positive.tolist(),
        "onset_positive_counts": onset_positive.tolist(),
        "frame_positive_weights": frame_weights.tolist(),
        "onset_positive_weights": onset_weights.tolist(),
    }
    if not args.resume_run:
        _json(run_dir / "dataset_statistics.json", statistics)

    sequence_options = {
        "batch_size": int(training["batch_size"]),
        "input_samples": int(config["dataset"]["input_samples"]),
        "normalization_gain": float(config["dataset"]["normalization_gain"]),
    }
    train_sequence = PolyphonicSequence(
        train_corpus,
        **sequence_options,
        seed=seed,
        pools=train_pools,
        dataset_pools=dataset_pools,
        dataset_fractions=dataset_fractions,
        examples_per_epoch=examples_per_epoch,
        sampling_fractions=sampling_fractions,
        augmentation_gain_db=float(training.get("augmentation_gain_db", 0.0)),
        shuffle=True,
    )
    validation_sequence = PolyphonicSequence(
        validation_corpus,
        **sequence_options,
        seed=seed + 1,
        refs=validation_refs,
        augmentation_gain_db=0.0,
        shuffle=False,
    )

    model_config = config["model"]
    if args.resume_run:
        model = load_polyphonic_checkpoint(run_dir / "last.keras")
        transfer = {
            "source": str(run_dir / "last.keras"),
            "resumed_at_epoch": initial_epoch,
        }
    else:
        model = build_polyphonic_model(
            pitch_classes=train_corpus.pitch_classes,
            input_samples=int(config["dataset"]["input_samples"]),
            channels=int(model_config["channels"]),
            tcn_blocks=int(model_config["tcn_blocks"]),
            dropout=float(model_config["dropout"]),
            dense_units=int(model_config["dense_units"]),
            harmonic_count=train_corpus.harmonic_count,
            harmonic_offset_scale_cents=float(
                model_config["harmonic_offset_scale_cents"]
            ),
            normal_window_samples=int(
                model_config.get(
                    "normal_window_samples",
                    config["dataset"]["input_samples"],
                )
            ),
            compressed_bass_branch=bool(
                model_config.get("compressed_bass_branch", False)
            ),
            bass_channels=int(model_config.get("bass_channels", 8)),
            bass_dense_units=int(model_config.get("bass_dense_units", 32)),
            bass_pitch_classes=int(
                model_config.get(
                    "bass_pitch_classes",
                    train_corpus.pitch_classes,
                )
            ),
        )
        initialization = config.get("initialization", {})
        source_model = (
            args.initial_checkpoint or initialization.get("mono_checkpoint")
        )
        if source_model:
            transfer = transfer_compatible_weights(model, Path(source_model))
        else:
            transfer = {"source": None, "transferred": [], "skipped": []}
    _json(run_dir / "weight_transfer.json", transfer)

    model.compile(
        optimizer=tf.keras.optimizers.Adam(float(training["learning_rate"])),
        loss={
            "frame": ClassWeightedBinaryCrossentropy(frame_weights.tolist()),
            "onset": ClassWeightedBinaryCrossentropy(onset_weights.tolist()),
            "harmonic_amplitude": PolyphonicMaskedHarmonicAmplitudeLoss(
                train_corpus.harmonic_count
            ),
            "harmonic_offset_cents": PolyphonicHarmonicOffsetLoss(
                train_corpus.harmonic_count,
                float(model_config["harmonic_offset_scale_cents"]),
            ),
        },
        loss_weights={
            "frame": 1.0,
            "onset": float(model_config["onset_loss_weight"]),
            "harmonic_amplitude": float(
                model_config["harmonic_amplitude_loss_weight"]
            ),
            "harmonic_offset_cents": float(
                model_config["harmonic_offset_loss_weight"]
            ),
        },
        metrics={
            "frame": [
                MicroF1(name="micro_f1"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
            ],
            "onset": [
                MicroF1(name="micro_f1"),
                tf.keras.metrics.Precision(name="precision"),
                tf.keras.metrics.Recall(name="recall"),
            ],
        },
    )
    epoch_checkpoints = run_dir / "epochs"
    epoch_checkpoints.mkdir(exist_ok=True)
    callbacks = [
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "best.keras"),
            monitor="val_frame_micro_f1",
            mode="max",
            save_best_only=True,
            verbose=1,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "last.keras"),
            save_best_only=False,
            verbose=0,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(epoch_checkpoints / "epoch-{epoch:02d}.keras"),
            save_best_only=False,
            verbose=0,
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_frame_micro_f1",
            mode="max",
            patience=int(training["early_stopping_patience"]),
            restore_best_weights=True,
            verbose=1,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_loss",
            mode="min",
            factor=0.5,
            patience=int(training["reduce_lr_patience"]),
            min_lr=float(training["minimum_learning_rate"]),
            verbose=1,
        ),
        tf.keras.callbacks.CSVLogger(
            str(run_dir / "history.csv"), append=bool(args.resume_run)
        ),
        tf.keras.callbacks.TerminateOnNaN(),
    ]

    print(f"Run directory: {run_dir}")
    print("Preloading compact audio cache...")
    train_corpus.preload_audio()
    validation_corpus.preload_audio()
    _json(run_dir / "audio_cache.json", {
        "train_gib": train_corpus.audio_gib,
        "validation_gib": validation_corpus.audio_gib,
    })
    model.summary()
    try:
        model.fit(
            train_sequence,
            validation_data=validation_sequence,
            initial_epoch=initial_epoch,
            epochs=epochs,
            callbacks=callbacks,
            **_fit_queue_options(
                model.fit, int(training.get("workers", 1))
            ),
        )
        model.save(run_dir / "final.keras")
    finally:
        train_corpus.close()
        validation_corpus.close()
    (Path(training["output_root"]) / "latest_run.txt").write_text(
        str(run_dir.resolve()), encoding="utf-8"
    )
    print(f"Polyphonic training complete: {run_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
