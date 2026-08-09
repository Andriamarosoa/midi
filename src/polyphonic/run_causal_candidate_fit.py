"""Sealed, train-only runner for the preregistered causal candidate fit V1.

The module is inert on import.  A real invocation requires an explicit
environment acknowledgement, a clean expected Git commit, CPU-only TensorFlow,
the exact V3 artifacts, and a fresh output directory.  It never opens the
official validation or locked-test splits.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import time
from typing import Mapping, Sequence

from .causal_candidate_fit import (
    CAUSAL_FEATURES,
    ENCODED_FEATURES,
    FEATURE_DIMENSION,
    CandidateFitPreflight,
    CandidateFitRow,
    CandidateFitExecutionSpec,
    CalibrationDecision,
    DevSignal,
    FitStandardizer,
    V1_CONTRACT,
    V1_EXECUTION_SPEC,
    assess_dev_signal,
    build_v1_logistic_model,
    choose_calibration_threshold,
    configure_deterministic_cpu_tensorflow,
    fit_standardizer,
    group_balanced_weights,
    preflight_sealed_candidate_artifact,
    transform_rows,
    verify_saved_model_parity,
)


FIT_RUN_SCHEMA_VERSION = 1
FIT_WALL_TIMEOUT_SECONDS = 15 * 60
FIT_EXECUTE_ENV = "DECODER_CANDIDATE_FIT_EXECUTE"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _require_git_sha(value: str, name: str) -> str:
    if not (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase 40-character Git SHA.")
    return value


def _require_explicit_execution_acknowledgement() -> None:
    if os.environ.get(FIT_EXECUTE_ENV) != "1":
        raise RuntimeError(
            "Fail closed: set DECODER_CANDIDATE_FIT_EXECUTE=1 only after the "
            "separately approved fit command."
        )


def _require_clean_expected_git_commit(
    repository_root: Path,
    expected_commit: str,
) -> str:
    expected_commit = _require_git_sha(expected_commit, "expected_runner_commit")
    repository_root = repository_root.resolve(strict=True)
    status = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise RuntimeError("Fail closed: runner repository worktree is not clean.")
    head = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if head != expected_commit:
        raise RuntimeError(
            f"Fail closed: expected runner commit {expected_commit}, got {head}."
        )
    return head


@dataclass(frozen=True)
class PartitionArrays:
    """One immutable canonical partition, with weights derived locally."""

    partition: str
    rows: tuple[CandidateFitRow, ...]
    features: tuple[tuple[float, ...], ...]
    targets: tuple[int, ...]
    weights: tuple[float, ...]

    def __post_init__(self) -> None:
        if self.partition not in ("fit", "dev", "calibration"):
            raise ValueError("partition must be fit, dev, or calibration.")
        if not self.rows or any(row.partition != self.partition for row in self.rows):
            raise ValueError("partition rows must be non-empty and homogeneous.")
        if not (
            len(self.rows) == len(self.features) == len(self.targets) == len(self.weights)
        ):
            raise ValueError("partition arrays must have the same length.")
        for vector in self.features:
            if len(vector) != FEATURE_DIMENSION or not all(math.isfinite(value) for value in vector):
                raise ValueError("partition features must be finite V1 vectors.")
        if any(type(target) is not int or target not in (0, 1) for target in self.targets):
            raise ValueError("partition targets must be binary integers.")
        if not all(math.isfinite(value) and value > 0.0 for value in self.weights):
            raise ValueError("partition weights must be finite and positive.")


@dataclass(frozen=True)
class FitRunResult:
    """A completed, still non-authorizing V1 internal-fit artifact."""

    output_dir: Path
    report_path: Path
    model_path: Path
    standardizer_path: Path
    status: str
    best_epoch: int
    duration_seconds: float


def build_partition_arrays(
    preflight: CandidateFitPreflight,
) -> tuple[FitStandardizer, PartitionArrays, PartitionArrays, PartitionArrays]:
    """Build every partition from canonical rows without caller-supplied weights."""

    fit_rows = preflight.rows_for_partition("fit")
    dev_rows = preflight.rows_for_partition("dev")
    calibration_rows = preflight.rows_for_partition("calibration")
    standardizer = fit_standardizer(fit_rows)

    def build(partition: str, rows: Sequence[CandidateFitRow]) -> PartitionArrays:
        return PartitionArrays(
            partition=partition,
            rows=tuple(rows),
            features=transform_rows(rows, standardizer),
            targets=tuple(row.target for row in rows),
            # Do not accept weights as a parameter: each partition gets its
            # own mandatory canonical group-balanced calculation.
            weights=group_balanced_weights(rows),
        )

    return (
        standardizer,
        build("fit", fit_rows),
        build("dev", dev_rows),
        build("calibration", calibration_rows),
    )


def _probabilities(model, features: Sequence[Sequence[float]]) -> tuple[float, ...]:
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("candidate fit runner requires NumPy.") from error
    matrix = np.asarray(features, dtype=np.float32)
    values = np.asarray(model(matrix, training=False), dtype=np.float64).reshape(-1)
    if len(values) != len(features) or not all(
        math.isfinite(float(value)) and 0.0 <= float(value) <= 1.0
        for value in values
    ):
        raise RuntimeError("candidate fit model returned invalid probabilities.")
    return tuple(float(value) for value in values)


def _as_training_arrays(partition: PartitionArrays):
    """Materialize the one-input Keras training tensors explicitly.

    ``PartitionArrays`` deliberately stores immutable Python tuples for the
    sealed preflight and reproducible report construction.  Keras, however,
    receives exactly one dense ``(candidates, 12)`` input and matching
    one-dimensional target/weight arrays.  Do not leave that boundary to
    Keras's nested-list interpretation on the first real fit.
    """

    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("candidate fit runner requires NumPy.") from error
    features = np.asarray(partition.features, dtype=np.float32)
    targets = np.asarray(partition.targets, dtype=np.float32)
    weights = np.asarray(partition.weights, dtype=np.float32)
    if features.shape != (len(partition.rows), FEATURE_DIMENSION):
        raise RuntimeError("candidate fit feature matrix shape is invalid.")
    if targets.shape != (len(partition.rows),) or weights.shape != targets.shape:
        raise RuntimeError("candidate fit target or weight array shape is invalid.")
    if not (
        np.isfinite(features).all()
        and np.isfinite(targets).all()
        and np.isfinite(weights).all()
    ):
        raise RuntimeError("candidate fit arrays must be finite.")
    return features, targets, weights


def _make_callbacks(
    tf,
    dev: PartitionArrays,
    *,
    execution_spec: CandidateFitExecutionSpec = V1_EXECUTION_SPEC,
    wall_timeout_seconds: float = FIT_WALL_TIMEOUT_SECONDS,
):
    """Create the only callbacks used by V1, with dev inference-only evidence."""

    class PreregisteredDevMonitor(tf.keras.callbacks.Callback):
        def __init__(self) -> None:
            super().__init__()
            self.started_at = 0.0
            self.best_epoch: int | None = None
            self.best_weighted_bce = math.inf
            self.best_weights = None
            self.wait = 0
            self.timed_out = False
            self.epoch_history: list[dict[str, object]] = []

        def on_train_begin(self, logs=None) -> None:
            self.started_at = time.monotonic()

        def _stop_if_over_budget(self) -> bool:
            if time.monotonic() - self.started_at <= wall_timeout_seconds:
                return False
            self.timed_out = True
            self.model.stop_training = True
            return True

        def on_train_batch_begin(self, batch, logs=None) -> None:
            self._stop_if_over_budget()

        def on_epoch_end(self, epoch, logs=None) -> None:
            if self._stop_if_over_budget():
                return
            # The dev set is observed only through inference.  It never enters
            # model.fit, sample_weight, a GradientTape, or a validation loss.
            probabilities = _probabilities(self.model, dev.features)
            signal = assess_dev_signal(dev.rows, probabilities)
            if logs is not None:
                logs["v1_dev_weighted_bce"] = signal.weighted_bce
            self.epoch_history.append({
                "epoch": epoch + 1,
                "weighted_bce": signal.weighted_bce,
                "weighted_brier": signal.weighted_brier,
                "roc_auc_by_family": dict(signal.roc_auc_by_family),
            })
            if signal.weighted_bce < self.best_weighted_bce - execution_spec.min_delta:
                self.best_epoch = epoch + 1
                self.best_weighted_bce = signal.weighted_bce
                self.best_weights = [weight.copy() for weight in self.model.get_weights()]
                self.wait = 0
                return
            self.wait += 1
            if self.wait >= execution_spec.patience:
                self.model.stop_training = True

        def on_train_end(self, logs=None) -> None:
            if self.best_weights is not None:
                self.model.set_weights(self.best_weights)

    return PreregisteredDevMonitor()


def _fit_model_v1(
    model,
    tensorflow,
    fit: PartitionArrays,
    dev: PartitionArrays,
    *,
    execution_spec: CandidateFitExecutionSpec = V1_EXECUTION_SPEC,
    wall_timeout_seconds: float = FIT_WALL_TIMEOUT_SECONDS,
):
    """Run the sealed single-input fit and return its exact fit/dev evidence.

    The public runner always uses :data:`V1_EXECUTION_SPEC`.  The two private
    keyword parameters exist solely to execute a one-epoch synthetic Keras
    regression test; they are not CLI or public-runner tuning knobs.
    """

    x_fit, y_fit, w_fit = _as_training_arrays(fit)
    monitor = _make_callbacks(
        tensorflow,
        dev,
        execution_spec=execution_spec,
        wall_timeout_seconds=wall_timeout_seconds,
    )
    started_at = time.monotonic()
    history = model.fit(
        x_fit,
        y_fit,
        sample_weight=w_fit,
        batch_size=execution_spec.batch_size,
        epochs=execution_spec.maximum_epochs,
        shuffle=execution_spec.shuffle,
        callbacks=[monitor],
        verbose=2,
    )
    duration_seconds = time.monotonic() - started_at
    if monitor.timed_out or duration_seconds > wall_timeout_seconds:
        raise TimeoutError("Fail closed: V1 fit exceeded its wall budget.")
    fit_losses = tuple(float(value) for value in history.history.get("loss", ()))
    if not fit_losses or len(fit_losses) != len(monitor.epoch_history):
        raise RuntimeError("V1 fit/dev histories are incomplete or misaligned.")
    if not all(math.isfinite(value) and value >= 0.0 for value in fit_losses):
        raise RuntimeError("V1 Keras fit losses are invalid.")
    return monitor, fit_losses, duration_seconds


def _training_history_json(
    fit_losses: Sequence[float],
    monitor,
) -> list[dict[str, object]]:
    if len(fit_losses) != len(monitor.epoch_history):
        raise RuntimeError("cannot serialize misaligned V1 fit/dev histories.")
    history: list[dict[str, object]] = []
    for loss, dev_epoch in zip(fit_losses, monitor.epoch_history):
        history.append({
            "epoch": dev_epoch["epoch"],
            "keras_fit_loss": float(loss),
            "dev_weighted_bce": dev_epoch["weighted_bce"],
            "dev_weighted_brier": dev_epoch["weighted_brier"],
            "dev_auc_by_family": dict(dev_epoch["roc_auc_by_family"]),
        })
    return history


def _weight_evidence(
    partitions: Sequence[PartitionArrays],
) -> list[dict[str, object]]:
    """Persist the exact local family/target/group weighting decomposition."""

    evidence: list[dict[str, object]] = []
    for partition in partitions:
        cells: dict[tuple[str, int], dict[str, list[float]]] = {}
        for row, weight in zip(partition.rows, partition.weights):
            by_group = cells.setdefault((row.family, row.target), {})
            by_group.setdefault(row.leakage_group_key, []).append(float(weight))
        for (family, target) in sorted(cells):
            by_group = cells[(family, target)]
            values = tuple(
                weight for group_values in by_group.values() for weight in group_values
            )
            evidence.append({
                "partition": partition.partition,
                "family": family,
                "target": target,
                "group_count": len(by_group),
                "row_count": len(values),
                "total_weight": math.fsum(values),
                "minimum_row_weight": min(values),
                "maximum_row_weight": max(values),
                "groups": [
                    {
                        "leakage_group_key": group,
                        "row_count": len(group_values),
                        "total_weight": math.fsum(group_values),
                        "minimum_row_weight": min(group_values),
                        "maximum_row_weight": max(group_values),
                    }
                    for group, group_values in sorted(by_group.items())
                ],
            })
    return evidence


def _inference_cost_json(model, partitions: Sequence[PartitionArrays]) -> dict[str, float | int]:
    """Measure post-fit train-only head inference cost once over all candidates."""

    features = tuple(
        vector for partition in partitions for vector in partition.features
    )
    if not features:
        raise RuntimeError("candidate inference-cost measurement requires candidates.")
    started_at = time.perf_counter()
    probabilities = _probabilities(model, features)
    elapsed_seconds = time.perf_counter() - started_at
    if len(probabilities) != len(features) or elapsed_seconds < 0.0:
        raise RuntimeError("candidate inference-cost measurement is invalid.")
    return {
        "candidates": len(features),
        "elapsed_seconds": elapsed_seconds,
        "microseconds_per_candidate": elapsed_seconds * 1_000_000.0 / len(features),
    }


def _signal_json(signal: DevSignal) -> dict[str, object]:
    return {
        "weighted_bce": signal.weighted_bce,
        "weighted_brier": signal.weighted_brier,
        "roc_auc_by_family": dict(signal.roc_auc_by_family),
        "passed": signal.passed,
    }


def _calibration_json(decision: CalibrationDecision | None) -> dict[str, object] | None:
    if decision is None:
        return None
    return {
        "threshold": decision.threshold,
        "weighted_brier": decision.weighted_brier,
        "grid": [dict(row) for row in decision.rows],
    }


def _standardizer_json(standardizer: FitStandardizer) -> dict[str, object]:
    return {
        "schema_version": FIT_RUN_SCHEMA_VERSION,
        "causal_features": list(CAUSAL_FEATURES),
        "encoded_features": list(ENCODED_FEATURES),
        "mean": list(standardizer.mean),
        "scale": list(standardizer.scale),
    }


def run_v1_fit(
    *,
    repository_root: Path,
    expected_runner_commit: str,
    candidate_events_path: Path,
    mining_report_path: Path,
    mining_protocol_path: Path,
    output_dir: Path,
) -> FitRunResult:
    """Execute exactly one V1 fit only when a user explicitly invokes it.

    This function deliberately has no knobs for optimization, weighting,
    threshold selection, validation, or test data.  The externally reviewed
    command must set :data:`FIT_EXECUTE_ENV` and name the expected Git commit.
    """

    _require_explicit_execution_acknowledgement()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"refusing to reuse fit output directory: {output_dir}")
    parent = output_dir.parent.resolve(strict=True)
    _require_clean_expected_git_commit(repository_root, expected_runner_commit)
    # These seven-digest checks happen before TensorFlow is imported.
    preflight = preflight_sealed_candidate_artifact(
        candidate_events_path,
        mining_report_path,
        mining_protocol_path,
        V1_CONTRACT,
    )
    standardizer, fit, dev, calibration = build_partition_arrays(preflight)
    tensorflow = configure_deterministic_cpu_tensorflow(V1_EXECUTION_SPEC.seed)
    model = build_v1_logistic_model(tensorflow, V1_EXECUTION_SPEC.seed)
    model.compile(
        optimizer=tensorflow.keras.optimizers.Adam(
            learning_rate=V1_EXECUTION_SPEC.learning_rate
        ),
        loss=tensorflow.keras.losses.BinaryCrossentropy(),
    )
    monitor, fit_losses, duration_seconds = _fit_model_v1(
        model,
        tensorflow,
        fit,
        dev,
    )
    if monitor.best_epoch is None:
        raise RuntimeError("V1 fit produced no monitored dev epoch.")
    training_history = _training_history_json(fit_losses, monitor)
    dev_probabilities = _probabilities(model, dev.features)
    dev_signal = assess_dev_signal(dev.rows, dev_probabilities)
    # Calibration is structurally unreachable until the separately defined dev
    # signal has passed.  It is inference-only and cannot affect gradients.
    calibration_decision = (
        choose_calibration_threshold(
            calibration.rows,
            _probabilities(model, calibration.features),
        )
        if dev_signal.passed
        else None
    )
    status = "complete_non_authorizing" if dev_signal.passed else "failed_dev_gate"
    weight_evidence = _weight_evidence((fit, dev, calibration))
    inference_cost = _inference_cost_json(model, (fit, dev, calibration))
    partial = parent / f".{output_dir.name}.partial-{os.getpid()}"
    if partial.exists():
        raise FileExistsError(f"refusing to reuse partial fit directory: {partial}")
    try:
        partial.mkdir()
        model_path = partial / "causal_candidate_fit_v1.keras"
        parity = verify_saved_model_parity(model, dev.features, model_path, tensorflow)
        model_sha256 = _sha256_file(model_path)
        standardizer_path = partial / "fit_standardizer.json"
        standardizer_payload = _standardizer_json(standardizer)
        standardizer_payload.update({
            "model_sha256": model_sha256,
            "candidate_events_sha256": preflight.candidate_events_sha256,
        })
        _write_json(standardizer_path, standardizer_payload)
        report_path = partial / "fit_report.json"
        report = {
            "schema_version": FIT_RUN_SCHEMA_VERSION,
            "purpose": "causal_decoder_candidate_fit_v1_train_only",
            "status": status,
            "locked_test_used": False,
            "validation_used": False,
            "fit_execution_spec": asdict(V1_EXECUTION_SPEC),
            "runner_commit": expected_runner_commit,
            "candidate_artifacts": {
                "candidate_events_sha256": preflight.candidate_events_sha256,
                "mining_report_sha256": preflight.mining_report_sha256,
                "mining_protocol_sha256": preflight.mining_protocol_sha256,
                "implementation_commit": V1_CONTRACT.implementation_commit,
                "required_protocol_digests": dict(
                    V1_CONTRACT.required_protocol_digests
                ),
            },
            "partitions": {
                value.partition: {
                    "rows": len(value.rows),
                    "targets": {
                        "0": sum(target == 0 for target in value.targets),
                        "1": sum(target == 1 for target in value.targets),
                    },
                    "weight_sum": math.fsum(value.weights),
                }
                for value in (fit, dev, calibration)
            },
            "weight_evidence": weight_evidence,
            "best_epoch": monitor.best_epoch,
            "duration_seconds": duration_seconds,
            "inference_cost": inference_cost,
            "dev": _signal_json(dev_signal),
            "calibration": _calibration_json(calibration_decision),
            "training_history": training_history,
            "model": {
                "path": model_path.name,
                "sha256": model_sha256,
                "save_reload_maximum_absolute_error": parity.maximum_absolute_error,
            },
            "standardizer": {
                "path": standardizer_path.name,
                "sha256": _sha256_file(standardizer_path),
            },
            "next_action": (
                "Review only: this train-only internal fit cannot authorize a "
                "historical validation, export, live use, or locked-test access."
            ),
        }
        _write_json(report_path, report)
        os.replace(partial, output_dir)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return FitRunResult(
        output_dir=output_dir,
        report_path=output_dir / "fit_report.json",
        model_path=output_dir / "causal_candidate_fit_v1.keras",
        standardizer_path=output_dir / "fit_standardizer.json",
        status=status,
        best_epoch=monitor.best_epoch,
        duration_seconds=duration_seconds,
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the separately-approved CPU-only causal candidate fit V1."
    )
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--expected-runner-commit", required=True)
    parser.add_argument("--candidate-events", type=Path, required=True)
    parser.add_argument("--mining-report", type=Path, required=True)
    parser.add_argument("--mining-protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    arguments = parser.parse_args()
    result = run_v1_fit(
        repository_root=arguments.repository_root,
        expected_runner_commit=arguments.expected_runner_commit,
        candidate_events_path=arguments.candidate_events,
        mining_report_path=arguments.mining_report,
        mining_protocol_path=arguments.mining_protocol,
        output_dir=arguments.output_dir,
    )
    print(json.dumps({
        "status": result.status,
        "output_dir": str(result.output_dir),
        "report": str(result.report_path),
        "best_epoch": result.best_epoch,
        "duration_seconds": result.duration_seconds,
        "locked_test_used": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
