"""Strict, zero-science loader for the dormant H24 harness.

This module resolves only reviewed JSON specifications.  It deliberately has
no DSP, NumPy, TensorFlow, project-data loader, command-line entry point, or
production capability.  A fixture can be translated into an immutable recipe,
but waveform materialization and evidence production remain impossible until a
separate reviewed authorization adds a different capability.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Iterable, Mapping, Sequence


H24_HARNESS_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_dormant_harness_contract.json"
)
H24_SUCCESSOR_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_successor_contract.json"
)
H24_POPULATION_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_population_manifest.json"
)
H24_TEST_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_test_manifest.json"
)
H24_BINDING_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_manifest_binding_contract.json"
)

H24_SUCCESSOR_SHA256 = (
    "184d3847a594ffaca263b45befe70d1f5aa63ade0a0ef599d969ba044f4e680a"
)
H24_POPULATION_SHA256 = (
    "52c88c74c837ad3c6109be466df38bac862e10d93c187fe60e8c5da30bd4b02b"
)
H24_TEST_SHA256 = (
    "7f87e486ffc6fdc2bfa60a5c617eca9b1ce78c570c1d72910173193ad1f7b416"
)
H24_BINDING_SHA256 = (
    "242c00d4d5fd3b9e777676b563f28b94b724159bde81307aebbba9e46608a1b5"
)
H24_HARNESS_CONTRACT_SHA256 = (
    "72675c6dda2128aa0036b7f0f2379de535fd74445a029f020f24f3f6f15fff39"
)

_ATTESTED_H24_PLANS: dict[int, "H24DormantHarnessPlan"] = {}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(value: object) -> bytes:
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


def _reject_duplicate_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H24 JSON contains duplicate key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H24 JSON contains forbidden numeric token {token!r}.")


def _parse_json_object(raw: bytes, label: str) -> dict[str, object]:
    if b"\r" in raw:
        raise ValueError(f"H24 {label} must use LF bytes only.")
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"H24 {label} must be UTF-8.") from exc
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise ValueError(f"H24 {label} root must be an object.")
    return value


def _load_sealed(
    repository: Path, relative_path: Path, expected_sha256: str, label: str
) -> tuple[bytes, dict[str, object]]:
    path = (repository / relative_path).resolve(strict=True)
    try:
        path.relative_to(repository.resolve(strict=True))
    except ValueError as exc:
        raise ValueError(f"H24 {label} path escapes repository root.") from exc
    raw = path.read_bytes()
    if _sha256(raw) != expected_sha256:
        raise ValueError(f"H24 {label} SHA-256 mismatch.")
    return raw, _parse_json_object(raw, label)


def _require_object(value: object, label: str) -> dict[str, object]:
    if type(value) is not dict:
        raise ValueError(f"H24 {label} must be an object.")
    return value


def _require_array(value: object, label: str) -> list[object]:
    if type(value) is not list:
        raise ValueError(f"H24 {label} must be an array.")
    return value


def _require_string(value: object, label: str) -> str:
    if type(value) is not str or not value:
        raise ValueError(f"H24 {label} must be a non-empty string.")
    return value


def _require_exact_keys(
    value: Mapping[str, object], expected: Iterable[str], label: str
) -> None:
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise ValueError(
            f"H24 {label} keys mismatch: missing={sorted(wanted - actual)}, "
            f"extra={sorted(actual - wanted)}."
        )


def _freeze_json(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType({key: _freeze_json(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(_freeze_json(item) for item in value)
    return value


@dataclass(frozen=True)
class H24FixtureSpecification:
    fixture_id: str
    canonical_specification: bytes
    specification_sha256: str

    def as_dict(self) -> dict[str, object]:
        return _parse_json_object(self.canonical_specification, self.fixture_id)


@dataclass(frozen=True)
class H24TestSpecification:
    test_id: str
    phase: str
    resolved_fixture_ids: tuple[str, ...]
    canonical_specification: bytes
    specification_sha256: str

    def as_dict(self) -> dict[str, object]:
        return _parse_json_object(self.canonical_specification, self.test_id)


@dataclass(frozen=True)
class H24DormantFixtureRecipe:
    fixture_id: str
    fixture_kind: str
    base_id: str
    variant_axis: str | None
    synthesis_seed: int
    base_fixture_parameters: Mapping[str, object]
    variant_parameters: Mapping[str, object]
    transform_rule: object
    expected_target: Mapping[str, object]
    source_specification_sha256: str


@dataclass(frozen=True)
class H24EvaluatorRegistration:
    test_id: str
    phase: str
    resolved_fixture_ids: tuple[str, ...]
    producer_id: str
    recomputer_id: str
    producer_callable: bool = False
    scientific_evaluator_callable: bool = False


@dataclass(frozen=True)
class H24DormancyFlags:
    fixture_translation_authorized: bool
    recomputation_from_persisted_operands_authorized: bool
    population_materialization_authorized: bool
    waveform_synthesis_authorized: bool
    scientific_test_execution_authorized: bool
    real_data_access_authorized: bool
    model_or_checkpoint_access_authorized: bool
    training_or_calibration_authorized: bool
    locked_test_used: bool


@dataclass(frozen=True)
class H24DormantHarnessPlan:
    repository_root: Path
    fixtures: tuple[H24FixtureSpecification, ...]
    tests: tuple[H24TestSpecification, ...]
    evaluator_registry: Mapping[str, H24EvaluatorRegistration]
    operator_registry: Mapping[str, Mapping[str, object]]
    sentinel_registry: Mapping[str, Mapping[str, object]]
    evidence_nonvacuity_contract_bytes: bytes
    raw_sha256: Mapping[str, str]
    flags: H24DormancyFlags

    @property
    def fixture_ids(self) -> tuple[str, ...]:
        return tuple(item.fixture_id for item in self.fixtures)

    @property
    def test_ids(self) -> tuple[str, ...]:
        return tuple(item.test_id for item in self.tests)

    @property
    def evidence_nonvacuity_contract(self) -> Mapping[str, object]:
        return _parse_json_object(
            self.evidence_nonvacuity_contract_bytes, "evidence nonvacuity contract"
        )


def _attest_h24_plan(plan: H24DormantHarnessPlan) -> H24DormantHarnessPlan:
    _ATTESTED_H24_PLANS[id(plan)] = plan
    return plan


def _require_h24_attested_plan(plan: object) -> H24DormantHarnessPlan:
    if type(plan) is not H24DormantHarnessPlan:
        raise TypeError("H24 operation requires the exact dormant plan type.")
    if _ATTESTED_H24_PLANS.get(id(plan)) is not plan:
        raise PermissionError("H24 dormant plan is not factory-attested.")
    return plan


def _validate_harness_contract(value: Mapping[str, object]) -> None:
    _require_exact_keys(
        value,
        {
            "schema_version",
            "purpose",
            "status",
            "authorization_source",
            "sealed_inputs",
            "implementation_surface",
            "state_transition",
            "dormancy",
            "review_boundary",
        },
        "dormant harness contract",
    )
    if value.get("schema_version") != 1 or type(value.get("schema_version")) is not int:
        raise ValueError("H24 dormant harness schema version mismatch.")
    if value.get("purpose") != "harmonic_censoring_h24_dormant_harness_contract":
        raise ValueError("H24 dormant harness purpose mismatch.")
    if value.get("status") != "implementation_authorized_dormant_only_pending_external_review":
        raise ValueError("H24 dormant harness status mismatch.")
    authorization = _require_object(
        value.get("authorization_source"), "authorization source"
    )
    if authorization != {
        "reviewed_commit": "16e612bad8e61ea554d194a5fc88f74b07f4f7d9",
        "authorization": "AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_HARNESS_ONLY",
    }:
        raise ValueError("H24 dormant harness authorization source mismatch.")
    sealed = _require_object(value.get("sealed_inputs"), "sealed inputs")
    expected = {
        "successor_contract": (H24_SUCCESSOR_RELATIVE_PATH, H24_SUCCESSOR_SHA256),
        "population_manifest": (H24_POPULATION_RELATIVE_PATH, H24_POPULATION_SHA256),
        "test_manifest": (H24_TEST_RELATIVE_PATH, H24_TEST_SHA256),
        "manifest_binding": (H24_BINDING_RELATIVE_PATH, H24_BINDING_SHA256),
    }
    if set(sealed) != set(expected):
        raise ValueError("H24 dormant harness sealed input names mismatch.")
    for name, (path, digest) in expected.items():
        entry = _require_object(sealed[name], f"sealed input {name}")
        if entry != {"path": path.as_posix(), "sha256": digest}:
            raise ValueError(f"H24 dormant harness sealed input {name} mismatch.")
    surface = _require_object(
        value.get("implementation_surface"), "implementation surface"
    )
    if surface != {
        "loader": "src/polyphonic/harmonic_censoring_h24.py",
        "operator_recomputer": "src/polyphonic/harmonic_censoring_h24_operators.py",
        "fixture_translation_count": 175,
        "evaluator_registration_count": 72,
        "operator_count": 27,
        "sentinel_count": 1,
        "producer_callable": False,
        "waveform_materializer_callable": False,
        "scientific_evaluator_callable": False,
        "recomputer_accepts_persisted_operands_only": True,
        "producer_verdict_is_authoritative": False,
    }:
        raise ValueError("H24 dormant harness implementation surface mismatch.")
    transition = _require_object(value.get("state_transition"), "state transition")
    if transition != {
        "bound_test_manifest_snapshot": {
            "status": "test_specifications_only_not_implemented",
            "evaluators_implemented": False,
            "oracles_implemented": False,
            "tests_executed": False,
        },
        "state_after_this_contract": {
            "strict_loader_implemented": True,
            "fixture_recipe_translator_implemented": True,
            "closed_operator_recomputer_implemented": True,
            "dormant_evaluator_registry_implemented": True,
            "evidence_producers_callable": False,
            "population_materialized": False,
            "waveforms_synthesized": False,
            "scientific_tests_executed": False,
        },
        "historical_manifest_is_not_rewritten": True,
    }:
        raise ValueError("H24 dormant harness state transition mismatch.")
    dormancy = _require_object(value.get("dormancy"), "dormancy")
    expected_dormancy = {
        "population_materialization_authorized",
        "waveform_synthesis_authorized",
        "scientific_test_execution_authorized",
        "P0_authorized",
        "P1_authorized",
        "P2_authorized",
        "production_capability_implemented",
        "claim_marker_implemented",
        "real_data_access_authorized",
        "H17_population_use_authorized",
        "model_or_checkpoint_access_authorized",
        "training_or_calibration_authorized",
        "locked_test_used",
    }
    if set(dormancy) != expected_dormancy:
        raise ValueError("H24 dormant harness dormancy keys mismatch.")
    for name, enabled in dormancy.items():
        if type(enabled) is not bool:
            raise ValueError(f"H24 dormancy flag {name} must be boolean.")
        if name != "locked_test_used" and enabled:
            raise PermissionError(f"H24 dormant harness unexpectedly authorizes {name}.")
    if dormancy.get("locked_test_used") is not False:
        raise PermissionError("H24 dormant harness cannot use locked test.")


def _validate_binding(value: Mapping[str, object]) -> None:
    expected_entries = {
        "H24_successor_contract": (H24_SUCCESSOR_RELATIVE_PATH, H24_SUCCESSOR_SHA256),
        "H24_population_manifest": (H24_POPULATION_RELATIVE_PATH, H24_POPULATION_SHA256),
        "H24_test_manifest": (H24_TEST_RELATIVE_PATH, H24_TEST_SHA256),
    }
    for name, (path, digest) in expected_entries.items():
        entry = _require_object(value.get(name), f"binding {name}")
        if entry.get("path") != path.as_posix() or entry.get("sha256") != digest:
            raise ValueError(f"H24 binding {name} mismatch.")
    authorization = _require_object(value.get("authorization"), "binding authorization")
    for forbidden in (
        "implementation_authorized",
        "population_creation_authorized",
        "waveform_synthesis_authorized",
        "scientific_execution_authorized",
        "real_data_access_authorized",
        "H17_population_use_authorized",
        "training_authorized",
    ):
        if authorization.get(forbidden) is not False:
            raise PermissionError(f"H24 binding unexpectedly authorizes {forbidden}.")
    if authorization.get("locked_test_used") is not False:
        raise PermissionError("H24 binding cannot use locked test.")


def _resolve_fixtures(population: Mapping[str, object]) -> tuple[H24FixtureSpecification, ...]:
    if population.get("purpose") != "harmonic_censoring_h24_population_manifest_contract_only":
        raise ValueError("H24 population purpose mismatch.")
    if population.get("status") != "specifications_only_not_materialized":
        raise ValueError("H24 population must remain unmaterialized.")
    fixture_ids = _require_array(population.get("fixture_ids"), "fixture IDs")
    specs = _require_array(
        population.get("fixture_specifications"), "fixture specifications"
    )
    if len(fixture_ids) != 175 or len(specs) != 175:
        raise ValueError("H24 population must contain exactly 175 specifications.")
    if any(type(item) is not str or not item for item in fixture_ids):
        raise ValueError("H24 fixture IDs must be non-empty strings.")
    if len(set(fixture_ids)) != len(fixture_ids):
        raise ValueError("H24 fixture IDs must be unique.")
    resolved: list[H24FixtureSpecification] = []
    for fixture_id, raw_spec in zip(fixture_ids, specs):
        spec = _require_object(raw_spec, f"fixture {fixture_id}")
        if spec.get("fixture_id") != fixture_id:
            raise ValueError(f"H24 fixture specification {fixture_id} identity mismatch.")
        if spec.get("waveform_synthesized") is not False:
            raise PermissionError(f"H24 fixture {fixture_id} is already synthesized.")
        if spec.get("scientific_outcome_present") is not False:
            raise PermissionError(f"H24 fixture {fixture_id} carries an outcome.")
        canonical = canonical_json_bytes(spec)
        resolved.append(
            H24FixtureSpecification(fixture_id, canonical, _sha256(canonical))
        )
    return tuple(resolved)


def _resolve_tests(
    manifest: Mapping[str, object], fixture_ids: tuple[str, ...]
) -> tuple[
    tuple[H24TestSpecification, ...],
    Mapping[str, Mapping[str, object]],
    Mapping[str, Mapping[str, object]],
    bytes,
]:
    if manifest.get("purpose") != "harmonic_censoring_h24_full_test_plan_contract_only":
        raise ValueError("H24 test manifest purpose mismatch.")
    if manifest.get("status") != "test_specifications_only_not_implemented":
        raise ValueError("H24 test manifest must remain specification-only.")
    test_ids = _require_array(manifest.get("test_ids"), "test IDs")
    tests = _require_array(manifest.get("tests"), "tests")
    if len(test_ids) != 72 or len(tests) != 72:
        raise ValueError("H24 test manifest must contain exactly 72 tests.")
    if len(set(test_ids)) != 72:
        raise ValueError("H24 test IDs must be unique.")
    fixture_set = set(fixture_ids)
    resolved: list[H24TestSpecification] = []
    for test_id, raw_test in zip(test_ids, tests):
        test = _require_object(raw_test, f"test {test_id}")
        if test.get("id") != test_id:
            raise ValueError(f"H24 test {test_id} identity mismatch.")
        if test.get("implementation_exists") is not False or test.get("test_executed") is not False:
            raise PermissionError(f"H24 test {test_id} manifest state is not dormant.")
        selection = _require_object(
            test.get("fixture_selection"), f"test {test_id} fixture selection"
        )
        if selection.get("mode") != "EXACT_IDS":
            raise ValueError(f"H24 test {test_id} selection mode mismatch.")
        selected = _require_array(
            selection.get("resolved_fixture_ids"),
            f"test {test_id} resolved fixture IDs",
        )
        if any(type(item) is not str or item not in fixture_set for item in selected):
            raise ValueError(f"H24 test {test_id} references an unbound fixture.")
        if len(selected) != len(set(selected)):
            raise ValueError(f"H24 test {test_id} duplicates a fixture ID.")
        if not selected and not selection.get("empty_selection_reason"):
            raise ValueError(f"H24 test {test_id} empty selection is unexplained.")
        canonical = canonical_json_bytes(test)
        resolved.append(
            H24TestSpecification(
                test_id=test_id,
                phase=_require_string(test.get("phase"), f"test {test_id} phase"),
                resolved_fixture_ids=tuple(selected),
                canonical_specification=canonical,
                specification_sha256=_sha256(canonical),
            )
        )
    operator_contract = _require_object(
        manifest.get("evidence_operator_contract"), "evidence operator contract"
    )
    operators = _require_object(
        operator_contract.get("operator_registry"), "operator registry"
    )
    sentinels = _require_object(
        operator_contract.get("sentinel_registry"), "sentinel registry"
    )
    nonvacuity = _require_object(
        operator_contract.get("evidence_nonvacuity_contract"),
        "evidence nonvacuity contract",
    )
    used: set[str] = set()
    for test in tests[1:]:
        evidence = _require_object(
            _require_object(test, "test").get("evidence_schema"), "evidence schema"
        )
        for side in ("primary_rules", "inverse_rules"):
            for rule in _require_array(evidence.get(side), side):
                used.add(_require_string(_require_object(rule, "rule").get("operator"), "operator"))
    if set(operators) != used or len(operators) != 27:
        raise ValueError("H24 closed operator registry does not match used operators.")
    if set(sentinels) != {"__PLAN_FIXTURE_IDS__"}:
        raise ValueError("H24 closed sentinel registry mismatch.")
    if nonvacuity.get("array_evidence_default_minimum_items") != 1:
        raise ValueError("H24 nonvacuity minimum mismatch.")
    if nonvacuity.get("explicit_empty_array_exceptions") != {}:
        raise ValueError("H24 empty evidence exceptions must remain empty.")
    return (
        tuple(resolved),
        MappingProxyType({key: MappingProxyType(value) for key, value in operators.items()}),
        MappingProxyType({key: MappingProxyType(value) for key, value in sentinels.items()}),
        canonical_json_bytes(nonvacuity),
    )


def _build_evaluator_registry(
    tests: tuple[H24TestSpecification, ...]
) -> Mapping[str, H24EvaluatorRegistration]:
    registry = {
        test.test_id: H24EvaluatorRegistration(
            test_id=test.test_id,
            phase=test.phase,
            resolved_fixture_ids=test.resolved_fixture_ids,
            producer_id=f"{test.test_id}:persisted-evidence-producer:DORMANT",
            recomputer_id=f"{test.test_id}:independent-recomputer:V1",
        )
        for test in tests
    }
    if len(registry) != 72:
        raise ValueError("H24 evaluator registry must contain exactly 72 entries.")
    return MappingProxyType(registry)


def load_h24_dormant_harness_plan(repository_root: Path) -> H24DormantHarnessPlan:
    repository = Path(repository_root).resolve(strict=True)
    contract_raw = (repository / H24_HARNESS_CONTRACT_RELATIVE_PATH).read_bytes()
    if _sha256(contract_raw) != H24_HARNESS_CONTRACT_SHA256:
        raise ValueError("H24 dormant harness contract SHA-256 mismatch.")
    contract = _parse_json_object(contract_raw, "dormant harness contract")
    _validate_harness_contract(contract)
    successor_raw, _ = _load_sealed(
        repository, H24_SUCCESSOR_RELATIVE_PATH, H24_SUCCESSOR_SHA256, "successor"
    )
    population_raw, population = _load_sealed(
        repository, H24_POPULATION_RELATIVE_PATH, H24_POPULATION_SHA256, "population"
    )
    test_raw, tests_manifest = _load_sealed(
        repository, H24_TEST_RELATIVE_PATH, H24_TEST_SHA256, "test manifest"
    )
    binding_raw, binding = _load_sealed(
        repository, H24_BINDING_RELATIVE_PATH, H24_BINDING_SHA256, "binding"
    )
    _validate_binding(binding)
    fixtures = _resolve_fixtures(population)
    tests, operators, sentinels, nonvacuity = _resolve_tests(
        tests_manifest, tuple(item.fixture_id for item in fixtures)
    )
    return _attest_h24_plan(H24DormantHarnessPlan(
        repository_root=repository,
        fixtures=fixtures,
        tests=tests,
        evaluator_registry=_build_evaluator_registry(tests),
        operator_registry=operators,
        sentinel_registry=sentinels,
        evidence_nonvacuity_contract_bytes=nonvacuity,
        raw_sha256=MappingProxyType(
            {
                "successor": _sha256(successor_raw),
                "population": _sha256(population_raw),
                "test_manifest": _sha256(test_raw),
                "binding": _sha256(binding_raw),
                "harness_contract": _sha256(contract_raw),
            }
        ),
        flags=H24DormancyFlags(
            fixture_translation_authorized=True,
            recomputation_from_persisted_operands_authorized=True,
            population_materialization_authorized=False,
            waveform_synthesis_authorized=False,
            scientific_test_execution_authorized=False,
            real_data_access_authorized=False,
            model_or_checkpoint_access_authorized=False,
            training_or_calibration_authorized=False,
            locked_test_used=False,
        ),
    ))


def translate_h24_fixture_specification(
    plan: H24DormantHarnessPlan, fixture_id: str
) -> H24DormantFixtureRecipe:
    plan = _require_h24_attested_plan(plan)
    by_id = {item.fixture_id: item for item in plan.fixtures}
    if fixture_id not in by_id:
        raise KeyError(f"H24 unknown fixture ID {fixture_id!r}.")
    source = by_id[fixture_id]
    spec = source.as_dict()
    seed = spec.get("synthesis_seed")
    if type(seed) is not int or seed < 0:
        raise ValueError(f"H24 fixture {fixture_id} synthesis seed is invalid.")
    axis = spec.get("variant_axis")
    if axis is not None and type(axis) is not str:
        raise ValueError(f"H24 fixture {fixture_id} variant axis is invalid.")
    return H24DormantFixtureRecipe(
        fixture_id=fixture_id,
        fixture_kind=_require_string(spec.get("fixture_kind"), "fixture kind"),
        base_id=_require_string(spec.get("base_id"), "base ID"),
        variant_axis=axis,
        synthesis_seed=seed,
        base_fixture_parameters=_freeze_json(
            _require_object(spec.get("base_fixture_parameters"), "base parameters")
        ),  # type: ignore[arg-type]
        variant_parameters=_freeze_json(
            _require_object(spec.get("variant_parameters"), "variant parameters")
        ),  # type: ignore[arg-type]
        transform_rule=_freeze_json(spec.get("transform_rule")),
        expected_target=_freeze_json(
            _require_object(spec.get("expected_target"), "expected target")
        ),  # type: ignore[arg-type]
        source_specification_sha256=source.specification_sha256,
    )


def translate_all_h24_fixture_specifications(
    plan: H24DormantHarnessPlan,
) -> tuple[H24DormantFixtureRecipe, ...]:
    plan = _require_h24_attested_plan(plan)
    recipes = tuple(
        translate_h24_fixture_specification(plan, fixture_id)
        for fixture_id in plan.fixture_ids
    )
    if len(recipes) != 175:
        raise ValueError("H24 dormant translation must yield exactly 175 recipes.")
    return recipes


def require_h24_population_materialization_authorized(_: object) -> None:
    raise PermissionError(
        "H24 population materialization remains unauthorized; the harness is dormant."
    )


def require_h24_scientific_execution_authorized(_: object) -> None:
    raise PermissionError(
        "H24 scientific execution remains unauthorized; P0/P1/P2 cannot run."
    )


__all__ = [
    "H24_BINDING_SHA256",
    "H24DormancyFlags",
    "H24DormantFixtureRecipe",
    "H24DormantHarnessPlan",
    "H24EvaluatorRegistration",
    "H24FixtureSpecification",
    "H24_HARNESS_CONTRACT_SHA256",
    "H24TestSpecification",
    "H24_POPULATION_SHA256",
    "H24_SUCCESSOR_SHA256",
    "H24_TEST_SHA256",
    "canonical_json_bytes",
    "load_h24_dormant_harness_plan",
    "require_h24_population_materialization_authorized",
    "require_h24_scientific_execution_authorized",
    "translate_all_h24_fixture_specifications",
    "translate_h24_fixture_specification",
]
