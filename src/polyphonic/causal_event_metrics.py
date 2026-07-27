"""Strictly causal NoteOn metrics for live polyphonic transcription.

The matcher in this module never gives a prediction credit for a future
reference onset.  A prediction is eligible only for a same-pitch reference
that has already happened, and every event can be used at most once.

The module is intentionally independent from TensorFlow, the decoder and the
dataset loaders.  It can therefore score live traces, offline transcriptions
or exported runtimes with the exact same policy.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from math import ceil, floor, isfinite
from numbers import Integral
from typing import Mapping, Sequence


DEFAULT_RECALL_DEADLINES_MS = (12.0, 18.0, 24.0, 35.0, 46.0)
DEFAULT_MAX_LATENCY_MS = 250.0
DEFAULT_SAME_PITCH_GAP_MS = 90.0

_TIME_EPSILON_S = 1e-12
_MILLISECOND_EPSILON = 1e-9
_CONTEXT_NAMES = ("monophonic", "polyphonic", "same_pitch_close")
_CONTEXT_ALIASES = {
    "mono": "monophonic",
    "monophonic": "monophonic",
    "poly": "polyphonic",
    "polyphonic": "polyphonic",
    "same_pitch": "same_pitch_close",
    "same_pitch_close": "same_pitch_close",
}


def _validate_pitch(value: int, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, Integral):
        raise TypeError(f"{field_name} must be an integer MIDI pitch.")
    if not 0 <= int(value) <= 127:
        raise ValueError(f"{field_name} must be between 0 and 127.")


def _finite_float(value: float, field_name: str) -> float:
    result = float(value)
    if not isfinite(result):
        raise ValueError(f"{field_name} must be finite.")
    return result


def _validate_nonnegative(value: float, field_name: str) -> float:
    result = _finite_float(value, field_name)
    if result < 0.0:
        raise ValueError(f"{field_name} must be non-negative.")
    return result


def _validate_optional_nonnegative(
    value: float | None,
    field_name: str,
) -> None:
    if value is not None:
        _validate_nonnegative(value, field_name)


def _ratio(numerator: int, denominator: int) -> float | None:
    return float(numerator / denominator) if denominator else None


def _percentile(
    values: Sequence[float],
    percentile: float,
) -> float | None:
    """Return the deterministic linear percentile used by NumPy by default."""
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    position = (len(ordered) - 1) * float(percentile) / 100.0
    lower = floor(position)
    upper = ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _deadline_key(deadline_ms: float) -> str:
    value = float(deadline_ms)
    if value.is_integer():
        return str(int(value))
    return format(value, ".12g")


def _normalise_deadlines(
    deadlines_ms: Sequence[float],
    *,
    max_latency_ms: float,
) -> tuple[float, ...]:
    maximum = _validate_nonnegative(max_latency_ms, "max_latency_ms")
    values = set(DEFAULT_RECALL_DEADLINES_MS)
    for index, raw_value in enumerate(deadlines_ms):
        value = _validate_nonnegative(
            raw_value, f"recall_deadlines_ms[{index}]"
        )
        values.add(value)
    result = tuple(sorted(values))
    if result and result[-1] > maximum + _MILLISECOND_EPSILON:
        raise ValueError(
            "Every recall deadline must be no greater than max_latency_ms."
        )
    return result


@dataclass(frozen=True)
class ReferenceNote:
    """A ground-truth note interval.

    ``end_s`` is used only to determine monophonic/polyphonic and close
    same-pitch contexts.  Matching itself uses ``pitch`` and ``start_s`` only.
    """

    pitch: int
    start_s: float
    end_s: float

    def __post_init__(self) -> None:
        _validate_pitch(self.pitch, "pitch")
        start = _finite_float(self.start_s, "start_s")
        end = _finite_float(self.end_s, "end_s")
        if start < 0.0:
            raise ValueError("start_s must be non-negative.")
        if end <= start:
            raise ValueError("end_s must be greater than start_s.")


@dataclass(frozen=True)
class NoteOnPrediction:
    """A predicted MIDI NoteOn at an observable causal time."""

    pitch: int
    time_s: float

    def __post_init__(self) -> None:
        _validate_pitch(self.pitch, "pitch")
        time_s = _finite_float(self.time_s, "time_s")
        if time_s < 0.0:
            raise ValueError("time_s must be non-negative.")


@dataclass(frozen=True)
class ClipNoteOnData:
    """All NoteOn inputs for one independently matched evaluation clip."""

    clip_id: str
    corpus_id: str
    duration_s: float
    reference: Sequence[ReferenceNote]
    predictions: Sequence[NoteOnPrediction]

    def __post_init__(self) -> None:
        if not isinstance(self.clip_id, str) or not self.clip_id.strip():
            raise ValueError("clip_id must be a non-empty string.")
        if not isinstance(self.corpus_id, str) or not self.corpus_id.strip():
            raise ValueError("corpus_id must be a non-empty string.")
        duration = _finite_float(self.duration_s, "duration_s")
        if duration <= 0.0:
            raise ValueError("duration_s must be positive.")
        references = tuple(self.reference)
        predictions = tuple(self.predictions)
        if not all(isinstance(item, ReferenceNote) for item in references):
            raise TypeError("reference must contain only ReferenceNote values.")
        if not all(isinstance(item, NoteOnPrediction) for item in predictions):
            raise TypeError(
                "predictions must contain only NoteOnPrediction values."
            )
        if any(item.start_s > duration + _TIME_EPSILON_S for item in references):
            raise ValueError("A reference onset is outside the clip duration.")
        if any(item.time_s > duration + _TIME_EPSILON_S for item in predictions):
            raise ValueError("A predicted onset is outside the clip duration.")
        object.__setattr__(self, "reference", references)
        object.__setattr__(self, "predictions", predictions)


@dataclass(frozen=True)
class CausalNoteOnMatch:
    reference_index: int
    prediction_index: int
    latency_ms: float


@dataclass(frozen=True)
class CausalNoteOnResult:
    matches: tuple[CausalNoteOnMatch, ...]
    missed_reference_indices: tuple[int, ...]
    false_prediction_indices: tuple[int, ...]

    def latency_by_reference(self) -> dict[int, float]:
        return {
            match.reference_index: match.latency_ms for match in self.matches
        }


def match_causal_note_ons(
    reference: Sequence[ReferenceNote],
    predictions: Sequence[NoteOnPrediction],
    *,
    max_latency_ms: float = DEFAULT_MAX_LATENCY_MS,
) -> CausalNoteOnResult:
    """Match each prediction to the latest eligible same-pitch reference.

    Predictions are processed in chronological order.  Only references with
    ``reference.start_s <= prediction.time_s`` are eligible, making negative
    latency impossible.  When several same-pitch references are pending, the
    latest one wins and older pending occurrences are left missed.  This is
    important for rapid same-pitch retriggers: a prompt second attack must not
    be credited to an older missed attack.
    """

    maximum = _validate_nonnegative(max_latency_ms, "max_latency_ms")
    references = tuple(reference)
    predicted = tuple(predictions)
    if not all(isinstance(item, ReferenceNote) for item in references):
        raise TypeError("reference must contain only ReferenceNote values.")
    if not all(isinstance(item, NoteOnPrediction) for item in predicted):
        raise TypeError(
            "predictions must contain only NoteOnPrediction values."
        )

    ordered_references = sorted(
        enumerate(references),
        key=lambda item: (
            item[1].start_s,
            int(item[1].pitch),
            item[0],
        ),
    )
    ordered_predictions = sorted(
        enumerate(predicted),
        key=lambda item: (
            item[1].time_s,
            int(item[1].pitch),
            item[0],
        ),
    )
    pending_by_pitch: dict[int, list[tuple[int, ReferenceNote]]] = {}
    unmatched_references = set(range(len(references)))
    matches: list[CausalNoteOnMatch] = []
    false_predictions: list[int] = []
    reference_cursor = 0
    maximum_s = maximum / 1000.0

    for prediction_index, prediction in ordered_predictions:
        while (
            reference_cursor < len(ordered_references)
            and ordered_references[reference_cursor][1].start_s
            <= prediction.time_s
        ):
            reference_index, note = ordered_references[reference_cursor]
            pending_by_pitch.setdefault(int(note.pitch), []).append(
                (reference_index, note)
            )
            reference_cursor += 1

        pitch_pending = pending_by_pitch.setdefault(
            int(prediction.pitch), []
        )
        pitch_pending[:] = [
            item
            for item in pitch_pending
            if (
                prediction.time_s - item[1].start_s
                <= maximum_s + _TIME_EPSILON_S
            )
        ]
        if not pitch_pending:
            false_predictions.append(prediction_index)
            continue

        reference_index, note = pitch_pending[-1]
        # Older same-pitch onsets cannot be recovered after a newer one was
        # observed.  Clearing them prevents out-of-order retrigger credit.
        pitch_pending.clear()
        latency_ms = (prediction.time_s - note.start_s) * 1000.0
        if (
            latency_ms < -_MILLISECOND_EPSILON
            or latency_ms > maximum + _MILLISECOND_EPSILON
        ):
            raise AssertionError(
                "The causal matcher selected an inadmissible latency."
            )
        latency_ms = max(0.0, latency_ms)
        unmatched_references.discard(reference_index)
        matches.append(
            CausalNoteOnMatch(
                reference_index=reference_index,
                prediction_index=prediction_index,
                latency_ms=latency_ms,
            )
        )

    return CausalNoteOnResult(
        matches=tuple(matches),
        missed_reference_indices=tuple(sorted(unmatched_references)),
        false_prediction_indices=tuple(sorted(false_predictions)),
    )


def reference_context_masks(
    reference: Sequence[ReferenceNote],
    *,
    same_pitch_gap_ms: float = DEFAULT_SAME_PITCH_GAP_MS,
) -> dict[str, tuple[bool, ...]]:
    """Return mutually useful onset contexts in original reference order."""

    gap_s = (
        _validate_nonnegative(same_pitch_gap_ms, "same_pitch_gap_ms")
        / 1000.0
    )
    references = tuple(reference)
    if not all(isinstance(item, ReferenceNote) for item in references):
        raise TypeError("reference must contain only ReferenceNote values.")

    polyphonic: list[bool] = []
    same_pitch_close: list[bool] = []
    for index, note in enumerate(references):
        is_polyphonic = any(
            other_index != index
            and other.start_s <= note.start_s + _TIME_EPSILON_S
            and note.start_s < other.end_s - _TIME_EPSILON_S
            for other_index, other in enumerate(references)
        )
        polyphonic.append(is_polyphonic)

        earlier_same_pitch = [
            (other_index, other)
            for other_index, other in enumerate(references)
            if (
                other_index != index
                and int(other.pitch) == int(note.pitch)
                and other.start_s < note.start_s - _TIME_EPSILON_S
            )
        ]
        previous = (
            max(
                earlier_same_pitch,
                key=lambda item: (item[1].start_s, -item[0]),
            )[1]
            if earlier_same_pitch
            else None
        )
        same_pitch_close.append(
            bool(
                previous is not None
                and note.start_s - previous.end_s
                <= gap_s + _TIME_EPSILON_S
            )
        )

    return {
        "monophonic": tuple(not value for value in polyphonic),
        "polyphonic": tuple(polyphonic),
        "same_pitch_close": tuple(same_pitch_close),
    }


@dataclass
class _MetricAccumulator:
    duration_s: float
    reference_noteons: int
    predicted_noteons: int
    matched_latencies_ms: list[float]
    missed_noteons: int
    false_noteons: int
    context_reference_noteons: dict[str, int]
    context_latencies_ms: dict[str, list[float]]
    octave_up_false_noteons: int
    octave_down_false_noteons: int


def _classify_octave_false_predictions(
    reference: Sequence[ReferenceNote],
    predictions: Sequence[NoteOnPrediction],
    false_prediction_indices: Sequence[int],
    *,
    max_latency_ms: float,
) -> tuple[int, int]:
    octave_up = 0
    octave_down = 0
    maximum_s = max_latency_ms / 1000.0
    for prediction_index in false_prediction_indices:
        prediction = predictions[prediction_index]
        candidates: list[tuple[float, int, int]] = []
        for reference_index, note in enumerate(reference):
            age_s = prediction.time_s - note.start_s
            pitch_delta = int(prediction.pitch) - int(note.pitch)
            if (
                age_s >= 0.0
                and age_s <= maximum_s + _TIME_EPSILON_S
                and abs(pitch_delta) == 12
            ):
                candidates.append(
                    (note.start_s, -reference_index, pitch_delta)
                )
        if not candidates:
            continue
        # Classify each false prediction once, against the latest causal
        # octave-related onset.  The index tie-break keeps the result stable.
        pitch_delta = max(candidates)[2]
        if pitch_delta > 0:
            octave_up += 1
        else:
            octave_down += 1
    return octave_up, octave_down


def _build_accumulator(
    reference: Sequence[ReferenceNote],
    predictions: Sequence[NoteOnPrediction],
    result: CausalNoteOnResult,
    *,
    duration_s: float,
    max_latency_ms: float,
    same_pitch_gap_ms: float,
) -> _MetricAccumulator:
    contexts = reference_context_masks(
        reference, same_pitch_gap_ms=same_pitch_gap_ms
    )
    latency_by_reference = result.latency_by_reference()
    context_latencies = {
        name: [
            latency_by_reference[index]
            for index, enabled in enumerate(mask)
            if enabled and index in latency_by_reference
        ]
        for name, mask in contexts.items()
    }
    octave_up, octave_down = _classify_octave_false_predictions(
        reference,
        predictions,
        result.false_prediction_indices,
        max_latency_ms=max_latency_ms,
    )
    return _MetricAccumulator(
        duration_s=float(duration_s),
        reference_noteons=len(reference),
        predicted_noteons=len(predictions),
        matched_latencies_ms=[
            match.latency_ms for match in result.matches
        ],
        missed_noteons=len(result.missed_reference_indices),
        false_noteons=len(result.false_prediction_indices),
        context_reference_noteons={
            name: sum(mask) for name, mask in contexts.items()
        },
        context_latencies_ms=context_latencies,
        octave_up_false_noteons=octave_up,
        octave_down_false_noteons=octave_down,
    )


def _recall_at(
    latencies_ms: Sequence[float],
    reference_count: int,
    deadlines_ms: Sequence[float],
) -> tuple[dict[str, float | None], dict[str, int]]:
    detected = {
        _deadline_key(deadline): sum(
            latency <= deadline + _MILLISECOND_EPSILON
            for latency in latencies_ms
        )
        for deadline in deadlines_ms
    }
    recall = {
        key: _ratio(count, reference_count)
        for key, count in detected.items()
    }
    return recall, detected


def _summary_from_accumulator(
    accumulator: _MetricAccumulator,
    deadlines_ms: Sequence[float],
) -> dict[str, object]:
    recall_at, detected_at = _recall_at(
        accumulator.matched_latencies_ms,
        accumulator.reference_noteons,
        deadlines_ms,
    )
    contexts: dict[str, dict[str, object]] = {}
    for name in _CONTEXT_NAMES:
        reference_count = accumulator.context_reference_noteons[name]
        latencies = accumulator.context_latencies_ms[name]
        context_recall, context_detected = _recall_at(
            latencies, reference_count, deadlines_ms
        )
        contexts[name] = {
            "reference_noteons": reference_count,
            "matched_noteons": len(latencies),
            "detected_at_ms": context_detected,
            "recall_at_ms": context_recall,
            "latency_p50_ms": _percentile(latencies, 50.0),
            "latency_p90_ms": _percentile(latencies, 90.0),
        }

    octave_errors = (
        accumulator.octave_up_false_noteons
        + accumulator.octave_down_false_noteons
    )
    minutes = accumulator.duration_s / 60.0
    summary: dict[str, object] = {
        "duration_s": accumulator.duration_s,
        "reference_noteons": accumulator.reference_noteons,
        "predicted_noteons": accumulator.predicted_noteons,
        "matched_noteons": len(accumulator.matched_latencies_ms),
        "missed_noteons": accumulator.missed_noteons,
        "false_noteons": accumulator.false_noteons,
        "precision": _ratio(
            len(accumulator.matched_latencies_ms),
            accumulator.predicted_noteons,
        ),
        "recall_within_max_latency": _ratio(
            len(accumulator.matched_latencies_ms),
            accumulator.reference_noteons,
        ),
        "false_noteons_per_min": (
            accumulator.false_noteons / minutes if minutes > 0.0 else None
        ),
        "detected_at_ms": detected_at,
        "recall_at_ms": recall_at,
        "latency_p50_ms": _percentile(
            accumulator.matched_latencies_ms, 50.0
        ),
        "latency_p90_ms": _percentile(
            accumulator.matched_latencies_ms, 90.0
        ),
        "contexts": contexts,
        "octave_error_false_noteons": octave_errors,
        "octave_up_false_noteons": accumulator.octave_up_false_noteons,
        "octave_down_false_noteons": accumulator.octave_down_false_noteons,
        "octave_error_rate_of_false_noteons": _ratio(
            octave_errors, accumulator.false_noteons
        ),
        "octave_error_noteons_per_min": (
            octave_errors / minutes if minutes > 0.0 else None
        ),
    }
    # Stable flat fields are convenient in experiment tables while the nested
    # representation remains the authoritative, extensible form.
    for deadline in deadlines_ms:
        key = _deadline_key(deadline)
        summary[f"recall_at_{key}ms"] = recall_at[key]
    for name in _CONTEXT_NAMES:
        summary[f"{name}_reference_noteons"] = contexts[name][
            "reference_noteons"
        ]
        summary[f"{name}_recall_at_24ms"] = contexts[name][
            "recall_at_ms"
        ]["24"]
    return summary


def causal_metrics_summary(
    reference: Sequence[ReferenceNote],
    predictions: Sequence[NoteOnPrediction],
    *,
    duration_s: float,
    max_latency_ms: float = DEFAULT_MAX_LATENCY_MS,
    recall_deadlines_ms: Sequence[float] = DEFAULT_RECALL_DEADLINES_MS,
    same_pitch_gap_ms: float = DEFAULT_SAME_PITCH_GAP_MS,
) -> tuple[dict[str, object], CausalNoteOnResult]:
    """Score one clip and return both JSON-ready metrics and exact matches."""

    duration = _finite_float(duration_s, "duration_s")
    if duration <= 0.0:
        raise ValueError("duration_s must be positive.")
    maximum = _validate_nonnegative(max_latency_ms, "max_latency_ms")
    deadlines = _normalise_deadlines(
        recall_deadlines_ms, max_latency_ms=maximum
    )
    gap = _validate_nonnegative(same_pitch_gap_ms, "same_pitch_gap_ms")
    references = tuple(reference)
    predicted = tuple(predictions)
    if any(item.start_s > duration + _TIME_EPSILON_S for item in references):
        raise ValueError("A reference onset is outside duration_s.")
    if any(item.time_s > duration + _TIME_EPSILON_S for item in predicted):
        raise ValueError("A predicted onset is outside duration_s.")
    result = match_causal_note_ons(
        references, predicted, max_latency_ms=maximum
    )
    accumulator = _build_accumulator(
        references,
        predicted,
        result,
        duration_s=duration,
        max_latency_ms=maximum,
        same_pitch_gap_ms=gap,
    )
    return _summary_from_accumulator(accumulator, deadlines), result


def compute_causal_note_on_metrics(
    reference: Sequence[ReferenceNote],
    predictions: Sequence[NoteOnPrediction],
    *,
    duration_s: float,
    max_latency_ms: float = DEFAULT_MAX_LATENCY_MS,
    recall_deadlines_ms: Sequence[float] = DEFAULT_RECALL_DEADLINES_MS,
    same_pitch_gap_ms: float = DEFAULT_SAME_PITCH_GAP_MS,
) -> dict[str, object]:
    """Return only the JSON-ready metrics for one clip."""

    summary, _ = causal_metrics_summary(
        reference,
        predictions,
        duration_s=duration_s,
        max_latency_ms=max_latency_ms,
        recall_deadlines_ms=recall_deadlines_ms,
        same_pitch_gap_ms=same_pitch_gap_ms,
    )
    return summary


def _merge_accumulators(
    accumulators: Sequence[_MetricAccumulator],
) -> _MetricAccumulator:
    return _MetricAccumulator(
        duration_s=sum(item.duration_s for item in accumulators),
        reference_noteons=sum(
            item.reference_noteons for item in accumulators
        ),
        predicted_noteons=sum(
            item.predicted_noteons for item in accumulators
        ),
        matched_latencies_ms=[
            latency
            for item in accumulators
            for latency in item.matched_latencies_ms
        ],
        missed_noteons=sum(item.missed_noteons for item in accumulators),
        false_noteons=sum(item.false_noteons for item in accumulators),
        context_reference_noteons={
            name: sum(
                item.context_reference_noteons[name]
                for item in accumulators
            )
            for name in _CONTEXT_NAMES
        },
        context_latencies_ms={
            name: [
                latency
                for item in accumulators
                for latency in item.context_latencies_ms[name]
            ]
            for name in _CONTEXT_NAMES
        },
        octave_up_false_noteons=sum(
            item.octave_up_false_noteons for item in accumulators
        ),
        octave_down_false_noteons=sum(
            item.octave_down_false_noteons for item in accumulators
        ),
    )


def _minimum_recall_row(
    rows: Sequence[Mapping[str, object]],
    deadline_key: str,
    *,
    clip_scope: bool,
) -> dict[str, object] | None:
    supported: list[Mapping[str, object]] = []
    for row in rows:
        value = row["recall_at_ms"][deadline_key]  # type: ignore[index]
        if value is not None:
            supported.append(row)
    if not supported:
        return None
    if clip_scope:
        worst = min(
            supported,
            key=lambda row: (
                float(row["recall_at_ms"][deadline_key]),  # type: ignore[index]
                str(row["corpus_id"]),
                str(row["clip_id"]),
            ),
        )
        return {
            "value": worst["recall_at_ms"][deadline_key],  # type: ignore[index]
            "corpus_id": worst["corpus_id"],
            "clip_id": worst["clip_id"],
        }
    worst = min(
        supported,
        key=lambda row: (
            float(row["recall_at_ms"][deadline_key]),  # type: ignore[index]
            str(row["corpus_id"]),
        ),
    )
    return {
        "value": worst["recall_at_ms"][deadline_key],  # type: ignore[index]
        "corpus_id": worst["corpus_id"],
    }


def _maximum_false_rate_row(
    rows: Sequence[Mapping[str, object]],
    *,
    clip_scope: bool,
) -> dict[str, object] | None:
    supported = [
        row for row in rows if row["false_noteons_per_min"] is not None
    ]
    if not supported:
        return None
    if clip_scope:
        worst = min(
            supported,
            key=lambda row: (
                -float(row["false_noteons_per_min"]),
                str(row["corpus_id"]),
                str(row["clip_id"]),
            ),
        )
        return {
            "value": worst["false_noteons_per_min"],
            "corpus_id": worst["corpus_id"],
            "clip_id": worst["clip_id"],
        }
    worst = min(
        supported,
        key=lambda row: (
            -float(row["false_noteons_per_min"]),
            str(row["corpus_id"]),
        ),
    )
    return {
        "value": worst["false_noteons_per_min"],
        "corpus_id": worst["corpus_id"],
    }


def _build_worst_summary(
    per_clip: Sequence[Mapping[str, object]],
    by_corpus: Mapping[str, Mapping[str, object]],
    deadlines_ms: Sequence[float],
) -> dict[str, object]:
    corpus_rows = [
        {"corpus_id": corpus_id, **metrics}
        for corpus_id, metrics in sorted(by_corpus.items())
    ]
    return {
        "clip": {
            "recall_at_ms": {
                _deadline_key(deadline): _minimum_recall_row(
                    per_clip, _deadline_key(deadline), clip_scope=True
                )
                for deadline in deadlines_ms
            },
            "false_noteons_per_min": _maximum_false_rate_row(
                per_clip, clip_scope=True
            ),
        },
        "corpus": {
            "recall_at_ms": {
                _deadline_key(deadline): _minimum_recall_row(
                    corpus_rows, _deadline_key(deadline), clip_scope=False
                )
                for deadline in deadlines_ms
            },
            "false_noteons_per_min": _maximum_false_rate_row(
                corpus_rows, clip_scope=False
            ),
        },
    }


def _normalise_ratio_thresholds(
    values: Mapping[float, float],
    field_name: str,
) -> dict[float, float]:
    result: dict[float, float] = {}
    for raw_deadline, raw_threshold in values.items():
        deadline = _validate_nonnegative(
            float(raw_deadline), f"{field_name} deadline"
        )
        threshold = _finite_float(
            raw_threshold, f"{field_name}[{raw_deadline!r}]"
        )
        if not 0.0 <= threshold <= 1.0:
            raise ValueError(
                f"{field_name} thresholds must be between 0 and 1."
            )
        if deadline in result:
            raise ValueError(f"{field_name} has a duplicate deadline.")
        result[deadline] = threshold
    return dict(sorted(result.items()))


@dataclass(frozen=True)
class CausalMetricGate:
    """Configurable promotion gate for aggregate and tail performance.

    Any configured check with no supporting reference events fails instead of
    silently passing.  Worst-clip and worst-corpus thresholds prevent a strong
    average or a long corpus from hiding a local regression.
    """

    minimum_recall_at_ms: Mapping[float, float] = field(
        default_factory=dict
    )
    maximum_latency_p50_ms: float | None = None
    maximum_latency_p90_ms: float | None = None
    maximum_false_noteons_per_min: float | None = None
    minimum_context_recall_at_ms: Mapping[
        str, Mapping[float, float]
    ] = field(default_factory=dict)
    maximum_octave_error_rate: float | None = None
    maximum_octave_error_noteons_per_min: float | None = None
    minimum_worst_clip_recall_at_ms: Mapping[float, float] = field(
        default_factory=dict
    )
    minimum_worst_corpus_recall_at_ms: Mapping[float, float] = field(
        default_factory=dict
    )
    maximum_worst_clip_false_noteons_per_min: float | None = None
    maximum_worst_corpus_false_noteons_per_min: float | None = None

    def __post_init__(self) -> None:
        _normalise_ratio_thresholds(
            self.minimum_recall_at_ms, "minimum_recall_at_ms"
        )
        _normalise_ratio_thresholds(
            self.minimum_worst_clip_recall_at_ms,
            "minimum_worst_clip_recall_at_ms",
        )
        _normalise_ratio_thresholds(
            self.minimum_worst_corpus_recall_at_ms,
            "minimum_worst_corpus_recall_at_ms",
        )
        for raw_name, thresholds in self.minimum_context_recall_at_ms.items():
            name = str(raw_name)
            if name not in _CONTEXT_ALIASES:
                raise ValueError(f"Unknown NoteOn context: {name!r}.")
            _normalise_ratio_thresholds(
                thresholds, f"minimum_context_recall_at_ms[{name!r}]"
            )
        for field_name in (
            "maximum_latency_p50_ms",
            "maximum_latency_p90_ms",
            "maximum_false_noteons_per_min",
            "maximum_octave_error_noteons_per_min",
            "maximum_worst_clip_false_noteons_per_min",
            "maximum_worst_corpus_false_noteons_per_min",
        ):
            _validate_optional_nonnegative(
                getattr(self, field_name), field_name
            )
        if self.maximum_octave_error_rate is not None:
            rate = _finite_float(
                self.maximum_octave_error_rate,
                "maximum_octave_error_rate",
            )
            if not 0.0 <= rate <= 1.0:
                raise ValueError(
                    "maximum_octave_error_rate must be between 0 and 1."
                )

    def required_deadlines_ms(self) -> tuple[float, ...]:
        values = set(self.minimum_recall_at_ms)
        values.update(self.minimum_worst_clip_recall_at_ms)
        values.update(self.minimum_worst_corpus_recall_at_ms)
        for thresholds in self.minimum_context_recall_at_ms.values():
            values.update(thresholds)
        return tuple(sorted(float(value) for value in values))

    def configured_check_count(self) -> int:
        """Return the number of effective promotion checks in this gate."""
        scalar_fields = (
            self.maximum_latency_p50_ms,
            self.maximum_latency_p90_ms,
            self.maximum_false_noteons_per_min,
            self.maximum_octave_error_rate,
            self.maximum_octave_error_noteons_per_min,
            self.maximum_worst_clip_false_noteons_per_min,
            self.maximum_worst_corpus_false_noteons_per_min,
        )
        return (
            len(self.minimum_recall_at_ms)
            + len(self.minimum_worst_clip_recall_at_ms)
            + len(self.minimum_worst_corpus_recall_at_ms)
            + sum(
                len(thresholds)
                for thresholds in self.minimum_context_recall_at_ms.values()
            )
            + sum(value is not None for value in scalar_fields)
        )


def _gate_config_report(config: CausalMetricGate) -> dict[str, object]:
    def thresholds(values: Mapping[float, float]) -> dict[str, float]:
        return {
            _deadline_key(deadline): threshold
            for deadline, threshold in _normalise_ratio_thresholds(
                values, "gate thresholds"
            ).items()
        }

    contexts: dict[str, dict[str, float]] = {}
    for raw_name, values in config.minimum_context_recall_at_ms.items():
        contexts[_CONTEXT_ALIASES[str(raw_name)]] = thresholds(values)
    return {
        "minimum_recall_at_ms": thresholds(
            config.minimum_recall_at_ms
        ),
        "maximum_latency_p50_ms": config.maximum_latency_p50_ms,
        "maximum_latency_p90_ms": config.maximum_latency_p90_ms,
        "maximum_false_noteons_per_min": (
            config.maximum_false_noteons_per_min
        ),
        "minimum_context_recall_at_ms": dict(sorted(contexts.items())),
        "maximum_octave_error_rate": config.maximum_octave_error_rate,
        "maximum_octave_error_noteons_per_min": (
            config.maximum_octave_error_noteons_per_min
        ),
        "minimum_worst_clip_recall_at_ms": thresholds(
            config.minimum_worst_clip_recall_at_ms
        ),
        "minimum_worst_corpus_recall_at_ms": thresholds(
            config.minimum_worst_corpus_recall_at_ms
        ),
        "maximum_worst_clip_false_noteons_per_min": (
            config.maximum_worst_clip_false_noteons_per_min
        ),
        "maximum_worst_corpus_false_noteons_per_min": (
            config.maximum_worst_corpus_false_noteons_per_min
        ),
    }


def _append_gate_check(
    checks: list[dict[str, object]],
    *,
    name: str,
    value: float | None,
    operator: str,
    threshold: float,
    scope: Mapping[str, object] | None = None,
) -> None:
    if operator == ">=":
        passed = (
            value is not None
            and float(value) + 1e-12 >= float(threshold)
        )
    elif operator == "<=":
        passed = (
            value is not None
            and float(value) <= float(threshold) + 1e-12
        )
    else:
        raise ValueError(f"Unsupported gate operator: {operator!r}.")
    row: dict[str, object] = {
        "name": name,
        "value": value,
        "operator": operator,
        "threshold": float(threshold),
        "passed": bool(passed),
    }
    if scope:
        row["scope"] = dict(scope)
    checks.append(row)


def evaluate_causal_metric_gate(
    report: Mapping[str, object],
    config: CausalMetricGate,
) -> dict[str, object]:
    """Evaluate a gate against an aggregate report."""

    if not isinstance(config, CausalMetricGate):
        raise TypeError("config must be a CausalMetricGate.")
    aggregate = report.get("aggregate")
    worst = report.get("worst")
    if not isinstance(aggregate, Mapping) or not isinstance(worst, Mapping):
        raise ValueError(
            "report must contain aggregate and worst metric mappings."
        )
    checks: list[dict[str, object]] = []

    def recall_value(
        metrics: Mapping[str, object],
        deadline: float,
    ) -> float | None:
        key = _deadline_key(deadline)
        values = metrics.get("recall_at_ms")
        if not isinstance(values, Mapping) or key not in values:
            raise ValueError(
                f"The report does not contain recall deadline {key} ms."
            )
        value = values[key]
        return None if value is None else float(value)

    for deadline, threshold in _normalise_ratio_thresholds(
        config.minimum_recall_at_ms, "minimum_recall_at_ms"
    ).items():
        _append_gate_check(
            checks,
            name=f"aggregate.recall_at_{_deadline_key(deadline)}ms",
            value=recall_value(aggregate, deadline),
            operator=">=",
            threshold=threshold,
        )

    for field_name, threshold in (
        ("latency_p50_ms", config.maximum_latency_p50_ms),
        ("latency_p90_ms", config.maximum_latency_p90_ms),
        (
            "false_noteons_per_min",
            config.maximum_false_noteons_per_min,
        ),
        (
            "octave_error_rate_of_false_noteons",
            config.maximum_octave_error_rate,
        ),
        (
            "octave_error_noteons_per_min",
            config.maximum_octave_error_noteons_per_min,
        ),
    ):
        if threshold is None:
            continue
        raw_value = aggregate.get(field_name)
        _append_gate_check(
            checks,
            name=f"aggregate.{field_name}",
            value=None if raw_value is None else float(raw_value),
            operator="<=",
            threshold=float(threshold),
        )

    contexts = aggregate.get("contexts")
    if not isinstance(contexts, Mapping):
        raise ValueError("The aggregate report has no context metrics.")
    for raw_name, raw_thresholds in sorted(
        config.minimum_context_recall_at_ms.items()
    ):
        name = _CONTEXT_ALIASES[str(raw_name)]
        context = contexts.get(name)
        if not isinstance(context, Mapping):
            raise ValueError(f"The report has no {name!r} context.")
        for deadline, threshold in _normalise_ratio_thresholds(
            raw_thresholds,
            f"minimum_context_recall_at_ms[{raw_name!r}]",
        ).items():
            _append_gate_check(
                checks,
                name=(
                    f"aggregate.contexts.{name}."
                    f"recall_at_{_deadline_key(deadline)}ms"
                ),
                value=recall_value(context, deadline),
                operator=">=",
                threshold=threshold,
            )

    clip_worst = worst.get("clip")
    corpus_worst = worst.get("corpus")
    if not isinstance(clip_worst, Mapping) or not isinstance(
        corpus_worst, Mapping
    ):
        raise ValueError("The report has incomplete worst-scope metrics.")

    for scope_name, scope_metrics, thresholds in (
        (
            "worst_clip",
            clip_worst,
            config.minimum_worst_clip_recall_at_ms,
        ),
        (
            "worst_corpus",
            corpus_worst,
            config.minimum_worst_corpus_recall_at_ms,
        ),
    ):
        recall_rows = scope_metrics.get("recall_at_ms")
        if not isinstance(recall_rows, Mapping):
            raise ValueError(f"The report has no {scope_name} recall.")
        for deadline, threshold in _normalise_ratio_thresholds(
            thresholds, f"minimum_{scope_name}_recall_at_ms"
        ).items():
            key = _deadline_key(deadline)
            row = recall_rows.get(key)
            if row is not None and not isinstance(row, Mapping):
                raise ValueError(f"Invalid {scope_name} recall row.")
            value = (
                None if row is None or row.get("value") is None
                else float(row["value"])
            )
            scope = (
                None
                if row is None
                else {
                    name: row[name]
                    for name in ("corpus_id", "clip_id")
                    if name in row
                }
            )
            _append_gate_check(
                checks,
                name=f"{scope_name}.recall_at_{key}ms",
                value=value,
                operator=">=",
                threshold=threshold,
                scope=scope,
            )

    for scope_name, scope_metrics, threshold in (
        (
            "worst_clip",
            clip_worst,
            config.maximum_worst_clip_false_noteons_per_min,
        ),
        (
            "worst_corpus",
            corpus_worst,
            config.maximum_worst_corpus_false_noteons_per_min,
        ),
    ):
        if threshold is None:
            continue
        row = scope_metrics.get("false_noteons_per_min")
        if row is not None and not isinstance(row, Mapping):
            raise ValueError(f"Invalid {scope_name} false-rate row.")
        value = (
            None if row is None or row.get("value") is None
            else float(row["value"])
        )
        scope = (
            None
            if row is None
            else {
                name: row[name]
                for name in ("corpus_id", "clip_id")
                if name in row
            }
        )
        _append_gate_check(
            checks,
            name=f"{scope_name}.false_noteons_per_min",
            value=value,
            operator="<=",
            threshold=float(threshold),
            scope=scope,
        )

    failed = [row["name"] for row in checks if not row["passed"]]
    return {
        "passed": not failed,
        "checks": checks,
        "failed_checks": failed,
        "configured_checks": len(checks),
        "observed_worst": worst,
        "config": _gate_config_report(config),
    }


def evaluate_causal_event_metrics(
    clips: Sequence[ClipNoteOnData],
    *,
    max_latency_ms: float = DEFAULT_MAX_LATENCY_MS,
    recall_deadlines_ms: Sequence[float] = DEFAULT_RECALL_DEADLINES_MS,
    same_pitch_gap_ms: float = DEFAULT_SAME_PITCH_GAP_MS,
    gate: CausalMetricGate | None = None,
) -> dict[str, object]:
    """Evaluate independent clips and aggregate them by clip and corpus.

    Counts are micro-aggregated and durations are summed.  Matching always
    remains clip-local, so equal pitches at file boundaries cannot match.
    """

    maximum = _validate_nonnegative(max_latency_ms, "max_latency_ms")
    extra_gate_deadlines = gate.required_deadlines_ms() if gate else ()
    deadlines = _normalise_deadlines(
        tuple(recall_deadlines_ms) + tuple(extra_gate_deadlines),
        max_latency_ms=maximum,
    )
    gap = _validate_nonnegative(same_pitch_gap_ms, "same_pitch_gap_ms")
    clip_values = tuple(clips)
    if not clip_values:
        raise ValueError("At least one clip is required.")
    if not all(isinstance(item, ClipNoteOnData) for item in clip_values):
        raise TypeError("clips must contain only ClipNoteOnData values.")
    identities = [
        (item.corpus_id, item.clip_id) for item in clip_values
    ]
    if len(set(identities)) != len(identities):
        raise ValueError("Duplicate corpus_id/clip_id identity.")

    evaluated: list[
        tuple[ClipNoteOnData, _MetricAccumulator, dict[str, object]]
    ] = []
    for clip in sorted(
        clip_values, key=lambda item: (item.corpus_id, item.clip_id)
    ):
        result = match_causal_note_ons(
            clip.reference,
            clip.predictions,
            max_latency_ms=maximum,
        )
        accumulator = _build_accumulator(
            clip.reference,
            clip.predictions,
            result,
            duration_s=clip.duration_s,
            max_latency_ms=maximum,
            same_pitch_gap_ms=gap,
        )
        metrics = _summary_from_accumulator(accumulator, deadlines)
        evaluated.append((clip, accumulator, metrics))

    per_clip = [
        {
            "clip_id": clip.clip_id,
            "corpus_id": clip.corpus_id,
            **metrics,
        }
        for clip, _, metrics in evaluated
    ]
    aggregate_accumulator = _merge_accumulators(
        [accumulator for _, accumulator, _ in evaluated]
    )
    aggregate = {
        "clips": len(evaluated),
        "corpora": len({clip.corpus_id for clip, _, _ in evaluated}),
        **_summary_from_accumulator(aggregate_accumulator, deadlines),
    }

    by_corpus: dict[str, dict[str, object]] = {}
    for corpus_id in sorted(
        {clip.corpus_id for clip, _, _ in evaluated}
    ):
        corpus_accumulators = [
            accumulator
            for clip, accumulator, _ in evaluated
            if clip.corpus_id == corpus_id
        ]
        by_corpus[corpus_id] = {
            "clips": len(corpus_accumulators),
            **_summary_from_accumulator(
                _merge_accumulators(corpus_accumulators), deadlines
            ),
        }

    report: dict[str, object] = {
        "schema_version": 1,
        "policy": {
            "matching": "latest_causal_same_pitch_one_to_one_per_clip",
            "negative_latency_allowed": False,
            "cross_clip_matching_allowed": False,
            "aggregation": "micro_counts_and_summed_duration",
        },
        "configuration": {
            "max_latency_ms": maximum,
            "recall_deadlines_ms": list(deadlines),
            "same_pitch_gap_ms": gap,
        },
        "aggregate": aggregate,
        "by_corpus": by_corpus,
        "per_clip": per_clip,
        "worst": _build_worst_summary(
            per_clip, by_corpus, deadlines
        ),
        "gate": None,
    }
    if gate is not None:
        report["gate"] = evaluate_causal_metric_gate(report, gate)
    return report


# Readable compatibility aliases for callers that use the shorter V6 names.
ReferenceNoteOn = ReferenceNote
PredictedNoteOn = NoteOnPrediction
CausalGateConfig = CausalMetricGate
causal_match_noteons = match_causal_note_ons
aggregate_causal_event_metrics = evaluate_causal_event_metrics


__all__ = [
    "DEFAULT_MAX_LATENCY_MS",
    "DEFAULT_RECALL_DEADLINES_MS",
    "DEFAULT_SAME_PITCH_GAP_MS",
    "CausalGateConfig",
    "CausalMetricGate",
    "CausalNoteOnMatch",
    "CausalNoteOnResult",
    "ClipNoteOnData",
    "NoteOnPrediction",
    "PredictedNoteOn",
    "ReferenceNote",
    "ReferenceNoteOn",
    "aggregate_causal_event_metrics",
    "causal_match_noteons",
    "causal_metrics_summary",
    "compute_causal_note_on_metrics",
    "evaluate_causal_event_metrics",
    "evaluate_causal_metric_gate",
    "match_causal_note_ons",
    "reference_context_masks",
]
