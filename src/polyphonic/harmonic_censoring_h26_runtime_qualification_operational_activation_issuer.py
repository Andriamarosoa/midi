"""Create-once publisher for one prevalidated H26 activation.

The generic publisher remains independently testable with a fake adapter. The
POSIX adapter is the reviewed operational boundary for macOS; constructing it
does not write anything, and the activation directory must already exist.
"""
from __future__ import annotations

import ctypes
import os
from pathlib import Path
import stat
from dataclasses import dataclass
from typing import Protocol

from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner import H26ActivationIssuancePlan

class H26IssuanceFilesystemAdapter(Protocol):
    def exists(self, path: str) -> bool: ...
    def create_exclusive(self, path: str, data: bytes) -> None: ...
    def sync_file(self, path: str) -> None: ...
    def rename_no_replace(self, source: str, destination: str) -> None: ...
    def sync_directory(self, path: str) -> None: ...

@dataclass(frozen=True)
class H26ActivationIssuanceReceipt:
    activation_id: str
    activation_raw_sha256: str
    final_path: str
    published: bool


_AT_FDCWD = -2
_RENAME_EXCL = 0x00000004


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


class H26PosixIssuanceFilesystemAdapter:
    """Narrow macOS adapter limited to the two paths in one issuance plan."""

    def __init__(self, administrative_root: str) -> None:
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
        self._root = str(root)
        self._activation_dir = str(activation_dir)
        self._final = str(activation_dir / "activation.json")
        self._staging = str(activation_dir / ".activation.json.staging")

    def _require_file_path(self, path: str) -> None:
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

def publish_prevalidated_activation_with_adapter(plan: H26ActivationIssuancePlan, adapter: H26IssuanceFilesystemAdapter) -> H26ActivationIssuanceReceipt:
    """Apply create-once/no-replace semantics through a caller-supplied adapter."""
    if type(plan) is not H26ActivationIssuancePlan:
        raise TypeError("exact H26ActivationIssuancePlan required")
    if adapter.exists(plan.final_path) or adapter.exists(plan.staging_path):
        raise FileExistsError("terminal activation issuance collision")
    adapter.create_exclusive(plan.staging_path, plan.canonical_bytes)
    adapter.sync_file(plan.staging_path)
    adapter.rename_no_replace(plan.staging_path, plan.final_path)
    adapter.sync_directory(f"{plan.administrative_root}/activation")
    return H26ActivationIssuanceReceipt(plan.activation_id, plan.activation_raw_sha256, plan.final_path, True)

__all__ = [
    "H26ActivationIssuanceReceipt",
    "H26IssuanceFilesystemAdapter",
    "H26PosixIssuanceFilesystemAdapter",
    "publish_prevalidated_activation_with_adapter",
]
