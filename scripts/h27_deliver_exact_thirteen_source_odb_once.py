#!/usr/bin/env python3
"""Deliver the reviewed self-contained H27 receiver over one SSH invocation."""
from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
from typing import Mapping


REPOSITORY = Path(r"C:\Users\user\Desktop\midi\.git")
RECEIVER_OID = "9d32cac8ddb29e43975a6b82f5c1c39a91f93df4"
RECEIVER_SIZE = 119406
RECEIVER_SHA256 = "996c4539a357b13af65012de84ed836179389f111dd1849eb1ca165d15374000"
SSH_COMMAND = (
    "ssh", "-T", "amcarene@100.89.128.87", "env",
    "H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1", "/usr/bin/python3", "-",
)
SSH_TIMEOUT_SECONDS = 900
TERMINAL_STATUS = "H27_SOURCE_ODB_EXACT_THIRTEEN_BLOB_DELIVERY_TERMINAL_SUCCESS"
SOURCE_GIT_DATABASE = "/Users/amcarene/midi/.git"
IDENTITY_KEYS = {"path", "git_blob_sha1", "size_bytes", "raw_sha256", "base64"}
TERMINAL_KEYS = {
    "status", "object_count", "object_blob_ids", "source_git_database",
    "head_unchanged", "symbolic_head_unchanged", "regular_refs_unchanged",
    "root_refs_and_pseudorefs_unchanged", "index_unchanged", "worktree_clean",
    "target_odb_changed", "import_executed", "detach_executed",
    "downstream_executed", "science_or_locked_test",
}


class ConsumedDeliveryFailure(RuntimeError):
    """The single SSH began and its result was not a valid terminal success."""


def clean_environment() -> dict[str, str]:
    environment = {
        key: value for key, value in os.environ.items()
        if not key.upper().startswith("GIT_")
    }
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_NO_LAZY_FETCH"] = "1"
    return environment


def require_windows_and_zero_arguments() -> None:
    if platform.system().lower() != "windows":
        raise PermissionError("H27 source delivery requires Windows")
    if len(sys.argv) != 1:
        raise PermissionError("H27 source delivery accepts zero arguments")
    if REPOSITORY.resolve(strict=True) != Path(r"C:\Users\user\Desktop\midi\.git").resolve(strict=True):
        raise PermissionError("source Git database realpath mismatch")


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def read_receiver_blob() -> bytes:
    result = subprocess.run(
        (
            "git", "--no-optional-locks", "--no-replace-objects",
            f"--git-dir={REPOSITORY}", "cat-file", "blob", RECEIVER_OID,
        ),
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=clean_environment(), shell=False,
    )
    if result.returncode != 0 or result.stderr != b"":
        raise PermissionError("exact receiver Git blob unavailable")
    raw = result.stdout
    if (
        len(raw) != RECEIVER_SIZE
        or git_blob_id(raw) != RECEIVER_OID
        or hashlib.sha256(raw).hexdigest() != RECEIVER_SHA256
    ):
        raise PermissionError("exact receiver identity mismatch")
    return raw


def embedded_blob_ids(receiver_raw: bytes) -> tuple[str, ...]:
    tree = ast.parse(receiver_raw.decode("utf-8"), filename="reviewed_receiver.py")
    values: object | None = None
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "EMBEDDED_OBJECTS"
        ):
            if values is not None:
                raise ValueError("duplicate EMBEDDED_OBJECTS assignment")
            values = ast.literal_eval(node.value)
    if not isinstance(values, tuple) or len(values) != 13:
        raise ValueError("receiver must embed exactly thirteen objects")
    blob_ids: list[str] = []
    paths: list[str] = []
    for item in values:
        if not isinstance(item, dict) or set(item) != IDENTITY_KEYS:
            raise ValueError("receiver embedded identity key set mismatch")
        oid = item["git_blob_sha1"]
        path = item["path"]
        if not isinstance(oid, str) or re.fullmatch(r"[0-9a-f]{40}", oid) is None:
            raise ValueError("receiver embedded blob ID invalid")
        if not isinstance(path, str) or not path:
            raise ValueError("receiver embedded path invalid")
        blob_ids.append(oid)
        paths.append(path)
    if len(set(blob_ids)) != 13 or len(set(paths)) != 13:
        raise ValueError("receiver embedded identities must be unique")
    return tuple(blob_ids)


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_terminal_report(stdout: bytes, expected_blob_ids: tuple[str, ...]) -> dict[str, object]:
    if stdout.count(b"\n") != 1 or not stdout.endswith(b"\n"):
        raise ConsumedDeliveryFailure("receiver stdout is not exactly one JSON line")

    def reject_constant(value: str) -> object:
        raise ValueError(f"non-finite JSON value: {value}")

    try:
        report = json.loads(
            stdout.decode("utf-8"), object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_constant,
        )
    except (UnicodeDecodeError, ValueError, json.JSONDecodeError) as error:
        raise ConsumedDeliveryFailure("receiver terminal JSON invalid") from error
    if not isinstance(report, dict) or set(report) != TERMINAL_KEYS:
        raise ConsumedDeliveryFailure("receiver terminal key set mismatch")
    expected: Mapping[str, object] = {
        "status": TERMINAL_STATUS,
        "object_count": 13,
        "object_blob_ids": list(expected_blob_ids),
        "source_git_database": SOURCE_GIT_DATABASE,
        "head_unchanged": True,
        "symbolic_head_unchanged": True,
        "regular_refs_unchanged": True,
        "root_refs_and_pseudorefs_unchanged": True,
        "index_unchanged": True,
        "worktree_clean": True,
        "target_odb_changed": False,
        "import_executed": False,
        "detach_executed": False,
        "downstream_executed": False,
        "science_or_locked_test": False,
    }
    if report != expected:
        raise ConsumedDeliveryFailure("receiver terminal values mismatch")
    return report


def deliver_once() -> dict[str, object]:
    require_windows_and_zero_arguments()
    receiver_raw = read_receiver_blob()
    expected_blob_ids = embedded_blob_ids(receiver_raw)
    try:
        result = subprocess.run(
            SSH_COMMAND, input=receiver_raw, check=False,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            env=clean_environment(), shell=False, timeout=SSH_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired) as error:
        raise ConsumedDeliveryFailure("single SSH failed or timed out; retry forbidden") from error
    if result.returncode != 0:
        raise ConsumedDeliveryFailure(f"single SSH returned {result.returncode}; retry forbidden")
    if result.stderr != b"":
        raise ConsumedDeliveryFailure("single SSH emitted stderr; retry forbidden")
    remote = parse_terminal_report(result.stdout, expected_blob_ids)
    return {
        "status": "H27_SOURCE_ODB_EXACT_THIRTEEN_DELIVERY_LOCAL_TERMINAL_SUCCESS_STOP",
        "ssh_invocation_count": 1,
        "receiver_git_blob_sha1": RECEIVER_OID,
        "receiver_size_bytes": RECEIVER_SIZE,
        "receiver_raw_sha256": RECEIVER_SHA256,
        "remote_status": remote["status"],
        "object_count": remote["object_count"],
        "object_blob_ids": remote["object_blob_ids"],
        "source_git_database": remote["source_git_database"],
        "source_odb_changed": True,
        "target_odb_changed": False,
        "import_executed": False,
        "detach_executed": False,
        "downstream_executed": False,
        "science_or_locked_test": False,
    }


def main() -> int:
    print(json.dumps(deliver_once(), ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
