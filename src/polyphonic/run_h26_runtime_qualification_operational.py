"""Reviewed STOP-2-to-STOP-3 boundary for one H26 runtime qualification.

This module is operational but must not be invoked until separately reviewed.
It has no arguments, no caller-selected paths and no injected observer.
"""
from __future__ import annotations

import ctypes
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, Mapping, Tuple
import weakref

from . import harmonic_censoring_h26_runtime_execution_primitives as primitives
from . import harmonic_censoring_h26_runtime_qualification as qualifier
from .harmonic_censoring_h26_runtime_qualification_operational_activation import (
    validate_artificial_runtime_qualification_operational_activation,
)

ADMINISTRATIVE_ROOT = "/Users/amcarene/h26-admin"
ACTIVATION_ID = (
    "h26-runtime-activation-v1-"
    "61c06216bb264254573c6f13257b923fd34b31ca00693c59665f8d8bdbd43dde"
)
ACTIVATION_RAW_SHA256 = (
    "f96a811b4d00e2a022c405d7e14b2b99d3af5028389536d03c0f7c9fce414fe2"
)
AUTHORITY_ID = (
    "h26-runtime-authority-v1-"
    "61c06216bb264254573c6f13257b923fd34b31ca00693c59665f8d8bdbd43dde"
)
AUTHORITY_ISSUED_AT = "2026-08-12T12:30:00Z"
ISSUER_IDENTITY = "h26-execution-codex-mac-primary"
ACKNOWLEDGEMENT_VARIABLE = "H26_RUNTIME_QUALIFICATION_EXECUTE"
AUTHORIZATION_COMMIT_VARIABLE = "H26_RUNTIME_QUALIFICATION_AUTHORIZATION_COMMIT"
WORKER_LOCK_PATH = "/Users/amcarene/midi-worker/active.lock"
ENTRYPOINT_CONTRACT_PATH = (
    "configs/harmonic_censoring_h26_runtime_operational_entrypoint_contract.json"
)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_AT_FDCWD = -2
_RENAME_EXCL = 0x00000004
_CAPABILITIES: dict[int, weakref.ReferenceType["_H26RuntimeBoundaryCapability"]] = {}
_OBSERVER_CAPABILITIES: dict[int, weakref.ReferenceType["_H26ObserverEntryCapability"]] = {}


class _H26RuntimeBoundaryCapability:
    __slots__ = ("head", "__weakref__")

    def __new__(cls):
        raise TypeError("H26 runtime boundary capability has no public constructor")


class _H26ObserverEntryCapability:
    __slots__ = ("execution", "claim_id", "__weakref__")

    def __new__(cls):
        raise TypeError("H26 observer-entry capability has no public constructor")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_output(*arguments: str) -> str:
    return subprocess.check_output(
        ("git", *arguments), cwd=_repo_root(), text=True, encoding="utf-8"
    ).strip()


def _is_darwin() -> bool:
    return os.name == "posix" and hasattr(os, "uname") and os.uname().sysname == "Darwin"


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    if not raw or b"\r" in raw or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("H26 operational contract must be UTF-8 LF JSON")

    def hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate H26 operational contract key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"floating H26 operational contract value forbidden: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid H26 operational contract JSON") from exc
    if type(value) is not dict:
        raise ValueError("H26 operational contract must be an object")
    return value


def _load_execution_contract() -> Mapping[str, Any]:
    path = (_repo_root() / ENTRYPOINT_CONTRACT_PATH).resolve(strict=True)
    value = _strict_json_object(path.read_bytes())
    expected = {
        "schema_identity": "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ENTRYPOINT_V1",
        "schema_version": 1,
        "status": "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_RUNTIME_CONSUMPTION",
        "approved_activation_id": ACTIVATION_ID,
        "approved_activation_raw_sha256": ACTIVATION_RAW_SHA256,
        "administrative_root": ADMINISTRATIVE_ROOT,
        "authority_id": AUTHORITY_ID,
        "authority_issued_at": AUTHORITY_ISSUED_AT,
        "issuer_identity": ISSUER_IDENTITY,
        "acknowledgement_variable": ACKNOWLEDGEMENT_VARIABLE,
        "authorization_commit_variable": AUTHORIZATION_COMMIT_VARIABLE,
        "worker_lock_path": WORKER_LOCK_PATH,
        "required_platform": "Darwin",
        "required_environment": dict(qualifier._EXPECTED_ENVIRONMENT_ITEMS),
        "publication_order": [
            "authority",
            "claim",
            "observer_entry_evidence_inside_boundary",
            "observe_primary_runtime_once",
            "runtime_record_if_available",
            "terminal_receipt_last",
        ],
        "operational_observer": "private capability-gated real observer",
        "retry_allowed": False,
        "cleanup_after_consumption_allowed": False,
        "runtime_consumed": False,
        "materialization_executed": False,
        "locked_test_used": False,
        "next_action": "External review before authority or claim creation",
    }
    if value != expected:
        raise ValueError("H26 runtime operational entrypoint contract mismatch")
    return value


