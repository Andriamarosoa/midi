"""Synthetic-only H19 frame-fallback exposure and risk-difference conformance.

The decoder already freezes the activation reason in each immutable emitted
``PolyphonicMidiEvent``.  This module observes that public output only: it does
not participate in ranking, state mutation, gating, or MIDI emission.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
from typing import Protocol, Sequence

import numpy as np

from .causal_event_metrics import ReferenceNote
from .provisional_resolution_age1 import (
    TARGET_EXCLUDED_INVALID_FRAME,
    TARGET_EXCLUDED_OUTSIDE_AUDIO,
    TARGET_MATCHABLE,
    Age1TargetRecord,
    extract_exact_causal_age1_targets,
)
from .provisional_resolution_age1_metrics import canonical_group_universe


BOOTSTRAP_REPLICATE_COUNT = 10_000
BOOTSTRAP_SEED = 721_629_268
MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT = 9_500
MINIMUM_ELIGIBLE_NOTEONS = 200
MINIMUM_FRAME_FALLBACK_NOTEONS = 50
MINIMUM_COMPARATOR_NOTEONS = 50
MINIMUM_RD_FALSE = 0.10

ELIGIBLE_REASONS = frozenset((
    "model_onset", "frame_attack", "chord_completion", "frame_fallback",
))
COMPARATOR_REASONS = frozenset((
    "model_onset", "frame_attack", "chord_completion",
))
EXCLUDED_REASONS = frozenset((
    "harmonic_strong_frame", "legacy", "retrigger",
))
KNOWN_REASONS = ELIGIBLE_REASONS | EXCLUDED_REASONS

FRAME_FALLBACK_EXECUTION_INVALID = "frame_fallback_execution_invalid"
FRAME_FALLBACK_SIGNAL_INSUFFICIENT = (
    "frame_fallback_signal_insufficient_valid_observations"
)
FRAME_FALLBACK_EXPOSED_INSUFFICIENT = (
    "frame_fallback_exposed_population_insufficient"
)
FRAME_FALLBACK_COMPARATOR_INSUFFICIENT = (
    "frame_fallback_comparator_population_insufficient"
)
GROUP_RESAMPLING_INCONCLUSIVE = "group_resampling_inconclusive"
FRAME_FALLBACK_RISK_DEMONSTRATED = (
    "frame_fallback_false_risk_enrichment_demonstrated"
)
FRAME_FALLBACK_RISK_NOT_DEMONSTRATED = (
    "frame_fallback_false_risk_enrichment_not_demonstrated"
)


class MidiEventLike(Protocol):
    kind: str
    pitch: int
    frame_index: int
    reason: str


def _metadata(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{name} must be a non-empty unpadded string.")
    return value


def _coordinate(frame_index: object, pitch: object) -> tuple[int, int]:
    if type(frame_index) is not int or frame_index < 0:
        raise ValueError("frame_index must be a non-negative JSON-native integer.")
    if type(pitch) is not int or not 0 <= pitch <= 127:
        raise ValueError("pitch must be a JSON-native MIDI integer in [0, 127].")
    return frame_index, pitch


@dataclass(frozen=True)
class FrameFallbackExposureRecord:
    frame_index: int
    pitch: int
    candidate_reason_at_noteon: str

    def __post_init__(self) -> None:
        _coordinate(self.frame_index, self.pitch)
        reason = _metadata(
            self.candidate_reason_at_noteon, "candidate_reason_at_noteon"
        )
        if reason not in KNOWN_REASONS:
            raise RuntimeError(
                f"{FRAME_FALLBACK_EXECUTION_INVALID}: unexpected NoteOn reason"
            )


class PassiveFrameFallbackExposureCollector:
    """Freeze reasons from already-emitted NoteOns without touching a decoder."""

    def __init__(self) -> None:
        self._records: list[FrameFallbackExposureRecord] = []
        self._seen: set[tuple[int, int]] = set()

    @property
    def records(self) -> tuple[FrameFallbackExposureRecord, ...]:
        return tuple(self._records)

    def observe_emitted_noteons(
        self, events: Sequence[MidiEventLike]
    ) -> tuple[MidiEventLike, ...]:
        """Observe the immutable emitted-event sequence and return it unchanged."""
        original = tuple(events)
        staged: list[tuple[tuple[int, int], FrameFallbackExposureRecord]] = []
        for event in original:
            if event.kind != "note_on":
                continue
            key = _coordinate(event.frame_index, event.pitch)
            if key in self._seen or any(key == item[0] for item in staged):
                raise RuntimeError(
                    f"{FRAME_FALLBACK_EXECUTION_INVALID}: duplicate NoteOn identity"
                )
            record = FrameFallbackExposureRecord(
                frame_index=key[0],
                pitch=key[1],
                candidate_reason_at_noteon=event.reason,
            )
            staged.append((key, record))
        for key, record in staged:
            self._seen.add(key)
            self._records.append(record)
        return original


@dataclass(frozen=True)
class GroupedFrameFallbackRow:
    recording_key: str
    corpus_category: str
    leakage_group_key: str
    frame_index: int
    pitch: int
    candidate_reason_at_noteon: str
    frame_fallback_indicator: int | None
    false_noteon: int | None
    target_status: str

    def __post_init__(self) -> None:
        for name in ("recording_key", "corpus_category", "leakage_group_key"):
            object.__setattr__(self, name, _metadata(getattr(self, name), name))
        _coordinate(self.frame_index, self.pitch)
        reason = _metadata(
            self.candidate_reason_at_noteon, "candidate_reason_at_noteon"
        )
        if reason not in KNOWN_REASONS:
            raise RuntimeError(
                f"{FRAME_FALLBACK_EXECUTION_INVALID}: unexpected NoteOn reason"
            )
        expected_f = (
            1 if reason == "frame_fallback" else 0 if reason in COMPARATOR_REASONS else None
        )
        if self.frame_fallback_indicator != expected_f:
            raise ValueError("frame_fallback_indicator does not match frozen reason.")
        if self.target_status == TARGET_MATCHABLE and reason in ELIGIBLE_REASONS:
            if type(self.false_noteon) is not int or self.false_noteon not in (0, 1):
                raise ValueError("Eligible matchable rows require binary false_noteon.")
        elif self.false_noteon is not None:
            raise ValueError("Excluded rows must not carry a false_noteon target.")
        if self.target_status not in (
            TARGET_MATCHABLE,
            TARGET_EXCLUDED_INVALID_FRAME,
            TARGET_EXCLUDED_OUTSIDE_AUDIO,
        ):
            raise ValueError("Unknown frozen causal target_status.")


def join_h19_exposures_and_targets(
    exposures: Sequence[FrameFallbackExposureRecord],
    targets: Sequence[Age1TargetRecord],
    *,
    recording_key: str,
    corpus_category: str,
    leakage_group_key: str,
) -> tuple[GroupedFrameFallbackRow, ...]:
    """Exact-coordinate join with the already frozen H17 causal target."""
    exposure_map = {(row.frame_index, row.pitch): row for row in exposures}
    target_map = {(row.frame_index, row.pitch): row for row in targets}
    if len(exposure_map) != len(exposures) or len(target_map) != len(targets):
        raise RuntimeError(f"{FRAME_FALLBACK_EXECUTION_INVALID}: duplicate identity")
    if exposure_map.keys() != target_map.keys():
        raise RuntimeError(f"{FRAME_FALLBACK_EXECUTION_INVALID}: identity mismatch")
    rows = []
    for key in sorted(exposure_map):
        exposure = exposure_map[key]
        target = target_map[key]
        reason = exposure.candidate_reason_at_noteon
        eligible = reason in ELIGIBLE_REASONS and target.target_status == TARGET_MATCHABLE
        rows.append(GroupedFrameFallbackRow(
            recording_key=recording_key,
            corpus_category=corpus_category,
            leakage_group_key=leakage_group_key,
            frame_index=key[0],
            pitch=key[1],
            candidate_reason_at_noteon=reason,
            frame_fallback_indicator=(
                1 if reason == "frame_fallback" else 0 if reason in COMPARATOR_REASONS else None
            ),
            false_noteon=(1 - int(target.true_noteon) if eligible else None),
            target_status=target.target_status,
        ))
    return tuple(rows)


def extract_synthetic_h19_rows(
    emitted_events: Sequence[MidiEventLike],
    reference: Sequence[ReferenceNote],
    *,
    recording_key: str,
    corpus_category: str,
    leakage_group_key: str,
    frame_valid: Sequence[object],
    sample_rate: int,
    hop_size: int,
    audio_frames: int,
) -> tuple[GroupedFrameFallbackRow, ...]:
    """Synthetic adapter which reuses the exact H17 causal target extractor."""
    collector = PassiveFrameFallbackExposureCollector()
    frozen_events = collector.observe_emitted_noteons(emitted_events)
    targets = extract_exact_causal_age1_targets(
        frozen_events,
        reference,
        frame_valid=frame_valid,
        sample_rate=sample_rate,
        hop_size=hop_size,
        audio_frames=audio_frames,
    )
    return join_h19_exposures_and_targets(
        collector.records,
        targets,
        recording_key=recording_key,
        corpus_category=corpus_category,
        leakage_group_key=leakage_group_key,
    )


def _eligible(
    rows: Sequence[GroupedFrameFallbackRow],
) -> tuple[GroupedFrameFallbackRow, ...]:
    checked = tuple(rows)
    if not all(isinstance(row, GroupedFrameFallbackRow) for row in checked):
        raise ValueError("rows must contain only GroupedFrameFallbackRow values.")
    return tuple(
        row for row in checked
        if row.candidate_reason_at_noteon in ELIGIBLE_REASONS
        and row.target_status == TARGET_MATCHABLE
    )


def risk_difference_false(rows: Sequence[GroupedFrameFallbackRow]) -> float:
    """P(false|F=1) - P(false|F=0), with both strata required."""
    eligible = _eligible(rows)
    exposed = [row.false_noteon for row in eligible if row.frame_fallback_indicator == 1]
    comparator = [row.false_noteon for row in eligible if row.frame_fallback_indicator == 0]
    if not exposed or not comparator:
        raise ValueError("Both H19 exposure strata are required.")
    value = float(np.mean(exposed) - np.mean(comparator))
    if not math.isfinite(value) or not -1.0 <= value <= 1.0:
        raise RuntimeError("Fail closed: RD_false escaped [-1, 1].")
    return value


@dataclass(frozen=True)
class H19BootstrapResult:
    status: str
    requested_replicates: int
    valid_replicates: int
    invalid_replicates: int
    seed: int
    rng: str
    percentile_method: str
    cohort_group_count: int
    lower_95: float | None
    upper_95: float | None


def grouped_rd_false_bootstrap(
    rows: Sequence[GroupedFrameFallbackRow],
    *,
    cohort_group_universe: Sequence[str],
) -> H19BootstrapResult:
    """Sample exactly G immutable group IDs, retaining empty groups."""
    checked = tuple(rows)
    if not all(isinstance(row, GroupedFrameFallbackRow) for row in checked):
        raise ValueError("rows must contain only GroupedFrameFallbackRow values.")
    groups = canonical_group_universe(cohort_group_universe)
    if {row.leakage_group_key for row in checked}.difference(groups):
        raise ValueError("row leakage_group_key is outside cohort_group_universe.")
    eligible = _eligible(checked)
    grouped = {
        group: tuple(row for row in eligible if row.leakage_group_key == group)
        for group in groups
    }
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    values: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATE_COUNT):
        indexes = rng.integers(0, len(groups), size=len(groups))
        sampled = tuple(
            row for index in indexes for row in grouped[groups[int(index)]]
        )
        if {row.frame_fallback_indicator for row in sampled} != {0, 1}:
            continue
        values.append(risk_difference_false(sampled))
    valid = len(values)
    invalid = BOOTSTRAP_REPLICATE_COUNT - valid
    complete = valid >= MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT
    lower = upper = None
    if complete:
        percentile = np.percentile(
            np.asarray(values, dtype=np.float64), [2.5, 97.5], method="linear"
        )
        lower, upper = float(percentile[0]), float(percentile[1])
        if not math.isfinite(lower) or not math.isfinite(upper):
            raise RuntimeError("Fail closed: H19 bootstrap percentile is non-finite.")
    return H19BootstrapResult(
        status="complete" if complete else GROUP_RESAMPLING_INCONCLUSIVE,
        requested_replicates=BOOTSTRAP_REPLICATE_COUNT,
        valid_replicates=valid,
        invalid_replicates=invalid,
        seed=BOOTSTRAP_SEED,
        rng="numpy.random.Generator(numpy.random.PCG64)",
        percentile_method="numpy.percentile(method=linear)",
        cohort_group_count=len(groups),
        lower_95=lower,
        upper_95=upper,
    )


@dataclass(frozen=True)
class H19SyntheticReport:
    status: str
    emitted_noteons_initially_considered: int
    audio_aware_activation_noteons_in_h17_population: int
    eligible_noteons: int
    frame_fallback_noteons: int
    comparator_noteons: int
    excluded_legacy_count: int
    excluded_retrigger_count: int
    excluded_harmonic_strong_frame_count: int
    target_unmatchable_or_excluded_count: int
    malformed_reason_count: int
    malformed_or_nonfinite_target_count: int
    counts_per_frozen_reason: dict[str, int]
    false_rate_frame_fallback: float | None
    false_rate_comparator: float | None
    rd_false: float | None
    bootstrap: H19BootstrapResult | None


def evaluate_h19_synthetic_metrics(
    rows: Sequence[GroupedFrameFallbackRow],
    *,
    cohort_group_universe: Sequence[str],
) -> H19SyntheticReport:
    checked = tuple(rows)
    groups = canonical_group_universe(cohort_group_universe)
    if {row.leakage_group_key for row in checked}.difference(groups):
        raise ValueError("row leakage_group_key is outside cohort_group_universe.")
    eligible = _eligible(checked)
    counts = Counter(row.candidate_reason_at_noteon for row in checked)
    exposed = tuple(row for row in eligible if row.frame_fallback_indicator == 1)
    comparator = tuple(row for row in eligible if row.frame_fallback_indicator == 0)
    common = dict(
        emitted_noteons_initially_considered=len(checked),
        audio_aware_activation_noteons_in_h17_population=sum(
            row.candidate_reason_at_noteon in ELIGIBLE_REASONS for row in checked
        ),
        eligible_noteons=len(eligible),
        frame_fallback_noteons=len(exposed),
        comparator_noteons=len(comparator),
        excluded_legacy_count=counts["legacy"],
        excluded_retrigger_count=counts["retrigger"],
        excluded_harmonic_strong_frame_count=counts["harmonic_strong_frame"],
        target_unmatchable_or_excluded_count=sum(
            row.candidate_reason_at_noteon in ELIGIBLE_REASONS
            and row.target_status != TARGET_MATCHABLE
            for row in checked
        ),
        malformed_reason_count=0,
        malformed_or_nonfinite_target_count=0,
        counts_per_frozen_reason={reason: counts[reason] for reason in sorted(KNOWN_REASONS)},
        false_rate_frame_fallback=(
            float(np.mean([row.false_noteon for row in exposed])) if exposed else None
        ),
        false_rate_comparator=(
            float(np.mean([row.false_noteon for row in comparator])) if comparator else None
        ),
    )
    if len(eligible) < MINIMUM_ELIGIBLE_NOTEONS:
        return H19SyntheticReport(FRAME_FALLBACK_SIGNAL_INSUFFICIENT, **common, rd_false=None, bootstrap=None)
    if len(exposed) < MINIMUM_FRAME_FALLBACK_NOTEONS:
        return H19SyntheticReport(FRAME_FALLBACK_EXPOSED_INSUFFICIENT, **common, rd_false=None, bootstrap=None)
    if len(comparator) < MINIMUM_COMPARATOR_NOTEONS:
        return H19SyntheticReport(FRAME_FALLBACK_COMPARATOR_INSUFFICIENT, **common, rd_false=None, bootstrap=None)
    rd = risk_difference_false(eligible)
    bootstrap = grouped_rd_false_bootstrap(
        eligible, cohort_group_universe=groups
    )
    if bootstrap.status == GROUP_RESAMPLING_INCONCLUSIVE:
        status = GROUP_RESAMPLING_INCONCLUSIVE
    elif rd >= MINIMUM_RD_FALSE and bootstrap.lower_95 is not None and bootstrap.lower_95 > 0.0:
        status = FRAME_FALLBACK_RISK_DEMONSTRATED
    else:
        status = FRAME_FALLBACK_RISK_NOT_DEMONSTRATED
    return H19SyntheticReport(status, **common, rd_false=rd, bootstrap=bootstrap)


__all__ = [
    "BOOTSTRAP_REPLICATE_COUNT", "BOOTSTRAP_SEED", "COMPARATOR_REASONS",
    "ELIGIBLE_REASONS", "EXCLUDED_REASONS", "FrameFallbackExposureRecord",
    "FRAME_FALLBACK_COMPARATOR_INSUFFICIENT", "FRAME_FALLBACK_EXPOSED_INSUFFICIENT",
    "FRAME_FALLBACK_RISK_DEMONSTRATED", "FRAME_FALLBACK_RISK_NOT_DEMONSTRATED",
    "FRAME_FALLBACK_SIGNAL_INSUFFICIENT",
    "GroupedFrameFallbackRow", "H19BootstrapResult", "H19SyntheticReport",
    "MINIMUM_COMPARATOR_NOTEONS", "MINIMUM_ELIGIBLE_NOTEONS",
    "MINIMUM_FRAME_FALLBACK_NOTEONS", "MINIMUM_RD_FALSE",
    "MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT",
    "PassiveFrameFallbackExposureCollector", "evaluate_h19_synthetic_metrics",
    "extract_synthetic_h19_rows", "grouped_rd_false_bootstrap",
    "join_h19_exposures_and_targets", "risk_difference_false",
]
