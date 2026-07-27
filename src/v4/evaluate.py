from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np


def _topk_accuracy(
    probabilities: np.ndarray,
    targets: np.ndarray,
    k: int,
) -> float:
    if len(targets) == 0:
        return 0.0

    k = min(int(k), probabilities.shape[1])
    topk = np.argpartition(
        probabilities,
        kth=probabilities.shape[1] - k,
        axis=1,
    )[:, -k:]

    return float(
        np.mean(
            np.any(
                topk == targets[:, None],
                axis=1,
            )
        )
    )


def _write_grouped_report(
    output_path: Path,
    values: np.ndarray,
    probabilities: np.ndarray,
    targets: np.ndarray,
    column_name: str,
) -> None:
    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                column_name,
                "count",
                "top1",
                "top3",
            ],
        )
        writer.writeheader()

        for value in np.unique(values):
            mask = values == value
            count = int(np.sum(mask))

            if count == 0:
                continue

            writer.writerow(
                {
                    column_name: value.item()
                    if hasattr(value, "item")
                    else value,
                    "count": count,
                    "top1": _topk_accuracy(
                        probabilities[mask],
                        targets[mask],
                        1,
                    ),
                    "top3": _topk_accuracy(
                        probabilities[mask],
                        targets[mask],
                        3,
                    ),
                }
            )


def _write_confusion_matrix(
    output_path: Path,
    probabilities: np.ndarray,
    targets: np.ndarray,
    min_pitch: int,
) -> np.ndarray:
    predicted = np.argmax(
        probabilities,
        axis=1,
    ).astype(np.int32)

    class_count = probabilities.shape[1]
    matrix = np.zeros(
        (class_count, class_count),
        dtype=np.int64,
    )

    for true_class, predicted_class in zip(
        targets,
        predicted,
    ):
        if (
            0 <= true_class < class_count
            and 0 <= predicted_class < class_count
        ):
            matrix[
                int(true_class),
                int(predicted_class),
            ] += 1

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    midi_values = np.arange(
        min_pitch,
        min_pitch + class_count,
    )

    with output_path.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as handle:
        writer = csv.writer(handle)
        writer.writerow(
            ["true_midi"]
            + [str(int(value)) for value in midi_values]
        )

        for midi_value, row in zip(
            midi_values,
            matrix,
        ):
            writer.writerow(
                [int(midi_value)]
                + [int(value) for value in row]
            )

    return matrix


