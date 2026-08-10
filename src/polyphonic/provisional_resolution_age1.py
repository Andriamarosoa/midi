"""Passive H7 age-1 signals and exact offline causal targets.

This module is deliberately independent of TensorFlow, audio readers, manifests,
and scientific metrics.  It provides only synthetic-ready instrumentation and
pure joins required by the H9 conformance contract.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Protocol, Sequence

from .causal_event_metrics import NoteOnPrediction, ReferenceNote, match_causal_note_ons
from .decoder_candidate_labels import (
    _event_matchability,
    _event_noteon_reasons,
    decoder_event_time_s,
)
from .decoder_candidate_mining import CAUSAL_MAX_LATENCY_MS


AGE1_OBSERVATION_AVAILABLE = "age1_observation_available"
AGE1_OBSERVATION_UNAVAILABLE = "age1_observation_unavailable"
TARGET_MATCHABLE = "matchable"
TARGET_EXCLUDED_INVALID_FRAME = "excluded_invalid_frame"
TARGET_EXCLUDED_OUTSIDE_AUDIO = "excluded_outside_audio"


class MidiEventLike(Protocol):
    kind: str
    pitch: int
    frame_index: int
    reason: str


def _finite_probability(value: object, name: str) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{name} must be a finite probability.") from error
    if not math.isfinite(result) or not 0.0 <= result <= 1.0:
        raise ValueError(f"{name} must be a finite probability in [0, 1].")
    return result


def _coordinate(frame_index: object, pitch: object) -> tuple[int, int]:
    if type(frame_index) is not int or frame_index < 0:
        raise ValueError("frame_index must be a non-negative JSON-native integer.")
    if type(pitch) is not int or not 0 <= pitch <= 127:
        raise ValueError("pitch must be a JSON-native MIDI integer in [0, 127].")
    return frame_index, pitch


@dataclass(frozen=True)
class Age1SignalRecord:
    """The complete and closed H7 signal schema for one emitted NoteOn."""

    frame_index: int
    pitch: int
    S0: float
    age1_status: str
    S1: float | None
    D1: float | None

    def __post_init__(self) -> None:
        _coordinate(self.frame_index, self.pitch)
        s0 = _finite_probability(self.S0, "S0")
        object.__setattr__(self, "S0", s0)
        if self.age1_status == AGE1_OBSERVATION_AVAILABLE:
            if self.S1 is None or self.D1 is None:
                raise ValueError("Available age-1 records require S1 and D1.")
            s1 = _finite_probability(self.S1, "S1")
            d1 = float(self.D1)
            if not math.isfinite(d1) or d1 != s1 - s0:
                raise ValueError("D1 must be the exact finite value S1 - S0.")
            object.__setattr__(self, "S1", s1)
            object.__setattr__(self, "D1", d1)
        elif self.age1_status == AGE1_OBSERVATION_UNAVAILABLE:
            if self.S1 is not None or self.D1 is not None:
                raise ValueError("Unavailable age-1 records must have null S1 and D1.")
        else:
            raise ValueError("Unknown age1_status.")


@dataclass(frozen=True)
class _PendingAge1Signal:
    frame_index: int
    pitch: int
    S0: float


class PassiveAge1SignalCollector:
    """Observe emitted NoteOns without participating in decoder decisions."""

    def __init__(self) -> None:
        self._pending: dict[tuple[int, int], _PendingAge1Signal] = {}
        self._completed: list[Age1SignalRecord] = []
        self._seen: set[tuple[int, int]] = set()

    @property
    def pending_count(self) -> int:
        return len(self._pending)

    @property
    def records(self) -> tuple[Age1SignalRecord, ...]:
        return tuple(self._completed)

    def observe_frame(
        self,
        *,
        frame_index: int,
        frame_probability: Sequence[object],
        midi_min: int,
    ) -> None:
        """Resolve pending observations before current-frame decoder decisions."""
        if type(frame_index) is not int or frame_index < 0:
            raise ValueError("frame_index must be a non-negative integer.")
        staged: list[tuple[tuple[int, int], Age1SignalRecord]] = []
        for key, pending in tuple(self._pending.items()):
            expected = pending.frame_index + 1
            if frame_index < expected:
                continue
            if frame_index == expected:
                class_index = pending.pitch - midi_min
                if not 0 <= class_index < len(frame_probability):
                    raise ValueError("Pending pitch is outside the supplied frame vector.")
                s1 = _finite_probability(frame_probability[class_index], "S1")
                record = Age1SignalRecord(
                    frame_index=pending.frame_index,
                    pitch=pending.pitch,
                    S0=pending.S0,
                    age1_status=AGE1_OBSERVATION_AVAILABLE,
                    S1=s1,
                    D1=s1 - pending.S0,
                )
            else:
                record = Age1SignalRecord(
                    frame_index=pending.frame_index,
                    pitch=pending.pitch,
                    S0=pending.S0,
                    age1_status=AGE1_OBSERVATION_UNAVAILABLE,
                    S1=None,
                    D1=None,
                )
            staged.append((key, record))
        for key, record in staged:
            del self._pending[key]
            self._completed.append(record)

    def observe_emitted_noteons(
        self,
        events: Sequence[MidiEventLike],
        *,
        frame_probability: Sequence[object],
        midi_min: int,
    ) -> None:
        """Freeze S0 only after the decoder has really emitted each NoteOn."""
        staged: list[tuple[tuple[int, int], _PendingAge1Signal]] = []
        for event in events:
            if event.kind != "note_on":
                continue
            key = _coordinate(event.frame_index, event.pitch)
            if key in self._seen or any(existing_key == key for existing_key, _ in staged):
                raise RuntimeError("Fail closed: duplicate passive age-1 event identity.")
            class_index = event.pitch - midi_min
            if not 0 <= class_index < len(frame_probability):
                raise ValueError("Emitted NoteOn pitch is outside the supplied frame vector.")
            staged.append((key, _PendingAge1Signal(
                frame_index=event.frame_index,
                pitch=event.pitch,
                S0=_finite_probability(frame_probability[class_index], "S0"),
            )))
        for key, pending in staged:
            self._seen.add(key)
            self._pending[key] = pending


@dataclass(frozen=True)
class Age1TargetRecord:
    """Offline strict-causal target for one emitted NoteOn coordinate."""

    frame_index: int
    pitch: int
    true_noteon: int | None
    target_status: str

    def __post_init__(self) -> None:
        _coordinate(self.frame_index, self.pitch)
        if self.target_status == TARGET_MATCHABLE:
            if type(self.true_noteon) is not int or self.true_noteon not in (0, 1):
                raise ValueError("Matchable target must be the integer 0 or 1.")
        elif self.target_status in (
            TARGET_EXCLUDED_INVALID_FRAME,
            TARGET_EXCLUDED_OUTSIDE_AUDIO,
        ):
            if self.true_noteon is not None:
                raise ValueError("Excluded targets must have null true_noteon.")
        else:
            raise ValueError("Unknown target_status.")


def extract_exact_causal_age1_targets(
    emitted_events: Sequence[MidiEventLike],
    reference: Sequence[ReferenceNote],
    *,
    frame_valid: Sequence[object],
    sample_rate: int,
    hop_size: int,
    audio_frames: int,
) -> tuple[Age1TargetRecord, ...]:
    """Reuse the frozen causal matcher for the complete emitted NoteOn flow."""
    if type(audio_frames) is not int or audio_frames < 0:
        raise ValueError("audio_frames must be a non-negative integer.")
    # Validate the frozen timing contract even when no event is matchable.
    decoder_event_time_s(0, sample_rate=sample_rate, hop_size=hop_size)
    reasons = _event_noteon_reasons(emitted_events)
    coordinates = tuple(sorted(reasons))
    statuses: dict[tuple[int, int], str] = {}
    matchable: list[tuple[int, int]] = []
    predictions: list[NoteOnPrediction] = []
    for frame_index, pitch in coordinates:
        raw_status = _event_matchability(
            frame_index,
            valid=frame_valid,
            hop_size=hop_size,
            audio_frames=audio_frames,
        )
        if raw_status == "invalid_frame":
            statuses[(frame_index, pitch)] = TARGET_EXCLUDED_INVALID_FRAME
        elif raw_status == "outside_audio":
            statuses[(frame_index, pitch)] = TARGET_EXCLUDED_OUTSIDE_AUDIO
        elif raw_status == "matchable":
            statuses[(frame_index, pitch)] = TARGET_MATCHABLE
            matchable.append((frame_index, pitch))
            predictions.append(NoteOnPrediction(
                pitch=pitch,
                time_s=decoder_event_time_s(
                    frame_index,
                    sample_rate=sample_rate,
                    hop_size=hop_size,
                ),
            ))
        else:
            raise AssertionError("Frozen event matchability returned an unknown status.")
    result = match_causal_note_ons(
        reference,
        predictions,
        max_latency_ms=CAUSAL_MAX_LATENCY_MS,
    )
    matched = {item.prediction_index for item in result.matches}
    false = set(result.false_prediction_indices)
    expected = set(range(len(predictions)))
    if matched & false or matched | false != expected:
        raise RuntimeError("Fail closed: causal match/false partition is not exact.")
    outcome = {
        coordinate: (1 if index in matched else 0)
        for index, coordinate in enumerate(matchable)
    }
    return tuple(
        Age1TargetRecord(
            frame_index=frame_index,
            pitch=pitch,
            true_noteon=(outcome[(frame_index, pitch)] if statuses[(frame_index, pitch)] == TARGET_MATCHABLE else None),
            target_status=statuses[(frame_index, pitch)],
        )
        for frame_index, pitch in coordinates
    )


@dataclass(frozen=True)
class Age1ScientificRow:
    """Pure exact-identity join of H7 signal and offline target."""

    frame_index: int
    pitch: int
    S0: float
    S1: float | None
    D1: float | None
    age1_status: str
    true_noteon: int | None
    target_status: str

    def __post_init__(self) -> None:
        signal = Age1SignalRecord(
            self.frame_index, self.pitch, self.S0, self.age1_status, self.S1, self.D1
        )
        target = Age1TargetRecord(
            self.frame_index, self.pitch, self.true_noteon, self.target_status
        )
        object.__setattr__(self, "S0", signal.S0)
        object.__setattr__(self, "S1", signal.S1)
        object.__setattr__(self, "D1", signal.D1)
        object.__setattr__(self, "true_noteon", target.true_noteon)


def join_age1_signals_and_targets(
    signals: Sequence[Age1SignalRecord],
    targets: Sequence[Age1TargetRecord],
) -> tuple[Age1ScientificRow, ...]:
    signal_map = {(item.frame_index, item.pitch): item for item in signals}
    target_map = {(item.frame_index, item.pitch): item for item in targets}
    if len(signal_map) != len(signals) or len(target_map) != len(targets):
        raise RuntimeError("Fail closed: duplicate event identity in H7 join input.")
    if signal_map.keys() != target_map.keys():
        raise RuntimeError("Fail closed: H7 signal and target identities differ.")
    return tuple(
        Age1ScientificRow(
            frame_index=key[0],
            pitch=key[1],
            S0=signal_map[key].S0,
            S1=signal_map[key].S1,
            D1=signal_map[key].D1,
            age1_status=signal_map[key].age1_status,
            true_noteon=target_map[key].true_noteon,
            target_status=target_map[key].target_status,
        )
        for key in sorted(signal_map)
    )


@dataclass(frozen=True)
class Age1AttritionCounts:
    emitted_noteons_initially_considered: int
    noteons_with_exact_age1_observation: int
    noteons_unavailable_due_to_decoder_clock_skip: int
    noteons_excluded_as_ambiguous_or_unmatchable: int
    malformed_or_nonfinite_signal_cases: int


def count_age1_attrition(
    rows: Sequence[Age1ScientificRow],
    *,
    malformed_or_nonfinite_signal_cases: int = 0,
) -> Age1AttritionCounts:
    if type(malformed_or_nonfinite_signal_cases) is not int or malformed_or_nonfinite_signal_cases < 0:
        raise ValueError("malformed_or_nonfinite_signal_cases must be a non-negative integer.")
    return Age1AttritionCounts(
        emitted_noteons_initially_considered=len(rows),
        noteons_with_exact_age1_observation=sum(
            row.age1_status == AGE1_OBSERVATION_AVAILABLE for row in rows
        ),
        noteons_unavailable_due_to_decoder_clock_skip=sum(
            row.age1_status == AGE1_OBSERVATION_UNAVAILABLE for row in rows
        ),
        noteons_excluded_as_ambiguous_or_unmatchable=sum(
            row.target_status != TARGET_MATCHABLE for row in rows
        ),
        malformed_or_nonfinite_signal_cases=malformed_or_nonfinite_signal_cases,
    )


__all__ = [
    "AGE1_OBSERVATION_AVAILABLE",
    "AGE1_OBSERVATION_UNAVAILABLE",
    "TARGET_EXCLUDED_INVALID_FRAME",
    "TARGET_EXCLUDED_OUTSIDE_AUDIO",
    "TARGET_MATCHABLE",
    "Age1AttritionCounts",
    "Age1ScientificRow",
    "Age1SignalRecord",
    "Age1TargetRecord",
    "PassiveAge1SignalCollector",
    "count_age1_attrition",
    "extract_exact_causal_age1_targets",
    "join_age1_signals_and_targets",
]
