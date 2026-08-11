"""Independent pure-Python recomputer for persisted H25 evidence.

This module deliberately imports no H25 producer code, numerical constants,
NumPy, population loader, or runner.  It reconstructs the sealed graph,
operator, causal state and outcomes from JSON-native raw operands.
"""
from __future__ import annotations

import math
import hashlib
import json
import struct
from dataclasses import dataclass
from typing import Any, Mapping, Sequence


_RTOL = 1e-10
_ATOL = 1e-12
_BASELINE_ABSOLUTE_MIN = 1e-24
_BASELINE_RELATIVE_MIN = 1e-12
_SAMPLE_RATE = 44100.0
_OUTCOMES = {"BIRTH_SUPPORTED", "NO_BIRTH", "ALREADY_ACTIVE_HISTORY", "AMBIGUOUS"}
_P2_007_SELF_PROJECTION = "H25_P2_007_NONRECURSIVE_SELF_CORE_V1"
_SCIENTIFIC_RUNTIME_FIELDS = {
    "implementation", "version", "platform_system", "platform_release",
    "platform_machine", "resolved_executable", "executable_size_bytes",
    "executable_sha256", "numpy_version", "numpy_multiarray_path",
    "numpy_multiarray_size_bytes", "numpy_multiarray_sha256", "blas_provider",
    "blas_library_path", "blas_library_size_bytes", "blas_library_sha256",
    "process_environment_exact",
}
_TRANSPORT_IDENTITY_FIELDS = {
    "command_sha256", "observer_payload_path", "observer_payload_size_bytes",
    "observer_payload_sha256",
}


@dataclass(frozen=True)
class H25RecomputedEvidence:
    test_id: str
    phase: str
    primary_pass: bool
    inverse_pass: bool
    final_pass: bool
    diagnostics: Mapping[str, object]


def _test(plan: object, test_id: str) -> object:
    matches = [item for item in getattr(plan, "tests") if getattr(item, "test_id") == test_id]
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
    return math.isclose(left, right, rel_tol=_RTOL, abs_tol=_ATOL)


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


def _independent_graph() -> list[dict[str, object]]:
    graph: list[dict[str, object]] = []
    for pitch in range(24, 77):
        for harmonic in range(1, 21):
            coordinate = pitch + 12.0 * math.log2(float(harmonic))
            if coordinate <= 128.0:
                graph.append({
                    "source_pitch": pitch,
                    "harmonic_rank": harmonic,
                    "observation_coordinate": float(coordinate),
                    "relation_type": "FUNDAMENTAL_IDENTITY" if harmonic == 1 else "PROPER_HARMONIC_ASCENT",
                })
    return graph


def _replay_active(trace_raw: object, *, expected_fixture_id: str) -> tuple[int, ...]:
    trace = _object(trace_raw, "causal replay trace")
    if set(trace) != {"fixture_id", "observed_through_sample", "initial_active_pitches", "transitions", "derived_active_pitches"}:
        raise ValueError("H25 causal replay trace schema is invalid.")
    if trace["fixture_id"] != expected_fixture_id:
        raise ValueError("H25 causal replay trace fixture identity mismatch.")
    through = trace["observed_through_sample"]
    if type(through) is not int or through != 16383:
        raise ValueError("H25 causal replay trace is not target-hop bounded.")
    initial = _array(trace["initial_active_pitches"], "initial active pitches")
    if initial:
        raise ValueError("H25 causal replay must start with every pitch INACTIVE.")
    active = set()
    for pitch in initial:
        if type(pitch) is not int or not 24 <= pitch <= 76:
            raise ValueError("H25 initial active pitch is invalid.")
        active.add(pitch)
    for raw in _array(trace["transitions"], "causal transitions"):
        item = _object(raw, "causal transition")
        if set(item) != {"sample_index", "kind", "pitch"}:
            raise ValueError("H25 causal transition schema is invalid.")
        sample = item["sample_index"]
        pitch = item["pitch"]
        if type(sample) is not int or sample > through or type(pitch) is not int or not 24 <= pitch <= 76:
            raise ValueError("H25 causal transition reads invalid/future state.")
        if item["kind"] == "note_on":
            active.add(pitch)
        elif item["kind"] == "note_off":
            active.discard(pitch)
        else:
            raise ValueError("H25 causal transition kind is invalid.")
    result = tuple(sorted(active))
    if list(result) != trace["derived_active_pitches"]:
        raise ValueError("H25 producer active state differs from independent replay.")
    return result


