"""Strict, standard-library-only loader for the dormant H26 contracts.

Loading this module or a plan cannot synthesize audio, import NumPy, create an
authority, or execute a preregistered test.  The three reviewed JSON blobs are
the sole scientific authority for the dormant implementation.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Sequence


SCIENTIFIC_CONTRACT_PATH = Path(
    "configs/harmonic_censoring_h26_scientific_preregistration_contract.json"
)
FIXTURE_SPECIFICATIONS_PATH = Path(
    "configs/harmonic_censoring_h26_fixture_specifications.json"
)
TEST_MANIFEST_PATH = Path("configs/harmonic_censoring_h26_test_manifest.json")

SCIENTIFIC_CONTRACT_SHA256 = "8ecbb1da33e67e78bb76a2b0364d0d5c1697414a711418a030aafb000943b583"
FIXTURE_SPECIFICATIONS_SHA256 = "c8e66f7f9d200451559bf538af5b6dd0b0e7131e042588b6f13ec8655804fc28"
TEST_MANIFEST_SHA256 = "f64b55a4b5dc21da0e2dc4bf9deb712073af59f3d67fd6e3d7d019ce8037e073"

OUTCOMES = (
    "BIRTH_SUPPORTED",
    "NO_BIRTH",
    "AMBIGUOUS",
    "ALREADY_ACTIVE_HISTORY",
)
PHASES = ("P0", "P1", "P2")
SOURCE_FIELDS = frozenset({
    "source_id", "pitch", "gain", "onset_sample", "envelope_id",
    "envelope_parameters", "partial_ranks", "phase_radians", "cents", "B",
})


def sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(value: object, *, line: bool = False) -> bytes:
    raw = json.dumps(
        value, ensure_ascii=False, allow_nan=False, sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return raw + (b"\n" if line else b"")


def _pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H26 JSON duplicate key {key!r}.")
        result[key] = value
    return result


def _nonfinite(token: str) -> None:
    raise ValueError(f"H26 JSON forbids {token!r}.")


def parse_strict_json(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H26 {label} must be UTF-8 LF without BOM.")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs,
            parse_constant=_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"H26 invalid {label} JSON.") from exc
    if type(value) is not dict:
        raise ValueError(f"H26 {label} root must be an object.")
    return value


def _bound_json(repository: Path, relative: Path, digest: str) -> dict[str, object]:
    path = (repository / relative).resolve(strict=True)
    try:
        path.relative_to(repository)
    except ValueError as exc:
        raise ValueError(f"H26 path escapes repository: {relative}.") from exc
    raw = path.read_bytes()
    if sha256_bytes(raw) != digest:
        raise ValueError(f"H26 {relative} SHA-256 mismatch.")
    return parse_strict_json(raw, str(relative))


@dataclass(frozen=True)
class H26TestSpecification:
    test_id: str
    order: int
    phase: str
    objective: str
    fixture_ids: tuple[str, ...]
    oracle: str
    pass_rule: str
    kill_status: str
    perturbation_grid_id: str | None


@dataclass(frozen=True)
class H26DormantPlan:
    repository_root: Path
    contract: Mapping[str, object]
    specifications: Mapping[str, object]
    test_manifest: Mapping[str, object]
    fixtures: tuple[Mapping[str, object], ...]
    recipes: Mapping[str, Mapping[str, object]]
    collision_fixture_ids: tuple[str, ...]
    tests: tuple[H26TestSpecification, ...]

    @property
    def fixture_ids(self) -> tuple[str, ...]:
        return tuple(str(item["id"]) for item in self.fixtures)

    @property
    def test_ids(self) -> tuple[str, ...]:
        return tuple(item.test_id for item in self.tests)

    def fixture(self, fixture_id: str) -> Mapping[str, object]:
        for item in self.fixtures:
            if item["id"] == fixture_id:
                return item
        raise KeyError(fixture_id)


def _require_source(source: object, fixture_id: str) -> None:
    if type(source) is not dict or set(source) != SOURCE_FIELDS:
        raise ValueError(f"H26 {fixture_id} source schema mismatch.")
    if type(source["source_id"]) is not str or not source["source_id"]:
        raise ValueError(f"H26 {fixture_id} source_id invalid.")
    if type(source["pitch"]) is not int or not 0 <= source["pitch"] <= 127:
        raise ValueError(f"H26 {fixture_id} pitch invalid.")
    if type(source["gain"]) not in (int, float) or float(source["gain"]) <= 0.0:
        raise ValueError(f"H26 {fixture_id} gain invalid.")
    if type(source["onset_sample"]) is not int or not 0 <= source["onset_sample"] < 16640:
        raise ValueError(f"H26 {fixture_id} onset invalid.")
    ranks = source["partial_ranks"]
    if type(ranks) is not list or ranks != sorted(set(ranks)) or not ranks:
        raise ValueError(f"H26 {fixture_id} partial ranks invalid.")
    if any(type(rank) is not int or not 1 <= rank <= 8 for rank in ranks):
        raise ValueError(f"H26 {fixture_id} partial rank out of range.")
    if source["cents"] != 0.0 or source["B"] != 0.0:
        raise ValueError(f"H26 {fixture_id} baseline cents/B drift.")
    envelope = source["envelope_id"]
    params = source["envelope_parameters"]
    if envelope == "H26_ENV_ATTACK_DECAY_V1":
        if params != {}:
            raise ValueError(f"H26 {fixture_id} attack envelope parameters drift.")
    elif envelope == "H26_ENV_EXP_DECAY_V1":
        if type(params) is not dict or set(params) != {"decay_samples"}:
            raise ValueError(f"H26 {fixture_id} decay envelope parameters missing.")
        if type(params["decay_samples"]) not in (int, float) or float(params["decay_samples"]) <= 0:
            raise ValueError(f"H26 {fixture_id} decay invalid.")
    else:
        raise ValueError(f"H26 {fixture_id} unknown envelope.")


def _validate_recipe(fixture: Mapping[str, object], recipe: object) -> Mapping[str, object]:
    fixture_id = str(fixture["id"])
    if type(recipe) is not dict or not {"sources", "noise"}.issubset(recipe):
        raise ValueError(f"H26 {fixture_id} recipe schema missing.")
    sources = recipe["sources"]
    if type(sources) is not list:
        raise ValueError(f"H26 {fixture_id} sources must be an array.")
    source_ids: list[str] = []
    for source in sources:
        _require_source(source, fixture_id)
        source_ids.append(str(source["source_id"]))
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(f"H26 {fixture_id} duplicate source ID.")
    noise = recipe["noise"]
    if type(noise) is not dict or noise.get("kind") not in {"NONE", "WHITE_GAUSSIAN_SNR_V1"}:
        raise ValueError(f"H26 {fixture_id} noise schema invalid.")
    if noise["kind"] == "NONE" and set(noise) != {"kind"}:
        raise ValueError(f"H26 {fixture_id} NONE noise has implicit fields.")
    if noise["kind"] == "WHITE_GAUSSIAN_SNR_V1":
        required = {"kind", "snr_db", "seed_uint64_decimal", "seed_preimage", "support_samples_inclusive"}
        if set(noise) != required or noise["support_samples_inclusive"] != [8192, 16639]:
            raise ValueError(f"H26 {fixture_id} white-noise schema drift.")
        seed = int.from_bytes(
            hashlib.sha256(str(noise["seed_preimage"]).encode("utf-8")).digest()[:8],
            "little",
        )
        if str(seed) != noise["seed_uint64_decimal"]:
            raise ValueError(f"H26 {fixture_id} noise seed mismatch.")
    _crosscheck_recipe(fixture, recipe)
    return MappingProxyType(dict(recipe))


def _source(recipe: Mapping[str, object], source_id: str) -> Mapping[str, object] | None:
    for source in recipe["sources"]:
        if source["source_id"] == source_id:
            return source
    return None


def _crosscheck_recipe(fixture: Mapping[str, object], recipe: Mapping[str, object]) -> None:
    fixture_id = str(fixture["id"])
    params = fixture.get("parameters")
    if type(params) is not dict:
        raise ValueError(f"H26 {fixture_id} parameters missing.")
    candidate = _source(recipe, "candidate")
    old = _source(recipe, "old")
    if candidate is not None:
        if candidate["pitch"] != fixture["candidate_pitch"]:
            raise ValueError(f"H26 {fixture_id} candidate pitch divergence.")
        for field, source_field in (
            ("candidate_gain", "gain"), ("onset_sample", "onset_sample"),
            ("phase_radians", "phase_radians"),
        ):
            if field in params and candidate[source_field] != params[field]:
                raise ValueError(f"H26 {fixture_id} candidate {field} divergence.")
    if old is not None:
        if old["pitch"] != params.get("old_pitch"):
            raise ValueError(f"H26 {fixture_id} old pitch divergence.")
        if "old_gain" in params and old["gain"] != params["old_gain"]:
            raise ValueError(f"H26 {fixture_id} old gain divergence.")
        if "old_decay_samples" in params and old["envelope_parameters"].get("decay_samples") != params["old_decay_samples"]:
            raise ValueError(f"H26 {fixture_id} old decay divergence.")
    if "active_pitches" in params:
        if [item["pitch"] for item in recipe["sources"]] != params["active_pitches"]:
            raise ValueError(f"H26 {fixture_id} active-pitch recipe divergence.")
    if params.get("fundamental_masked") is True:
        if candidate is None or candidate["partial_ranks"] != list(range(1, 9)):
            raise ValueError(f"H26 {fixture_id} masked H1 must remain physical.")
    if "observed_candidate_gain" in params:
        if params["observed_candidate_gain"] != 0.0 or candidate is not None or recipe.get("candidate_physically_absent") is not True:
            raise ValueError(f"H26 {fixture_id} candidate-absence divergence.")
    if fixture["category"] == "active_history":
        if recipe["sources"] != [] or recipe.get("history_waveform_convention") != "SILENT_STATE_ONLY":
            raise ValueError(f"H26 {fixture_id} history-only waveform divergence.")


def load_h26_dormant_plan(repository_root: Path) -> H26DormantPlan:
    """Load and validate only the three reviewed declarative H26 blobs."""

    repository = Path(repository_root).resolve(strict=True)
    contract = _bound_json(repository, SCIENTIFIC_CONTRACT_PATH, SCIENTIFIC_CONTRACT_SHA256)
    specifications = _bound_json(repository, FIXTURE_SPECIFICATIONS_PATH, FIXTURE_SPECIFICATIONS_SHA256)
    test_manifest = _bound_json(repository, TEST_MANIFEST_PATH, TEST_MANIFEST_SHA256)
    if any(type(blob.get("schema_version")) is not int or blob["schema_version"] != 1 for blob in (
        contract, specifications, test_manifest,
    )):
        raise ValueError("H26 schema version must be exact integer 1.")
    if contract.get("status") != "declarative_dormant_no_implementation_no_execution":
        raise ValueError("H26 scientific contract authority state changed.")
    authorization = contract.get("authorization_boundary")
    if type(authorization) is not dict or any(value is not False for value in authorization.values()):
        raise ValueError("H26 authorization boundary must remain entirely false.")
    if specifications.get("materialized") is not False or specifications.get("waveform_count") != 0 or specifications.get("generation_authorized") is not False:
        raise ValueError("H26 fixture specifications are no longer dormant.")
    fixtures_raw = specifications.get("fixtures")
    recipes_raw = specifications.get("baseline_waveform_recipes")
    collision = specifications.get("exact_nonzero_collision_contract")
    if type(fixtures_raw) is not list or type(recipes_raw) is not dict or type(collision) is not dict:
        raise ValueError("H26 fixture/recipe/collision sections missing.")
    if len(fixtures_raw) != 40:
        raise ValueError("H26 fixture cardinality mismatch.")
    fixtures: list[Mapping[str, object]] = []
    for ordinal, raw in enumerate(fixtures_raw, start=1):
        if type(raw) is not dict or raw.get("order") != ordinal:
            raise ValueError("H26 fixture schema/order mismatch.")
        if raw.get("expected") not in OUTCOMES:
            raise ValueError("H26 fixture expected outcome invalid.")
        fixtures.append(MappingProxyType(dict(raw)))
    ids = tuple(str(item["id"]) for item in fixtures)
    if len(set(ids)) != 40 or ids != tuple(f"H26-F-{prefix}{index:02d}" for prefix, count in (("P",10),("N",10),("H",8),("A",12)) for index in range(1,count+1)):
        raise ValueError("H26 fixture identity/order mismatch.")
    collision_ids_raw = collision.get("applies_to_fixture_ids")
    if type(collision_ids_raw) is not list:
        raise ValueError("H26 collision identity array missing.")
    collision_ids = tuple(str(value) for value in collision_ids_raw)
    if collision_ids != tuple(f"H26-F-A{index:02d}" for index in range(1, 7)):
        raise ValueError("H26 collision fixture set drift.")
    expected_collision = {
        "allowed_sample_indices": [0, 16639],
        "old_note_on_sample": 8192,
        "collision_onset_sample": 16128,
        "old_background_partial_ranks": list(range(1, 9)),
        "old_background_collision_rank_excluded": True,
        "old_background_phase_radians": 0.0,
        "candidate_partial_ranks_present": [1],
        "candidate_partial_ranks_absent": list(range(2, 9)),
        "old_collision_component_present_before_collision_onset": False,
        "candidate_component_present_before_collision_onset": False,
    }
    for key, expected in expected_collision.items():
        if collision.get(key) != expected:
            raise ValueError(f"H26 collision contract {key} drift.")
    for fixture in fixtures:
        if fixture["id"] not in collision_ids:
            continue
        params = fixture.get("parameters", {})
        rank = params.get("collision_harmonic_rank")
        old_gain = params.get("old_source_gain")
        candidate_gain = params.get("candidate_source_gain")
        if rank not in {2, 4, 8} or type(old_gain) not in (int, float) or float(old_gain) <= 0.0:
            raise ValueError("H26 collision fixture rank/gain invalid.")
        if type(candidate_gain) not in (int, float) or float(candidate_gain) != float(old_gain) / float(rank):
            raise ValueError("H26 collision fixture exact gain equality drift.")
    if set(recipes_raw) != set(ids) - set(collision_ids) or len(recipes_raw) != 34:
        raise ValueError("H26 recipe coverage must be exactly 34+6.")
    recipes = {
        fixture_id: _validate_recipe(next(item for item in fixtures if item["id"] == fixture_id), raw)
        for fixture_id, raw in recipes_raw.items()
    }
    tests_raw = test_manifest.get("tests")
    if type(tests_raw) is not list or len(tests_raw) != 27:
        raise ValueError("H26 test cardinality mismatch.")
    tests: list[H26TestSpecification] = []
    for ordinal, raw in enumerate(tests_raw, start=1):
        if type(raw) is not dict:
            raise ValueError("H26 test record must be an object.")
        required = {"id", "order", "phase", "objective", "fixture_ids", "oracle", "pass_rule", "kill_status"}
        allowed = required | {"perturbation_grid_id"}
        if not required.issubset(raw) or not set(raw).issubset(allowed):
            raise ValueError("H26 test record schema mismatch.")
        phase = PHASES[(ordinal - 1) // 9]
        expected_id = f"H26-T-{phase}-{((ordinal - 1) % 9) + 1:03d}"
        fixture_refs = tuple(str(value) for value in raw["fixture_ids"])
        if raw["id"] != expected_id or raw["order"] != ordinal or raw["phase"] != phase:
            raise ValueError("H26 test ID/order/phase mismatch.")
        if len(fixture_refs) != len(set(fixture_refs)) or not set(fixture_refs).issubset(ids):
            raise ValueError("H26 test fixture reference invalid.")
        grid = raw.get("perturbation_grid_id")
        if grid is not None and grid not in contract.get("p2_perturbation_grids", {}):
            raise ValueError("H26 test perturbation grid missing.")
        tests.append(H26TestSpecification(
            test_id=str(raw["id"]), order=ordinal, phase=phase,
            objective=str(raw["objective"]), fixture_ids=fixture_refs,
            oracle=str(raw["oracle"]), pass_rule=str(raw["pass_rule"]),
            kill_status=str(raw["kill_status"]),
            perturbation_grid_id=None if grid is None else str(grid),
        ))
    return H26DormantPlan(
        repository_root=repository,
        contract=MappingProxyType(contract),
        specifications=MappingProxyType(specifications),
        test_manifest=MappingProxyType(test_manifest),
        fixtures=tuple(fixtures), recipes=MappingProxyType(recipes),
        collision_fixture_ids=collision_ids, tests=tuple(tests),
    )


__all__ = [
    "FIXTURE_SPECIFICATIONS_PATH", "FIXTURE_SPECIFICATIONS_SHA256",
    "H26DormantPlan", "H26TestSpecification", "OUTCOMES",
    "SCIENTIFIC_CONTRACT_PATH", "SCIENTIFIC_CONTRACT_SHA256",
    "TEST_MANIFEST_PATH", "TEST_MANIFEST_SHA256", "canonical_json_bytes",
    "load_h26_dormant_plan", "parse_strict_json", "sha256_bytes",
]
