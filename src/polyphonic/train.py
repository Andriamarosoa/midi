"""Train the causal polyphonic Guitar MIDI model."""

from __future__ import annotations

import argparse
import csv
import hashlib
import inspect
import json
import os
import platform
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence

import keras
import numpy as np
import tensorflow as tf
import yaml

from src.polyphonic.data import (
    PlanBatchSlice,
    PolyphonicEpochPlan,
    PolyphonicCorpus,
    PolyphonicSequence,
    build_dataset_frame_pools,
    build_frame_pools,
    class_counts,
    dataset_balanced_class_counts,
    dataset_balanced_validation_refs,
    load_independent_note_fundamental_offsets,
    load_manifest,
    natural_validation_refs,
    sampler_effective_class_counts,
)
from src.polyphonic.model import (
    ClassWeightedBinaryCrossentropy,
    MicroF1,
    PolyphonicHarmonicOffsetLoss,
    PolyphonicMaskedHarmonicAmplitudeLoss,
    PolyphonicMaskedHarmonicPresenceBrier,
    PolyphonicMaskedHarmonicPresenceF1,
    PolyphonicMaskedHarmonicPresenceLoss,
    PolyphonicMaskedHarmonicPresencePrecision,
    PolyphonicMaskedHarmonicPresenceRecall,
    PolyphonicMaskedIndependentNoteBrier,
    PolyphonicMaskedIndependentNoteF1,
    PolyphonicMaskedIndependentNoteLoss,
    PolyphonicMaskedIndependentNotePrecision,
    PolyphonicMaskedIndependentNoteRecall,
    build_polyphonic_model,
    transfer_compatible_weights,
)
from src.polyphonic.recovery import (
    RecoverySignatures,
    RecoverySnapshot,
    atomic_write_json,
    file_sha256,
    load_latest_recovery_checkpoint,
    save_recovery_checkpoint,
)
from src.v5.train import git_commit


def _rss_to_mib(value: float, *, platform_name: str | None = None) -> float:
    """Normalize ``ru_maxrss`` to MiB on Linux and macOS."""
    current_platform = platform_name or sys.platform
    divisor = 1024.0**2 if current_platform == "darwin" else 1024.0
    return float(value) / divisor


def _fit_queue_options(
    fit,
    workers: int,
    max_queue_size: int = 2,
) -> dict[str, object]:
    """Return only queue options supported by the installed Keras version."""
    if int(workers) < 1 or int(max_queue_size) < 1:
        raise ValueError("workers and max_queue_size must be positive.")
    supported = inspect.signature(fit).parameters
    candidates: dict[str, object] = {
        "workers": int(workers),
        "use_multiprocessing": False,
        "max_queue_size": int(max_queue_size),
    }
    return {
        name: value for name, value in candidates.items()
        if name in supported
    }


def _freeze_independent_note_backbone(
    model: tf.keras.Model,
    transfer: Mapping[str, object],
) -> list[str]:
    """Freeze only after every weighted backbone layer was restored."""

    transferred = {str(name) for name in transfer.get("transferred", [])}
    skipped = {str(name) for name in transfer.get("skipped", [])}
    allowed_skipped = {
        layer.name for layer in model.layers
        if layer.name.startswith("independent_note") and layer.weights
    }
    unexpected_skipped = sorted(skipped - allowed_skipped)
    weighted_backbone = {
        layer.name for layer in model.layers
        if not layer.name.startswith("independent_note") and layer.weights
    }
    missing_backbone = sorted(weighted_backbone - transferred)
    if unexpected_skipped or missing_backbone:
        raise RuntimeError(
            "Refusing to freeze an incompletely restored backbone: "
            f"unexpected_skipped={unexpected_skipped}, "
            f"missing_backbone={missing_backbone}."
        )
    for layer in model.layers:
        layer.trainable = layer.name.startswith("independent_note")
    trainable_layers = [
        layer.name for layer in model.layers if layer.trainable
    ]
    if not any(
        layer.trainable and layer.weights for layer in model.layers
    ):
        raise RuntimeError("The independent-note head has no trainable weights.")
    return trainable_layers


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


def _harmonic_supervision_preflight(
    corpus: PolyphonicCorpus,
    *,
    split: str,
    required_datasets: Sequence[str],
    minimum_schema_version: int = 3,
) -> dict[str, object]:
    """Fail closed before a presence-head train can accept stale labels."""

    required = tuple(sorted({str(value) for value in required_datasets}))
    if not required:
        raise ValueError(
            "harmonic_supervision_required_datasets must not be empty."
        )
    if int(minimum_schema_version) < 3:
        raise ValueError("Harmonic supervision schema must be at least 3.")
    if len(corpus.items) != len(corpus.labels):
        raise ValueError(f"{split}: corpus item/label counts differ.")

    by_corpus: dict[str, dict[str, float | int]] = {}

    def counters(dataset_id: str) -> dict[str, float | int]:
        return by_corpus.setdefault(
            dataset_id,
            {
                "recordings": 0,
                "schema_recordings": 0,
                "notes": 0,
                "supervised_partials": 0,
                "positive_partials": 0,
                "negative_partials": 0,
                "weighted_supervision": 0.0,
                "weighted_positive": 0.0,
                "weighted_negative": 0.0,
            },
        )

    contract_names = {
        "harmonic_supervision_schema_version",
        "harmonic_presence_floor_db",
        "harmonic_reliability_formula",
        "note_harmonic_supervised",
        "note_harmonic_reliability",
        "note_harmonic_relative_db",
        "note_harmonic_frames_measured",
    }
    for item, cached in zip(corpus.items, corpus.labels):
        dataset_id = str(item.dataset_id)
        row = counters(dataset_id)
        row["recordings"] = int(row["recordings"]) + 1
        arrays = cached.arrays
        available = contract_names & set(arrays)
        if dataset_id in required and available != contract_names:
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: harmonic "
                "supervision schema 3 arrays are required."
            )
        if available and available != contract_names:
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: incomplete "
                "harmonic supervision contract."
            )
        if not available:
            continue

        schema = int(
            np.asarray(
                arrays["harmonic_supervision_schema_version"]
            ).reshape(())
        )
        if schema < int(minimum_schema_version):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: harmonic schema "
                f"{schema} is older than {minimum_schema_version}."
            )
        presence_floor_db = float(
            np.asarray(arrays["harmonic_presence_floor_db"]).reshape(())
        )
        reliability_formula = str(
            np.asarray(arrays["harmonic_reliability_formula"]).reshape(())
        )
        if not np.isfinite(presence_floor_db) or presence_floor_db >= 0.0:
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: invalid harmonic "
                "presence floor."
            )
        if reliability_formula != "sqrt(n/(n+1))":
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: unsupported "
                "harmonic reliability formula."
            )
        supervised = np.asarray(
            arrays["note_harmonic_supervised"], np.float32
        )
        reliability = np.asarray(
            arrays["note_harmonic_reliability"], np.float32
        )
        present = np.asarray(
            arrays["note_harmonic_present"], np.float32
        )
        amplitude = np.asarray(
            arrays["note_harmonic_amplitude"], np.float32
        )
        offset = np.asarray(
            arrays["note_harmonic_offset_cents"], np.float32
        )
        relative_db = np.asarray(
            arrays["note_harmonic_relative_db"], np.float32
        )
        raw_frames = np.asarray(
            arrays["note_harmonic_frames_measured"]
        )
        if (
            supervised.ndim != 2
            or supervised.shape != reliability.shape
            or supervised.shape != present.shape
            or supervised.shape != amplitude.shape
            or supervised.shape != offset.shape
            or supervised.shape != relative_db.shape
            or supervised.shape != raw_frames.shape
        ):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: inconsistent "
                "harmonic supervision shapes."
            )
        if (
            np.any((supervised != 0.0) & (supervised != 1.0))
            or np.any((present != 0.0) & (present != 1.0))
        ):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: harmonic masks "
                "must be binary."
            )
        if (
            np.any(~np.isfinite(reliability))
            or np.any(reliability < 0.0)
            or np.any(reliability > 1.0)
            or np.any(~np.isfinite(amplitude))
            or np.any(amplitude < 0.0)
            or np.any(amplitude > 1.0)
            or np.any(~np.isfinite(offset))
            or raw_frames.dtype.kind not in {"i", "u"}
            or np.any(raw_frames < 0)
        ):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: invalid harmonic "
                "target values."
            )
        if np.any(present > supervised):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: presence without "
                "supervision."
            )
        supervised_mask = supervised > 0.5
        if (
            np.any(reliability[~supervised_mask] != 0.0)
            or np.any(reliability[supervised_mask] <= 0.0)
            or np.any(raw_frames[~supervised_mask] != 0)
            or np.any(raw_frames[supervised_mask] <= 0)
            or np.any(~np.isfinite(relative_db[supervised_mask]))
        ):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: reliability and "
                "supervision disagree."
            )
        if np.any(supervised_mask):
            expected_reliability = np.sqrt(
                raw_frames[supervised_mask].astype(np.float64)
                / (
                    raw_frames[supervised_mask].astype(np.float64)
                    + 1.0
                )
            )
            if not np.allclose(
                reliability[supervised_mask],
                expected_reliability,
                rtol=2e-3,
                atol=2e-3,
            ):
                raise ValueError(
                    f"{split}/{dataset_id}/{item.source_id}: harmonic "
                    "reliability formula mismatch."
                )
            expected_presence = (
                relative_db[supervised_mask] >= presence_floor_db
            ).astype(np.float32)
            if not np.array_equal(
                present[supervised_mask], expected_presence
            ):
                raise ValueError(
                    f"{split}/{dataset_id}/{item.source_id}: harmonic "
                    "presence floor mismatch."
                )
        expected_amplitude = np.zeros_like(amplitude)
        for note_index in range(supervised.shape[0]):
            note_mask = supervised_mask[note_index]
            if not np.any(note_mask):
                continue
            relative = relative_db[note_index, note_mask]
            expected_amplitude[note_index, note_mask] = np.power(
                np.float32(10.0),
                (relative - np.max(relative)) / np.float32(20.0),
            )
        if not np.allclose(
            amplitude, expected_amplitude, rtol=2e-3, atol=2e-3
        ):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: relative harmonic "
                "strength mismatch."
            )
        note_valid = np.asarray(
            arrays["note_harmonic_valid"], np.float32
        ).reshape(-1)
        expected_valid = np.any(supervised_mask, axis=1).astype(np.float32)
        if (
            len(note_valid) != supervised.shape[0]
            or np.any((note_valid > 0.5) != (expected_valid > 0.5))
        ):
            raise ValueError(
                f"{split}/{dataset_id}/{item.source_id}: note-level "
                "harmonic validity disagrees with supervision."
            )

        positive = supervised_mask & (present > 0.5)
        negative = supervised_mask & ~positive
        weighted = supervised * reliability
        row["schema_recordings"] = int(row["schema_recordings"]) + 1
        row["notes"] = int(row["notes"]) + int(supervised.shape[0])
        row["supervised_partials"] = (
            int(row["supervised_partials"]) + int(np.sum(supervised_mask))
        )
        row["positive_partials"] = (
            int(row["positive_partials"]) + int(np.sum(positive))
        )
        row["negative_partials"] = (
            int(row["negative_partials"]) + int(np.sum(negative))
        )
        row["weighted_supervision"] = (
            float(row["weighted_supervision"]) + float(np.sum(weighted))
        )
        row["weighted_positive"] = (
            float(row["weighted_positive"])
            + float(np.sum(weighted * present))
        )
        row["weighted_negative"] = (
            float(row["weighted_negative"])
            + float(np.sum(weighted * (1.0 - present)))
        )

    for dataset_id in required:
        row = by_corpus.get(dataset_id)
        if row is None or int(row["recordings"]) == 0:
            raise ValueError(
                f"{split}: required harmonic dataset {dataset_id!r} is absent."
            )
        if int(row["schema_recordings"]) != int(row["recordings"]):
            raise ValueError(
                f"{split}/{dataset_id}: not every recording uses schema 3."
            )
        if (
            float(row["weighted_positive"]) <= 0.0
            or float(row["weighted_negative"]) <= 0.0
        ):
            raise ValueError(
                f"{split}/{dataset_id}: positive and negative weighted "
                "harmonic supervision are both required."
            )

    totals = {
        name: (
            float(sum(float(row[name]) for row in by_corpus.values()))
            if name.startswith("weighted_")
            else int(sum(int(row[name]) for row in by_corpus.values()))
        )
        for name in (
            "recordings",
            "schema_recordings",
            "notes",
            "supervised_partials",
            "positive_partials",
            "negative_partials",
            "weighted_supervision",
            "weighted_positive",
            "weighted_negative",
        )
    }
    if (
        float(totals["weighted_positive"]) <= 0.0
        or float(totals["weighted_negative"]) <= 0.0
    ):
        raise ValueError(
            f"{split}: weighted positive and negative supervision are required."
        )
    return {
        "split": str(split),
        "minimum_schema_version": int(minimum_schema_version),
        "required_datasets": list(required),
        "totals": totals,
        "by_corpus": {
            name: by_corpus[name] for name in sorted(by_corpus)
        },
    }


