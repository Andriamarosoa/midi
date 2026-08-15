#!/usr/bin/env python3
"""One-shot local Windows transition for dormant H27 sender preparation."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import stat
import subprocess
import sys
from typing import Mapping, Sequence

import psutil


ACK_ENV = "H27_WINDOWS_LOCAL_SENDER_TRANSITION_EXECUTE"
SENDER_ACK_ENV = "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARE"
WORKTREE_TEXT = r"C:\Users\user\Desktop\midi\tmp\local\worktrees\independent-note-neural-v2"
WORKTREE = Path(WORKTREE_TEXT)
COMMON_GIT_DIR = Path(r"C:\Users\user\Desktop\midi\.git")
INDEX_PATH = COMMON_GIT_DIR / "worktrees" / "independent-note-neural-v2" / "index"
INDEX_LOCK = Path(str(INDEX_PATH) + ".lock")
INDEX_TEMP = Path(str(INDEX_PATH) + ".h27-windows-transition-restore.tmp")
HEAD_LOG = COMMON_GIT_DIR / "worktrees" / "independent-note-neural-v2" / "logs" / "HEAD"
BRANCH_LOG = COMMON_GIT_DIR / "logs" / "refs" / "heads" / "codex" / "independent-note-neural-v2"
ORIG_HEAD = COMMON_GIT_DIR / "worktrees" / "independent-note-neural-v2" / "ORIG_HEAD"
INITIAL = "61dc4b496a454b596fca6ac361504f441e987aab"
INITIAL_TREE = "b3443b500f9cb3ec26951627c79cb292e99d78a1"
HISTORICAL = "c0bb8d20862f80cabc72ea64a5d437750b7c12e8"
HISTORICAL_TREE = "714601093597b7d7560ea619d660d533b347cbfd"
BRANCH = "refs/heads/codex/independent-note-neural-v2"
REMOTE_TRACKING = "refs/remotes/origin/codex/independent-note-neural-v2"
PYTHON_EXACT = r"C:\Users\user\Desktop\midi\.venv\Scripts\python.exe"
GIT_PREFIX = (
    "git", "--no-optional-locks", "--no-replace-objects", "-C", WORKTREE_TEXT,
)
BINARY_FLAG = getattr(os, "O_BINARY", 0)

IDENTITY_KEYS = {"path", "git_blob_sha1", "size_bytes", "raw_sha256"}
GRAPH_IDENTITIES = (
    {"path":"scripts/h27_prepare_exact_thirteen_source_odb_delivery.py","git_blob_sha1":"b59564dac93954976bd0d7028e01316fcd556592","size_bytes":13580,"raw_sha256":"a58ac7f3dad832691c47855e777f3ff971650f1d02b82aecd3f3eb1682ab71aa"},
    {"path":"configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_sender_identity_binding.json","git_blob_sha1":"7f7a4713ce44a9ae5779013de4de3e42dc643679","size_bytes":4777,"raw_sha256":"8e6a27a58e4d998b8c22eb775fa656bd7d530a8afdf1dd967e937777cabe7912"},
    {"path":"configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_sender_identity_binding_external_seal.json","git_blob_sha1":"80c74882b66ca486b79ae9d53a48e30dda26fd19","size_bytes":4697,"raw_sha256":"59ef9621ef3af7dd65423ced648b2be52919e0d34b22bd5e8d309c8af6f1b8be"},
    {"path":"configs/harmonic_censoring_h27_windows_local_sender_transition_contract.json","git_blob_sha1":"f1a394bb9c764e0d1942f10cf36711517dcb5f4b","size_bytes":10871,"raw_sha256":"499fb31e73c5fc8b371d9c0a2f860e58dd614b58afa0cbca900755c19d3f1a70"},
    {"path":"configs/harmonic_censoring_h27_windows_local_sender_transition_contract_external_seal.json","git_blob_sha1":"eb5888e8f03b3c558dd3fcedc6d4bf44c898b911","size_bytes":5828,"raw_sha256":"415b140882a981ee2dd0ab3ca0c4aeedf14eeeaeb1832d5eb9b92fef02371fd6"},
    {"path":"scripts/h27_receive_exact_thirteen_source_odb_blobs_one_shot.py","git_blob_sha1":"9d32cac8ddb29e43975a6b82f5c1c39a91f93df4","size_bytes":119406,"raw_sha256":"996c4539a357b13af65012de84ed836179389f111dd1849eb1ca165d15374000"},
    {"path":"configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_receiver_identity_binding.json","git_blob_sha1":"676b04ce154b2210b714f87d20ae191017aa57c1","size_bytes":6625,"raw_sha256":"47914c545457de3622d4c7aedf96cc5b457b2eb937f4ae95c970f5ff98bfe67b"},
    {"path":"configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_receiver_identity_binding_external_seal.json","git_blob_sha1":"60242774586277d9eccd8049d8d7c0062e08942b","size_bytes":6040,"raw_sha256":"e9d30ee756843fc9475a08673ca0415e7aa88a4ff9928f409c5b2d1b160d5ec6"},
    {"path":"configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract.json","git_blob_sha1":"83fba2bc54bb22712680453bc3253b85aca50ca4","size_bytes":10717,"raw_sha256":"c538c3567f46993f8a1a420a272db552d07ea7e2f2362142700d9670b31f0df2"},
    {"path":"configs/harmonic_censoring_h27_external_source_odb_exact_thirteen_blob_delivery_contract_external_seal.json","git_blob_sha1":"b579a3604e1aa08d9485d10585ebba24febdf446","size_bytes":5112,"raw_sha256":"5c6535d8178f03cee8f91e14fac448567603900cca2e1261758e10ae13166daa"},
)
SENDER_OID = "b59564dac93954976bd0d7028e01316fcd556592"


class ConsumedTransitionFailure(RuntimeError):
    """The first reset was attempted, restoration succeeded, and retry is forbidden."""


class RestorationFailure(RuntimeError):
    """The single mandatory restoration attempt failed and manual action is required."""


def clean_git_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    inherited = dict(os.environ if source is None else source)
    cleaned = {key: value for key, value in inherited.items() if not key.upper().startswith("GIT_")}
    cleaned["GIT_TERMINAL_PROMPT"] = "0"
    cleaned["GIT_NO_LAZY_FETCH"] = "1"
    return cleaned


def run_git(arguments: Sequence[str]) -> subprocess.CompletedProcess[bytes]:
    forbidden = {"push", "fetch", "pull", "clone", "ls-remote"}
    if any(argument in forbidden for argument in arguments):
        raise PermissionError("network Git operations are forbidden")
    command = [*GIT_PREFIX, *arguments]
    if tuple(command[:len(GIT_PREFIX)]) != GIT_PREFIX:
        raise PermissionError("Git repository selector prefix drift")
    result = subprocess.run(
        command, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        env=clean_git_environment(),
    )
    if result.stderr != b"":
        raise RuntimeError("Git command emitted stderr")
    return result


def git_blob_id(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def require_identity(raw: bytes, expected: Mapping[str, object]) -> None:
    if set(expected) != IDENTITY_KEYS:
        raise ValueError("identity key set drift")
    if len(raw) != expected["size_bytes"]:
        raise ValueError(f"size mismatch for {expected['path']}")
    if hashlib.sha256(raw).hexdigest() != expected["raw_sha256"]:
        raise ValueError(f"SHA-256 mismatch for {expected['path']}")
    if git_blob_id(raw) != expected["git_blob_sha1"]:
        raise ValueError(f"Git blob mismatch for {expected['path']}")


def read_exact_blob(expected: Mapping[str, object]) -> bytes:
    raw = run_git(("cat-file", "blob", str(expected["git_blob_sha1"]))).stdout
    require_identity(raw, expected)
    return raw


def reject_duplicate_keys(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def parse_strict_json(raw: bytes, label: str) -> dict[str, object]:
    def reject_constant(value: str) -> object:
        raise ValueError(f"non-finite JSON constant in {label}: {value}")
    value = json.loads(
        raw.decode("utf-8"), object_pairs_hook=reject_duplicate_keys,
        parse_constant=reject_constant,
    )
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def require_platform_ack_and_zero_arguments() -> None:
    if platform.system().lower() != "windows":
        raise PermissionError("H27 local transition requires Windows")
    if os.environ.get(ACK_ENV) != "1":
        raise PermissionError(f"set {ACK_ENV}=1")
    if len(sys.argv) != 1:
        raise PermissionError("H27 local transition accepts zero arguments")


def require_paths_and_locks() -> None:
    if WORKTREE.resolve(strict=True) != Path(WORKTREE_TEXT).resolve(strict=True):
        raise PermissionError("execution worktree realpath mismatch")
    if COMMON_GIT_DIR.resolve(strict=True) != Path(r"C:\Users\user\Desktop\midi\.git").resolve(strict=True):
        raise PermissionError("common Git directory realpath mismatch")
    metadata = INDEX_PATH.lstat()
    if not stat.S_ISREG(metadata.st_mode) or INDEX_PATH.is_symlink():
        raise PermissionError("execution index must be a real regular file")
    if INDEX_LOCK.exists() or INDEX_TEMP.exists():
        raise PermissionError("index lock or transition temporary index already exists")


def require_no_conflicting_process() -> None:
    own = psutil.Process()
    excluded = {own.pid}
    excluded.update(parent.pid for parent in own.parents())
    needle = WORKTREE_TEXT.lower()
    for process in psutil.process_iter(("pid", "name", "cmdline")):
        try:
            if process.info["pid"] in excluded:
                continue
            command = " ".join(process.info.get("cmdline") or []).lower()
            name = str(process.info.get("name") or "").lower()
        except (psutil.AccessDenied, psutil.NoSuchProcess, psutil.ZombieProcess):
            continue
        if needle in command and ("git" in name or "git " in command or "h27" in command):
            raise PermissionError(f"conflicting process present: {process.info['pid']}")


def basic_state(expected_head: str, expected_tree: str) -> dict[str, bytes]:
    state = {
        "head": run_git(("rev-parse", "HEAD")).stdout,
        "tree": run_git(("rev-parse", f"{expected_head}^{{tree}}")).stdout,
        "symbolic": run_git(("symbolic-ref", "-q", "HEAD")).stdout,
        "local_ref": run_git(("rev-parse", BRANCH)).stdout,
        "remote_ref": run_git(("rev-parse", REMOTE_TRACKING)).stdout,
        "status": run_git(("status", "--porcelain=v1", "-z", "--untracked-files=all")).stdout,
    }
    if state["head"] != (expected_head + "\n").encode("ascii"):
        raise PermissionError("HEAD mismatch")
    if state["tree"] != (expected_tree + "\n").encode("ascii"):
        raise PermissionError("commit tree mismatch")
    if state["symbolic"] != (BRANCH + "\n").encode("utf-8"):
        raise PermissionError("symbolic HEAD mismatch")
    if state["local_ref"] != (expected_head + "\n").encode("ascii"):
        raise PermissionError("local branch ref mismatch")
    if state["remote_ref"] != (INITIAL + "\n").encode("ascii"):
        raise PermissionError("remote-tracking ref mismatch")
    if state["status"] != b"":
        raise PermissionError("execution worktree is not clean")
    if INDEX_LOCK.exists() or INDEX_TEMP.exists():
        raise PermissionError("index lock or transition temporary index present")
    return state


def tracked_snapshot() -> tuple[tuple[object, ...], ...]:
    raw = run_git(("ls-files", "-s", "-z")).stdout
    entries: list[tuple[object, ...]] = []
    for record in raw.split(b"\0"):
        if not record:
            continue
        metadata, encoded_path = record.split(b"\t", 1)
        mode, oid, stage = metadata.decode("ascii").split(" ")
        if stage != "0":
            raise PermissionError("non-stage-zero index entry")
        relative = encoded_path.decode("utf-8", "surrogateescape")
        path = WORKTREE / relative
        if mode == "160000":
            entries.append((relative, mode, oid, "gitlink", 0, "", b""))
            continue
        info = path.lstat()
        if mode == "120000":
            if not path.is_symlink():
                raise PermissionError(f"expected symlink: {relative}")
            content = os.readlink(path).encode("utf-8", "surrogateescape")
            kind = "symlink"
        else:
            if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                raise PermissionError(f"expected regular tracked file: {relative}")
            content = path.read_bytes()
            kind = "regular"
        entries.append((relative, mode, oid, kind, len(content), hashlib.sha256(content).hexdigest(), content))
    return tuple(entries)


def object_paths_snapshot() -> tuple[tuple[object, ...], ...]:
    objects = COMMON_GIT_DIR / "objects"
    rows: list[tuple[object, ...]] = []
    for root, directories, files in os.walk(objects):
        directories.sort()
        files.sort()
        for name in files:
            path = Path(root) / name
            info = path.lstat()
            if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                raise PermissionError("non-regular Git object database entry")
            rows.append((
                path.relative_to(COMMON_GIT_DIR).as_posix(), info.st_dev, info.st_ino,
                info.st_mode, info.st_size, info.st_mtime_ns,
            ))
    return tuple(rows)


def reflog_snapshot() -> tuple[tuple[str, bytes], ...]:
    roots = (COMMON_GIT_DIR / "logs", HEAD_LOG.parent)
    rows: dict[str, bytes] = {}
    for root in roots:
        for directory, directories, files in os.walk(root):
            directories.sort()
            files.sort()
            for name in files:
                path = Path(directory) / name
                info = path.lstat()
                if not stat.S_ISREG(info.st_mode) or path.is_symlink():
                    raise PermissionError("non-regular reflog entry")
                rows[str(path)] = path.read_bytes()
    if str(HEAD_LOG) not in rows or str(BRANCH_LOG) not in rows:
        raise PermissionError("required HEAD or branch reflog absent")
    return tuple(sorted(rows.items()))


def capture_snapshot() -> dict[str, object]:
    state = basic_state(INITIAL, INITIAL_TREE)
    index_raw = INDEX_PATH.read_bytes()
    return {
        "state": state,
        "refs": run_git(("for-each-ref", "--sort=refname", "--format=%(refname)%00%(objectname)%00%(objecttype)%00")).stdout,
        "index_raw": index_raw,
        "index_size": len(index_raw),
        "index_sha256": hashlib.sha256(index_raw).hexdigest(),
        "index_entries": run_git(("ls-files", "-s", "-z")).stdout,
        "tracked_snapshot": tracked_snapshot(),
        "objects": object_paths_snapshot(),
        "reflogs": reflog_snapshot(),
        "orig_head": ORIG_HEAD.read_bytes() if ORIG_HEAD.exists() else None,
    }


def load_prevalidated_graph() -> dict[str, bytes]:
    graph = {str(identity["git_blob_sha1"]): read_exact_blob(identity) for identity in GRAPH_IDENTITIES}
    contract = parse_strict_json(graph["f1a394bb9c764e0d1942f10cf36711517dcb5f4b"], "transition contract")
    seal = parse_strict_json(graph["eb5888e8f03b3c558dd3fcedc6d4bf44c898b911"], "transition seal")
    if contract.get("approved_sender") != GRAPH_IDENTITIES[0]:
        raise ValueError("transition contract sender identity drift")
    if seal.get("contract") != GRAPH_IDENTITIES[3]:
        raise ValueError("transition seal contract identity drift")
    return graph


def execute_sender_once(sender_raw: bytes) -> dict[str, object]:
    environment = clean_git_environment()
    environment[SENDER_ACK_ENV] = "1"
    result = subprocess.run(
        [PYTHON_EXACT, "-"], input=sender_raw, cwd=WORKTREE_TEXT,
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=environment,
    )
    if result.returncode != 0 or result.stderr != b"":
        raise RuntimeError(
            f"sender preparation failed rc={result.returncode}; "
            f"stdout_sha256={hashlib.sha256(result.stdout).hexdigest()}; "
            f"stderr_sha256={hashlib.sha256(result.stderr).hexdigest()}"
        )
    if result.stdout.count(b"\n") != 1 or not result.stdout.endswith(b"\n"):
        raise ValueError("sender stdout must be exactly one JSON line")
    report = parse_strict_json(result.stdout, "sender report")
    required = {
        "status": "H27_SOURCE_ODB_EXACT_THIRTEEN_SENDER_PREPARED_DORMANT_STOP",
        "transport_executed": False,
        "remote_acknowledgement_set": False,
        "object_delivery_executed": False,
        "source_odb_changed": False,
        "target_odb_changed": False,
        "science_or_locked_test": False,
    }
    for key, expected in required.items():
        if report.get(key) != expected:
            raise ValueError(f"sender terminal report mismatch: {key}")
    return report


def reset_hard_once(commit: str) -> None:
    if commit not in {INITIAL, HISTORICAL}:
        raise PermissionError("unsealed reset target")
    result = run_git(("reset", "--hard", commit))
    if result.stderr != b"":
        raise RuntimeError("reset emitted stderr")


def restore_index_raw_once(index_raw: bytes) -> None:
    if INDEX_TEMP.exists():
        raise PermissionError("transition temporary index already exists")
    descriptor = os.open(
        INDEX_TEMP, os.O_WRONLY | os.O_CREAT | os.O_EXCL | BINARY_FLAG, 0o600,
    )
    try:
        view = memoryview(index_raw)
        written = 0
        while written < len(view):
            written += os.write(descriptor, view[written:])
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    os.replace(INDEX_TEMP, INDEX_PATH)


def restore_tracked_raw_once(entries: Sequence[tuple[object, ...]]) -> None:
    suffix = ".h27-windows-tracked-restore.tmp"
    for entry in entries:
        relative, _mode, _oid, kind, _size, _sha256, content = entry
        if kind == "gitlink":
            continue
        if not isinstance(relative, str) or not isinstance(content, bytes):
            raise RestorationFailure("invalid retained tracked entry")
        path = WORKTREE / relative
        temporary = Path(str(path) + suffix)
        if temporary.exists() or temporary.is_symlink():
            raise RestorationFailure(f"tracked restore temporary exists: {relative}")
        if kind == "symlink":
            current = os.readlink(path).encode("utf-8", "surrogateescape") if path.is_symlink() else None
            if current == content:
                continue
            os.symlink(content.decode("utf-8", "surrogateescape"), temporary)
            os.replace(temporary, path)
            continue
        if kind != "regular":
            raise RestorationFailure(f"unexpected tracked kind: {kind}")
        if path.is_file() and not path.is_symlink() and path.read_bytes() == content:
            continue
        descriptor = os.open(
            temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | BINARY_FLAG, 0o600,
        )
        try:
            view = memoryview(content)
            written = 0
            while written < len(view):
                written += os.write(descriptor, view[written:])
            os.fsync(descriptor)
        finally:
            os.close(descriptor)
        os.replace(temporary, path)


def require_exact_reset_reflog_append(
    before: bytes, after: bytes, log_label: str,
) -> None:
    if not after.startswith(before):
        raise RestorationFailure(f"{log_label} reflog prefix changed")
    appended = after[len(before):].splitlines(keepends=True)
    expected = ((INITIAL, HISTORICAL), (HISTORICAL, INITIAL))
    if len(appended) != len(expected):
        raise RestorationFailure(f"{log_label} reflog append count differs")
    for line, (old, new) in zip(appended, expected):
        prefix = f"{old} {new} ".encode("ascii")
        suffix = f"\treset: moving to {new}\n".encode("ascii")
        if not line.startswith(prefix) or not line.endswith(suffix):
            raise RestorationFailure(f"{log_label} reset transition differs")
        identity = line[len(prefix):-len(suffix)]
        if not identity or b"\n" in identity or b"\r" in identity or b"\t" in identity:
            raise RestorationFailure(f"{log_label} reflog identity invalid")


def verify_administrative_delta(snapshot: Mapping[str, object]) -> None:
    before = dict(snapshot["reflogs"])
    after = dict(reflog_snapshot())
    if set(after) != set(before):
        raise RestorationFailure("reflog path set changed")
    head_key = str(HEAD_LOG)
    branch_key = str(BRANCH_LOG)
    for path, raw in before.items():
        if path not in {head_key, branch_key} and after[path] != raw:
            raise RestorationFailure(f"unexpected reflog changed: {path}")
    require_exact_reset_reflog_append(before[head_key], after[head_key], "HEAD")
    require_exact_reset_reflog_append(before[branch_key], after[branch_key], "branch")
    if ORIG_HEAD.read_bytes() != (HISTORICAL + "\n").encode("ascii"):
        raise RestorationFailure("ORIG_HEAD does not identify the second reset source")


def verify_restored(snapshot: Mapping[str, object]) -> None:
    state = basic_state(INITIAL, INITIAL_TREE)
    if state != snapshot["state"]:
        raise RestorationFailure("restored basic state differs from snapshot")
    index_raw = INDEX_PATH.read_bytes()
    if index_raw != snapshot["index_raw"]:
        raise RestorationFailure("restored index raw bytes differ")
    if run_git(("ls-files", "-s", "-z")).stdout != snapshot["index_entries"]:
        raise RestorationFailure("restored index entries differ")
    if run_git(("for-each-ref", "--sort=refname", "--format=%(refname)%00%(objectname)%00%(objecttype)%00")).stdout != snapshot["refs"]:
        raise RestorationFailure("restored refs differ")
    if tracked_snapshot() != snapshot["tracked_snapshot"]:
        raise RestorationFailure("restored tracked bytes or modes differ")
    if object_paths_snapshot() != snapshot["objects"]:
        raise RestorationFailure("unexpected Git object database change")
    verify_administrative_delta(snapshot)
    if INDEX_LOCK.exists() or INDEX_TEMP.exists():
        raise RestorationFailure("lock or temporary index remains")


def run_one_shot_transition() -> dict[str, object]:
    require_platform_ack_and_zero_arguments()
    require_paths_and_locks()
    require_no_conflicting_process()
    snapshot = capture_snapshot()
    graph = load_prevalidated_graph()
    if capture_snapshot() != snapshot:
        raise PermissionError("initial state drift before first effect")

    first_effect_started = False
    primary_error: BaseException | None = None
    sender_report: dict[str, object] | None = None
    restoration_error: BaseException | None = None
    try:
        first_effect_started = True
        reset_hard_once(HISTORICAL)
        basic_state(HISTORICAL, HISTORICAL_TREE)
        require_no_conflicting_process()
        sender_report = execute_sender_once(graph[SENDER_OID])
    except BaseException as error:
        primary_error = error
    finally:
        if first_effect_started:
            try:
                reset_hard_once(INITIAL)
                restore_tracked_raw_once(snapshot["tracked_snapshot"])
                restore_index_raw_once(snapshot["index_raw"])
                verify_restored(snapshot)
            except BaseException as error:
                restoration_error = error

    if restoration_error is not None:
        raise RestorationFailure(
            "single mandatory restoration attempt failed; manual intervention required; "
            f"primary={type(primary_error).__name__ if primary_error else 'none'}; "
            f"restoration={type(restoration_error).__name__}"
        ) from restoration_error
    if primary_error is not None:
        raise ConsumedTransitionFailure(
            "transition consumed and exactly restored after failure; retry forbidden; "
            f"cause={type(primary_error).__name__}"
        ) from primary_error
    if sender_report is None:
        raise ConsumedTransitionFailure("sender report missing after consumed transition")
    return {
        "status": "H27_WINDOWS_LOCAL_SENDER_TRANSITION_TERMINAL_SUCCESS_RESTORED_STOP",
        "initial_head": INITIAL,
        "historical_head_materialized_once": HISTORICAL,
        "sender_status": sender_report["status"],
        "transport_executed": False,
        "restoration_executed": True,
        "restored_head": INITIAL,
        "branch_restored": True,
        "index_restored_byte_exact": True,
        "tracked_worktree_restored_byte_exact": True,
        "remote_tracking_ref_unchanged": True,
        "ssh_invoked": False,
        "remote_acknowledgement_set": False,
        "object_delivery_executed": False,
        "science_or_locked_test": False,
    }


def main() -> int:
    report = run_one_shot_transition()
    print(json.dumps(report, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
