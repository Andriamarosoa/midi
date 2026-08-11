"""Dormant, fail-closed runtime qualification primitives for H26.

This module deliberately separates acquisition of a real process observation
from pure validation and record construction.  No capability can currently be
issued, so the acquisition and publication paths are unreachable until a
separate reviewed change adds an issuer.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Sequence, Tuple


RUNTIME_QUALIFICATION_CONTRACT_COMMIT = (
    "89cc0659de3afb5194afcf8e7ea9ac6c300e1f92"
)
RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA = (
    "c3a021872dfd3a99b6977fdef1302d5edc755fea"
)
_APPROVED_RUNTIME_QUALIFICATION_CONTRACT_COMMIT = (
    "89cc0659de3afb5194afcf8e7ea9ac6c300e1f92"
)
_APPROVED_RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA = (
    "c3a021872dfd3a99b6977fdef1302d5edc755fea"
)
AUTHORITY_CONTRACT_COMMIT = "236a84b4eb928b102bc1548fb2b32d1bffda2e63"
AUTHORITY_CONTRACT_GIT_BLOB_SHA = "dd5bcbff325e74f74e7bde4d425a11ac84aa264d"
REVIEWED_IMPLEMENTATION_COMMIT = "60b8d90bcbb5fb6e3a82d839bae706a359ab310e"
MATERIALIZER_GIT_BLOB_SHA = "2991c69db8a8816d0261c1fb6bb4e339e9408c11"

RECORD_SCHEMA_IDENTITY = "H26_MATERIALIZATION_RUNTIME_QUALIFICATION_RECORD_V1"
RECORD_SCHEMA_VERSION = 1
TARGET_RUNTIME_ROLE = "H26_PRIMARY_MATERIALIZATION_RUNTIME"

STATUS_QUALIFIED = "H26_MATERIALIZATION_RUNTIME_QUALIFIED"
STATUS_DISQUALIFIED = "H26_MATERIALIZATION_RUNTIME_DISQUALIFIED"
STATUS_INCONCLUSIVE = (
    "H26_MATERIALIZATION_RUNTIME_QUALIFICATION_INCONCLUSIVE_CONSUMED"
)

CONTROL_ENVIRONMENT_KEYS: Tuple[str, ...] = (
    "MIDI_FORCE_CPU",
    "OMP_NUM_THREADS",
    "OPENBLAS_NUM_THREADS",
    "MKL_NUM_THREADS",
    "NUMEXPR_NUM_THREADS",
    "VECLIB_MAXIMUM_THREADS",
    "PYTHONHASHSEED",
    "LC_ALL",
    "LANG",
    "TZ",
)

_EXPECTED_ENVIRONMENT_ITEMS: Tuple[Tuple[str, str], ...] = (
    ("MIDI_FORCE_CPU", "1"),
    ("OMP_NUM_THREADS", "1"),
    ("OPENBLAS_NUM_THREADS", "1"),
    ("MKL_NUM_THREADS", "1"),
    ("NUMEXPR_NUM_THREADS", "1"),
    ("VECLIB_MAXIMUM_THREADS", "1"),
    ("PYTHONHASHSEED", "0"),
    ("LC_ALL", "C"),
    ("LANG", "C"),
    ("TZ", "UTC"),
)

_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_SELF_SHA_KEYS = frozenset(
    {"record_sha256", "runtime_record_sha256", "self_sha256"}
)


@dataclass(frozen=True)
class RuntimeIdentity:
    implementation: str
    version: str
    platform_system: str
    platform_release: str
    platform_machine: str
    numpy_version: str
    blas_provider: str

    def as_dict(self) -> dict[str, str]:
        return {
            "implementation": self.implementation,
            "version": self.version,
            "platform_system": self.platform_system,
            "platform_release": self.platform_release,
            "platform_machine": self.platform_machine,
            "numpy_version": self.numpy_version,
            "blas_provider": self.blas_provider,
        }


@dataclass(frozen=True)
class ExpectedRuntime:
    identity: RuntimeIdentity
    numpy_multiarray_size_bytes: int
    numpy_multiarray_sha256: str
    blas_library_size_bytes: int
    blas_library_sha256: str

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = self.identity.as_dict()
        result.update(
            {
                "numpy_multiarray_size_bytes": self.numpy_multiarray_size_bytes,
                "numpy_multiarray_sha256": self.numpy_multiarray_sha256,
                "blas_library_size_bytes": self.blas_library_size_bytes,
                "blas_library_sha256": self.blas_library_sha256,
            }
        )
        return result


@dataclass(frozen=True)
class BinaryProof:
    resolved_path: Optional[str]
    size_bytes: Optional[int]
    sha256: Optional[str]
    acquisition_error: Optional[str] = None


@dataclass(frozen=True)
class BlasDependencyEvidence:
    provider: str
    dependency_path: str
    binary_proof: BinaryProof


EnvironmentItems = Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class RuntimeObservation:
    runtime: Optional[RuntimeIdentity]
    process_environment: Optional[EnvironmentItems]
    executable: Optional[BinaryProof]
    numpy_multiarray: Optional[BinaryProof]
    blas_library: Optional[BinaryProof]


@dataclass(frozen=True)
class RuntimeQualificationContract:
    raw_sha256: str
    expected_runtime: ExpectedRuntime
    process_environment_exact: EnvironmentItems
    qualification_contract_commit: str
    qualification_contract_git_blob_sha: str
    authority_contract_commit: str
    authority_contract_git_blob_sha: str
    reviewed_implementation_commit: str
    materializer_git_blob_sha: str
    target_runtime_role: str


@dataclass(frozen=True, init=False)
class H26RuntimeQualificationRecord:
    _payload: Mapping[str, Any]

    def __new__(cls) -> "H26RuntimeQualificationRecord":
        raise PermissionError("runtime records must be produced by the sealed builder")

    def as_dict(self) -> dict[str, Any]:
        return _thaw(self._payload)


class H26RuntimeQualificationCapability:
    """Unissuable capability for the dormant real-observation boundary."""

    __slots__ = ()

    def __new__(cls) -> "H26RuntimeQualificationCapability":
        raise PermissionError("H26 runtime qualification capability has no issuer")


def _require_capability(value: object) -> None:
    # There is deliberately no registry, issuer, singleton, factory or token.
    # Even object.__new__(H26RuntimeQualificationCapability) is rejected here.
    del value
    raise PermissionError("H26 runtime qualification capability is unavailable")


def environment_items(values: Mapping[str, str]) -> EnvironmentItems:
    """Return a deterministic immutable representation of an observation."""

    items: list[Tuple[str, str]] = []
    for key, value in values.items():
        if not isinstance(key, str) or not isinstance(value, str):
            raise TypeError("environment keys and values must be strings")
        items.append((key, value))
    items.sort()
    return tuple(items)


def _strict_json_loads(raw: bytes) -> Any:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("contract must be UTF-8") from exc

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-finite JSON constant: {value}")

    try:
        return json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_constant=reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("invalid JSON contract") from exc


def _canonical_git_text_bytes(raw: bytes) -> bytes:
    # The reviewed identity is the Git text blob.  A Windows checkout may
    # expose that same text through core.autocrlf as CRLF, so reproduce Git's
    # text normalization while refusing any non-CRLF carriage return.
    if b"\r" in raw:
        if raw.replace(b"\r\n", b"").find(b"\r") != -1:
            raise ValueError("contract contains a non-CRLF carriage return")
        raw = raw.replace(b"\r\n", b"\n")
    return raw


def _git_blob_sha(raw: bytes) -> str:
    raw = _canonical_git_text_bytes(raw)
    header = f"blob {len(raw)}\0".encode("ascii")
    return hashlib.sha1(header + raw).hexdigest()


def _contract_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "harmonic_censoring_h26_materialization_runtime_qualification_contract.json"
    )


def _require_dict(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{name} must be an object")
    return value


def _require_exact(value: Any, expected: Any, name: str) -> None:
    if type(value) is not type(expected) or value != expected:
        raise ValueError(f"{name} does not match the sealed contract")


def _expected_runtime_dict() -> dict[str, Any]:
    return {
        "implementation": "CPython",
        "version": "3.11.9",
        "platform_system": "Darwin",
        "platform_release": "24.5.0",
        "platform_machine": "arm64",
        "numpy_version": "1.26.4",
        "numpy_multiarray_size_bytes": 3164400,
        "numpy_multiarray_sha256": (
            "6a88945aed63a76e3c57076d657d704eef5d0d1e8d6cb1576724b1deb2872e44"
        ),
        "blas_provider": "OpenBLAS ILP64",
        "blas_library_size_bytes": 23198400,
        "blas_library_sha256": (
            "dde2b735d01caa531885115ea853b5a4172b935167b95a1acb2a10243e0d97e7"
        ),
    }


def load_runtime_qualification_contract(
    path: Optional[Path] = None,
) -> RuntimeQualificationContract:
    if (
        RUNTIME_QUALIFICATION_CONTRACT_COMMIT
        != _APPROVED_RUNTIME_QUALIFICATION_CONTRACT_COMMIT
    ):
        raise ValueError("runtime qualification contract commit binding mismatch")
    if (
        RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA
        != _APPROVED_RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA
    ):
        raise ValueError("runtime qualification contract blob binding mismatch")
    resolved = (path or _contract_path()).resolve(strict=True)
    raw = resolved.read_bytes()
    canonical_raw = _canonical_git_text_bytes(raw)
    blob_sha = _git_blob_sha(canonical_raw)
    if blob_sha != RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("runtime qualification contract Git blob mismatch")
    payload = _require_dict(_strict_json_loads(canonical_raw), "contract")

    required_top_level = {
        "schema_version": 1,
        "hypothesis_id": "H26_BOUNDED_EVIDENCE_V1",
        "population_namespace": "H26_SYNTHETIC_V1",
        "test_namespace": "H26_TEST_V1",
        "approved_materialization_authority_contract_commit": (
            AUTHORITY_CONTRACT_COMMIT
        ),
        "authority_contract_git_blob_sha": AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "materializer_git_blob_sha": MATERIALIZER_GIT_BLOB_SHA,
        "target_runtime_role": TARGET_RUNTIME_ROLE,
    }
    for key, expected in required_top_level.items():
        _require_exact(payload.get(key), expected, key)

    expected_runtime_dict = _expected_runtime_dict()
    _require_exact(
        payload.get("expected_primary_runtime"),
        expected_runtime_dict,
        "expected_primary_runtime",
    )
    expected_environment = dict(_EXPECTED_ENVIRONMENT_ITEMS)
    _require_exact(
        payload.get("process_environment_exact"),
        expected_environment,
        "process_environment_exact",
    )

    record_schema = _require_dict(
        payload.get("future_runtime_record_schema"),
        "future_runtime_record_schema",
    )
    constraints = _require_dict(
        record_schema.get("required_constraints"),
        "required_constraints",
    )
    exact_constraints = {
        "record_schema_identity": RECORD_SCHEMA_IDENTITY,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "authority_contract_commit": AUTHORITY_CONTRACT_COMMIT,
        "authority_contract_git_blob_sha": AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        "reviewed_implementation_commit": REVIEWED_IMPLEMENTATION_COMMIT,
        "materializer_git_blob_sha": MATERIALIZER_GIT_BLOB_SHA,
        "target_runtime_role": TARGET_RUNTIME_ROLE,
        "expected_runtime": expected_runtime_dict,
        "process_environment_exact": expected_environment,
    }
    for key, expected in exact_constraints.items():
        _require_exact(constraints.get(key), expected, f"required_constraints.{key}")

    identity = RuntimeIdentity(
        implementation=expected_runtime_dict["implementation"],
        version=expected_runtime_dict["version"],
        platform_system=expected_runtime_dict["platform_system"],
        platform_release=expected_runtime_dict["platform_release"],
        platform_machine=expected_runtime_dict["platform_machine"],
        numpy_version=expected_runtime_dict["numpy_version"],
        blas_provider=expected_runtime_dict["blas_provider"],
    )
    expected_runtime = ExpectedRuntime(
        identity=identity,
        numpy_multiarray_size_bytes=expected_runtime_dict[
            "numpy_multiarray_size_bytes"
        ],
        numpy_multiarray_sha256=expected_runtime_dict[
            "numpy_multiarray_sha256"
        ],
        blas_library_size_bytes=expected_runtime_dict["blas_library_size_bytes"],
        blas_library_sha256=expected_runtime_dict["blas_library_sha256"],
    )
    return RuntimeQualificationContract(
        raw_sha256=hashlib.sha256(canonical_raw).hexdigest(),
        expected_runtime=expected_runtime,
        process_environment_exact=_EXPECTED_ENVIRONMENT_ITEMS,
        qualification_contract_commit=RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
        qualification_contract_git_blob_sha=(
            RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA
        ),
        authority_contract_commit=AUTHORITY_CONTRACT_COMMIT,
        authority_contract_git_blob_sha=AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        reviewed_implementation_commit=REVIEWED_IMPLEMENTATION_COMMIT,
        materializer_git_blob_sha=MATERIALIZER_GIT_BLOB_SHA,
        target_runtime_role=TARGET_RUNTIME_ROLE,
    )


def _valid_runtime_identity(value: Optional[RuntimeIdentity]) -> bool:
    if not isinstance(value, RuntimeIdentity):
        return False
    return all(
        isinstance(field, str) and bool(field) and field == field.strip()
        for field in value.as_dict().values()
    )


def _valid_binary_proof(value: Optional[BinaryProof]) -> bool:
    if not isinstance(value, BinaryProof) or value.acquisition_error is not None:
        return False
    if not isinstance(value.resolved_path, str) or not value.resolved_path.startswith("/"):
        return False
    if type(value.size_bytes) is not int or value.size_bytes <= 0:
        return False
    return isinstance(value.sha256, str) and _SHA256_RE.fullmatch(value.sha256) is not None


def _environment_mapping(
    items: Optional[EnvironmentItems],
) -> Optional[dict[str, str]]:
    if items is None or not isinstance(items, tuple):
        return None
    result: dict[str, str] = {}
    for item in items:
        if (
            not isinstance(item, tuple)
            or len(item) != 2
            or not isinstance(item[0], str)
            or not isinstance(item[1], str)
            or item[0] in result
        ):
            return None
        result[item[0]] = item[1]
    return result


def derive_runtime_terminal_status(
    contract: RuntimeQualificationContract,
    observation: RuntimeObservation,
) -> str:
    """Classify an artificial or future acquired observation, fail-closed."""

    environment = _environment_mapping(observation.process_environment)
    required_proofs_are_valid = (
        _valid_runtime_identity(observation.runtime)
        and environment is not None
        and _valid_binary_proof(observation.executable)
        and _valid_binary_proof(observation.numpy_multiarray)
        and _valid_binary_proof(observation.blas_library)
    )
    if not required_proofs_are_valid:
        return STATUS_INCONCLUSIVE

    assert observation.runtime is not None
    assert observation.numpy_multiarray is not None
    assert observation.blas_library is not None
    assert environment is not None

    mismatch = observation.runtime != contract.expected_runtime.identity
    expected_environment = dict(contract.process_environment_exact)
    mismatch = mismatch or any(
        environment.get(key) != expected_environment[key]
        for key in CONTROL_ENVIRONMENT_KEYS
    )
    mismatch = mismatch or (
        observation.numpy_multiarray.size_bytes
        != contract.expected_runtime.numpy_multiarray_size_bytes
    )
    mismatch = mismatch or (
        observation.numpy_multiarray.sha256
        != contract.expected_runtime.numpy_multiarray_sha256
    )
    mismatch = mismatch or (
        observation.blas_library.size_bytes
        != contract.expected_runtime.blas_library_size_bytes
    )
    mismatch = mismatch or (
        observation.blas_library.sha256
        != contract.expected_runtime.blas_library_sha256
    )
    return STATUS_DISQUALIFIED if mismatch else STATUS_QUALIFIED


def _proof_fields(prefix: str, proof: Optional[BinaryProof]) -> dict[str, Any]:
    if proof is None:
        return {
            f"{prefix}_resolved_path": None,
            f"{prefix}_size_bytes": None,
            f"{prefix}_sha256": None,
        }
    return {
        f"{prefix}_resolved_path": proof.resolved_path,
        f"{prefix}_size_bytes": proof.size_bytes,
        f"{prefix}_sha256": proof.sha256,
    }


def _freeze(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType({key: _freeze(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(_freeze(item) for item in value)
    return value


def _thaw(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {key: _thaw(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return [_thaw(item) for item in value]
    return value


def build_runtime_qualification_record(
    contract: RuntimeQualificationContract,
    observation: RuntimeObservation,
) -> H26RuntimeQualificationRecord:
    terminal_status = derive_runtime_terminal_status(contract, observation)
    environment = _environment_mapping(observation.process_environment)
    observed_environment = None
    if environment is not None:
        observed_environment = {
            key: environment[key]
            for key in CONTROL_ENVIRONMENT_KEYS
            if key in environment
        }
    payload: dict[str, Any] = {
        "record_schema_identity": RECORD_SCHEMA_IDENTITY,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "qualification_contract_commit": contract.qualification_contract_commit,
        "qualification_contract_raw_sha256": contract.raw_sha256,
        "authority_contract_commit": contract.authority_contract_commit,
        "authority_contract_git_blob_sha": contract.authority_contract_git_blob_sha,
        "reviewed_implementation_commit": contract.reviewed_implementation_commit,
        "materializer_git_blob_sha": contract.materializer_git_blob_sha,
        "target_runtime_role": contract.target_runtime_role,
        "expected_runtime": contract.expected_runtime.as_dict(),
        "observed_runtime": (
            observation.runtime.as_dict()
            if _valid_runtime_identity(observation.runtime)
            else None
        ),
        "process_environment_exact": dict(contract.process_environment_exact),
        "observed_process_environment": observed_environment,
        "terminal_status": terminal_status,
    }
    if observation.executable is None:
        payload.update(
            {
                "resolved_executable": None,
                "executable_size_bytes": None,
                "executable_sha256": None,
            }
        )
    else:
        payload.update(
            {
                "resolved_executable": observation.executable.resolved_path,
                "executable_size_bytes": observation.executable.size_bytes,
                "executable_sha256": observation.executable.sha256,
            }
        )
    payload.update(
        _proof_fields("numpy_multiarray", observation.numpy_multiarray)
    )
    payload.update(_proof_fields("blas_library", observation.blas_library))
    record = object.__new__(H26RuntimeQualificationRecord)
    object.__setattr__(record, "_payload", _freeze(payload))
    return record


def _find_forbidden_self_sha(value: Any) -> bool:
    if isinstance(value, Mapping):
        return any(
            key in _SELF_SHA_KEYS or _find_forbidden_self_sha(item)
            for key, item in value.items()
        )
    if isinstance(value, (list, tuple)):
        return any(_find_forbidden_self_sha(item) for item in value)
    return False


_RUNTIME_IDENTITY_FIELDS = (
    "implementation",
    "version",
    "platform_system",
    "platform_release",
    "platform_machine",
    "numpy_version",
    "blas_provider",
)

_RUNTIME_RECORD_FIELDS = frozenset(
    {
        "record_schema_identity",
        "record_schema_version",
        "qualification_contract_commit",
        "qualification_contract_raw_sha256",
        "authority_contract_commit",
        "authority_contract_git_blob_sha",
        "reviewed_implementation_commit",
        "materializer_git_blob_sha",
        "target_runtime_role",
        "expected_runtime",
        "observed_runtime",
        "process_environment_exact",
        "observed_process_environment",
        "resolved_executable",
        "executable_size_bytes",
        "executable_sha256",
        "numpy_multiarray_resolved_path",
        "numpy_multiarray_size_bytes",
        "numpy_multiarray_sha256",
        "blas_library_resolved_path",
        "blas_library_size_bytes",
        "blas_library_sha256",
        "terminal_status",
    }
)


def _proof_from_payload(payload: Mapping[str, Any], prefix: str) -> Optional[BinaryProof]:
    if prefix == "executable":
        path_key = "resolved_executable"
    else:
        path_key = f"{prefix}_resolved_path"
    path = payload[path_key]
    size = payload[f"{prefix}_size_bytes"]
    sha256 = payload[f"{prefix}_sha256"]
    if path is None and size is None and sha256 is None:
        return None
    proof = BinaryProof(resolved_path=path, size_bytes=size, sha256=sha256)
    if not _valid_binary_proof(proof):
        raise ValueError(f"{prefix} proof is not canonical available evidence")
    return proof


def _observation_from_record_payload(payload: Mapping[str, Any]) -> RuntimeObservation:
    observed_runtime = payload["observed_runtime"]
    runtime_identity: Optional[RuntimeIdentity]
    if observed_runtime is None:
        runtime_identity = None
    else:
        if not isinstance(observed_runtime, dict):
            raise ValueError("observed_runtime must be a canonical object or null")
        if tuple(observed_runtime) != _RUNTIME_IDENTITY_FIELDS:
            raise ValueError("observed_runtime fields are not canonical")
        runtime_identity = RuntimeIdentity(
            **{field: observed_runtime[field] for field in _RUNTIME_IDENTITY_FIELDS}
        )

    observed_environment = payload["observed_process_environment"]
    environment: Optional[EnvironmentItems]
    if observed_environment is None:
        environment = None
    else:
        if not isinstance(observed_environment, dict):
            raise ValueError("observed_process_environment must be an object or null")
        if not set(observed_environment).issubset(CONTROL_ENVIRONMENT_KEYS):
            raise ValueError("observed_process_environment contains an unlisted key")
        try:
            environment = environment_items(observed_environment)
        except (TypeError, ValueError) as exc:
            raise ValueError("observed_process_environment is malformed") from exc

    return RuntimeObservation(
        runtime=runtime_identity,
        process_environment=environment,
        executable=_proof_from_payload(payload, "executable"),
        numpy_multiarray=_proof_from_payload(payload, "numpy_multiarray"),
        blas_library=_proof_from_payload(payload, "blas_library"),
    )


def _validate_runtime_record_payload(payload: Mapping[str, Any]) -> None:
    if _find_forbidden_self_sha(payload):
        raise ValueError("runtime record must not contain its own SHA256")
    if set(payload) != _RUNTIME_RECORD_FIELDS:
        raise ValueError("runtime record fields are not the exact canonical schema")

    contract = load_runtime_qualification_contract()
    exact_bindings = {
        "record_schema_identity": RECORD_SCHEMA_IDENTITY,
        "record_schema_version": RECORD_SCHEMA_VERSION,
        "qualification_contract_commit": contract.qualification_contract_commit,
        "qualification_contract_raw_sha256": contract.raw_sha256,
        "authority_contract_commit": contract.authority_contract_commit,
        "authority_contract_git_blob_sha": contract.authority_contract_git_blob_sha,
        "reviewed_implementation_commit": contract.reviewed_implementation_commit,
        "materializer_git_blob_sha": contract.materializer_git_blob_sha,
        "target_runtime_role": contract.target_runtime_role,
        "expected_runtime": contract.expected_runtime.as_dict(),
        "process_environment_exact": dict(contract.process_environment_exact),
    }
    for key, expected in exact_bindings.items():
        if type(payload[key]) is not type(expected) or payload[key] != expected:
            raise ValueError(f"runtime record binding mismatch: {key}")

    try:
        observation = _observation_from_record_payload(payload)
        derived_status = derive_runtime_terminal_status(contract, observation)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("runtime record observation is malformed") from exc
    if payload["terminal_status"] != derived_status:
        raise ValueError("runtime record terminal_status is not the derived status")


def serialize_runtime_qualification_record(
    record: H26RuntimeQualificationRecord,
) -> bytes:
    if type(record) is not H26RuntimeQualificationRecord:
        raise TypeError("record must be built by build_runtime_qualification_record")
    payload = record.as_dict()
    _validate_runtime_record_payload(payload)
    try:
        text = json.dumps(
            payload,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("runtime record is not finite canonical JSON") from exc
    return (text + "\n").encode("utf-8")


def write_runtime_qualification_record_atomic(
    capability: H26RuntimeQualificationCapability,
    record: H26RuntimeQualificationRecord,
    destination: Path,
) -> None:
    _require_capability(capability)
    data = serialize_runtime_qualification_record(record)
    destination = Path(destination)
    staging = destination.with_name(destination.name + ".part")
    if destination.exists() or staging.exists():
        raise FileExistsError("runtime record destination or staging already exists")
    if not destination.parent.is_dir():
        raise FileNotFoundError("runtime record parent directory must already exist")
    with staging.open("xb") as handle:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(staging, destination)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _binary_proof(path: Path) -> BinaryProof:
    resolved = path.resolve(strict=True)
    stat = resolved.stat()
    return BinaryProof(
        resolved_path=str(resolved),
        size_bytes=stat.st_size,
        sha256=_sha256_file(resolved),
    )


def parse_otool_dependency_paths(output: str) -> Tuple[str, ...]:
    """Parse dependency identifiers from artificial or future ``otool -L`` text."""

    if not isinstance(output, str):
        raise TypeError("otool output must be text")
    lines = output.splitlines()
    if not lines or not lines[0].strip().endswith(":"):
        raise ValueError("otool output has no binary header")
    dependencies: list[str] = []
    for line in lines[1:]:
        stripped = line.strip()
        if not stripped:
            continue
        dependency = stripped.split(" (", 1)[0].strip()
        if not dependency:
            raise ValueError("otool output contains an empty dependency")
        dependencies.append(dependency)
    return tuple(dependencies)


def _provider_from_linked_dependency(dependency: str) -> Optional[str]:
    lower = dependency.lower()
    if "openblas" in lower:
        if "ilp64" in lower or "openblas64" in lower or "openblas_64" in lower:
            return "OpenBLAS ILP64"
        return "OpenBLAS LP64"
    if "accelerate.framework" in lower:
        return "Apple Accelerate"
    if "mkl" in lower and ("blas" in lower or "mkl_rt" in lower):
        return "Intel MKL"
    name = lower.rsplit("/", 1)[-1]
    if name.startswith("libblas") or name.startswith("blas"):
        return "Generic BLAS"
    return None


def _resolve_linked_dependency(multiarray_path: Path, dependency: str) -> Path:
    if dependency.startswith("@loader_path/"):
        suffix = dependency[len("@loader_path/") :]
        return (multiarray_path.resolve(strict=True).parent / suffix).resolve(strict=True)
    path = Path(dependency)
    if path.is_absolute():
        return path.resolve(strict=True)
    raise RuntimeError("BLAS dependency path is not unambiguously resolvable")


def derive_blas_dependency_evidence(
    multiarray_path: Path,
    dependency_paths: Sequence[str],
) -> BlasDependencyEvidence:
    """Derive provider and binary proof only from one linked BLAS dependency."""

    candidates: list[Tuple[str, str]] = []
    for dependency in dependency_paths:
        if not isinstance(dependency, str) or not dependency:
            raise ValueError("dependency identifiers must be non-empty strings")
        provider = _provider_from_linked_dependency(dependency)
        if provider is not None:
            candidates.append((dependency, provider))
    if len(candidates) != 1:
        raise RuntimeError("exactly one linked BLAS dependency must be observable")
    dependency, provider = candidates[0]
    resolved = _resolve_linked_dependency(Path(multiarray_path), dependency)
    proof = _binary_proof(resolved)
    return BlasDependencyEvidence(
        provider=provider,
        dependency_path=dependency,
        binary_proof=proof,
    )


def _observe_linked_blas_dependency(
    multiarray_path: Path,
) -> BlasDependencyEvidence:
    command = ("/usr/bin/otool", "-L", str(multiarray_path.resolve(strict=True)))
    completed = subprocess.run(
        command,
        check=True,
        capture_output=True,
        text=True,
        env={"LC_ALL": "C", "LANG": "C", "PATH": "/usr/bin:/bin"},
    )
    dependencies = parse_otool_dependency_paths(completed.stdout)
    return derive_blas_dependency_evidence(multiarray_path, dependencies)


def observe_primary_runtime(
    capability: H26RuntimeQualificationCapability,
) -> RuntimeObservation:
    """Dormant real observer. No capability can reach this body today."""

    _require_capability(capability)
    numpy_module = importlib.import_module("numpy")
    multiarray_module = importlib.import_module("numpy.core._multiarray_umath")
    multiarray_file = Path(str(multiarray_module.__file__))
    environment = environment_items(dict(os.environ))
    executable_proof = _binary_proof(Path(sys.executable))
    multiarray_proof = _binary_proof(multiarray_file)
    try:
        blas_evidence = _observe_linked_blas_dependency(multiarray_file)
    except Exception as exc:
        return RuntimeObservation(
            runtime=None,
            process_environment=environment,
            executable=executable_proof,
            numpy_multiarray=multiarray_proof,
            blas_library=BinaryProof(
                resolved_path=None,
                size_bytes=None,
                sha256=None,
                acquisition_error=f"BLAS dependency evidence unavailable: {exc}",
            ),
        )
    identity = RuntimeIdentity(
        implementation=platform.python_implementation(),
        version=platform.python_version(),
        platform_system=platform.system(),
        platform_release=platform.release(),
        platform_machine=platform.machine(),
        numpy_version=str(numpy_module.__version__),
        blas_provider=blas_evidence.provider,
    )
    return RuntimeObservation(
        runtime=identity,
        process_environment=environment,
        executable=executable_proof,
        numpy_multiarray=multiarray_proof,
        blas_library=blas_evidence.binary_proof,
    )


__all__ = [
    "AUTHORITY_CONTRACT_COMMIT",
    "AUTHORITY_CONTRACT_GIT_BLOB_SHA",
    "BinaryProof",
    "BlasDependencyEvidence",
    "CONTROL_ENVIRONMENT_KEYS",
    "H26RuntimeQualificationCapability",
    "H26RuntimeQualificationRecord",
    "MATERIALIZER_GIT_BLOB_SHA",
    "REVIEWED_IMPLEMENTATION_COMMIT",
    "RUNTIME_QUALIFICATION_CONTRACT_COMMIT",
    "RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA",
    "RuntimeIdentity",
    "RuntimeObservation",
    "RuntimeQualificationContract",
    "STATUS_DISQUALIFIED",
    "STATUS_INCONCLUSIVE",
    "STATUS_QUALIFIED",
    "build_runtime_qualification_record",
    "derive_runtime_terminal_status",
    "derive_blas_dependency_evidence",
    "environment_items",
    "load_runtime_qualification_contract",
    "observe_primary_runtime",
    "parse_otool_dependency_paths",
    "serialize_runtime_qualification_record",
    "write_runtime_qualification_record_atomic",
]
