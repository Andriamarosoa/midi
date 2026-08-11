"""Reviewed but not yet authorized real H26 materialization one-shot boundary."""
from __future__ import annotations

from dataclasses import asdict
import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
from types import SimpleNamespace
import weakref
from typing import Any, Mapping

from . import harmonic_censoring_h26_materialization_authority_artifact as authority_artifact
from . import harmonic_censoring_h26_materialization_runtime_execution_proof as proof_validator
from . import harmonic_censoring_h26_runtime_execution_primitives as runtime
from . import harmonic_censoring_h26_runtime_qualification as qualifier

ADMIN_ROOT = Path("/Users/amcarene/h26-admin")
DESTINATION = Path("/Users/amcarene/h26-admin/population/h26-synthetic-v1")
AUTHORITY_DIRECTORY = ADMIN_ROOT / "materialization-authority"
SEAL_DIRECTORY = ADMIN_ROOT / "materialization-authority-seal"
ACK = "H26_MATERIALIZATION_EXECUTE"
AUTHORIZATION_COMMIT = "H26_MATERIALIZATION_AUTHORIZATION_COMMIT"
ISSUED_AT = "2026-08-12T13:00:00Z"
ISSUER = "h26-execution-codex-mac-primary"
WORKER_LOCK = Path("/Users/amcarene/midi-worker/active.lock")
ENTRYPOINT_CONTRACT = Path("configs/harmonic_censoring_h26_materialization_operational_entrypoint_contract.json")
RUNTIME_SHAS = {
    "authority": "8a082d7ebde873baaa92a0559b93a92154db2dfaee835c7c5022b436b21398ef",
    "claim": "f703fd0c831758acd16232f5923ab06ae5b411fbe81a99a066e56da0f7a64ca9",
    "observer-entry": "d7459e680faeecb87c1635fe7e0bc8398749842331ea7c871f990e1ee97d2b1c",
    "runtime-record": "7ed6b9090284fae99009cb27054467e26268529c9608ae0082c7238688659dc2",
    "receipt": "aa0347dcc787033d3b6cb224b2bfb30943257284e904e8c12c95d7fdfeb4017a",
}
RUNTIME_FILENAMES = {
    "authority": RUNTIME_SHAS["authority"] + ".json",
    "claim": "h26-runtime-claim-v1-1d6d556e460da9163ebaeb462360204d5881d118862aefd9be07d393fd274c7d.json",
    "observer-entry": "h26-runtime-entry-v1-e252ea620222e0acd37e39322f2fe86ca7f4bb599c63de614f7739af6545b9e6.json",
    "runtime-record": "h26-runtime-claim-v1-1d6d556e460da9163ebaeb462360204d5881d118862aefd9be07d393fd274c7d.json",
    "receipt": "h26-runtime-claim-v1-1d6d556e460da9163ebaeb462360204d5881d118862aefd9be07d393fd274c7d.json",
}

_BOUNDARIES: dict[int, weakref.ReferenceType["_H26MaterializationBoundary"]] = {}
_MATERIALIZER_ADAPTER_LOCK = threading.Lock()

class _H26MaterializationBoundary:
    __slots__ = ("head", "authority_sha256", "authority_path", "seal_path", "__weakref__")
    def __new__(cls):
        raise TypeError("H26 materialization boundary has no public constructor")

def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]

def _git(*args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=_repo_root(), text=True, encoding="utf-8").strip()

def _load_entrypoint_contract() -> Mapping[str, Any]:
    value = runtime.parse_canonical_json_bytes((_repo_root() / ENTRYPOINT_CONTRACT).read_bytes())
    expected = {
        "schema_identity": "H26_MATERIALIZATION_OPERATIONAL_ENTRYPOINT_V1",
        "schema_version": 1,
        "approved_stop3_archive_commit": "71cf6638b3c0b50786dea71ca32445972049aa6c",
        "administrative_root": "/Users/amcarene/h26-admin",
        "absolute_destination": "/Users/amcarene/h26-admin/population/h26-synthetic-v1",
        "issued_at": ISSUED_AT, "issuer_identity": ISSUER,
        "acknowledgement_variable": ACK, "authorization_commit_variable": AUTHORIZATION_COMMIT,
        "runtime_artifact_sha256": {
            "authority": RUNTIME_SHAS["authority"], "claim": RUNTIME_SHAS["claim"],
            "observer_entry": RUNTIME_SHAS["observer-entry"],
            "runtime_record": RUNTIME_SHAS["runtime-record"], "receipt": RUNTIME_SHAS["receipt"],
        },
        "materializer_invocations_maximum": 1, "retry_allowed": False,
        "locked_test_used": False,
    }
    lifecycle = {
        (
            "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_MATERIALIZATION",
            False,
            "External review before materialization authority publication or materializer invocation",
        ),
        (
            "AUTHORIZED_REAL_MATERIALIZATION_ONE_SHOT",
            True,
            "Run the single authorized H26 materialization invocation, then stop for external review",
        ),
    }
    actual_lifecycle = (
        value.get("status"), value.get("real_execution_authorized"),
        value.get("next_action"),
    )
    comparable = dict(value)
    for key in ("status", "real_execution_authorized", "next_action"):
        comparable.pop(key, None)
    if comparable != expected or actual_lifecycle not in lifecycle:
        raise ValueError("H26 materialization entrypoint contract mismatch")
    return value

