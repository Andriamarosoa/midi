"""STOP-1 entrypoint for one future H26 activation publication.

The command has no CLI arguments. It consumes caller-supplied canonical
activation bytes from stdin and can publish them only on the pre-registered
Mac root after explicit OS acknowledgement and exact clean-HEAD verification.
This module is implemented but must not be invoked before separate review.
"""
from __future__ import annotations

import ctypes
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Any, Iterable, Tuple
import weakref

from .harmonic_censoring_h26_runtime_execution_primitives import canonical_json_bytes
from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner import (
    plan_runtime_qualification_operational_activation_issuance,
)
from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuer import (
    publish_prevalidated_activation_with_adapter,
)

ADMINISTRATIVE_ROOT = "/Users/amcarene/h26-admin"
ISSUER_IDENTITY = "h26-execution-codex-mac-primary"
ISSUED_AT = "2026-08-12T12:00:00Z"
ACKNOWLEDGEMENT_VARIABLE = "H26_RUNTIME_ACTIVATION_ISSUANCE_EXECUTE"
AUTHORIZATION_COMMIT_VARIABLE = "H26_RUNTIME_ACTIVATION_AUTHORIZATION_COMMIT"
MAXIMUM_REQUEST_BYTES = 65536
ENTRYPOINT_CONTRACT_PATH = (
    "configs/harmonic_censoring_h26_runtime_activation_operational_entrypoint_contract.json"
)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")
_AT_FDCWD = -2
_RENAME_EXCL = 0x00000004
_BOUNDARY_CAPABILITIES: dict[int, weakref.ReferenceType["_H26ExecutionBoundaryCapability"]] = {}


class _H26ExecutionBoundaryCapability:
    __slots__ = ("head", "__weakref__")

    def __new__(cls):
        raise TypeError("H26 execution boundary capability has no public constructor")


def _require_boundary_capability(value: object) -> _H26ExecutionBoundaryCapability:
    reference = _BOUNDARY_CAPABILITIES.get(id(value))
    if (
        type(value) is not _H26ExecutionBoundaryCapability
        or reference is None
        or reference() is not value
    ):
        raise PermissionError("H26 operational filesystem requires an attested execution boundary")
    return value


def _darwin_rename_no_replace(source: str, destination: str) -> None:
    if os.name != "posix" or not hasattr(os, "uname") or os.uname().sysname != "Darwin":
        raise OSError("H26 operational activation publication requires Darwin renameatx_np")
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
        raise OSError(error, os.strerror(error), destination)


class _H26BoundaryGatedPosixIssuanceFilesystemAdapter:
    """Private macOS adapter constructible only with an attested boundary."""

    def __init__(
        self,
        capability: _H26ExecutionBoundaryCapability,
        administrative_root: str,
    ) -> None:
        _require_boundary_capability(capability)
        if capability.head != _git_output("rev-parse", "HEAD"):
            raise PermissionError("H26 boundary capability HEAD is stale")
        if type(administrative_root) is not str:
            raise TypeError("administrative_root must be a string")
        root = Path(administrative_root)
        if not root.is_absolute() or root == Path("/"):
            raise ValueError("administrative_root must be absolute and non-root")
        activation_dir = root / "activation"
        resolved_root = root.resolve(strict=True)
        resolved_activation_dir = activation_dir.resolve(strict=True)
        if resolved_root != root or resolved_activation_dir != activation_dir:
            raise ValueError("H26 administrative root and activation directory must not use symlinks")
        if not root.is_dir() or not activation_dir.is_dir():
            raise NotADirectoryError("H26 administrative root directories must already exist")
        self._capability = capability
        self._activation_dir = str(activation_dir)
        self._final = str(activation_dir / "activation.json")
        self._staging = str(activation_dir / ".activation.json.staging")

    def _require_live_boundary(self) -> None:
        capability = _require_boundary_capability(self._capability)
        if capability.head != _git_output("rev-parse", "HEAD"):
            raise PermissionError("H26 boundary capability HEAD changed")
        if _git_output("status", "--porcelain=v1"):
            raise PermissionError("H26 operational filesystem requires a clean worktree")

    def _require_file_path(self, path: str) -> None:
        self._require_live_boundary()
        if path not in (self._final, self._staging):
            raise ValueError("path is outside the fixed H26 activation slot")

    def exists(self, path: str) -> bool:
        self._require_file_path(path)
        return os.path.lexists(path)

    def create_exclusive(self, path: str, data: bytes) -> None:
        self._require_file_path(path)
        if path != self._staging:
            raise ValueError("only the fixed staging path may be created")
        if type(data) is not bytes:
            raise TypeError("activation data must be exact bytes")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            view = memoryview(data)
            while view:
                written = os.write(descriptor, view)
                if written <= 0:
                    raise OSError("short activation write")
                view = view[written:]
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def sync_file(self, path: str) -> None:
        self._require_file_path(path)
        if not stat.S_ISREG(os.lstat(path).st_mode):
            raise ValueError("activation staging evidence must be a regular file")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        descriptor = os.open(path, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    def rename_no_replace(self, source: str, destination: str) -> None:
        self._require_file_path(source)
        self._require_file_path(destination)
        if source != self._staging or destination != self._final:
            raise ValueError("H26 activation rename paths mismatch")
        _darwin_rename_no_replace(source, destination)

    def sync_directory(self, path: str) -> None:
        self._require_live_boundary()
        if path != self._activation_dir:
            raise ValueError("directory sync path mismatch")
        flags = os.O_RDONLY
        if hasattr(os, "O_DIRECTORY"):
            flags |= os.O_DIRECTORY
        descriptor = os.open(path, flags)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAXIMUM_REQUEST_BYTES:
        raise ValueError("activation request byte length mismatch")
    if b"\r" in raw or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("activation request must be canonical UTF-8 LF bytes")

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate activation request key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"non-integer activation JSON value forbidden: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid activation request JSON") from exc
    if type(value) is not dict:
        raise ValueError("activation request must be a JSON object")
    return value


