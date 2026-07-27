from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from src.v5.evaluate import (
    generate_harmonic_reports,
    generate_reports as generate_pitch_reports,
    topk_accuracy,
)


def _binary_arrays(probabilities: np.ndarray, targets: np.ndarray):
    probabilities = np.asarray(probabilities, dtype=np.float64).reshape(-1)
    targets = np.asarray(targets, dtype=np.float32).reshape(-1) > 0.5
    if len(probabilities) != len(targets):
        raise ValueError("Nombre de predictions active incoherent.")
    if not np.isfinite(probabilities).all():
        raise ValueError("Predictions active non finies.")
    return np.clip(probabilities, 0.0, 1.0), targets


def binary_metrics(
    probabilities: np.ndarray,
    targets: np.ndarray,
    threshold: float,
) -> dict[str, Any]:
    probabilities, targets = _binary_arrays(probabilities, targets)
    predicted = probabilities >= float(threshold)
    tp = int(np.sum(predicted & targets))
    fp = int(np.sum(predicted & ~targets))
    tn = int(np.sum(~predicted & ~targets))
    fn = int(np.sum(~predicted & targets))
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    specificity = tn / max(tn + fp, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        "count": int(len(targets)),
        "positives": int(np.sum(targets)),
        "negatives": int(np.sum(~targets)),
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "tn": tn,
        "fn": fn,
        "precision": float(precision),
        "recall": float(recall),
        "specificity": float(specificity),
        "f1": float(f1),
        "false_positive_rate": float(fp / max(fp + tn, 1)),
        "false_negative_rate": float(fn / max(fn + tp, 1)),
        "accuracy": float((tp + tn) / max(len(targets), 1)),
    }


def average_precision(probabilities: np.ndarray, targets: np.ndarray) -> float:
    probabilities, targets = _binary_arrays(probabilities, targets)
    positives = int(np.sum(targets))
    if positives == 0:
        return 0.0
    order = np.argsort(-probabilities, kind="mergesort")
    sorted_targets = targets[order].astype(np.float64)
    precision = np.cumsum(sorted_targets) / np.arange(1, len(targets) + 1)
    return float(np.sum(precision * sorted_targets) / positives)


def select_f1_threshold(
    probabilities: np.ndarray,
    targets: np.ndarray,
) -> tuple[float, dict[str, Any]]:
    """Select a validation-only threshold, breaking ties toward fewer FPs."""
    probabilities, targets = _binary_arrays(probabilities, targets)
    if not np.any(targets) or np.all(targets):
        raise ValueError("La validation active doit contenir les deux classes.")

    order = np.argsort(-probabilities, kind="mergesort")
    scores = probabilities[order]
    labels = targets[order].astype(np.int64)
    tp = np.cumsum(labels)
    fp = np.cumsum(1 - labels)
    fn = int(np.sum(labels)) - tp
    precision = tp / np.maximum(tp + fp, 1)
    recall = tp / np.maximum(tp + fn, 1)
    f1 = 2.0 * precision * recall / np.maximum(precision + recall, 1e-12)

    boundaries = np.flatnonzero(np.r_[scores[1:] != scores[:-1], True])
    best_f1 = float(np.max(f1[boundaries]))
    candidates = boundaries[np.isclose(f1[boundaries], best_f1, rtol=0.0, atol=1e-12)]
    best_precision = float(np.max(precision[candidates]))
    candidates = candidates[
        np.isclose(precision[candidates], best_precision, rtol=0.0, atol=1e-12)
    ]
    selected = int(candidates[np.argmax(scores[candidates])])
    threshold = float(scores[selected])
    metrics = binary_metrics(probabilities, targets, threshold)
    metrics["average_precision"] = average_precision(probabilities, targets)
    metrics["selection"] = "maximum_validation_f1_then_precision_then_threshold"
    return threshold, metrics