def _derive_outcome(item: Mapping[str, object]) -> str:
    pitch = item.get("candidate_pitch")
    if pitch is None:
        return "AMBIGUOUS"
    if type(pitch) is not int:
        raise ValueError("H25 candidate pitch is invalid.")
    fixture_id = item.get("fixture_id")
    if type(fixture_id) is not str:
        raise ValueError("H25 fixture measurement identity is invalid.")
    active = _replay_active(item.get("causal_replay_trace"), expected_fixture_id=fixture_id)
    if pitch in active:
        return "ALREADY_ACTIVE_HISTORY"
    features = _object(item.get("features"), "candidate features")
    if features.get("maximum_sample_read") != 16639:
        raise ValueError("H25 resolution feature is not one hop after target.")
    if features.get("short_valid") is not True or features.get("long_valid") is not True:
        return "AMBIGUOUS"
    names = (
        "short_window_onset_rise", "short_window_harmonic_novelty",
        "short_window_new_energy", "old_source_explanation_residual",
        "dilution_residual_change_l1",
    )
    values = [features.get(name) for name in names]
    if any(type(value) not in {int, float} or not math.isfinite(float(value)) for value in values):
        return "AMBIGUOUS"
    onset, novelty, new_energy, old_residual, dilution = (float(value) for value in values)
    if onset > _ATOL and novelty > _ATOL and new_energy > _ATOL and old_residual > _ATOL and dilution >= 0.0:
        return "BIRTH_SUPPORTED"
    if onset <= _ATOL and novelty <= _ATOL and new_energy <= _ATOL:
        return "NO_BIRTH" if old_residual <= _ATOL else "AMBIGUOUS"
    return "AMBIGUOUS"