def _git_output(*arguments: str) -> str:
    return subprocess.check_output(
        ("git", *arguments), cwd=_repo_root(), text=True, encoding="utf-8"
    ).strip()


def _load_entrypoint_contract() -> dict[str, Any]:
    raw = (_repo_root() / ENTRYPOINT_CONTRACT_PATH).resolve(strict=True).read_bytes()
    value = _strict_json_object(raw)
    expected = {
        "schema_identity": "H26_RUNTIME_ACTIVATION_OPERATIONAL_ENTRYPOINT_CONTRACT_V1",
        "schema_version": 1,
        "status": "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_ACTIVATION_CREATED",
        "approved_parent_commit": "fcb6992cfee5ef0cb9c1e09c8e52f9600e3419a4",
        "administrative_root": ADMINISTRATIVE_ROOT,
        "issuer_identity": ISSUER_IDENTITY,
        "issued_at": ISSUED_AT,
        "acknowledgement_variable": ACKNOWLEDGEMENT_VARIABLE,
        "authorization_commit_variable": AUTHORIZATION_COMMIT_VARIABLE,
        "request_transport": "exact canonical activation bytes on stdin",
        "required_platform": "Darwin",
        "requires_clean_head_equal_authorization_commit": True,
        "operational_adapter_boundary": "private adapter requires identity-attested capability minted only after execution boundary",
        "publication": "create-exclusive staging fsync renameatx_np(RENAME_EXCL) directory-fsync",
        "retry_allowed": False,
        "activation_created": False,
        "runtime_observed": False,
        "materialization_executed": False,
        "p0_executed": False,
        "p1_executed": False,
        "p2_executed": False,
        "locked_test_used": False,
        "next_action": "External review of this operational entrypoint before any administrative root or activation creation",
    }
    if value != expected:
        raise ValueError("H26 operational entrypoint contract mismatch")
    return value


def _require_execution_boundary() -> _H26ExecutionBoundaryCapability:
    _load_entrypoint_contract()
    if os.name != "posix" or not hasattr(os, "uname") or os.uname().sysname != "Darwin":
        raise RuntimeError("H26 activation issuance requires the reviewed macOS boundary")
    if os.environ.get(ACKNOWLEDGEMENT_VARIABLE) != "1":
        raise PermissionError("H26 activation issuance acknowledgement missing")
    authorization_commit = os.environ.get(AUTHORIZATION_COMMIT_VARIABLE)
    if type(authorization_commit) is not str or _COMMIT.fullmatch(authorization_commit) is None:
        raise PermissionError("H26 activation authorization commit missing")
    head = _git_output("rev-parse", "HEAD")
    if authorization_commit != head:
        raise PermissionError("H26 activation authorization commit must equal HEAD")
    if _git_output("status", "--porcelain=v1"):
        raise PermissionError("H26 activation issuance requires a clean worktree")
    capability = object.__new__(_H26ExecutionBoundaryCapability)
    capability.head = head
    identity = id(capability)

    def cleanup(reference):
        if _BOUNDARY_CAPABILITIES.get(identity) is reference:
            _BOUNDARY_CAPABILITIES.pop(identity, None)

    _BOUNDARY_CAPABILITIES[identity] = weakref.ref(capability, cleanup)
    return capability


def issue_h26_runtime_activation_once(raw_request: bytes):
    """Publish the exact caller-supplied activation after reversible checks."""
    capability = _require_execution_boundary()
    activation = _strict_json_object(raw_request)
    if activation.get("administrative_root") != ADMINISTRATIVE_ROOT:
        raise ValueError("pre-registered administrative_root mismatch")
    if activation.get("issuer_identity") != ISSUER_IDENTITY:
        raise ValueError("pre-registered issuer_identity mismatch")
    if activation.get("issued_at") != ISSUED_AT:
        raise ValueError("pre-registered issued_at mismatch")
    plan = plan_runtime_qualification_operational_activation_issuance(activation)
    if raw_request != plan.canonical_bytes or raw_request != canonical_json_bytes(activation):
        raise ValueError("activation request bytes are not canonical validator bytes")
    adapter = _H26BoundaryGatedPosixIssuanceFilesystemAdapter(
        capability, ADMINISTRATIVE_ROOT
    )
    return publish_prevalidated_activation_with_adapter(plan, adapter)


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("H26 activation issuance accepts no arguments")
    raw = sys.stdin.buffer.read(MAXIMUM_REQUEST_BYTES + 1)
    receipt = issue_h26_runtime_activation_once(raw)
    print(
        json.dumps(
            {
                "activation_id": receipt.activation_id,
                "activation_raw_sha256": receipt.activation_raw_sha256,
                "final_path": receipt.final_path,
                "published": receipt.published,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
