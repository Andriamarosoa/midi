"""Dormant process-local authority for one-shot H25 scientific execution.

The reviewed scientific seal, activation and OS binding intentionally do not
exist in this commit.  The issuer therefore fails before population access or
NumPy import.  The types and state transitions are nevertheless complete and
testable with TEST-ONLY paths.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
from types import MappingProxyType
from typing import Mapping, Sequence
import weakref


CAPABILITY_CONTRACT = Path(
    "configs/harmonic_censoring_h25_scientific_execution_capability_contract.json"
)
AUTHORIZATION_SEAL = Path(
    "configs/harmonic_censoring_h25_scientific_execution_authorization_seal.json"
)
ACTIVATION_RECORD = Path(
    "configs/harmonic_censoring_h25_scientific_execution_activation.json"
)
AUTHORIZATION_COMMIT_ENV = "H25_SCIENTIFIC_EXECUTION_AUTHORIZATION_COMMIT"
AUTHORIZATION_SEAL_SHA256_ENV = "H25_SCIENTIFIC_EXECUTION_AUTHORIZATION_SEAL_SHA256"
REVIEWED_SCIENTIFIC_COMMIT = "de73a8f99e206e0677e48ef38427287f24f7f5d5"
REVIEWED_ENGINE_BLOB = "171602b54a8023e2c85c128aca14ec053da176ad"
REVIEWED_RECOMPUTER_BLOB = "9b1c878b6e99b07c3aeff1cd2e80a3c5bf21ff0f"
REVIEWED_RUNNER_BLOB = "09777f18f198ca94e6b1155652fc5c1b460977dd"
ADMINISTRATIVE_QUALIFICATION_SHA256 = (
    "54bd361a99223dd24d6e4f0883ace47572965604c406efe69e5564f675d14ee1"
)

_ATTESTED: dict[int, weakref.ReferenceType["AttestedH25ScientificCapability"]] = {}
_CLAIMED: dict[int, weakref.ReferenceType["AttestedH25ScientificCapability"]] = {}
_ISSUE_LOCK = threading.Lock()
_ISSUED = False
_WRAPPER_TOKEN = object()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
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


def _reject_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    value: dict[str, object] = {}
    for key, item in pairs:
        if key in value:
            raise ValueError(f"H25 authority JSON duplicates key {key!r}.")
        value[key] = item
    return value


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H25 authority JSON forbids {token!r}.")


def _parse(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H25 {label} must be UTF-8 LF without BOM.")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict or _canonical(value) != raw:
        raise ValueError(f"H25 {label} must be canonical JSON with one LF.")
    return value


def _object(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H25 {label} must be UTF-8 LF without BOM.")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise ValueError(f"H25 {label} must be a JSON object.")
    return value


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=root, text=True, encoding="utf-8"
    ).strip()


def _write_new_durable(path: Path, raw: bytes) -> None:
    if not path.parent.is_dir() or path.parent.is_symlink():
        raise FileNotFoundError("H25 durable claim parent must already exist and be non-symlinked.")
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("H25 durable write made no progress.")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if os.name != "nt":
        parent = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)


@dataclass(frozen=True, init=False)
class AttestedH25ScientificCapability:
    repository_root: Path
    authorization_commit: str
    activation_sha256: str
    seal_sha256: str
    capability_contract_sha256: str
    authority_source_blob: str
    runner_source_blob: str
    engine_source_blob: str
    recomputer_source_blob: str
    population_directory: Path
    population_index_sha256: str
    population_provenance_sha256: str
    population_receipt_sha256: str
    administrative_qualification_sha256: str
    ordered_fixture_ids: tuple[str, ...]
    ordered_test_ids: tuple[str, ...]
    ordered_test_phases: tuple[str, ...]
    claim_path: Path
    staging_directory: Path
    success_directory: Path
    terminal_path: Path
    forensic_terminal_path: Path
    secondary_runtime_command: tuple[str, ...]
    secondary_runtime_timeout_seconds: int
    secondary_runtime_identity: Mapping[str, object]

    def __new__(cls) -> "AttestedH25ScientificCapability":
        raise TypeError("AttestedH25ScientificCapability has no public constructor.")

    def __copy__(self):
        raise TypeError("H25 scientific capability cannot be copied.")

    def __deepcopy__(self, memo):
        raise TypeError("H25 scientific capability cannot be deep-copied.")

    def __reduce_ex__(self, protocol):
        raise TypeError("H25 scientific capability cannot be serialized.")


def _register(
    value: AttestedH25ScientificCapability,
) -> AttestedH25ScientificCapability:
    identity = id(value)

    def cleanup(reference: weakref.ReferenceType[AttestedH25ScientificCapability]) -> None:
        if _ATTESTED.get(identity) is reference:
            _ATTESTED.pop(identity, None)
        if _CLAIMED.get(identity) is reference:
            _CLAIMED.pop(identity, None)

    _ATTESTED[identity] = weakref.ref(value, cleanup)
    return value


def _new_capability(**values: object) -> AttestedH25ScientificCapability:
    expected = {item.name for item in fields(AttestedH25ScientificCapability)}
    if set(values) != expected:
        raise ValueError("H25 internal capability field set mismatch.")
    capability = object.__new__(AttestedH25ScientificCapability)
    for name, value in values.items():
        object.__setattr__(capability, name, value)
    return _register(capability)


def require_attested_h25_scientific_capability(
    value: object,
) -> AttestedH25ScientificCapability:
    if type(value) is not AttestedH25ScientificCapability:
        raise TypeError("H25 scientific execution requires the exact capability type.")
    reference = _ATTESTED.get(id(value))
    if reference is None or reference() is not value:
        raise PermissionError("H25 scientific capability is not process-local attested.")
    return value


def require_claimed_h25_scientific_capability(
    value: object,
) -> AttestedH25ScientificCapability:
    checked = require_attested_h25_scientific_capability(value)
    reference = _CLAIMED.get(id(checked))
    if reference is None or reference() is not checked:
        raise PermissionError("H25 scientific capability has not crossed its durable claim.")
    if not checked.claim_path.is_file():
        raise PermissionError("H25 scientific claim disappeared after consumption.")
    return checked


def _validate_dormant_contract(root: Path) -> Mapping[str, object]:
    raw = (root / CAPABILITY_CONTRACT).read_bytes()
    contract = _object(raw, "scientific capability contract")
    reviewed = contract.get("reviewed_scientific_base")
    if type(reviewed) is not dict or reviewed.get("commit") != REVIEWED_SCIENTIFIC_COMMIT:
        raise ValueError("H25 reviewed scientific commit mismatch.")
    expected = {
        "engine": REVIEWED_ENGINE_BLOB,
        "recomputer": REVIEWED_RECOMPUTER_BLOB,
        "runner": REVIEWED_RUNNER_BLOB,
    }
    for name, blob in expected.items():
        binding = reviewed.get(name)
        if type(binding) is not dict or binding.get("git_blob") != blob:
            raise ValueError(f"H25 reviewed {name} blob mismatch.")
        if _git(root, "rev-parse", f"{REVIEWED_SCIENTIFIC_COMMIT}:{binding['path']}") != blob:
            raise ValueError(f"H25 reviewed {name} historical blob changed.")
    _git(root, "merge-base", "--is-ancestor", REVIEWED_SCIENTIFIC_COMMIT, "HEAD")
    for name, binding in contract["sealed_git_inputs"].items():
        path = root / binding["path"]
        if _sha256(path.read_bytes()) != binding["raw_sha256"]:
            raise ValueError(f"H25 sealed input SHA mismatch for {name}.")
        if _git(root, "rev-parse", f"HEAD:{binding['path']}") != binding["git_blob"]:
            raise ValueError(f"H25 sealed input Git blob mismatch for {name}.")
    return contract


def _validate_future_transition(root: Path) -> tuple[Mapping[str, object], Mapping[str, object], str]:
    seal_path = root / AUTHORIZATION_SEAL
    activation_path = root / ACTIVATION_RECORD
    if not seal_path.is_file() or not activation_path.is_file():
        raise PermissionError(
            "H25 scientific issuer remains dormant: reviewed seal and activation are absent."
        )
    seal_raw = seal_path.read_bytes()
    external_sha = os.environ.get(AUTHORIZATION_SEAL_SHA256_ENV)
    if external_sha is None or _sha256(seal_raw) != external_sha:
        raise PermissionError("H25 scientific seal external SHA binding mismatch before parsing.")
    seal = _object(seal_raw, "scientific authorization seal")
    activation_raw = activation_path.read_bytes()
    activation = _object(activation_raw, "scientific activation")
    seal_fields = {
        "schema_version", "purpose", "status", "authorized_action",
        "reviewed_authority_commit", "authority_source_blob", "runner_source_blob",
        "engine_source_blob", "recomputer_source_blob", "capability_contract_sha256",
        "population_index_sha256", "population_provenance_sha256",
        "population_receipt_sha256", "administrative_qualification_record_path",
        "administrative_qualification_sha256", "secondary_runtime_command",
        "secondary_runtime_timeout_seconds", "secondary_runtime_identity",
    }
    activation_fields = {
        "schema_version", "purpose", "status", "seal_path",
        "seal_raw_sha256", "external_review",
    }
    if set(seal) != seal_fields or type(seal.get("schema_version")) is not int or seal["schema_version"] != 1:
        raise ValueError("H25 scientific seal field set mismatch.")
    if set(activation) != activation_fields or type(activation.get("schema_version")) is not int or activation["schema_version"] != 1:
        raise ValueError("H25 scientific activation field set mismatch.")
    head = _git(root, "rev-parse", "HEAD")
    if os.environ.get(AUTHORIZATION_COMMIT_ENV) != head:
        raise PermissionError("H25 scientific activation HEAD/OS binding mismatch.")
    if _git(root, "status", "--porcelain"):
        raise RuntimeError("H25 scientific issuance requires a clean worktree.")
    if seal.get("status") != "reviewed_H25_scientific_execution_authorized_once":
        raise PermissionError("H25 scientific seal is not active.")
    if seal.get("purpose") != "harmonic_censoring_h25_scientific_execution_authorization_seal" or seal.get("authorized_action") != "AUTHORIZED_TO_EXECUTE_H25_SYNTHETIC_V1_ONCE":
        raise PermissionError("H25 scientific seal purpose/action mismatch.")
    if activation.get("status") != "externally_reviewed_H25_scientific_activation":
        raise PermissionError("H25 scientific activation is not active.")
    if activation.get("purpose") != "harmonic_censoring_h25_scientific_execution_activation" or activation.get("seal_path") != AUTHORIZATION_SEAL.as_posix():
        raise PermissionError("H25 scientific activation purpose/path mismatch.")
    if activation.get("external_review") != {"verdict": "APPROVED", "activation_commit_review_required": True}:
        raise PermissionError("H25 scientific activation review mismatch.")
    if activation.get("seal_raw_sha256") != _sha256(seal_raw):
        raise ValueError("H25 activation does not bind the exact seal bytes.")
    return seal, activation, head


def _require_hex(value: object, length: int, label: str) -> str:
    if type(value) is not str or len(value) != length or any(ch not in "0123456789abcdef" for ch in value):
        raise ValueError(f"H25 {label} must be lowercase hex length {length}.")
    return value


def _require_relative(value: object, label: str) -> Path:
    if type(value) is not str or not value:
        raise ValueError(f"H25 {label} must be a relative path.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"H25 {label} escapes repository.")
    return path


def _validate_secondary_runtime_identity(
    root: Path, command: Sequence[str], raw_identity: object
) -> Mapping[str, object]:
    if type(raw_identity) is not dict:
        raise ValueError("H25 secondary runtime identity must be an object.")
    if set(raw_identity) != {"scientific_runtime", "transport"}:
        raise ValueError("H25 secondary runtime identity field set mismatch.")
    scientific = raw_identity["scientific_runtime"]
    transport = raw_identity["transport"]
    if type(scientific) is not dict or type(transport) is not dict:
        raise ValueError("H25 secondary runtime identity components must be objects.")
    scientific_fields = {
        "implementation", "version", "platform_system", "platform_release",
        "platform_machine", "resolved_executable", "executable_size_bytes",
        "executable_sha256", "numpy_version", "numpy_multiarray_path",
        "numpy_multiarray_size_bytes", "numpy_multiarray_sha256", "blas_provider",
        "blas_library_path", "blas_library_size_bytes", "blas_library_sha256",
        "process_environment_exact",
    }
    transport_fields = {
        "command_sha256", "observer_payload_path",
        "observer_payload_size_bytes", "observer_payload_sha256",
    }
    if set(scientific) != scientific_fields or set(transport) != transport_fields:
        raise ValueError("H25 secondary scientific/transport identity field set mismatch.")
    for field in (
        "implementation", "version", "platform_system", "platform_release",
        "platform_machine", "resolved_executable", "numpy_version",
        "numpy_multiarray_path", "blas_provider", "blas_library_path",
    ):
        if type(scientific[field]) is not str or not scientific[field]:
            raise ValueError(f"H25 secondary runtime identity {field} is invalid.")
    if type(transport["observer_payload_path"]) is not str or not transport["observer_payload_path"]:
        raise ValueError("H25 secondary observer payload path is invalid.")
    size = scientific["executable_size_bytes"]
    if type(size) is not int or type(size) is bool or size <= 0:
        raise ValueError("H25 secondary executable size is invalid.")
    executable_sha = _require_hex(
        scientific["executable_sha256"], 64, "secondary executable SHA"
    )
    command_sha = _require_hex(
        transport["command_sha256"], 64, "secondary command SHA"
    )
    executable_argument = Path(command[0])
    if not executable_argument.is_absolute():
        raise ValueError("H25 secondary runtime executable must be absolute.")
    executable = executable_argument.resolve(strict=True)
    if str(executable) != scientific["resolved_executable"]:
        raise ValueError("H25 secondary runtime executable path mismatch.")
    if executable.stat().st_size != size or _sha256(executable.read_bytes()) != executable_sha:
        raise ValueError("H25 secondary runtime executable byte identity mismatch.")
    if _sha256(_canonical(list(command))) != command_sha:
        raise ValueError("H25 secondary runtime command identity mismatch.")
    for prefix in ("numpy_multiarray", "blas_library"):
        binary_size = scientific[f"{prefix}_size_bytes"]
        if type(binary_size) is not int or type(binary_size) is bool or binary_size <= 0:
            raise ValueError(f"H25 secondary {prefix} size is invalid.")
        binary_sha = _require_hex(
            scientific[f"{prefix}_sha256"], 64, f"secondary {prefix} SHA"
        )
        binary = Path(scientific[f"{prefix}_path"])
        if not binary.is_absolute():
            raise ValueError(f"H25 secondary {prefix} path must be absolute.")
        binary = binary.resolve(strict=True)
        if binary.stat().st_size != binary_size or _sha256(binary.read_bytes()) != binary_sha:
            raise ValueError(f"H25 secondary {prefix} byte identity mismatch.")
    capability_contract = _object(
        (root / CAPABILITY_CONTRACT).read_bytes(), "scientific capability contract"
    )
    runtime_contract = _object(
        (root / capability_contract["reference_runtime"]["contract_path"]).read_bytes(),
        "reference runtime contract",
    )
    expected_environment = runtime_contract["reference_runtime_identity"][
        "process_environment_exact"
    ]
    if scientific["process_environment_exact"] != expected_environment:
        raise ValueError("H25 secondary process environment contract mismatch.")
    payload_size = transport["observer_payload_size_bytes"]
    if type(payload_size) is not int or type(payload_size) is bool or payload_size <= 0:
        raise ValueError("H25 secondary observer payload size is invalid.")
    payload_sha = _require_hex(
        transport["observer_payload_sha256"], 64,
        "secondary observer payload SHA",
    )
    payload = Path(transport["observer_payload_path"])
    if not payload.is_absolute():
        raise ValueError("H25 secondary observer payload path must be absolute.")
    payload = payload.resolve(strict=True)
    if str(payload) not in command:
        raise ValueError("H25 secondary observer payload is not bound by the command.")
    if payload.stat().st_size != payload_size or _sha256(payload.read_bytes()) != payload_sha:
        raise ValueError("H25 secondary observer payload byte identity mismatch.")
    return MappingProxyType({
        "scientific_runtime": MappingProxyType(dict(scientific)),
        "transport": MappingProxyType(dict(transport)),
    })


def _require_secondary_runtime_before_numpy(
    raw_identity: Mapping[str, object],
) -> None:
    scientific = raw_identity["scientific_runtime"]
    if (
        platform.python_implementation() != scientific["implementation"]
        or platform.python_version() != scientific["version"]
        or platform.system() != scientific["platform_system"]
        or platform.release() != scientific["platform_release"]
        or platform.machine() != scientific["platform_machine"]
        or str(Path(sys.executable).resolve(strict=True))
        != scientific["resolved_executable"]
    ):
        raise PermissionError("H25 secondary scientific runtime mismatch before NumPy.")
    for name, expected in scientific["process_environment_exact"].items():
        if os.environ.get(name) != expected:
            raise PermissionError(f"H25 secondary environment mismatch for {name}.")


def _require_runtime_before_numpy(root: Path, contract: Mapping[str, object]) -> None:
    runtime_path = root / contract["reference_runtime"]["contract_path"]
    runtime = _object(runtime_path.read_bytes(), "runtime contract")["reference_runtime_identity"]
    expected_platform = runtime["platform"]
    expected_python = runtime["python"]
    if (
        platform.system() != expected_platform["os_system"]
        or platform.release() != expected_platform["os_release"]
        or platform.machine() != expected_platform["machine"]
        or platform.python_implementation() != expected_python["implementation"]
        or platform.python_version() != expected_python["version"]
        or str(Path(sys.executable).resolve(strict=True)) != expected_python["resolved_executable"]
    ):
        raise PermissionError("H25 scientific runtime identity mismatch before NumPy.")
    for name, expected in runtime["process_environment_exact"].items():
        if os.environ.get(name) != expected:
            raise PermissionError(f"H25 scientific environment mismatch for {name}.")
    numpy_binary = Path(runtime["numpy"]["multiarray_extension_path"]).resolve(strict=True)
    if numpy_binary.stat().st_size != runtime["numpy"]["multiarray_extension_size_bytes"] or _sha256(numpy_binary.read_bytes()) != runtime["numpy"]["multiarray_extension_sha256"]:
        raise PermissionError("H25 scientific NumPy binary identity mismatch.")
    blas = Path(runtime["linear_algebra_backend"]["loaded_library_path"]).resolve(strict=True)
    if blas.stat().st_size != runtime["linear_algebra_backend"]["loaded_library_size_bytes"] or _sha256(blas.read_bytes()) != runtime["linear_algebra_backend"]["loaded_library_sha256"]:
        raise PermissionError("H25 scientific BLAS identity mismatch.")


def _load_ordered_population_ids(
    population_directory: Path, index_path: Path
) -> tuple[str, ...]:
    raw = index_path.read_bytes()
    lines = raw.splitlines(keepends=True)
    if len(lines) != 36 or b"".join(lines) != raw:
        raise ValueError("H25 population index must contain exactly 36 lines.")
    identifiers: list[str] = []
    for ordinal, line in enumerate(lines):
        record = _parse(line, f"population index line {ordinal}")
        if record.get("ordinal") != ordinal or type(record.get("fixture_id")) is not str:
            raise ValueError("H25 population index identity/order mismatch.")
        identifiers.append(record["fixture_id"])
        for stem in ("waveform", "fixture_record", "target_record"):
            relative = record.get(f"{stem}_path")
            size = record.get(f"{stem}_size_bytes")
            digest = record.get(f"{stem}_sha256")
            if type(relative) is not str or type(size) is not int or type(size) is bool:
                raise ValueError("H25 population index artifact binding schema mismatch.")
            _require_hex(digest, 64, f"{stem} SHA")
            candidate = population_directory / relative
            if candidate.is_symlink():
                raise ValueError(f"H25 population artifact symlink is forbidden for {stem}.")
            path = candidate.resolve(strict=True)
            path.relative_to(population_directory.resolve(strict=True))
            if path.stat().st_size != size or _sha256(path.read_bytes()) != digest:
                raise ValueError(f"H25 population artifact binding mismatch for {stem}.")
    if len(set(identifiers)) != 36:
        raise ValueError("H25 population index fixture IDs are not unique.")
    return tuple(identifiers)


class IssuedH25ScientificAuthority:
    __slots__ = ("__capability", "__state", "__lock")

    def __init__(
        self, capability: AttestedH25ScientificCapability, *, _token: object = None
    ) -> None:
        if _token is not _WRAPPER_TOKEN:
            raise PermissionError("H25 scientific authority is factory-only.")
        self.__capability = require_attested_h25_scientific_capability(capability)
        self.__state = "ISSUED"
        self.__lock = threading.Lock()

    @property
    def state(self) -> str:
        return self.__state

    def __copy__(self):
        raise TypeError("H25 scientific authority cannot be copied.")

    def __deepcopy__(self, memo):
        raise TypeError("H25 scientific authority cannot be deep-copied.")

    def __reduce_ex__(self, protocol):
        raise TypeError("H25 scientific authority cannot be serialized.")

    def execute_once(self, repository_root: Path) -> Path:
        with self.__lock:
            if self.__state != "ISSUED":
                raise PermissionError("H25 scientific authority is already consumed.")
            if Path(repository_root).resolve(strict=True) != self.__capability.repository_root:
                raise ValueError("H25 runner repository differs from capability.")
            self.__state = "CONSUMED_BEFORE_DELEGATION"
        from . import run_harmonic_censoring_h25_scientific as runner

        return runner._execute_attested_h25_scientific_execution(self.__capability)


def _issue_h25_scientific_authority(repository_root: Path) -> IssuedH25ScientificAuthority:
    """Future issuer; currently fails before contracts, population or NumPy."""

    global _ISSUED
    root = Path(repository_root).resolve(strict=True)
    seal, activation, head = _validate_future_transition(root)
    contract = _validate_dormant_contract(root)
    contract_raw = (root / CAPABILITY_CONTRACT).read_bytes()
    if seal["capability_contract_sha256"] != _sha256(contract_raw):
        raise ValueError("H25 seal capability-contract SHA mismatch.")
    _git(root, "merge-base", "--is-ancestor", seal["reviewed_authority_commit"], "HEAD")
    source_bindings = (
        ("authority_source_blob", "src/polyphonic/harmonic_censoring_h25_scientific_capability.py"),
        ("runner_source_blob", "src/polyphonic/run_harmonic_censoring_h25_scientific.py"),
        ("engine_source_blob", "src/polyphonic/harmonic_censoring_h25_scientific_engine.py"),
        ("recomputer_source_blob", "src/polyphonic/harmonic_censoring_h25_recomputer.py"),
    )
    for field_name, source_path in source_bindings:
        expected_blob = _require_hex(seal[field_name], 40, field_name)
        if _git(root, "rev-parse", f"HEAD:{source_path}") != expected_blob:
            raise ValueError(f"H25 current {field_name} mismatch.")
        if field_name in {
            "authority_source_blob", "runner_source_blob", "recomputer_source_blob"
        } and _git(
            root,
            "rev-parse",
            f"{seal['reviewed_authority_commit']}:{source_path}",
        ) != expected_blob:
            raise ValueError(f"H25 reviewed {field_name} historical binding mismatch.")
    if seal["engine_source_blob"] != REVIEWED_ENGINE_BLOB:
        raise ValueError("H25 seal does not preserve the approved engine blob.")
    population = contract["published_population"]
    population_directory = (root / population["directory"]).resolve(strict=True)
    population_hashes = {
        "population_index_sha256": (root / population["index"]["path"], population["index"]["raw_sha256"]),
        "population_provenance_sha256": (root / population["runtime_provenance"]["path"], population["runtime_provenance"]["raw_sha256"]),
        "population_receipt_sha256": (root / population["receipt"]["path"], population["receipt"]["raw_sha256"]),
    }
    for field_name, (path, expected) in population_hashes.items():
        if seal[field_name] != expected or _sha256(path.read_bytes()) != expected:
            raise ValueError(f"H25 published {field_name} mismatch.")
    administrative_path = root / _require_relative(
        seal["administrative_qualification_record_path"],
        "administrative qualification record path",
    )
    if seal["administrative_qualification_sha256"] != ADMINISTRATIVE_QUALIFICATION_SHA256 or _sha256(administrative_path.read_bytes()) != ADMINISTRATIVE_QUALIFICATION_SHA256:
        raise ValueError("H25 administrative qualification record mismatch.")
    _require_runtime_before_numpy(root, contract)
    from .harmonic_censoring_h25_scientific_engine import load_h25_dormant_scientific_plan

    plan = load_h25_dormant_scientific_plan(root)
    ordered_fixture_ids = _load_ordered_population_ids(
        population_directory, root / population["index"]["path"]
    )
    if ordered_fixture_ids != plan.fixture_ids:
        raise ValueError("H25 published population order differs from the sealed plan.")
    topology = contract["one_shot_execution"]
    one_shot_paths = {
        name: (root / topology[name]).resolve()
        for name in (
            "claim_path", "staging_directory", "success_directory",
            "terminal_path", "forensic_terminal_path",
        )
    }
    population_root = population_directory.resolve(strict=True)
    for name, path in one_shot_paths.items():
        path.relative_to(root)
        if path.exists():
            raise FileExistsError(f"H25 scientific one-shot path already exists: {name}.")
        if name in {"terminal_path", "forensic_terminal_path"} and path.with_name(
            path.name + ".part"
        ).exists():
            raise FileExistsError(
                f"H25 scientific one-shot staging file already exists: {name}.part."
            )
        cursor = path.parent
        while cursor != root:
            if cursor.exists() and cursor.is_symlink():
                raise ValueError(f"H25 scientific {name} has a symlink ancestor.")
            cursor = cursor.parent
        if path == population_root or path in population_root.parents or population_root in path.parents:
            raise ValueError(f"H25 scientific {name} overlaps the published population.")
    if len(set(one_shot_paths.values())) != len(one_shot_paths):
        raise ValueError("H25 scientific one-shot paths collide.")
    command = seal["secondary_runtime_command"]
    timeout = seal["secondary_runtime_timeout_seconds"]
    if type(command) is not list or not command or any(type(item) is not str or not item for item in command):
        raise ValueError("H25 secondary runtime command is invalid.")
    if type(timeout) is not int or type(timeout) is bool or timeout <= 0:
        raise ValueError("H25 secondary runtime timeout is invalid.")
    secondary_runtime_identity = _validate_secondary_runtime_identity(
        root, command, seal["secondary_runtime_identity"]
    )
    with _ISSUE_LOCK:
        if _ISSUED:
            raise PermissionError("H25 scientific authority was already issued in this process.")
        capability = _new_capability(
            repository_root=root,
            authorization_commit=head,
            activation_sha256=_sha256((root / ACTIVATION_RECORD).read_bytes()),
            seal_sha256=_sha256((root / AUTHORIZATION_SEAL).read_bytes()),
            capability_contract_sha256=_sha256(contract_raw),
            authority_source_blob=str(seal["authority_source_blob"]),
            runner_source_blob=str(seal["runner_source_blob"]),
            engine_source_blob=str(seal["engine_source_blob"]),
            recomputer_source_blob=str(seal["recomputer_source_blob"]),
            population_directory=population_directory,
            population_index_sha256=str(seal["population_index_sha256"]),
            population_provenance_sha256=str(seal["population_provenance_sha256"]),
            population_receipt_sha256=str(seal["population_receipt_sha256"]),
            administrative_qualification_sha256=str(seal["administrative_qualification_sha256"]),
            ordered_fixture_ids=ordered_fixture_ids,
            ordered_test_ids=plan.test_ids,
            ordered_test_phases=tuple(test.phase for test in plan.tests),
            claim_path=one_shot_paths["claim_path"],
            staging_directory=one_shot_paths["staging_directory"],
            success_directory=one_shot_paths["success_directory"],
            terminal_path=one_shot_paths["terminal_path"],
            forensic_terminal_path=one_shot_paths["forensic_terminal_path"],
            secondary_runtime_command=tuple(command),
            secondary_runtime_timeout_seconds=timeout,
            secondary_runtime_identity=secondary_runtime_identity,
        )
        wrapper = IssuedH25ScientificAuthority(capability, _token=_WRAPPER_TOKEN)
        _ISSUED = True
        return wrapper


def _claim_h25_scientific_execution(
    value: object,
) -> AttestedH25ScientificCapability:
    checked = require_attested_h25_scientific_capability(value)
    marker = {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h25_scientific_execution_claim",
        "claim_state": "CLAIMED_BEFORE_FIRST_POPULATION_WAVEFORM",
        "authorization_commit": checked.authorization_commit,
        "activation_sha256": checked.activation_sha256,
        "seal_sha256": checked.seal_sha256,
        "capability_contract_sha256": checked.capability_contract_sha256,
        "authority_source_blob": checked.authority_source_blob,
        "runner_source_blob": checked.runner_source_blob,
        "engine_source_blob": checked.engine_source_blob,
        "recomputer_source_blob": checked.recomputer_source_blob,
        "population_index_sha256": checked.population_index_sha256,
        "population_provenance_sha256": checked.population_provenance_sha256,
        "population_receipt_sha256": checked.population_receipt_sha256,
        "administrative_qualification_sha256": checked.administrative_qualification_sha256,
        "ordered_fixture_ids": list(checked.ordered_fixture_ids),
        "ordered_test_ids": list(checked.ordered_test_ids),
        "real_data_used": False,
        "H17_H23_H24_population_used": False,
        "locked_test_used": False,
        "model_or_training_authorized": False,
    }
    raw = _canonical(marker)
    _write_new_durable(checked.claim_path, raw)
    if checked.claim_path.read_bytes() != raw:
        raise ValueError("H25 scientific claim bytes changed after durable write.")
    if os.name != "nt" and checked.claim_path.stat().st_mode & 0o777 != 0o600:
        raise PermissionError("H25 scientific claim mode is not 0600.")
    _CLAIMED[id(checked)] = weakref.ref(checked)
    return checked


__all__ = [
    "AttestedH25ScientificCapability",
    "IssuedH25ScientificAuthority",
    "require_attested_h25_scientific_capability",
    "require_claimed_h25_scientific_capability",
]