def _require_capability(value: object) -> _H26RuntimeBoundaryCapability:
    reference = _CAPABILITIES.get(id(value))
    if (
        type(value) is not _H26RuntimeBoundaryCapability
        or reference is None
        or reference() is not value
    ):
        raise PermissionError("H26 runtime operation requires an attested boundary")
    if value.head != _git_output("rev-parse", "HEAD"):
        raise PermissionError("H26 runtime boundary HEAD changed")
    if _git_output("status", "--porcelain=v1"):
        raise PermissionError("H26 runtime boundary requires a clean worktree")
    return value


def _require_observer_capability(value: object) -> _H26ObserverEntryCapability:
    reference = _OBSERVER_CAPABILITIES.get(id(value))
    if (
        type(value) is not _H26ObserverEntryCapability
        or reference is None
        or reference() is not value
    ):
        raise PermissionError("H26 observer requires an attested entry boundary")
    _require_capability(value.execution)
    return value


def _enter_observer_boundary(
    capability: _H26RuntimeBoundaryCapability,
    claim_id: str,
    claim_path: Path,
) -> _H26ObserverEntryCapability:
    _require_capability(capability)
    if claim_path.is_symlink() or not claim_path.is_file():
        raise PermissionError("H26 observer boundary requires the durable claim")
    observer = object.__new__(_H26ObserverEntryCapability)
    observer.execution = capability
    observer.claim_id = claim_id
    identity = id(observer)

    def cleanup(reference):
        if _OBSERVER_CAPABILITIES.get(identity) is reference:
            _OBSERVER_CAPABILITIES.pop(identity, None)

    _OBSERVER_CAPABILITIES[identity] = weakref.ref(observer, cleanup)
    return observer


def _require_execution_boundary() -> _H26RuntimeBoundaryCapability:
    _load_execution_contract()
    if not _is_darwin():
        raise RuntimeError("H26 runtime qualification requires macOS")
    if os.environ.get(ACKNOWLEDGEMENT_VARIABLE) != "1":
        raise PermissionError("H26 runtime qualification acknowledgement missing")
    authorization_commit = os.environ.get(AUTHORIZATION_COMMIT_VARIABLE)
    if type(authorization_commit) is not str or _COMMIT.fullmatch(authorization_commit) is None:
        raise PermissionError("H26 runtime authorization commit missing")
    head = _git_output("rev-parse", "HEAD")
    if authorization_commit != head:
        raise PermissionError("H26 runtime authorization commit must equal HEAD")
    if _git_output("status", "--porcelain=v1"):
        raise PermissionError("H26 runtime qualification requires a clean worktree")
    if os.path.lexists(WORKER_LOCK_PATH):
        raise PermissionError("H26 runtime qualification requires no active worker lock")
    contract = qualifier.load_runtime_qualification_contract()
    expected_environment = dict(contract.process_environment_exact)
    for key, expected in expected_environment.items():
        if os.environ.get(key) != expected:
            raise PermissionError(f"H26 runtime environment mismatch: {key}")

    capability = object.__new__(_H26RuntimeBoundaryCapability)
    capability.head = head
    identity = id(capability)

    def cleanup(reference):
        if _CAPABILITIES.get(identity) is reference:
            _CAPABILITIES.pop(identity, None)

    _CAPABILITIES[identity] = weakref.ref(capability, cleanup)
    return capability


