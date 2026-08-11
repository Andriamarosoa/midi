"""Independent dormant recomputation of persisted H26 measurement records."""
from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Mapping, Sequence

from .harmonic_censoring_h26_contract import H26DormantPlan


@dataclass(frozen=True)
class H26RecomputedRecord:
    fixture_id: str
    outcome: str
    reason: str
    positive_certificate_complete: bool
    negative_certificate_complete: bool


@dataclass(frozen=True)
class H26RecomputedEvidence:
    fixture_id: str
    measurement: Mapping[str, object]
    resolution: H26RecomputedRecord


@dataclass(frozen=True)
class H26TranscriptRecord:
    test_id: str
    order: int
    phase: str
    status: str
    evidence_sha256: str | None
    kill_status: str | None


def _bool(record: Mapping[str, object], key: str) -> bool:
    value = record.get(key)
    if type(value) is not bool:
        raise ValueError(f"H26 recomputer requires boolean {key}.")
    return value


def _finite(record: Mapping[str, object], key: str) -> float:
    value = record.get(key)
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"H26 recomputer requires finite {key}.")
    return float(value)


def _float_tuple(record: Mapping[str, object], key: str, *, infinity_allowed: bool = False) -> tuple[float, ...]:
    raw = record.get(key)
    if type(raw) not in (list, tuple):
        raise ValueError(f"H26 recomputer requires array {key}.")
    values = tuple(float(value) for value in raw)
    for value in values:
        if math.isnan(value) or (math.isinf(value) and not infinity_allowed):
            raise ValueError(f"H26 recomputer invalid {key} value.")
    return values


def recompute_h26_resolution(
    plan: H26DormantPlan, *, fixture_id: str,
    measurement: Mapping[str, object],
) -> H26RecomputedRecord:
    """Re-derive an outcome without importing or calling the producer engine."""

    plan.fixture(fixture_id)  # membership only; expected/category remain unread.
    active = _bool(measurement, "candidate_active")
    valid = _bool(measurement, "support_valid")
    equivalent = _bool(measurement, "observation_equivalent")
    if active:
        return H26RecomputedRecord(fixture_id, "ALREADY_ACTIVE_HISTORY", "candidate_active_before_proposal", False, False)
    if not valid:
        return H26RecomputedRecord(fixture_id, "AMBIGUOUS", "invalid_or_incomplete_support", False, False)
    if equivalent:
        return H26RecomputedRecord(fixture_id, "AMBIGUOUS", "observation_equivalent_latent_causes", False, False)
    ratios = _float_tuple(measurement, "exclusive_energy_ratios")
    bounds = _float_tuple(measurement, "candidate_lower_bounds")
    margins = _float_tuple(measurement, "negative_margin_ratios", infinity_allowed=True)
    if not (len(ratios) == len(bounds) == len(margins)):
        raise ValueError("H26 recomputer certificate vector length mismatch.")
    onset = _finite(measurement, "onset_rise")
    improvement = _finite(measurement, "active_only_residual_improvement")
    positive = plan.contract["positive_certificate"]
    negative = plan.contract["negative_certificate"]
    bounded_claim = plan.contract["bounded_candidate_claim"]
    positive_complete = (
        sum(ratio >= float(positive["minimum_exclusive_energy_ratio_each"]) for ratio in ratios)
        >= int(positive["minimum_exclusive_partial_count"])
        and onset >= float(positive["minimum_short_window_onset_rise"])
        and improvement >= float(positive["minimum_active_only_residual_improvement"])
    )
    bounded_indexes = tuple(
        index for index, bound in enumerate(bounds)
        if math.isfinite(bound) and bound >= float(bounded_claim["minimum_exclusive_energy_ratio"])
    )
    negative_complete = (
        len(bounded_indexes) >= int(bounded_claim["minimum_exclusive_partial_count"])
        and all(ratios[index] <= float(negative["maximum_exclusive_energy_ratio_each"]) for index in bounded_indexes)
        and all(margins[index] >= float(negative["minimum_margin_below_candidate_claim"]) for index in bounded_indexes)
        and onset <= float(negative["maximum_short_window_onset_rise"])
        and improvement <= float(negative["maximum_active_only_residual_improvement"])
    )
    if positive_complete:
        return H26RecomputedRecord(fixture_id, "BIRTH_SUPPORTED", "complete_positive_certificate", True, negative_complete)
    if negative_complete:
        return H26RecomputedRecord(fixture_id, "NO_BIRTH", "complete_bounded_negative_certificate", False, True)
    return H26RecomputedRecord(fixture_id, "AMBIGUOUS", "certificate_gap_or_conflict", False, False)


