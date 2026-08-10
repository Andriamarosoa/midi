"""Closed H24 operators and independent recomputation from persisted evidence.

No producer verdict is accepted.  The functions in this module consume only
JSON-native operands already persisted by a future separately authorized
producer.  This module performs no synthesis, inference, data loading, or test
execution on its own.
"""
from __future__ import annotations

from dataclasses import dataclass
from collections import Counter
import math
from typing import Callable, Mapping, Sequence

from .harmonic_censoring_h24 import (
    H24DormantHarnessPlan,
    H24TestSpecification,
    _require_h24_attested_plan,
    canonical_json_bytes,
)


@dataclass(frozen=True)
class H24RecomputedOracle:
    test_id: str
    primary_pass: bool
    inverse_pass: bool

    @property
    def final_pass(self) -> bool:
        return self.primary_pass and self.inverse_pass


def _array(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"H24 {label} must be an array.")
    return value


def _object(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"H24 {label} must be an object.")
    return value


def _pair(value: object, label: str) -> tuple[object, object]:
    items = _array(value, label)
    if len(items) != 2:
        raise ValueError(f"H24 {label} must contain exactly two operands.")
    return items[0], items[1]


def _finite_numeric(value: object, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(float(value)):
        raise ValueError(f"H24 {label} must be a finite JSON number.")
    return float(value)


def _contains_nonfinite(value: object) -> bool:
    if type(value) is float:
        return not math.isfinite(value)
    if type(value) is list:
        return any(_contains_nonfinite(item) for item in value)
    if type(value) is dict:
        return any(_contains_nonfinite(item) for item in value.values())
    return False


def _require_json_native(value: object, label: str) -> None:
    if value is None or type(value) in (bool, int, str):
        return
    if type(value) is float:
        if not math.isfinite(value):
            raise ValueError(f"H24 {label} contains a nonfinite number.")
        return
    if type(value) is list:
        for item in value:
            _require_json_native(item, label)
        return
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise ValueError(f"H24 {label} object keys must be strings.")
        for item in value.values():
            _require_json_native(item, label)
        return
    raise ValueError(f"H24 {label} must use JSON-native types only.")


def strict_equal(left: object, right: object) -> bool:
    """JSON-native recursive equality with bool/int/float kept distinct."""

    if _contains_nonfinite(left) or _contains_nonfinite(right):
        return False
    if type(left) is not type(right):
        return False
    if type(left) is list:
        return len(left) == len(right) and all(  # type: ignore[arg-type]
            strict_equal(a, b) for a, b in zip(left, right)  # type: ignore[arg-type]
        )
    if type(left) is dict:
        return set(left) == set(right) and all(  # type: ignore[arg-type]
            strict_equal(left[key], right[key]) for key in left  # type: ignore[index]
        )
    return bool(left == right)


def _allclose(left: object, right: object, rtol: float, atol: float) -> bool:
    if type(left) is list or type(right) is list:
        if type(left) is not list or type(right) is not list:
            return False
        return len(left) == len(right) and all(
            _allclose(a, b, rtol, atol) for a, b in zip(left, right)
        )
    if type(left) not in (int, float) or type(right) not in (int, float):
        return False
    a = float(left)
    b = float(right)
    if not math.isfinite(a) or not math.isfinite(b):
        return False
    return abs(a - b) <= max(atol, rtol * max(abs(a), abs(b)))


def _require_nonempty_array(value: object, label: str) -> list[object]:
    items = _array(value, label)
    if not items:
        raise ValueError(f"H24 {label} evidence must be non-empty.")
    return items


def _validate_tolerances(rule: Mapping[str, object], uses_tolerance: bool) -> tuple[float, float]:
    rtol = _finite_numeric(rule.get("rtol"), "rtol")
    atol = _finite_numeric(rule.get("atol"), "atol")
    if rtol < 0.0 or atol < 0.0:
        raise ValueError("H24 rtol/atol must be nonnegative.")
    if not uses_tolerance and (rtol != 0.0 or atol != 0.0):
        raise ValueError("H24 operator without tolerance requires zero rtol/atol.")
    return rtol, atol


def _expand_expected(
    expected: object, plan_fixture_ids: Sequence[str], sentinels: Mapping[str, object]
) -> object:
    if type(expected) is str and expected.startswith("__") and expected.endswith("__"):
        if expected not in sentinels:
            raise ValueError(f"H24 unknown evidence sentinel {expected!r}.")
        if expected != "__PLAN_FIXTURE_IDS__":
            raise ValueError(f"H24 unsupported evidence sentinel {expected!r}.")
        return list(plan_fixture_ids)
    return expected


def _support_formula_exact(value: object) -> bool:
    triples = _require_nonempty_array(value, "support formula")
    for raw in triples:
        triple = _array(raw, "support formula triple")
        if len(triple) != 3 or type(triple[0]) is not bool or type(triple[2]) is not bool:
            return False
        frequency = _finite_numeric(triple[1], "support frequency")
        if triple[0] is not ((frequency <= 22050.0) and triple[2]):
            return False
    return True


def _d08_traces_exact(value: object) -> bool:
    traces = _require_nonempty_array(value, "D08 traces")
    offsets: list[object] = []
    exact_keys = {
        "offset",
        "event_hop",
        "states",
        "target_category",
        "resolved_category",
        "pending_lifetime",
    }
    for raw in traces:
        if type(raw) is not dict or set(raw) != exact_keys:
            return False
        trace = raw
        offset = trace["offset"]
        states = trace["states"]
        if type(offset) is not int or type(states) is not list:
            return False
        event_hop = offset // 256
        if trace["event_hop"] != event_hop:
            return False
        expected_states = ["INACTIVE"] + [
            "INACTIVE"
            if hop < event_hop
            else "PENDING_NEW"
            if hop == event_hop
            else "ACTIVE"
            for hop in range(16)
        ]
        if 4096 - offset < 3840:
            expected_states.append("ACTIVE")
        if not strict_equal(states, expected_states):
            return False
        offsets.append(offset)
    return offsets == [0, 1, 255, 256, 3840, 4095]


def _timing_components_exact(value: object) -> bool:
    return type(value) is dict and set(value) == {
        "window",
        "hop",
        "feature",
        "inference",
        "decoder",
        "MIDI",
    } and all(type(item) is int and item >= 0 for item in value.values())


def _ts01_evidence_exact(value: object, plan_fixture_ids: Sequence[str]) -> bool:
    if type(value) is not dict or set(value) != {
        "all_fixture_ids",
        "passed_at_6",
        "failed_at_6",
        "rescued_at_16",
        "rescued_at_32",
        "regressed_at_16",
        "regressed_at_32",
    }:
        return False
    if any(type(items) is not list for items in value.values()):
        return False
    all_ids = value["all_fixture_ids"]
    passed = value["passed_at_6"]
    failed = value["failed_at_6"]
    if all_ids != sorted(plan_fixture_ids):
        return False
    if sorted(passed + failed) != all_ids or set(passed).intersection(failed):
        return False
    return (
        set(value["rescued_at_16"]).issubset(failed)
        and set(value["rescued_at_32"]).issubset(failed)
        and set(value["regressed_at_16"]).issubset(passed)
        and set(value["regressed_at_32"]).issubset(passed)
    )


def evaluate_h24_operator(
    operator: str,
    value: object,
    expected: object,
    *,
    rtol: float,
    atol: float,
    plan_fixture_ids: Sequence[str],
) -> bool:
    """Evaluate one already validated closed-world H24 operator."""

    if _contains_nonfinite(value) or _contains_nonfinite(expected):
        return False
    if operator == "eq":
        return strict_equal(value, expected)
    if operator == "ne":
        return not strict_equal(value, expected)
    if operator == "in":
        return any(strict_equal(value, item) for item in _require_nonempty_array(expected, "allowed values"))
    if operator in {"gt", "ge", "le"}:
        left = _finite_numeric(value, operator)
        right = _finite_numeric(expected, f"{operator} expected")
        return left > right if operator == "gt" else left >= right if operator == "ge" else left <= right
    if operator == "close":
        return _allclose(value, expected, rtol, atol)
    if operator in {"pair_equal", "pair_different", "close_pair", "allclose_pair"}:
        left, right = _pair(value, operator)
        equal = _allclose(left, right, rtol, atol) if "close" in operator else strict_equal(left, right)
        return equal if operator in {"pair_equal", "close_pair", "allclose_pair"} else not equal
    if operator in {"all_equal", "not_all_equal"}:
        items = _require_nonempty_array(value, operator)
        if operator == "not_all_equal" and len(items) < 2:
            return False
        equal = all(strict_equal(items[0], item) for item in items[1:])
        return equal if operator == "all_equal" else not equal
    if operator == "all_eq":
        return all(strict_equal(item, expected) for item in _require_nonempty_array(value, operator))
    if operator == "all_in":
        items = _require_nonempty_array(value, operator)
        allowed = _require_nonempty_array(expected, "allowed values")
        return all(any(strict_equal(item, option) for option in allowed) for item in items)
    if operator == "all_true":
        return all(item is True for item in _require_nonempty_array(value, operator))
    if operator == "none_in":
        items = _require_nonempty_array(value, operator)
        low, high = _pair(expected, "inclusive interval")
        if type(low) is not int or type(high) is not int or any(type(item) is not int for item in items):
            return False
        return all(not (low <= item <= high) for item in items)
    if operator in {"all_exact_pairs", "allclose_pairs", "any_different_pair"}:
        pairs = [_pair(item, operator) for item in _require_nonempty_array(value, operator)]
        equalities = [
            _allclose(left, right, rtol, atol)
            if operator == "allclose_pairs"
            else strict_equal(left, right)
            for left, right in pairs
        ]
        return any(not item for item in equalities) if operator == "any_different_pair" else all(equalities)
    if operator == "allclose_all":
        items = _require_nonempty_array(value, operator)
        return all(_allclose(items[0], item, rtol, atol) for item in items[1:])
    if operator in {"strictly_gain_ordered", "nonincreasing"}:
        items = _require_nonempty_array(value, operator)
        if len(items) < 2:
            return False
        numbers = [_finite_numeric(item, operator) for item in items]
        if operator == "strictly_gain_ordered":
            return all(left < right for left, right in zip(numbers, numbers[1:]))
        return all(right - left <= atol for left, right in zip(numbers, numbers[1:]))
    if operator == "support_formula_exact":
        return _support_formula_exact(value)
    if operator == "d08_traces_exact":
        return _d08_traces_exact(value)
    if operator == "timing_components_exact":
        return _timing_components_exact(value)
    if operator == "ts01_evidence_exact":
        return _ts01_evidence_exact(value, plan_fixture_ids)
    raise ValueError(f"H24 unknown sealed operator {operator!r}.")


def _cardinality_requirement(
    plan: H24DormantHarnessPlan, test_id: str, side: str, name: str
) -> int | None:
    contract = plan.evidence_nonvacuity_contract
    overrides = _object(contract.get("cardinality_overrides"), "cardinality overrides")
    test_override = overrides.get(test_id)
    if test_override is None:
        return None
    side_override = _object(_object(test_override, test_id).get(side), f"{test_id} {side}")
    rule_override = side_override.get(name)
    if rule_override is None:
        return None
    exact = _object(rule_override, f"{test_id} {name}").get("exact_items")
    if type(exact) is not int or exact < 1:
        raise ValueError(f"H24 {test_id} {name} exact cardinality is invalid.")
    return exact


def evaluate_h24_rule(
    plan: H24DormantHarnessPlan,
    test_id: str,
    side: str,
    rule: Mapping[str, object],
    value: object,
) -> bool:
    plan = _require_h24_attested_plan(plan)
    if set(rule) != {"name", "operator", "expected", "rtol", "atol"}:
        raise ValueError(f"H24 {test_id} evidence rule keys mismatch.")
    name = rule["name"]
    operator = rule["operator"]
    if type(name) is not str or type(operator) is not str:
        raise ValueError(f"H24 {test_id} evidence rule identity is invalid.")
    if operator not in plan.operator_registry:
        raise ValueError(f"H24 unknown evidence operator {operator!r}.")
    _require_json_native(value, f"{test_id} {name} evidence")
    _require_json_native(rule["expected"], f"{test_id} {name} expected")
    if type(value) is list:
        minimum = plan.evidence_nonvacuity_contract.get(
            "array_evidence_default_minimum_items"
        )
        if type(minimum) is not int or len(value) < minimum:
            raise ValueError(f"H24 {test_id} {name} evidence is vacuous.")
        exact = _cardinality_requirement(plan, test_id, side, name)
        if exact is not None and len(value) != exact:
            raise ValueError(
                f"H24 {test_id} {name} evidence requires exactly {exact} items."
            )
    operator_spec = plan.operator_registry[operator]
    uses_tolerance = operator_spec.get("uses_rtol_atol") is True
    rtol, atol = _validate_tolerances(rule, uses_tolerance)
    expected = _expand_expected(
        rule["expected"], plan.fixture_ids, plan.sentinel_registry
    )
    return evaluate_h24_operator(
        operator,
        value,
        expected,
        rtol=rtol,
        atol=atol,
        plan_fixture_ids=plan.fixture_ids,
    )


def _test_by_id(plan: H24DormantHarnessPlan, test_id: str) -> H24TestSpecification:
    if test_id not in plan.evaluator_registry:
        raise KeyError(f"H24 unregistered evaluator {test_id!r}.")
    for test in plan.tests:
        if test.test_id == test_id:
            return test
    raise RuntimeError(f"H24 evaluator registry has no specification for {test_id}.")


def _recompute_generic(
    plan: H24DormantHarnessPlan,
    test: H24TestSpecification,
    persisted_evidence: object,
) -> H24RecomputedOracle:
    evidence = _object(persisted_evidence, f"{test.test_id} persisted evidence")
    if set(evidence) != {"primary", "inverse"}:
        raise ValueError(f"H24 {test.test_id} evidence requires primary/inverse only.")
    primary_values = _object(evidence["primary"], f"{test.test_id} primary evidence")
    inverse_values = _object(evidence["inverse"], f"{test.test_id} inverse evidence")
    schema = _object(test.as_dict().get("evidence_schema"), "evidence schema")
    primary_rules = [_object(item, "primary rule") for item in _array(schema.get("primary_rules"), "primary rules")]
    inverse_rules = [_object(item, "inverse rule") for item in _array(schema.get("inverse_rules"), "inverse rules")]
    if set(primary_values) != {rule["name"] for rule in primary_rules}:
        raise ValueError(f"H24 {test.test_id} primary evidence keys mismatch.")
    if set(inverse_values) != {rule["name"] for rule in inverse_rules}:
        raise ValueError(f"H24 {test.test_id} inverse evidence keys mismatch.")
    primary_pass = all(
        evaluate_h24_rule(plan, test.test_id, "primary", rule, primary_values[rule["name"]])
        for rule in primary_rules
    )
    inverse_pass = all(
        evaluate_h24_rule(plan, test.test_id, "inverse", rule, inverse_values[rule["name"]])
        for rule in inverse_rules
    )
    return H24RecomputedOracle(test.test_id, primary_pass, inverse_pass)


def _expected_h24_edges() -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for source_pitch in range(24, 77):
        for harmonic_rank in range(1, 21):
            if harmonic_rank ** 12 > 2 ** (128 - source_pitch):
                continue
            result.append(
                {
                    "source_pitch": source_pitch,
                    "harmonic_rank": harmonic_rank,
                    "observation_coordinate": float(source_pitch)
                    + 12.0 * math.log2(float(harmonic_rank)),
                    "relation_type": "FUNDAMENTAL_IDENTITY"
                    if harmonic_rank == 1
                    else "PROPER_HARMONIC_ASCENT",
                }
            )
    return result


def _edge_diagnostics(value: object) -> tuple[bool, dict[str, object]]:
    edges = _array(value, "typed edges")
    expected = _expected_h24_edges()
    expected_by_key = {
        (edge["source_pitch"], edge["harmonic_rank"]): edge for edge in expected
    }
    observed_keys: list[tuple[int, int]] = []
    coordinate_mismatches: list[list[int]] = []
    relation_mismatches: list[list[int]] = []
    malformed = False
    for raw in edges:
        if type(raw) is not dict or set(raw) != {
            "source_pitch",
            "harmonic_rank",
            "observation_coordinate",
            "relation_type",
        }:
            malformed = True
            continue
        pitch = raw["source_pitch"]
        rank = raw["harmonic_rank"]
        if type(pitch) is not int or type(rank) is not int:
            malformed = True
            continue
        key = (pitch, rank)
        observed_keys.append(key)
        expected_edge = expected_by_key.get(key)
        if expected_edge is None:
            continue
        coordinate = raw["observation_coordinate"]
        if type(coordinate) not in (int, float) or not math.isfinite(float(coordinate)):
            coordinate_mismatches.append([pitch, rank])
        else:
            target = float(expected_edge["observation_coordinate"])
            if abs(float(coordinate) - target) > max(1e-12, 1e-15 * abs(target)):
                coordinate_mismatches.append([pitch, rank])
        if raw["relation_type"] != expected_edge["relation_type"]:
            relation_mismatches.append([pitch, rank])
    expected_keys = set(expected_by_key)
    observed_set = set(observed_keys)
    duplicate_keys = sorted({key for key in observed_keys if observed_keys.count(key) > 1})
    diagnostics: dict[str, object] = {
        "recomputed_expected_edges": expected,
        "missing_keys": [list(key) for key in sorted(expected_keys - observed_set)],
        "extra_keys": [list(key) for key in sorted(observed_set - expected_keys)],
        "duplicate_keys": [list(key) for key in duplicate_keys],
        "coordinate_mismatches": coordinate_mismatches,
        "relation_type_mismatches": relation_mismatches,
    }
    valid = not malformed and all(not diagnostics[key] for key in diagnostics if key != "recomputed_expected_edges")
    return valid, diagnostics


_H24_EDGE_KEYS = {
    "source_pitch",
    "harmonic_rank",
    "observation_coordinate",
    "relation_type",
}


def _valid_edge_record(raw: object) -> bool:
    if type(raw) is not dict or set(raw) != _H24_EDGE_KEYS:
        return False
    return (
        type(raw["source_pitch"]) is int
        and type(raw["harmonic_rank"]) is int
        and type(raw["observation_coordinate"]) in (int, float)
        and math.isfinite(float(raw["observation_coordinate"]))
        and type(raw["relation_type"]) is str
    )


def _edge_key(raw: Mapping[str, object]) -> tuple[int, int]:
    return int(raw["source_pitch"]), int(raw["harmonic_rank"])


def _unique_edge_map(value: object) -> dict[tuple[int, int], dict[str, object]] | None:
    if type(value) is not list or any(not _valid_edge_record(item) for item in value):
        return None
    result: dict[tuple[int, int], dict[str, object]] = {}
    for raw in value:
        edge = raw
        key = _edge_key(edge)
        if key in result:
            return None
        result[key] = edge
    return result


def _single_same_key_mutation(
    primary_edges: object,
    mutated_edges: object,
    predicate: Callable[[Mapping[str, object], Mapping[str, object]], bool],
) -> bool:
    primary = _unique_edge_map(primary_edges)
    mutated = _unique_edge_map(mutated_edges)
    if primary is None or mutated is None or set(primary) != set(mutated):
        return False
    changed = [key for key in primary if not strict_equal(primary[key], mutated[key])]
    if len(changed) != 1:
        return False
    return predicate(primary[changed[0]], mutated[changed[0]])


def _only_field_changed(
    before: Mapping[str, object], after: Mapping[str, object], field: str
) -> bool:
    return all(
        strict_equal(before[name], after[name])
        for name in _H24_EDGE_KEYS
        if name != field
    ) and not strict_equal(before[field], after[field])


def _canonical_edge_counter(value: object) -> Counter[bytes] | None:
    if type(value) is not list or any(not _valid_edge_record(item) for item in value):
        return None
    try:
        return Counter(canonical_json_bytes(item) for item in value)
    except (TypeError, ValueError):
        return None


def _one_added_record(
    primary_edges: object, mutated_edges: object
) -> tuple[dict[str, object], Counter[bytes], Counter[bytes]] | None:
    primary_counter = _canonical_edge_counter(primary_edges)
    mutated_counter = _canonical_edge_counter(mutated_edges)
    if primary_counter is None or mutated_counter is None:
        return None
    if type(primary_edges) is not list or type(mutated_edges) is not list:
        return None
    if len(mutated_edges) != len(primary_edges) + 1:
        return None
    if primary_counter - mutated_counter:
        return None
    added = mutated_counter - primary_counter
    if sum(added.values()) != 1:
        return None
    token = next(iter(added))
    extra = next(
        item for item in mutated_edges if canonical_json_bytes(item) == token
    )
    return extra, primary_counter, mutated_counter


def _a01_i1_exact(primary_edges: object, mutated_edges: object) -> bool:
    def predicate(before: Mapping[str, object], after: Mapping[str, object]) -> bool:
        return (
            before["harmonic_rank"] == 1
            and _only_field_changed(before, after, "observation_coordinate")
            and float(after["observation_coordinate"]) != float(before["source_pitch"])
        )

    return _single_same_key_mutation(primary_edges, mutated_edges, predicate)


def _a01_i2_exact(primary_edges: object, mutated_edges: object) -> bool:
    def predicate(before: Mapping[str, object], after: Mapping[str, object]) -> bool:
        return (
            2 <= int(before["harmonic_rank"]) <= 20
            and _only_field_changed(before, after, "observation_coordinate")
            and float(after["observation_coordinate"]) == float(before["source_pitch"])
        )

    return _single_same_key_mutation(primary_edges, mutated_edges, predicate)


def _a01_i3_exact(primary_edges: object, mutated_edges: object) -> bool:
    result = _one_added_record(primary_edges, mutated_edges)
    if result is None:
        return False
    extra, _, _ = result
    return (
        24 <= int(extra["source_pitch"]) <= 76
        and 2 <= int(extra["harmonic_rank"]) <= 20
        and float(extra["observation_coordinate"]) < float(extra["source_pitch"])
        and extra["relation_type"] == "PROPER_HARMONIC_ASCENT"
    )


def _a01_i4_exact(primary_edges: object, mutated_edges: object) -> bool:
    def predicate(before: Mapping[str, object], after: Mapping[str, object]) -> bool:
        return (
            before["harmonic_rank"] == 1
            and _only_field_changed(before, after, "relation_type")
            and after["relation_type"] == "PROPER_HARMONIC_ASCENT"
        )

    return _single_same_key_mutation(primary_edges, mutated_edges, predicate)


def _a01_i5_exact(primary_edges: object, mutated_edges: object) -> bool:
    primary_counter = _canonical_edge_counter(primary_edges)
    mutated_counter = _canonical_edge_counter(mutated_edges)
    if primary_counter is None or mutated_counter is None:
        return False
    if type(primary_edges) is not list or type(mutated_edges) is not list:
        return False
    return (
        len(mutated_edges) == len(primary_edges) - 1
        and not (mutated_counter - primary_counter)
        and sum((primary_counter - mutated_counter).values()) == 1
    )


def _a01_i6_exact(primary_edges: object, mutated_edges: object) -> bool:
    result = _one_added_record(primary_edges, mutated_edges)
    if result is None:
        return False
    extra, primary_counter, _ = result
    return canonical_json_bytes(extra) in primary_counter


def _a01_i7_exact(primary_edges: object, mutated_edges: object) -> bool:
    def predicate(before: Mapping[str, object], after: Mapping[str, object]) -> bool:
        delta = float(after["observation_coordinate"]) - float(
            before["observation_coordinate"]
        )
        return (
            _only_field_changed(before, after, "observation_coordinate")
            and math.isclose(delta, 0.25, rel_tol=0.0, abs_tol=1e-12)
            and float(after["observation_coordinate"]) > float(after["source_pitch"])
        )

    return _single_same_key_mutation(primary_edges, mutated_edges, predicate)


def _a01_inverse_suite_exact(
    primary_edges: object, inverse: Mapping[str, object]
) -> bool:
    validators = {
        "H24-A01-I1": _a01_i1_exact,
        "H24-A01-I2": _a01_i2_exact,
        "H24-A01-I3": _a01_i3_exact,
        "H24-A01-I4": _a01_i4_exact,
        "H24-A01-I5": _a01_i5_exact,
        "H24-A01-I6": _a01_i6_exact,
        "H24-A01-I7": _a01_i7_exact,
    }
    return set(inverse) == set(validators) and all(
        validator(primary_edges, inverse[inverse_id])
        for inverse_id, validator in validators.items()
    )


def _recompute_a01(
    test: H24TestSpecification, persisted_evidence: object
) -> H24RecomputedOracle:
    evidence = _object(persisted_evidence, "H24-A01 persisted evidence")
    if set(evidence) != {"primary", "inverse"}:
        raise ValueError("H24-A01 evidence requires primary/inverse only.")
    primary = _object(evidence["primary"], "H24-A01 primary evidence")
    inverse = _object(evidence["inverse"], "H24-A01 inverse evidence")
    schema = _object(test.as_dict()["evidence_schema"], "H24-A01 evidence schema")
    primary_names = _array(schema["primary_required_fields"], "H24-A01 primary fields")
    inverse_names = _array(schema["inverse_required_fields"], "H24-A01 inverse fields")
    if set(primary) != set(primary_names) or set(inverse) != set(inverse_names):
        raise ValueError("H24-A01 evidence keys mismatch.")
    graph_pass, diagnostics = _edge_diagnostics(primary["typed_edges"])
    diagnostics_pass = all(
        strict_equal(primary[name], diagnostics[name])
        for name in primary_names
        if name != "typed_edges"
    )
    inverse_pass = graph_pass and _a01_inverse_suite_exact(
        primary["typed_edges"], inverse
    )
    return H24RecomputedOracle(test.test_id, graph_pass and diagnostics_pass, inverse_pass)


def recompute_h24_persisted_evidence(
    plan: H24DormantHarnessPlan, test_id: str, persisted_evidence: object
) -> H24RecomputedOracle:
    """Recompute evidence only; never invoke a producer or scientific evaluator."""

    plan = _require_h24_attested_plan(plan)
    if "pass" in _object(persisted_evidence, "persisted evidence") or "verdict" in persisted_evidence:
        raise ValueError("H24 producer pass/verdict fields are forbidden.")
    test = _test_by_id(plan, test_id)
    if test_id == "H24-A01-GRAPH-DIRECTION":
        return _recompute_a01(test, persisted_evidence)
    return _recompute_generic(plan, test, persisted_evidence)


def require_h24_evidence_production_authorized(_: object) -> None:
    raise PermissionError(
        "H24 evidence production remains unauthorized; producer registry is dormant."
    )


__all__ = [
    "H24RecomputedOracle",
    "evaluate_h24_operator",
    "evaluate_h24_rule",
    "recompute_h24_persisted_evidence",
    "require_h24_evidence_production_authorized",
    "strict_equal",
]
