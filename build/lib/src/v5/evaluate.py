from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def topk_accuracy(probabilities: np.ndarray, targets: np.ndarray, k: int) -> float:
    if len(targets) == 0:
        return 0.0
    k = min(k, probabilities.shape[1])
    topk = np.argpartition(probabilities, -k, axis=1)[:, -k:]
    return float(np.mean(np.any(topk == targets[:, None], axis=1)))


def _grouped(
    output: Path,
    name: str,
    values: np.ndarray,
    probabilities: np.ndarray,
    targets: np.ndarray,
) -> None:
    with output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[name, "count", "top1", "top3"],
        )
        writer.writeheader()

        for value in np.unique(values):
            mask = values == value
            writer.writerow({
                name: value.item() if hasattr(value, "item") else value,
                "count": int(np.sum(mask)),
                "top1": topk_accuracy(probabilities[mask], targets[mask], 1),
                "top3": topk_accuracy(probabilities[mask], targets[mask], 3),
            })


def generate_reports(
    run_dir: str | Path,
    probabilities: np.ndarray,
    targets: np.ndarray,
    metadata: dict[str, np.ndarray],
    min_pitch: int,
    evaluated_checkpoint: str | None = None,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    probabilities = np.asarray(probabilities, dtype=np.float32)
    targets = np.asarray(targets, dtype=np.int32).reshape(-1)

    if len(probabilities) != len(targets):
        raise ValueError("Nombre de prédictions différent du nombre de labels.")

    ages = np.asarray(metadata["prediction_age_ms"], dtype=np.float32)
    windows = np.asarray(metadata["visible_window"], dtype=np.int32)
    midi = np.asarray(metadata["pitch_midi"], dtype=np.int32)
    players = np.asarray(metadata["player_id"], dtype=str)
    sources = np.asarray(metadata["source_id"], dtype=str)
    datasets = np.asarray(metadata.get("dataset_id", np.full(len(targets), "unknown")), dtype=str)

    for name, values in {
        "prediction_age_ms": ages,
        "visible_window": windows,
        "pitch_midi": midi,
        "player_id": players,
        "source_id": sources,
        "dataset_id": datasets,
    }.items():
        if len(values) != len(targets):
            raise ValueError(f"Métadonnées incohérentes pour {name}.")

    _grouped(reports / "prediction_age_ms.csv", "prediction_age_ms", np.round(ages, 2), probabilities, targets)
    _grouped(reports / "visible_window.csv", "visible_window", windows, probabilities, targets)
    _grouped(reports / "pitch_midi.csv", "pitch_midi", midi, probabilities, targets)
    _grouped(reports / "player_id.csv", "player_id", players, probabilities, targets)
    _grouped(reports / "source_id.csv", "source_id", sources, probabilities, targets)
    _grouped(reports / "dataset_id.csv", "dataset_id", datasets, probabilities, targets)

    predicted = np.argmax(probabilities, axis=1).astype(np.int32)
    true_midi = targets + int(min_pitch)
    predicted_midi = predicted + int(min_pitch)
    errors = predicted_midi - true_midi

    metrics = {
        "samples": int(len(targets)),
        "top1": topk_accuracy(probabilities, targets, 1),
        "top3": topk_accuracy(probabilities, targets, 3),
        "mean_absolute_semitone_error": float(np.mean(np.abs(errors))),
        "semitone_errors": int(np.sum(np.abs(errors) == 1)),
        "octave_errors": int(np.sum(np.abs(errors) == 12)),
    }
    if evaluated_checkpoint is not None:
        metrics["evaluated_checkpoint"] = str(evaluated_checkpoint)

    (reports / "metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    (reports / "summary.md").write_text(
        "\n".join([
            "# V5 evaluation",
            "",
            f"- Samples: {metrics['samples']}",
            f"- Top-1: {metrics['top1']:.3%}",
            f"- Top-3: {metrics['top3']:.3%}",
            f"- Mean absolute semitone error: {metrics['mean_absolute_semitone_error']:.3f}",
            f"- Semitone errors: {metrics['semitone_errors']}",
            f"- Octave errors: {metrics['octave_errors']}",
            *(
                [f"- Evaluated checkpoint: {evaluated_checkpoint}"]
                if evaluated_checkpoint is not None else []
            ),
            "",
        ]),
        encoding="utf-8",
    )

    return metrics


def generate_harmonic_reports(
    run_dir: str | Path,
    predictions: dict[str, np.ndarray],
    targets: dict[str, np.ndarray],
    harmonic_count: int,
) -> dict[str, Any]:
    """Evaluate auxiliary harmonics against useful constant baselines."""
    run_dir = Path(run_dir)
    reports = run_dir / "reports"
    reports.mkdir(parents=True, exist_ok=True)

    count = int(harmonic_count)
    amplitude_target = np.asarray(
        targets["harmonic_amplitude"][:, :count], dtype=np.float32
    )
    valid = np.asarray(
        targets["harmonic_amplitude"][:, count : 2 * count], dtype=np.float32
    )
    offset_target = np.asarray(
        targets["harmonic_offset_cents"][:, :count], dtype=np.float32
    )
    amplitude_prediction = np.asarray(
        predictions["harmonic_amplitude"], dtype=np.float32
    )
    offset_prediction = np.asarray(
        predictions["harmonic_offset_cents"], dtype=np.float32
    )

    expected_shape = amplitude_target.shape
    for name, values in {
        "valid": valid,
        "offset_target": offset_target,
        "amplitude_prediction": amplitude_prediction,
        "offset_prediction": offset_prediction,
    }.items():
        if values.shape != expected_shape:
            raise ValueError(
                f"Shape harmonique incoherente pour {name}: "
                f"{values.shape} != {expected_shape}"
            )

    valid_weight = np.clip(valid, 0.0, 1.0)
    valid_denominator = max(float(np.sum(valid_weight)), 1.0)
    amplitude_mae = float(
        np.sum(np.abs(amplitude_prediction - amplitude_target) * valid_weight)
        / valid_denominator
    )
    zero_amplitude_mae = float(
        np.sum(np.abs(amplitude_target) * valid_weight) / valid_denominator
    )

    offset_weight = valid_weight * np.maximum(amplitude_target, 0.0)
    offset_denominator = max(float(np.sum(offset_weight)), 1e-8)
    offset_mae_cents = float(
        np.sum(np.abs(offset_prediction - offset_target) * offset_weight)
        / offset_denominator
    )
    zero_offset_mae_cents = float(
        np.sum(np.abs(offset_target) * offset_weight) / offset_denominator
    )

    metrics = {
        "samples": int(len(amplitude_target)),
        "harmonic_count": count,
        "valid_partial_values": int(np.sum(valid_weight > 0.5)),
        "amplitude_mae": amplitude_mae,
        "zero_amplitude_baseline_mae": zero_amplitude_mae,
        "amplitude_improvement_over_zero": zero_amplitude_mae - amplitude_mae,
        "amplitude_weighted_offset_mae_cents": offset_mae_cents,
        "zero_offset_baseline_mae_cents": zero_offset_mae_cents,
        "offset_improvement_over_zero_cents": (
            zero_offset_mae_cents - offset_mae_cents
        ),
    }
    (reports / "harmonic_metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    return metrics
