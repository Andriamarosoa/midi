#!/usr/bin/env python3
"""Dormant one-shot creator for the exact H27 administrative root on macOS."""
from __future__ import annotations

import errno
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Mapping, Optional


ACK_ENV = "H27_ADMIN_ROOT_CREATE_EXECUTE"
GIT_DATABASE = Path("/Users/amcarene/midi-worker/repository/.git")
PARENT = Path("/Users/amcarene")
TARGET_LEAF = "h27-admin"
TARGET = PARENT / TARGET_LEAF

ROOT_IDENTITIES = (
    {"path":"configs/harmonic_censoring_h27_admin_root_creation_contract_identity_binding.json","git_blob_sha1":"4ecb86e7e14e80ee276c6b9a8ca300de2981e127","size_bytes":3541,"raw_sha256":"1efcd187908ae791bb8740e659cc327b11c31f56af194bafffb8e498adeab0c9"},
    {"path":"configs/harmonic_censoring_h27_admin_root_creation_contract_identity_binding_external_seal.json","git_blob_sha1":"7c0c8ee64f4f684c1aff63b1c37089d720d19f29","size_bytes":1282,"raw_sha256":"d1d4c3f5d47d6585cd85578b20580e29386667b9397fcb1b96681cb34128d302"},
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def identity_ok(identity: Mapping[str, object], raw: bytes) -> bool:
    return (
        tuple(key for key in ("path", "git_blob_sha1", "size_bytes", "raw_sha256") if key in identity)
        == ("path", "git_blob_sha1", "size_bytes", "raw_sha256")
        and type(identity["path"]) is str
        and type(identity["git_blob_sha1"]) is str
        and type(identity["size_bytes"]) is int
        and type(identity["raw_sha256"]) is str
        and len(raw) == identity["size_bytes"]
        and git_blob(raw) == identity["git_blob_sha1"]
        and sha256(raw) == identity["raw_sha256"]
    )


def read_blob(blob_sha1: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", blob_sha1) is None:
        raise PermissionError("H27 malformed Git blob identity.")
    result = subprocess.run(
        ["git", f"--git-dir={GIT_DATABASE}", "cat-file", "blob", blob_sha1],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if result.returncode != 0:
        raise PermissionError("H27 exact Git blob unavailable.")
    return result.stdout


def parse_object(raw: bytes, label: str) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        parsed: dict[str, object] = {}
        for key, value in values:
            if key in parsed:
                raise PermissionError(f"H27 duplicate JSON key in {label}.")
            parsed[key] = value
        return parsed

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PermissionError(f"H27 invalid JSON in {label}.") from exc
    if type(value) is not dict:
        raise PermissionError(f"H27 {label} must be a JSON object.")
    return value


def exact_identity_list(value: object, count: int, label: str) -> list[dict[str, object]]:
    if type(value) is not list or len(value) != count or any(type(item) is not dict for item in value):
        raise PermissionError(f"H27 {label} identity set mismatch.")
    return value


def require_environment() -> None:
    if sys.platform != "darwin" or os.environ.get(ACK_ENV) != "1" or len(sys.argv) != 1:
        raise PermissionError("H27 exact macOS one-shot acknowledgement required.")
    if not hasattr(os, "O_NOFOLLOW"):
        raise PermissionError("H27 no-follow access unavailable.")


def require_git_database() -> None:
    if GIT_DATABASE.resolve(strict=True) != GIT_DATABASE or GIT_DATABASE.is_symlink():
        raise PermissionError("H27 exact Git object database realpath mismatch.")


def verify_identity_graph() -> dict[str, bytes]:
    require_git_database()
    roots: dict[str, bytes] = {}
    for identity in ROOT_IDENTITIES:
        raw = read_blob(str(identity["git_blob_sha1"]))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 root identity mismatch: {identity['path']}.")
        roots[str(identity["path"])] = raw
    binding = parse_object(roots[str(ROOT_IDENTITIES[0]["path"])], "admin-root contract binding")
    seal = parse_object(roots[str(ROOT_IDENTITIES[1]["path"])], "admin-root contract binding seal")
    if seal.get("identity_binding") != ROOT_IDENTITIES[0]:
        raise PermissionError("H27 admin-root binding seal mismatch.")
    identities = [
        binding.get("reviewed_contract"),
        binding.get("contract_external_seal"),
        *exact_identity_list(binding.get("reviewed_predecessor_chain"), 3, "predecessor"),
    ]
    if any(type(identity) is not dict for identity in identities):
        raise PermissionError("H27 malformed bound identity.")
    paths = [identity.get("path") for identity in identities]
    if len(identities) != 5 or any(type(path) is not str for path in paths) or len(set(paths)) != 5:
        raise PermissionError("H27 requires exactly five unique contract identities.")
    if binding.get("transitive_identity_binding") != {
        "combined_unique_path_count": 5,
        "all_five_identities_must_be_rehashed": True,
        "duplicates_forbidden": True,
        "path_or_identity_drift_forbidden": True,
    }:
        raise PermissionError("H27 transitive identity contract mismatch.")
    verified = dict(roots)
    for identity in identities:
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 identity mismatch: {identity.get('path')}.")
        verified[str(identity["path"])] = raw
    if len(verified) != 7:
        raise PermissionError("H27 requires exactly seven unique preflight identities.")
    return verified


def open_verified_parent() -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(PARENT, flags)
    try:
        descriptor = os.fstat(fd)
        named = os.stat(PARENT, follow_symlinks=False)
        if (
            PARENT.resolve(strict=True) != PARENT
            or PARENT.is_symlink()
            or not stat.S_ISDIR(descriptor.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or (descriptor.st_dev, descriptor.st_ino) != (named.st_dev, named.st_ino)
        ):
            raise PermissionError("H27 parent realpath or identity mismatch.")
        return fd
    except BaseException:
        os.close(fd)
        raise


def require_parent_fd_still_named(fd: int) -> None:
    descriptor = os.fstat(fd)
    named = os.stat(PARENT, follow_symlinks=False)
    if (
        PARENT.resolve(strict=True) != PARENT
        or PARENT.is_symlink()
        or not stat.S_ISDIR(descriptor.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (descriptor.st_dev, descriptor.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise PermissionError("H27 parent identity changed.")


def probe_target_absence_once(parent_fd: int) -> None:
    try:
        os.stat(TARGET_LEAF, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(errno.EEXIST, "H27 administrative root already exists.", TARGET_LEAF)


def open_created_leaf(parent_fd: int) -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    return os.open(TARGET_LEAF, flags, dir_fd=parent_fd)


def verify_created_leaf(parent_fd: int, leaf_fd: int) -> tuple[int, int]:
    descriptor = os.fstat(leaf_fd)
    named = os.stat(TARGET_LEAF, dir_fd=parent_fd, follow_symlinks=False)
    if (
        not stat.S_ISDIR(descriptor.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (descriptor.st_dev, descriptor.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise PermissionError("H27 created administrative root identity mismatch.")
    return descriptor.st_dev, descriptor.st_ino


def create() -> dict[str, object]:
    verified = verify_identity_graph()
    require_environment()
    parent_fd = open_verified_parent()
    leaf_fd: Optional[int] = None
    try:
        probe_target_absence_once(parent_fd)
        require_parent_fd_still_named(parent_fd)

        # First and only irreversible effect.  No cleanup, repair, or retry
        # follows any failure, including a failure after this exact mkdir.
        os.mkdir(TARGET_LEAF, mode=0o700, dir_fd=parent_fd)
        os.fsync(parent_fd)
        leaf_fd = open_created_leaf(parent_fd)
        device, inode = verify_created_leaf(parent_fd, leaf_fd)
        require_parent_fd_still_named(parent_fd)
    finally:
        if leaf_fd is not None:
            os.close(leaf_fd)
        os.close(parent_fd)
    return {
        "status": "H27_ADMIN_ROOT_CREATED_TERMINAL_SUCCESS",
        "verified_identity_count": len(verified),
        "target_path": str(TARGET),
        "target_device": device,
        "target_inode": inode,
        "publisher_authorization_consumed": False,
        "creator_child_created": False,
        "registry_opened": False,
        "control_bundle_created": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(create(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