def _write_model_overview(
    model: tf.keras.Model,
    run_dir: Path,
) -> dict[str, object]:
    """Persist a compact model description without rendering a summary table."""
    overview: dict[str, object] = {
        "name": str(model.name),
        "parameter_count": int(model.count_params()),
        "layer_count": len(model.layers),
        "input_count": len(model.inputs),
        "output_names": [str(name) for name in model.output_names],
    }
    _json(run_dir / "model_overview.json", overview)
    print(
        "MODEL_OVERVIEW "
        + json.dumps(overview, separators=(",", ":"), sort_keys=True),
        flush=True,
    )
    return overview


class EpochProgressLogger(tf.keras.callbacks.Callback):
    """Persist and flush one machine-readable status line per epoch."""

    def __init__(
        self,
        path: str | Path,
        *,
        total_epochs: int,
        initial_epoch: int = 0,
    ) -> None:
        super().__init__()
        self.path = Path(path)
        self.total_epochs = int(total_epochs)
        self.initial_epoch = int(initial_epoch)
        self.current_epoch = int(initial_epoch)
        self.last_metrics: dict[str, float] = {}

    @staticmethod
    def _metrics(logs: dict[str, object] | None) -> dict[str, float]:
        return {
            str(name): float(value)
            for name, value in (logs or {}).items()
            if value is not None
        }

    def _write(self, status: str, **values: object) -> None:
        report = {
            "schema_version": 1,
            "status": status,
            "epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            **values,
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
        print(
            "EPOCH_PROGRESS " + json.dumps(report, separators=(",", ":")),
            flush=True,
        )

    def on_train_begin(self, logs=None) -> None:
        self.current_epoch = self.initial_epoch
        self._write("starting")

    def on_epoch_begin(self, epoch: int, logs=None) -> None:
        self.current_epoch = int(epoch) + 1
        self._write("running")

    def on_epoch_end(self, epoch: int, logs=None) -> None:
        self.current_epoch = int(epoch) + 1
        self.last_metrics = self._metrics(logs)
        self._write("epoch_completed", metrics=self.last_metrics)

    def on_train_end(self, logs=None) -> None:
        self._write("training_finished", metrics=self.last_metrics)


class BatchProgressLogger(tf.keras.callbacks.Callback):
    """Persist batch throughput and GPU telemetry during long cloud epochs."""

    def __init__(
        self,
        path: str | Path,
        *,
        total_batches: int,
        total_epochs: int,
        batch_size: int,
        every_batches: int = 25,
        maximum_runtime_minutes: float | None = None,
    ) -> None:
        super().__init__()
        self.path = Path(path)
        self.total_batches = int(total_batches)
        self.total_epochs = int(total_epochs)
        self.batch_size = int(batch_size)
        self.every_batches = int(every_batches)
        self.maximum_runtime_seconds = (
            None
            if maximum_runtime_minutes is None
            else float(maximum_runtime_minutes) * 60.0
        )
        if (
            self.total_batches < 1
            or self.total_epochs < 1
            or self.batch_size < 1
            or self.every_batches < 1
        ):
            raise ValueError("Invalid batch progress dimensions.")
        if (
            self.maximum_runtime_seconds is not None
            and self.maximum_runtime_seconds <= 0.0
        ):
            raise ValueError("Maximum runtime must be positive.")
        self.started = 0.0
        self.epoch_started = 0.0
        self.batch_started = 0.0
        self.current_epoch = 0
        self.completed_batches = 0
        self.completed_batches_in_epoch = 0
        self.time_budget_reached = False

    @staticmethod
    def _metrics(logs: dict[str, object] | None) -> dict[str, float]:
        return {
            str(name): float(value)
            for name, value in (logs or {}).items()
            if value is not None
        }

    @staticmethod
    def _gpu_snapshot() -> list[dict[str, object]]:
        command = [
            "nvidia-smi",
            "--query-gpu=index,name,utilization.gpu,memory.used,memory.total",
            "--format=csv,noheader,nounits",
        ]
        try:
            result = subprocess.run(
                command,
                check=True,
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            # Apple Metal has no nvidia-smi equivalent. Preserve visibility of
            # the TensorFlow device while marking utilization as unavailable.
            return [
                {
                    "index": index,
                    "name": device.name,
                    "backend": "tensorflow",
                    "utilization_percent": None,
                    "memory_used_mib": None,
                    "memory_total_mib": None,
                }
                for index, device in enumerate(
                    tf.config.list_physical_devices("GPU")
                )
            ]
        devices: list[dict[str, object]] = []
        for line in result.stdout.splitlines():
            fields = [value.strip() for value in line.split(",")]
            if len(fields) != 5:
                continue
            try:
                devices.append({
                    "index": int(fields[0]),
                    "name": fields[1],
                    "utilization_percent": float(fields[2]),
                    "memory_used_mib": float(fields[3]),
                    "memory_total_mib": float(fields[4]),
                })
            except ValueError:
                continue
        return devices

    @staticmethod
    def _maximum_rss_mib() -> float | None:
        if os.name == "nt":
            return None
        try:
            import resource

            # Linux reports KiB while macOS reports bytes.
            value = float(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            return _rss_to_mib(value)
        except (ImportError, OSError, ValueError):
            return None

    def _write(
        self,
        status: str,
        *,
        logs: dict[str, object] | None = None,
        batch_seconds: float | None = None,
    ) -> None:
        now = time.monotonic()
        overall_elapsed = max(now - self.started, 0.0)
        epoch_elapsed = max(now - self.epoch_started, 0.0)
        batches = max(self.completed_batches_in_epoch, 1)
        examples = self.completed_batches_in_epoch * self.batch_size
        epoch_fraction = (
            self.completed_batches_in_epoch / float(self.total_batches)
        )
        overall_fraction = (
            (
                max(self.current_epoch - 1, 0)
                + min(max(epoch_fraction, 0.0), 1.0)
            )
            / float(self.total_epochs)
        )
        report = {
            "schema_version": 1,
            "status": status,
            "epoch": self.current_epoch,
            "total_epochs": self.total_epochs,
            "batch": self.completed_batches_in_epoch,
            "total_batches": self.total_batches,
            "completed_batches": self.completed_batches,
            "batch_size": self.batch_size,
            "elapsed_seconds": overall_elapsed,
            "epoch_elapsed_seconds": epoch_elapsed,
            "batch_seconds": batch_seconds,
            "examples_per_second": (
                examples / epoch_elapsed if epoch_elapsed > 0.0 else None
            ),
            "projected_epoch_seconds": (
                epoch_elapsed / epoch_fraction
                if epoch_fraction > 0.0 else None
            ),
            "projected_training_seconds": (
                overall_elapsed / overall_fraction
                if overall_fraction > 0.0 else None
            ),
            "maximum_runtime_seconds": self.maximum_runtime_seconds,
            "maximum_rss_mib": self._maximum_rss_mib(),
            "gpu": self._gpu_snapshot(),
            "metrics": self._metrics(logs),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        }
        temporary = self.path.with_suffix(self.path.suffix + ".tmp")
        temporary.write_text(
            json.dumps(report, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(self.path)
        print(
            "BATCH_PROGRESS " + json.dumps(report, separators=(",", ":")),
            flush=True,
        )

    def on_train_begin(self, logs=None) -> None:
        self.started = time.monotonic()
        self.epoch_started = self.started
        self._write("starting", logs=logs)

    def on_epoch_begin(self, epoch: int, logs=None) -> None:
        self.current_epoch = int(epoch) + 1
        self.completed_batches_in_epoch = 0
        self.epoch_started = time.monotonic()
        self._write("epoch_starting", logs=logs)

    def on_train_batch_begin(self, batch: int, logs=None) -> None:
        self.batch_started = time.monotonic()

    def on_train_batch_end(self, batch: int, logs=None) -> None:
        self.completed_batches += 1
        self.completed_batches_in_epoch = int(batch) + 1
        batch_seconds = time.monotonic() - self.batch_started
        should_write = (
            self.completed_batches_in_epoch == 1
            or self.completed_batches_in_epoch % self.every_batches == 0
            or self.completed_batches_in_epoch >= self.total_batches
        )
        if should_write:
            self._write(
                "running",
                logs=logs,
                batch_seconds=batch_seconds,
            )
        if (
            self.maximum_runtime_seconds is not None
            and time.monotonic() - self.started
            >= self.maximum_runtime_seconds
        ):
            self.time_budget_reached = True
            self._write(
                "time_budget_reached",
                logs=logs,
                batch_seconds=batch_seconds,
            )
            self.model.stop_training = True

    def on_train_end(self, logs=None) -> None:
        self._write(
            (
                "paused_for_time_budget"
                if self.time_budget_reached
                else "training_finished"
            ),
            logs=logs,
        )


def _canonical_json_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _atomic_model_save(model: Any, destination: str | Path) -> None:
    """Save a native Keras archive without exposing a partial destination."""

    path = Path(destination)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(
        f".{path.stem}.{os.getpid()}.{os.urandom(8).hex()}.keras"
    )
    try:
        model.save(temporary)
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _atomic_copy(source: str | Path, destination: str | Path) -> None:
    source_path = Path(source)
    destination_path = Path(destination)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination_path.with_name(
        f".{destination_path.name}.{os.getpid()}.{os.urandom(8).hex()}.tmp"
    )
    try:
        shutil.copyfile(source_path, temporary)
        with temporary.open("r+b") as handle:
            os.fsync(handle.fileno())
        os.replace(temporary, destination_path)
    finally:
        temporary.unlink(missing_ok=True)


def _optimizer_iterations(model: Any) -> int:
    optimizer = getattr(model, "optimizer", None)
    if optimizer is None:
        raise ValueError("Recoverable training requires a compiled model.")
    return int(optimizer.iterations.numpy())


def _optimizer_learning_rate(model: Any) -> float:
    optimizer = getattr(model, "optimizer", None)
    if optimizer is None:
        raise ValueError("Recoverable training requires a compiled model.")
    value = optimizer.learning_rate
    if callable(value):
        value = value(optimizer.iterations)
    try:
        value = value.numpy()
    except AttributeError:
        value = tf.keras.backend.get_value(value)
    result = float(value)
    if not np.isfinite(result):
        raise FloatingPointError("Optimizer learning rate is not finite.")
    return result


def _assign_optimizer_learning_rate(model: Any, value: float) -> None:
    optimizer = getattr(model, "optimizer", None)
    if optimizer is None:
        raise ValueError("Recoverable training requires a compiled model.")
    target = float(value)
    if not np.isfinite(target) or target <= 0.0:
        raise ValueError("Optimizer learning rate must be finite and positive.")
    learning_rate = optimizer.learning_rate
    if hasattr(learning_rate, "assign"):
        learning_rate.assign(target)
    else:
        optimizer.learning_rate = target


def _assert_model_finite(model: Any) -> None:
    """Refuse to serialize a model or optimizer containing NaN/Inf."""

    variables = list(model.weights)
    optimizer = getattr(model, "optimizer", None)
    if optimizer is None:
        raise ValueError("Recoverable training requires a compiled model.")
    optimizer_variables = getattr(optimizer, "variables", ())
    if callable(optimizer_variables):
        optimizer_variables = optimizer_variables()
    variables.extend(list(optimizer_variables))
    for variable in variables:
        values = np.asarray(variable.numpy())
        if not np.all(np.isfinite(values)):
            raise FloatingPointError(
                f"Non-finite value detected in {variable.name}; "
                "the recovery slot was not updated."
            )


def _finite_metrics(
    logs: Mapping[str, object], *, context: str
) -> dict[str, float]:
    normalized: dict[str, float] = {}
    for name, raw_value in logs.items():
        if raw_value is None:
            continue
        value = float(raw_value)
        if not np.isfinite(value):
            raise FloatingPointError(
                f"Non-finite {context} metric {name}={value}; "
                "the recovery slot was not updated."
            )
        canonical_name = str(name)
        # Keras 2 can add the output prefix a second time after restoring a
        # compiled multi-output model (for example frame_frame_micro_f1).
        # Keep the public history/monitor contract stable across recovery.
        for output_prefix in ("frame_", "onset_"):
            doubled = output_prefix + output_prefix
            while canonical_name.startswith(doubled):
                canonical_name = canonical_name[len(output_prefix):]
        previous = normalized.get(canonical_name)
        if previous is not None and not np.isclose(previous, value):
            raise ValueError(
                f"Conflicting {context} metric {canonical_name}."
            )
        normalized[canonical_name] = value
    if not normalized:
        raise ValueError(f"No {context} metrics were produced.")
    return normalized


@dataclass
class MetricAccumulator:
    """Serializable weighted aggregate of completed chunks in one epoch."""

    weight: int
    weighted_sums: dict[str, float]

    @classmethod
    def empty(cls) -> "MetricAccumulator":
        return cls(weight=0, weighted_sums={})

    @classmethod
    def from_dict(cls, value: Mapping[str, object]) -> "MetricAccumulator":
        weight = int(value.get("weight", 0))
        if weight < 0:
            raise ValueError("Metric accumulator weight must be non-negative.")
        raw_sums = value.get("weighted_sums", {})
        if not isinstance(raw_sums, Mapping):
            raise ValueError("Metric accumulator sums must be a mapping.")
        sums = {
            str(name): float(raw)
            for name, raw in raw_sums.items()
        }
        if not all(np.isfinite(value) for value in sums.values()):
            raise ValueError("Metric accumulator contains non-finite values.")
        return cls(weight=weight, weighted_sums=sums)

    def add(self, logs: Mapping[str, object], weight: int) -> None:
        chunk_weight = int(weight)
        if chunk_weight < 1:
            raise ValueError("Completed chunk weight must be positive.")
        metrics = _finite_metrics(logs, context="training")
        for name, value in metrics.items():
            self.weighted_sums[name] = (
                self.weighted_sums.get(name, 0.0)
                + value * chunk_weight
            )
        self.weight += chunk_weight

    def metrics(self) -> dict[str, float]:
        if self.weight < 1:
            raise ValueError("A completed epoch has no training metrics.")
        return {
            name: value / float(self.weight)
            for name, value in self.weighted_sums.items()
        }

    def as_dict(self) -> dict[str, object]:
        return {
            "weight": self.weight,
            "weighted_sums": dict(self.weighted_sums),
        }


@dataclass(frozen=True)
class EpochPolicyDecision:
    improved: bool
    should_stop: bool
    learning_rate_before: float
    learning_rate_after: float

    def as_dict(self) -> dict[str, object]:
        return {
            "improved": self.improved,
            "should_stop": self.should_stop,
            "learning_rate_before": self.learning_rate_before,
            "learning_rate_after": self.learning_rate_after,
        }


@dataclass
class SerializableTrainingPolicy:
    """Epoch-boundary checkpoint, early-stop, and LR plateau policy."""

    early_stopping_patience: int
    reduce_lr_patience: int
    minimum_learning_rate: float
    reduce_lr_factor: float = 0.5
    early_min_delta: float = 0.0
    reduce_min_delta: float = 1e-4
    early_monitor_metric: str = "val_frame_micro_f1"
    early_monitor_mode: str = "max"
    best_frame_micro_f1: float | None = None
    best_frame_epoch: int | None = None
    early_stopping_wait: int = 0
    best_validation_loss: float | None = None
    reduce_lr_wait: int = 0
    completed_epochs: int = 0
    stopped_epoch: int | None = None

    def __post_init__(self) -> None:
        if self.early_stopping_patience < 0:
            raise ValueError("Early-stopping patience must be non-negative.")
        if self.reduce_lr_patience < 0:
            raise ValueError("Reduce-LR patience must be non-negative.")
        if not 0.0 < self.reduce_lr_factor < 1.0:
            raise ValueError("Reduce-LR factor must be in ]0, 1[.")
        if self.minimum_learning_rate <= 0.0:
            raise ValueError("Minimum learning rate must be positive.")
        if not str(self.early_monitor_metric).strip():
            raise ValueError("Early-stopping monitor metric cannot be empty.")
        if self.early_monitor_mode not in {"min", "max"}:
            raise ValueError("Early-stopping monitor mode must be min or max.")

    @classmethod
    def from_dict(
        cls, value: Mapping[str, object]
    ) -> "SerializableTrainingPolicy":
        optional_float = lambda name: (
            None
            if value.get(name) is None
            else float(value[name])
        )
        optional_int = lambda name: (
            None
            if value.get(name) is None
            else int(value[name])
        )
        return cls(
            early_stopping_patience=int(
                value["early_stopping_patience"]
            ),
            reduce_lr_patience=int(value["reduce_lr_patience"]),
            minimum_learning_rate=float(value["minimum_learning_rate"]),
            reduce_lr_factor=float(value.get("reduce_lr_factor", 0.5)),
            early_min_delta=float(value.get("early_min_delta", 0.0)),
            reduce_min_delta=float(value.get("reduce_min_delta", 1e-4)),
            early_monitor_metric=str(
                value.get("early_monitor_metric", "val_frame_micro_f1")
            ),
            early_monitor_mode=str(
                value.get("early_monitor_mode", "max")
            ),
            best_frame_micro_f1=optional_float(
                "best_frame_micro_f1"
            ),
            best_frame_epoch=optional_int("best_frame_epoch"),
            early_stopping_wait=int(
                value.get("early_stopping_wait", 0)
            ),
            best_validation_loss=optional_float(
                "best_validation_loss"
            ),
            reduce_lr_wait=int(value.get("reduce_lr_wait", 0)),
            completed_epochs=int(value.get("completed_epochs", 0)),
            stopped_epoch=optional_int("stopped_epoch"),
        )

    def as_dict(self) -> dict[str, object]:
        return {
            "early_stopping_patience": self.early_stopping_patience,
            "reduce_lr_patience": self.reduce_lr_patience,
            "minimum_learning_rate": self.minimum_learning_rate,
            "reduce_lr_factor": self.reduce_lr_factor,
            "early_min_delta": self.early_min_delta,
            "reduce_min_delta": self.reduce_min_delta,
            "early_monitor_metric": self.early_monitor_metric,
            "early_monitor_mode": self.early_monitor_mode,
            "best_frame_micro_f1": self.best_frame_micro_f1,
            "best_frame_epoch": self.best_frame_epoch,
            "early_stopping_wait": self.early_stopping_wait,
            "best_validation_loss": self.best_validation_loss,
            "reduce_lr_wait": self.reduce_lr_wait,
            "completed_epochs": self.completed_epochs,
            "stopped_epoch": self.stopped_epoch,
        }

    def advance(
        self,
        epoch: int,
        metrics: Mapping[str, float],
        learning_rate: float,
    ) -> EpochPolicyDecision:
        monitored_value = float(metrics[self.early_monitor_metric])
        validation_loss = float(metrics["val_loss"])
        if self.early_monitor_mode == "max":
            improved = (
                self.best_frame_micro_f1 is None
                or monitored_value
                > self.best_frame_micro_f1 + self.early_min_delta
            )
        else:
            improved = (
                self.best_frame_micro_f1 is None
                or monitored_value
                < self.best_frame_micro_f1 - self.early_min_delta
            )
        if improved:
            self.best_frame_micro_f1 = monitored_value
            self.best_frame_epoch = int(epoch)
            self.early_stopping_wait = 0
        else:
            self.early_stopping_wait += 1

        loss_improved = (
            self.best_validation_loss is None
            or validation_loss
            < self.best_validation_loss - self.reduce_min_delta
        )
        learning_rate_after = float(learning_rate)
        if loss_improved:
            self.best_validation_loss = validation_loss
            self.reduce_lr_wait = 0
        else:
            self.reduce_lr_wait += 1
            if self.reduce_lr_wait >= self.reduce_lr_patience:
                learning_rate_after = max(
                    learning_rate_after * self.reduce_lr_factor,
                    self.minimum_learning_rate,
                )
                self.reduce_lr_wait = 0

        self.completed_epochs = int(epoch) + 1
        should_stop = (
            not improved
            and self.early_stopping_wait
            >= self.early_stopping_patience
        )
        if should_stop:
            self.stopped_epoch = int(epoch) + 1
        return EpochPolicyDecision(
            improved=improved,
            should_stop=should_stop,
            learning_rate_before=float(learning_rate),
            learning_rate_after=learning_rate_after,
        )


def _initial_callback_state(
    policy: SerializableTrainingPolicy,
) -> dict[str, object]:
    return {
        "schema_version": 1,
        "policy": policy.as_dict(),
        "history_rows": [],
        "metric_accumulator": MetricAccumulator.empty().as_dict(),
    }


def _validate_callback_state(
    value: Mapping[str, object],
) -> dict[str, object]:
    if int(value.get("schema_version", -1)) != 1:
        raise ValueError("Unsupported recoverable training state.")
    policy_value = value.get("policy")
    history_rows = value.get("history_rows")
    accumulator_value = value.get("metric_accumulator")
    if not isinstance(policy_value, Mapping):
        raise ValueError("Recovery policy state is missing.")
    if not isinstance(history_rows, list):
        raise ValueError("Recovery history state is missing.")
    if not isinstance(accumulator_value, Mapping):
        raise ValueError("Recovery metric accumulator is missing.")
    policy = SerializableTrainingPolicy.from_dict(policy_value)
    accumulator = MetricAccumulator.from_dict(accumulator_value)
    normalized_rows: list[dict[str, float | int]] = []
    seen_epochs: set[int] = set()
    for raw_row in history_rows:
        if not isinstance(raw_row, Mapping):
            raise ValueError("Recovery history row must be a mapping.")
        epoch = int(raw_row["epoch"])
        if epoch in seen_epochs:
            raise ValueError("Recovery history contains duplicate epochs.")
        seen_epochs.add(epoch)
        row: dict[str, float | int] = {"epoch": epoch}
        for name, raw in raw_row.items():
            if name == "epoch":
                continue
            number = float(raw)
            if not np.isfinite(number):
                raise ValueError("Recovery history is not finite.")
            row[str(name)] = number
        normalized_rows.append(row)
    normalized_rows.sort(key=lambda row: int(row["epoch"]))
    if len(normalized_rows) != policy.completed_epochs:
        raise ValueError(
            "Recovery history and policy epoch counters disagree."
        )
    return {
        "schema_version": 1,
        "policy": policy.as_dict(),
        "history_rows": normalized_rows,
        "metric_accumulator": accumulator.as_dict(),
    }


def _write_history_csv(
    path: str | Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    destination = Path(path)
    columns = sorted({
        str(name)
        for row in rows
        for name in row
        if name != "epoch"
    })
    fieldnames = ["epoch", *columns]
    temporary = destination.with_suffix(destination.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in sorted(rows, key=lambda value: int(value["epoch"])):
            writer.writerow({name: row.get(name, "") for name in fieldnames})
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, destination)


def _write_epoch_progress(
    path: str | Path,
    *,
    status: str,
    epoch: int,
    total_epochs: int,
    metrics: Mapping[str, object] | None = None,
) -> None:
    report: dict[str, object] = {
        "schema_version": 2,
        "status": status,
        "epoch": int(epoch),
        "total_epochs": int(total_epochs),
        "updated_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    if metrics is not None:
        report["metrics"] = {
            str(name): float(value) for name, value in metrics.items()
        }
    atomic_write_json(path, report)
    print(
        "EPOCH_PROGRESS " + json.dumps(report, separators=(",", ":")),
        flush=True,
    )


def _persist_or_load_epoch_plans(
    path: str | Path,
    sequence: PolyphonicSequence,
    epochs: int,
) -> tuple[list[PolyphonicEpochPlan], str]:
    """Create every immutable epoch plan before the first training batch."""

    destination = Path(path)
    if not destination.exists():
        payload: dict[str, np.ndarray] = {
            "schema_version": np.asarray([1], dtype=np.int32),
            "epoch_count": np.asarray([int(epochs)], dtype=np.int32),
        }
        for epoch in range(int(epochs)):
            plan = sequence.plan_for_epoch(epoch)
            for name, values in plan.export().items():
                payload[f"epoch_{epoch:04d}__{name}"] = np.asarray(values)
        temporary = destination.with_name(
            f".{destination.name}.{os.getpid()}.{os.urandom(8).hex()}.npz"
        )
        try:
            np.savez_compressed(temporary, **payload)
            with temporary.open("r+b") as handle:
                os.fsync(handle.fileno())
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)

    plans: list[PolyphonicEpochPlan] = []
    with np.load(destination, allow_pickle=False) as archive:
        schema = int(np.asarray(archive["schema_version"]).reshape(-1)[0])
        epoch_count = int(
            np.asarray(archive["epoch_count"]).reshape(-1)[0]
        )
        if schema != 1 or epoch_count != int(epochs):
            raise ValueError("Epoch-plan manifest contract mismatch.")
        for epoch in range(epoch_count):
            prefix = f"epoch_{epoch:04d}__"
            exported = {
                name[len(prefix):]: np.asarray(archive[name]).copy()
                for name in archive.files
                if name.startswith(prefix)
            }
            plan = PolyphonicEpochPlan.from_export(exported)
            expected = sequence.plan_for_epoch(epoch)
            if plan.epoch != epoch or plan.sha256 != expected.sha256:
                raise ValueError(
                    f"Persisted epoch plan {epoch} is incompatible."
                )
            plans.append(plan)
    digest = file_sha256(destination)
    atomic_write_json(
        destination.with_suffix(destination.suffix + ".json"),
        {
            "schema_version": 1,
            "epochs": int(epochs),
            "sha256": digest,
            "locked_test_used": False,
        },
    )
    return plans, digest


def _load_epoch_plans_archive(
    path: str | Path,
) -> list[PolyphonicEpochPlan]:
    """Load an immutable plan archive without regenerating its sequence."""

    source = Path(path)
    plans: list[PolyphonicEpochPlan] = []
    with np.load(source, allow_pickle=False) as archive:
        schema = int(np.asarray(archive["schema_version"]).reshape(-1)[0])
        epoch_count = int(
            np.asarray(archive["epoch_count"]).reshape(-1)[0]
        )
        if schema != 1 or epoch_count < 1:
            raise ValueError("Epoch-plan archive contract mismatch.")
        for epoch in range(epoch_count):
            prefix = f"epoch_{epoch:04d}__"
            exported = {
                name[len(prefix):]: np.asarray(archive[name]).copy()
                for name in archive.files
                if name.startswith(prefix)
            }
            plan = PolyphonicEpochPlan.from_export(exported)
            if plan.epoch != epoch:
                raise ValueError(
                    f"Persisted epoch plan {epoch} has a bad index."
                )
            plans.append(plan)
    return plans


def _validate_continuation_config(
    source_config: Mapping[str, object],
    target_config: Mapping[str, object],
) -> int:
    """Allow only an increase of the immutable epoch target."""

    source = json.loads(json.dumps(dict(source_config)))
    target = json.loads(json.dumps(dict(target_config)))
    source_train = source.get("train")
    target_train = target.get("train")
    if not isinstance(source_train, dict) or not isinstance(
        target_train, dict
    ):
        raise ValueError("Continuation configs require a train mapping.")
    source_epochs = int(source_train.get("epochs", 0))
    target_epochs = int(target_train.get("epochs", 0))
    if source_epochs < 1 or target_epochs <= source_epochs:
        raise ValueError(
            "Continuation must increase the completed epoch target."
        )
    source_train["epochs"] = target_epochs
    if source != target:
        raise ValueError(
            "Continuation config may differ only by train.epochs."
        )
    return source_epochs


def _validate_continuation_epoch_plans(
    source_plans: Sequence[PolyphonicEpochPlan],
    target_plans: Sequence[PolyphonicEpochPlan],
    completed_epochs: int,
) -> None:
    """Prove that the expanded plan retains every completed epoch."""

    completed = int(completed_epochs)
    if completed < 1 or len(source_plans) != completed:
        raise ValueError(
            "Continuation source plan count differs from completed epochs."
        )
    if len(target_plans) <= completed:
        raise ValueError(
            "Continuation target must contain at least one new epoch plan."
        )
    for epoch in range(completed):
        if source_plans[epoch].sha256 != target_plans[epoch].sha256:
            raise ValueError(
                f"Continuation changed completed epoch plan {epoch + 1}."
            )


def _continuation_source_signatures(
    source_run: Path,
    source_config: Mapping[str, object],
) -> RecoverySignatures:
    runtime_path = source_run / "runtime.json"
    plan_path = source_run / "epoch_plans.npz"
    if not runtime_path.is_file() or not plan_path.is_file():
        raise FileNotFoundError(
            "Continuation source lacks runtime.json or epoch_plans.npz."
        )
    runtime = json.loads(runtime_path.read_text(encoding="utf-8"))
    dataset = source_config.get("dataset")
    if not isinstance(dataset, Mapping):
        raise ValueError("Continuation source dataset config is invalid.")
    manifest = Path(str(dataset["manifest"]))
    if not manifest.is_file():
        raise FileNotFoundError(
            f"Continuation manifest is unavailable: {manifest}"
        )
    return RecoverySignatures(
        plan_sha256=file_sha256(plan_path),
        config_sha256=_canonical_json_sha256(source_config),
        manifest_sha256=file_sha256(manifest),
        commit=str(runtime["git_commit"]),
    )


def _bootstrap_continuation(
    *,
    source_run: str | Path,
    run_dir: Path,
    target_config: Mapping[str, object],
    target_plans: Sequence[PolyphonicEpochPlan],
    target_signatures: RecoverySignatures,
    smoke_test: bool,
) -> RecoverySnapshot:
    """Fork a completed run while retaining compiled optimizer and policy."""

    source = Path(source_run).resolve()
    status_path = source / "training_status.json"
    config_path = source / "config.json"
    if (
        not source.is_dir()
        or not status_path.is_file()
        or not config_path.is_file()
    ):
        raise FileNotFoundError(
            f"Continuation source is not a complete run: {source}"
        )
    status = json.loads(status_path.read_text(encoding="utf-8"))
    if (
        status.get("status") != "complete"
        or status.get("locked_test_used") is not False
    ):
        raise ValueError(
            "Continuation source must be complete and exclude the locked test."
        )
    source_config = json.loads(config_path.read_text(encoding="utf-8"))
    source_epochs = _validate_continuation_config(
        source_config, target_config
    )
    source_signatures = _continuation_source_signatures(
        source, source_config
    )
    source_snapshot = load_latest_recovery_checkpoint(
        source / "recovery",
        signatures=source_signatures,
    )
    if source_snapshot is None:
        raise FileNotFoundError(
            f"Continuation source has no compiled recovery: {source}"
        )
    if (
        int(source_snapshot.state["epoch"]) != source_epochs
        or int(source_snapshot.state["next_batch"]) != 0
    ):
        raise ValueError(
            "Continuation source is not at a completed epoch boundary."
        )
    callback_state = _validate_callback_state(
        source_snapshot.state["callback_state"]
    )
    if not smoke_test:
        source_plans = _load_epoch_plans_archive(
            source / "epoch_plans.npz"
        )
        _validate_continuation_epoch_plans(
            source_plans, target_plans, source_epochs
        )
    elif len(target_plans) != source_epochs + 1:
        raise ValueError(
            "A continuation smoke must exercise exactly one new epoch."
        )

    epoch_dir = run_dir / "epochs"
    epoch_dir.mkdir(parents=True, exist_ok=True)
    for epoch in range(1, source_epochs + 1):
        checkpoint = source / "epochs" / f"epoch-{epoch:02d}.keras"
        if not checkpoint.is_file():
            raise FileNotFoundError(
                f"Continuation source checkpoint is missing: {checkpoint}"
            )
        _atomic_copy(checkpoint, epoch_dir / checkpoint.name)
    for name in ("best.keras", "last.keras"):
        checkpoint = source / name
        if not checkpoint.is_file():
            raise FileNotFoundError(
                f"Continuation source checkpoint is missing: {checkpoint}"
            )
        _atomic_copy(checkpoint, run_dir / name)
    history_rows = callback_state["history_rows"]
    if not isinstance(history_rows, list):
        raise ValueError("Continuation history state is invalid.")
    _write_history_csv(run_dir / "history.csv", history_rows)

    snapshot = save_recovery_checkpoint(
        run_dir / "recovery",
        source_snapshot.model,
        epoch=source_epochs,
        next_batch=0,
        signatures=target_signatures,
        callback_state=callback_state,
    )
    atomic_write_json(
        run_dir / "continuation_source.json",
        {
            "schema_version": 1,
            "source_run": str(source),
            "source_epochs": source_epochs,
            "target_epochs": len(target_plans),
            "source_generation": source_snapshot.state["generation"],
            "source_model_sha256": source_snapshot.state["model_sha256"],
            "source_optimizer_iterations": source_snapshot.state[
                "optimizer_iterations"
            ],
            "source_learning_rate": source_snapshot.state["learning_rate"],
            "target_generation": snapshot.state["generation"],
            "target_model_sha256": snapshot.state["model_sha256"],
            "locked_test_used": False,
            "smoke_test": bool(smoke_test),
        },
    )
    return snapshot


def _chunk_example_count(
    plan: PolyphonicEpochPlan,
    batch_size: int,
    start_batch: int,
    end_batch: int,
) -> int:
    start = int(start_batch) * int(batch_size)
    end = min(int(end_batch) * int(batch_size), len(plan.order))
    return max(end - start, 0)


def _chunk_seed(
    signatures: RecoverySignatures, epoch: int, start_batch: int
) -> int:
    payload = (
        f"{signatures.plan_sha256}:{int(epoch)}:{int(start_batch)}"
    ).encode("ascii")
    value = int.from_bytes(
        hashlib.sha256(payload).digest()[:4], "big"
    ) & 0x7FFFFFFF
    return max(value, 1)


def _reset_chunk_randomness(model: Any, seed: int) -> None:
    """Make stochastic layers depend only on the immutable chunk identity."""

    tf.keras.utils.set_random_seed(int(seed))
    try:
        keras_major = int(str(keras.__version__).split(".", 1)[0])
    except (AttributeError, ValueError):
        keras_major = 3
    if hasattr(model, "_flatten_layers"):
        layers = model._flatten_layers(
            include_self=False, recursive=True
        )
    else:
        layers = getattr(model, "submodules", model.layers)
    for index, layer in enumerate(layers):
        if not isinstance(layer, tf.keras.layers.Dropout):
            continue
        layer_seed = (int(seed) + index + 1) & 0x7FFFFFFF
        layer_seed = max(layer_seed, 1)
        if hasattr(layer, "seed"):
            layer.seed = layer_seed
        legacy_generator = getattr(layer, "_random_generator", None)
        if keras_major < 3 and legacy_generator is not None:
            if hasattr(legacy_generator, "_seed"):
                legacy_generator._seed = layer_seed
            if hasattr(legacy_generator, "_rng_type"):
                # The TF 2.15 legacy RNG embeds a stateful-op counter in the
                # traced graph and cannot be reconstructed exactly after a
                # process restart. Force its supported Generator-backed mode
                # and reset that explicit state at every chunk.
                legacy_generator._rng_type = "stateful"
            if hasattr(legacy_generator, "_generator"):
                legacy_generator._generator = tf.random.Generator.from_seed(
                    layer_seed
                )
            if hasattr(legacy_generator, "_built"):
                legacy_generator._built = True
        seed_generator = (
            getattr(layer, "seed_generator", None)
            or getattr(layer, "_seed_generator", None)
        )
        state = getattr(seed_generator, "state", None)
        if state is not None and hasattr(state, "assign"):
            current = np.asarray(state.numpy())
            replacement = np.zeros_like(current)
            replacement.reshape(-1)[0] = layer_seed
            state.assign(replacement)
    # TF/Keras 2 freezes the legacy Dropout seed while tracing the training
    # function. Rebuild once per relatively large recovery chunk so a resumed
    # process and an uninterrupted process start that chunk from the same
    # stateless identity. Keras 3 also tolerates this invalidation.
    if keras_major < 3:
        if hasattr(model, "train_function"):
            model.train_function = None
        if hasattr(model, "make_train_function"):
            parameters = inspect.signature(
                model.make_train_function
            ).parameters
            if "force" in parameters:
                model.make_train_function(force=True)
            else:
                model.make_train_function()


class _ChunkProgress(tf.keras.callbacks.Callback):
    """Observe one recovery chunk without enforcing a mid-chunk time stop."""

    def __init__(
        self,
        path: str | Path,
        *,
        epoch: int,
        total_epochs: int,
        batch_offset: int,
        total_batches: int,
        batch_size: int,
        session_completed_before: int,
        logical_completed_before: int,
        run_started: float,
        every_batches: int,
        maximum_runtime_seconds: float | None,
    ) -> None:
        super().__init__()
        self.path = Path(path)
        self.epoch = int(epoch)
        self.total_epochs = int(total_epochs)
        self.batch_offset = int(batch_offset)
        self.total_batches = int(total_batches)
        self.batch_size = int(batch_size)
        self.session_completed_before = int(session_completed_before)
        self.logical_completed_before = int(logical_completed_before)
        self.run_started = float(run_started)
        self.every_batches = int(every_batches)
        self.maximum_runtime_seconds = maximum_runtime_seconds
        self.completed = 0
        self.non_finite: str | None = None
        self.batch_started = 0.0

    def on_train_batch_begin(self, batch: int, logs=None) -> None:
        self.batch_started = time.monotonic()

    def on_train_batch_end(self, batch: int, logs=None) -> None:
        self.completed = int(batch) + 1
        for name, raw in (logs or {}).items():
            if raw is not None and not np.isfinite(float(raw)):
                self.non_finite = f"{name}={raw}"
                self.model.stop_training = True
                break
        logical_batch = self.batch_offset + self.completed
        if (
            self.completed == 1
            or logical_batch % self.every_batches == 0
            or logical_batch >= self.total_batches
            or self.non_finite is not None
        ):
            now = time.monotonic()
            elapsed = max(now - self.run_started, 0.0)
            session_completed = (
                self.session_completed_before + self.completed
            )
            logical_completed = (
                self.logical_completed_before + self.completed
            )
            total_training_batches = self.total_batches * self.total_epochs
            session_rate = (
                session_completed / elapsed if elapsed > 0.0 else None
            )
            remaining_batches = max(
                total_training_batches - logical_completed, 0
            )
            report = {
                "schema_version": 2,
                "status": (
                    "non_finite"
                    if self.non_finite is not None
                    else "running"
                ),
                "epoch": self.epoch + 1,
                "total_epochs": self.total_epochs,
                "batch": logical_batch,
                "total_batches": self.total_batches,
                "completed_batches": logical_completed,
                "session_completed_batches": session_completed,
                "batch_size": self.batch_size,
                "elapsed_seconds": elapsed,
                "batch_seconds": now - self.batch_started,
                "examples_per_second": (
                    session_rate * self.batch_size
                    if session_rate is not None else None
                ),
                "projected_training_seconds": (
                    elapsed + remaining_batches / session_rate
                    if session_rate is not None and session_rate > 0.0
                    else None
                ),
                "projected_remaining_seconds": (
                    remaining_batches / session_rate
                    if session_rate is not None and session_rate > 0.0
                    else None
                ),
                "maximum_runtime_seconds": self.maximum_runtime_seconds,
                "maximum_rss_mib": BatchProgressLogger._maximum_rss_mib(),
                "gpu": BatchProgressLogger._gpu_snapshot(),
                "metrics": {
                    str(name): float(value)
                    for name, value in (logs or {}).items()
                    if (
                        value is not None
                        and np.isfinite(float(value))
                    )
                },
                "updated_at_utc": datetime.now(
                    timezone.utc
                ).isoformat(),
            }
            atomic_write_json(self.path, report)
            print(
                "BATCH_PROGRESS "
                + json.dumps(report, separators=(",", ":")),
                flush=True,
            )


def _history_last(history: Any) -> dict[str, float]:
    values: dict[str, float] = {}
    for name, series in history.history.items():
        if series:
            values[str(name)] = float(series[-1])
    return _finite_metrics(values, context="training")


def _epoch_transaction_path(run_dir: Path, epoch: int) -> Path:
    return run_dir / "epoch_transactions" / f"epoch-{epoch + 1:02d}.json"


def _prepare_or_load_epoch_transaction(
    *,
    run_dir: Path,
    epoch: int,
    model: Any,
    validation_sequence: PolyphonicSequence,
    callback_state: Mapping[str, object],
    recovery_snapshot: RecoverySnapshot,
    signatures: RecoverySignatures,
) -> dict[str, object]:
    transaction_path = _epoch_transaction_path(run_dir, epoch)
    transaction_path.parent.mkdir(parents=True, exist_ok=True)
    policy_pre = SerializableTrainingPolicy.from_dict(
        callback_state["policy"]  # type: ignore[arg-type]
    )
    immutable = {
        "schema_version": 1,
        "epoch": int(epoch),
        "source_model_sha256": recovery_snapshot.state["model_sha256"],
        "source_optimizer_iterations": _optimizer_iterations(model),
        "signatures": signatures.as_dict(),
        "policy_pre": policy_pre.as_dict(),
        "locked_test_used": False,
    }
    if transaction_path.exists():
        transaction = json.loads(
            transaction_path.read_text(encoding="utf-8")
        )
        for name, expected in immutable.items():
            if transaction.get(name) != expected:
                raise ValueError(
                    f"Epoch transaction {epoch + 1} disagrees on {name}."
                )
        return transaction

    validation_raw = model.evaluate(
        validation_sequence,
        verbose=2,
        return_dict=True,
    )
    validation_metrics = {
        f"val_{name}": value
        for name, value in _finite_metrics(
            validation_raw, context="validation"
        ).items()
    }
    accumulator = MetricAccumulator.from_dict(
        callback_state["metric_accumulator"]  # type: ignore[arg-type]
    )
    metrics = {**accumulator.metrics(), **validation_metrics}
    policy_post = SerializableTrainingPolicy.from_dict(
        policy_pre.as_dict()
    )
    decision = policy_post.advance(
        epoch,
        metrics,
        _optimizer_learning_rate(model),
    )
    history_row: dict[str, float | int] = {"epoch": int(epoch)}
    history_row.update(metrics)
    transaction = {
        **immutable,
        "metrics": metrics,
        "history_row": history_row,
        "policy_post": policy_post.as_dict(),
        "decision": decision.as_dict(),
    }
    atomic_write_json(transaction_path, transaction)
    return transaction


def _upsert_history_row(
    rows: Sequence[Mapping[str, object]],
    row: Mapping[str, object],
) -> list[dict[str, object]]:
    epoch = int(row["epoch"])
    result = [
        dict(value) for value in rows if int(value["epoch"]) != epoch
    ]
    result.append(dict(row))
    result.sort(key=lambda value: int(value["epoch"]))
    return result


def _finalize_epoch_transaction(
    *,
    run_dir: Path,
    epoch: int,
    total_epochs: int,
    model: Any,
    transaction: Mapping[str, object],
    callback_state: Mapping[str, object],
    signatures: RecoverySignatures,
    recovery_dir: Path,
) -> tuple[RecoverySnapshot, dict[str, object], bool]:
    decision = transaction["decision"]
    if not isinstance(decision, Mapping):
        raise ValueError("Epoch transaction decision is invalid.")
    _assign_optimizer_learning_rate(
        model, float(decision["learning_rate_after"])
    )
    _assert_model_finite(model)

    epoch_path = run_dir / "epochs" / f"epoch-{epoch + 1:02d}.keras"
    _atomic_model_save(model, epoch_path)
    _atomic_model_save(model, run_dir / "last.keras")
    if bool(decision["improved"]):
        _atomic_model_save(model, run_dir / "best.keras")

    raw_rows = callback_state["history_rows"]
    if not isinstance(raw_rows, list):
        raise ValueError("Recovery history state is invalid.")
    history_rows = _upsert_history_row(
        raw_rows,
        transaction["history_row"],  # type: ignore[arg-type]
    )
    _write_history_csv(run_dir / "history.csv", history_rows)
    next_callback_state = {
        "schema_version": 1,
        "policy": transaction["policy_post"],
        "history_rows": history_rows,
        "metric_accumulator": MetricAccumulator.empty().as_dict(),
    }
    snapshot = save_recovery_checkpoint(
        recovery_dir,
        model,
        epoch=epoch + 1,
        next_batch=0,
        signatures=signatures,
        callback_state=next_callback_state,
    )
    metrics = transaction["metrics"]
    if not isinstance(metrics, Mapping):
        raise ValueError("Epoch transaction metrics are invalid.")
    _write_epoch_progress(
        run_dir / "epoch_progress.json",
        status="epoch_completed",
        epoch=epoch + 1,
        total_epochs=total_epochs,
        metrics=metrics,
    )
    return snapshot, next_callback_state, bool(decision["should_stop"])


def run_recoverable_training(
    *,
    model: Any,
    train_sequence: PolyphonicSequence,
    validation_sequence: PolyphonicSequence,
    epoch_plans: Sequence[PolyphonicEpochPlan],
    run_dir: str | Path,
    signatures: RecoverySignatures,
    policy: SerializableTrainingPolicy,
    recovery_snapshot: RecoverySnapshot | None = None,
    chunk_batches: int = 250,
    log_every_batches: int = 25,
    maximum_runtime_minutes: float | None = None,
    workers: int = 1,
) -> tuple[str, Any, RecoverySnapshot]:
    """Train at crash-safe chunk boundaries and exact logical epochs."""

    destination = Path(run_dir)
    destination.mkdir(parents=True, exist_ok=True)
    recovery_dir = destination / "recovery"
    total_epochs = len(epoch_plans)
    total_batches = len(train_sequence)
    batch_size = int(train_sequence.batch_size)
    if total_epochs < 1 or total_batches < 1:
        raise ValueError("Recoverable training dimensions must be positive.")
    if chunk_batches < 1 or log_every_batches < 1:
        raise ValueError("Recovery and logging chunks must be positive.")
    maximum_runtime_seconds = (
        None
        if maximum_runtime_minutes is None
        else float(maximum_runtime_minutes) * 60.0
    )
    if (
        maximum_runtime_seconds is not None
        and maximum_runtime_seconds <= 0.0
    ):
        raise ValueError("Maximum runtime must be positive.")

    print("RECOVERY_PREFLIGHT finite_check_begin", flush=True)
    _assert_model_finite(model)
    print("RECOVERY_PREFLIGHT finite_check_complete", flush=True)
    if recovery_snapshot is None:
        print("RECOVERY_PREFLIGHT initial_checkpoint_begin", flush=True)
        callback_state = _initial_callback_state(policy)
        recovery_snapshot = save_recovery_checkpoint(
            recovery_dir,
            model,
            epoch=0,
            next_batch=0,
            signatures=signatures,
            callback_state=callback_state,
        )
        print(
            "RECOVERY_PREFLIGHT initial_checkpoint_complete "
            f"generation={recovery_snapshot.state['generation']} "
            f"slot={recovery_snapshot.state['slot']} "
            f"optimizer_iterations="
            f"{recovery_snapshot.state['optimizer_iterations']}",
            flush=True,
        )
    else:
        if recovery_snapshot.model is not model:
            raise ValueError("Recovery snapshot and training model differ.")
        callback_state = _validate_callback_state(
            recovery_snapshot.state["callback_state"]
        )

    run_started = time.monotonic()
    session_completed_batches = 0
    while True:
        epoch = int(recovery_snapshot.state["epoch"])
        next_batch = int(recovery_snapshot.state["next_batch"])
        if epoch > total_epochs:
            raise ValueError("Recovery epoch exceeds the training target.")
        if next_batch < 0 or next_batch > total_batches:
            raise ValueError("Recovery batch position is invalid.")
        if epoch == total_epochs:
            status = "complete"
            break
        restored_policy = SerializableTrainingPolicy.from_dict(
            callback_state["policy"]  # type: ignore[arg-type]
        )
        if restored_policy.stopped_epoch is not None:
            status = "early_stopped"
            break

        plan = epoch_plans[epoch]
        train_sequence.install_plan(plan)
        if train_sequence.plan_sha256 != plan.sha256:
            raise ValueError("Installed training plan digest mismatch.")
        _write_epoch_progress(
            destination / "epoch_progress.json",
            status=(
                "validating"
                if next_batch == total_batches
                else "running"
            ),
            epoch=epoch + 1,
            total_epochs=total_epochs,
        )

        if next_batch < total_batches:
            end_batch = min(next_batch + chunk_batches, total_batches)
            batch_slice = PlanBatchSlice(
                train_sequence, next_batch, end_batch
            )
            logical_completed_before = (
                epoch * total_batches + next_batch
            )
            observer = _ChunkProgress(
                destination / "batch_progress.json",
                epoch=epoch,
                total_epochs=total_epochs,
                batch_offset=next_batch,
                total_batches=total_batches,
                batch_size=batch_size,
                session_completed_before=session_completed_batches,
                logical_completed_before=logical_completed_before,
                run_started=run_started,
                every_batches=log_every_batches,
                maximum_runtime_seconds=maximum_runtime_seconds,
            )
            iterations_before = _optimizer_iterations(model)
            _reset_chunk_randomness(
                model, _chunk_seed(signatures, epoch, next_batch)
            )
            print(
                f"RECOVERY_CHUNK epoch={epoch + 1}/{total_epochs} "
                f"batches={next_batch}:{end_batch}",
                flush=True,
            )
            history = model.fit(
                batch_slice,
                epochs=1,
                callbacks=[observer],
                verbose=2,
                **_fit_queue_options(
                    model.fit,
                    workers,
                    max_queue_size=int(train_sequence.max_queue_size),
                ),
            )
            if observer.non_finite is not None:
                raise FloatingPointError(
                    "Training produced a non-finite batch "
                    f"({observer.non_finite}); recovery remains at "
                    f"epoch={epoch}, next_batch={next_batch}."
                )
            expected_batches = end_batch - next_batch
            if observer.completed != expected_batches:
                raise RuntimeError(
                    "A recovery chunk ended early: "
                    f"{observer.completed}/{expected_batches} batches."
                )
            iterations_after = _optimizer_iterations(model)
            if iterations_after - iterations_before != expected_batches:
                raise RuntimeError(
                    "Optimizer iteration count does not match the "
                    "completed recovery chunk."
                )
            session_completed_batches += observer.completed
            _assert_model_finite(model)

            accumulator = MetricAccumulator.from_dict(
                callback_state["metric_accumulator"]  # type: ignore[arg-type]
            )
            accumulator.add(
                _history_last(history),
                _chunk_example_count(
                    plan, batch_size, next_batch, end_batch
                ),
            )
            callback_state = {
                **callback_state,
                "metric_accumulator": accumulator.as_dict(),
            }
            recovery_snapshot = save_recovery_checkpoint(
                recovery_dir,
                model,
                epoch=epoch,
                next_batch=end_batch,
                signatures=signatures,
                callback_state=callback_state,
            )
            next_batch = end_batch
            if (
                maximum_runtime_seconds is not None
                and time.monotonic() - run_started
                >= maximum_runtime_seconds
            ):
                _atomic_model_save(model, destination / "paused.keras")
                atomic_write_json(
                    destination / "training_status.json",
                    {
                        "status": "paused_for_time_budget",
                        "epoch": epoch,
                        "next_batch": next_batch,
                        "time_budget_reached": True,
                        "recovery_generation": recovery_snapshot.state[
                            "generation"
                        ],
                        "locked_test_used": False,
                        "updated_at_utc": datetime.now(
                            timezone.utc
                        ).isoformat(),
                    },
                )
                return (
                    "paused_for_time_budget",
                    model,
                    recovery_snapshot,
                )
            if next_batch < total_batches:
                continue

        transaction = _prepare_or_load_epoch_transaction(
            run_dir=destination,
            epoch=epoch,
            model=model,
            validation_sequence=validation_sequence,
            callback_state=callback_state,
            recovery_snapshot=recovery_snapshot,
            signatures=signatures,
        )
        recovery_snapshot, callback_state, should_stop = (
            _finalize_epoch_transaction(
                run_dir=destination,
                epoch=epoch,
                total_epochs=total_epochs,
                model=model,
                transaction=transaction,
                callback_state=callback_state,
                signatures=signatures,
                recovery_dir=recovery_dir,
            )
        )
        if should_stop:
            status = "early_stopped"
            break

    best_path = destination / "best.keras"
    if not best_path.is_file():
        raise FileNotFoundError(
            "Training completed without a valid best.keras checkpoint."
        )
    _atomic_copy(best_path, destination / "final.keras")
    atomic_write_json(
        destination / "training_status.json",
        {
            "status": status,
            "epoch": int(recovery_snapshot.state["epoch"]),
            "next_batch": int(recovery_snapshot.state["next_batch"]),
            "time_budget_reached": False,
            "recovery_generation": recovery_snapshot.state["generation"],
            "locked_test_used": False,
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
        },
    )
    _write_epoch_progress(
        destination / "epoch_progress.json",
        status=status,
        epoch=int(recovery_snapshot.state["epoch"]),
        total_epochs=total_epochs,
    )
    return status, model, recovery_snapshot


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(line_buffering=True, write_through=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(line_buffering=True, write_through=True)
    if os.environ.get("MIDI_FORCE_CPU") == "1":
        tf.config.set_visible_devices([], "GPU")
        print("DEVICE_POLICY cpu_only", flush=True)
    else:
        print("DEVICE_POLICY default", flush=True)
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
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
    recovery_mode = parser.add_mutually_exclusive_group()
    recovery_mode.add_argument(
        "--resume-run", type=Path,
        help=(
            "Resume from an intact compiled A/B recovery generation. "
            "Legacy last.keras-only resumes are intentionally refused."
        ),
    )
    recovery_mode.add_argument(
        "--continue-from-run",
        type=Path,
        help=(
            "Start a new expanded run from a completed compiled recovery, "
            "preserving optimizer, history, policy, and epoch numbering."
        ),
    )
    parser.add_argument(
        "--workers",
        type=int,
        help="Override train.workers for the Keras PyDataset loader.",
    )
    parser.add_argument(
        "--representative-smoke",
        action="store_true",
        help="Use every train/validation recording in a timed smoke.",
    )
    parser.add_argument("--smoke-examples", type=int, default=8192)
    parser.add_argument(
        "--smoke-validation-examples", type=int, default=2048
    )
    parser.add_argument("--log-every-batches", type=int)
    parser.add_argument("--maximum-runtime-minutes", type=float)
    parser.add_argument(
        "--recovery-chunk-batches",
        type=int,
        help="Save exact compiled A/B recovery state every N train batches.",
    )
    args = parser.parse_args()
    if (
        args.continue_from_run is not None
        and args.initial_checkpoint is not None
    ):
        parser.error(
            "--continue-from-run and --initial-checkpoint are mutually exclusive."
        )
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    continuation_source_epochs: int | None = None
    if args.continue_from_run is not None:
        source_config_path = args.continue_from_run / "config.json"
        if not source_config_path.is_file():
            raise FileNotFoundError(
                "Continuation source has no immutable config.json: "
                f"{args.continue_from_run}"
            )
        source_config = json.loads(
            source_config_path.read_text(encoding="utf-8")
        )
        continuation_source_epochs = _validate_continuation_config(
            source_config, config
        )
    seed = int(config["dataset"].get("seed", 42))
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        # Older TensorFlow builds may not expose the deterministic-op switch.
        pass

    model_config = config["model"]
    independent_note_head = bool(
        model_config.get("independent_note_head", False)
    )
    manifest_path = Path(config["dataset"]["manifest"]).resolve(strict=True)
    items = load_manifest(manifest_path)
    train_items = [item for item in items if item.split == "train"]
    validation_items = [item for item in items if item.split == "validation"]
    if args.smoke_test and not args.representative_smoke:
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

    fundamental_offsets: dict[tuple[str, str], np.ndarray] = {}
    required_offset_datasets: tuple[str, ...] = ()
    if independent_note_head:
        sidecar_value = str(
            config["dataset"].get("independent_note_fundamental_offsets", "")
        )
        sidecar_expected_sha = str(
            config["dataset"].get(
                "independent_note_fundamental_offsets_sha256", ""
            )
        )
        if not sidecar_value or len(sidecar_expected_sha) != 64:
            raise ValueError(
                "A verified independent-note fundamental-offset sidecar is required."
            )
        sidecar_path = Path(sidecar_value)
        if not sidecar_path.is_absolute():
            sidecar_path = Path(__file__).resolve().parents[2] / sidecar_path
        fundamental_offsets = load_independent_note_fundamental_offsets(
            sidecar_path,
            expected_sha256=sidecar_expected_sha,
            expected_manifest_sha256=file_sha256(manifest_path),
        )
        configured_required = config["dataset"].get(
            "independent_note_fundamental_offset_required_datasets",
            ["guitarset_poly_mix"],
        )
        if not isinstance(configured_required, (list, tuple)):
            raise ValueError(
                "dataset.independent_note_fundamental_offset_required_datasets "
                "must be a list."
            )
        required_offset_datasets = tuple(str(value) for value in configured_required)

    train_corpus = PolyphonicCorpus(
        train_items,
        fundamental_offsets=fundamental_offsets,
        required_fundamental_offset_datasets=required_offset_datasets,
    )
    validation_corpus = PolyphonicCorpus(
        validation_items,
        fundamental_offsets=fundamental_offsets,
        required_fundamental_offset_datasets=required_offset_datasets,
    )
    if (
        train_corpus.midi_min != validation_corpus.midi_min
        or train_corpus.midi_max != validation_corpus.midi_max
    ):
        raise ValueError("Train/validation pitch contracts differ.")

    training = config["train"]
    harmonic_presence_head = bool(
        model_config.get("harmonic_presence_head", False)
    )
    independent_note_auxiliary_only = bool(
        model_config.get("independent_note_auxiliary_only", False)
    )
    freeze_backbone = bool(
        model_config.get("independent_note_freeze_backbone", False)
    )
    if independent_note_auxiliary_only and not independent_note_head:
        raise ValueError(
            "independent_note_auxiliary_only requires independent_note_head."
        )
    if freeze_backbone and not independent_note_head:
        raise ValueError(
            "independent_note_freeze_backbone requires independent_note_head."
        )
    if harmonic_presence_head or independent_note_head:
        required_harmonic_datasets = model_config.get(
            "harmonic_supervision_required_datasets",
            ["guitarset_poly_mix"],
        )
        if not isinstance(required_harmonic_datasets, (list, tuple)):
            raise ValueError(
                "model.harmonic_supervision_required_datasets must be a list."
            )
        minimum_harmonic_schema = int(
            model_config.get(
                "harmonic_supervision_minimum_schema_version", 3
            )
        )
        harmonic_supervision_report: dict[str, object] = {
            "enabled": True,
            "minimum_schema_version": minimum_harmonic_schema,
            "required_datasets": [
                str(value) for value in required_harmonic_datasets
            ],
            "train": _harmonic_supervision_preflight(
                train_corpus,
                split="train",
                required_datasets=required_harmonic_datasets,
                minimum_schema_version=minimum_harmonic_schema,
            ),
            "validation": _harmonic_supervision_preflight(
                validation_corpus,
                split="validation",
                required_datasets=required_harmonic_datasets,
                minimum_schema_version=minimum_harmonic_schema,
            ),
        }
    else:
        harmonic_supervision_report = {"enabled": False}
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
        examples_per_epoch = int(args.smoke_examples)
        validation_examples = int(args.smoke_validation_examples)
        epochs = (
            1
            if continuation_source_epochs is None
            else continuation_source_epochs + 1
        )
    if examples_per_epoch < 1 or validation_examples < 1:
        raise ValueError("Training and validation example counts must be positive.")
    workers = int(
        args.workers
        if args.workers is not None
        else training.get("workers", 1)
    )
    if workers < 1:
        raise ValueError("workers must be positive.")

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
        recovery_dir = run_dir / "recovery"
        if (
            not run_dir.is_dir()
            or not any(
                (recovery_dir / f"recovery-{slot}.json").is_file()
                for slot in ("a", "b")
            )
        ):
            raise FileNotFoundError(
                "Resume run must contain compiled A/B recovery state; "
                f"legacy last.keras-only resume is not exact: {run_dir}"
            )
        saved_config_path = run_dir / "config.json"
        if not saved_config_path.is_file():
            raise FileNotFoundError(
                f"Resume run has no immutable config.json: {run_dir}"
            )
        saved_config = json.loads(
            saved_config_path.read_text(encoding="utf-8")
        )
        if _canonical_json_sha256(saved_config) != _canonical_json_sha256(
            config
        ):
            raise ValueError(
                "Resume config differs from the immutable run config."
            )
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        suffix = "_smoke" if args.smoke_test else ""
        run_dir = Path(training["output_root"]) / (
            f"{training['run_name']}{suffix}_{timestamp}"
        )
        run_dir.mkdir(parents=True, exist_ok=False)
        _json(run_dir / "config.json", config)
        _json(run_dir / "runtime.json", {
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "keras": keras.__version__,
            "numpy": np.__version__,
            "git_commit": git_commit(),
            "smoke_test": args.smoke_test,
            "representative_smoke": args.representative_smoke,
            "workers": workers,
            "recovery_chunk_batches": int(
                args.recovery_chunk_batches
                if args.recovery_chunk_batches is not None
                else training.get("recovery_chunk_batches", 250)
            ),
            "continuation_source": (
                None
                if args.continue_from_run is None
                else str(args.continue_from_run.resolve())
            ),
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
        "harmonic_supervision": harmonic_supervision_report,
    }
    if not args.resume_run:
        _json(run_dir / "dataset_statistics.json", statistics)

    sequence_options = {
        "batch_size": int(training["batch_size"]),
        "input_samples": int(config["dataset"]["input_samples"]),
        "normalization_gain": float(config["dataset"]["normalization_gain"]),
        "harmonic_presence_target": harmonic_presence_head,
        "independent_note_target": independent_note_head,
        "workers": workers,
        "max_queue_size": int(training.get("max_queue_size", 2)),
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

    epoch_plans, plan_sha256 = _persist_or_load_epoch_plans(
        run_dir / "epoch_plans.npz",
        train_sequence,
        epochs,
    )
    signatures = RecoverySignatures(
        plan_sha256=plan_sha256,
        config_sha256=_canonical_json_sha256(config),
        manifest_sha256=file_sha256(
            Path(config["dataset"]["manifest"])
        ),
        commit=git_commit(),
    )
    recovery_snapshot: RecoverySnapshot | None = None
    if args.resume_run:
        recovery_snapshot = load_latest_recovery_checkpoint(
            run_dir / "recovery",
            signatures=signatures,
        )
        if recovery_snapshot is None:
            raise FileNotFoundError(
                f"No recoverable compiled generation in {run_dir}."
            )
        model = recovery_snapshot.model
        if getattr(model, "optimizer", None) is None:
            raise ValueError(
                "Recovery model was not loaded with its compiled optimizer."
            )
        print(
            "Recovered compiled model "
            f"generation={recovery_snapshot.state['generation']} "
            f"epoch={recovery_snapshot.state['epoch']} "
            f"next_batch={recovery_snapshot.state['next_batch']} "
            f"optimizer_iterations={recovery_snapshot.state['optimizer_iterations']}",
            flush=True,
        )
    elif args.continue_from_run is not None:
        recovery_snapshot = _bootstrap_continuation(
            source_run=args.continue_from_run,
            run_dir=run_dir,
            target_config=config,
            target_plans=epoch_plans,
            target_signatures=signatures,
            smoke_test=bool(args.smoke_test),
        )
        model = recovery_snapshot.model
        print(
            "Continued compiled model "
            f"source={args.continue_from_run.resolve()} "
            f"epoch={recovery_snapshot.state['epoch']} "
            f"optimizer_iterations="
            f"{recovery_snapshot.state['optimizer_iterations']}",
            flush=True,
        )
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
            harmonic_presence_head=harmonic_presence_head,
            independent_note_head=independent_note_head,
            independent_note_units=int(
                model_config.get("independent_note_units", 32)
            ),
        )
        initialization = config.get("initialization", {})
        source_model = (
            args.initial_checkpoint or initialization.get("mono_checkpoint")
        )
        if source_model:
            source_path = Path(source_model)
            required_checkpoint_sha256 = initialization.get(
                "required_checkpoint_sha256"
            )
            if required_checkpoint_sha256:
                actual_checkpoint_sha256 = file_sha256(source_path)
                if actual_checkpoint_sha256 != str(
                    required_checkpoint_sha256
                ):
                    raise ValueError(
                        "Initialization checkpoint SHA-256 differs from the "
                        "immutable config: "
                        f"{actual_checkpoint_sha256} != "
                        f"{required_checkpoint_sha256}."
                    )
            transfer = transfer_compatible_weights(model, source_path)
        else:
            transfer = {"source": None, "transferred": [], "skipped": []}
        if freeze_backbone:
            if not source_model:
                raise ValueError(
                    "A verified initialization checkpoint is required when "
                    "the independent-note backbone is frozen."
                )
            trainable_layers = _freeze_independent_note_backbone(
                model, transfer
            )
        else:
            trainable_layers = [
                layer.name for layer in model.layers if layer.trainable
            ]
        transfer["frozen_backbone"] = freeze_backbone
        transfer["trainable_layers"] = trainable_layers
        _json(run_dir / "weight_transfer.json", transfer)
        losses = {
            "frame": ClassWeightedBinaryCrossentropy(
                frame_weights.tolist()
            ),
            "onset": ClassWeightedBinaryCrossentropy(
                onset_weights.tolist()
            ),
            "harmonic_amplitude": (
                PolyphonicMaskedHarmonicAmplitudeLoss(
                    train_corpus.harmonic_count,
                    normalize_by_supervised_count=(
                        harmonic_presence_head
                    ),
                )
            ),
            "harmonic_offset_cents": PolyphonicHarmonicOffsetLoss(
                train_corpus.harmonic_count,
                float(model_config["harmonic_offset_scale_cents"]),
                normalize_by_supervised_count=harmonic_presence_head,
            ),
        }
        loss_weights = {
            "frame": 1.0,
            "onset": float(model_config["onset_loss_weight"]),
            "harmonic_amplitude": float(
                model_config["harmonic_amplitude_loss_weight"]
            ),
            "harmonic_offset_cents": float(
                model_config["harmonic_offset_loss_weight"]
            ),
        }
        if harmonic_presence_head:
            losses["harmonic_presence"] = (
                PolyphonicMaskedHarmonicPresenceLoss(
                    train_corpus.harmonic_count,
                    positive_weight=float(
                        model_config.get(
                            "harmonic_presence_positive_weight", 1.0
                        )
                    ),
                    negative_weight=float(
                        model_config.get(
                            "harmonic_presence_negative_weight", 1.0
                        )
                    ),
                )
            )
            loss_weights["harmonic_presence"] = float(
                model_config.get("harmonic_presence_loss_weight", 0.05)
            )
        if independent_note_head:
            losses["independent_note"] = PolyphonicMaskedIndependentNoteLoss(
                train_corpus.pitch_classes,
                positive_weight=float(
                    model_config.get("independent_note_positive_weight", 1.0)
                ),
                negative_weight=float(
                    model_config.get("independent_note_negative_weight", 1.0)
                ),
            )
            loss_weights["independent_note"] = float(
                model_config.get("independent_note_loss_weight", 1.0)
            )
            if independent_note_auxiliary_only:
                for output_name in tuple(loss_weights):
                    if output_name != "independent_note":
                        loss_weights[output_name] = 0.0
        metrics: dict[str, list[tf.keras.metrics.Metric]] = {
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
        }
        if harmonic_presence_head:
            presence_threshold = float(
                model_config.get("harmonic_presence_metric_threshold", 0.5)
            )
            metrics["harmonic_presence"] = [
                PolyphonicMaskedHarmonicPresencePrecision(
                    train_corpus.harmonic_count,
                    threshold=presence_threshold,
                ),
                PolyphonicMaskedHarmonicPresenceRecall(
                    train_corpus.harmonic_count,
                    threshold=presence_threshold,
                ),
                PolyphonicMaskedHarmonicPresenceF1(
                    train_corpus.harmonic_count,
                    threshold=presence_threshold,
                ),
                PolyphonicMaskedHarmonicPresenceBrier(
                    train_corpus.harmonic_count
                ),
            ]
        if independent_note_head:
            independent_threshold = float(
                model_config.get("independent_note_metric_threshold", 0.5)
            )
            metrics["independent_note"] = [
                PolyphonicMaskedIndependentNotePrecision(
                    train_corpus.pitch_classes,
                    threshold=independent_threshold,
                ),
                PolyphonicMaskedIndependentNoteRecall(
                    train_corpus.pitch_classes,
                    threshold=independent_threshold,
                ),
                PolyphonicMaskedIndependentNoteF1(
                    train_corpus.pitch_classes,
                    threshold=independent_threshold,
                ),
                PolyphonicMaskedIndependentNoteBrier(
                    train_corpus.pitch_classes
                ),
            ]
        model.compile(
            optimizer=tf.keras.optimizers.Adam(
                float(training["learning_rate"])
            ),
            loss=losses,
            loss_weights=loss_weights,
            metrics=metrics,
        )
    (run_dir / "epochs").mkdir(exist_ok=True)

    print(f"Run directory: {run_dir}")
    print("Preloading compact audio cache...")
    train_corpus.preload_audio()
    validation_corpus.preload_audio()
    _json(run_dir / "audio_cache.json", {
        "train_gib": train_corpus.audio_gib,
        "validation_gib": validation_corpus.audio_gib,
    })
    training_status = "running"
    try:
        _write_model_overview(model, run_dir)
        training_status, model, recovery_snapshot = (
            run_recoverable_training(
                model=model,
                train_sequence=train_sequence,
                validation_sequence=validation_sequence,
                epoch_plans=epoch_plans,
                run_dir=run_dir,
                signatures=signatures,
                policy=SerializableTrainingPolicy(
                    early_stopping_patience=int(
                        training["early_stopping_patience"]
                    ),
                    reduce_lr_patience=int(
                        training["reduce_lr_patience"]
                    ),
                    minimum_learning_rate=float(
                        training["minimum_learning_rate"]
                    ),
                    early_monitor_metric=(
                        "val_independent_note_loss"
                        if (
                            independent_note_auxiliary_only
                            or freeze_backbone
                        )
                        else "val_frame_micro_f1"
                    ),
                    early_monitor_mode=(
                        "min"
                        if (
                            independent_note_auxiliary_only
                            or freeze_backbone
                        )
                        else "max"
                    ),
                ),
                recovery_snapshot=recovery_snapshot,
                chunk_batches=int(
                    args.recovery_chunk_batches
                    if args.recovery_chunk_batches is not None
                    else training.get("recovery_chunk_batches", 250)
                ),
                log_every_batches=int(
                    args.log_every_batches
                    if args.log_every_batches is not None
                    else training.get("log_every_batches", 25)
                ),
                maximum_runtime_minutes=(
                    args.maximum_runtime_minutes
                    if args.maximum_runtime_minutes is not None
                    else training.get("maximum_runtime_minutes")
                ),
                workers=workers,
            )
        )
    except Exception as error:
        training_status = "error"
        try:
            latest_recovery = load_latest_recovery_checkpoint(
                run_dir / "recovery",
                signatures=signatures,
            )
            if latest_recovery is not None:
                recovery_snapshot = latest_recovery
        except Exception:
            # Preserve the original training error; the A/B loader will expose
            # any recovery-integrity problem on the explicit resume attempt.
            pass
        state = (
            {}
            if recovery_snapshot is None
            else {
                "epoch": recovery_snapshot.state["epoch"],
                "next_batch": recovery_snapshot.state["next_batch"],
                "recovery_generation": recovery_snapshot.state[
                    "generation"
                ],
            }
        )
        atomic_write_json(run_dir / "training_status.json", {
            "status": training_status,
            **state,
            "error_type": type(error).__name__,
            "error": str(error),
            "updated_at_utc": datetime.now(timezone.utc).isoformat(),
            "time_budget_reached": False,
            "locked_test_used": False,
        })
        raise
    finally:
        train_corpus.close()
        validation_corpus.close()
    (Path(training["output_root"]) / "latest_run.txt").write_text(
        str(run_dir.resolve()), encoding="utf-8"
    )
    print(f"Polyphonic training {training_status}: {run_dir}", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
