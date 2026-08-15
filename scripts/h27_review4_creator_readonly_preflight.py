#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import sys
from typing import Optional


CREATOR = Path("/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1/h27_reviewed_control_bundle_creator.py")
MANIFEST = CREATOR.with_name("manifest.json")
EXPECTED_CREATOR_SHA256 = "0f0dd5867c82b1237736d03f48a6176171c4459b9106bca251ab53778092e42f"
EXPECTED_MANIFEST_SHA256 = "1d21fc852bec98310f331b2122fb1b2005ab2fd4d2a1b0c5cdd270a1c6dc9a0f"
EXPECTED_CLOSED_DIGEST = "bc0d75ebf043018b677652b414d122d7dcbdd4c5a7fef0a38eef9b93b4c6d51d"
EXPECTED_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"
EXPECTED_AUTHORITY = "4e1072559ff1ef5ec1e2fb0e4ec72b3baca2d98811fabfb568e9380951129c76"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def regular_bytes(path: Path, *, mode: Optional[int] = None) -> tuple[bytes, os.stat_result]:
    require(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode), f"not a regular file: {path}")
        require(stat.S_ISREG(named.st_mode), f"named entry not regular: {path}")
        require(before.st_nlink == 1, f"unexpected hard links: {path}")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), f"descriptor drift: {path}")
        if mode is not None:
            require(stat.S_IMODE(before.st_mode) == mode, f"mode mismatch: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        stable = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, key) == getattr(after, key) for key in stable), f"file changed while read: {path}")
        return raw, after
    finally:
        os.close(fd)


def absent(path: Path) -> bool:
    try:
        os.lstat(path)
    except FileNotFoundError:
        return True
    return False


def git(*args: str, allow_one: bool = False) -> tuple[int, str]:
    env = {
        "HOME": "/Users/amcarene",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-replace-objects", "-C", "/Users/amcarene/midi-worker/repository", *args],
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    require(result.returncode == 0 or (allow_one and result.returncode == 1), f"git failed: {args!r}")
    return result.returncode, result.stdout


def main() -> int:
    require(sys.platform == "darwin", "macOS required")
    require(len(sys.argv) == 1, "arguments forbidden")
    require(os.environ.get("H27_REVIEWED_CONTROL_BUNDLE_CREATOR_EXECUTE") is None, "creator ACK must be absent")
    safe_git_environment = {"GIT_TERMINAL_PROMPT", "GIT_NO_LAZY_FETCH", "GIT_OPTIONAL_LOCKS"}
    require(
        not any(key.startswith("GIT_") and key not in safe_git_environment for key in os.environ),
        "inherited Git redirector environment forbidden",
    )
    require(os.environ.get("GIT_TERMINAL_PROMPT") == "0", "Git prompting must be disabled")
    require(os.environ.get("GIT_NO_LAZY_FETCH") == "1", "Git lazy fetch must be disabled")
    require(os.environ.get("GIT_OPTIONAL_LOCKS") == "0", "Git optional locks must be disabled")

    creator_raw, _ = regular_bytes(CREATOR)
    manifest_raw, _ = regular_bytes(MANIFEST)
    require(len(creator_raw) == 44063, "creator size mismatch")
    require(sha256(creator_raw) == EXPECTED_CREATOR_SHA256, "creator SHA mismatch")
    require(len(manifest_raw) == 790, "manifest size mismatch")
    require(sha256(manifest_raw) == EXPECTED_MANIFEST_SHA256, "manifest SHA mismatch")
    require(sorted(path.name for path in CREATOR.parent.iterdir()) == sorted((CREATOR.name, MANIFEST.name)), "creator source is not closed")
    digest_lines = (
        f"{CREATOR.name}\0{len(creator_raw)}\0{sha256(creator_raw)}\n"
        f"{MANIFEST.name}\0{len(manifest_raw)}\0{sha256(manifest_raw)}\n"
    ).encode("utf-8")
    require(sha256(digest_lines) == EXPECTED_CLOSED_DIGEST, "closed source digest mismatch")

    spec = importlib.util.spec_from_file_location("h27_reviewed_creator_readonly_preflight", CREATOR)
    require(spec is not None and spec.loader is not None, "creator import spec unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    require(module._verify_source() == EXPECTED_CREATOR_SHA256, "creator self-verification failed")
    identities = module.bound_predecessor_identities()
    require(len(identities) == 130, "predecessor count mismatch")
    module.verify_bound_predecessors(module._read_blob)
    authority_raw = module._read_blob(module.CREATOR_ROOTS[0]["git_blob_sha1"])
    authority = module._strict_json(authority_raw)
    require(authority.get("creation_authority_artifact_id") == EXPECTED_AUTHORITY, "authority mismatch")
    require(authority.get("expected_execution_git_head") == EXPECTED_HEAD, "authority HEAD mismatch")
    require(authority.get("single_use") is True and authority.get("consumed") is False, "authority state mismatch")

    checkout = Path("/Users/amcarene/midi-worker/repository")
    git_dir = checkout / ".git"
    require(checkout.resolve(strict=True) == checkout, "checkout realpath mismatch")
    require(git_dir.resolve(strict=True) == git_dir, "Git database realpath mismatch")
    _, head = git("rev-parse", "HEAD")
    require(head.strip() == EXPECTED_HEAD, "checkout HEAD mismatch")
    symbolic_rc, symbolic = git("symbolic-ref", "-q", "HEAD", allow_one=True)
    require(symbolic_rc == 1 and symbolic == "", "checkout is not detached")
    _, status_text = git("status", "--porcelain")
    require(status_text == "", "checkout not clean")
    require(absent(git_dir / "index.lock"), "index lock present")

    control = Path("/Users/amcarene/h27-admin/control")
    require(control.resolve(strict=True) == control and not control.is_symlink() and control.is_dir(), "control directory mismatch")
    final = control / "h27-constructor-execution-gate-v1"
    staging = control / ".h27-constructor-execution-gate-v1.staging"
    require(absent(final), "final bundle already exists")
    require(absent(staging), "staging bundle already exists")

    registry = Path("/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl")
    registry_raw, registry_stat = regular_bytes(registry, mode=0o600)
    require(registry_stat.st_size == 0 and registry_raw == b"", "registry is not empty")

    ps = subprocess.run(["/bin/ps", "-axo", "pid=,command="], check=True, text=True, stdout=subprocess.PIPE).stdout
    active = []
    for line in ps.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        pid_text, _, command = stripped.partition(" ")
        if pid_text.isdigit() and int(pid_text) != os.getpid() and str(CREATOR) in command:
            active.append({"pid": int(pid_text), "command": command})
    require(not active, "creator process active")

    report = {
        "status": "H27_REVIEW4_CREATOR_READ_ONLY_PREFLIGHT_PASS_STOP",
        "creator_sha256": sha256(creator_raw),
        "manifest_sha256": sha256(manifest_raw),
        "closed_source_digest": sha256(digest_lines),
        "predecessor_identity_count": len(identities),
        "authority_id": authority["creation_authority_artifact_id"],
        "checkout_head": head.strip(),
        "expected_head": EXPECTED_HEAD,
        "head_match": True,
        "detached": True,
        "worktree_clean": True,
        "control_real_non_symlink": True,
        "final_absent": True,
        "staging_absent": True,
        "registry_mode": "0600",
        "registry_size": registry_stat.st_size,
        "registry_record_count": 0,
        "creator_process_count": 0,
        "creator_ack_present": False,
        "flock_used": False,
        "registry_appended": False,
        "authority_reserved": False,
        "authority_consumed": False,
        "creator_invoked": False,
        "bundle_created": False,
        "materializer_executed": False,
        "science_or_locked_test": False,
    }
    print(json.dumps(report, separators=(",", ":"), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
