#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


CREATOR = Path("/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1/h27_reviewed_control_bundle_creator.py")
EXPECTED_CREATOR_SHA256 = "0f0dd5867c82b1237736d03f48a6176171c4459b9106bca251ab53778092e42f"
EXPECTED_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def regular_bytes(path: Path, *, expected_mode: int) -> tuple[bytes, os.stat_result]:
    require(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode), f"not regular: {path}")
        require(before.st_nlink == 1, f"hard-link count mismatch: {path}")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), f"descriptor drift: {path}")
        require(stat.S_IMODE(before.st_mode) == expected_mode, f"mode mismatch: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        stable = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, key) == getattr(after, key) for key in stable), f"changed while read: {path}")
        return raw, after
    finally:
        os.close(fd)


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
    require(sys.platform == "darwin" and len(sys.argv) == 1, "exact macOS zero-argument postcheck required")
    require(os.environ.get("H27_REVIEWED_CONTROL_BUNDLE_CREATOR_EXECUTE") is None, "creator ACK must be absent")

    spec = importlib.util.spec_from_file_location("h27_reviewed_creator_postcheck", CREATOR)
    require(spec is not None and spec.loader is not None, "creator import unavailable")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    creator_sha = module._verify_source()
    require(creator_sha == EXPECTED_CREATOR_SHA256, "creator SHA mismatch")

    registry_raw, registry_stat = regular_bytes(module.REGISTRY, expected_mode=0o600)
    lines = registry_raw.splitlines(keepends=True)
    require(len(lines) == 3 and b"".join(lines) == registry_raw, "registry must contain exactly three complete lines")

    final = module.FINAL_BUNDLE
    staging = module.STAGING_BUNDLE
    require(final.resolve(strict=True) == final and final.is_dir() and not final.is_symlink(), "final bundle root mismatch")
    try:
        os.lstat(staging)
    except FileNotFoundError:
        pass
    else:
        raise PermissionError("staging bundle remains present")

    actual_files = sorted(str(path.relative_to(final).as_posix()) for path in final.rglob("*") if path.is_file())
    expected_files = sorted(str(identity["path"]) for identity in module.BUNDLE_FILES)
    require(actual_files == expected_files, "bundle closed file set mismatch")
    for path in final.rglob("*"):
        require(not path.is_symlink(), f"bundle symlink forbidden: {path}")
        require(path.is_dir() or path.is_file(), f"bundle entry type forbidden: {path}")

    bundle_identities = []
    digest_lines = []
    for identity in module.BUNDLE_FILES:
        relative = str(identity["path"])
        raw, _ = regular_bytes(final / relative, expected_mode=0o400)
        require(module._identity_ok(identity, raw), f"bundle identity mismatch: {relative}")
        bundle_identities.append({
            "path": relative,
            "git_blob_sha1": identity["git_blob_sha1"],
            "size_bytes": len(raw),
            "raw_sha256": sha256(raw),
        })
        digest_lines.append(
            f"{relative}\0{identity['git_blob_sha1']}\0{identity['size_bytes']}\0{identity['raw_sha256']}\n"
        )
    bundle_digest = sha256("".join(digest_lines).encode("utf-8"))
    require(module._closed_bundle_digest(final) == bundle_digest, "creator closed bundle digest mismatch")

    reserved = module.canonical_registry_record(
        transition_index=0,
        state="reserved",
        prior_record_raw_sha256=None,
        creator_sha256=creator_sha,
        bundle_sha256=None,
        failure_stage=None,
    )
    consumed = module.canonical_registry_record(
        transition_index=1,
        state="consumed",
        prior_record_raw_sha256=sha256(reserved),
        creator_sha256=creator_sha,
        bundle_sha256=None,
        failure_stage=None,
    )
    succeeded = module.canonical_registry_record(
        transition_index=2,
        state="bundle_creation_succeeded",
        prior_record_raw_sha256=sha256(consumed),
        creator_sha256=creator_sha,
        bundle_sha256=bundle_digest,
        failure_stage=None,
    )
    require(lines == [reserved, consumed, succeeded], "registry transition bytes mismatch")
    records = [module._strict_json(line) for line in lines]

    _, head = git("rev-parse", "HEAD")
    require(head.strip() == EXPECTED_HEAD, "checkout HEAD drift")
    symbolic_rc, symbolic = git("symbolic-ref", "-q", "HEAD", allow_one=True)
    require(symbolic_rc == 1 and symbolic == "", "checkout no longer detached")
    _, status_text = git("status", "--porcelain")
    require(status_text == "", "checkout not clean")
    require(not (Path("/Users/amcarene/midi-worker/repository/.git") / "index.lock").exists(), "index lock present")

    ps = subprocess.run(["/bin/ps", "-axo", "pid=,command="], check=True, text=True, stdout=subprocess.PIPE).stdout
    forbidden_names = (
        "h27_reviewed_control_bundle_creator.py",
        "harmonic_censoring_h27_population_materializer",
        "run_harmonic_censoring_h27",
    )
    active = [line.strip() for line in ps.splitlines() if any(name in line for name in forbidden_names)]
    require(not active, "H27 creator/materializer/science process remains active")

    report = {
        "status": "H27_REVIEW4_CREATOR_TERMINAL_SUCCESS_STOP",
        "creator_exitcode": 0,
        "creator_stdout_size": 0,
        "creator_stdout_sha256": sha256(b""),
        "creator_stderr_size": 0,
        "creator_stderr_sha256": sha256(b""),
        "registry_size_bytes": registry_stat.st_size,
        "registry_raw_sha256": sha256(registry_raw),
        "registry_record_count": len(records),
        "registry_states": [record["state"] for record in records],
        "registry_record_ids": [record["record_id"] for record in records],
        "bundle_file_count": len(bundle_identities),
        "bundle_identities": bundle_identities,
        "closed_bundle_digest": bundle_digest,
        "staging_absent": True,
        "final_present": True,
        "checkout_head": head.strip(),
        "detached": True,
        "worktree_clean": True,
        "materializer_executed": False,
        "p0_p1_p2_executed": False,
        "science_or_locked_test": False,
    }
    print(json.dumps(report, separators=(",", ":"), sort_keys=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
