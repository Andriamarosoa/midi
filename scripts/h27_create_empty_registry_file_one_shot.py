#!/usr/bin/env python3
"""Dormant one-shot creator for the exact empty H27 registry JSONL on macOS."""
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


ACK_ENV = "H27_REGISTRY_FILE_CREATE_EXECUTE"
GIT_DATABASE = Path("/Users/amcarene/midi-worker/repository/.git")
PARENT_TEXT = "/Users/amcarene/h27-admin/registry"
TARGET_TEXT = "/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl"
PARENT = Path(PARENT_TEXT)
PARENT_EXPECTED_DEVICE = 16777233
PARENT_EXPECTED_INODE = 1448669
TARGET_LEAF = "h27-control-bundle-creation-authority-v1.jsonl"
TARGET = Path(TARGET_TEXT)

ROOT_IDENTITIES = (
    {"path":"configs/harmonic_censoring_h27_registry_file_creation_contract_identity_binding.json","git_blob_sha1":"30e013f3dec986b031eed5a08c1b2f537742b5fb","size_bytes":3930,"raw_sha256":"8d7131482ee43c7ac19cbdf1a3e9c24ac3700b784712ec07870f68581c7929db"},
    {"path":"configs/harmonic_censoring_h27_registry_file_creation_contract_identity_binding_external_seal.json","git_blob_sha1":"f7abe0b02a4b721a9a28c15e25f94e099932e178","size_bytes":2212,"raw_sha256":"15beb864045f9cacce11bae5f07a360e155fe4a7d8394e6f10d3bdd094187cda"},
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
    binding = parse_object(roots[str(ROOT_IDENTITIES[0]["path"])], "registry-file contract binding")
    seal = parse_object(roots[str(ROOT_IDENTITIES[1]["path"])], "registry-file contract binding seal")
    if seal.get("identity_binding") != ROOT_IDENTITIES[0]:
        raise PermissionError("H27 registry-file binding seal mismatch.")
    if binding.get("bound_future_registry_file") != {
        "parent_path_exact": PARENT_TEXT,
        "parent_device_exact": PARENT_EXPECTED_DEVICE,
        "parent_inode_exact": PARENT_EXPECTED_INODE,
        "target_path_exact": TARGET_TEXT,
        "initial_size_bytes_exact": 0,
        "nlink_exact": 1,
        "mode_exact_octal": "0600",
        "acknowledgement_environment_exact": "H27_REGISTRY_FILE_CREATE_EXECUTE=1",
        "static_preflight_count": 4,
        "creation_step_count": 9,
        "creation_rule_count": 18,
        "runner_requirement_count": 7,
    }:
        raise PermissionError("H27 registry-file execution contract mismatch.")
    if binding.get("bound_authority_state") != {
        "registry_leaf_creation_authority_terminally_consumed": True,
        "registry_leaf_runner_retry_forbidden": True,
        "registry_leaf_exists": True,
        "registry_file_creation_authority_reserved": False,
        "registry_file_creation_authority_consumed": False,
    }:
        raise PermissionError("H27 registry-file authority state mismatch.")
    if binding.get("identity_graph") != {
        "unique_path_count": 6,
        "reviewed_contract_and_seal_bound": True,
        "all_four_contract_predecessors_rebound": True,
        "acyclic": True,
        "self_hash_present": False,
        "historical_back_reference_present": False,
    }:
        raise PermissionError("H27 registry-file identity graph mismatch.")
    identities = [
        binding.get("reviewed_contract"),
        binding.get("contract_external_seal"),
        *exact_identity_list(binding.get("bound_predecessor_identities"), 4, "registry-file predecessor"),
    ]
    if any(type(identity) is not dict for identity in identities):
        raise PermissionError("H27 malformed bound identity.")
    paths = [identity.get("path") for identity in identities]
    if len(identities) != 6 or any(type(path) is not str for path in paths) or len(set(paths)) != 6:
        raise PermissionError("H27 requires exactly six unique contract identities.")
    verified = dict(roots)
    for identity in identities:
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 identity mismatch: {identity.get('path')}.")
        verified[str(identity["path"])] = raw
    if len(verified) != 8:
        raise PermissionError("H27 requires exactly eight unique preflight identities.")
    return verified


def parent_identity_ok(descriptor: os.stat_result, named: os.stat_result) -> bool:
    expected = (PARENT_EXPECTED_DEVICE, PARENT_EXPECTED_INODE)
    return (
        stat.S_ISDIR(descriptor.st_mode)
        and stat.S_ISDIR(named.st_mode)
        and (descriptor.st_dev, descriptor.st_ino) == expected
        and (named.st_dev, named.st_ino) == expected
    )


def open_verified_parent() -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(PARENT, flags)
    try:
        descriptor = os.fstat(fd)
        named = os.stat(PARENT, follow_symlinks=False)
        if PARENT.resolve(strict=True) != PARENT or PARENT.is_symlink() or not parent_identity_ok(descriptor, named):
            raise PermissionError("H27 registry parent terminal identity mismatch.")
        return fd
    except BaseException:
        os.close(fd)
        raise


def require_parent_fd_still_named(fd: int) -> None:
    descriptor = os.fstat(fd)
    named = os.stat(PARENT, follow_symlinks=False)
    if PARENT.resolve(strict=True) != PARENT or PARENT.is_symlink() or not parent_identity_ok(descriptor, named):
        raise PermissionError("H27 registry parent identity changed.")


def probe_target_absence_once(parent_fd: int) -> None:
    try:
        os.stat(TARGET_LEAF, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(errno.EEXIST, "H27 registry file already exists.", TARGET_LEAF)


def exact_empty_regular_file(descriptor: os.stat_result) -> bool:
    return (
        stat.S_ISREG(descriptor.st_mode)
        and descriptor.st_nlink == 1
        and descriptor.st_size == 0
        and stat.S_IMODE(descriptor.st_mode) == 0o600
    )


def require_file_identity(parent_fd: int, file_fd: int, expected: Optional[tuple[int, int]] = None) -> tuple[int, int]:
    descriptor = os.fstat(file_fd)
    named = os.stat(TARGET_LEAF, dir_fd=parent_fd, follow_symlinks=False)
    identity = (descriptor.st_dev, descriptor.st_ino)
    if (
        not exact_empty_regular_file(descriptor)
        or not exact_empty_regular_file(named)
        or identity != (named.st_dev, named.st_ino)
        or (expected is not None and identity != expected)
    ):
        raise PermissionError("H27 exact empty registry-file identity mismatch.")
    return identity


def create() -> dict[str, object]:
    verified = verify_identity_graph()
    require_environment()
    parent_fd = open_verified_parent()
    created_fd: Optional[int] = None
    reopened_fd: Optional[int] = None
    try:
        probe_target_absence_once(parent_fd)
        require_parent_fd_still_named(parent_fd)

        # First and only irreversible effect. No cleanup, repair, or retry
        # follows any failure, including a failure after this exclusive open.
        created_fd = os.open(
            TARGET_LEAF,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        os.fsync(created_fd)
        target_device, target_inode = require_file_identity(parent_fd, created_fd)
        os.fsync(parent_fd)
        reopened_fd = os.open(TARGET_LEAF, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
        require_file_identity(parent_fd, reopened_fd, (target_device, target_inode))
        require_parent_fd_still_named(parent_fd)
    finally:
        if reopened_fd is not None:
            os.close(reopened_fd)
        if created_fd is not None:
            os.close(created_fd)
        os.close(parent_fd)
    return {
        "status": "H27_EMPTY_REGISTRY_FILE_CREATED_TERMINAL_SUCCESS",
        "verified_identity_count": len(verified),
        "parent_path": PARENT_TEXT,
        "parent_device": PARENT_EXPECTED_DEVICE,
        "parent_inode": PARENT_EXPECTED_INODE,
        "target_path": TARGET_TEXT,
        "target_device": target_device,
        "target_inode": target_inode,
        "target_size_bytes": 0,
        "target_nlink": 1,
        "target_mode_octal": "0600",
        "registry_leaf_creation_authority_consumed": True,
        "registry_file_creation_authority_consumed": True,
        "registry_record_written": False,
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
