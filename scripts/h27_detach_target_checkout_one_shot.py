#!/usr/bin/env python3
"""Dormant one-shot H27 transition to the exact reviewed detached HEAD."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Mapping


ACK_ENV = "H27_TARGET_CHECKOUT_DETACH_EXECUTE"
CHECKOUT_TEXT = "/Users/amcarene/midi-worker/repository"
GIT_DATABASE_TEXT = "/Users/amcarene/midi-worker/repository/.git"
CHECKOUT = Path(CHECKOUT_TEXT)
GIT_DATABASE = Path(GIT_DATABASE_TEXT)
INITIAL_HEAD = "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf"
TARGET_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"

ROOT_IDENTITIES = (
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding.json","git_blob_sha1":"a514aa0270926dca1d8402ac84078a50754d2f17","size_bytes":4496,"raw_sha256":"c614d733121451c65134f480427a6d883013256633b123f34aa57f2a25f09f82"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding_external_seal.json","git_blob_sha1":"0f6a64b7477bde24968200a81d389b03a4a6ced0","size_bytes":2797,"raw_sha256":"bd187e4e692d0d36572d8d3e151e40682b528b03e584d6b9620b34267ffd133f"},
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


def clean_git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("GIT_"):
            del environment[key]
    environment["GIT_TERMINAL_PROMPT"] = "0"
    return environment


def read_blob(blob_sha1: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", blob_sha1) is None:
        raise PermissionError("H27 malformed Git blob identity.")
    result = subprocess.run(
        ["git", "--no-optional-locks", f"--git-dir={GIT_DATABASE_TEXT}", "cat-file", "blob", blob_sha1],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_git_environment(),
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


def require_platform_and_zero_arguments() -> None:
    if sys.platform != "darwin" or len(sys.argv) != 1 or os.environ.get(ACK_ENV) != "1":
        raise PermissionError("H27 exact macOS one-shot acknowledgement and zero arguments required.")


def verify_checkout_and_odb_realpaths() -> None:
    if (
        CHECKOUT.resolve(strict=True) != CHECKOUT
        or CHECKOUT.is_symlink()
        or not CHECKOUT.is_dir()
        or GIT_DATABASE.resolve(strict=True) != GIT_DATABASE
        or GIT_DATABASE.is_symlink()
        or not GIT_DATABASE.is_dir()
    ):
        raise PermissionError("H27 exact checkout or Git object database realpath mismatch.")


def verify_identity_graph() -> dict[str, bytes]:
    roots: dict[str, bytes] = {}
    for identity in ROOT_IDENTITIES:
        raw = read_blob(str(identity["git_blob_sha1"]))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 root identity mismatch: {identity['path']}.")
        roots[str(identity["path"])] = raw
    binding = parse_object(roots[str(ROOT_IDENTITIES[0]["path"])], "transition contract binding")
    seal = parse_object(roots[str(ROOT_IDENTITIES[1]["path"])], "transition contract binding seal")
    if seal.get("identity_binding") != ROOT_IDENTITIES[0]:
        raise PermissionError("H27 transition binding seal mismatch.")
    identities = [
        binding.get("reviewed_transition_contract"),
        binding.get("transition_contract_external_seal"),
        binding.get("reviewed_preflight_evidence"),
    ]
    if any(type(identity) is not dict for identity in identities):
        raise PermissionError("H27 malformed bound transition identity.")
    paths = [identity.get("path") for identity in identities]
    if len(paths) != 3 or any(type(path) is not str for path in paths) or len(set(paths)) != 3:
        raise PermissionError("H27 requires exactly three unique transition roots.")
    if binding.get("identity_graph") != {
        "unique_path_count": 3,
        "contract_seal_and_preflight_evidence_bound": True,
        "duplicates_forbidden": True,
        "path_or_identity_drift_forbidden": True,
        "acyclic": True,
        "self_hash_present": False,
        "historical_back_reference_present": False,
    }:
        raise PermissionError("H27 transition identity graph mismatch.")
    verified = dict(roots)
    for identity in identities:
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 transition identity mismatch: {identity.get('path')}.")
        verified[str(identity["path"])] = raw
    if len(verified) != 5:
        raise PermissionError("H27 requires exactly five unique predecessor identities.")
    contract_path = "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json"
    contract = parse_object(verified[contract_path], "reviewed transition contract")
    order = binding.get("bound_future_fail_closed_order")
    if (
        type(order) is not list
        or len(order) != 11
        or order != contract.get("future_fail_closed_order")
        or seal.get("future_fail_closed_order_exact") != contract.get("future_fail_closed_order")
    ):
        raise PermissionError("H27 exact fail-closed order binding mismatch.")
    return verified


def git_read(arguments: list[str], *, expected_returncodes: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null", "-C", CHECKOUT_TEXT, *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_git_environment(),
    )
    if result.returncode not in expected_returncodes:
        raise PermissionError(f"H27 Git read-only verification failed: {arguments[0]}.")
    return result


def current_head() -> str:
    return git_read(["rev-parse", "--verify", "HEAD"]).stdout.decode("ascii").strip()


def require_initial_head_exact() -> None:
    if current_head() != INITIAL_HEAD:
        raise PermissionError("H27 initial checkout HEAD mismatch.")


def require_worktree_clean() -> None:
    result = git_read(["status", "--porcelain=v1", "--untracked-files=all"])
    if result.stdout != b"":
        raise PermissionError("H27 checkout worktree is not clean.")


def require_target_object_commit() -> None:
    result = git_read(["cat-file", "-t", TARGET_HEAD])
    if result.stdout != b"commit\n":
        raise PermissionError("H27 target object is not the exact commit.")


def perform_single_explicit_detach() -> None:
    result = subprocess.run(
        [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
            "-C", CHECKOUT_TEXT, "checkout", "--detach", "--no-recurse-submodules", TARGET_HEAD,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_git_environment(),
    )
    if result.returncode != 0:
        raise PermissionError("H27 single explicit detach failed; terminal STOP, no repair or retry.")


def require_target_head_exact() -> None:
    if current_head() != TARGET_HEAD:
        raise PermissionError("H27 terminal target HEAD mismatch.")


def require_detached_state() -> None:
    result = git_read(["symbolic-ref", "-q", "HEAD"], expected_returncodes=(0, 1))
    if result.returncode != 1 or result.stdout != b"":
        raise PermissionError("H27 terminal checkout is not detached.")


def transition() -> dict[str, object]:
    require_platform_and_zero_arguments()
    verify_checkout_and_odb_realpaths()
    verified = verify_identity_graph()
    require_initial_head_exact()
    require_worktree_clean()
    require_target_object_commit()
    require_initial_head_exact()
    require_worktree_clean()

    # First and only mutation. No retry, reset, cleanup, repair, or automatic
    # recovery follows any failure, including a failure after this command.
    perform_single_explicit_detach()
    require_target_head_exact()
    require_detached_state()
    require_worktree_clean()
    return {
        "status": "H27_TARGET_CHECKOUT_EXACT_DETACH_TERMINAL_SUCCESS",
        "verified_identity_count": len(verified),
        "checkout_path": CHECKOUT_TEXT,
        "git_object_database": GIT_DATABASE_TEXT,
        "initial_head": INITIAL_HEAD,
        "target_head": TARGET_HEAD,
        "detached": True,
        "worktree_clean": True,
        "registry_opened": False,
        "authority_reserved": False,
        "authority_consumed": False,
        "creator_acknowledgement_set": False,
        "creator_invoked": False,
        "control_bundle_created": False,
        "constructor_or_materializer_executed": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(transition(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
