#!/usr/bin/env python3
"""Dormant corrected one-shot creator for the exact H27 control parent."""
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


ACK_ENV = "H27_CONTROL_PARENT_CREATE_EXECUTE"
GIT_DATABASE = Path("/Users/amcarene/midi-worker/repository/.git")
PARENT = Path("/Users/amcarene/h27-admin")
PARENT_DEVICE = 16777234
PARENT_INODE = 1445438
TARGET_LEAF = "control"
TARGET = PARENT / TARGET_LEAF
STALE_RUNNER_BLOB = "96df05111a5e40a418e12fb2b3db4bd9516bcab3"

ROOT_IDENTITIES = (
    {"path":"configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract_identity_binding.json","git_blob_sha1":"6a7fb83658d07a9c553e9bb66852652894f46b14","size_bytes":5067,"raw_sha256":"5c35433aea01fc8ca2772289d4a2bd3ca291161e16625abaeff4e8d73dc7d5f3"},
    {"path":"configs/harmonic_censoring_h27_control_parent_identity_drift_correction_contract_identity_binding_external_seal.json","git_blob_sha1":"f847de69400b7a2ea57e395c684448b39bc7d9c9","size_bytes":2221,"raw_sha256":"d0d7dd7403ad91fd375ea2516b8bf966a59ffb672bc5e14b883464310e9b96d2"},
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
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise PermissionError("H27 no-follow directory access unavailable.")


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
    binding = parse_object(roots[str(ROOT_IDENTITIES[0]["path"])], "corrective binding")
    seal = parse_object(roots[str(ROOT_IDENTITIES[1]["path"])], "corrective binding seal")
    if seal.get("identity_binding") != ROOT_IDENTITIES[0]:
        raise PermissionError("H27 corrective binding seal mismatch.")
    identities = [
        binding.get("reviewed_correction_contract"),
        binding.get("correction_contract_external_seal"),
        *exact_identity_list(binding.get("bound_historical_identities"), 7, "historical"),
    ]
    if any(type(identity) is not dict for identity in identities):
        raise PermissionError("H27 malformed bound identity.")
    paths = [identity.get("path") for identity in identities]
    if len(identities) != 9 or any(type(path) is not str for path in paths) or len(set(paths)) != 9:
        raise PermissionError("H27 requires exactly nine unique bound identities.")
    if binding.get("identity_graph") != {
        "unique_path_count": 9,
        "correction_contract_and_seal_bound": True,
        "all_seven_historical_identities_rebound": True,
        "duplicates_forbidden": True,
        "path_or_identity_drift_forbidden": True,
        "acyclic": True,
        "self_hash_present": False,
        "historical_back_reference_present": False,
    }:
        raise PermissionError("H27 corrective identity graph mismatch.")
    stale = binding.get("bound_stale_runner_state")
    if stale != {
        "runner_git_blob_sha1": STALE_RUNNER_BLOB,
        "execution_authorization_revoked": True,
        "executable": False,
        "executed": False,
        "consumed": False,
        "acknowledgement_set": False,
        "mkdir_attempted": False,
    }:
        raise PermissionError("H27 stale runner state mismatch.")
    verified = dict(roots)
    for identity in identities:
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 identity mismatch: {identity.get('path')}.")
        verified[str(identity["path"])] = raw
    if len(verified) != 11:
        raise PermissionError("H27 requires exactly eleven unique preflight identities.")
    return verified


def require_parent_fd_still_named(fd: int) -> None:
    descriptor = os.fstat(fd)
    named = os.stat(PARENT, follow_symlinks=False)
    if (
        PARENT.resolve(strict=True) != PARENT
        or PARENT.is_symlink()
        or not stat.S_ISDIR(descriptor.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (descriptor.st_dev, descriptor.st_ino) != (PARENT_DEVICE, PARENT_INODE)
        or (named.st_dev, named.st_ino) != (PARENT_DEVICE, PARENT_INODE)
    ):
        raise PermissionError("H27 corrected parent identity mismatch.")


def open_verified_parent() -> int:
    fd = os.open(PARENT, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY)
    try:
        require_parent_fd_still_named(fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def probe_target_absence_once(parent_fd: int) -> None:
    try:
        os.stat(TARGET_LEAF, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(errno.EEXIST, "H27 control parent already exists.", TARGET_LEAF)


def open_created_leaf(parent_fd: int) -> int:
    return os.open(TARGET_LEAF, os.O_RDONLY | os.O_NOFOLLOW | os.O_DIRECTORY, dir_fd=parent_fd)


def verify_created_leaf(parent_fd: int, leaf_fd: int) -> tuple[int, int]:
    descriptor = os.fstat(leaf_fd)
    named = os.stat(TARGET_LEAF, dir_fd=parent_fd, follow_symlinks=False)
    if (
        not stat.S_ISDIR(descriptor.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or stat.S_IMODE(descriptor.st_mode) != 0o700
        or stat.S_IMODE(named.st_mode) != 0o700
        or (descriptor.st_dev, descriptor.st_ino) != (named.st_dev, named.st_ino)
    ):
        raise PermissionError("H27 created control parent identity or mode mismatch.")
    return descriptor.st_dev, descriptor.st_ino


def create() -> dict[str, object]:
    verified = verify_identity_graph()
    require_environment()
    parent_fd = open_verified_parent()
    leaf_fd: Optional[int] = None
    try:
        probe_target_absence_once(parent_fd)
        require_parent_fd_still_named(parent_fd)

        # First and only irreversible effect. No cleanup, repair, or retry
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
        "status": "H27_CONTROL_PARENT_CORRECTED_CREATED_TERMINAL_SUCCESS",
        "verified_identity_count": len(verified),
        "stale_runner_git_blob_sha1": STALE_RUNNER_BLOB,
        "stale_runner_executed": False,
        "stale_runner_consumed": False,
        "parent_path": str(PARENT),
        "parent_device": PARENT_DEVICE,
        "parent_inode": PARENT_INODE,
        "target_path": str(TARGET),
        "target_device": device,
        "target_inode": inode,
        "registry_opened": False,
        "authority_reserved": False,
        "authority_consumed": False,
        "creator_entrypoint_executed": False,
        "control_bundle_created": False,
        "constructor_or_materializer_executed": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(create(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
