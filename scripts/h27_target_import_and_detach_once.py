#!/usr/bin/env python3
"""Self-contained one-shot import of eight H27 blobs and exact target detach."""
from __future__ import annotations

import base64
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import zlib
from typing import Mapping, Optional


ACK_ENV = "H27_TARGET_IMPORT_AND_DETACH_EXECUTE"
CHECKOUT_TEXT = "/Users/amcarene/midi-worker/repository"
GIT_DATABASE_TEXT = "/Users/amcarene/midi-worker/repository/.git"
CHECKOUT = Path(CHECKOUT_TEXT)
GIT_DATABASE = Path(GIT_DATABASE_TEXT)
INITIAL_HEAD = "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf"
SYMBOLIC_HEAD = "refs/heads/codex/independent-note-neural-v2"
TARGET_HEAD = "7ee0a8977208bfa389e284b07207abc40a3517fd"
ROOT_REF_PATTERN = re.compile(r"^[A-Z][A-Z0-9_]*$")

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

EMBEDDED_ARCHIVE_SIZE = 46399
EMBEDDED_ARCHIVE_COMPRESSED_SHA256 = '0a181f259bc2242f65153d12de8d4c0908c1ab247752d41bbf638c88b0dd0a5d'
EMBEDDED_ARCHIVE_BASE64 = (
    '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'
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


def verify_checkout_and_odb_realpaths() -> None:
    if (
        CHECKOUT.resolve(strict=True) != CHECKOUT or CHECKOUT.is_symlink() or not CHECKOUT.is_dir()
        or GIT_DATABASE.resolve(strict=True) != GIT_DATABASE or GIT_DATABASE.is_symlink() or not GIT_DATABASE.is_dir()
    ):
        raise PermissionError("H27 exact checkout or target Git database realpath mismatch.")


def require_reference_storage_files() -> None:
    repository_format = target_git(["config", "--local", "--get", "core.repositoryFormatVersion"])
    ref_storage = target_git(
        ["config", "--local", "--get", "extensions.refStorage"],
        expected=(0, 1),
    )
    refs_directory = GIT_DATABASE / "refs"
    reftable_directory = GIT_DATABASE / "reftable"
    try:
        refs_directory_resolved = refs_directory.resolve(strict=True)
    except OSError as exc:
        raise PermissionError("H27 target reference storage format is not the sealed files backend.") from exc
    if (
        repository_format.stdout != b"0\n" or repository_format.stderr != b""
        or ref_storage.returncode != 1 or ref_storage.stdout != b"" or ref_storage.stderr != b""
        or refs_directory_resolved != refs_directory
        or refs_directory.is_symlink() or not refs_directory.is_dir()
        or reftable_directory.exists() or reftable_directory.is_symlink()
    ):
        raise PermissionError("H27 target reference storage format is not the sealed files backend.")


def require_baseline() -> None:
    if target_git(["rev-parse", "--verify", "HEAD"]).stdout != (INITIAL_HEAD + "\n").encode("ascii"):
        raise PermissionError("H27 baseline HEAD mismatch.")
    if target_git(["symbolic-ref", "-q", "HEAD"]).stdout != (SYMBOLIC_HEAD + "\n").encode("ascii"):
        raise PermissionError("H27 baseline symbolic HEAD mismatch.")
    if target_worktree_git(["status", "--porcelain=v1", "--untracked-files=all"]).stdout != b"":
        raise PermissionError("H27 target worktree is not clean.")
    if (GIT_DATABASE / "index.lock").exists():
        raise PermissionError("H27 target index lock is present.")


def require_conflicting_runner_absent() -> None:
    result = run_git(["ps", "-axo", "pid=,command="])
    for line in result.stdout.decode("utf-8", errors="strict").splitlines():
        fields = line.strip().split(maxsplit=1)
        if len(fields) != 2 or not fields[0].isdigit() or int(fields[0]) == os.getpid():
            continue
        command = fields[1]
        if (
            "h27_detach_target_checkout_one_shot.py" in command
            or "d1cdf1562a814cef271d606da331e96565fcc79a" in command
            or "h27_import_exact_blobs_odb_only_one_shot.py" in command
            or "h27_target_import_and_detach_once.py" in command
        ):
            raise PermissionError("H27 conflicting importer or detach runner is active.")


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


def decode_and_prevalidate_all() -> dict[str, bytes]:
    try:
        compressed = base64.b64decode(EMBEDDED_ARCHIVE_BASE64.encode("ascii"), validate=True)
        if sha256(compressed) != EMBEDDED_ARCHIVE_COMPRESSED_SHA256:
            raise PermissionError("H27 embedded archive digest mismatch.")
        archive = zlib.decompress(compressed)
        if len(archive) != EMBEDDED_ARCHIVE_SIZE:
            raise PermissionError("H27 embedded archive size mismatch.")
        rows = json.loads(archive.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError, zlib.error) as exc:
        raise PermissionError("H27 embedded archive is invalid.") from exc
    if type(rows) is not list or len(rows) != 8:
        raise PermissionError("H27 embedded archive must contain exactly eight payloads.")
    payloads: dict[str, bytes] = {}
    for row, identity in zip(rows, PAYLOADS):
        if type(row) is not dict or set(row) != {"path", "git_blob_sha1", "size_bytes", "raw_sha256", "base64"}:
            raise PermissionError("H27 embedded payload schema mismatch.")
        projected = {key: row[key] for key in ("path", "git_blob_sha1", "size_bytes", "raw_sha256")}
        if projected != identity or type(row["base64"]) is not str:
            raise PermissionError("H27 embedded payload identity mismatch.")
        try:
            raw = base64.b64decode(row["base64"].encode("ascii"), validate=True)
        except (UnicodeEncodeError, ValueError) as exc:
            raise PermissionError("H27 embedded payload encoding mismatch.") from exc
        if base64.b64encode(raw).decode("ascii") != row["base64"] or not identity_ok(identity, raw):
            raise PermissionError("H27 embedded payload bytes mismatch.")
        payloads[str(identity["git_blob_sha1"])] = raw
    if len(payloads) != 8:
        raise PermissionError("H27 requires eight unique buffered payloads.")
    for identity in PAYLOADS:
        raw = payloads[str(identity["git_blob_sha1"])]
        calculated = target_git(["hash-object", "--stdin"], stdin=raw).stdout
        if calculated != (str(identity["git_blob_sha1"]) + "\n").encode("ascii"):
            raise PermissionError("H27 target Git hash-object prevalidation mismatch.")
    return payloads


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


def require_target_commit() -> None:
    if target_git(["cat-file", "-t", TARGET_HEAD]).stdout != b"commit\n":
        raise PermissionError("H27 exact target commit is unavailable.")


def perform_single_explicit_detach() -> None:
    result = run_git([
        "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
        "-C", CHECKOUT_TEXT, "checkout", "--detach", "--no-recurse-submodules", TARGET_HEAD,
    ])
    if result.returncode != 0:
        raise PermissionError("H27 exact detach failed; terminal consumed failure.")


def require_terminal_detached_state() -> None:
    if target_git(["rev-parse", "--verify", "HEAD"]).stdout != (TARGET_HEAD + "\n").encode("ascii"):
        raise PermissionError("H27 terminal target HEAD mismatch.")
    symbolic = target_git(["symbolic-ref", "-q", "HEAD"], expected=(0, 1))
    if symbolic.returncode != 1 or symbolic.stdout != b"":
        raise PermissionError("H27 terminal checkout is not detached.")
    if target_worktree_git(["status", "--porcelain=v1", "--untracked-files=all"]).stdout != b"":
        raise PermissionError("H27 terminal worktree is not clean.")
    if (GIT_DATABASE / "index.lock").exists():
        raise PermissionError("H27 terminal index lock is present.")
    index_snapshot()


def require_only_head_root_ref_changed(root_before: tuple[tuple[bytes, bytes], ...]) -> None:
    before = dict(root_before)
    after = dict(root_refs_snapshot())
    expected_head = (TARGET_HEAD + "\n").encode("ascii")
    if before.pop(b"HEAD", None) is None or after.pop(b"HEAD", None) != expected_head or after != before:
        raise PermissionError("H27 unexpected terminal root ref or pseudoref drift.")


def import_and_detach_once() -> dict[str, object]:
    require_platform_ack_and_zero_arguments()
    verify_checkout_and_odb_realpaths()
    require_reference_storage_files()
    require_baseline()
    regular_before = regular_refs_snapshot()
    root_before = root_refs_snapshot()
    index_before = index_snapshot()
    require_conflicting_runner_absent()
    payloads = decode_and_prevalidate_all()
    require_target_commit()
    require_reference_storage_files()
    require_baseline()
    if regular_refs_snapshot() != regular_before or root_refs_snapshot() != root_before or index_snapshot() != index_before:
        raise PermissionError("H27 target refs or index changed before first write.")
    require_conflicting_runner_absent()
    require_all_target_blobs_absent()
    objects_before = object_paths_snapshot()

    # First irreversible effect. Any failure from here is terminal and consumed.
    write_exact_payloads(payloads)
    require_all_target_blobs_exact()
    require_reference_storage_files()
    require_baseline()
    if regular_refs_snapshot() != regular_before or root_refs_snapshot() != root_before or index_snapshot() != index_before:
        raise PermissionError("H27 terminal refs or index drift; terminal consumed failure.")
    require_conflicting_runner_absent()
    objects_after = object_paths_snapshot()
    expected_new = {"objects/" + str(item["git_blob_sha1"])[:2] + "/" + str(item["git_blob_sha1"])[2:] for item in PAYLOADS}
    if set(objects_after) != set(objects_before) | expected_new or any(objects_after[path] != metadata for path, metadata in objects_before.items()):
        raise PermissionError("H27 unexpected target object database change; terminal consumed failure.")
    if regular_refs_snapshot() != regular_before:
        raise PermissionError("H27 regular refs drifted before detach; terminal consumed failure.")

    # Second and final mutation in the same one-shot process. No retry, reset,
    # cleanup, repair, or automatic recovery follows any failure.
    perform_single_explicit_detach()
    require_terminal_detached_state()
    require_only_head_root_ref_changed(root_before)
    if regular_refs_snapshot() != regular_before:
        raise PermissionError("H27 regular refs drifted after detach; terminal consumed failure.")
    return {
        "status": "H27_TARGET_EXACT_EIGHT_BLOB_IMPORT_AND_DETACH_TERMINAL_SUCCESS",
        "payload_count": 8,
        "payload_blob_ids": [item["git_blob_sha1"] for item in PAYLOADS],
        "payload_source": "embedded_byte_exact_archive",
        "target_git_database": GIT_DATABASE_TEXT,
        "initial_head": INITIAL_HEAD,
        "target_head": TARGET_HEAD,
        "detached": True,
        "regular_refs_unchanged": True,
        "worktree_clean": True,
        "registry_opened": False,
        "authority_reserved": False,
        "creator_invoked": False,
        "control_bundle_created": False,
        "materializer_executed": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(import_and_detach_once(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