def _grouped_active(
    output: Path,
    name: str,
    values: np.ndarray,
    probabilities: np.ndarray,
    targets: np.ndarray,
    threshold: float,
) -> None:
    fields = [
        name,
        "count",
        "positives",
        "negatives",
        "tp",
        "fp",
        "tn",
        "fn",
        "precision",
        "recall",
        "specificity",
        "f1",
        "false_positive_rate",
        "false_negative_rate",
        "accuracy",
    ]
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for value in np.unique(values):
            mask = values == value
            metrics = binary_metrics(probabilities[mask], targets[mask], threshold)
            row = {key: metrics[key] for key in fields if key != name}
            row[name] = value.item() if hasattr(value, "item") else value
            writer.writerow(row)


def generate_active_reports(
    run_dir: str | Path,
    probabilities: np.ndarray,
    targets: np.ndarray,
    metadata: dict[str, np.ndarray],
    threshold: float,
    threshold_source: str,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    probabilities, binary_targets = _binary_arrays(probabilities, targets)
    metrics = binary_metrics(probabilities, binary_targets, threshold)
    metrics["average_precision"] = average_precision(probabilities, binary_targets)
    metrics["threshold_source"] = str(threshold_source)
    (reports / "active_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    group_values = {
        "visible_window": np.asarray(metadata["visible_window"], dtype=np.int32),
        "prediction_age_ms": np.round(
            np.asarray(metadata["prediction_age_ms"], dtype=np.float32), 2
        ),
        "release_phase": np.asarray(metadata["release_phase"], dtype=np.float32),
        "player_id": np.asarray(metadata["player_id"], dtype=str),
        "dataset_id": np.asarray(metadata["dataset_id"], dtype=str),
    }
    for name, values in group_values.items():
        if len(values) != len(binary_targets):
            raise ValueError(f"Metadonnees active incoherentes pour {name}.")
        _grouped_active(
            reports / f"active_{name}.csv",
            name,
            values,
            probabilities,
            binary_targets,
            threshold,
        )
    return metrics


def generate_onset_reports(
    run_dir: str | Path,
    probabilities: np.ndarray,
    targets: np.ndarray,
    metadata: dict[str, np.ndarray],
    threshold: float,
    threshold_source: str,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)
    probabilities, binary_targets = _binary_arrays(probabilities, targets)
    metrics = binary_metrics(probabilities, binary_targets, threshold)
    metrics["average_precision"] = average_precision(
        probabilities, binary_targets
    )
    metrics["threshold_source"] = str(threshold_source)
    (reports / "onset_metrics.json").write_text(
        json.dumps(metrics, indent=2), encoding="utf-8"
    )

    group_values = {
        "visible_window": np.asarray(metadata["visible_window"], dtype=np.int32),
        "prediction_age_ms": np.round(
            np.asarray(metadata["prediction_age_ms"], dtype=np.float32), 2
        ),
        "player_id": np.asarray(metadata["player_id"], dtype=str),
        "dataset_id": np.asarray(metadata["dataset_id"], dtype=str),
    }
    for name, values in group_values.items():
        if len(values) != len(binary_targets):
            raise ValueError(f"Metadonnees onset incoherentes pour {name}.")
        _grouped_active(
            reports / f"onset_{name}.csv",
            name,
            values,
            probabilities,
            binary_targets,
            threshold,
        )
    return metrics


def _filter_rows(values: dict[str, np.ndarray], mask: np.ndarray) -> dict[str, np.ndarray]:
    return {
        name: np.asarray(array)[mask]
        for name, array in values.items()
        if len(np.asarray(array)) == len(mask)
    }


def generate_v6_reports(
    run_dir: str | Path,
    predictions: dict[str, np.ndarray],
    targets: dict[str, np.ndarray],
    metadata: dict[str, np.ndarray],
    min_pitch: int,
    active_threshold: float,
    evaluated_checkpoint: str,
    harmonic_count: int | None = None,
    onset_threshold: float | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    active_probabilities, active_targets = _binary_arrays(
        predictions["active"], targets["active"]
    )
    positive = active_targets
    if not np.any(positive):
        raise ValueError("Aucune note active dans le test V6.")

    active_metrics = generate_active_reports(
        run_dir,
        active_probabilities,
        active_targets,
        metadata,
        active_threshold,
        threshold_source="validation",
    )
    pitch_metadata = _filter_rows(metadata, positive)
    pitch_metrics = generate_pitch_reports(
        run_dir,
        np.asarray(predictions["pitch"])[positive],
        np.asarray(targets["pitch"])[positive],
        pitch_metadata,
        min_pitch,
        evaluated_checkpoint=evaluated_checkpoint,
    )

    harmonic_metrics = None
    if harmonic_count is not None:
        harmonic_metrics = generate_harmonic_reports(
            run_dir,
            _filter_rows(predictions, positive),
            _filter_rows(targets, positive),
            harmonic_count,
        )

    onset_metrics = None
    if "onset" in predictions or "onset" in targets:
        if "onset" not in predictions or "onset" not in targets:
            raise ValueError("Predictions et cibles onset doivent etre presentes ensemble.")
        if onset_threshold is None:
            raise ValueError("onset_threshold requis pour la tete onset.")
        onset_metrics = generate_onset_reports(
            run_dir,
            predictions["onset"],
            targets["onset"],
            metadata,
            onset_threshold,
            threshold_source="validation",
        )

    pitch_probabilities = np.asarray(predictions["pitch"], dtype=np.float32)
    pitch_targets = np.asarray(targets["pitch"], dtype=np.int32).reshape(-1)
    predicted_active = active_probabilities >= active_threshold
    predicted_pitch = np.argmax(pitch_probabilities, axis=1)
    pitch_correct = predicted_pitch == pitch_targets
    joint_correct = (
        (~active_targets & ~predicted_active)
        | (active_targets & predicted_active & pitch_correct)
    )
    joint = {
        "samples": int(len(active_targets)),
        "joint_frame_accuracy": float(np.mean(joint_correct)),
        "gated_correct_pitch_recall": float(
            np.sum(active_targets & predicted_active & pitch_correct)
            / max(int(np.sum(active_targets)), 1)
        ),
        "conditional_pitch_top1": topk_accuracy(
            pitch_probabilities[positive], pitch_targets[positive], 1
        ),
        "conditional_pitch_top3": topk_accuracy(
            pitch_probabilities[positive], pitch_targets[positive], 3
        ),
        "evaluated_checkpoint": str(evaluated_checkpoint),
    }
    (run_dir / "reports" / "joint_metrics.json").write_text(
        json.dumps(joint, indent=2), encoding="utf-8"
    )

    combined = {
        "active": active_metrics,
        "pitch_on_true_active": pitch_metrics,
        "joint": joint,
        "harmonics_on_true_active": harmonic_metrics,
        "onset": onset_metrics,
    }
    (run_dir / "reports" / "v6_metrics.json").write_text(
        json.dumps(combined, indent=2), encoding="utf-8"
    )
    summary = [
        "# V6.0 evaluation",
        "",
        f"- Checkpoint: {evaluated_checkpoint}",
        f"- Active threshold (validation): {active_threshold:.6f}",
        f"- Active precision: {active_metrics['precision']:.3%}",
        f"- Active recall: {active_metrics['recall']:.3%}",
        f"- Active F1: {active_metrics['f1']:.3%}",
        f"- Inactive false-positive rate: {active_metrics['false_positive_rate']:.3%}",
        f"- Pitch Top-1 on true active: {pitch_metrics['top1']:.3%}",
        f"- Pitch Top-3 on true active: {pitch_metrics['top3']:.3%}",
        f"- Joint frame accuracy: {joint['joint_frame_accuracy']:.3%}",
    ]
    if onset_metrics is not None:
        summary.extend([
            f"- Onset threshold (validation): {onset_threshold:.6f}",
            f"- Onset precision: {onset_metrics['precision']:.3%}",
            f"- Onset recall: {onset_metrics['recall']:.3%}",
            f"- Onset F1: {onset_metrics['f1']:.3%}",
        ])
    summary.append("")
    (run_dir / "reports" / "summary.md").write_text(
        "\n".join(summary), encoding="utf-8"
    )
    return combined