def _load_activation(capability: _H26RuntimeBoundaryCapability) -> Mapping[str, Any]:
    _require_capability(capability)
    path = Path(ADMINISTRATIVE_ROOT) / "activation" / "activation.json"
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError("reviewed H26 activation is absent or non-regular")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != ACTIVATION_RAW_SHA256:
        raise ValueError("reviewed H26 activation SHA-256 mismatch")
    value = primitives.parse_canonical_json_bytes(raw)
    if type(value) is not dict:
        raise ValueError("reviewed H26 activation must be an object")
    validated = validate_artificial_runtime_qualification_operational_activation(value)
    if validated.activation_id != ACTIVATION_ID or validated.canonical_bytes != raw:
        raise ValueError("reviewed H26 activation binding mismatch")
    return value


def _authority() -> dict[str, Any]:
    return {
        "schema_identity": "H26_RUNTIME_QUALIFICATION_EXECUTION_AUTHORITY_V1",
        "schema_version": 1,
        "execution_authority_contract_commit": primitives.EXECUTION_AUTHORITY_CONTRACT_COMMIT,
        "execution_authority_contract_raw_sha256": primitives.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256,
        "runtime_qualification_contract_commit": primitives.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
        "runtime_qualification_contract_git_blob_sha": primitives.RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA,
        "runtime_qualification_contract_raw_sha256": primitives.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
        "qualifier_commit": primitives.APPROVED_DORMANT_QUALIFIER_COMMIT,
        "qualifier_git_blob_sha": primitives.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
        "materialization_authority_contract_commit": primitives.MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT,
        "materialization_authority_contract_git_blob_sha": primitives.MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        "target_runtime_role": primitives.TARGET_RUNTIME_ROLE,
        "authority_id": AUTHORITY_ID,
        "single_use": True,
        "maximum_claims_per_authority": 1,
        "maximum_observer_invocations": 1,
        "authority_consumed_by_first_claim_creation": True,
        "retry_allowed": False,
        "execution_authorized": True,
        "issued_at": AUTHORITY_ISSUED_AT,
        "issuer_identity": ISSUER_IDENTITY,
    }


def _claim(authority: Mapping[str, Any], authority_sha: str) -> dict[str, Any]:
    return {
        "schema_identity": "H26_RUNTIME_QUALIFICATION_SINGLE_USE_CLAIM_V1",
        "schema_version": 1,
        "claim_id": primitives.derive_claim_id(AUTHORITY_ID, authority_sha),
        "authority_id": AUTHORITY_ID,
        "authority_raw_sha256": authority_sha,
        "execution_authority_contract_commit": authority["execution_authority_contract_commit"],
        "execution_authority_contract_raw_sha256": authority["execution_authority_contract_raw_sha256"],
        "runtime_qualification_contract_commit": primitives.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
        "runtime_qualification_contract_git_blob_sha": primitives.RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA,
        "runtime_qualification_contract_raw_sha256": primitives.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
        "qualifier_commit": primitives.APPROVED_DORMANT_QUALIFIER_COMMIT,
        "qualifier_git_blob_sha": primitives.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
        "target_runtime_role": primitives.TARGET_RUNTIME_ROLE,
        "single_use": True,
        "maximum_claims_per_authority": 1,
        "maximum_observer_invocations": 1,
        "authority_consumed": True,
        "claim_consumed": True,
        "retry_allowed": False,
    }


def _evidence(
    observer_capability: _H26ObserverEntryCapability,
    authority: Mapping[str, Any],
    authority_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
) -> dict[str, Any]:
    observer = _require_observer_capability(observer_capability)
    if observer.claim_id != claim["claim_id"]:
        raise PermissionError("H26 observer boundary claim mismatch")
    return {
        "schema_identity": "H26_RUNTIME_QUALIFICATION_OBSERVER_ENTRY_EVIDENCE_V1",
        "schema_version": 1,
        "observer_entry_evidence_id": primitives.derive_observer_entry_evidence_id(
            AUTHORITY_ID, authority_sha, str(claim["claim_id"]), claim_sha
        ),
        "authority_id": AUTHORITY_ID,
        "authority_raw_sha256": authority_sha,
        "claim_id": claim["claim_id"],
        "claim_raw_sha256": claim_sha,
        "qualifier_commit": primitives.APPROVED_DORMANT_QUALIFIER_COMMIT,
        "qualifier_git_blob_sha": primitives.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
        "observer_entry_ordinal": 1,
    }


