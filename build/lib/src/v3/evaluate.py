from __future__ import annotations

from pathlib import Path
from typing import Dict
import csv
import json
import numpy as np


def _topk(probabilities: np.ndarray, targets: np.ndarray, k: int) -> float:
    if len(targets) == 0:
        return float("nan")
    top = np.argpartition(probabilities, -k, axis=1)[:, -k:]
    return float(np.mean(np.any(top == targets[:, None], axis=1)))


def _write_group_report(path: Path, key_name: str, keys: np.ndarray, probs: np.ndarray, targets: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow([key_name, "n", "top1", "top3"])
        for key in sorted(np.unique(keys)):
            mask = keys == key
            writer.writerow([float(key), int(mask.sum()), _topk(probs[mask], targets[mask], 1), _topk(probs[mask], targets[mask], 3)])


def generate_reports(
    run_dir: Path,
    probabilities: np.ndarray,
    targets: np.ndarray,
    metadata: Dict[str, np.ndarray],
    min_pitch: int,
    history_path: Path,
    split_report: Dict[str, object],
    make_plots: bool,
) -> Dict[str, float]:
    reports = run_dir / "reports"
    plots = run_dir / "plots"
    reports.mkdir(parents=True, exist_ok=True)
    plots.mkdir(parents=True, exist_ok=True)

    pred = np.argmax(probabilities, axis=1)
    true_midi = targets + min_pitch
    pred_midi = pred + min_pitch
    top1 = _topk(probabilities, targets, 1)
    top3 = _topk(probabilities, targets, 3)

    _write_group_report(reports / "pitch_age.csv", "prediction_age_ms", np.round(metadata["prediction_age_ms"], 2), probabilities, targets)
    _write_group_report(reports / "pitch_window.csv", "visible_window", metadata["visible_window"], probabilities, targets)
    _write_group_report(reports / "pitch_note.csv", "pitch_midi", metadata["pitch_midi"], probabilities, targets)

    classes = np.arange(min_pitch, min_pitch + probabilities.shape[1])
    matrix = np.zeros((len(classes), len(classes)), dtype=np.int64)
    for truth, guess in zip(true_midi, pred_midi):
        matrix[truth - min_pitch, guess - min_pitch] += 1
    with (reports / "confusion.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["true_midi", *classes.tolist()])
        for midi, row in zip(classes, matrix):
            writer.writerow([int(midi), *row.tolist()])

    history = np.genfromtxt(history_path, delimiter=",", names=True)
    if history.shape == ():
        history = np.array([history])
    val_top1 = np.atleast_1d(history["val_top1"])
    best_index = int(np.nanargmax(val_top1))
    best_epoch = best_index + 1

    summary = {
        "top1": top1,
        "top3": top3,
        "validation_examples": int(len(targets)),
        "best_epoch": best_epoch,
        "semitone_error_rate": float(np.mean(np.abs(pred_midi - true_midi) == 1)),
        "octave_error_rate": float(np.mean(np.abs(pred_midi - true_midi) == 12)),
    }
    (reports / "metrics.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")

    lines = [
        "# V3 Training Summary", "",
        f"- Validation examples: {len(targets)}",
        f"- Top-1: {top1:.3%}",
        f"- Top-3: {top3:.3%}",
        f"- Best epoch: {best_epoch}",
        f"- Semitone errors: {summary['semitone_error_rate']:.3%}",
        f"- Octave errors: {summary['octave_error_rate']:.3%}", "",
        "## Split", "",
        f"- Train examples: {split_report['train_examples']}",
        f"- Validation examples: {split_report['validation_examples']}",
        f"- Train-only singleton pitches: {split_report['singleton_train_only_pitches']}",
    ]
    (reports / "summary.md").write_text("\n".join(lines), encoding="utf-8")

    if make_plots:
        import matplotlib.pyplot as plt
        for metric, filename in [("loss", "loss.png"), ("top1", "top1.png"), ("top3", "top3.png")]:
            plt.figure(figsize=(8, 4))
            plt.plot(np.atleast_1d(history[metric]), label=f"train_{metric}")
            plt.plot(np.atleast_1d(history[f"val_{metric}"]), label=f"val_{metric}")
            plt.xlabel("Epoch")
            plt.ylabel(metric)
            plt.legend()
            plt.tight_layout()
            plt.savefig(plots / filename, dpi=150)
            plt.close()

        plt.figure(figsize=(8, 7))
        plt.imshow(matrix, aspect="auto", interpolation="nearest")
        plt.xlabel("Predicted class index")
        plt.ylabel("True class index")
        plt.tight_layout()
        plt.savefig(plots / "confusion.png", dpi=150)
        plt.close()

    return summary
