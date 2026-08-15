#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


CONTROL_BUNDLE = Path("/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1")
TARGET = Path("/Users/amcarene/midi-worker/repository")
OBSERVED_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"
REQUIRED_HEAD = "46a6bdf81a56a7a7a10524d4e55092301a452207"
AUTHORITY_ID = "45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e"
ACK = "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE"
REGISTRY = Path("/Users/amcarene/h27-admin/registry/h27-real-publication-constructor-execution-authority-v1.jsonl")
FINAL = Path("/Users/amcarene/h27-real-publication/governed/authority-instance-v1")
STAGING = Path("/Users/amcarene/h27-real-publication/governed/.authority-instance-v1.staging")
CONSTRUCTOR_PATH = "src/polyphonic/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor.py"
CONSTRUCTOR_BLOB = "0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62"
CONSTRUCTOR_SIZE = 12599
CONSTRUCTOR_SHA256 = "0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807"
CLOSED_BUNDLE_DIGEST = "879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe"

BUNDLE_FILES = (
    {
        "path": "configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract.json",
        "git_blob_sha1": "1bdc95411520793c2f1ff0c08ef2245e569ef2a0",
        "size_bytes": 6387,
        "raw_sha256": "0134f4c459ac9d4e642da70dbcf257f34998db064e568ea0e039b58d5952f215",
    },
    {
        "path": "configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_external_seal.json",
        "git_blob_sha1": "099703d92d9cfd761f5aa9065467fff1516d5a46",
        "size_bytes": 1673,
        "raw_sha256": "6cd9cc7f67c60ea71804fd01137ee2fddd1947c0fb0e56d3bc7d0db362054778",
    },
    {
        "path": "configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact.json",
        "git_blob_sha1": "fedcf0f1c2be368ddf619e8f1715a55f499815c8",
        "size_bytes": 688,
        "raw_sha256": "dccc4afaf20390fe07226fbfd237c06b381b203d25f6f80908adc3753c985296",
    },
    {
        "path": "configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_external_seal.json",
        "git_blob_sha1": "4f3e49d29e5777b1ad5174b24870ac21f348ac78",
        "size_bytes": 1683,
        "raw_sha256": "5b2b985f694b1e360afc9aec84a6ba8329cf6bc7b4cfea106a67108ac550decc",
    },
    {
        "path": "configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding.json",
        "git_blob_sha1": "fe89c67096bef9e41a0405a1e37a291be5fd1afa",
        "size_bytes": 2986,
        "raw_sha256": "8e9549db0821ed3f0334aab369abb18373bc5e2141d656b8e0c0e5ba6a65a9da",
    },
    {
        "path": "configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding_external_seal.json",
        "git_blob_sha1": "3d79c43ee50ccc9b2e87c3c07d63a2061b18edbf",
        "size_bytes": 1431,
        "raw_sha256": "95892205cf7af0d84a5ec75b466467486eb50996d4040bdca7d25e4b9a58940c",
    },
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    header = b"blob " + str(len(raw)).encode("ascii") + b"\0"
    return hashlib.sha1(header + raw).hexdigest()


def strict_json(raw: bytes) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            require(type(key) is str and key not in result, "duplicate or non-string JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"non-RFC8259 constant: {value}")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
    require(type(value) is dict, "JSON root must be an object")
    return value


def regular_bytes(path: Path, expected_mode: int) -> bytes:
    require(hasattr(os, "O_NOFOLLOW"), "O_NOFOLLOW unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode), f"not regular: {path}")
        require(before.st_nlink == 1, f"hard-link count mismatch: {path}")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), f"descriptor mismatch: {path}")
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
        return raw
    finally:
        os.close(fd)


def git(*args: str, allowed: tuple[int, ...] = (0,)) -> tuple[int, bytes, bytes]:
    env = {
        "HOME": "/Users/amcarene",
        "PATH": "/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin:/opt/homebrew/bin",
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
    }
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-replace-objects", "-C", str(TARGET), *args],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
    )
    require(result.returncode in allowed, f"git failed: {args!r}: {result.stderr!r}")
    return result.returncode, result.stdout, result.stderr


def path_state(path: Path) -> str:
    try:
        info = os.lstat(path)
    except FileNotFoundError:
        return "absent"
    if stat.S_ISLNK(info.st_mode):
        return "symlink"
    if stat.S_ISREG(info.st_mode):
        return f"regular:{stat.S_IMODE(info.st_mode):04o}:{info.st_size}"
    if stat.S_ISDIR(info.st_mode):
        return f"directory:{stat.S_IMODE(info.st_mode):04o}"
    return "other"


