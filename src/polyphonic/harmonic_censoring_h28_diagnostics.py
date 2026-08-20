"""Pure reconciliation and serialization for future H28 results.

This module does not issue a capability, read a payload, import NumPy, or run
scientific code.  It converts only a completed engine/recomputer pair into the
closed diagnostic schema preregistered by H28.
"""
from __future__ import annotations

import math
from types import MappingProxyType
from typing import Mapping

from .harmonic_censoring_h28_engine import H28EngineResult
from .harmonic_censoring_h28_recomputer import (
    H28RecomputedResult,
    compare_h28_engine_and_recomputer,
)
from .harmonic_censoring_h28_timing_contract import (
    H28TimingContract,
    REQUIRED_DIAGNOSTIC_FIELDS,
    validate_h28_diagnostic_record,
)


def _required(value: object, *, field: str) -> object:
    if value is None:
        raise ValueError(f"H28 complete diagnostic missing: {field}")
    return value


def _finite_list(values: tuple[float, ...] | None, *, field: str) -> list[float]:
    required = _required(values, field=field)
    if type(required) is not tuple:
        raise TypeError(f"H28 diagnostic tuple required: {field}")
    result = [float(value) for value in required]
    if any(not math.isfinite(value) for value in result):
        raise ValueError(f"H28 non-finite diagnostic forbidden: {field}")
    return result


def _margin_list(values: tuple[float, ...] | None) -> list[float | str]:
    required = _required(values, field="negative_margins")
    if type(required) is not tuple:
        raise TypeError("H28 diagnostic tuple required: negative_margins")
    result: list[float | str] = []
    for value in required:
        number = float(value)
        if math.isinf(number) and number > 0.0:
            result.append("Infinity")
        elif math.isfinite(number):
            result.append(number)
        else:
            raise ValueError("H28 negative margin must be finite or positive infinity")
    return result


def serialize_h28_reconciled_diagnostic(
    contract: H28TimingContract,
    engine_result: H28EngineResult,
    recomputed_result: H28RecomputedResult,
) -> Mapping[str, object]:
    """Return one validated, JSON-native row after independent agreement."""

    if type(contract) is not H28TimingContract:
        raise TypeError("H28 timing contract type invalid")
    if type(engine_result) is not H28EngineResult:
        raise TypeError("H28 engine result type invalid")
    compare_h28_engine_and_recomputer(engine_result, recomputed_result)
    try:
        fixture_id, horizon_id = engine_result.record_identity.split("/")
    except ValueError as exc:
        raise ValueError("H28 diagnostic identity invalid") from exc
    payloads = engine_result.validated_payload_sha256
    if tuple(sorted(payloads)) != ("sample-valid-mask.u8", "waveform.f64le"):
        raise ValueError("H28 diagnostic payload set invalid")
    curve = _required(engine_result.pitch_dilution_curve, field="pitch_dilution_curve")
    if type(curve) is not tuple:
        raise TypeError("H28 diagnostic tuple required: pitch_dilution_curve")

    row: dict[str, object] = {
        "record_identity": engine_result.record_identity,
        "fixture_id": fixture_id,
        "horizon_id": horizon_id,
        "proposal_hop_end": engine_result.maximum_sample_read,
        "maximum_sample_read": engine_result.maximum_sample_read,
        "role_classifications": dict(engine_result.role_classifications),
        "mask_counts": dict(engine_result.mask_counts),
        "current_short_total_power": float(_required(
            engine_result.current_short_total_power, field="current_short_total_power"
        )),
        "previous_short_total_power": float(_required(
            engine_result.previous_short_total_power, field="previous_short_total_power"
        )),
        "current_long_total_power": float(_required(
            engine_result.current_long_total_power, field="current_long_total_power"
        )),
        "previous_long_total_power": float(_required(
            engine_result.previous_long_total_power, field="previous_long_total_power"
        )),
        "exclusive_ranks": list(engine_result.exclusive_ranks),
        "exclusive_band_energies": _finite_list(
            engine_result.exclusive_band_energies, field="exclusive_band_energies"
        ),
        "harmonic_ratios": _finite_list(engine_result.harmonic_ratios, field="harmonic_ratios"),
        "ratios_at_or_above_positive_threshold": _required(
            engine_result.ratios_at_or_above_positive_threshold,
            field="ratios_at_or_above_positive_threshold",
        ),
        "onset_rise": float(_required(engine_result.onset_rise, field="onset_rise")),
        "active_residual_before_candidate": float(_required(
            engine_result.active_residual_before_candidate,
            field="active_residual_before_candidate",
        )),
        "augmented_residual_after_candidate": float(_required(
            engine_result.augmented_residual_after_candidate,
            field="augmented_residual_after_candidate",
        )),
        "residual_improvement": float(_required(
            engine_result.residual_improvement, field="residual_improvement"
        )),
        "persistence": float(_required(engine_result.persistence, field="persistence")),
        "bounded_claim_lower_bounds": _finite_list(
            engine_result.bounded_claim_lower_bounds, field="bounded_claim_lower_bounds"
        ),
        "negative_margins": _margin_list(engine_result.negative_margins),
        "pitch_dilution_curve": [
            [int(pitch), float(improvement)] for pitch, improvement in curve
        ],
        "positive_partial_condition": _required(
            engine_result.positive_partial_condition, field="positive_partial_condition"
        ),
        "positive_onset_condition": _required(
            engine_result.positive_onset_condition, field="positive_onset_condition"
        ),
        "positive_residual_condition": _required(
            engine_result.positive_residual_condition, field="positive_residual_condition"
        ),
        "negative_partial_condition": _required(
            engine_result.negative_partial_condition, field="negative_partial_condition"
        ),
        "negative_onset_condition": _required(
            engine_result.negative_onset_condition, field="negative_onset_condition"
        ),
        "negative_residual_condition": _required(
            engine_result.negative_residual_condition, field="negative_residual_condition"
        ),
        "outcome": engine_result.outcome,
        "certificate_kind": engine_result.certificate_kind,
        "certificate_complete": engine_result.certificate_complete,
        "decision_reason": _required(engine_result.decision_reason, field="decision_reason"),
        "waveform_sha256": payloads["waveform.f64le"],
        "mask_sha256": payloads["sample-valid-mask.u8"],
    }
    if tuple(row) != REQUIRED_DIAGNOSTIC_FIELDS:
        raise RuntimeError("H28 serializer field order differs from preregistration")
    validated = validate_h28_diagnostic_record(contract, row)
    return MappingProxyType(dict(validated))


__all__ = ["serialize_h28_reconciled_diagnostic"]