def _require_execution_boundary() -> str:
    entrypoint_contract = _load_entrypoint_contract()
    if entrypoint_contract["real_execution_authorized"] is not True:
        raise PermissionError("H26 real materialization is not externally authorized")
    if platform.system() != "Darwin":
        raise RuntimeError("H26 materialization requires macOS")
    if os.environ.get(ACK) != "1":
        raise PermissionError("H26 materialization acknowledgement missing")
    head = _git("rev-parse", "HEAD")
    if os.environ.get(AUTHORIZATION_COMMIT) != head:
        raise PermissionError("H26 materialization authorization commit must equal HEAD")
    if _git("status", "--porcelain=v1"):
        raise PermissionError("H26 materialization requires a clean worktree")
    if WORKER_LOCK.exists():
        raise PermissionError("H26 materialization requires no worker lock")
    contract = qualifier.load_runtime_qualification_contract()
    for key, value in contract.process_environment_exact:
        if os.environ.get(key) != value:
            raise PermissionError(f"H26 materialization environment mismatch: {key}")
    return head

def _read_runtime_artifacts() -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], qualifier.H26RuntimeQualificationRecord, dict[str, Any]]:
    values: dict[str, Any] = {}
    raws: dict[str, bytes] = {}
    for kind, expected in RUNTIME_SHAS.items():
        path = ADMIN_ROOT / kind / RUNTIME_FILENAMES[kind]
        if path.is_symlink() or not path.is_file():
            raise FileNotFoundError(f"H26 runtime {kind} artifact absent")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected:
            raise ValueError(f"H26 runtime {kind} SHA mismatch")
        raws[kind] = raw
    for kind in ("authority", "claim", "observer-entry", "receipt"):
        values[kind] = runtime.parse_canonical_json_bytes(raws[kind])
    payload = runtime.parse_canonical_json_bytes(raws["runtime-record"])
    observed_runtime = payload.get("observed_runtime")
    if isinstance(observed_runtime, dict):
        payload["observed_runtime"] = {
            field: observed_runtime[field]
            for field in qualifier._RUNTIME_IDENTITY_FIELDS
        }
    qualifier._validate_runtime_record_payload(payload)
    record = object.__new__(qualifier.H26RuntimeQualificationRecord)
    object.__setattr__(record, "_payload", qualifier._freeze(payload))
    if qualifier.serialize_runtime_qualification_record(record) != raws["runtime-record"]:
        raise ValueError("H26 runtime record bytes are not canonical")
    proof_validator.validate_artificial_materialization_runtime_execution_proof(
        values["authority"], values["claim"], values["observer-entry"], values["receipt"],
        RUNTIME_SHAS["authority"], RUNTIME_SHAS["claim"], RUNTIME_SHAS["observer-entry"],
        RUNTIME_SHAS["receipt"], record,
    )
    return values["authority"], values["claim"], values["observer-entry"], record, values["receipt"]

def _observe_live_materialization_runtime() -> qualifier.RuntimeObservation:
    """Acquire read-only evidence for this process without the one-shot observer."""

    numpy_module = importlib.import_module("numpy")
    multiarray_module = importlib.import_module("numpy.core._multiarray_umath")
    multiarray_path = Path(str(multiarray_module.__file__))
    environment = qualifier.environment_items({
        key: os.environ[key]
        for key in qualifier.CONTROL_ENVIRONMENT_KEYS
        if key in os.environ
    })
    executable_proof = qualifier._binary_proof(Path(sys.executable))
    multiarray_proof = qualifier._binary_proof(multiarray_path)
    try:
        blas = qualifier._observe_linked_blas_dependency(multiarray_path)
    except Exception as exc:
        return qualifier.RuntimeObservation(
            runtime=None,
            process_environment=environment,
            executable=executable_proof,
            numpy_multiarray=multiarray_proof,
            blas_library=qualifier.BinaryProof(
                resolved_path=None,
                size_bytes=None,
                sha256=None,
                acquisition_error=f"BLAS dependency evidence unavailable: {exc}",
            ),
        )
    return qualifier.RuntimeObservation(
        runtime=qualifier.RuntimeIdentity(
            implementation=platform.python_implementation(),
            version=platform.python_version(),
            platform_system=platform.system(),
            platform_release=platform.release(),
            platform_machine=platform.machine(),
            numpy_version=str(numpy_module.__version__),
            blas_provider=blas.provider,
        ),
        process_environment=environment,
        executable=executable_proof,
        numpy_multiarray=multiarray_proof,
        blas_library=blas.binary_proof,
    )

