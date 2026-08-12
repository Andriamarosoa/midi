"""Strict standard-library-only loader for the reviewed dormant H27 design.

The loader binds the five reviewed Git blobs.  It performs no synthesis,
imports no numeric runtime, creates no authority, and writes no file.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence


PREREGISTRATION_PATH = Path("configs/harmonic_censoring_h27_scientific_preregistration_contract.json")
ZERO_CONTEXT_PATH = Path("configs/harmonic_censoring_h27_zero_context_synthetic_cases.json")
FIXTURE_SPECIFICATIONS_PATH = Path("configs/harmonic_censoring_h27_fixture_specifications.json")
TEST_MANIFEST_PATH = Path("configs/harmonic_censoring_h27_test_manifest.json")
FUTURE_POPULATION_PATH = Path("configs/harmonic_censoring_h27_future_population_contract.json")

REVIEWED_GIT_BLOBS = MappingProxyType({
    PREREGISTRATION_PATH: "869c70f7c643d8387645377a8cf5166b8728914d",
    ZERO_CONTEXT_PATH: "1b57c27936cfb0befeceaf0c30ff73189f304672",
    FIXTURE_SPECIFICATIONS_PATH: "9aea04053a13a3f5cf81b461a58977c377600f5b",
    TEST_MANIFEST_PATH: "594b33c8c579733718f7f0445d3780c9f60b2b2a",
    FUTURE_POPULATION_PATH: "fc82c1c7b3dec837a63c6f86afed9a5f724f7aad",
})
HYPOTHESIS_ID = "H27_ROLE_AWARE_ZERO_CONTEXT_V1"
POPULATION_NAMESPACE = "H27_SYNTHETIC_V1"
TEST_NAMESPACE = "H27_TEST_V1"
OUTCOMES = ("BIRTH_SUPPORTED", "NO_BIRTH", "AMBIGUOUS", "ALREADY_ACTIVE_HISTORY")
ROLE_ORDER = ("current_short", "previous_short", "current_long", "previous_long")


def git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H27 duplicate JSON key {key!r}.")
        result[key] = value
    return result


def _nonfinite(token: str) -> None:
    raise ValueError(f"H27 forbids non-finite JSON token {token!r}.")


def parse_strict_json(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H27 {label} must be UTF-8 LF without BOM.")
    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=_pairs, parse_constant=_nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"H27 invalid {label} JSON.") from exc
    if type(value) is not dict:
        raise ValueError(f"H27 {label} root must be an object.")
    return value


def deep_freeze(value: object) -> object:
    if type(value) is dict:
        return MappingProxyType({key: deep_freeze(item) for key, item in value.items()})
    if type(value) is list:
        return tuple(deep_freeze(item) for item in value)
    if type(value) in (str, int, float, bool) or value is None:
        return value
    raise TypeError(f"H27 cannot freeze {type(value).__name__}.")


def deep_thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: deep_thaw(item) for key, item in value.items()}
    if type(value) is tuple:
        return [deep_thaw(item) for item in value]
    if type(value) in (str, int, float, bool) or value is None:
        return value
    raise TypeError(f"H27 cannot thaw {type(value).__name__}.")


def _bound_json(repository: Path, relative: Path) -> dict[str, object]:
    path = (repository / relative).resolve(strict=True)
    try:
        path.relative_to(repository)
    except ValueError as exc:
        raise ValueError(f"H27 path escapes repository: {relative}.") from exc
    raw = path.read_bytes()
    if git_blob_sha1(raw) != REVIEWED_GIT_BLOBS[relative]:
        raise ValueError(f"H27 reviewed Git blob mismatch: {relative}.")
    return parse_strict_json(raw, str(relative))


@dataclass(frozen=True)
class H27DormantPlan:
    repository_root: Path
    preregistration: Mapping[str, object]
    zero_context: Mapping[str, object]
    specifications: Mapping[str, object]
    test_manifest: Mapping[str, object]
    population_contract: Mapping[str, object]

    @property
    def fixtures(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self.specifications["fixtures"])

    @property
    def fixture_ids(self) -> tuple[str, ...]:
        return tuple(str(item["id"]) for item in self.fixtures)

    @property
    def tests(self) -> tuple[Mapping[str, object], ...]:
        return tuple(self.test_manifest["tests"])


def _require_false_authorizations(value: object) -> None:
    if isinstance(value, Mapping):
        for key, item in value.items():
            if str(key).endswith("_authorized") or key in {
                "population_exists", "tests_implemented", "tests_executed",
                "runner_exists", "engine_exists", "recomputer_exists",
                "authority_exists", "claim_exists",
            }:
                if item is not False:
                    raise ValueError(f"H27 forbidden active state {key!r}.")
            _require_false_authorizations(item)
    elif type(value) is tuple:
        for item in value:
            _require_false_authorizations(item)


def _validate_fixture_design(specifications: Mapping[str, object]) -> None:
    fixtures = specifications.get("fixtures")
    if type(fixtures) is not tuple or len(fixtures) != 17:
        raise ValueError("H27 fixture cardinality mismatch.")
    ids: list[str] = []
    categories: dict[str, int] = {}
    for order, fixture in enumerate(fixtures, start=1):
        if not isinstance(fixture, Mapping) or fixture.get("order") != order:
            raise ValueError("H27 fixture order mismatch.")
        fixture_id = fixture.get("id")
        if type(fixture_id) is not str or not fixture_id.startswith("H27-F-"):
            raise ValueError("H27 fixture ID invalid.")
        if fixture.get("expected") not in OUTCOMES:
            raise ValueError("H27 fixture outcome invalid.")
        ids.append(fixture_id)
        category = str(fixture.get("category"))
        categories[category] = categories.get(category, 0) + 1
    if len(set(ids)) != 17 or categories != {"positive":4,"negative":4,"active_history":2,"ambiguous":7}:
        raise ValueError("H27 fixture identities/categories mismatch.")
    collisions = specifications.get("exact_nonzero_collision_contract")
    recipes = specifications.get("baseline_waveform_recipes")
    if not isinstance(collisions, Mapping) or not isinstance(recipes, Mapping):
        raise ValueError("H27 recipe/collision contract missing.")
    collision_ids = tuple(collisions.get("applies_to_fixture_ids", ()))
    if collision_ids != ("H27-F-A01", "H27-F-A02"):
        raise ValueError("H27 collision fixture set mismatch.")
    if set(recipes) != set(ids) - set(collision_ids) or len(recipes) != 15:
        raise ValueError("H27 recipe coverage must be exactly 15+2.")
    mask = specifications.get("sample_valid_mask_contract")
    if not isinstance(mask, Mapping):
        raise ValueError("H27 mask contract missing.")
    if tuple(mask.get("role_order", ())) != ROLE_ORDER or mask.get("samples_per_role") != 16640:
        raise ValueError("H27 role-major mask order/shape mismatch.")
    if mask.get("payload_length_bytes") != 66560 or tuple(mask.get("allowed_byte_values", ())) != (0, 1):
        raise ValueError("H27 role-major mask encoding mismatch.")
    exceptions = mask.get("baseline_exceptions")
    if not isinstance(exceptions, Mapping) or tuple(exceptions) != ("H27-F-A04",):
        raise ValueError("H27 mask exception set mismatch.")


def _cell_ids(manifest: Mapping[str, object]) -> tuple[str, ...]:
    identity = manifest["cell_identity_contract"]
    grids = manifest["perturbation_grids"]
    result: list[str] = []
    import itertools
    for grid_id in identity["grid_order"]:
        grid = grids[grid_id]
        axis_names = tuple(grid["axis_names"])
        token_lists = tuple(tuple(item["value_token"] for item in grid["axes"][axis]) for axis in axis_names)
        cells = tuple(
            "__".join(f"{axis}={token}" for axis, token in zip(axis_names, values))
            for values in itertools.product(*token_lists)
        )
        if len(cells) * len(grid["fixture_ids"]) != grid["record_count"]:
            raise ValueError(f"H27 grid cardinality mismatch: {grid_id}.")
        result.extend(f"{grid_id}/{fixture_id}/{cell}" for fixture_id in grid["fixture_ids"] for cell in cells)
    return tuple(result)


def _validate_test_design(manifest: Mapping[str, object], fixture_ids: tuple[str, ...]) -> None:
    tests = manifest.get("tests")
    if type(tests) is not tuple or len(tests) != 27:
        raise ValueError("H27 test cardinality mismatch.")
    phases = ("P0", "P1", "P2")
    for order, test in enumerate(tests, start=1):
        phase = phases[(order - 1) // 9]
        expected = f"H27-T-{phase}-{((order - 1) % 9) + 1:03d}"
        if test.get("id") != expected or test.get("order") != order or test.get("phase") != phase:
            raise ValueError("H27 test identity/order mismatch.")
    obligations = tuple(manifest.get("r_zero_obligations", ()))
    if obligations != tuple(f"R-ZERO-{index:03d}" for index in range(1, 12)):
        raise ValueError("H27 R-ZERO obligations mismatch.")
    covered = tuple(
        fixture_id for test in tests[9:17] for fixture_id in test["fixture_ids"]
    )
    if len(covered) != 17 or set(covered) != set(fixture_ids):
        raise ValueError("H27 P1 categorical coverage mismatch.")
    cells = _cell_ids(manifest)
    if len(cells) != len(set(cells)) or len(cells) != 107:
        raise ValueError("H27 P2 cell identity mismatch.")


def load_h27_dormant_plan(repository_root: Path) -> H27DormantPlan:
    repository = Path(repository_root).resolve(strict=True)
    raw = {path: _bound_json(repository, path) for path in REVIEWED_GIT_BLOBS}
    frozen = {path: deep_freeze(value) for path, value in raw.items()}
    prereg = frozen[PREREGISTRATION_PATH]
    zero = frozen[ZERO_CONTEXT_PATH]
    specs = frozen[FIXTURE_SPECIFICATIONS_PATH]
    tests = frozen[TEST_MANIFEST_PATH]
    population = frozen[FUTURE_POPULATION_PATH]
    for value in frozen.values():
        if value.get("schema_version") != 1 or type(value.get("schema_version")) is not int:
            raise ValueError("H27 schema version must be exact integer 1.")
        if value.get("hypothesis_id") != HYPOTHESIS_ID:
            raise ValueError("H27 hypothesis binding mismatch.")
    for value in (prereg, specs, tests, population):
        if value.get("population_namespace") != POPULATION_NAMESPACE or value.get("test_namespace") != TEST_NAMESPACE:
            raise ValueError("H27 namespace binding mismatch.")
    if zero.get("case_count") != 11 or len(zero.get("cases", ())) != 11:
        raise ValueError("H27 zero-context case count mismatch.")
    _validate_fixture_design(specs)
    fixture_ids = tuple(str(item["id"]) for item in specs["fixtures"])
    _validate_test_design(tests, fixture_ids)
    if population.get("baseline_fixture_count") != 17 or population.get("p2_record_count") != 107 or population.get("total_population_record_count") != 124:
        raise ValueError("H27 population count mismatch.")
    if population["sample_valid_mask_payload"].get("payload_length_bytes") != 66560:
        raise ValueError("H27 population mask payload mismatch.")
    for value in frozen.values():
        _require_false_authorizations(value)
    return H27DormantPlan(repository, prereg, zero, specs, tests, population)


def canonical_h27_record_identities(plan: H27DormantPlan) -> tuple[str, ...]:
    baseline = tuple(f"baseline/{fixture_id}" for fixture_id in plan.fixture_ids)
    return baseline + tuple(f"p2/{value}" for value in _cell_ids(plan.test_manifest))


__all__ = ["FIXTURE_SPECIFICATIONS_PATH", "FUTURE_POPULATION_PATH", "H27DormantPlan",
           "PREREGISTRATION_PATH", "REVIEWED_GIT_BLOBS", "TEST_MANIFEST_PATH",
           "ZERO_CONTEXT_PATH", "canonical_h27_record_identities", "deep_freeze",
           "deep_thaw", "git_blob_sha1", "load_h27_dormant_plan", "parse_strict_json"]