def main() -> int:
    require(sys.platform == "darwin" and len(sys.argv) == 1, "exact macOS zero-argument preflight required")
    require(os.environ.get(ACK) is None, "constructor ACK must be absent")
    require(CONTROL_BUNDLE.resolve(strict=True) == CONTROL_BUNDLE, "control bundle root mismatch")
    require(CONTROL_BUNDLE.is_dir() and not CONTROL_BUNDLE.is_symlink(), "control bundle must be a real directory")

    actual_paths = sorted(str(path.relative_to(CONTROL_BUNDLE).as_posix()) for path in CONTROL_BUNDLE.rglob("*") if path.is_file())
    expected_paths = sorted(str(item["path"]) for item in BUNDLE_FILES)
    require(actual_paths == expected_paths, "control bundle closed file set mismatch")
    for path in CONTROL_BUNDLE.rglob("*"):
        require(not path.is_symlink(), f"control bundle symlink forbidden: {path}")
        require(path.is_dir() or path.is_file(), f"control bundle entry type forbidden: {path}")

    parsed: dict[str, dict[str, object]] = {}
    digest_lines: list[str] = []
    verified_identities: list[dict[str, object]] = []
    for identity in BUNDLE_FILES:
        relative = str(identity["path"])
        raw = regular_bytes(CONTROL_BUNDLE / relative, 0o400)
        require(len(raw) == identity["size_bytes"], f"bundle size mismatch: {relative}")
        require(git_blob(raw) == identity["git_blob_sha1"], f"bundle blob mismatch: {relative}")
        require(sha256(raw) == identity["raw_sha256"], f"bundle SHA mismatch: {relative}")
        parsed[relative] = strict_json(raw)
        digest_lines.append(
            f"{relative}\0{identity['git_blob_sha1']}\0{identity['size_bytes']}\0{identity['raw_sha256']}\n"
        )
        verified_identities.append(dict(identity))
    bundle_digest = sha256("".join(digest_lines).encode("utf-8"))
    require(bundle_digest == CLOSED_BUNDLE_DIGEST, "closed bundle digest mismatch")

    gate = parsed[str(BUNDLE_FILES[0]["path"])]
    gate_seal = parsed[str(BUNDLE_FILES[1]["path"])]
    authority = parsed[str(BUNDLE_FILES[2]["path"])]
    authority_seal = parsed[str(BUNDLE_FILES[3]["path"])]
    authority_binding = parsed[str(BUNDLE_FILES[4]["path"])]
    authority_binding_seal = parsed[str(BUNDLE_FILES[5]["path"])]
    require(gate.get("contract_id") == "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE_CONTRACT_V1", "gate contract id mismatch")
    require(gate["bound_authority"] == {"execution_authority_artifact_id": AUTHORITY_ID, "expected_git_head": REQUIRED_HEAD, "single_use": True, "consumed": False}, "gate authority mismatch")
    require(gate["future_runtime_source_model"]["target_checkout_root"] == str(TARGET), "target path mismatch")
    require(gate["future_runtime_source_model"]["administrative_control_bundle_root"] == str(CONTROL_BUNDLE), "control path mismatch")
    require(gate_seal.get("execution_authority_artifact_id") == AUTHORITY_ID and gate_seal.get("expected_git_head") == REQUIRED_HEAD, "gate seal mismatch")
    require(authority.get("execution_authority_artifact_id") == AUTHORITY_ID and authority.get("expected_git_head") == REQUIRED_HEAD, "authority mismatch")
    require(authority.get("single_use") is True and authority.get("consumed") is False, "authority state mismatch")
    require(authority_seal.get("execution_authority_artifact_id") == AUTHORITY_ID and authority_seal.get("expected_git_head") == REQUIRED_HEAD, "authority seal mismatch")
    require(authority_binding["bound_artifact_values"] == {"execution_authority_artifact_id": AUTHORITY_ID, "expected_git_head": REQUIRED_HEAD, "single_use": True, "consumed": False}, "authority binding mismatch")
    require(authority_binding_seal.get("artifact_id") == AUTHORITY_ID and authority_binding_seal.get("expected_git_head") == REQUIRED_HEAD, "authority binding seal mismatch")

    _, head_raw, _ = git("rev-parse", "HEAD")
    head = head_raw.decode("ascii").strip()
    require(head == OBSERVED_HEAD, "unexpected observed checkout HEAD")
    symbolic_rc, symbolic_raw, _ = git("symbolic-ref", "-q", "HEAD", allowed=(0, 1))
    require(symbolic_rc == 1 and symbolic_raw == b"", "checkout must remain detached")
    _, status_raw, _ = git("status", "--porcelain")
    require(status_raw == b"", "checkout must remain clean")
    index_lock_absent = not (TARGET / ".git" / "index.lock").exists()
    require(index_lock_absent, "index lock present")

    _, required_type, _ = git("cat-file", "-t", REQUIRED_HEAD)
    require(required_type == b"commit\n", "required constructor HEAD unavailable")
    ancestor_rc, _, _ = git("merge-base", "--is-ancestor", REQUIRED_HEAD, head, allowed=(0, 1))
    require(ancestor_rc == 0, "required constructor HEAD is not an ancestor of observed HEAD")
    _, distance_raw, _ = git("rev-list", "--count", f"{REQUIRED_HEAD}..{head}")
    distance = int(distance_raw)
    require(distance == 11, "unexpected constructor HEAD distance")

    _, tree_raw, _ = git("ls-tree", REQUIRED_HEAD, CONSTRUCTOR_PATH)
    fields = tree_raw.rstrip(b"\n").split(maxsplit=3)
    require(len(fields) == 4 and fields[1] == b"blob" and fields[2].decode("ascii") == CONSTRUCTOR_BLOB, "constructor tree identity mismatch")
    _, constructor_raw, _ = git("cat-file", "blob", CONSTRUCTOR_BLOB)
    require(len(constructor_raw) == CONSTRUCTOR_SIZE and sha256(constructor_raw) == CONSTRUCTOR_SHA256, "constructor bytes mismatch")

    _, observed_tree, _ = git("ls-tree", "-r", "-z", head)
    transition_candidates: list[dict[str, object]] = []
    for record in observed_tree.split(b"\0"):
        if not record:
            continue
        metadata, path_raw = record.split(b"\t", 1)
        mode, object_type, object_id = metadata.split(b" ")
        path = path_raw.decode("utf-8")
        if object_type != b"blob" or not path.endswith((".py", ".sh", ".ps1")):
            continue
        if not (path.startswith("scripts/") or path.startswith("src/")):
            continue
        _, raw, _ = git("cat-file", "blob", object_id.decode("ascii"))
        if REQUIRED_HEAD.encode("ascii") in raw and any(token in raw for token in (b"checkout", b"switch", b"reset", b"detach")):
            transition_candidates.append({"path": path, "git_blob_sha1": object_id.decode("ascii"), "size_bytes": len(raw), "raw_sha256": sha256(raw)})

    registry_state = path_state(REGISTRY)
    final_state = path_state(FINAL)
    staging_state = path_state(STAGING)
    ps = subprocess.run(["/bin/ps", "-axo", "pid=,command="], check=True, stdout=subprocess.PIPE).stdout.decode("utf-8")
    active = [line.strip() for line in ps.splitlines() if any(name in line for name in (
        "harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor",
        "harmonic_censoring_h27_population_materializer",
        "run_harmonic_censoring_h27",
    ))]
    require(not active, "constructor/materializer/science process active")

    report = {
        "status": "H27_REVIEW4_CONSTRUCTOR_GATE_READ_ONLY_PREFLIGHT_PASS_STOP",
        "control_bundle_digest": bundle_digest,
        "six_file_identities_verified": True,
        "bundle_identities": verified_identities,
        "constructor_authority_id": AUTHORITY_ID,
        "required_head": REQUIRED_HEAD,
        "observed_head": head,
        "head_match": head == REQUIRED_HEAD,
        "required_head_is_ancestor": True,
        "commits_back_to_required_head": distance,
        "detached": True,
        "worktree_clean": True,
        "index_lock_absent": index_lock_absent,
        "constructor_entrypoint": CONSTRUCTOR_PATH,
        "constructor_git_blob_sha1": CONSTRUCTOR_BLOB,
        "constructor_size_bytes": CONSTRUCTOR_SIZE,
        "constructor_raw_sha256": CONSTRUCTOR_SHA256,
        "transition_runner_candidates": transition_candidates,
        "transition_entrypoint_identified": len(transition_candidates) == 1,
        "transition_candidate_command_not_authorized": [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
            "-C", str(TARGET), "checkout", "--detach", "--no-recurse-submodules", REQUIRED_HEAD,
        ],
        "constructor_registry_state": registry_state,
        "constructor_final_state": final_state,
        "constructor_staging_state": staging_state,
        "constructor_ack_present": False,
        "registry_appended": False,
        "authority_reserved": False,
        "authority_consumed": False,
        "constructor_invoked": False,
        "materializer_invoked": False,
        "science_or_locked_test": False,
        "head_changed": False,
        "transition_executed": False,
    }
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
