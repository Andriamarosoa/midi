"""Deterministic, zero-science harness resolver for the H23 contract.

This module deliberately contains no DSP, waveform synthesis, project-data
loader, model import, or executable P0 path.  It closes the administrative
boundary between the reviewed JSON contract and a future synthetic executor:
the exact 72 test records and 175 fixture specifications can be resolved and
hashed now, while execution remains fail-closed until a separate contract
changes both reviewed authorization flags.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence


H23_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_pretrain_h23_contract.json"
)
H23_CONTRACT_SHA256 = (
    "719eba0aa440fc1e77ae7d204adee9e5b51517f455fad3bfed7e761d3c00a74a"
)
H23_PURPOSE = "harmonic_censoring_multiscale_pretrain_h23_contract"
H23_STATUS = "externally_approved_for_implementation_only"
H23_REVIEWED_COMMIT = "1e5075f5d9eb23bdab077bed3faeb6c58c61942e"
H23_FIXTURE_MANIFEST_PURPOSE = "harmonic_censoring_h23_fixture_manifest"
H23_RESOLVED_TEST_MANIFEST_PURPOSE = "harmonic_censoring_h23_resolved_tests"


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
    """Return the single canonical JSON representation used by the harness."""
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _reject_duplicate_object_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H23 JSON contains duplicate key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite_json(token: str) -> None:
    raise ValueError(f"H23 JSON contains forbidden numeric token {token!r}.")


def _load_json_object(raw: bytes) -> dict[str, object]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("H23 contract must be UTF-8.") from exc
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_object_pairs,
        parse_constant=_reject_nonfinite_json,
    )
    if not isinstance(value, dict):
        raise ValueError("H23 contract root must be an object.")
    return value


def _require_object(value: object, label: str) -> dict[str, object]:
    if not isinstance(value, dict):
        raise ValueError(f"H23 {label} must be an object.")
    return value


def _require_list(value: object, label: str) -> list[object]:
    if not isinstance(value, list):
        raise ValueError(f"H23 {label} must be an array.")
    return value


def _require_exact_keys(
    value: Mapping[str, object], expected: Iterable[str], label: str
) -> None:
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise ValueError(
            f"H23 {label} keys mismatch: missing={sorted(wanted - actual)}, "
            f"extra={sorted(actual - wanted)}."
        )


def _json_scalar_token(value: object) -> str:
    if isinstance(value, (dict, list)) or value is None or isinstance(value, bool):
        raise ValueError("H23 fixture ID tokens must be string or numeric scalars.")
    if isinstance(value, str):
        token = value
    elif type(value) in (int, float):
        token = json.dumps(value, allow_nan=False, separators=(",", ":"))
    else:
        raise ValueError("H23 fixture ID token has unsupported JSON type.")
    return token.replace("-", "m").replace(".", "p")


def fixture_seed(fixture_id: str) -> int:
    digest = hashlib.sha256(f"H23|{fixture_id}".encode("utf-8")).digest()
    return int.from_bytes(digest[:8], byteorder="little", signed=False)


@dataclass(frozen=True)
class H23FixtureSpec:
    fixture_id: str
    base_id: str
    variant_axis: str | None
    synthesis_seed: int
    spec_sha256: str
    canonical_spec: bytes

    def as_dict(self) -> dict[str, object]:
        return _load_json_object(self.canonical_spec)


@dataclass(frozen=True)
class H23ResolvedTest:
    test_id: str
    phase: str
    resolved_sha256: str
    canonical_record: bytes

    def as_dict(self) -> dict[str, object]:
        return _load_json_object(self.canonical_record)


@dataclass(frozen=True)
class H23ExecutionFlags:
    implementation_authorized: bool
    synthetic_execution_authorized: bool
    scientific_execution_authorized: bool
    real_data_access_authorized: bool
    training_authorized: bool
    locked_test_used: bool
    reviewed_synthetic_execution_authorized: bool


@dataclass(frozen=True)
class H23HarnessPlan:
    contract_path: Path
    contract_sha256: str
    fixtures: tuple[H23FixtureSpec, ...]
    tests: tuple[H23ResolvedTest, ...]
    fixture_manifest: bytes
    fixture_manifest_sha256: str
    resolved_test_manifest: bytes
    resolved_test_manifest_sha256: str
    flags: H23ExecutionFlags

    @property
    def fixture_ids(self) -> tuple[str, ...]:
        return tuple(item.fixture_id for item in self.fixtures)

    @property
    def test_ids(self) -> tuple[str, ...]:
        return tuple(item.test_id for item in self.tests)


def _variant_combinations(family: Mapping[str, object]) -> list[dict[str, object]]:
    values = family.get("values")
    if isinstance(values, list):
        combinations = [{"value": value} for value in values]
    elif isinstance(values, dict):
        names = list(values)
        axes: list[list[object]] = []
        for name in names:
            axes.append(_require_list(values[name], f"variant values {name}"))
        combinations = [
            dict(zip(names, combination))
            for combination in itertools.product(*axes)
        ]
    else:
        raise ValueError("H23 variant family values must be an array or object.")

    excluded = family.get("exclude_exact_pairs", [])
    if not isinstance(excluded, list):
        raise ValueError("H23 exclude_exact_pairs must be an array.")
    if excluded:
        if not isinstance(values, dict):
            raise ValueError("H23 exclusions require Cartesian object values.")
        names = list(values)
        excluded_bytes = {
            canonical_json_bytes(item)
            for item in excluded
            if isinstance(item, list)
        }
        combinations = [
            item
            for item in combinations
            if canonical_json_bytes([item[name] for name in names])
            not in excluded_bytes
        ]
    return combinations


def _fixture_id(base_id: str, axis: str, parameters: Mapping[str, object]) -> str:
    tokens = [_json_scalar_token(value) for value in parameters.values()]
    return "__".join((base_id, axis, *tokens))


def _variant_target(
    *,
    base_oracle: Mapping[str, object],
    axis: str,
    parameters: Mapping[str, object],
    named_values: Mapping[str, object],
) -> dict[str, object]:
    """Resolve the target instructions without evaluating any waveform."""
    target: dict[str, object] = {
        "base_oracle": dict(base_oracle),
        "target_transform": axis,
        "parameters": dict(parameters),
    }
    scalar = parameters.get("value")
    if axis == "noise" and parameters.get("snr_db") == 0:
        target["categorical_oracle_override"] = "AMBIGUOUS_OR_OOD"
    elif axis == "neighbour_semitones":
        target["required_target_operation"] = "add_birth_pitch_and_increment_all_identifiable_cardinalities"
    elif axis == "interval_semitones":
        target["required_target_operation"] = "add_old_pitch_and_increment_all_identifiable_cardinalities"
    elif axis == "chord_spec":
        target["named_target"] = named_values[axis][str(scalar)]
        target["required_target_operation"] = "replace_with_exact_sorted_chord_pitch_set"
    elif axis == "physical_unison":
        target["K_latent_pitch"] = 1
        target["K_emit_pitch"] = 1
        target["K_source"] = "AMBIGUOUS"
    elif axis == "technique":
        target["named_target"] = named_values[axis][str(scalar)]
        target["K_source"] = 1
        target["intermediate_semitone_birth_allowed"] = False
    elif axis == "natural_harmonic":
        target["named_target"] = named_values[axis][str(scalar)]
        target["K_latent_pitch"] = 1
        target["K_emit_pitch"] = 1
        target["source_identity"] = "NATURAL_HARMONIC_OR_UNKNOWN"
        target["added_midi_birth"] = False
    elif axis == "sympathetic_resonance":
        target["named_target"] = named_values[axis][str(scalar)]
        target["K_source_and_birth"] = "AMBIGUOUS_OR_RESONANCE"
    elif axis == "event_sample_offset":
        if scalar in (0, 1, 255, 256):
            target["target_hop_category"] = "ALREADY_ACTIVE_HISTORY"
        elif scalar in (3840, 4095):
            target["target_hop_category"] = "PENDING_NEW_AWAITING_ONE_HOP"
            target["resolution_hop_category"] = "BIRTH_SUPPORTED_DELAYED_ONE_HOP"
        else:
            raise ValueError("H23 event_sample_offset is outside the sealed grid.")
    elif axis == "pitch_boundary":
        if scalar == "analytical_128":
            target["observation_coordinate"] = 128
            target["emission_pitch_valid"] = False
            target["source_or_candidate_at_128"] = False
        else:
            target["replacement_birth_pitch"] = scalar
    elif axis == "silence":
        target["categorical_oracle_override"] = "SILENCE_UNEXPLAINED"
        target["all_normalization_valid"] = False
    elif axis == "synthetic_OOD":
        target["categorical_oracle_override"] = "OOD_OR_UNEXPLAINED"
        target["required_pitches"] = []
    return target


def _resolve_fixtures(
    payload: Mapping[str, object], contract_sha256: str
) -> tuple[H23FixtureSpec, ...]:
    fixture_contract = _require_object(
        payload.get("synthetic_fixture_contract"), "synthetic_fixture_contract"
    )
    base_parameters = _require_object(
        fixture_contract.get("base_fixture_exact_parameters"),
        "base_fixture_exact_parameters",
    )
    transforms = _require_object(
        fixture_contract.get("variant_transform_rules"), "variant_transform_rules"
    )
    named_values = _require_object(
        fixture_contract.get("named_variant_value_contract"),
        "named_variant_value_contract",
    )
    closed = _require_object(
        fixture_contract.get("closed_variant_manifest"), "closed_variant_manifest"
    )
    if closed.get("combination_policy") != "one_factor_at_a_time_only; no undeclared Cartesian cross-axis combinations":
        raise ValueError("H23 fixture combination policy mismatch.")
    base_ids = _require_list(closed.get("base_fixture_ids"), "base_fixture_ids")
    if base_ids != ["S1C", "S1P", "S2", "S3", "S4", "S5"]:
        raise ValueError("H23 base fixture IDs mismatch.")

    specs: list[H23FixtureSpec] = []

    def append_spec(
        base_id: str,
        axis: str | None,
        parameters: Mapping[str, object],
        transform_rule: object,
        expected_target: Mapping[str, object],
    ) -> None:
        fixture_id = base_id if axis is None else _fixture_id(base_id, axis, parameters)
        base = _require_object(base_parameters.get(base_id), f"base fixture {base_id}")
        spec = {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h23_fixture_spec",
            "contract_sha256": contract_sha256,
            "fixture_id": fixture_id,
            "fixture_kind": "base" if axis is None else "one_factor_variant",
            "base_id": base_id,
            "variant_axis": axis,
            "variant_parameters": dict(parameters),
            "transform_rule": transform_rule,
            "base_fixture_parameters": base,
            "expected_target": dict(expected_target),
            "synthesis_seed": fixture_seed(fixture_id),
            "RNG_algorithm": payload["reproducibility_seal"]["RNG_algorithm"],  # type: ignore[index]
        }
        raw = canonical_json_bytes(spec)
        specs.append(
            H23FixtureSpec(
                fixture_id=fixture_id,
                base_id=base_id,
                variant_axis=axis,
                synthesis_seed=int(spec["synthesis_seed"]),
                spec_sha256=_sha256(raw),
                canonical_spec=raw,
            )
        )

    for raw_base_id in base_ids:
        if not isinstance(raw_base_id, str):
            raise ValueError("H23 base fixture ID must be a string.")
        base = _require_object(base_parameters.get(raw_base_id), f"base fixture {raw_base_id}")
        oracle = _require_object(base.get("oracle"), f"base fixture oracle {raw_base_id}")
        append_spec(raw_base_id, None, {}, None, oracle)

    families = _require_list(closed.get("variant_families"), "variant_families")
    axes: list[str] = []
    for raw_family in families:
        family = _require_object(raw_family, "variant family")
        axis = family.get("axis")
        if not isinstance(axis, str) or axis in axes:
            raise ValueError("H23 variant axis must be a unique string.")
        axes.append(axis)
        if axis not in transforms:
            raise ValueError(f"H23 variant axis {axis!r} has no transform rule.")
        combinations = _variant_combinations(family)
        if type(family.get("count")) is not int or len(combinations) * len(
            _require_list(family.get("base_ids"), f"{axis} base_ids")
        ) != family["count"]:
            raise ValueError(f"H23 variant family count mismatch for {axis}.")
        for raw_base_id in family["base_ids"]:  # type: ignore[index]
            if not isinstance(raw_base_id, str) or raw_base_id not in base_ids:
                raise ValueError(f"H23 variant {axis} has invalid base fixture.")
            base = _require_object(base_parameters[raw_base_id], f"base fixture {raw_base_id}")
            oracle = _require_object(base.get("oracle"), f"base oracle {raw_base_id}")
            for parameters in combinations:
                append_spec(
                    raw_base_id,
                    axis,
                    parameters,
                    transforms[axis],
                    _variant_target(
                        base_oracle=oracle,
                        axis=axis,
                        parameters=parameters,
                        named_values=named_values,
                    ),
                )

    if sorted(axes) != sorted(transforms) or len(axes) != 17:
        raise ValueError("H23 transform rules and variant axes do not match exactly.")
    if len(specs) != 175 or closed.get("expected_total_fixture_count") != 175:
        raise ValueError("H23 fixture universe must contain exactly 175 specs.")
    ids = [item.fixture_id for item in specs]
    if len(set(ids)) != len(ids):
        raise ValueError("H23 fixture IDs must be unique.")
    return tuple(specs)


def _resolve_tests(payload: Mapping[str, object]) -> tuple[H23ResolvedTest, ...]:
    schema = _require_list(payload.get("test_record_schema"), "test_record_schema")
    expected_schema = [
        "id", "phase", "objective", "exact_input", "procedure", "oracle",
        "metrics", "pass_rule", "fail_rule", "artifacts", "drawback",
        "inverse_check",
    ]
    if schema != expected_schema:
        raise ValueError("H23 resolved test schema mismatch.")
    resolution = _require_object(
        payload.get("test_record_resolution"), "test_record_resolution"
    )
    defaults = _require_object(resolution.get("inherited_defaults"), "test defaults")
    catalogue = _require_object(payload.get("test_catalogue"), "test_catalogue")
    phase_order = _require_object(payload.get("phase_order"), "phase_order")
    prefix_to_phase = _require_object(
        phase_order.get("catalogue_prefix_to_phase"), "catalogue phase map"
    )
    resolved: list[H23ResolvedTest] = []
    phase_ids: dict[str, list[str]] = {"P0": [], "P1": [], "P2": []}
    for prefix, raw_entries in catalogue.items():
        phase = prefix_to_phase.get(prefix)
        if phase not in phase_ids:
            raise ValueError(f"H23 catalogue prefix {prefix!r} has no valid phase.")
        entries = _require_list(raw_entries, f"catalogue {prefix}")
        for raw_entry in entries:
            entry = _require_object(raw_entry, f"catalogue entry {prefix}")
            record = dict(defaults)
            record.update(entry)
            record["phase"] = phase
            _require_exact_keys(record, expected_schema, f"resolved test {entry.get('id')}")
            test_id = record.get("id")
            if not isinstance(test_id, str):
                raise ValueError("H23 test ID must be a string.")
            raw = canonical_json_bytes(record)
            resolved.append(H23ResolvedTest(test_id, phase, _sha256(raw), raw))
            phase_ids[phase].append(test_id)

    for phase in ("P0", "P1", "P2"):
        expected = _require_list(phase_order.get(f"{phase}_test_ids"), f"{phase} IDs")
        if phase_ids[phase] != expected:
            raise ValueError(f"H23 {phase} catalogue order mismatch.")
    if len(resolved) != 72 or len({item.test_id for item in resolved}) != 72:
        raise ValueError("H23 test universe must contain 72 unique records.")
    return tuple(resolved)


def _validate_contract_identity(payload: Mapping[str, object]) -> H23ExecutionFlags:
    if type(payload.get("schema_version")) is not int or payload.get("schema_version") != 1:
        raise ValueError("H23 contract schema version mismatch.")
    if payload.get("purpose") != H23_PURPOSE or payload.get("status") != H23_STATUS:
        raise ValueError("H23 contract identity/status mismatch.")
    scope = _require_object(payload.get("scope"), "scope")
    expected_scope = {
        "contract_only": True,
        "implementation_authorized": True,
        "synthetic_execution_authorized": False,
        "scientific_execution_authorized": False,
        "real_data_access_authorized": False,
        "training_authorized": False,
        "fit_performed": False,
        "calibration_performed": False,
        "h17_population_used": False,
        "locked_test_used": False,
    }
    if scope != expected_scope:
        raise ValueError("H23 implementation-only scope mismatch.")
    review = _require_object(payload.get("external_review_gate"), "review gate")
    if (
        review.get("reviewed_commit") != H23_REVIEWED_COMMIT
        or review.get("verdict") != "APPROVED"
        or review.get("authorized_scope")
        != "implementation_of_the_synthetic_harness_only"
        or review.get("synthetic_P0_execution_authorized") is not False
        or review.get("scientific_execution_authorized") is not False
        or review.get("training_authorized") is not False
    ):
        raise ValueError("H23 external review gate mismatch.")
    return H23ExecutionFlags(
        implementation_authorized=True,
        synthetic_execution_authorized=False,
        scientific_execution_authorized=False,
        real_data_access_authorized=False,
        training_authorized=False,
        locked_test_used=False,
        reviewed_synthetic_execution_authorized=False,
    )


def _validate_closed_dimensions(payload: Mapping[str, object]) -> None:
    product = _require_object(payload.get("product_contract"), "product_contract")
    expected = {
        "sample_rate_hz": 44100,
        "hop_samples": 256,
        "causal_window_samples": 4096,
        "future_lookahead_samples": 0,
        "physical_midi_output_min": 40,
        "physical_midi_output_max": 76,
        "emission_candidate_pitch_count": 37,
        "latent_source_hypothesis_min": 24,
        "latent_source_hypothesis_max": 76,
        "latent_source_hypothesis_count": 53,
        "virtual_observation_coordinate_min": 40,
        "virtual_observation_coordinate_max_inclusive": 128,
        "virtual_observation_coordinate_count": 89,
        "live_cutoff_count": 6,
        "live_relative_harmonic_cutoffs": [1, 2, 3, 4, 8, 20],
    }
    for key, value in expected.items():
        if product.get(key) != value:
            raise ValueError(f"H23 closed product dimension mismatch: {key}.")
    replay = _require_object(payload.get("replay_stream_contract"), "replay stream")
    replay_expected = {
        "first_valid_hop_end_sample": 4095,
        "target_hop_index_from_first_valid": 32,
        "target_hop_end_sample": 12287,
        "target_window_global_samples": [8192, 12287],
        "previous_hop_end_sample": 12031,
        "previous_window_global_samples": [7936, 12031],
        "resolution_hop_end_sample": 12543,
        "old_source_global_onset_sample": 4096,
        "base_new_source_global_onset_sample": 12032,
    }
    for key, value in replay_expected.items():
        if replay.get(key) != value:
            raise ValueError(f"H23 replay timeline mismatch: {key}.")
    machine = _require_object(
        payload.get("causal_temporal_state_machine"), "temporal state machine"
    )
    if machine.get("states") != ["INACTIVE", "PENDING_NEW", "ACTIVE"]:
        raise ValueError("H23 temporal states mismatch.")
    if machine.get("runtime_state_fields") != ["pitch", "state", "first_seen_hop"]:
        raise ValueError("H23 runtime-state schema mismatch.")
    if machine.get("forbidden_runtime_state_fields") != [
        "onset_coordinate", "ground_truth_onset", "samples_seen", "fixture_id", "target"
    ]:
        raise ValueError("H23 forbidden runtime-state schema mismatch.")


def _fixture_manifest_bytes(
    contract_sha256: str, fixtures: Sequence[H23FixtureSpec]
) -> bytes:
    return canonical_json_bytes(
        {
            "schema_version": 1,
            "purpose": H23_FIXTURE_MANIFEST_PURPOSE,
            "contract_sha256": contract_sha256,
            "fixture_count": len(fixtures),
            "fixture_ids": [item.fixture_id for item in fixtures],
            "fixtures": [
                {
                    "fixture_id": item.fixture_id,
                    "base_id": item.base_id,
                    "variant_axis": item.variant_axis,
                    "synthesis_seed": item.synthesis_seed,
                    "fixture_spec_sha256": item.spec_sha256,
                }
                for item in fixtures
            ],
            "real_data_used": False,
            "h17_population_used": False,
            "locked_test_used": False,
            "fit_performed": False,
            "waveforms_synthesized": False,
            "tests_executed": False,
        }
    )


def _test_manifest_bytes(
    contract_sha256: str, tests: Sequence[H23ResolvedTest]
) -> bytes:
    return canonical_json_bytes(
        {
            "schema_version": 1,
            "purpose": H23_RESOLVED_TEST_MANIFEST_PURPOSE,
            "contract_sha256": contract_sha256,
            "test_count": len(tests),
            "test_ids": [item.test_id for item in tests],
            "tests": [
                {
                    "test_id": item.test_id,
                    "phase": item.phase,
                    "resolved_test_contract_sha256": item.resolved_sha256,
                }
                for item in tests
            ],
            "tests_executed": False,
        }
    )


def load_h23_harness_plan(repository_root: Path) -> H23HarnessPlan:
    """Load the one canonical reviewed contract and resolve its dormant plan."""
    repository = Path(repository_root).resolve(strict=True)
    contract_path = (repository / H23_CONTRACT_RELATIVE_PATH).resolve(strict=True)
    expected_path = (repository / H23_CONTRACT_RELATIVE_PATH).resolve(strict=True)
    if contract_path != expected_path:
        raise ValueError("H23 contract path mismatch.")
    raw = contract_path.read_bytes()
    if b"\r\n" in raw:
        raise ValueError("H23 contract checkout must use LF bytes.")
    contract_sha256 = _sha256(raw)
    if contract_sha256 != H23_CONTRACT_SHA256:
        raise ValueError("H23 contract SHA-256 mismatch.")
    payload = _load_json_object(raw)
    flags = _validate_contract_identity(payload)
    _validate_closed_dimensions(payload)
    fixtures = _resolve_fixtures(payload, contract_sha256)
    tests = _resolve_tests(payload)
    fixture_manifest = _fixture_manifest_bytes(contract_sha256, fixtures)
    test_manifest = _test_manifest_bytes(contract_sha256, tests)
    return H23HarnessPlan(
        contract_path=contract_path,
        contract_sha256=contract_sha256,
        fixtures=fixtures,
        tests=tests,
        fixture_manifest=fixture_manifest,
        fixture_manifest_sha256=_sha256(fixture_manifest),
        resolved_test_manifest=test_manifest,
        resolved_test_manifest_sha256=_sha256(test_manifest),
        flags=flags,
    )


def require_h23_synthetic_execution_authorized(plan: H23HarnessPlan) -> None:
    """Fail closed until a later reviewed contract authorizes actual P0 work."""
    if not isinstance(plan, H23HarnessPlan):
        raise TypeError("H23 execution requires an exact resolved harness plan.")
    # This implementation commit is intentionally incapable of authorizing
    # execution.  Public/frozen dataclasses are value containers, not
    # capabilities: changing their booleans (including with dataclasses.replace)
    # must never turn a dormant plan into an execution authority.  A later
    # reviewed execution commit must introduce a separately attested capability
    # and replace this unconditional denial in code as well as in the contract.
    raise PermissionError(
        "H23 synthetic execution is not authorized by this implementation; "
        "fixture synthesis and P0 execution require a separate reviewed "
        "contract-and-code execution capability."
    )


__all__ = [
    "H23_CONTRACT_RELATIVE_PATH",
    "H23_CONTRACT_SHA256",
    "H23ExecutionFlags",
    "H23FixtureSpec",
    "H23HarnessPlan",
    "H23ResolvedTest",
    "canonical_json_bytes",
    "fixture_seed",
    "load_h23_harness_plan",
    "require_h23_synthetic_execution_authorized",
]