def _measurement_map(evidence: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    result: dict[str, Mapping[str, object]] = {}
    for raw in _array(evidence.get("fixture_measurements"), "fixture measurements"):
        item = _object(raw, "fixture measurement")
        fixture_id = item.get("fixture_id")
        if type(fixture_id) is not str or fixture_id in result:
            raise ValueError("H25 fixture measurement identity is invalid.")
        derived = _derive_outcome(item)
        declared = item.get("outcome")
        if declared not in _OUTCOMES or declared != derived:
            raise ValueError("H25 producer outcome differs from independently derived outcome.")
        result[fixture_id] = item
    return result


def _independent_operator(raw: object) -> dict[str, object]:
    operands = _object(raw, "raw operator operands")
    if set(operands) != {"candidate_pitch", "power", "frequencies_hz"}:
        raise ValueError("H25 raw operator operand schema is invalid.")
    pitch = operands["candidate_pitch"]
    power = _array(operands["power"], "power bins")
    hz = _array(operands["frequencies_hz"], "frequency bins")
    if type(pitch) is not int or not 40 <= pitch <= 76 or len(power) != len(hz) or len(power) < 2:
        raise ValueError("H25 raw operator dimensions are invalid.")
    values = [float(value) for value in power]
    frequencies = [float(value) for value in hz]
    if any(not math.isfinite(value) or value < 0.0 for value in values):
        raise ValueError("H25 power operand is invalid.")
    if frequencies[0] != 0.0 or any(not math.isfinite(value) for value in frequencies) or any(b <= a for a, b in zip(frequencies, frequencies[1:])):
        raise ValueError("H25 frequency operand is invalid.")
    energies: list[float] = []
    masses: list[float] = []
    coordinates: list[float] = []
    supported: list[bool] = []
    for harmonic in range(1, 21):
        coordinate = pitch + 12.0 * math.log2(float(harmonic))
        target_hz = 440.0 * math.pow(2.0, (coordinate - 69.0) / 12.0)
        kernel = []
        for frequency in frequencies:
            if frequency <= 0.0:
                kernel.append(0.0)
            else:
                kernel.append(max(0.0, 1.0 - abs(1200.0 * math.log2(frequency / target_hz)) / 35.0))
        mass = math.fsum(kernel)
        coordinates.append(coordinate)
        energies.append(math.fsum(value * weight for value, weight in zip(values, kernel)) / harmonic)
        masses.append(mass / harmonic)
        supported.append(coordinate <= 128.0 and target_hz <= _SAMPLE_RATE / 2.0 and mass > 0.0)
    raw_values: list[float] = []
    null_values: list[float] = []
    pair_support: list[bool] = []
    for shift in range(89):
        keep = [base and coordinate + shift <= 128.0 for base, coordinate in zip(supported, coordinates)]
        pair_support.append(any(keep))
        raw_values.append(math.fsum(value for value, flag in zip(energies, keep) if flag))
        null_values.append(math.fsum(value for value, flag in zip(masses, keep) if flag))
    total = math.fsum(values)
    baseline_valid = raw_values[0] > max(_BASELINE_ABSOLUTE_MIN, _BASELINE_RELATIVE_MIN * total)
    result: dict[str, object] = {"pair_support": pair_support, "baseline_valid": baseline_valid}
    for key in ("raw", "normalized", "geometric_null", "residual"):
        result[key] = []
    for keep, raw_value, null_value in zip(pair_support, raw_values, null_values):
        result["raw"].append(raw_value if keep else None)
        if not keep or not baseline_valid or null_values[0] <= 0.0:
            result["normalized"].append(None)
            result["geometric_null"].append(None)
            result["residual"].append(None)
        else:
            normalized = raw_value / raw_values[0]
            null = null_value / null_values[0]
            result["normalized"].append(normalized)
            result["geometric_null"].append(null)
            result["residual"].append(normalized - null)
    return result


def _operator_exact(evidence: Mapping[str, object]) -> bool:
    measurements = evidence.get("operator_measurements")
    if type(measurements) is not list or not measurements:
        return False
    for raw in measurements:
        item = _object(raw, "operator measurement")
        recomputed = _independent_operator(item.get("raw_operands"))
        if item.get("pair_support") != recomputed["pair_support"] or item.get("baseline_valid") != recomputed["baseline_valid"]:
            return False
        for key in ("raw", "normalized", "geometric_null", "residual"):
            if not _masked_close(_array(item.get(key), key), recomputed[key]):
                return False
    return True


def _expected_outcome(fixture: Mapping[str, object]) -> str:
    if str(fixture["category"]) == "positive":
        return "BIRTH_SUPPORTED"
    if str(fixture["category"]) == "ambiguous":
        return "AMBIGUOUS"
    if str(fixture["family"]) == "ACTIVE_ONLY" or str(fixture["id"]) in {"H25-F-N10", "H25-F-N11"}:
        return "ALREADY_ACTIVE_HISTORY"
    return "NO_BIRTH"


def _all_expected(plan: object, test: object, measured: Mapping[str, Mapping[str, object]]) -> bool:
    fixture_by_id = {str(item["id"]): item for item in getattr(plan, "fixtures")}
    expected_ids = tuple(getattr(test, "fixture_ids"))
    if tuple(measured) != expected_ids:
        return False
    return all(_derive_outcome(measured[fixture_id]) == _expected_outcome(fixture_by_id[fixture_id]) for fixture_id in expected_ids)


def _analytic_equivalence(plan: object, test: object, evidence: Mapping[str, object]) -> bool:
    records = evidence.get("analytic_scaling_operands")
    if type(records) is not list or not records:
        return False
    seen: set[tuple[str, int, int, int]] = set()
    for raw in records:
        item = _object(raw, "analytic scaling operand")
        fixture_id = item.get("fixture_id")
        pitch, harmonic, shift = item.get("candidate_pitch"), item.get("harmonic_rank"), item.get("shift_semitones")
        if type(fixture_id) is not str or type(pitch) is not int or type(harmonic) is not int or type(shift) is not int:
            return False
        key = (fixture_id, pitch, harmonic, shift)
        if key in seen or not 1 <= harmonic <= 20 or not 0 <= shift <= 88:
            return False
        seen.add(key)
        scaled_hz = 440.0 * math.pow(2.0, (pitch - 69.0) / 12.0) * math.pow(2.0, shift / 12.0) * harmonic
        recovered_coordinate = 69.0 + 12.0 * math.log2(scaled_hz / 440.0)
        remap_coordinate = pitch + shift + 12.0 * math.log2(float(harmonic))
        if not _close(float(item.get("whole_spectrum_scaled_hz")), scaled_hz) or not _close(float(item.get("relative_remap_coordinate")), remap_coordinate) or not _close(recovered_coordinate, remap_coordinate):
            return False
    fixtures = {str(item["id"]): item for item in getattr(plan, "fixtures")}
    expected = {
        (fixture_id, int(fixtures[fixture_id]["candidate_pitch"]), harmonic, shift)
        for fixture_id in getattr(test, "fixture_ids")
        if fixtures[fixture_id].get("candidate_pitch") is not None
        for harmonic in range(1, 21)
        for shift in range(89)
    }
    return seen == expected


def _collision_exact(evidence: Mapping[str, object], measured: Mapping[str, Mapping[str, object]]) -> bool:
    records = evidence.get("collision_explanations")
    if type(records) is not list or len(records) != 6:
        return False
    seen: set[str] = set()
    for raw in records:
        item = _object(raw, "collision explanation record")
        fixture_id = item.get("fixture_id")
        if type(fixture_id) is not str or fixture_id in seen or fixture_id not in measured:
            return False
        seen.add(fixture_id)
        explanations = item.get("latent_explanations")
        samples = item.get("waveform_samples_float64")
        if type(samples) is not list or not samples or any(type(value) not in {int, float} for value in samples):
            return False
        sample_sha256 = hashlib.sha256(b"".join(struct.pack("<d", float(value)) for value in samples)).hexdigest()
        if type(explanations) is not list or len(explanations) != 2:
            return False
        left = _object(explanations[0], "left latent explanation")
        right = _object(explanations[1], "right latent explanation")
        if {left.get("explanation_id"), right.get("explanation_id")} != {"OLD_HARMONIC_ONLY", "PUTATIVE_NEW_FUNDAMENTAL"}:
            return False
        for key in ("waveform_sha256", "features", "causal_state"):
            if left.get(key) != right.get(key):
                return False
        if left.get("waveform_sha256") != sample_sha256:
            return False
        if _derive_outcome(measured[fixture_id]) != "AMBIGUOUS":
            return False
    return seen == set(measured)


def _permutation_exact(plan: object, test: object, evidence: Mapping[str, object]) -> bool:
    bundle = _object(evidence.get("permutation_evidence"), "permutation evidence")
    rows = bundle.get("candidate_transform_rows")
    graph_orders = bundle.get("graph_orders")
    if type(rows) is not list or type(graph_orders) is not list or len(graph_orders) != 2:
        return False
    graph = _independent_graph()
    if graph_orders[0] != graph or graph_orders[1] != list(reversed(graph)):
        return False
    expected_ids = tuple(getattr(test, "fixture_ids"))
    if [row.get("fixture_id") for row in rows if type(row) is dict] != list(expected_ids):
        return False
    for raw in rows:
        row = _object(raw, "candidate transform permutation row")
        pitch = row.get("candidate_pitch")
        orders = row.get("candidate_orders")
        transforms = row.get("transform_records_reversed")
        if pitch is None:
            if orders != [] or transforms != []:
                return False
            continue
        if type(pitch) is not int or type(orders) is not list or len(orders) != 2 or type(transforms) is not list or len(transforms) != 89:
            return False
        canonical_by_order = []
        for order_raw in orders:
            order = _object(order_raw, "candidate order")
            pitches = order.get("pitches")
            support = order.get("pair_support")
            raw_values = order.get("raw")
            if type(pitches) is not list or type(support) is not list or type(raw_values) is not list or len(pitches) != 2 or len(support) != 2 or len(raw_values) != 2:
                return False
            canonical_by_order.append({candidate: (support[index], raw_values[index]) for index, candidate in enumerate(pitches)})
        if canonical_by_order[0] != canonical_by_order[1] or pitch not in canonical_by_order[0]:
            return False
        if [item.get("shift") for item in transforms if type(item) is dict] != list(reversed(range(89))):
            return False
        canonical_transforms = sorted(transforms, key=lambda item: item["shift"])
        expected_support, expected_raw = canonical_by_order[0][pitch]
        if [item.get("support") for item in canonical_transforms] != expected_support or not _masked_close([item.get("raw") for item in canonical_transforms], expected_raw):
            return False
    return True


def _cross_runtime_tree_close(left: object, right: object) -> bool:
    if type(left) in {int, float} and type(right) in {int, float} and type(left) is not bool and type(right) is not bool:
        return _close(float(left), float(right))
    if type(left) is not type(right):
        return False
    if type(left) is dict:
        return set(left) == set(right) and all(_cross_runtime_tree_close(left[key], right[key]) for key in left)
    if type(left) is list:
        return len(left) == len(right) and all(_cross_runtime_tree_close(a, b) for a, b in zip(left, right))
    return left == right


def _runtime_identity(raw: object) -> tuple[dict[str, object], dict[str, object]]:
    identity = _object(raw, "runtime identity")
    if set(identity) != {"scientific_runtime", "transport"}:
        raise ValueError("H25 runtime identity field set is invalid.")
    scientific = dict(_object(identity["scientific_runtime"], "scientific runtime identity"))
    transport = dict(_object(identity["transport"], "transport identity"))
    if set(scientific) != _SCIENTIFIC_RUNTIME_FIELDS:
        raise ValueError("H25 scientific runtime identity field set is invalid.")
    if set(transport) != _TRANSPORT_IDENTITY_FIELDS:
        raise ValueError("H25 transport identity field set is invalid.")
    scientific_strings = _SCIENTIFIC_RUNTIME_FIELDS - {
        "executable_size_bytes", "numpy_multiarray_size_bytes",
        "blas_library_size_bytes", "process_environment_exact",
    }
    if any(
        type(scientific[field]) is not str or not scientific[field]
        for field in scientific_strings
    ):
        raise ValueError("H25 scientific runtime identity string field is invalid.")
    if any(
        type(scientific[field]) is not int
        or type(scientific[field]) is bool
        or scientific[field] <= 0
        for field in (
            "executable_size_bytes", "numpy_multiarray_size_bytes",
            "blas_library_size_bytes",
        )
    ):
        raise ValueError("H25 scientific runtime identity size is invalid.")
    for field in (
        "executable_sha256", "numpy_multiarray_sha256", "blas_library_sha256"
    ):
        value = scientific[field]
        if len(value) != 64 or any(character not in "0123456789abcdef" for character in value):
            raise ValueError("H25 scientific runtime identity SHA is invalid.")
    environment = scientific["process_environment_exact"]
    if type(environment) is not dict or not environment or any(
        type(key) is not str or not key or type(value) is not str
        for key, value in environment.items()
    ):
        raise ValueError("H25 scientific runtime environment is invalid.")
    if any(
        type(transport[field]) is not str or not transport[field]
        for field in ("command_sha256", "observer_payload_path", "observer_payload_sha256")
    ):
        raise ValueError("H25 transport identity string field is invalid.")
    if (
        len(transport["command_sha256"]) != 64
        or len(transport["observer_payload_sha256"]) != 64
        or any(
            character not in "0123456789abcdef"
            for field in ("command_sha256", "observer_payload_sha256")
            for character in transport[field]
        )
        or type(transport["observer_payload_size_bytes"]) is not int
        or type(transport["observer_payload_size_bytes"]) is bool
        or transport["observer_payload_size_bytes"] <= 0
    ):
        raise ValueError("H25 transport identity hash or size is invalid.")
    return scientific, transport


def _identity_sha(value: Mapping[str, object]) -> str:
    return hashlib.sha256(
        json.dumps(
            dict(value), ensure_ascii=False, allow_nan=False, sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8") + b"\n"
    ).hexdigest()


def _runtime_observation_map(raw: object, *, fixture_ids: Sequence[str], test_ids: Sequence[str]) -> tuple[str, dict[str, object], dict[str, object], dict[str, object]]:
    observation = _object(raw, "runtime observation")
    if set(observation) != {
        "runtime_id", "transport_id", "runtime_identity",
        "fixture_measurements", "test_records",
    } or type(observation["runtime_id"]) is not str or type(observation["transport_id"]) is not str:
        raise ValueError("H25 runtime observation schema is invalid.")
    scientific, transport = _runtime_identity(observation["runtime_identity"])
    if _identity_sha(scientific) != observation["runtime_id"]:
        raise ValueError("H25 runtime ID is not derived from scientific runtime identity.")
    if _identity_sha(transport) != observation["transport_id"]:
        raise ValueError("H25 transport ID is not derived from transport identity.")
    fixture_rows = _array(observation["fixture_measurements"], "runtime fixture measurements")
    test_rows = _array(observation["test_records"], "runtime test records")
    fixture_map = {row.get("fixture_id"): row for row in fixture_rows if type(row) is dict and type(row.get("fixture_id")) is str}
    test_map = {row.get("test_id"): row for row in test_rows if type(row) is dict and type(row.get("test_id")) is str}
    if len(fixture_map) != len(fixture_rows) or tuple(fixture_map) != tuple(fixture_ids):
        raise ValueError("H25 runtime fixture observation is incomplete or reordered.")
    if len(test_map) != len(test_rows) or tuple(test_map) != tuple(test_ids):
        raise ValueError("H25 runtime test observation is incomplete or reordered.")
    return str(observation["runtime_id"]), scientific, fixture_map, test_map


def derive_h25_p2_007_self_core_outcome(
    plan: object, raw: object
) -> H25RecomputedEvidence:
    """Derive the finite P2-007 self/core outcome without trusting booleans."""

    record = _object(raw, "P2-007 nonrecursive self record")
    test = _test(plan, "H25-T-P2-007")
    if set(record) != {"test_id", "phase", "fixture_ids", "evidence", "recomputation"}:
        raise ValueError("H25 P2-007 self record schema is invalid.")
    if (
        record["test_id"] != "H25-T-P2-007"
        or record["phase"] != getattr(test, "phase")
        or record["fixture_ids"] != list(getattr(test, "fixture_ids"))
    ):
        raise ValueError("H25 P2-007 self record identity is invalid.")
    evidence = _object(record["evidence"], "P2-007 self evidence")
    fields = {
        "schema_version", "projection_kind", "fixture_measurements",
        "same_runtime_replay", "runtime_id", "transport_id",
        "runtime_identity", "inverse_measurement",
    }
    if (
        set(evidence) != fields
        or type(evidence.get("schema_version")) is not int
        or evidence.get("schema_version") != 1
    ):
        raise ValueError("H25 P2-007 self evidence schema is invalid.")
    if evidence.get("projection_kind") != _P2_007_SELF_PROJECTION:
        raise ValueError("H25 P2-007 self projection kind is invalid.")
    scientific, transport = _runtime_identity(evidence.get("runtime_identity"))
    same = _object(evidence.get("same_runtime_replay"), "P2-007 self replay")
    measurements = _array(evidence.get("fixture_measurements"), "P2-007 self measurements")
    observed_ids = tuple(
        row.get("fixture_id") for row in measurements if type(row) is dict
    )
    primary = (
        type(evidence.get("runtime_id")) is str
        and evidence["runtime_id"] == _identity_sha(scientific)
        and type(evidence.get("transport_id")) is str
        and evidence["transport_id"] == _identity_sha(transport)
        and observed_ids == tuple(getattr(test, "fixture_ids"))
        and len(measurements) == len(getattr(test, "fixture_ids"))
        and same.get("first") == measurements
        and same.get("second") == measurements
    )
    inverse = evidence.get("inverse_measurement") == {"runtime_binding_changed": True}
    outcome = H25RecomputedEvidence(
        test_id="H25-T-P2-007",
        phase="P2",
        primary_pass=primary,
        inverse_pass=inverse,
        final_pass=primary and inverse,
        diagnostics={"projection_kind": _P2_007_SELF_PROJECTION},
    )
    return outcome


def recompute_h25_p2_007_self_record(
    plan: object, raw: object
) -> H25RecomputedEvidence:
    """Recompute and validate the persisted finite P2-007 self/core record."""

    record = _object(raw, "P2-007 nonrecursive self record")
    outcome = derive_h25_p2_007_self_core_outcome(plan, record)
    expected = {
        "primary_pass": outcome.primary_pass,
        "inverse_pass": outcome.inverse_pass,
        "final_pass": outcome.final_pass,
    }
    if record.get("recomputation") != expected:
        raise ValueError("H25 P2-007 self recomputation is not reproducible.")
    return outcome


def _validated_runtime_test_record(
    plan: object, test_id: str, raw: object
) -> tuple[dict[str, object], H25RecomputedEvidence]:
    record = _object(raw, "runtime recomputed test record")
    test = _test(plan, test_id)
    if set(record) != {"test_id", "phase", "fixture_ids", "evidence", "recomputation"}:
        raise ValueError("H25 runtime recomputed test record schema is invalid.")
    if (
        record["test_id"] != test_id
        or record["phase"] != getattr(test, "phase")
        or record["fixture_ids"] != list(getattr(test, "fixture_ids"))
    ):
        raise ValueError("H25 runtime recomputed test record identity is invalid.")
    if test_id == "H25-T-P2-007":
        return record, recompute_h25_p2_007_self_record(plan, record)
    evidence = _object(record["evidence"], "runtime test evidence")
    outcome = recompute_h25_persisted_evidence(plan, test_id, evidence)
    expected = {
        "primary_pass": outcome.primary_pass,
        "inverse_pass": outcome.inverse_pass,
        "final_pass": outcome.final_pass,
    }
    if record["recomputation"] != expected:
        raise ValueError("H25 runtime test recomputation is not independently reproducible.")
    return record, outcome


def _runtime_test_records_compliant(
    plan: object,
    test_ids: Sequence[str],
    current: Mapping[str, object],
    secondary: Mapping[str, object],
) -> bool:
    for test_id in test_ids:
        left, left_outcome = _validated_runtime_test_record(plan, test_id, current[test_id])
        right, right_outcome = _validated_runtime_test_record(plan, test_id, secondary[test_id])
        if test_id == "H25-T-P2-008":
            if not left_outcome.final_pass or not right_outcome.final_pass:
                return False
            left_counters = _object(left["evidence"].get("operational_counters"), "current cost counters")
            right_counters = _object(right["evidence"].get("operational_counters"), "secondary cost counters")
            stable = {
                "GPU_device_count", "scientific_process_count",
                "model_inference_call_count",
                "hidden_repeated_pitch_shift_inference_count",
            }
            if any(left_counters.get(key) != right_counters.get(key) for key in stable):
                return False
            continue
        if test_id == "H25-T-P2-007":
            if not left_outcome.final_pass or not right_outcome.final_pass:
                return False
            left_evidence = dict(left["evidence"])
            right_evidence = dict(right["evidence"])
            for value in (left_evidence, right_evidence):
                value.pop("runtime_id", None)
                value.pop("transport_id", None)
                value.pop("runtime_identity", None)
            if not _cross_runtime_tree_close(left_evidence, right_evidence):
                return False
            continue
        if not _cross_runtime_tree_close(left, right):
            return False
    return True


def _phase_primary(plan: object, test: object, evidence: Mapping[str, object], measured: Mapping[str, Mapping[str, object]]) -> bool:
    test_id = getattr(test, "test_id")
    if test_id == "H25-T-P0-001":
        return evidence.get("typed_harmonic_graph") == _independent_graph()
    if test_id in {"H25-T-P0-002", "H25-T-P0-005", "H25-T-P0-006", "H25-T-P0-008"}:
        operator_ok = _operator_exact(evidence)
        if test_id == "H25-T-P0-002":
            return operator_ok and _analytic_equivalence(plan, test, evidence)
        if test_id == "H25-T-P0-006":
            pairs = evidence.get("gain_invariance_pairs")
            if type(pairs) is not list or not pairs:
                return False
            for raw in pairs:
                item = _object(raw, "gain invariance pair")
                base = _independent_operator(item.get("base_raw_operands"))
                scaled = _independent_operator(item.get("scaled_raw_operands"))
                if not _masked_close(base["residual"], scaled["residual"]):
                    return False
                if not _masked_close(base["residual"], _array(item.get("base_residual"), "base residual")) or not _masked_close(scaled["residual"], _array(item.get("scaled_residual"), "scaled residual")):
                    return False
            return operator_ok
        return operator_ok
    if test_id == "H25-T-P0-003":
        forbidden = {"raw_disappearance_index", "survival_index", "disappearance_transform"}
        return not forbidden.intersection(str({key: value for key, value in evidence.items() if key != "inverse_measurement"}))
    if test_id == "H25-T-P0-004":
        return _collision_exact(evidence, measured)
    if test_id == "H25-T-P0-007":
        boundaries = evidence.get("causal_boundaries")
        return type(boundaries) is list and len(boundaries) == len(getattr(test, "fixture_ids")) and all(
            item == {
                "fixture_id": item.get("fixture_id"),
                "short_current_end": 16383,
                "long_current_end": 16383,
                "short_previous_end": 16127,
                "long_previous_end": 16127,
                "maximum_sample_read": 16383,
            }
            for item in boundaries if type(item) is dict
        )
    if test_id == "H25-T-P0-009":
        return _permutation_exact(plan, test, evidence)
    if getattr(test, "phase") == "P1":
        return _all_expected(plan, test, measured)
    if test_id == "H25-T-P2-001":
        pairs = evidence.get("future_suffix_pairs")
        return type(pairs) is list and len(pairs) == len(getattr(test, "fixture_ids")) and all(
            type(item) is dict
            and item.get("causal_end") == 16383
            and item.get("changed_suffix_start") == 16384
            and item.get("original_features") == item.get("changed_future_features")
            for item in pairs
        )
    if test_id == "H25-T-P2-002":
        rows = evidence.get("hop_translation_results")
        return type(rows) is list and len(rows) == len(getattr(test, "fixture_ids")) and all(
            [item.get("hop_translation") for item in row.get("translations", [])] == [0, 1, 2, 4]
            and len({str((item.get("features"), item.get("derived_outcome"), item.get("resolution_delay_hops"))) for item in row.get("translations", [])}) == 1
            and all(item.get("resolution_delay_hops") == 1 for item in row.get("translations", []))
            for row in rows if type(row) is dict
        )
    if test_id in {"H25-T-P2-003", "H25-T-P2-004", "H25-T-P2-005"}:
        expected = _all_expected(plan, test, measured)
        if test_id == "H25-T-P2-005":
            return expected and _operator_exact({"operator_measurements": evidence.get("boundary_operator_measurements")})
        return expected
    if test_id == "H25-T-P2-006":
        permutations = _object(evidence.get("permutation_results"), "permutation results")
        manifest = tuple(getattr(test, "fixture_ids"))
        if set(permutations) != {"manifest", "reverse", "candidate_pitch_then_id"}:
            return False
        canonical = None
        for rows in permutations.values():
            if type(rows) is not list or {row.get("fixture_id") for row in rows if type(row) is dict} != set(manifest):
                return False
            current = {row["fixture_id"]: row for row in rows}
            serialized = [current[fixture_id] for fixture_id in manifest]
            canonical = serialized if canonical is None else canonical
            if serialized != canonical:
                return False
        return _permutation_exact(plan, test, evidence)
    if test_id == "H25-T-P2-007":
        same = _object(evidence.get("same_runtime_replay"), "same-runtime replay")
        if same.get("first") != same.get("second"):
            return False
        cross = evidence.get("cross_runtime_observation")
        if type(cross) is not dict:
            return False
        current_id, current_scientific, current_fixtures, current_tests = _runtime_observation_map(
            evidence.get("current_runtime_observation"),
            fixture_ids=getattr(test, "fixture_ids"),
            test_ids=getattr(plan, "test_ids"),
        )
        cross_id, cross_scientific, cross_fixtures, cross_tests = _runtime_observation_map(
            cross,
            fixture_ids=getattr(test, "fixture_ids"),
            test_ids=getattr(plan, "test_ids"),
        )
        return (
            cross_id != current_id
            and cross_scientific != current_scientific
            and all(_cross_runtime_tree_close(current_fixtures[key], cross_fixtures[key]) for key in current_fixtures)
            and _runtime_test_records_compliant(
                plan, getattr(plan, "test_ids"), current_tests, cross_tests
            )
        )
    if test_id == "H25-T-P2-008":
        counters = _object(evidence.get("operational_counters"), "operational counters")
        required = {"elapsed_ns_since_context_start", "peak_rss_bytes", "GPU_device_count", "scientific_process_count", "model_inference_call_count", "hidden_repeated_pitch_shift_inference_count"}
        return set(counters) == required and all(type(counters[key]) is int for key in required) and 0 <= counters["elapsed_ns_since_context_start"] <= 600_000_000_000 and 0 <= counters["peak_rss_bytes"] <= 4_294_967_296 and counters["GPU_device_count"] == 0 and counters["scientific_process_count"] == 1 and counters["model_inference_call_count"] == 0 and counters["hidden_repeated_pitch_shift_inference_count"] == 0
    if test_id == "H25-T-P2-009":
        observed = _object(evidence.get("observed_id_evidence"), "observed ID evidence")
        return observed.get("fixture_ids") == list(getattr(plan, "fixture_ids")) and observed.get("test_ids") == list(getattr(plan, "test_ids")) and len(set(observed["fixture_ids"])) == 36 and len(set(observed["test_ids"])) == 27
    return False


def _inverse_exact(plan: object, test: object, evidence: Mapping[str, object]) -> bool:
    inverse = _object(evidence.get("inverse_measurement"), "inverse measurement")
    test_id = getattr(test, "test_id")
    if test_id == "H25-T-P0-001":
        return inverse.get("mutated_typed_harmonic_graph") != _independent_graph()
    if test_id == "H25-T-P0-002":
        perturbed = inverse.get("misaligned_candidate_raw_operands")
        if type(perturbed) is not dict:
            return False
        recomputed = _independent_operator(perturbed)
        first = _array(evidence.get("operator_measurements"), "operator measurements")[0]
        return not _masked_close(recomputed["residual"], _array(_object(first, "operator measurement").get("residual"), "residual"))
    if test_id == "H25-T-P0-005":
        records = inverse.get("permuted_transform_records")
        if type(records) is not list or len(records) != 89 or [item.get("shift") for item in records if type(item) is dict] != list(reversed(range(89))):
            return False
        canonical = sorted(records, key=lambda item: item["shift"])
        first = _object(_array(evidence.get("operator_measurements"), "operator measurements")[0], "operator measurement")
        return all(
            [item.get(key) for item in canonical] == first.get(key)
            for key in ("pair_support", "raw", "normalized", "geometric_null", "residual")
        )
    if test_id in {"H25-T-P0-006", "H25-T-P0-008"}:
        corrupted = inverse.get("zero_filled_invalid_measurement")
        if type(corrupted) is not dict:
            return False
        recomputed = _independent_operator(corrupted.get("raw_operands"))
        return any(
            not _masked_close(_array(corrupted.get(key), key), recomputed[key])
            for key in ("raw", "normalized", "geometric_null", "residual")
        )
    if test_id == "H25-T-P0-003":
        return inverse.get("injected_feature_name") == "raw_disappearance_index"
    if test_id == "H25-T-P0-004":
        return inverse.get("forced_attribution") in {"BIRTH_SUPPORTED", "NO_BIRTH"}
    if test_id == "H25-T-P0-007":
        boundaries = inverse.get("causal_boundaries")
        return type(boundaries) is list and any(type(item) is dict and item.get("maximum_sample_read", 0) > 16383 for item in boundaries)
    if test_id == "H25-T-P0-009":
        return inverse.get("forced_order_invariance") == "DIFFERENT"
    if test_id == "H25-T-P2-001":
        return inverse.get("future_dependent") is True
    if test_id == "H25-T-P2-002":
        return inverse.get("waveform_only_shift_hops") == 1
    if test_id == "H25-T-P2-006":
        return inverse.get("filesystem_order_ids") == sorted(getattr(test, "fixture_ids"), key=str.lower)
    if test_id == "H25-T-P2-007":
        return inverse.get("runtime_binding_changed") is True
    if test_id == "H25-T-P2-008":
        counters = inverse.get("operational_counters")
        return type(counters) is dict and counters.get("model_inference_call_count", 0) > 0
    if test_id == "H25-T-P2-009":
        observed = inverse.get("observed_id_evidence")
        return type(observed) is dict and observed.get("fixture_ids") != list(getattr(plan, "fixture_ids"))
    perturbations = inverse.get("input_perturbations")
    if type(perturbations) is not list or not perturbations:
        return False
    kind = perturbations[0].get("perturbation_kind") if type(perturbations[0]) is dict else None
    if kind in {"exclusive_partial_owner_claim", "resolve_at_target_hop", "force_old_harmonic_as_new_state", "force_binary_attribution", "force_nearest_midi_source", "phase_label_only", "undeclared_100_cent_shift", "coordinate_128_emit_capable"}:
        expected_mutations = {
            "exclusive_partial_owner_claim": lambda value: set(value) == {"exclusive_partial_owner_pitch"} and type(value["exclusive_partial_owner_pitch"]) is int,
            "resolve_at_target_hop": lambda value: value == {"resolution_sample": 16383},
            "force_old_harmonic_as_new_state": lambda value: value == {"state_override": "PENDING_NEW", "state_source": "fixture_label"},
            "force_binary_attribution": lambda value: value == {"forced_outcome": "BIRTH_SUPPORTED"},
            "force_nearest_midi_source": lambda value: set(value) == {"forced_source_pitch"} and type(value["forced_source_pitch"]) is int,
            "phase_label_only": lambda value: set(value) == {"phase_label_radians"} and type(value["phase_label_radians"]) in {int, float},
            "undeclared_100_cent_shift": lambda value: value == {"pitch_shift_cents": 100.0},
            "coordinate_128_emit_capable": lambda value: value == {"emit_coordinate": 128.0},
        }
        for item in perturbations:
            if type(item) is not dict or item.get("perturbation_kind") != kind:
                return False
            mutation = item.get("raw_mutation")
            if type(mutation) is not dict or not expected_mutations[kind](mutation):
                return False
            if set(mutation).intersection({"features", "outcome", "target", "family", "accepted_by_input_schema"}):
                return False
        return True
    outcomes = [_derive_outcome(item) for item in perturbations]
    if kind in {"remove_new_source_waveform", "remove_newest_hop_attack"}:
        return all(value != "BIRTH_SUPPORTED" for value in outcomes)
    if kind == "erase_old_source_state":
        return all(value != "ALREADY_ACTIVE_HISTORY" for value in outcomes)
    if kind == "inject_independent_attack":
        return all(value == "BIRTH_SUPPORTED" for value in outcomes)
    return False


def recompute_h25_persisted_evidence(plan: object, test_id: str, evidence: Mapping[str, object]) -> H25RecomputedEvidence:
    if type(evidence) is not dict:
        raise ValueError("H25 persisted evidence must be a JSON object.")
    forbidden = {"pass", "passed", "verdict", "final_pass", "primary_pass", "inverse_pass"}
    if forbidden.intersection(evidence):
        raise ValueError("H25 producer evidence contains a forbidden self-declared verdict.")
    if not _finite(evidence):
        raise ValueError("H25 persisted evidence contains a nonfinite value.")
    test = _test(plan, test_id)
    if evidence.get("schema_version") != 1 or evidence.get("test_id") != getattr(test, "test_id") or evidence.get("phase") != getattr(test, "phase") or evidence.get("objective") != getattr(test, "objective"):
        raise ValueError("H25 persisted evidence identity mismatch.")
    measured = _measurement_map(evidence)
    primary = _phase_primary(plan, test, evidence, measured)
    inverse = _inverse_exact(plan, test, evidence)
    return H25RecomputedEvidence(
        test_id=getattr(test, "test_id"),
        phase=getattr(test, "phase"),
        primary_pass=primary,
        inverse_pass=inverse,
        final_pass=primary and inverse,
        diagnostics={"fixture_measurement_count": len(measured), "expected_fixture_count": len(getattr(test, "fixture_ids")), "primary_pass": primary, "inverse_pass": inverse},
    )


__all__ = [
    "H25RecomputedEvidence",
    "derive_h25_p2_007_self_core_outcome",
    "recompute_h25_p2_007_self_record",
    "recompute_h25_persisted_evidence",
]
