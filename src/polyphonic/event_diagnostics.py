"""Deterministic root-cause diagnostics for note-event errors.

The aggregate F1 score cannot distinguish a hallucinated pitch from a real
note that was split by an early NoteOff and restarted.  These diagnostics are
pure functions so the exact same predicted intervals can be compared before
and after a decoder change without running the model again.
"""

from __future__ import annotations

from collections import Counter
from typing import Protocol, Sequence

import numpy as np


class NoteLike(Protocol):
    pitch: int
    start_s: float
    end_s: float


def _overlap_s(left: NoteLike, right: NoteLike) -> float:
    return max(0.0, min(left.end_s, right.end_s) - max(left.start_s, right.start_s))


def diagnose_note_errors(
    reference: Sequence[NoteLike],
    estimated: Sequence[NoteLike],
    matches: Sequence[tuple[int, int]],
) -> dict[str, object]:
    """Classify false positives, fragmentation and timing on fixed matches."""
    matched_reference = {int(pair[0]) for pair in matches}
    matched_estimated = {int(pair[1]) for pair in matches}
    false_positive_indices = [
        index for index in range(len(estimated)) if index not in matched_estimated
    ]
    missing_indices = [
        index for index in range(len(reference)) if index not in matched_reference
    ]

    interval_counts: Counter[int] = Counter()
    false_positive_without_active_reference = 0
    same_pitch_during_reference = 0
    for estimated_index in false_positive_indices:
        prediction = estimated[estimated_index]
        active_truth = [
            note for note in reference
            if note.start_s <= prediction.start_s < note.end_s
        ]
        if not active_truth:
            false_positive_without_active_reference += 1
            continue
        closest = min(
            active_truth,
            key=lambda note: abs(int(prediction.pitch) - int(note.pitch)),
        )
        interval = int(prediction.pitch) - int(closest.pitch)
        interval_counts[interval] += 1
        if interval == 0:
            same_pitch_during_reference += 1

    fragments_per_reference: list[int] = []
    fragmented_references = 0
    excess_fragments = 0
    for truth in reference:
        overlapping = sum(
            int(prediction.pitch) == int(truth.pitch)
            and _overlap_s(truth, prediction) > 0.0
            for prediction in estimated
        )
        fragments_per_reference.append(overlapping)
        if overlapping > 1:
            fragmented_references += 1
            excess_fragments += overlapping - 1

    onset_error_ms = np.asarray([
        (estimated[estimated_index].start_s - reference[reference_index].start_s)
        * 1000.0
        for reference_index, estimated_index in matches
    ], dtype=np.float64)
    offset_error_ms = np.asarray([
        (estimated[estimated_index].end_s - reference[reference_index].end_s)
        * 1000.0
        for reference_index, estimated_index in matches
    ], dtype=np.float64)

    # Rounded MIDI intervals for partials 3 through 8 above a fundamental.
    harmonic_intervals = {7, 12, 19, 24, 28, 31, 34, 36}
    harmonic_false_positives = sum(
        count for interval, count in interval_counts.items()
        if interval in harmonic_intervals
    )

    def timing(values: np.ndarray) -> dict[str, float]:
        if not len(values):
            return {"median_ms": 0.0, "p95_absolute_ms": 0.0}
        return {
            "median_ms": float(np.median(values)),
            "p95_absolute_ms": float(np.percentile(np.abs(values), 95)),
        }

    return {
        "false_positive_notes": len(false_positive_indices),
        "missing_notes": len(missing_indices),
        "false_positive_without_active_reference": (
            false_positive_without_active_reference
        ),
        "same_pitch_during_reference": same_pitch_during_reference,
        "harmonic_interval_false_positives": harmonic_false_positives,
        "false_positive_interval_counts": {
            str(interval): count
            for interval, count in sorted(interval_counts.items())
        },
        "fragmented_reference_notes": fragmented_references,
        "excess_fragments": excess_fragments,
        "maximum_fragments_for_one_reference": max(fragments_per_reference, default=0),
        "matched_onset_timing": timing(onset_error_ms),
        "matched_offset_timing": timing(offset_error_ms),
    }
