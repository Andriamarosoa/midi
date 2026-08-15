#!/usr/bin/env python3
"""Dormant one-shot H27 Review 4 transition to the constructor gate HEAD."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


ACK = "H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_EXECUTE"
CONSTRUCTOR_ACK = "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE"
TARGET_TEXT = "/Users/amcarene/midi-worker/repository"
GIT_DATABASE_TEXT = "/Users/amcarene/midi-worker/repository/.git"
TARGET = Path(TARGET_TEXT)
GIT_DATABASE = Path(GIT_DATABASE_TEXT)
INITIAL_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"
TARGET_HEAD = "46a6bdf81a56a7a7a10524d4e55092301a452207"
CONTROL_BUNDLE_TEXT = "/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1"
CONTROL_BUNDLE = Path(CONTROL_BUNDLE_TEXT)
REGISTRY = Path("/Users/amcarene/h27-admin/registry/h27-real-publication-constructor-execution-authority-v1.jsonl")
FINAL = Path("/Users/amcarene/h27-real-publication/governed/authority-instance-v1")
STAGING = Path("/Users/amcarene/h27-real-publication/governed/.authority-instance-v1.staging")
CLOSED_BUNDLE_DIGEST = "879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe"
AUTHORITY_ID = "45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e"
CONSTRUCTOR_PATH = "src/polyphonic/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor.py"
CONSTRUCTOR_BLOB = "0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62"
CONSTRUCTOR_SIZE = 12599
CONSTRUCTOR_SHA256 = "0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807"

BUNDLE_FILES = (
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract.json", "1bdc95411520793c2f1ff0c08ef2245e569ef2a0", 6387, "0134f4c459ac9d4e642da70dbcf257f34998db064e568ea0e039b58d5952f215"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_external_seal.json", "099703d92d9cfd761f5aa9065467fff1516d5a46", 1673, "6cd9cc7f67c60ea71804fd01137ee2fddd1947c0fb0e56d3bc7d0db362054778"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact.json", "fedcf0f1c2be368ddf619e8f1715a55f499815c8", 688, "dccc4afaf20390fe07226fbfd237c06b381b203d25f6f80908adc3753c985296"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_external_seal.json", "4f3e49d29e5777b1ad5174b24870ac21f348ac78", 1683, "5b2b985f694b1e360afc9aec84a6ba8329cf6bc7b4cfea106a67108ac550decc"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding.json", "fe89c67096bef9e41a0405a1e37a291be5fd1afa", 2986, "8e9549db0821ed3f0334aab369abb18373bc5e2141d656b8e0c0e5ba6a65a9da"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding_external_seal.json", "3d79c43ee50ccc9b2e87c3c07d63a2061b18edbf", 1431, "95892205cf7af0d84a5ec75b466467486eb50996d4040bdca7d25e4b9a58940c"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def clean_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("GIT_"):
            del environment[key]
    environment.update({
        "GIT_TERMINAL_PROMPT": "0",
        "GIT_NO_LAZY_FETCH": "1",
        "GIT_OPTIONAL_LOCKS": "0",
    })
    return environment


def git_read(*arguments: str, allowed: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-replace-objects", "-c", "core.hooksPath=/dev/null", "-C", TARGET_TEXT, *arguments],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_environment(),
    )
    require(result.returncode in allowed, f"H27 Git read failed: {arguments!r}")
    return result


def regular_bytes(path: Path) -> bytes:
    require(hasattr(os, "O_NOFOLLOW"), "H27 O_NOFOLLOW unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode), f"H27 non-regular bundle file: {path}")
        require(before.st_nlink == 1, f"H27 bundle hard link forbidden: {path}")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), f"H27 bundle descriptor mismatch: {path}")
        require(stat.S_IMODE(before.st_mode) == 0o400, f"H27 bundle mode mismatch: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, field) == getattr(after, field) for field in fields), f"H27 bundle changed during read: {path}")
        return raw
    finally:
        os.close(fd)


def strict_json(raw: bytes) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            require(type(key) is str and key not in result, "H27 duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError(f"H27 non-RFC8259 constant: {value}")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
    require(type(value) is dict, "H27 bundle JSON root mismatch")
    return value


def require_platform_ack_and_zero_arguments() -> None:
    require(sys.platform == "darwin", "H27 exact macOS runner required")
    require(len(sys.argv) == 1, "H27 zero arguments required")
    require(os.environ.get(ACK) == "1", "H27 transition ACK required")
    require(os.environ.get(CONSTRUCTOR_ACK) is None, "H27 constructor ACK must remain absent")


def verify_checkout_realpaths() -> None:
    require(TARGET.resolve(strict=True) == TARGET and TARGET.is_dir() and not TARGET.is_symlink(), "H27 checkout realpath mismatch")
    require(GIT_DATABASE.resolve(strict=True) == GIT_DATABASE and GIT_DATABASE.is_dir() and not GIT_DATABASE.is_symlink(), "H27 Git database realpath mismatch")


def verify_control_bundle() -> str:
    require(CONTROL_BUNDLE.resolve(strict=True) == CONTROL_BUNDLE, "H27 control bundle root mismatch")
    require(CONTROL_BUNDLE.is_dir() and not CONTROL_BUNDLE.is_symlink(), "H27 control bundle root type mismatch")
    actual = sorted(path.relative_to(CONTROL_BUNDLE).as_posix() for path in CONTROL_BUNDLE.rglob("*") if path.is_file())
    expected = sorted(identity[0] for identity in BUNDLE_FILES)
    require(actual == expected, "H27 closed bundle file set mismatch")
    for path in CONTROL_BUNDLE.rglob("*"):
        require(not path.is_symlink() and (path.is_dir() or path.is_file()), f"H27 control bundle entry type mismatch: {path}")

    parsed: dict[str, dict[str, object]] = {}
    digest_lines: list[str] = []
    for relative, blob_id, size, digest in BUNDLE_FILES:
        raw = regular_bytes(CONTROL_BUNDLE / relative)
        require((git_blob(raw), len(raw), sha256(raw)) == (blob_id, size, digest), f"H27 bundle identity mismatch: {relative}")
        parsed[relative] = strict_json(raw)
        digest_lines.append(f"{relative}\0{blob_id}\0{size}\0{digest}\n")
    closed_digest = sha256("".join(digest_lines).encode("utf-8"))
    require(closed_digest == CLOSED_BUNDLE_DIGEST, "H27 closed bundle digest mismatch")

    gate, gate_seal, authority, authority_seal, binding, binding_seal = (
        parsed[identity[0]] for identity in BUNDLE_FILES
    )
    require(gate.get("contract_id") == "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE_CONTRACT_V1", "H27 gate contract mismatch")
    require(gate.get("bound_authority") == {"execution_authority_artifact_id": AUTHORITY_ID, "expected_git_head": TARGET_HEAD, "single_use": True, "consumed": False}, "H27 gate authority mismatch")
    require(gate["future_runtime_source_model"]["target_checkout_root"] == TARGET_TEXT, "H27 target binding mismatch")
    require(gate["future_runtime_source_model"]["administrative_control_bundle_root"] == CONTROL_BUNDLE_TEXT, "H27 control binding mismatch")
    require(gate_seal.get("execution_authority_artifact_id") == AUTHORITY_ID and gate_seal.get("expected_git_head") == TARGET_HEAD, "H27 gate seal mismatch")
    require(authority.get("execution_authority_artifact_id") == AUTHORITY_ID and authority.get("expected_git_head") == TARGET_HEAD, "H27 authority mismatch")
    require(authority.get("single_use") is True and authority.get("consumed") is False, "H27 authority state mismatch")
    require(authority_seal.get("execution_authority_artifact_id") == AUTHORITY_ID and authority_seal.get("expected_git_head") == TARGET_HEAD, "H27 authority seal mismatch")
    require(binding.get("bound_artifact_values") == {"execution_authority_artifact_id": AUTHORITY_ID, "expected_git_head": TARGET_HEAD, "single_use": True, "consumed": False}, "H27 authority binding mismatch")
    require(binding_seal.get("artifact_id") == AUTHORITY_ID and binding_seal.get("expected_git_head") == TARGET_HEAD, "H27 authority binding seal mismatch")
    return closed_digest


def current_head() -> str:
    return git_read("rev-parse", "--verify", "HEAD").stdout.decode("ascii").strip()


def require_detached() -> None:
    result = git_read("symbolic-ref", "-q", "HEAD", allowed=(0, 1))
    require(result.returncode == 1 and result.stdout == b"", "H27 checkout must be detached")


def require_clean_and_unlocked() -> None:
    require(git_read("status", "--porcelain=v1", "--untracked-files=all").stdout == b"", "H27 checkout must be clean")
    require(not (GIT_DATABASE / "index.lock").exists(), "H27 index.lock must be absent")


def regular_refs_snapshot() -> bytes:
    return git_read("for-each-ref", "--format=%(refname)%00%(objectname)%00%(objecttype)", "refs/heads", "refs/tags", "refs/remotes").stdout


def verify_initial_git_state() -> bytes:
    require(current_head() == INITIAL_HEAD, "H27 initial HEAD mismatch")
    require_detached()
    require_clean_and_unlocked()
    require(git_read("cat-file", "-t", TARGET_HEAD).stdout == b"commit\n", "H27 target is not a commit")
    require(git_read("merge-base", "--is-ancestor", TARGET_HEAD, INITIAL_HEAD, allowed=(0, 1)).returncode == 0, "H27 target is not the required ancestor")
    require(int(git_read("rev-list", "--count", f"{TARGET_HEAD}..{INITIAL_HEAD}").stdout) == 11, "H27 target distance mismatch")
    return regular_refs_snapshot()


def verify_constructor() -> None:
    tree = git_read("ls-tree", TARGET_HEAD, CONSTRUCTOR_PATH).stdout.rstrip(b"\n").split(maxsplit=3)
    require(len(tree) == 4 and tree[1] == b"blob" and tree[2].decode("ascii") == CONSTRUCTOR_BLOB, "H27 constructor tree identity mismatch")
    raw = git_read("cat-file", "blob", CONSTRUCTOR_BLOB).stdout
    require((len(raw), sha256(raw)) == (CONSTRUCTOR_SIZE, CONSTRUCTOR_SHA256), "H27 constructor byte identity mismatch")


def require_publication_paths_absent() -> None:
    for path in (REGISTRY, FINAL, STAGING):
        try:
            os.lstat(path)
        except FileNotFoundError:
            continue
        raise PermissionError(f"H27 future publication path must be absent: {path}")


def require_no_active_processes() -> None:
    raw = subprocess.run(["/bin/ps", "-axo", "pid=,command="], check=True, stdout=subprocess.PIPE).stdout
    forbidden = (
        b"harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor",
        b"harmonic_censoring_h27_population_materializer",
        b"run_harmonic_censoring_h27",
    )
    require(not any(any(token in line for token in forbidden) for line in raw.splitlines()), "H27 constructor/materializer/science process active")


def perform_single_explicit_detach() -> None:
    result = subprocess.run(
        [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
            "-C", TARGET_TEXT, "checkout", "--detach", "--no-recurse-submodules", TARGET_HEAD,
        ],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_environment(),
    )
    require(result.returncode == 0, "H27 transition consumed and failed; terminal STOP, no retry or repair")


def transition() -> dict[str, object]:
    require_platform_ack_and_zero_arguments()
    verify_checkout_realpaths()
    bundle_digest = verify_control_bundle()
    refs_before = verify_initial_git_state()
    verify_constructor()
    require_publication_paths_absent()
    require_no_active_processes()

    # Complete revalidation immediately before the first and only mutation.
    require(current_head() == INITIAL_HEAD, "H27 initial HEAD drifted")
    require_detached()
    require_clean_and_unlocked()
    require(regular_refs_snapshot() == refs_before, "H27 regular refs drifted")
    require(verify_control_bundle() == bundle_digest, "H27 control bundle drifted")
    verify_constructor()
    require_publication_paths_absent()
    require_no_active_processes()

    # Consumption boundary: once this subprocess is launched, this transition
    # attempt is consumed regardless of its result. Never retry or repair.
    perform_single_explicit_detach()

    require(current_head() == TARGET_HEAD, "H27 terminal HEAD mismatch")
    require_detached()
    require_clean_and_unlocked()
    require(regular_refs_snapshot() == refs_before, "H27 regular refs changed")
    require(verify_control_bundle() == bundle_digest, "H27 terminal control bundle drift")
    verify_constructor()
    require_publication_paths_absent()
    require_no_active_processes()
    return {
        "status": "H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_TERMINAL_SUCCESS_STOP",
        "initial_head": INITIAL_HEAD,
        "target_head": TARGET_HEAD,
        "target_is_exact_ancestor": True,
        "distance_commits": 11,
        "detached": True,
        "worktree_clean": True,
        "index_lock_absent": True,
        "regular_refs_unchanged": True,
        "control_bundle_digest": bundle_digest,
        "constructor_authority_id": AUTHORITY_ID,
        "constructor_git_blob_sha1": CONSTRUCTOR_BLOB,
        "constructor_size_bytes": CONSTRUCTOR_SIZE,
        "constructor_raw_sha256": CONSTRUCTOR_SHA256,
        "constructor_registry_absent": True,
        "constructor_final_absent": True,
        "constructor_staging_absent": True,
        "transition_attempt_consumed": True,
        "constructor_ack_present": False,
        "registry_opened": False,
        "authority_reserved": False,
        "authority_consumed": False,
        "constructor_invoked": False,
        "materializer_invoked": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(transition(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