def generate_reports(
    run_dir: str | Path,
    probabilities: np.ndarray,
    targets: np.ndarray,
    metadata: dict[str, np.ndarray],
    min_pitch: int,
) -> dict[str, Any]:
    """Generate V4 evaluation reports.

    Parameters
    ----------
    run_dir:
        Run output directory.
    probabilities:
        Model softmax predictions with shape (N, classes).
    targets:
        Zero-based pitch classes with shape (N,).
    metadata:
        Dictionary containing prediction_age_ms, visible_window,
        pitch_midi, player_id and optionally source_id/note_id/channel.
    min_pitch:
        MIDI pitch represented by class zero.
    """

    run_dir = Path(run_dir)
    reports_dir = run_dir / "reports"
    reports_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    probabilities = np.asarray(
        probabilities,
        dtype=np.float32,
    )
    targets = np.asarray(
        targets,
        dtype=np.int32,
    ).reshape(-1)

    if probabilities.ndim != 2:
        raise ValueError(
            "probabilities doit avoir la forme (N, classes)."
        )

    if len(probabilities) != len(targets):
        raise ValueError(
            "Nombre de probabilités et de labels différent : "
            f"{len(probabilities)} != {len(targets)}"
        )

    required_metadata = {
        "prediction_age_ms",
        "visible_window",
        "pitch_midi",
        "player_id",
    }

    missing = sorted(
        required_metadata - set(metadata.keys())
    )

    if missing:
        raise ValueError(
            f"Métadonnées manquantes : {missing}"
        )

    ages = np.asarray(
        metadata["prediction_age_ms"],
        dtype=np.float32,
    ).reshape(-1)

    windows = np.asarray(
        metadata["visible_window"],
        dtype=np.int32,
    ).reshape(-1)

    midi = np.asarray(
        metadata["pitch_midi"],
        dtype=np.int32,
    ).reshape(-1)

    players = np.asarray(
        metadata["player_id"],
        dtype=str,
    ).reshape(-1)

    for name, values in {
        "prediction_age_ms": ages,
        "visible_window": windows,
        "pitch_midi": midi,
        "player_id": players,
    }.items():
        if len(values) != len(targets):
            raise ValueError(
                f"Longueur invalide pour {name}: "
                f"{len(values)} != {len(targets)}"
            )

    top1 = _topk_accuracy(
        probabilities,
        targets,
        1,
    )

    top3 = _topk_accuracy(
        probabilities,
        targets,
        3,
    )

    _write_grouped_report(
        reports_dir / "prediction_age_ms.csv",
        np.round(ages, 2),
        probabilities,
        targets,
        "prediction_age_ms",
    )

    _write_grouped_report(
        reports_dir / "visible_window.csv",
        windows,
        probabilities,
        targets,
        "visible_window",
    )

    _write_grouped_report(
        reports_dir / "pitch_midi.csv",
        midi,
        probabilities,
        targets,
        "pitch_midi",
    )

    _write_grouped_report(
        reports_dir / "player_id.csv",
        players,
        probabilities,
        targets,
        "player_id",
    )

    if "source_id" in metadata:
        source_ids = np.asarray(
            metadata["source_id"],
            dtype=str,
        ).reshape(-1)

        if len(source_ids) == len(targets):
            _write_grouped_report(
                reports_dir / "source_id.csv",
                source_ids,
                probabilities,
                targets,
                "source_id",
            )

    confusion = _write_confusion_matrix(
        reports_dir / "confusion.csv",
        probabilities,
        targets,
        int(min_pitch),
    )

    predicted = np.argmax(
        probabilities,
        axis=1,
    ).astype(np.int32)

    true_midi = targets + int(min_pitch)
    predicted_midi = predicted + int(min_pitch)
    errors = predicted_midi - true_midi

    metrics: dict[str, Any] = {
        "samples": int(len(targets)),
        "classes": int(probabilities.shape[1]),
        "min_pitch": int(min_pitch),
        "max_pitch": int(
            min_pitch + probabilities.shape[1] - 1
        ),
        "top1": float(top1),
        "top3": float(top3),
        "mean_absolute_semitone_error": float(
            np.mean(np.abs(errors))
        ) if len(errors) else 0.0,
        "semitone_errors": int(
            np.sum(np.abs(errors) == 1)
        ),
        "octave_errors": int(
            np.sum(np.abs(errors) == 12)
        ),
    }

    (reports_dir / "metrics.json").write_text(
        json.dumps(
            metrics,
            indent=2,
        ),
        encoding="utf-8",
    )

    summary = "\n".join(
        [
            "# V4 evaluation",
            "",
            f"- Samples: {metrics['samples']}",
            f"- Pitch classes: {metrics['classes']}",
            (
                f"- MIDI range: "
                f"{metrics['min_pitch']}–{metrics['max_pitch']}"
            ),
            f"- Top-1: {metrics['top1']:.3%}",
            f"- Top-3: {metrics['top3']:.3%}",
            (
                "- Mean absolute semitone error: "
                f"{metrics['mean_absolute_semitone_error']:.3f}"
            ),
            f"- Semitone errors: {metrics['semitone_errors']}",
            f"- Octave errors: {metrics['octave_errors']}",
            "",
        ]
    )

    (reports_dir / "summary.md").write_text(
        summary,
        encoding="utf-8",
    )

    return metrics