def _require_live_runtime_matches_stop3(
    record: qualifier.H26RuntimeQualificationRecord,
) -> qualifier.RuntimeObservation:
    payload = record.as_dict()
    expected = qualifier._observation_from_record_payload(payload)
    live = _observe_live_materialization_runtime()
    if live != expected:
        raise PermissionError("current materialization runtime differs from STOP3 evidence")
    contract = qualifier.load_runtime_qualification_contract()
    if qualifier.derive_runtime_terminal_status(contract, live) != qualifier.STATUS_QUALIFIED:
        raise PermissionError("current materialization runtime is not qualified")
    return live

def _build_authority(runtime_values: tuple[Any, ...]) -> tuple[dict[str, Any], bytes, str]:
    ra, rc, re, record, rr = runtime_values
    proof = proof_validator.validate_artificial_materialization_runtime_execution_proof(
        ra, rc, re, rr, RUNTIME_SHAS["authority"], RUNTIME_SHAS["claim"],
        RUNTIME_SHAS["observer-entry"], RUNTIME_SHAS["receipt"], record,
    )
    contract = authority_artifact.load_materialization_authority_artifact_contract()
    rules = contract["future_authority_artifact"]
    value = dict(rules["fixed_values"])
    value.update(asdict(proof))
    value.update({"authority_id": "h26-materialization-authority-v1-" + "0" * 64,
                  "absolute_destination": str(DESTINATION), "issued_at": ISSUED_AT,
                  "issuer_identity": ISSUER})
    value["authority_id"] = authority_artifact.derive_materialization_authority_id(value)
    validated = authority_artifact.validate_artificial_materialization_authority_artifact(
        value, runtime_authority=ra, runtime_claim=rc, runtime_evidence=re,
        runtime_receipt=rr, runtime_authority_raw_sha256=RUNTIME_SHAS["authority"],
        runtime_claim_raw_sha256=RUNTIME_SHAS["claim"],
        runtime_evidence_raw_sha256=RUNTIME_SHAS["observer-entry"],
        runtime_receipt_raw_sha256=RUNTIME_SHAS["receipt"], runtime_record=record)
    return value, validated.canonical_bytes, validated.raw_sha256

def _seal(authority_sha: str) -> bytes:
    return runtime.canonical_json_bytes({
        "seal_schema_identity": "H26_EXTERNAL_AUTHORITY_SEAL_V1", "seal_schema_version": 1,
        "authority_raw_sha256": authority_sha,
        "authority_contract_raw_sha256": "a82b00cfe197dc927dcc7a34ee409b7ea8ab374f36b6e41ebdaea12710258002",
        "approved_authority_contract_commit": "84d1a196635c6ace7f3ea5ec9b7e338f5da70300",
    })

def _publish(path: Path, raw: bytes) -> None:
    staging = path.with_name("." + path.name + ".part")
    if path.exists() or staging.exists():
        raise FileExistsError("H26 materialization publication slot exists")
    fd = os.open(str(staging), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as handle:
        handle.write(raw); handle.flush(); os.fsync(handle.fileno())
    _rename_no_replace(staging, path)
    _sync_directory(path.parent)

def _sync_directory(path: Path) -> None:
    directory_fd = os.open(str(path), os.O_RDONLY)
    try: os.fsync(directory_fd)
    finally: os.close(directory_fd)

def _rename_no_replace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.renameatx_np
    function.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    function.restype = ctypes.c_int
    if function(-2, os.fsencode(source), -2, os.fsencode(destination), 0x00000004) != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))