def _receipt(
    authority: Mapping[str, Any],
    authority_sha: str,
    claim: Mapping[str, Any],
    claim_sha: str,
    evidence: Mapping[str, Any],
    evidence_sha: str,
    record,
) -> dict[str, Any]:
    record_sha = None
    status = qualifier.STATUS_INCONCLUSIVE
    if record is not None:
        record_raw = qualifier.serialize_runtime_qualification_record(record)
        record_sha = hashlib.sha256(record_raw).hexdigest()
        status = record.as_dict()["terminal_status"]
    return {
        "schema_identity": "H26_RUNTIME_QUALIFICATION_EXECUTION_RECEIPT_V1",
        "schema_version": 1,
        "claim_id": claim["claim_id"],
        "claim_raw_sha256": claim_sha,
        "authority_id": AUTHORITY_ID,
        "authority_raw_sha256": authority_sha,
        "qualifier_commit": primitives.APPROVED_DORMANT_QUALIFIER_COMMIT,
        "qualifier_git_blob_sha": primitives.APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
        "runtime_qualification_contract_commit": primitives.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
        "runtime_qualification_contract_raw_sha256": primitives.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
        "observer_entered": True,
        "observer_entry_evidence_id": evidence["observer_entry_evidence_id"],
        "observer_entry_evidence_raw_sha256": evidence_sha,
        "runtime_record_exists": record is not None,
        "runtime_record_raw_sha256": record_sha,
        "terminal_status": status,
        "observer_invocation_count": 1,
        "claim_consumed": True,
        "retry_allowed": False,
    }


def _paths(authority_sha: str, claim_id: str, evidence_id: str) -> dict[str, tuple[Path, Path]]:
    root = Path(ADMINISTRATIVE_ROOT)
    return {
        "authority": (
            root / "authority" / f"{authority_sha}.json",
            root / "authority" / f".{authority_sha}.json.staging",
        ),
        "claim": (
            root / "claim" / f"{claim_id}.json",
            root / "claim" / f".{claim_id}.json.staging",
        ),
        "evidence": (
            root / "observer-entry" / f"{evidence_id}.json",
            root / "observer-entry" / f".{evidence_id}.json.staging",
        ),
        "record": (
            root / "runtime-record" / f"{claim_id}.json",
            root / "runtime-record" / f".{claim_id}.json.staging",
        ),
        "receipt": (
            root / "receipt" / f"{claim_id}.json",
            root / "receipt" / f".{claim_id}.json.staging",
        ),
    }


def _preflight_paths(capability: _H26RuntimeBoundaryCapability, paths) -> None:
    _require_capability(capability)
    root = Path(ADMINISTRATIVE_ROOT)
    if root.resolve(strict=True) != root or root.is_symlink():
        raise ValueError("H26 administrative root is not canonical")
    for final, staging in paths.values():
        parent = final.parent
        if parent.resolve(strict=True) != parent or parent.is_symlink() or not parent.is_dir():
            raise ValueError("H26 operational artifact directory mismatch")
        if final.exists() or final.is_symlink() or staging.exists() or staging.is_symlink():
            raise FileExistsError("H26 operational final or staging slot already exists")


