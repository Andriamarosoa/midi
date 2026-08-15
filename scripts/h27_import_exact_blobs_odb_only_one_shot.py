#!/usr/bin/env python3
"""Dormant one-shot importer for the eight exact H27 Git blobs."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
from typing import Mapping, Optional


ACK_ENV = "H27_ODB_ONLY_BLOB_IMPORT_EXECUTE"
SOURCE_GIT_DIR_ENV = "H27_ODB_ONLY_BLOB_IMPORT_SOURCE_GIT_DIR"
DETACH_ACK_ENV = "H27_TARGET_CHECKOUT_DETACH_EXECUTE"
CHECKOUT_TEXT = "/Users/amcarene/midi-worker/repository"
GIT_DATABASE_TEXT = "/Users/amcarene/midi-worker/repository/.git"
CHECKOUT = Path(CHECKOUT_TEXT)
GIT_DATABASE = Path(GIT_DATABASE_TEXT)
INITIAL_HEAD = "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf"
SYMBOLIC_HEAD = "refs/heads/codex/independent-note-neural-v2"
ROOT_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

CONTRACT_IDENTITY = {"path":"configs/harmonic_censoring_h27_odb_only_blob_import_contract.json","git_blob_sha1":"42eebb259f247715ddcb404c8c236418093b6a81","size_bytes":7477,"raw_sha256":"567712b4e5c4491498be68be65b2633a4537d2221d484bd4a4dcbdbaf16a5b7a"}
CONTRACT_SEAL_IDENTITY = {"path":"configs/harmonic_censoring_h27_odb_only_blob_import_contract_external_seal.json","git_blob_sha1":"4002015587573e9a3e0b8f6dbb6dcea93b967b6e","size_bytes":5382,"raw_sha256":"95120579e240b454a4bbac21236a4c993b80244ff11d687b27e7a550ed422272"}
PAYLOADS = (
    {"path":"scripts/h27_detach_target_checkout_one_shot.py","git_blob_sha1":"d1cdf1562a814cef271d606da331e96565fcc79a","size_bytes":10428,"raw_sha256":"e0fd3a4794cc2fdb266b9f3b89da25fa1260f6575e31dc3d95f761ed313b833f"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_runner_identity_binding.json","git_blob_sha1":"d03385d842ca11631ba690d0a4bb70448c84480e","size_bytes":4927,"raw_sha256":"3db676881b0fca2265c09801be5fbb94d98bbf475429a7113deee872a68970df"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_runner_identity_binding_external_seal.json","git_blob_sha1":"e574ddbcccb8bac791d9719fbee3e7fd5db8a047","size_bytes":3118,"raw_sha256":"b935cb71933f35517fa407d904b5554dc6fba949e9d3045830e07c5d3e913339"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding.json","git_blob_sha1":"a514aa0270926dca1d8402ac84078a50754d2f17","size_bytes":4496,"raw_sha256":"c614d733121451c65134f480427a6d883013256633b123f34aa57f2a25f09f82"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_identity_binding_external_seal.json","git_blob_sha1":"0f6a64b7477bde24968200a81d389b03a4a6ced0","size_bytes":2797,"raw_sha256":"bd187e4e692d0d36572d8d3e151e40682b528b03e584d6b9620b34267ffd133f"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json","git_blob_sha1":"11fff0962fc0951a0bb06605e233d34756a2f4d9","size_bytes":3643,"raw_sha256":"f1c7bf1b94b0a35e3f0bd1771e93addd594053cb155ed1c3a9e09670e57de1e5"},
    {"path":"configs/harmonic_censoring_h27_target_checkout_detach_transition_contract_external_seal.json","git_blob_sha1":"24a8c14fddd52eca148f961a31c39abaa4de018f","size_bytes":1796,"raw_sha256":"b62eff68cbca0c84c7483cbd9f3ea5049b1156129398e571b88adcbf553f0aba"},
    {"path":"readme/results/2026-08-15_harmonic-censoring-h27-creator-read-only-preflight.md","git_blob_sha1":"bda7e1fae7379996563e73d8bbcf1b2d7a871aa0","size_bytes":1987,"raw_sha256":"a28a73389a338c8d493b7c75ca82656fb01ce75eddf3aa0f277d4a928b5dbc95"},
)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def identity_ok(identity: Mapping[str, object], raw: bytes) -> bool:
    return (
        set(identity) == {"path", "git_blob_sha1", "size_bytes", "raw_sha256"}
        and type(identity["path"]) is str
        and re.fullmatch(r"[0-9a-f]{40}", str(identity["git_blob_sha1"])) is not None
        and type(identity["size_bytes"]) is int
        and re.fullmatch(r"[0-9a-f]{64}", str(identity["raw_sha256"])) is not None
        and len(raw) == identity["size_bytes"]
        and git_blob(raw) == identity["git_blob_sha1"]
        and sha256(raw) == identity["raw_sha256"]
    )


def parse_object(raw: bytes, label: str) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            if key in result:
                raise PermissionError(f"H27 duplicate JSON key in {label}.")
            result[key] = value
        return result

    try:
        value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PermissionError(f"H27 invalid JSON in {label}.") from exc
    if type(value) is not dict:
        raise PermissionError(f"H27 {label} must be a JSON object.")
    return value


def clean_git_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("GIT_"):
            del environment[key]
    environment["GIT_TERMINAL_PROMPT"] = "0"
    environment["GIT_NO_LAZY_FETCH"] = "1"
    return environment


def run_git(arguments: list[str], *, stdin: Optional[bytes] = None, expected: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        arguments,
        input=stdin,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=clean_git_environment(),
    )
    if result.returncode not in expected:
        raise PermissionError("H27 exact Git operation failed.")
    return result


def target_git(arguments: list[str], *, stdin: Optional[bytes] = None, expected: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    return run_git(
        ["git", "--no-optional-locks", "--no-replace-objects", f"--git-dir={GIT_DATABASE_TEXT}", *arguments],
        stdin=stdin,
        expected=expected,
    )


def target_worktree_git(arguments: list[str]) -> subprocess.CompletedProcess[bytes]:
    return run_git([
        "git", "--no-optional-locks", "--no-replace-objects", "-c", "core.hooksPath=/dev/null",
        "-C", CHECKOUT_TEXT, *arguments,
    ])


def require_platform_ack_and_zero_arguments() -> None:
    if sys.platform != "darwin" or len(sys.argv) != 1 or os.environ.get(ACK_ENV) != "1":
        raise PermissionError("H27 exact macOS one-shot acknowledgement and zero arguments required.")


def verify_checkout_odb_and_source_realpaths() -> Path:
    if (
        CHECKOUT.resolve(strict=True) != CHECKOUT or CHECKOUT.is_symlink() or not CHECKOUT.is_dir()
        or GIT_DATABASE.resolve(strict=True) != GIT_DATABASE or GIT_DATABASE.is_symlink() or not GIT_DATABASE.is_dir()
    ):
        raise PermissionError("H27 exact checkout or target Git database realpath mismatch.")
    source_text = os.environ.get(SOURCE_GIT_DIR_ENV)
    if not source_text:
        raise PermissionError("H27 external source Git database environment is required.")
    source = Path(source_text)
    resolved = source.resolve(strict=True)
    try:
        resolved.relative_to(CHECKOUT)
    except ValueError:
        pass
    else:
        raise PermissionError("H27 source Git database must be outside the target checkout.")
    if source != resolved or source.is_symlink() or not source.is_dir() or resolved == GIT_DATABASE:
        raise PermissionError("H27 external source Git database realpath mismatch.")
    return resolved


def require_reference_storage_files() -> None:
    if target_git(["rev-parse", "--show-ref-format"]).stdout != b"files\n":
        raise PermissionError("H27 target reference storage format is not files.")


def require_baseline() -> None:
    if target_git(["rev-parse", "--verify", "HEAD"]).stdout != (INITIAL_HEAD + "\n").encode("ascii"):
        raise PermissionError("H27 baseline HEAD mismatch.")
    if target_git(["symbolic-ref", "-q", "HEAD"]).stdout != (SYMBOLIC_HEAD + "\n").encode("ascii"):
        raise PermissionError("H27 baseline symbolic HEAD mismatch.")
    if target_worktree_git(["status", "--porcelain=v1", "--untracked-files=all"]).stdout != b"":
        raise PermissionError("H27 target worktree is not clean.")
    if (GIT_DATABASE / "index.lock").exists() or os.environ.get(DETACH_ACK_ENV) is not None:
        raise PermissionError("H27 target lock or detach acknowledgement present.")


def require_detach_runner_absent() -> None:
    result = run_git(["ps", "-axo", "pid=,command="])
    for line in result.stdout.decode("utf-8", errors="strict").splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit() or int(fields[0]) == os.getpid():
            continue
        command = fields[1]
        if "h27_detach_target_checkout_one_shot.py" in command or "d1cdf1562a814cef271d606da331e96565fcc79a" in command:
            raise PermissionError("H27 detach runner process is active.")


def regular_refs_snapshot() -> bytes:
    return target_git(["for-each-ref", "--sort=refname", "--format=%(refname)%00%(objectname)%00%(objecttype)%00"]).stdout


def read_regular_nofollow(path: Path, label: str) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise PermissionError(f"H27 {label} must be a regular non-symlink file.")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                return b"".join(chunks)
            chunks.append(chunk)
    finally:
        os.close(descriptor)


def root_refs_snapshot() -> tuple[tuple[bytes, bytes], ...]:
    rows: list[tuple[bytes, bytes]] = []
    with os.scandir(GIT_DATABASE) as entries:
        selected = [entry for entry in entries if ROOT_REF_PATTERN.fullmatch(entry.name)]
    for entry in sorted(selected, key=lambda item: item.name.encode("utf-8")):
        metadata = entry.stat(follow_symlinks=False)
        if stat.S_ISLNK(metadata.st_mode) or not stat.S_ISREG(metadata.st_mode):
            raise PermissionError("H27 root ref or pseudoref is not a regular non-symlink file.")
        path = GIT_DATABASE / entry.name
        if path.is_symlink():
            raise PermissionError("H27 root ref or pseudoref symlink rejected.")
        rows.append((entry.name.encode("utf-8"), read_regular_nofollow(path, "root ref or pseudoref")))
    return tuple(rows)


def index_snapshot() -> tuple[bool, bytes]:
    path = GIT_DATABASE / "index"
    if not path.exists():
        return False, b""
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
        raise PermissionError("H27 index must be a regular non-symlink file.")
    return True, read_regular_nofollow(path, "index")


def object_paths_snapshot() -> dict[str, tuple[int, int, int, int, int]]:
    root = GIT_DATABASE / "objects"
    snapshot: dict[str, tuple[int, int, int, int, int]] = {}
    for directory, names, files in os.walk(root, followlinks=False):
        names.sort(key=lambda value: value.encode("utf-8"))
        files.sort(key=lambda value: value.encode("utf-8"))
        directory_path = Path(directory)
        for name in names:
            child = directory_path / name
            if child.is_symlink():
                raise PermissionError("H27 target object database contains a symlink directory.")
        for name in files:
            path = directory_path / name
            metadata = path.lstat()
            if not stat.S_ISREG(metadata.st_mode) or path.is_symlink():
                raise PermissionError("H27 target object database contains a non-regular object entry.")
            relative = path.relative_to(GIT_DATABASE).as_posix()
            snapshot[relative] = (metadata.st_dev, metadata.st_ino, metadata.st_mode, metadata.st_size, metadata.st_mtime_ns)
    return snapshot


def read_source_blob(source_git_dir: Path, blob_sha1: str) -> bytes:
    if re.fullmatch(r"[0-9a-f]{40}", blob_sha1) is None:
        raise PermissionError("H27 malformed source blob identity.")
    return run_git([
        "git", "--no-optional-locks", "--no-replace-objects", f"--git-dir={source_git_dir}",
        "cat-file", "blob", blob_sha1,
    ]).stdout


def receive_and_prevalidate_all(source_git_dir: Path) -> tuple[dict[str, bytes], dict[str, object]]:
    contract_raw = read_source_blob(source_git_dir, str(CONTRACT_IDENTITY["git_blob_sha1"]))
    seal_raw = read_source_blob(source_git_dir, str(CONTRACT_SEAL_IDENTITY["git_blob_sha1"]))
    if not identity_ok(CONTRACT_IDENTITY, contract_raw) or not identity_ok(CONTRACT_SEAL_IDENTITY, seal_raw):
        raise PermissionError("H27 import contract or seal identity mismatch.")
    contract = parse_object(contract_raw, "ODB-only import contract")
    seal = parse_object(seal_raw, "ODB-only import contract seal")
    if contract.get("payloads") != list(PAYLOADS) or seal.get("contract") != CONTRACT_IDENTITY or seal.get("payloads") != list(PAYLOADS):
        raise PermissionError("H27 import contract, seal, or payload binding mismatch.")
    payloads: dict[str, bytes] = {}
    for identity in PAYLOADS:
        raw = read_source_blob(source_git_dir, str(identity["git_blob_sha1"]))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 payload identity mismatch: {identity['path']}.")
        calculated = target_git(["hash-object", "--stdin"], stdin=raw).stdout
        if calculated != (str(identity["git_blob_sha1"]) + "\n").encode("ascii"):
            raise PermissionError("H27 target Git hash-object prevalidation mismatch.")
        payloads[str(identity["git_blob_sha1"])] = raw
    if len(payloads) != 8:
        raise PermissionError("H27 requires exactly eight unique buffered payloads.")
    return payloads, contract


def require_all_target_blobs_absent() -> None:
    for identity in PAYLOADS:
        result = target_git(["cat-file", "-e", str(identity["git_blob_sha1"])], expected=(0, 1))
        if result.returncode != 1:
            raise PermissionError("H27 target blob must be absent before the one-shot import.")


def write_exact_payloads(payloads: Mapping[str, bytes]) -> None:
    for identity in PAYLOADS:
        blob_sha1 = str(identity["git_blob_sha1"])
        raw = payloads[blob_sha1]
        result = run_git(
            ["git", "--no-replace-objects", f"--git-dir={GIT_DATABASE_TEXT}", "hash-object", "-w", "--stdin"],
            stdin=raw,
        )
        if result.stdout != (blob_sha1 + "\n").encode("ascii"):
            raise PermissionError("H27 written blob identity mismatch; terminal consumed failure.")


def require_all_target_blobs_exact() -> None:
    for identity in PAYLOADS:
        raw = target_git(["cat-file", "blob", str(identity["git_blob_sha1"])]).stdout
        if not identity_ok(identity, raw):
            raise PermissionError("H27 terminal target blob identity mismatch.")


def import_exact_blobs() -> dict[str, object]:
    require_platform_ack_and_zero_arguments()
    source_git_dir = verify_checkout_odb_and_source_realpaths()
    require_reference_storage_files()
    require_baseline()
    regular_before = regular_refs_snapshot()
    root_before = root_refs_snapshot()
    index_before = index_snapshot()
    require_detach_runner_absent()
    payloads, _contract = receive_and_prevalidate_all(source_git_dir)
    require_reference_storage_files()
    require_baseline()
    if regular_refs_snapshot() != regular_before or root_refs_snapshot() != root_before or index_snapshot() != index_before:
        raise PermissionError("H27 target refs or index changed before first write.")
    require_detach_runner_absent()
    require_all_target_blobs_absent()
    objects_before = object_paths_snapshot()

    # First irreversible effect. Any failure from here is terminal and consumed.
    write_exact_payloads(payloads)
    require_all_target_blobs_exact()
    require_reference_storage_files()
    require_baseline()
    if regular_refs_snapshot() != regular_before or root_refs_snapshot() != root_before or index_snapshot() != index_before:
        raise PermissionError("H27 terminal refs or index drift; terminal consumed failure.")
    require_detach_runner_absent()
    objects_after = object_paths_snapshot()
    expected_new = {"objects/" + str(item["git_blob_sha1"])[:2] + "/" + str(item["git_blob_sha1"])[2:] for item in PAYLOADS}
    if set(objects_after) != set(objects_before) | expected_new or any(objects_after[path] != metadata for path, metadata in objects_before.items()):
        raise PermissionError("H27 unexpected target object database change; terminal consumed failure.")
    return {
        "status": "H27_ODB_ONLY_EXACT_EIGHT_BLOB_IMPORT_TERMINAL_SUCCESS",
        "payload_count": 8,
        "payload_blob_ids": [item["git_blob_sha1"] for item in PAYLOADS],
        "source_git_database": str(source_git_dir),
        "target_git_database": GIT_DATABASE_TEXT,
        "head_unchanged": True,
        "symbolic_head_unchanged": True,
        "regular_refs_unchanged": True,
        "root_refs_and_pseudorefs_unchanged": True,
        "index_unchanged": True,
        "worktree_clean": True,
        "detach_runner_invoked": False,
        "registry_opened": False,
        "authority_reserved": False,
        "creator_invoked": False,
        "control_bundle_created": False,
        "materializer_executed": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(import_exact_blobs(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
