"""Dormant H24 population materializer and one-shot publisher.

This module deliberately has no CLI and never imports NumPy at module import.
The only capability factory requires a future reviewed authorization seal that
does not exist in this commit.  Consequently the claim, synthesis and publish
machinery is implementable and reviewable here, but cannot run operationally.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Sequence
import weakref

from .harmonic_censoring_h24 import (
    H24DormantFixtureRecipe,
    H24DormantHarnessPlan,
    load_h24_dormant_harness_plan,
    translate_all_h24_fixture_specifications,
)


H24_MATERIALIZATION_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_population_materialization_one_shot_contract.json"
)
H24_MATERIALIZATION_CONTRACT_RAW_SHA256 = (
    "b48aa4f417a9857983c79809efe24137d6b82ad0984d20e906286477f05a14ca"
)
H24_AUTHORIZATION_SEAL_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_population_materialization_authorization_seal.json"
)
H24_AUTHORIZATION_COMMIT_ENV = "H24_POPULATION_MATERIALIZATION_AUTHORIZATION_COMMIT"
H24_MATERIALIZER_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/harmonic_censoring_h24_population_materializer.py"
)
H24_HARNESS_SOURCE_RELATIVE_PATH = Path("src/polyphonic/harmonic_censoring_h24.py")
H24_OPERATOR_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/harmonic_censoring_h24_operators.py"
)
H24_APPROVED_HARNESS_COMMIT = "1b6aa27536dd5bfceba62d6bc5c9a499b4c11f18"
H24_APPROVED_HARNESS_BLOB = "1a8759d6587b05e9064c6e033a7b906bd6e2955b"
H24_APPROVED_OPERATOR_BLOB = "7e72ed05dcbebd1f3ed546733a811fbc3be5495e"
H24_POPULATION_ID = "H24_SYNTHETIC_V1"

_RUNTIME_IDENTITY = MappingProxyType(
    {
        "implementation": "CPython",
        "python_version": "3.11.9",
        "numpy_version": "1.26.4",
        "architecture": "arm64",
        "execution_device": "CPU",
        "thread_count": 1,
        "sample_rate_hz": 44100,
        "hop_samples": 256,
    }
)
_FIXED_PATHS = MappingProxyType(
    {
        "claim_marker_path": "tmp/local/harmonic_censoring_h24_synthetic_v1/H24_SYNTHETIC_V1.consumed.json",
        "staging_directory": "tmp/local/harmonic_censoring_h24_synthetic_v1/population.materializing",
        "success_directory": "tmp/local/harmonic_censoring_h24_synthetic_v1/population",
        "terminal_record_path": "tmp/local/harmonic_censoring_h24_synthetic_v1/materialization_terminal.json",
    }
)
_SEALED_HASH_FIELDS = MappingProxyType(
    {
        "successor_contract_raw_sha256": "184d3847a594ffaca263b45befe70d1f5aa63ade0a0ef599d969ba044f4e680a",
        "population_manifest_raw_sha256": "52c88c74c837ad3c6109be466df38bac862e10d93c187fe60e8c5da30bd4b02b",
        "test_manifest_raw_sha256": "7f87e486ffc6fdc2bfa60a5c617eca9b1ce78c570c1d72910173193ad1f7b416",
        "manifest_binding_raw_sha256": "242c00d4d5fd3b9e777676b563f28b94b724159bde81307aebbba9e46608a1b5",
        "dormant_harness_contract_raw_sha256": "72675c6dda2128aa0036b7f0f2379de535fd74445a029f020f24f3f6f15fff39",
    }
)


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_json_line(value: object) -> bytes:
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


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H24 materializer JSON contains duplicate key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H24 materializer JSON contains forbidden token {token!r}.")


def _parse_json_object(raw: bytes, label: str) -> dict[str, object]:
    if b"\r" in raw:
        raise ValueError(f"H24 {label} must use LF bytes only.")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"H24 {label} must be canonical UTF-8 JSON.") from exc
    if type(value) is not dict:
        raise ValueError(f"H24 {label} root must be an object.")
    return value


def _require_exact_keys(
    value: Mapping[str, object], expected: Iterable[str], label: str
) -> None:
    actual = set(value)
    wanted = set(expected)
    if actual != wanted:
        raise ValueError(
            f"H24 {label} keys mismatch: missing={sorted(wanted-actual)}, "
            f"extra={sorted(actual-wanted)}."
        )


def _require_lower_hex(value: object, length: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or any(ch not in "0123456789abcdef" for ch in value)
    ):
        raise ValueError(f"H24 {label} must be lowercase hexadecimal length {length}.")
    return value


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=repository, text=True, encoding="utf-8"
    ).strip()


def _resolve_bound_path(repository: Path, relative: str | Path) -> Path:
    root = repository.resolve(strict=True)
    path = (root / Path(relative)).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("H24 sealed path escapes repository root.") from exc
    return path


@dataclass(frozen=True)
class H24PopulationMaterializationAuthorizationSeal:
    raw_sha256: str
    reviewed_materializer_commit: str
    exact_changed_files: tuple[str, ...]
    materializer_source_blob: str
    materialization_contract_raw_sha256: str


_SEAL_FIELDS = {
    "schema_version",
    "purpose",
    "status",
    "reviewed_materializer_commit",
    "exact_changed_files",
    "materializer_source_blob",
    "materialization_contract_raw_sha256",
    "authorized_action",
}


def validate_h24_population_materialization_authorization_seal(
    payload: Mapping[str, object], *, raw_sha256: str
) -> H24PopulationMaterializationAuthorizationSeal:
    """Validate a future seal without issuing authority or touching science."""

    _require_exact_keys(payload, _SEAL_FIELDS, "authorization seal")
    if type(payload.get("schema_version")) is not int or payload["schema_version"] != 1:
        raise ValueError("H24 authorization seal schema mismatch.")
    if payload.get("purpose") != "harmonic_censoring_h24_population_materialization_authorization_seal":
        raise ValueError("H24 authorization seal purpose mismatch.")
    if payload.get("status") != "reviewed_dormant_materializer_authorized_for_one_shot_activation":
        raise PermissionError("H24 authorization seal status is not active.")
    if payload.get("authorized_action") != "AUTHORIZED_TO_ACTIVATE_H24_ONE_SHOT_POPULATION_MATERIALIZATION":
        raise PermissionError("H24 authorization action mismatch.")
    files = payload.get("exact_changed_files")
    if type(files) is not list or any(type(item) is not str or not item for item in files):
        raise ValueError("H24 authorization changed-file list is invalid.")
    if files != sorted(set(files)):
        raise ValueError("H24 authorization changed-file list must be sorted and unique.")
    digest = _require_lower_hex(
        payload.get("materialization_contract_raw_sha256"), 64, "contract SHA-256"
    )
    if digest != H24_MATERIALIZATION_CONTRACT_RAW_SHA256:
        raise ValueError("H24 authorization seal contract binding mismatch.")
    return H24PopulationMaterializationAuthorizationSeal(
        raw_sha256=_require_lower_hex(raw_sha256, 64, "authorization seal SHA-256"),
        reviewed_materializer_commit=_require_lower_hex(
            payload.get("reviewed_materializer_commit"), 40, "materializer commit"
        ),
        exact_changed_files=tuple(files),
        materializer_source_blob=_require_lower_hex(
            payload.get("materializer_source_blob"), 40, "materializer source blob"
        ),
        materialization_contract_raw_sha256=digest,
    )


class AttestedH24PopulationMaterializationCapability:
    """Immutable factory-only, identity-attested process-local authority."""

    __slots__ = (
        "population_id",
        "materialization_contract_raw_sha256",
        "implementation_commit",
        "materializer_source_blob",
        "harness_source_blob",
        "operator_source_blob",
        "successor_contract_raw_sha256",
        "population_manifest_raw_sha256",
        "test_manifest_raw_sha256",
        "manifest_binding_raw_sha256",
        "dormant_harness_contract_raw_sha256",
        "authorization_seal_path",
        "authorization_seal_raw_sha256",
        "claim_marker_path",
        "staging_directory",
        "success_directory",
        "terminal_record_path",
        "runtime_identity",
        "__weakref__",
    )

    def __init__(self, *args: object, **kwargs: object) -> None:
        del args, kwargs
        raise TypeError("H24 materialization capability construction is factory-only.")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("H24 materialization capability is immutable.")

    def __copy__(self) -> object:
        raise TypeError("H24 materialization capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        raise TypeError("H24 materialization capability cannot be deep-copied.")

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("H24 materialization capability cannot be serialized.")


@dataclass(frozen=True)
class _CapabilityState:
    repository: Path
    activation_commit: str
    plan: H24DormantHarnessPlan
    recipes: tuple[H24DormantFixtureRecipe, ...]
    binding: tuple[object, ...]


def _capability_binding(
    value: AttestedH24PopulationMaterializationCapability,
) -> tuple[object, ...]:
    return tuple(
        tuple(sorted(item.items())) if isinstance(item, Mapping) else item
        for item in (
            value.population_id,
            value.materialization_contract_raw_sha256,
            value.implementation_commit,
            value.materializer_source_blob,
            value.harness_source_blob,
            value.operator_source_blob,
            value.successor_contract_raw_sha256,
            value.population_manifest_raw_sha256,
            value.test_manifest_raw_sha256,
            value.manifest_binding_raw_sha256,
            value.dormant_harness_contract_raw_sha256,
            value.authorization_seal_path,
            value.authorization_seal_raw_sha256,
            value.claim_marker_path,
            value.staging_directory,
            value.success_directory,
            value.terminal_record_path,
            value.runtime_identity,
        )
    )


def _runtime_identity_without_numpy_import() -> dict[str, object]:
    if any(name == "numpy" or name.startswith("numpy.") for name in sys.modules):
        raise RuntimeError("H24 NumPy was imported before the durable claim.")
    return {
        "implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "numpy_version": importlib.metadata.version("numpy"),
        "architecture": platform.machine().lower(),
        "execution_device": "CPU" if os.environ.get("MIDI_FORCE_CPU") == "1" else "UNKNOWN",
        "thread_count": 1
        if all(
            os.environ.get(name) == "1"
            for name in (
                "OMP_NUM_THREADS",
                "OPENBLAS_NUM_THREADS",
                "MKL_NUM_THREADS",
                "NUMEXPR_NUM_THREADS",
            )
        )
        else 0,
        "sample_rate_hz": 44100,
        "hop_samples": 256,
    }


def _seed_for_fixture_id(fixture_id: str) -> int:
    digest = hashlib.sha256(("H24|" + fixture_id).encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "little", signed=False)


def _load_authorization_seal(
    repository: Path,
) -> tuple[H24PopulationMaterializationAuthorizationSeal, str]:
    activation_commit = os.environ.get(H24_AUTHORIZATION_COMMIT_ENV)
    if activation_commit is None:
        raise PermissionError(
            "H24 materializer remains dormant: no reviewed authorization commit is OS-bound."
        )
    activation_commit = _require_lower_hex(
        activation_commit, 40, "authorization activation commit"
    )
    if _git(repository, "status", "--porcelain"):
        raise RuntimeError("H24 materialization requires a clean worktree.")
    if _git(repository, "rev-parse", "HEAD") != activation_commit:
        raise ValueError("H24 checkout HEAD does not match authorization commit.")
    path = _resolve_bound_path(repository, H24_AUTHORIZATION_SEAL_RELATIVE_PATH)
    committed_blob = _git(
        repository,
        "rev-parse",
        f"{activation_commit}:{H24_AUTHORIZATION_SEAL_RELATIVE_PATH.as_posix()}",
    )
    if _git(repository, "hash-object", path.as_posix()) != committed_blob:
        raise ValueError("H24 authorization seal bytes differ from activation commit.")
    raw = path.read_bytes()
    seal = validate_h24_population_materialization_authorization_seal(
        _parse_json_object(raw, "authorization seal"), raw_sha256=_sha256(raw)
    )
    return seal, activation_commit


def _zero_science_preflight(
    repository: Path,
    seal: H24PopulationMaterializationAuthorizationSeal,
    activation_commit: str,
) -> tuple[H24DormantHarnessPlan, tuple[H24DormantFixtureRecipe, ...]]:
    contract_path = _resolve_bound_path(repository, H24_MATERIALIZATION_CONTRACT_RELATIVE_PATH)
    contract_raw = contract_path.read_bytes()
    if _sha256(contract_raw) != H24_MATERIALIZATION_CONTRACT_RAW_SHA256:
        raise ValueError("H24 materialization contract SHA-256 mismatch.")
    contract = _parse_json_object(contract_raw, "materialization contract")
    if contract.get("purpose") != "harmonic_censoring_h24_population_materialization_and_one_shot_contract":
        raise ValueError("H24 materialization contract purpose mismatch.")
    sealed = contract.get("sealed_inputs")
    if type(sealed) is not dict:
        raise ValueError("H24 sealed input contract is invalid.")
    field_to_name = {
        "successor_contract_raw_sha256": "successor_contract",
        "population_manifest_raw_sha256": "population_manifest",
        "test_manifest_raw_sha256": "test_manifest",
        "manifest_binding_raw_sha256": "manifest_binding",
        "dormant_harness_contract_raw_sha256": "dormant_harness_contract",
    }
    for field, name in field_to_name.items():
        binding = sealed.get(name)
        if type(binding) is not dict:
            raise ValueError(f"H24 sealed input {name} is invalid.")
        raw = _resolve_bound_path(repository, str(binding["path"])).read_bytes()
        if _sha256(raw) != _SEALED_HASH_FIELDS[field] or binding.get("raw_sha256") != _SEALED_HASH_FIELDS[field]:
            raise ValueError(f"H24 sealed input {name} bytes changed.")
    if _git(repository, "status", "--porcelain"):
        raise RuntimeError("H24 preflight requires a clean worktree.")
    if _git(repository, "rev-parse", "HEAD") != activation_commit:
        raise ValueError("H24 HEAD changed after seal load.")
    changed = tuple(
        sorted(
            line
            for line in _git(
                repository,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                seal.reviewed_materializer_commit,
            ).splitlines()
            if line
        )
    )
    if changed != seal.exact_changed_files:
        raise ValueError("H24 reviewed implementation changed-file set mismatch.")
    for relative, commit, expected in (
        (H24_HARNESS_SOURCE_RELATIVE_PATH, H24_APPROVED_HARNESS_COMMIT, H24_APPROVED_HARNESS_BLOB),
        (H24_OPERATOR_SOURCE_RELATIVE_PATH, H24_APPROVED_HARNESS_COMMIT, H24_APPROVED_OPERATOR_BLOB),
        (H24_MATERIALIZER_SOURCE_RELATIVE_PATH, seal.reviewed_materializer_commit, seal.materializer_source_blob),
    ):
        reviewed = _git(repository, "rev-parse", f"{commit}:{relative.as_posix()}")
        current = _git(repository, "hash-object", relative.as_posix())
        if reviewed != expected or current != expected:
            raise ValueError(f"H24 reviewed source blob mismatch for {relative}.")
    if _runtime_identity_without_numpy_import() != dict(_RUNTIME_IDENTITY):
        raise RuntimeError("H24 runtime identity mismatch.")
    paths = tuple(_resolve_bound_path(repository, path) for path in _FIXED_PATHS.values())
    if any(path.exists() for path in paths):
        raise FileExistsError("H24 claim, staging, success, or terminal path already exists.")
    plan = load_h24_dormant_harness_plan(repository)
    recipes = translate_all_h24_fixture_specifications(plan)
    if len(recipes) != 175 or tuple(item.fixture_id for item in recipes) != plan.fixture_ids:
        raise ValueError("H24 preflight recipe order mismatch.")
    for recipe in recipes:
        if recipe.synthesis_seed != _seed_for_fixture_id(recipe.fixture_id):
            raise ValueError(f"H24 seed mismatch for {recipe.fixture_id}.")
    return plan, recipes


def _build_capability_authority():
    registered: dict[
        int, tuple[weakref.ReferenceType[object], _CapabilityState]
    ] = {}
    claimed: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...], str]
    ] = {}

    def require(value: object) -> AttestedH24PopulationMaterializationCapability:
        if type(value) is not AttestedH24PopulationMaterializationCapability:
            raise TypeError("H24 materialization requires its exact capability type.")
        entry = registered.get(id(value))
        if (
            entry is None
            or entry[0]() is not value
            or entry[1].binding != _capability_binding(value)
        ):
            raise PermissionError("H24 materialization capability is not factory-attested.")
        return value

    def issue(repository_root: Path) -> AttestedH24PopulationMaterializationCapability:
        repository = Path(repository_root).resolve(strict=True)
        seal, activation_commit = _load_authorization_seal(repository)
        plan, recipes = _zero_science_preflight(repository, seal, activation_commit)
        created = object.__new__(AttestedH24PopulationMaterializationCapability)
        values: dict[str, object] = {
            "population_id": H24_POPULATION_ID,
            "materialization_contract_raw_sha256": H24_MATERIALIZATION_CONTRACT_RAW_SHA256,
            "implementation_commit": seal.reviewed_materializer_commit,
            "materializer_source_blob": seal.materializer_source_blob,
            "harness_source_blob": H24_APPROVED_HARNESS_BLOB,
            "operator_source_blob": H24_APPROVED_OPERATOR_BLOB,
            **dict(_SEALED_HASH_FIELDS),
            "authorization_seal_path": H24_AUTHORIZATION_SEAL_RELATIVE_PATH.as_posix(),
            "authorization_seal_raw_sha256": seal.raw_sha256,
            **dict(_FIXED_PATHS),
            "runtime_identity": MappingProxyType(dict(_RUNTIME_IDENTITY)),
        }
        for name, item in values.items():
            object.__setattr__(created, name, item)
        binding = _capability_binding(created)
        identity = id(created)

        def cleanup(reference: weakref.ReferenceType[object]) -> None:
            current = registered.get(identity)
            if current is not None and current[0] is reference:
                registered.pop(identity, None)
            consumed = claimed.get(identity)
            if consumed is not None and consumed[0] is reference:
                claimed.pop(identity, None)

        reference = weakref.ref(created, cleanup)
        registered[identity] = (
            reference,
            _CapabilityState(repository, activation_commit, plan, recipes, binding),
        )
        return created

    def state(value: object) -> _CapabilityState:
        checked = require(value)
        return registered[id(checked)][1]

    def claim(value: object) -> AttestedH24PopulationMaterializationCapability:
        checked = require(value)
        if id(checked) in claimed and claimed[id(checked)][0]() is checked:
            raise FileExistsError("H24 capability was already claimed in this process.")
        authority = state(checked)
        marker = _resolve_bound_path(authority.repository, checked.claim_marker_path)
        marker.parent.mkdir(parents=True, exist_ok=True)
        _revalidate_claim_authority(checked, authority)
        raw = _canonical_json_line(_claim_marker_payload(checked))
        _write_exclusive_durable_file(marker, raw, create_parent=False)
        claimed[id(checked)] = (
            weakref.ref(checked),
            authority.binding,
            _sha256(raw),
        )
        return checked

    def require_claimed(value: object) -> AttestedH24PopulationMaterializationCapability:
        checked = require(value)
        authority = state(checked)
        entry = claimed.get(id(checked))
        if (
            entry is None
            or entry[0]() is not checked
            or entry[1] != authority.binding
        ):
            raise PermissionError("H24 capability is not durably claimed in this process.")
        marker = _resolve_bound_path(authority.repository, checked.claim_marker_path)
        raw = marker.read_bytes()
        if raw != _canonical_json_line(_claim_marker_payload(checked)) or _sha256(raw) != entry[2]:
            raise PermissionError("H24 claim marker bytes changed after claim.")
        return checked

    return issue, require, state, claim, require_claimed


(
    issue_h24_population_materialization_capability,
    require_attested_h24_population_materialization_capability,
    _capability_state,
    claim_h24_population_materialization_capability,
    require_claimed_h24_population_materialization_capability,
) = _build_capability_authority()


def _claim_marker_payload(
    capability: AttestedH24PopulationMaterializationCapability,
) -> dict[str, object]:
    checked = require_attested_h24_population_materialization_capability(capability)
    fields = (
        "population_id",
        "materialization_contract_raw_sha256",
        "implementation_commit",
        "materializer_source_blob",
        "harness_source_blob",
        "operator_source_blob",
        "successor_contract_raw_sha256",
        "population_manifest_raw_sha256",
        "test_manifest_raw_sha256",
        "manifest_binding_raw_sha256",
        "dormant_harness_contract_raw_sha256",
        "authorization_seal_path",
        "authorization_seal_raw_sha256",
        "claim_marker_path",
        "staging_directory",
        "success_directory",
        "terminal_record_path",
    )
    result = {name: getattr(checked, name) for name in fields}
    result.update(
        {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h24_population_materialization_claim",
            "runtime_identity": dict(checked.runtime_identity),
            "population_consumed": True,
        }
    )
    return result


def _write_exclusive_durable_file(
    path: Path, raw: bytes, *, create_parent: bool = True
) -> None:
    if create_parent:
        path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        view = memoryview(raw)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("H24 durable write made no progress.")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _revalidate_claim_authority(
    capability: AttestedH24PopulationMaterializationCapability,
    state: _CapabilityState,
) -> None:
    repository = state.repository
    if _git(repository, "status", "--porcelain"):
        raise RuntimeError("H24 preclaim requires the issued clean worktree.")
    if _git(repository, "rev-parse", "HEAD") != state.activation_commit:
        raise ValueError("H24 preclaim HEAD changed after capability issuance.")
    exact_files = {
        H24_MATERIALIZATION_CONTRACT_RELATIVE_PATH: capability.materialization_contract_raw_sha256,
        H24_AUTHORIZATION_SEAL_RELATIVE_PATH: capability.authorization_seal_raw_sha256,
    }
    for relative, expected in exact_files.items():
        if _sha256(_resolve_bound_path(repository, relative).read_bytes()) != expected:
            raise ValueError(f"H24 preclaim authority bytes changed for {relative}.")
    for relative, commit, expected in (
        (H24_MATERIALIZER_SOURCE_RELATIVE_PATH, capability.implementation_commit, capability.materializer_source_blob),
        (H24_HARNESS_SOURCE_RELATIVE_PATH, H24_APPROVED_HARNESS_COMMIT, capability.harness_source_blob),
        (H24_OPERATOR_SOURCE_RELATIVE_PATH, H24_APPROVED_HARNESS_COMMIT, capability.operator_source_blob),
    ):
        if (
            _git(repository, "rev-parse", f"{commit}:{relative.as_posix()}") != expected
            or _git(repository, "hash-object", relative.as_posix()) != expected
        ):
            raise ValueError(f"H24 preclaim source bytes changed for {relative}.")
    if _runtime_identity_without_numpy_import() != dict(capability.runtime_identity):
        raise RuntimeError("H24 preclaim runtime identity changed.")
    plan = load_h24_dormant_harness_plan(repository)
    recipes = translate_all_h24_fixture_specifications(plan)
    if tuple(item.fixture_id for item in recipes) != tuple(
        item.fixture_id for item in state.recipes
    ) or any(
        left.synthesis_seed != right.synthesis_seed
        or left.source_specification_sha256 != right.source_specification_sha256
        for left, right in zip(recipes, state.recipes)
    ):
        raise ValueError("H24 preclaim resolved recipes changed.")
    for relative in _FIXED_PATHS.values():
        if _resolve_bound_path(repository, relative).exists():
            raise FileExistsError(f"H24 one-shot path already exists: {relative}")


def _thaw(value: object) -> object:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def _source_envelope(np: Any, source: Mapping[str, object], samples: Any) -> Any:
    kind = str(source["envelope"])
    if kind == "old":
        result = np.zeros(samples.shape, dtype=np.float64)
        valid = samples >= 4096
        age = int(source.get("old_source_age_hops", 0))
        result[valid] = np.exp(-((samples[valid] - 4096) + age * 256) / 8192.0)
        return result
    if kind == "second_distinct":
        result = np.zeros(samples.shape, dtype=np.float64)
        valid = samples >= 12160
        elapsed = samples[valid] - 12160
        result[valid] = np.minimum(1.0, (elapsed + 1.0) / 32.0) * np.exp(
            -elapsed / 1024.0
        )
        return result
    if kind != "new":
        raise ValueError(f"H24 unknown source envelope {kind!r}.")
    onset = int(source.get("onset", 12032))
    attack_hops = int(source.get("attack_hops", 0))
    decay_hops = int(source.get("decay_tau_hops", 8))
    result = np.zeros(samples.shape, dtype=np.float64)
    valid = samples >= onset
    elapsed = samples[valid] - onset
    attack_samples = max(1, attack_hops * 256 + 1)
    decay_samples = decay_hops * 256
    result[valid] = np.minimum(1.0, (elapsed + 1.0) / attack_samples) * np.exp(
        -elapsed / decay_samples
    )
    return result


def _instantaneous_pitch_offset(
    np: Any, technique: Mapping[str, object], samples: Any, onset: int
) -> Any:
    elapsed = np.maximum(samples - onset, 0).astype(np.float64)
    trajectory = technique["trajectory"]
    if trajectory == "sinusoidal_cents":
        return float(technique["depth"]) / 100.0 * np.sin(
            2.0 * np.pi * float(technique["rate_hz"]) * elapsed / 44100.0
        )
    duration = max(1, int(technique["duration_hops"]) * 256)
    fraction = np.minimum(elapsed / duration, 1.0)
    scale = 0.01 if trajectory == "linear_cents" else 1.0
    if trajectory not in {"linear_cents", "linear_semitones"}:
        raise ValueError(f"H24 unknown technique trajectory {trajectory!r}.")
    return (
        float(technique.get("start", 0.0))
        + (float(technique["end"]) - float(technique.get("start", 0.0))) * fraction
    ) * scale


def _render_source(np: Any, source: Mapping[str, object], samples: Any) -> Any:
    allowed = {
        "pitch", "harmonics", "envelope", "gain", "cents", "inharmonicity_B",
        "fundamental_amplitude", "h1_phase", "phase", "old_source_age_hops",
        "onset", "attack_hops", "decay_tau_hops", "technique",
        "instantaneous_pitch_offset",
    }
    if not {"pitch", "harmonics", "envelope"}.issubset(source) or set(source) - allowed:
        raise ValueError("H24 source fields violate the closed source schema.")
    pitch = float(source["pitch"])
    harmonics = tuple(int(value) for value in source["harmonics"])  # type: ignore[arg-type]
    gain = float(source.get("gain", 1.0))
    cents = float(source.get("cents", 0.0))
    inharmonicity = float(source.get("inharmonicity_B", 0.0))
    envelope = _source_envelope(np, source, samples)
    technique = source.get("technique")
    if isinstance(technique, Mapping):
        pitch_offset = _instantaneous_pitch_offset(
            np, technique, samples, int(source.get("onset", 12032))
        )
    else:
        pitch_offset = np.zeros(samples.shape, dtype=np.float64)
    pitch_offset = pitch_offset + float(source.get("instantaneous_pitch_offset", 0.0))
    waveform = np.zeros(samples.shape, dtype=np.float64)
    for harmonic in harmonics:
        amplitude = 0.4 / harmonic
        if harmonic == 1:
            amplitude *= float(source.get("fundamental_amplitude", 1.0))
        frequency = (
            440.0
            * np.power(2.0, (pitch + pitch_offset - 69.0) / 12.0)
            * harmonic
            * math.pow(2.0, cents / 1200.0)
            * math.sqrt(1.0 + inharmonicity * harmonic * harmonic)
        )
        phase = 2.0 * np.pi * np.cumsum(frequency, dtype=np.float64) / 44100.0
        phase -= phase[0]
        phase += (
            float(source.get("phase", 0.0))
            if harmonic >= 2
            else float(source.get("h1_phase", 0.0))
        )
        waveform += gain * amplitude * envelope * np.sin(phase)
    return waveform


def _unit_rms_noise(np: Any, colour: str, seed: int, length: int) -> Any:
    generator = np.random.Generator(np.random.PCG64(seed))
    if colour == "white":
        noise = generator.standard_normal(length).astype(np.float64)
    elif colour == "pink":
        bins = length // 2 + 1
        real = generator.standard_normal(bins)
        imag = generator.standard_normal(bins)
        values = real + 1j * imag
        values *= 1.0 / np.sqrt(np.maximum(np.arange(bins), 1))
        values[0] = values[0].real
        values[-1] = values[-1].real
        noise = np.fft.irfft(values, n=length).astype(np.float64)
    else:
        raise ValueError("H24 noise colour is not sealed.")
    noise -= np.mean(noise)
    rms = float(np.sqrt(np.mean(noise * noise)))
    if not math.isfinite(rms) or rms <= 0.0:
        raise ValueError("H24 noise generator produced invalid RMS.")
    return noise / rms


def _named_values(contract: Mapping[str, object]) -> Mapping[str, object]:
    algorithm = contract["deterministic_waveform_algorithm_v1"]
    if type(algorithm) is not dict or type(algorithm.get("named_values_required")) is not dict:
        raise ValueError("H24 named values contract is invalid.")
    return algorithm["named_values_required"]  # type: ignore[return-value]


def _fixture_sources(
    recipe: H24DormantFixtureRecipe, contract: Mapping[str, object]
) -> list[dict[str, object]]:
    base = _thaw(recipe.base_fixture_parameters)
    parameters = _thaw(recipe.variant_parameters)
    if type(base) is not dict or type(parameters) is not dict:
        raise ValueError("H24 recipe mappings are invalid.")
    sources = [dict(item) for item in base.get("sources", [])]
    axis = recipe.variant_axis
    named = _named_values(contract)
    if axis == "amplitude_gain":
        for source in sources:
            source["gain"] = float(parameters["value"])
    elif axis == "relative_phase_radians":
        for source in sources:
            source["phase"] = float(parameters["value"])
    elif axis == "envelope_attack_decay_hops":
        for source in sources:
            if source.get("envelope") == "new":
                source["attack_hops"] = int(parameters["attack"])
                source["decay_tau_hops"] = int(parameters["decay_tau"])
    elif axis == "cents_inharmonicity":
        for source in sources:
            source["cents"] = float(parameters["cents"])
            source["inharmonicity_B"] = float(parameters["B"])
    elif axis == "neighbour_semitones":
        primary = next(source for source in sources if source.get("envelope") == "new")
        neighbour = dict(primary)
        neighbour["pitch"] = int(primary["pitch"]) + int(parameters["value"])
        sources.append(neighbour)
    elif axis == "interval_semitones":
        source = dict(sources[0])
        source["pitch"] = int(source["pitch"]) + int(parameters["value"])
        source["harmonics"] = [1, 2, 3, 4]
        sources.append(source)
    elif axis == "chord_spec":
        offsets = named["chord_spec"][parameters["value"]]  # type: ignore[index]
        sources = [
            {"pitch": 64 + int(offset), "harmonics": [1, 2, 3, 4], "envelope": "new"}
            for offset in offsets
        ]
    elif axis == "physical_unison":
        definition = named["physical_unison"][parameters["value"]]  # type: ignore[index]
        second = dict(sources[0])
        second["gain"] = float(definition["second_source_gain"])
        second["phase"] = float(definition["second_source_phase"])
        if parameters["value"] == "distinct_envelopes_two_sources":
            second["envelope"] = "second_distinct"
        sources.append(second)
    elif axis == "technique":
        definition = named["technique"][parameters["value"]]  # type: ignore[index]
        for source in sources:
            source["technique"] = dict(definition)
    elif axis == "natural_harmonic":
        definition = named["natural_harmonic"][parameters["value"]]  # type: ignore[index]
        sources[0]["harmonics"] = list(definition["retained_harmonics"])
        sources[0]["fundamental_amplitude"] = float(definition["fundamental_amplitude"])
    elif axis == "sympathetic_resonance":
        gain = named["sympathetic_resonance_gain"][parameters["value"]]  # type: ignore[index]
        sources.append({"pitch": 64, "harmonics": [1], "envelope": "old", "gain": float(gain)})
    elif axis == "old_source_age_hops":
        for source in sources:
            if source.get("envelope") == "old":
                source["old_source_age_hops"] = int(parameters["value"])
    elif axis == "event_sample_offset":
        for source in sources:
            if source.get("envelope") == "new":
                source["onset"] = 8192 + int(parameters["value"])
    elif axis == "pitch_boundary" and parameters["value"] != "analytical_128":
        for source in sources:
            if source.get("envelope") == "new":
                source["pitch"] = int(parameters["value"])
    return sources


def _synthesize_waveform(
    np: Any, recipe: H24DormantFixtureRecipe, contract: Mapping[str, object]
) -> Any:
    """Execute the sealed trace using an already-claimed caller-provided NumPy."""

    samples = np.arange(12544, dtype=np.float64)
    if recipe.base_id == "S5":
        envelope = _source_envelope(np, {"envelope": "old"}, samples)
        frequency = 4.0 * 440.0 * math.pow(2.0, (40.0 - 69.0) / 12.0)
        waveform = 0.1 * envelope * np.sin(
            2.0 * np.pi * frequency * samples / 44100.0
        )
    else:
        waveform = np.zeros(samples.shape, dtype=np.float64)
        for source in _fixture_sources(recipe, contract):
            waveform += _render_source(np, source, samples)
    parameters = _thaw(recipe.variant_parameters)
    if type(parameters) is not dict:
        raise ValueError("H24 variant parameters are invalid.")
    if recipe.variant_axis == "noise":
        noise = _unit_rms_noise(
            np, str(parameters["colour"]), recipe.synthesis_seed, 12544
        )
        clean_rms = float(np.sqrt(np.mean(waveform * waveform)))
        clean_reference = clean_rms if clean_rms > 0.0 else 1.0
        noise_gain = clean_reference / math.pow(10.0, float(parameters["snr_db"]) / 20.0)
        waveform += noise * noise_gain
    elif recipe.variant_axis == "silence":
        waveform.fill(0.0)
    elif recipe.variant_axis == "synthetic_OOD":
        waveform.fill(0.0)
        name = parameters["value"]
        if name == "impulse":
            waveform[12032] = 0.4
        elif name in {"linear_chirp", "log_chirp", "nonharmonic_stack"}:
            local = np.arange(4096, dtype=np.float64)
            if name == "linear_chirp":
                duration = 4095.0 / 44100.0
                phase = 2.0 * np.pi * (
                    80.0 * local / 44100.0
                    + 0.5 * (8000.0 - 80.0) * (local / 44100.0) ** 2 / duration
                )
                waveform[8192:12288] = 0.4 * np.sin(phase)
            elif name == "log_chirp":
                frequency = 80.0 * np.power(100.0, local / 4095.0)
                phase = 2.0 * np.pi * np.cumsum(frequency) / 44100.0
                waveform[8192:12288] = 0.4 * np.sin(phase)
            else:
                for frequency in (233, 377, 611, 997, 1597):
                    waveform[8192:12288] += 0.08 * np.sin(
                        2.0 * np.pi * frequency * local / 44100.0
                    )
        elif name == "pink_noise_burst":
            waveform = _unit_rms_noise(np, "pink", recipe.synthesis_seed, 12544)
            waveform *= 0.4 * _source_envelope(np, {"envelope": "new"}, samples)
        elif name == "inharmonic_bell":
            valid = samples >= 12032
            elapsed = samples[valid] - 12032
            for harmonic in range(1, 9):
                waveform[valid] += (
                    0.3
                    / harmonic
                    * np.exp(-elapsed / (512.0 * harmonic))
                    * np.sin(
                        2.0
                        * np.pi
                        * 220.0
                        * math.pow(harmonic, 1.08)
                        * elapsed
                        / 44100.0
                    )
                )
        else:
            raise ValueError("H24 OOD waveform is not sealed.")
    return _encode_waveform(np, waveform)


def _encode_waveform(np: Any, waveform: Any) -> bytes:
    """Validate and encode without allocating or synthesizing a test waveform."""

    if waveform.dtype != np.float64 or waveform.shape != (12544,):
        raise ValueError("H24 waveform dtype or shape mismatch.")
    if not bool(np.all(np.isfinite(waveform))):
        raise ValueError("H24 waveform contains nonfinite values.")
    raw = waveform.astype("<f8", copy=False).tobytes(order="C")
    if len(raw) != 100352:
        raise ValueError("H24 waveform byte count mismatch.")
    return raw


def _write_new_fsynced(path: Path, raw: bytes) -> None:
    _write_exclusive_durable_file(path, raw, create_parent=False)


def _append_index_line(path: Path, raw: bytes) -> None:
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_APPEND | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        if os.write(descriptor, raw) != len(raw):
            raise OSError("H24 index append was incomplete.")
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _verify_staging(
    staging: Path, index_rows: Sequence[Mapping[str, object]], receipt_raw: bytes
) -> None:
    expected_top = {"fixtures", "population_index.jsonl", "population_receipt.json"}
    if {item.name for item in staging.iterdir()} != expected_top:
        raise ValueError("H24 staging top-level layout mismatch.")
    fixture_dir = staging / "fixtures"
    files = tuple(fixture_dir.iterdir())
    if len(files) != 525:
        raise ValueError("H24 staging fixture file count mismatch.")
    for path in files:
        stat = path.lstat()
        if not path.is_file() or path.is_symlink() or stat.st_nlink != 1:
            raise ValueError("H24 staging contains a linked or special fixture entry.")
    for row in index_rows:
        for path_key, hash_key in (
            ("specification_path", "specification_sha256"),
            ("target_path", "target_sha256"),
            ("waveform_path", "waveform_sha256"),
        ):
            _require_reopened_hash(
                staging / str(row[path_key]), str(row[hash_key]), path_key
            )
    index_raw = (staging / "population_index.jsonl").read_bytes()
    if index_raw != b"".join(_canonical_json_line(row) for row in index_rows):
        raise ValueError("H24 reopened population index bytes mismatch.")
    if (staging / "population_receipt.json").read_bytes() != receipt_raw:
        raise ValueError("H24 reopened receipt bytes mismatch.")


def _require_reopened_hash(path: Path, expected: str, label: str) -> None:
    if _sha256(path.read_bytes()) != expected:
        raise ValueError(f"H24 reopened {label} hash mismatch.")


def _atomic_terminal_write(path: Path, payload: Mapping[str, object]) -> None:
    temporary = path.with_name(path.name + ".materializing")
    try:
        _write_exclusive_durable_file(temporary, _canonical_json_line(payload))
        os.replace(temporary, path)
        _fsync_directory(path.parent)
    except BaseException:
        if path.exists() and not temporary.exists():
            os.replace(path, temporary)
        if temporary.exists():
            temporary.unlink()
        _fsync_directory(path.parent)
        raise


def _materialize_and_publish_h24_population_claimed(
    capability: AttestedH24PopulationMaterializationCapability, np: Any
) -> Mapping[str, object]:
    """Dormant reviewed body; callable only after a future durable claim.

    No code in this commit imports NumPy, calls the capability factory, calls
    the claim, or calls this function.
    """

    checked = require_claimed_h24_population_materialization_capability(capability)
    if getattr(np, "__name__", None) != "numpy" or getattr(np, "__version__", None) != "1.26.4":
        raise RuntimeError("H24 claimed materializer requires exact NumPy 1.26.4.")
    state = _capability_state(checked)
    repository = state.repository
    staging = _resolve_bound_path(repository, checked.staging_directory)
    success = _resolve_bound_path(repository, checked.success_directory)
    terminal = _resolve_bound_path(repository, checked.terminal_record_path)
    marker = _resolve_bound_path(repository, checked.claim_marker_path)
    first_failed: str | None = None
    rows: list[dict[str, object]] = []
    try:
        staging.mkdir(parents=False, exist_ok=False)
        fixture_dir = staging / "fixtures"
        fixture_dir.mkdir(exist_ok=False)
        index_path = staging / "population_index.jsonl"
        contract = _parse_json_object(
            _resolve_bound_path(repository, H24_MATERIALIZATION_CONTRACT_RELATIVE_PATH).read_bytes(),
            "materialization contract",
        )
        specifications = {item.fixture_id: item for item in state.plan.fixtures}
        for ordinal, recipe in enumerate(state.recipes):
            first_failed = recipe.fixture_id
            prefix = f"{ordinal:06d}__{recipe.fixture_id}"
            relative_spec = f"fixtures/{prefix}.spec.json"
            relative_target = f"fixtures/{prefix}.target.json"
            relative_waveform = f"fixtures/{prefix}.f64le"
            spec_raw = specifications[recipe.fixture_id].canonical_specification
            target_raw = _canonical_json_line(_thaw(recipe.expected_target))
            waveform_raw = _synthesize_waveform(np, recipe, contract)
            for relative, raw in (
                (relative_spec, spec_raw),
                (relative_target, target_raw),
                (relative_waveform, waveform_raw),
            ):
                _write_new_fsynced(staging / relative, raw)
            row = {
                "ordinal": ordinal,
                "fixture_id": recipe.fixture_id,
                "synthesis_seed": recipe.synthesis_seed,
                "specification_path": relative_spec,
                "specification_sha256": _sha256((staging / relative_spec).read_bytes()),
                "target_path": relative_target,
                "target_sha256": _sha256((staging / relative_target).read_bytes()),
                "waveform_path": relative_waveform,
                "waveform_sha256": _sha256((staging / relative_waveform).read_bytes()),
                "waveform_byte_count": 100352,
                "sample_count": 12544,
                "sample_rate_hz": 44100,
                "dtype": "<f8",
            }
            if row["specification_sha256"] != recipe.source_specification_sha256:
                raise ValueError("H24 specification SHA-256 changed before indexing.")
            rows.append(row)
            _append_index_line(index_path, _canonical_json_line(row))
        ordered_ids_raw = _canonical_json_line([item.fixture_id for item in state.recipes])
        index_raw = index_path.read_bytes()
        receipt = {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h24_population_materialization_receipt",
            "population_id": H24_POPULATION_ID,
            "population_materialized": True,
            "fixture_count": 175,
            "ordered_fixture_ids_sha256": _sha256(ordered_ids_raw),
            "population_index_sha256": _sha256(index_raw),
            "materialization_contract_raw_sha256": checked.materialization_contract_raw_sha256,
            "successor_contract_raw_sha256": checked.successor_contract_raw_sha256,
            "population_manifest_raw_sha256": checked.population_manifest_raw_sha256,
            "test_manifest_raw_sha256": checked.test_manifest_raw_sha256,
            "manifest_binding_raw_sha256": checked.manifest_binding_raw_sha256,
            "dormant_harness_contract_raw_sha256": checked.dormant_harness_contract_raw_sha256,
            "implementation_commit": checked.implementation_commit,
            "materializer_source_blob": checked.materializer_source_blob,
            "runtime_identity": dict(checked.runtime_identity),
            "real_data_used": False,
            "H17_population_used": False,
            "locked_test_used": False,
            "scientific_tests_executed": 0,
            "training_authorized": False,
        }
        receipt_raw = _canonical_json_line(receipt)
        _write_new_fsynced(staging / "population_receipt.json", receipt_raw)
        _verify_staging(staging, rows, receipt_raw)
        _fsync_directory(staging)
        os.rename(staging, success)
        _fsync_directory(success.parent)
        terminal_payload = {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h24_population_materialization_terminal",
            "status": "H24_SYNTHETIC_V1_POPULATION_MATERIALIZED",
            "population_id": H24_POPULATION_ID,
            "population_consumed": True,
            "claim_marker_sha256": _sha256(marker.read_bytes()),
            "receipt_sha256": _sha256(receipt_raw),
            "population_index_sha256": _sha256(index_raw),
            "materialized_fixture_count": 175,
            "first_failed_fixture_id": None,
            "scientific_tests_executed": 0,
            "locked_test_used": False,
        }
        _atomic_terminal_write(terminal, terminal_payload)
        return MappingProxyType(terminal_payload)
    except BaseException:
        if success.exists() and not terminal.exists() and not staging.exists():
            os.rename(success, staging)
            _fsync_directory(staging.parent)
        if marker.exists() and not terminal.exists():
            failure = {
                "schema_version": 1,
                "purpose": "harmonic_censoring_h24_population_materialization_terminal",
                "status": "H24_POPULATION_MATERIALIZATION_INCONCLUSIVE_CONSUMED",
                "population_id": H24_POPULATION_ID,
                "population_consumed": True,
                "claim_marker_sha256": _sha256(marker.read_bytes()),
                "receipt_sha256": None,
                "population_index_sha256": None,
                "materialized_fixture_count": len(rows),
                "first_failed_fixture_id": first_failed,
                "scientific_tests_executed": 0,
                "locked_test_used": False,
            }
            _atomic_terminal_write(terminal, failure)
        raise


def materialize_and_publish_h24_population(
    capability: AttestedH24PopulationMaterializationCapability,
) -> Mapping[str, object]:
    """Keep the reviewed body dormant until a distinct activation bridge exists."""

    require_claimed_h24_population_materialization_capability(capability)
    raise PermissionError(
        "H24 NumPy import/runtime bridge remains unauthorized in the dormant materializer."
    )


__all__ = [
    "AttestedH24PopulationMaterializationCapability",
    "H24PopulationMaterializationAuthorizationSeal",
    "H24_MATERIALIZATION_CONTRACT_RAW_SHA256",
    "claim_h24_population_materialization_capability",
    "issue_h24_population_materialization_capability",
    "materialize_and_publish_h24_population",
    "require_attested_h24_population_materialization_capability",
    "require_claimed_h24_population_materialization_capability",
    "validate_h24_population_materialization_authorization_seal",
]
