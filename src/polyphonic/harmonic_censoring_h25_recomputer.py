"""Independent H25 persisted-evidence recomputer.

The recomputer consumes JSON-native operands emitted by the scientific engine
and derives the pass/fail result itself.  Producers are forbidden from
persisting a verdict or pass field.  This module imports neither NumPy nor the
population materializer.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Mapping, Sequence

from .harmonic_censoring_h25_scientific_engine import (
    ATOL,
    H25DormantScientificPlan,
    H25TestSpecification,
    OUTCOMES,
    RTOL,
    build_typed_harmonic_graph,
)


@dataclass(frozen=True)
class H25RecomputedEvidence:
    test_id: str
    phase: str
    primary_pass: bool
    inverse_pass: bool
    final_pass: bool
    diagnostics: Mapping[str, object]


def _test(plan: H25DormantScientificPlan, test_id: str) -> H25TestSpecification:
    matches = [item for item in plan.tests if item.test_id == test_id]
    if len(matches) != 1:
        raise ValueError("H25 test is absent or duplicated in the sealed plan.")
    return matches[0]


def _object(value: object, label: str) -> Mapping[str, object]:
    if type(value) is not dict:
        raise ValueError(f"H25 {label} must be a JSON object.")
    return value


def _array(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"H25 {label} must be a JSON array.")
    return value


def _finite(value: object) -> bool:
    if type(value) in {int, float}:
        return math.isfinite(float(value))
    if value is None or type(value) in {str, bool}:
        return True
    if type(value) is list:
        return all(_finite(item) for item in value)
    if type(value) is dict:
        return all(_finite(item) for item in value.values())
    return False


def _close(left: float, right: float) -> bool:
    return math.isclose(left, right, rel_tol=RTOL, abs_tol=ATOL)


def _masked_close(left: Sequence[object], right: Sequence[object]) -> bool:
    if len(left) != len(right):
        return False
    for a, b in zip(left, right):
        if a is None or b is None:
            if a is not None or b is not None:
                return False
        elif type(a) not in {int, float} or type(b) not in {int, float} or not _close(float(a), float(b)):
            return False
    return True


def _expected_outcome(fixture: Mapping[str, object]) -> str:
    family = str(fixture["family"])
    fixture_id = str(fixture["id"])
    if str(fixture["category"]) == "positive":
        return "BIRTH_SUPPORTED"
    if str(fixture["category"]) == "ambiguous":
        return "AMBIGUOUS"
    if family == "ACTIVE_ONLY" or fixture_id in {"H25-F-N10", "H25-F-N11"}:
        return "ALREADY_ACTIVE_HISTORY"
    return "NO_BIRTH"


def _measurement_map(evidence: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for raw in _array(evidence.get("fixture_measurements"), "fixture measurements"):
        item = _object(raw, "fixture measurement")
        fixture_id = item.get("fixture_id")
        if type(fixture_id) is not str or fixture_id in result:
            raise ValueError("H25 fixture measurement identity is invalid.")
        outcome = item.get("outcome")
        if outcome not in OUTCOMES:
            raise ValueError("H25 fixture measurement outcome is invalid.")
        state_trace = item.get("state_trace")
        if type(state_trace) is not list or "PENDING_NEW" not in state_trace and outcome != "ALREADY_ACTIVE_HISTORY":
            raise ValueError("H25 state trace is invalid.")
        features = item.get("features")
        if features is not None:
            fields = _object(features, "candidate features")
            if fields.get("maximum_sample_read") != 16639:
                raise ValueError("H25 feature trace is not resolved at the sealed causal hop.")
            if not _finite(fields):
                raise ValueError("H25 candidate features contain a nonfinite value.")
        result[fixture_id] = item
    return result


def _graph_exact(evidence: Mapping[str, object]) -> bool:
    actual = evidence.get("typed_harmonic_graph")
    expected = list(build_typed_harmonic_graph())
    if actual != expected:
        return False
    seen: set[tuple[int, int]] = set()
    for item in actual:
        if type(item) is not dict:
            return False
        key = (item.get("source_pitch"), item.get("harmonic_rank"))
        if key in seen:
            return False
        seen.add(key)
        pitch, harmonic = key
        coordinate = item.get("observation_coordinate")
        relation = item.get("relation_type")
        if type(pitch) is not int or type(harmonic) is not int or type(coordinate) is not float:
            return False
        if harmonic == 1:
            if relation != "FUNDAMENTAL_IDENTITY" or coordinate != float(pitch):
                return False
        elif relation != "PROPER_HARMONIC_ASCENT" or not coordinate > pitch:
            return False
    return True


def _operator_exact(evidence: Mapping[str, object]) -> bool:
    raw_measurements = evidence.get("operator_measurements")
    if type(raw_measurements) is not list or not raw_measurements:
        return False
    for raw in raw_measurements:
        item = _object(raw, "operator measurement")
        if item.get("pair_support") != item.get("scalar_pair_support"):
            return False
        if item.get("baseline_valid") != item.get("scalar_baseline_valid"):
            return False
        for vector_key, scalar_key in (
            ("raw", "scalar_raw"),
            ("normalized", "scalar_normalized"),
            ("geometric_null", "scalar_geometric_null"),
            ("residual", "scalar_residual"),
        ):
            left = _array(item.get(vector_key), vector_key)
            right = _array(item.get(scalar_key), scalar_key)
            if len(left) != 89 or not _masked_close(left, right):
                return False
        support = _array(item.get("pair_support"), "pair support")
        residual = _array(item.get("residual"), "residual")
        if len(support) != 89 or any(type(value) is not bool for value in support):
            return False
        if any((value is None) != (not keep or not bool(item.get("baseline_valid"))) for value, keep in zip(residual, support)):
            return False
    return True


def _single_operator_measurement_exact(raw: object) -> bool:
    return _operator_exact({"operator_measurements": [raw]})


def _all_expected(plan: H25DormantScientificPlan, test: H25TestSpecification, measured: Mapping[str, Mapping[str, object]]) -> bool:
    fixture_by_id = {str(item["id"]): item for item in plan.fixtures}
    if tuple(measured) != test.fixture_ids:
        return False
    return all(measured[fixture_id]["outcome"] == _expected_outcome(fixture_by_id[fixture_id]) for fixture_id in test.fixture_ids)


def _phase_specific_primary(plan: H25DormantScientificPlan, test: H25TestSpecification, evidence: Mapping[str, object], measured: Mapping[str, Mapping[str, object]]) -> bool:
    if test.test_id == "H25-T-P0-001":
        return _graph_exact(evidence)
    if test.test_id in {"H25-T-P0-002", "H25-T-P0-005", "H25-T-P0-006", "H25-T-P0-008"}:
        operator_ok = _operator_exact(evidence)
        if test.test_id == "H25-T-P0-002":
            return operator_ok and evidence.get("analytic_equivalence_max_abs_error") == 0.0
        if test.test_id == "H25-T-P0-006":
            error = evidence.get("gain_invariance_max_abs_error")
            return operator_ok and type(error) is float and error <= 1e-12
        return operator_ok
    if test.test_id == "H25-T-P0-003":
        forbidden = {"raw_disappearance_index", "survival_index", "disappearance_transform"}
        primary_only = {key: value for key, value in evidence.items() if key != "inverse_measurement"}
        return not forbidden.intersection(str(primary_only))
    if test.test_id == "H25-T-P0-004":
        return bool(measured) and all(item["outcome"] == "AMBIGUOUS" for item in measured.values())
    if test.test_id == "H25-T-P0-007":
        return all(
            item.get("features") is not None
            and _object(item["features"], "features").get("maximum_sample_read") == 16639
            for item in measured.values()
        )
    if test.test_id == "H25-T-P0-009":
        return evidence.get("order_invariance") == "EXACT"
    if test.phase == "P1":
        return _all_expected(plan, test, measured)
    if test.test_id in {"H25-T-P2-001", "H25-T-P2-002", "H25-T-P2-006", "H25-T-P2-007"}:
        return evidence.get("invariance") == "EXACT"
    if test.test_id in {"H25-T-P2-003", "H25-T-P2-004", "H25-T-P2-005"}:
        return _all_expected(plan, test, measured)
    if test.test_id == "H25-T-P2-008":
        counters = _object(evidence.get("operational_counters"), "operational counters")
        return (
            type(counters.get("elapsed_ns_since_context_start")) is int
            and 0 <= int(counters["elapsed_ns_since_context_start"]) <= 600_000_000_000
            and type(counters.get("peak_rss_bytes")) is int
            and 0 <= int(counters["peak_rss_bytes"]) <= 4_294_967_296
            and counters.get("GPU_device_count") == 0
            and counters.get("scientific_process_count") == 1
            and counters.get("model_inference_call_count") == 0
            and counters.get("hidden_repeated_pitch_shift_inference_count") == 0
        )
    if test.test_id == "H25-T-P2-009":
        return evidence.get("attrition") == {
            "fixture_count": 36,
            "test_count": 27,
            "omitted_fixture_count": 0,
            "duplicate_fixture_count": 0,
            "extra_fixture_count": 0,
        }
    return False


def _inverse_exact(plan: H25DormantScientificPlan, test: H25TestSpecification, evidence: Mapping[str, object]) -> bool:
    inverse = _object(evidence.get("inverse_measurement"), "inverse measurement")
    if test.test_id == "H25-T-P0-001":
        mutated = inverse.get("mutated_typed_harmonic_graph")
        return type(mutated) is list and mutated != list(build_typed_harmonic_graph())
    if test.test_id in {"H25-T-P0-002", "H25-T-P0-005", "H25-T-P0-006", "H25-T-P0-008"}:
        mutated = inverse.get("misaligned_scalar_measurement")
        return type(mutated) is dict and not _single_operator_measurement_exact(mutated)
    if test.test_id == "H25-T-P0-003":
        return inverse.get("injected_feature_name") == "raw_disappearance_index"
    if test.test_id == "H25-T-P0-007":
        return type(inverse.get("maximum_sample_read")) is int and int(inverse["maximum_sample_read"]) > 16639
    if test.test_id == "H25-T-P0-009":
        return inverse.get("forced_order_invariance") == "DIFFERENT"
    if test.test_id in {"H25-T-P2-001", "H25-T-P2-002", "H25-T-P2-006", "H25-T-P2-007"}:
        return inverse.get("forced_invariance") == "DIFFERENT"
    if test.test_id == "H25-T-P2-008":
        return inverse.get("model_inference_call_count") == 1
    if test.test_id == "H25-T-P2-009":
        return inverse.get("omitted_fixture_count") == 1
    mutated_raw = inverse.get("mutated_fixture_measurements")
    if type(mutated_raw) is not list:
        return False
    mutated_evidence = dict(evidence)
    mutated_evidence["fixture_measurements"] = mutated_raw
    mutated = _measurement_map(mutated_evidence)
    return not _all_expected(plan, test, mutated)


def recompute_h25_persisted_evidence(plan: H25DormantScientificPlan, test_id: str, evidence: Mapping[str, object]) -> H25RecomputedEvidence:
    """Derive a test outcome from operands; never trust a producer verdict."""

    if type(evidence) is not dict:
        raise ValueError("H25 persisted evidence must be a JSON object.")
    forbidden = {"pass", "passed", "verdict", "final_pass", "primary_pass", "inverse_pass"}
    if forbidden.intersection(evidence):
        raise ValueError("H25 producer evidence contains a forbidden self-declared verdict.")
    if not _finite(evidence):
        raise ValueError("H25 persisted evidence contains a nonfinite value.")
    test = _test(plan, test_id)
    if (
        evidence.get("schema_version") != 1
        or evidence.get("test_id") != test.test_id
        or evidence.get("phase") != test.phase
        or evidence.get("objective") != test.objective
    ):
        raise ValueError("H25 persisted evidence identity mismatch.")
    measured = _measurement_map(evidence)
    primary = _phase_specific_primary(plan, test, evidence, measured)
    inverse = _inverse_exact(plan, test, evidence)
    return H25RecomputedEvidence(
        test_id=test.test_id,
        phase=test.phase,
        primary_pass=primary,
        inverse_pass=inverse,
        final_pass=primary and inverse,
        diagnostics={
            "fixture_measurement_count": len(measured),
            "expected_fixture_count": len(test.fixture_ids),
            "primary_pass": primary,
            "inverse_pass": inverse,
        },
    )


__all__ = ["H25RecomputedEvidence", "recompute_h25_persisted_evidence"]