def recompute_h26_evidence_from_raw_operands(
    plan: H26DormantPlan, *, fixture_id: str, operands: Mapping[str, object],
) -> H26RecomputedEvidence:
    """Independently derive measurement features and outcome from raw operands."""

    plan.fixture(fixture_id)  # membership only; no expected/category oracle input.
    forbidden = {"expected", "category", "family", "target", "ground_truth_onset"}
    if forbidden & set(operands):
        raise ValueError("H26 forbidden oracle field in raw operands.")
    active = _bool(operands, "candidate_active")
    valid = _bool(operands, "support_valid")
    equivalent = _bool(operands, "observation_equivalent")
    maximum_read = operands.get("maximum_sample_read")
    if type(maximum_read) is not int or maximum_read < 0:
        raise ValueError("H26 maximum sample read invalid.")
    if active:
        measurement: Mapping[str, object] = {
            "candidate_active": True, "support_valid": valid,
            "observation_equivalent": equivalent,
            "exclusive_partial_ranks": (), "exclusive_energy_ratios": (),
            "onset_rise": 0.0, "active_only_residual_improvement": 0.0,
            "candidate_lower_bounds": (), "negative_margin_ratios": (),
            "long_window_persistence": 0.0,
            "maximum_sample_read": maximum_read,
        }
        resolution = recompute_h26_resolution(
            plan, fixture_id=fixture_id, measurement=measurement,
        )
        return H26RecomputedEvidence(fixture_id, measurement, resolution)
    if not valid or equivalent:
        ranks_raw = operands.get("exclusive_partial_ranks", ())
        if type(ranks_raw) not in (list, tuple) or any(type(rank) is not int for rank in ranks_raw):
            raise ValueError("H26 masked raw ranks invalid.")
        measurement = {
            "candidate_active": False, "support_valid": valid,
            "observation_equivalent": equivalent,
            "exclusive_partial_ranks": tuple(ranks_raw),
            "exclusive_energy_ratios": (), "onset_rise": 0.0,
            "active_only_residual_improvement": 0.0,
            "candidate_lower_bounds": (), "negative_margin_ratios": (),
            "long_window_persistence": 0.0,
            "maximum_sample_read": maximum_read,
        }
        resolution = recompute_h26_resolution(
            plan, fixture_id=fixture_id, measurement=measurement,
        )
        return H26RecomputedEvidence(fixture_id, measurement, resolution)
    required = {
        "candidate_active", "support_valid", "observation_equivalent",
        "exclusive_partial_ranks", "exclusive_band_energies", "shared_band_energy",
        "current_short_total_power", "previous_short_total_power",
        "active_only_residual", "active_plus_candidate_residual",
        "current_long_total_power", "previous_long_total_power",
        "maximum_sample_read", "active_pitches", "candidate_pitch", "perturbation",
    }
    if set(operands) != required:
        raise ValueError("H26 raw operand schema mismatch.")
    ranks_raw = operands["exclusive_partial_ranks"]
    if type(ranks_raw) not in (list, tuple):
        raise ValueError("H26 raw ranks missing.")
    ranks = tuple(ranks_raw)
    if any(type(rank) is not int or not 1 <= rank <= 8 for rank in ranks) or len(ranks) != len(set(ranks)):
        raise ValueError("H26 raw ranks invalid.")
    energies = _float_tuple(operands, "exclusive_band_energies")
    if len(energies) != len(ranks) or any(value < 0.0 for value in energies):
        raise ValueError("H26 raw exclusive energies invalid.")
    shared = _finite(operands, "shared_band_energy")
    current_short = _finite(operands, "current_short_total_power")
    previous_short = _finite(operands, "previous_short_total_power")
    active_residual = _finite(operands, "active_only_residual")
    candidate_residual = _finite(operands, "active_plus_candidate_residual")
    current_long = _finite(operands, "current_long_total_power")
    previous_long = _finite(operands, "previous_long_total_power")
    if min(shared, previous_short, active_residual, candidate_residual, current_long, previous_long) < 0.0 or current_short <= 1e-24:
        raise ValueError("H26 raw power/residual operand invalid.")
    lower_factor = float(
        plan.contract["measurement_definitions"]["global_synthetic_timbre_v1"]["lower_envelope_factor"]
    )
    ratios = tuple(value / current_short for value in energies)
    bounds = tuple(lower_factor * shared / float(rank * rank) / current_short for rank in ranks)
    margins = tuple(math.inf if ratio == 0.0 else lower / ratio for ratio, lower in zip(ratios, bounds))
    onset = max(0.0, current_short - previous_short) / max(current_short, 1e-24)
    improvement = max(0.0, active_residual - candidate_residual) / max(active_residual, 1e-24)
    persistence = (current_long - previous_long) / max(current_long, 1e-24)
    measurement = {
        "candidate_active": False, "support_valid": valid,
        "observation_equivalent": equivalent,
        "exclusive_partial_ranks": ranks, "exclusive_energy_ratios": ratios,
        "onset_rise": onset, "active_only_residual_improvement": improvement,
        "candidate_lower_bounds": bounds, "negative_margin_ratios": margins,
        "long_window_persistence": persistence,
        "maximum_sample_read": maximum_read,
    }
    resolution = recompute_h26_resolution(plan, fixture_id=fixture_id, measurement=measurement)
    return H26RecomputedEvidence(fixture_id, measurement, resolution)


def validate_transcript_prefix(
    plan: H26DormantPlan, records: Sequence[H26TranscriptRecord],
) -> None:
    if len(records) > len(plan.tests):
        raise ValueError("H26 transcript longer than manifest.")
    failed = False
    for index, record in enumerate(records):
        test = plan.tests[index]
        if (record.test_id, record.order, record.phase) != (test.test_id, test.order, test.phase):
            raise ValueError("H26 transcript order/identity mismatch.")
        if failed and record.status != "NOT_RUN_BY_KILL_RULE":
            raise ValueError("H26 tests after first failure must be kill-rule not-run.")
        if record.status == "FAILED":
            if record.kill_status != test.kill_status:
                raise ValueError("H26 transcript kill status mismatch.")
            failed = True
        elif record.status == "PASSED":
            if record.evidence_sha256 is None or record.kill_status is not None:
                raise ValueError("H26 passed transcript record incomplete.")
        elif record.status == "NOT_RUN_BY_KILL_RULE":
            if not failed or record.evidence_sha256 is not None:
                raise ValueError("H26 invalid not-run transcript record.")
        else:
            raise ValueError("H26 unknown transcript status.")


__all__ = [
    "H26RecomputedEvidence", "H26RecomputedRecord", "H26TranscriptRecord",
    "recompute_h26_evidence_from_raw_operands", "recompute_h26_resolution",
    "validate_transcript_prefix",
]