def _mint_boundary(
    head: str, authority_sha: str, authority_path: Path, seal_path: Path,
) -> _H26MaterializationBoundary:
    if not authority_path.is_file() or authority_path.is_symlink():
        raise PermissionError("durable materialization authority required")
    if hashlib.sha256(authority_path.read_bytes()).hexdigest() != authority_sha:
        raise PermissionError("durable materialization authority SHA mismatch")
    if not seal_path.is_file() or seal_path.is_symlink() or seal_path.read_bytes() != _seal(authority_sha):
        raise PermissionError("durable materialization authority seal mismatch")
    boundary = object.__new__(_H26MaterializationBoundary)
    boundary.head, boundary.authority_sha256 = head, authority_sha
    boundary.authority_path, boundary.seal_path = authority_path, seal_path
    identity = id(boundary)
    def cleanup(reference: weakref.ReferenceType[_H26MaterializationBoundary]) -> None:
        if _BOUNDARIES.get(identity) is reference: _BOUNDARIES.pop(identity, None)
    _BOUNDARIES[identity] = weakref.ref(boundary, cleanup)
    return boundary

def _require_materialization_boundary(value: object) -> _H26MaterializationBoundary:
    reference = _BOUNDARIES.get(id(value))
    if type(value) is not _H26MaterializationBoundary or reference is None or reference() is not value:
        raise PermissionError("attested H26 materialization boundary required")
    if value.authority_path.is_symlink() or not value.authority_path.is_file():
        raise PermissionError("attested H26 authority disappeared")
    if hashlib.sha256(value.authority_path.read_bytes()).hexdigest() != value.authority_sha256:
        raise PermissionError("attested H26 authority changed")
    if value.seal_path.is_symlink() or not value.seal_path.is_file():
        raise PermissionError("attested H26 authority seal disappeared")
    if value.seal_path.read_bytes() != _seal(value.authority_sha256):
        raise PermissionError("attested H26 authority seal changed")
    return value

def _invoke_real_materializer(boundary: _H26MaterializationBoundary) -> None:
    _require_materialization_boundary(boundary)
    import numpy as np
    from .harmonic_censoring_h26_contract import load_h26_dormant_plan
    from . import harmonic_censoring_h26_materializer as materializer
    plan = load_h26_dormant_plan(_repo_root())
    class _PrivateCapability:
        implementation_commit = "60b8d90bcbb5fb6e3a82d839bae706a359ab310e"
    capability = _PrivateCapability()
    def private_adapter(candidate: object) -> Any:
        _require_materialization_boundary(boundary)
        if candidate is not capability:
            raise PermissionError("private H26 materializer capability mismatch")
        return plan
    with _MATERIALIZER_ADAPTER_LOCK:
        original = materializer._require_capability
        original_os = materializer.os
        materializer_os = SimpleNamespace(
            open=os.open, fdopen=os.fdopen, fsync=os.fsync,
            O_WRONLY=os.O_WRONLY, O_CREAT=os.O_CREAT, O_EXCL=os.O_EXCL,
            replace=_rename_no_replace,
        )
        materializer._require_capability = private_adapter
        materializer.os = materializer_os
        try:
            materializer.materialize_h26_population(np, capability, DESTINATION)
        finally:
            materializer.os = original_os
            materializer._require_capability = original

def execute_h26_materialization_once() -> Mapping[str, Any]:
    head = _require_execution_boundary()
    runtime_values = _read_runtime_artifacts()
    _require_live_runtime_matches_stop3(runtime_values[3])
    authority, authority_raw, authority_sha = _build_authority(runtime_values)
    seal_raw = _seal(authority_sha)
    authority_path = AUTHORITY_DIRECTORY / f"{authority_sha}.json"
    seal_path = SEAL_DIRECTORY / f"{authority_sha}.json"
    staging = DESTINATION.with_name(DESTINATION.name + ".staging")
    for directory in (AUTHORITY_DIRECTORY, SEAL_DIRECTORY, DESTINATION.parent):
        if directory.is_symlink() or not directory.is_dir():
            raise FileNotFoundError(f"required materialization directory absent: {directory}")
    publication_staging = (
        authority_path.with_name("." + authority_path.name + ".part"),
        seal_path.with_name("." + seal_path.name + ".part"),
    )
    if any(path.exists() for path in (authority_path, seal_path, DESTINATION, staging, *publication_staging)):
        raise FileExistsError("H26 materialization slot already exists")
    _publish(authority_path, authority_raw)
    _publish(seal_path, seal_raw)
    boundary = _mint_boundary(head, authority_sha, authority_path, seal_path)
    _invoke_real_materializer(boundary)
    return {"authority_id": authority["authority_id"], "authority_raw_sha256": authority_sha,
            "destination": str(DESTINATION), "materializer_invocations": 1,
            "retry_allowed": False}

def main() -> int:
    if len(sys.argv) != 1: raise SystemExit("H26 materialization accepts no arguments")
    print(json.dumps(dict(execute_h26_materialization_once()), sort_keys=True, separators=(",", ":")))
    return 0

if __name__ == "__main__": raise SystemExit(main())