def _rename_no_replace(source: Path, destination: Path) -> None:
    libc = ctypes.CDLL(None, use_errno=True)
    renameatx_np = libc.renameatx_np
    renameatx_np.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameatx_np.restype = ctypes.c_int
    result = renameatx_np(
        _AT_FDCWD,
        os.fsencode(source),
        _AT_FDCWD,
        os.fsencode(destination),
        _RENAME_EXCL,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


def _sync_directory(path: Path) -> None:
    directory_fd = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(directory_fd)
    finally:
        os.close(directory_fd)


def _publish(
    capability: _H26RuntimeBoundaryCapability,
    final: Path,
    staging: Path,
    raw: bytes,
) -> None:
    _require_capability(capability)
    if (
        type(raw) is not bytes
        or final.parent.is_symlink()
        or final.parent.resolve(strict=True) != final.parent
        or not stat.S_ISDIR(final.parent.stat().st_mode)
    ):
        raise ValueError("H26 operational publication input mismatch")
    if final.exists() or final.is_symlink() or staging.exists() or staging.is_symlink():
        raise FileExistsError("H26 operational artifact slot is no longer absent")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(staging, flags, 0o600)
    try:
        os.fchmod(descriptor, 0o600)
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("short H26 operational artifact write")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _require_capability(capability)
    _rename_no_replace(staging, final)
    _sync_directory(final.parent)


def _observe_primary_runtime(
    capability: _H26ObserverEntryCapability,
) -> qualifier.RuntimeObservation:
    _require_observer_capability(capability)
    numpy_module = importlib.import_module("numpy")
    multiarray_module = importlib.import_module("numpy.core._multiarray_umath")
    multiarray_path = Path(str(multiarray_module.__file__))
    environment = qualifier.environment_items(dict(os.environ))
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
    identity = qualifier.RuntimeIdentity(
        implementation=platform.python_implementation(),
        version=platform.python_version(),
        platform_system=platform.system(),
        platform_release=platform.release(),
        platform_machine=platform.machine(),
        numpy_version=str(numpy_module.__version__),
        blas_provider=blas.provider,
    )
    return qualifier.RuntimeObservation(
        runtime=identity,
        process_environment=environment,
        executable=executable_proof,
        numpy_multiarray=multiarray_proof,
        blas_library=blas.binary_proof,
    )


def execute_h26_runtime_qualification_once() -> dict[str, Any]:
    capability = _require_execution_boundary()
    _load_activation(capability)
    primitives.load_runtime_execution_contract()
    primitives.load_runtime_execution_external_seal()

    authority = _authority()
    primitives.validate_artificial_authority(authority)
    authority_raw = primitives.canonical_json_bytes(authority)
    authority_sha = hashlib.sha256(authority_raw).hexdigest()
    claim = _claim(authority, authority_sha)
    primitives.validate_artificial_claim(authority, claim, authority_sha)
    claim_raw = primitives.canonical_json_bytes(claim)
    claim_sha = hashlib.sha256(claim_raw).hexdigest()
    evidence_id = primitives.derive_observer_entry_evidence_id(
        AUTHORITY_ID, authority_sha, str(claim["claim_id"]), claim_sha
    )
    paths = _paths(authority_sha, str(claim["claim_id"]), evidence_id)
    _preflight_paths(capability, paths)

    _publish(capability, *paths["authority"], authority_raw)
    _publish(capability, *paths["claim"], claim_raw)
    observer_capability = _enter_observer_boundary(
        capability, str(claim["claim_id"]), paths["claim"][0]
    )
    evidence = _evidence(
        observer_capability, authority, authority_sha, claim, claim_sha
    )
    primitives.validate_artificial_observer_entry_evidence(
        authority, claim, evidence, authority_sha, claim_sha
    )
    evidence_raw = primitives.canonical_json_bytes(evidence)
    evidence_sha = hashlib.sha256(evidence_raw).hexdigest()
    _publish(capability, *paths["evidence"], evidence_raw)

    try:
        observation = _observe_primary_runtime(observer_capability)
        record = qualifier.build_runtime_qualification_record(
            qualifier.load_runtime_qualification_contract(), observation
        )
        record_raw = qualifier.serialize_runtime_qualification_record(record)
        _publish(capability, *paths["record"], record_raw)
    except Exception:
        receipt = _receipt(
            authority, authority_sha, claim, claim_sha, evidence, evidence_sha, None
        )
        primitives.validate_artificial_terminal_execution_receipt(
            authority, claim, evidence, receipt,
            authority_sha, claim_sha, evidence_sha, None,
        )
        _publish(capability, *paths["receipt"], primitives.canonical_json_bytes(receipt))
        raise

    receipt = _receipt(
        authority, authority_sha, claim, claim_sha, evidence, evidence_sha, record
    )
    primitives.validate_artificial_terminal_execution_receipt(
        authority, claim, evidence, receipt,
        authority_sha, claim_sha, evidence_sha, record,
    )
    receipt_raw = primitives.canonical_json_bytes(receipt)
    _publish(capability, *paths["receipt"], receipt_raw)
    return {
        "activation_id": ACTIVATION_ID,
        "authority_raw_sha256": authority_sha,
        "claim_id": claim["claim_id"],
        "claim_raw_sha256": claim_sha,
        "observer_entry_evidence_id": evidence["observer_entry_evidence_id"],
        "observer_entry_evidence_raw_sha256": evidence_sha,
        "runtime_record_raw_sha256": receipt["runtime_record_raw_sha256"],
        "receipt_raw_sha256": hashlib.sha256(receipt_raw).hexdigest(),
        "terminal_status": receipt["terminal_status"],
        "observer_invocation_count": 1,
        "retry_allowed": False,
    }


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("H26 runtime qualification accepts no arguments")
    result = execute_h26_runtime_qualification_once()
    print(json.dumps(result, sort_keys=True, separators=(",", ":")), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
