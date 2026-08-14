#!/usr/bin/env python3
"""Dormant one-shot creator for the exact H27 registry leaf on macOS."""
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


ACK_ENV = "H27_REGISTRY_LEAF_CREATE_EXECUTE"
GIT_DATABASE = Path("/Users/amcarene/midi-worker/repository/.git")
PARENT = Path("/Users/amcarene/h27-admin")
PARENT_EXPECTED_DEVICE = 16777233
PARENT_EXPECTED_INODE = 1445438
TARGET_LEAF = "registry"
TARGET = PARENT / TARGET_LEAF

ROOT_IDENTITIES = (
    {"path":"configs/harmonic_censoring_h27_registry_leaf_creation_contract_identity_binding.json","git_blob_sha1":"5a48c974f5ada84378a5f9010f24436e61a7968a","size_bytes":3787,"raw_sha256":"96adb1dcf9b024d8c62e319c5a1c0c19cce541165e568c2c138442c3a4454d27"},
    {"path":"configs/harmonic_censoring_h27_registry_leaf_creation_contract_identity_binding_external_seal.json","git_blob_sha1":"f21eccb486b1fd7dfdd3ded43ba732a85561b54b","size_bytes":2078,"raw_sha256":"0723b935874e3e240a36c3b6a11976df320c70ce3b30692c74eaec7f1b0531f7"},
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
    binding = parse_object(roots[str(ROOT_IDENTITIES[0]["path"])], "registry-leaf contract binding")
    seal = parse_object(roots[str(ROOT_IDENTITIES[1]["path"])], "registry-leaf contract binding seal")
    if seal.get("identity_binding") != ROOT_IDENTITIES[0]:
        raise PermissionError("H27 registry-leaf binding seal mismatch.")
    if binding.get("bound_future_registry_leaf") != {
        "platform_exact": "darwin",
        "acknowledgement_environment_exact": "H27_REGISTRY_LEAF_CREATE_EXECUTE=1",
        "arguments_forbidden": True,
        "parent_path_exact": "/Users/amcarene/h27-admin",
        "parent_expected_device_exact": PARENT_EXPECTED_DEVICE,
        "parent_expected_inode_exact": PARENT_EXPECTED_INODE,
        "parent_fd_and_named_entry_must_match_terminal_identity": True,
        "target_leaf_exact": "registry",
        "target_path_exact": "/Users/amcarene/h27-admin/registry",
        "static_preflight_count": 4,
        "one_shot_creation_step_count": 7,
        "creation_rule_count": 14,
        "future_runner_requirement_count": 7,
    }:
        raise PermissionError("H27 registry-leaf execution contract mismatch.")
    if binding.get("bound_authority_state") != {
        "admin_root_creation_authority_terminally_consumed": True,
        "admin_root_creator_retry_forbidden": True,
        "publisher_authority_terminally_consumed": True,
        "publisher_retry_forbidden": True,
        "reviewed_creator_source_published": True,
    }:
        raise PermissionError("H27 registry-leaf authority state mismatch.")
    if binding.get("identity_graph") != {
        "unique_path_count": 5,
        "reviewed_contract_and_seal_bound": True,
        "all_three_contract_predecessors_rebound": True,
        "acyclic": True,
        "self_hash_present": False,
        "historical_back_reference_present": False,
    }:
        raise PermissionError("H27 registry-leaf identity graph mismatch.")
    identities = [
        binding.get("reviewed_contract"),
        binding.get("contract_external_seal"),
        *exact_identity_list(binding.get("bound_predecessor_identities"), 3, "registry-leaf predecessor"),
    ]
    if any(type(identity) is not dict for identity in identities):
        raise PermissionError("H27 malformed bound identity.")
    paths = [identity.get("path") for identity in identities]
    if len(identities) != 5 or any(type(path) is not str for path in paths) or len(set(paths)) != 5:
        raise PermissionError("H27 requires exactly five unique contract identities.")
    verified = dict(roots)
    for identity in identities:
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 identity mismatch: {identity.get('path')}.")
        verified[str(identity["path"])] = raw
    if len(verified) != 7:
        raise PermissionError("H27 requires exactly seven unique preflight identities.")
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
    raise FileExistsError(errno.EEXIST, "H27 registry leaf already exists.", TARGET_LEAF)


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
        raise PermissionError("H27 created registry-leaf identity mismatch.")
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
        "status": "H27_REGISTRY_LEAF_CREATED_TERMINAL_SUCCESS",
        "verified_identity_count": len(verified),
        "parent_path": str(PARENT),
        "parent_device": PARENT_EXPECTED_DEVICE,
        "parent_inode": PARENT_EXPECTED_INODE,
        "target_path": str(TARGET),
        "target_device": device,
        "target_inode": inode,
        "admin_root_creation_authority_consumed": True,
        "publisher_authority_consumed": True,
        "registry_jsonl_observed": False,
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
