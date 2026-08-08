"""Bounded train-only gate for the neural independent-note head.

This module deliberately has no validation phase.  It reads manifest metadata,
retains only ``split=train`` items, partitions them by a corpus-aware leakage
key into fit/dev/calibration cohorts, freezes the historical model, and trains only
layers whose name starts with ``independent_note``.  A frozen threshold is
published only when the independent-note recall and harmonic-removal gates are
met on the train calibration cohort.
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import math
import os
import platform
import re
import subprocess
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

import numpy as np

_FORCE_CPU = os.environ.get("MIDI_FORCE_CPU") == "1"
if _FORCE_CPU:
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import tensorflow as tf
import yaml

if _FORCE_CPU:
    tf.config.set_visible_devices([], "GPU")

from src.polyphonic.data import (
    ManifestItem,
    PolyphonicCorpus,
    PolyphonicSequence,
    dataset_balanced_validation_refs,
    load_independent_note_fundamental_offsets,
    load_manifest,
)
from src.polyphonic.decoder_candidate_provenance import (
    canonical_digest,
    canonical_identifier,
    dataset_family as _dataset_family,
    leakage_group_key,
    partition_train_groups,
    train_items_only,
)
from src.polyphonic.keras_compat import load_polyphonic_checkpoint
from src.polyphonic.model import (
    PolyphonicMaskedIndependentNoteLoss,
    build_polyphonic_model,
    transfer_compatible_weights,
)


SCHEMA_VERSION = 1
EXPECTED_MANIFEST_SHA256 = (
    "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
)
GLOBAL_RECALL_MINIMUM = 0.98
CORPUS_RECALL_MINIMUM = 0.95
HARMONIC_REMOVAL_MINIMUM = 0.05
CALIBRATION_POSITIVES_PER_CORPUS_MINIMUM = 50
CALIBRATION_HARMONIC_NEGATIVES_PER_SUPERVISED_CORPUS_MINIMUM = 20
MAXIMUM_EPOCHS = 12
MAXIMUM_EXAMPLES_PER_PARTITION = 65_536
MAXIMUM_RUNTIME_MINUTES = 60.0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_snapshot(root: Path) -> dict[str, object]:
    if (root / ".git").exists():
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
        status = subprocess.check_output(
            ["git", "status", "--short", "--untracked-files=all"],
            cwd=root,
            text=True,
        ).splitlines()
        if not re.fullmatch(r"[0-9a-f]{40}", head):
            raise RuntimeError("The source worktree has no exact Git commit.")
        if status:
            raise RuntimeError(
                "The train-only gate requires a clean committed worktree: "
                + "; ".join(status)
            )
        return {
            "root": str(root),
            "commit": head,
            "dirty": False,
            "archive_snapshot": False,
        }

    provenance = root / ".source.env"
    if not provenance.is_file():
        raise RuntimeError(
            "Source has neither Git metadata nor the required .source.env."
        )
    lines = provenance.read_text(encoding="utf-8").splitlines()
    if len(lines) != 2 or any("=" not in line for line in lines):
        raise RuntimeError("Malformed .source.env provenance file.")
    pairs = [line.split("=", 1) for line in lines]
    values = {key: value for key, value in pairs}
    if len(values) != 2 or set(values) != {"commit", "archive_sha256"}:
        raise RuntimeError("Malformed .source.env provenance keys.")
    commit = values["commit"]
    archive_sha256 = values["archive_sha256"]
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise RuntimeError("Malformed .source.env commit.")
    if not re.fullmatch(r"[0-9a-f]{64}", archive_sha256):
        raise RuntimeError("Malformed .source.env archive SHA-256.")
    return {
        "root": str(root),
        "commit": commit,
        "dirty": False,
        "archive_snapshot": True,
        "archive_sha256": archive_sha256,
        "provenance_file": str(provenance),
    }


def freeze_independent_note_only(model: tf.keras.Model) -> dict[str, object]:
    for layer in model.layers:
        layer.trainable = layer.name.startswith("independent_note")
    trainable = [layer.name for layer in model.layers if layer.trainable]
    weighted_trainable = [
        layer.name for layer in model.layers if layer.trainable and layer.weights
    ]
    if not weighted_trainable:
        raise RuntimeError("The model has no trainable independent-note weights.")
    if any(not name.startswith("independent_note") for name in trainable):
        raise RuntimeError("Fail closed: a backbone layer remained trainable.")
    frozen_weighted = [
        layer.name for layer in model.layers if not layer.trainable and layer.weights
    ]
    if not frozen_weighted:
        raise RuntimeError("Fail closed: no pretrained backbone was frozen.")
    return {
        "trainable_layers": trainable,
        "trainable_weight_layers": weighted_trainable,
        "frozen_weight_layers": frozen_weighted,
    }


def _weighted_ratio(mask: np.ndarray, denominator_mask: np.ndarray, weights: np.ndarray) -> float:
    denominator = float(np.sum(weights[denominator_mask]))
    if denominator <= 0.0:
        return float("nan")
    return float(np.sum(weights[mask & denominator_mask]) / denominator)


def select_least_aggressive_threshold(
    probability: np.ndarray,
    target: np.ndarray,
    weight: np.ndarray,
    corpus: Sequence[str],
) -> dict[str, object]:
    """Apply the immutable train-only threshold gate on calibration data."""

    probability = np.asarray(probability, dtype=np.float64).reshape(-1)
    target = np.asarray(target, dtype=np.float64).reshape(-1)
    weight = np.asarray(weight, dtype=np.float64).reshape(-1)
    corpus_array = np.asarray(tuple(str(value) for value in corpus), dtype=object)
    if not (
        probability.shape == target.shape == weight.shape == corpus_array.shape
    ):
        raise ValueError("Calibration arrays must have identical flat shapes.")
    if not (
        np.all(np.isfinite(probability))
        and np.all(np.isfinite(target))
        and np.all(np.isfinite(weight))
    ):
        raise ValueError("Calibration arrays must be finite.")
    if np.any((probability < 0.0) | (probability > 1.0)):
        raise ValueError("Probabilities must be in [0, 1].")
    if np.any(weight < 0.0):
        raise ValueError("Reliability weights cannot be negative.")
    supervised = weight > 0.0
    if np.any((target[supervised] != 0.0) & (target[supervised] != 1.0)):
        raise ValueError("Supervised targets must be binary.")
    positive = supervised & (target > 0.5)
    negative = supervised & ~positive
    if not np.any(positive) or not np.any(negative):
        raise RuntimeError("Both supervised classes are required for calibration.")
    corpora = sorted(set(corpus_array[supervised].tolist()))
    if not corpora:
        raise RuntimeError("Calibration has no supervised corpus.")
    for name in corpora:
        if not np.any(positive & (corpus_array == name)):
            raise RuntimeError(
                f"Corpus {name!r} has no independent-note calibration target."
            )

    supervised_weight = weight[supervised]
    prevalence = float(
        np.sum(weight[supervised] * target[supervised])
        / np.sum(supervised_weight)
    )
    brier = float(
        np.sum(weight[supervised] * np.square(probability[supervised] - target[supervised]))
        / np.sum(supervised_weight)
    )
    constant_brier = float(
        np.sum(weight[supervised] * np.square(prevalence - target[supervised]))
        / np.sum(supervised_weight)
    )
    brier_passed = brier < constant_brier

    rows: list[dict[str, object]] = []
    for raw_threshold in np.arange(0.01, 1.0, 0.01):
        threshold = float(round(float(raw_threshold), 2))
        kept = probability >= threshold
        independent_recall = _weighted_ratio(kept, positive, weight)
        harmonic_removed = _weighted_ratio(~kept, negative, weight)
        per_corpus = {
            name: _weighted_ratio(
                kept,
                positive & (corpus_array == name),
                weight,
            )
            for name in corpora
        }
        eligible = bool(
            brier_passed
            and independent_recall >= GLOBAL_RECALL_MINIMUM
            and all(
                value >= CORPUS_RECALL_MINIMUM
                for value in per_corpus.values()
            )
            and harmonic_removed >= HARMONIC_REMOVAL_MINIMUM
        )
        rows.append({
            "threshold": threshold,
            "independent_recall": independent_recall,
            "independent_recall_by_corpus": per_corpus,
            "harmonic_only_removed_recall": harmonic_removed,
            "eligible": eligible,
        })
    selected = next((row for row in rows if row["eligible"]), None)
    return {
        "scope": "supervised_candidate_learnability_not_decoder_noteon_delta",
        "requires_paired_decoder_validation": True,
        "selected_threshold": (
            None if selected is None else float(selected["threshold"])
        ),
        "brier": brier,
        "constant_brier": constant_brier,
        "brier_better_than_constant": brier_passed,
        "weighted_prevalence": prevalence,
        "supervised": int(np.count_nonzero(supervised)),
        "independent_note": int(np.count_nonzero(positive)),
        "harmonic_only": int(np.count_nonzero(negative)),
        "grid": rows,
    }


class _IndependentTargetSequence(tf.keras.utils.Sequence):
    """Expose only the independent-note target of a PolyphonicSequence."""

    def __init__(self, sequence: PolyphonicSequence) -> None:
        try:
            super().__init__(workers=1, use_multiprocessing=False, max_queue_size=1)
        except TypeError:
            super().__init__()
        self.sequence = sequence

    def __len__(self) -> int:
        return len(self.sequence)

    def __getitem__(self, index: int):
        inputs, targets = self.sequence[index]
        if "independent_note" not in targets:
            raise RuntimeError(
                "PolyphonicSequence did not emit the independent_note target."
            )
        return inputs, targets["independent_note"]

    def on_epoch_end(self) -> None:
        self.sequence.on_epoch_end()


class _RuntimeBudget(tf.keras.callbacks.Callback):
    def __init__(self, seconds: float) -> None:
        super().__init__()
        self.seconds = float(seconds)
        self.started = 0.0
        self.exhausted = False

    def on_train_begin(self, logs=None) -> None:
        self.started = time.monotonic()

    def on_train_batch_end(self, batch, logs=None) -> None:
        if time.monotonic() - self.started >= self.seconds:
            self.exhausted = True
            self.model.stop_training = True


def _equal_dataset_fractions(items: Sequence[ManifestItem]) -> dict[str, float]:
    names = sorted({str(item.dataset_id) for item in items})
    if not names:
        raise RuntimeError("A partition contains no corpus.")
    return {name: 1.0 / len(names) for name in names}


def _make_sequence(
    items: Sequence[ManifestItem],
    config: Mapping[str, Any],
    *,
    examples: int,
    seed: int,
    shuffle: bool,
    fundamental_offsets: Mapping[tuple[str, str], np.ndarray],
    required_fundamental_offset_datasets: Sequence[str],
    corpus_registry: list[PolyphonicCorpus] | None = None,
) -> PolyphonicSequence:
    corpus = PolyphonicCorpus(
        items,
        fundamental_offsets=fundamental_offsets,
        required_fundamental_offset_datasets=required_fundamental_offset_datasets,
    )
    if corpus_registry is not None:
        corpus_registry.append(corpus)
    refs = dataset_balanced_validation_refs(
        corpus,
        maximum_examples=int(examples),
        dataset_fractions=_equal_dataset_fractions(items),
        seed=int(seed),
    )
    return PolyphonicSequence(
        corpus,
        batch_size=int(config["train"]["batch_size"]),
        input_samples=int(config["dataset"]["input_samples"]),
        normalization_gain=float(config["dataset"]["normalization_gain"]),
        seed=int(seed),
        refs=refs,
        augmentation_gain_db=(
            float(config["train"].get("augmentation_gain_db", 0.0))
            if shuffle
            else 0.0
        ),
        harmonic_presence_target=bool(
            config["model"].get("harmonic_presence_head", False)
        ),
        independent_note_target=True,
        shuffle=bool(shuffle),
        workers=1,
        max_queue_size=1,
    )


def _target_rows(sequence: PolyphonicSequence) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    targets: list[np.ndarray] = []
    weights: list[np.ndarray] = []
    corpora: list[np.ndarray] = []
    pitch_classes = int(sequence.corpus.pitch_classes)
    for batch_index in range(len(sequence)):
        _, batch_targets = sequence[batch_index]
        packed = np.asarray(batch_targets["independent_note"], dtype=np.float32)
        if packed.ndim != 2 or packed.shape[1] != 2 * pitch_classes:
            raise RuntimeError("Unexpected packed independent-note target shape.")
        size = len(packed)
        start = batch_index * int(sequence.batch_size)
        selected = sequence.order[start : start + size]
        row_corpora = np.asarray([
            str(sequence.corpus.items[int(recording_index)].dataset_id)
            for recording_index in selected[:, 0]
        ], dtype=object)
        targets.append(packed[:, :pitch_classes].reshape(-1))
        weights.append(packed[:, pitch_classes:].reshape(-1))
        corpora.append(np.repeat(row_corpora, pitch_classes))
    return (
        np.concatenate(targets),
        np.concatenate(weights),
        np.concatenate(corpora),
    )


def _class_report(
    target: np.ndarray,
    weight: np.ndarray,
    corpus: np.ndarray,
    *,
    require_calibration_minimums: bool = False,
) -> dict[str, object]:
    supervised = weight > 0.0
    positive = supervised & (target > 0.5)
    negative = supervised & ~positive
    report = {
        "supervised": int(np.count_nonzero(supervised)),
        "independent_note": int(np.count_nonzero(positive)),
        "harmonic_only": int(np.count_nonzero(negative)),
        "reliability_sum": float(np.sum(weight[supervised])),
        "by_corpus": {},
    }
    for name in sorted(set(corpus.tolist())):
        selected = corpus == name
        report["by_corpus"][name] = {
            "supervised": int(np.count_nonzero(supervised & selected)),
            "independent_note": int(np.count_nonzero(positive & selected)),
            "harmonic_only": int(np.count_nonzero(negative & selected)),
        }
    if not np.any(positive) or not np.any(negative):
        raise RuntimeError("A train-only partition is missing a supervised class.")
    missing = [
        name
        for name, values in report["by_corpus"].items()
        if int(values["independent_note"]) == 0
    ]
    if missing:
        raise RuntimeError(
            f"Train-only partition has no positive target for {missing}."
        )
    if require_calibration_minimums:
        sparse_positive = {
            name: int(values["independent_note"])
            for name, values in report["by_corpus"].items()
            if int(values["independent_note"])
            < CALIBRATION_POSITIVES_PER_CORPUS_MINIMUM
        }
        if sparse_positive:
            raise RuntimeError(
                "Fail closed: calibration needs at least "
                f"{CALIBRATION_POSITIVES_PER_CORPUS_MINIMUM} positives per corpus; "
                f"observed {sparse_positive}."
            )
        sparse_harmonic = {
            name: int(values["harmonic_only"])
            for name, values in report["by_corpus"].items()
            if _dataset_family(name) == "guitarset"
            and int(values["harmonic_only"])
            < CALIBRATION_HARMONIC_NEGATIVES_PER_SUPERVISED_CORPUS_MINIMUM
        }
        if sparse_harmonic:
            raise RuntimeError(
                "Fail closed: harmonic-supervised calibration corpora need at least "
                f"{CALIBRATION_HARMONIC_NEGATIVES_PER_SUPERVISED_CORPUS_MINIMUM} "
                f"negatives; observed {sparse_harmonic}."
            )
    return report


def _predict_flat(
    head_model: tf.keras.Model,
    sequence: PolyphonicSequence,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    target, weight, corpus = _target_rows(sequence)
    predictions: list[np.ndarray] = []
    for batch_index in range(len(sequence)):
        inputs, _ = sequence[batch_index]
        value = head_model.predict_on_batch(inputs)
        if isinstance(value, Mapping):
            value = value["independent_note"]
        predictions.append(np.asarray(value, dtype=np.float32).reshape(-1))
    probability = np.concatenate(predictions)
    if probability.shape != target.shape:
        raise RuntimeError("Independent-note prediction/target shapes differ.")
    return probability, target, weight, corpus


def _model_kwargs(config: Mapping[str, Any], corpus: PolyphonicCorpus) -> dict[str, object]:
    model = config["model"]
    return {
        "pitch_classes": corpus.pitch_classes,
        "input_samples": int(config["dataset"]["input_samples"]),
        "channels": int(model["channels"]),
        "tcn_blocks": int(model["tcn_blocks"]),
        "dropout": float(model["dropout"]),
        "dense_units": int(model["dense_units"]),
        "harmonic_count": corpus.harmonic_count,
        "harmonic_offset_scale_cents": float(model["harmonic_offset_scale_cents"]),
        "normal_window_samples": int(model.get(
            "normal_window_samples", config["dataset"]["input_samples"]
        )),
        "compressed_bass_branch": bool(model.get("compressed_bass_branch", False)),
        "bass_channels": int(model.get("bass_channels", 8)),
        "bass_dense_units": int(model.get("bass_dense_units", 32)),
        "bass_pitch_classes": int(model.get("bass_pitch_classes", corpus.pitch_classes)),
        "harmonic_presence_head": bool(model.get("harmonic_presence_head", False)),
        "independent_note_head": True,
        "independent_note_units": int(model.get("independent_note_units", 32)),
    }


def _loss(config: Mapping[str, Any], pitch_classes: int):
    parameters = inspect.signature(
        PolyphonicMaskedIndependentNoteLoss.__init__
    ).parameters
    kwargs: dict[str, object] = {"pitch_classes": int(pitch_classes)}
    if "positive_weight" in parameters:
        kwargs["positive_weight"] = float(
            config["model"].get("independent_note_positive_weight", 1.0)
        )
    if "negative_weight" in parameters:
        kwargs["negative_weight"] = float(
            config["model"].get("independent_note_negative_weight", 1.0)
        )
    return PolyphonicMaskedIndependentNoteLoss(**kwargs)


def _fit_queue_options(fit) -> dict[str, object]:
    """Use one queue worker only when the installed Keras accepts it."""

    supported = inspect.signature(fit).parameters
    candidates: dict[str, object] = {
        "workers": 1,
        "use_multiprocessing": False,
        "max_queue_size": 1,
    }
    return {
        name: value for name, value in candidates.items()
        if name in supported
    }


def _write_json(path: Path, value: Mapping[str, object]) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def _run_with_corpus_registry(
    args: argparse.Namespace,
    corpus_registry: list[PolyphonicCorpus],
) -> dict[str, object]:
    root = Path(__file__).resolve().parents[2]
    config_path = args.config.resolve(strict=True)
    checkpoint = args.initial_checkpoint.resolve(strict=True)
    output_dir = args.output_dir.resolve()
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Refusing to overwrite non-empty {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, Mapping):
        raise ValueError("The YAML config must contain a mapping.")
    configured_epochs = int(config["train"]["epochs"])
    if int(args.epochs) != configured_epochs:
        raise RuntimeError(
            "The train-only gate requires the exact configured epoch count: "
            f"{args.epochs} != {configured_epochs}."
        )
    source = source_snapshot(root)
    visible_gpus = [
        device.name for device in tf.config.get_visible_devices("GPU")
    ]
    if _FORCE_CPU and visible_gpus:
        raise RuntimeError(
            "Fail closed: MIDI_FORCE_CPU=1 but TensorFlow still exposes a GPU."
        )
    manifest = Path(config["dataset"]["manifest"]).resolve(strict=True)
    manifest_sha = file_sha256(manifest)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("Unexpected train/validation manifest SHA-256.")
    sidecar_value = str(config["dataset"].get("independent_note_fundamental_offsets", ""))
    sidecar_expected_sha = str(
        config["dataset"].get("independent_note_fundamental_offsets_sha256", "")
    )
    if not sidecar_value or len(sidecar_expected_sha) != 64:
        raise RuntimeError("A verified independent-note offset sidecar is required.")
    sidecar = Path(sidecar_value)
    if not sidecar.is_absolute():
        sidecar = root / sidecar
    fundamental_offsets = load_independent_note_fundamental_offsets(
        sidecar,
        expected_sha256=sidecar_expected_sha,
        expected_manifest_sha256=manifest_sha,
    )
    required_offset_datasets = tuple(
        str(value) for value in config["dataset"].get(
            "independent_note_fundamental_offset_required_datasets",
            ["guitarset_poly_mix"],
        )
    )
    expected_checkpoint = str(
        config.get("initialization", {}).get("required_checkpoint_sha256", "")
    )
    if len(expected_checkpoint) != 64:
        raise RuntimeError("A required initial checkpoint SHA-256 is mandatory.")
    checkpoint_sha = file_sha256(checkpoint)
    if checkpoint_sha != expected_checkpoint:
        raise RuntimeError("Initial checkpoint SHA-256 does not match the config.")

    items = load_manifest(manifest)
    train_items = train_items_only(items)
    partitions, partition_report = partition_train_groups(
        train_items, seed=int(config["dataset"]["seed"])
    )
    sequences = {
        "fit": _make_sequence(
            partitions["fit"], config, examples=args.fit_examples,
            seed=int(config["dataset"]["seed"]), shuffle=True,
            fundamental_offsets=fundamental_offsets,
            required_fundamental_offset_datasets=required_offset_datasets,
            corpus_registry=corpus_registry,
        ),
        "dev": _make_sequence(
            partitions["dev"], config, examples=args.dev_examples,
            seed=int(config["dataset"]["seed"]) + 1, shuffle=False,
            fundamental_offsets=fundamental_offsets,
            required_fundamental_offset_datasets=required_offset_datasets,
            corpus_registry=corpus_registry,
        ),
        "calibration": _make_sequence(
            partitions["calibration"], config,
            examples=args.calibration_examples,
            seed=int(config["dataset"]["seed"]) + 2, shuffle=False,
            fundamental_offsets=fundamental_offsets,
            required_fundamental_offset_datasets=required_offset_datasets,
            corpus_registry=corpus_registry,
        ),
    }
    target_cache = {
        name: _target_rows(sequence)
        for name, sequence in sequences.items()
    }
    class_reports = {
        name: _class_report(
            *values,
            require_calibration_minimums=(name == "calibration"),
        )
        for name, values in target_cache.items()
    }

    full_model = build_polyphonic_model(
        **_model_kwargs(config, sequences["fit"].corpus)
    )
    transfer = transfer_compatible_weights(full_model, checkpoint)
    allowed_skipped = {
        layer.name
        for layer in full_model.layers
        if layer.name.startswith("independent_note") and layer.weights
    }
    unexpected_skipped = sorted(set(transfer["skipped"]) - allowed_skipped)
    if unexpected_skipped:
        raise RuntimeError(
            f"Fail closed: pretrained layers were not restored: {unexpected_skipped}"
        )
    frozen = freeze_independent_note_only(full_model)
    head_model = tf.keras.Model(
        full_model.inputs,
        full_model.get_layer("independent_note").output,
        name="independent_note_train_only",
    )
    head_model.compile(
        optimizer=tf.keras.optimizers.Adam(
            float(config["train"]["learning_rate"])
        ),
        loss=_loss(config, sequences["fit"].corpus.pitch_classes),
    )
    budget = _RuntimeBudget(float(args.maximum_runtime_minutes) * 60.0)
    history = head_model.fit(
        _IndependentTargetSequence(sequences["fit"]),
        validation_data=_IndependentTargetSequence(sequences["dev"]),
        epochs=int(args.epochs),
        callbacks=[
            tf.keras.callbacks.EarlyStopping(
                monitor="val_loss",
                mode="min",
                patience=2,
                restore_best_weights=True,
            ),
            budget,
        ],
        verbose=2,
        **_fit_queue_options(head_model.fit),
    )

    model_path = output_dir / "independent_note_head.keras"
    # Native ``.keras`` saving under Keras 3 rejects ``include_optimizer``.
    # The gate reloads only for inference parity, so the default native format
    # is sufficient and stays compatible with both Keras 2 and 3.
    full_model.save(model_path)
    probability, target, weight, corpus = _predict_flat(
        head_model, sequences["calibration"]
    )
    threshold = select_least_aggressive_threshold(
        probability, target, weight, corpus
    )

    reloaded = load_polyphonic_checkpoint(model_path)
    reloaded_head = tf.keras.Model(
        reloaded.inputs, reloaded.get_layer("independent_note").output
    )
    reloaded_probability, _, _, _ = _predict_flat(
        reloaded_head, sequences["calibration"]
    )
    parity_max = float(np.max(np.abs(
        probability.astype(np.float64) - reloaded_probability.astype(np.float64)
    )))
    selected_threshold = threshold["selected_threshold"]
    decision_agreement = (
        None
        if selected_threshold is None
        else float(np.mean(
            (probability >= float(selected_threshold))
            == (reloaded_probability >= float(selected_threshold))
        ))
    )
    parity_passed = parity_max <= 1e-6 and (
        decision_agreement is None or decision_agreement == 1.0
    )
    status = "passed" if (
        not budget.exhausted
        and selected_threshold is not None
        and parity_passed
    ) else "failed_gate"

    payload: dict[str, object] = {
        "schema_version": SCHEMA_VERSION,
        "phase": "train_only",
        "status": status,
        "locked_test_used": False,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "provenance": {
            "source": source,
            "config": str(config_path),
            "config_sha256": file_sha256(config_path),
            "manifest": str(manifest),
            "manifest_sha256": manifest_sha,
            "fundamental_offset_sidecar": str(sidecar),
            "fundamental_offset_sidecar_sha256": sidecar_expected_sha,
            "fundamental_offset_records": len(fundamental_offsets),
            "fundamental_offset_required_datasets": list(required_offset_datasets),
            "manifest_split_counts": dict(sorted(Counter(
                str(item.split) for item in items
            ).items())),
            "loaded_audio_label_split": "train",
            "initial_checkpoint": str(checkpoint),
            "initial_checkpoint_sha256": checkpoint_sha,
            "python": sys.version,
            "platform": platform.platform(),
            "tensorflow": tf.__version__,
            "force_cpu": _FORCE_CPU,
            "visible_tensorflow_gpus": visible_gpus,
            "pid": os.getpid(),
        },
        "contract": {
            "validation_loaded": False,
            "test_loaded": False,
            "backbone_frozen": True,
            "workers": 1,
            "max_queue_size": 1,
            "maximum_runtime_minutes": float(args.maximum_runtime_minutes),
            "automatic_validation": False,
            "automatic_full_train": False,
            "automatic_export": False,
        },
        "partitions": partition_report,
        "examples": {
            "fit": int(args.fit_examples),
            "dev": int(args.dev_examples),
            "calibration": int(args.calibration_examples),
        },
        "class_counts": class_reports,
        "model": {
            "independent_note_units": int(
                config["model"].get("independent_note_units", 32)
            ),
            "transfer": transfer,
            "freeze": frozen,
            "artifact": str(model_path),
            "artifact_sha256": file_sha256(model_path),
        },
        "history": {
            key: [float(value) for value in values]
            for key, values in history.history.items()
        },
        "runtime_budget_exhausted": budget.exhausted,
        "threshold_gate": threshold,
        "parity": {
            "maximum_absolute_error": parity_max,
            "decision_agreement": decision_agreement,
            "passed": parity_passed,
        },
    }
    report_path = output_dir / "independent_note_train_gate.json"
    _write_json(report_path, payload)
    print(json.dumps({
        "phase": "train_only",
        "status": status,
        "report": str(report_path),
        "report_sha256": file_sha256(report_path),
        "model": str(model_path),
        "model_sha256": file_sha256(model_path),
        "selected_threshold": selected_threshold,
        "locked_test_used": False,
    }, indent=2), flush=True)
    return payload


def run(args: argparse.Namespace) -> dict[str, object]:
    corpora: list[PolyphonicCorpus] = []
    try:
        return _run_with_corpus_registry(args, corpora)
    finally:
        closed: set[int] = set()
        for corpus in reversed(corpora):
            identity = id(corpus)
            if identity not in closed:
                corpus.close()
                closed.add(identity)


def _bounded_positive(value: int, name: str) -> int:
    result = int(value)
    if not 1 <= result <= MAXIMUM_EXAMPLES_PER_PARTITION:
        raise argparse.ArgumentTypeError(
            f"{name} must be in 1..{MAXIMUM_EXAMPLES_PER_PARTITION}."
        )
    return result


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--initial-checkpoint", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--fit-examples", type=int, required=True)
    parser.add_argument("--dev-examples", type=int, required=True)
    parser.add_argument("--calibration-examples", type=int, required=True)
    parser.add_argument("--epochs", type=int, required=True)
    parser.add_argument(
        "--maximum-runtime-minutes", type=float, required=True
    )
    args = parser.parse_args()
    for name in ("fit_examples", "dev_examples", "calibration_examples"):
        setattr(args, name, _bounded_positive(getattr(args, name), name))
    if not 1 <= int(args.epochs) <= MAXIMUM_EPOCHS:
        parser.error(f"--epochs must be in 1..{MAXIMUM_EPOCHS}.")
    if not (
        math.isfinite(float(args.maximum_runtime_minutes))
        and 0.0 < float(args.maximum_runtime_minutes) <= MAXIMUM_RUNTIME_MINUTES
    ):
        parser.error(
            f"--maximum-runtime-minutes must be in (0, {MAXIMUM_RUNTIME_MINUTES}]."
        )
    payload = run(args)
    return 0 if payload["status"] == "passed" else 3


if __name__ == "__main__":
    raise SystemExit(main())
