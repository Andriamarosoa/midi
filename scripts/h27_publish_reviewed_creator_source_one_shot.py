#!/usr/bin/env python3
"""One-shot publication of the reviewed H27 creator source on macOS."""
from __future__ import annotations

import ast
import base64
import ctypes
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
import zlib


ACK_ENV = "H27_REVIEWED_CREATOR_SOURCE_PUBLISH_EXECUTE"
GIT_DATABASE = Path("/Users/amcarene/midi-worker/repository/.git")
CREATOR_PARENT = Path("/Users/amcarene/h27-admin/creator")
FINAL_ROOT = CREATOR_PARENT / "h27-reviewed-control-bundle-creator-v1"
STAGING_ROOT = CREATOR_PARENT / ".h27-reviewed-control-bundle-creator-v1.staging"
ENTRYPOINT_NAME = "h27_reviewed_control_bundle_creator.py"
MANIFEST_NAME = "manifest.json"
RENAME_EXCL = 0x00000004
STAGING_NAME = ".h27-reviewed-control-bundle-creator-v1.staging"
FINAL_NAME = "h27-reviewed-control-bundle-creator-v1"

ROOT_IDENTITIES = (
    {"path":"configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_identity_binding.json","git_blob_sha1":"3eea754aeb355780e082e9de9bbdeec350b66152","size_bytes":6091,"raw_sha256":"0d0844952802dfe4b29c5c04104a4128c9a480171255f1aa6178a4cdbdd44367"},
    {"path":"configs/harmonic_censoring_h27_reviewed_control_bundle_creator_implementation_source_identity_binding_external_seal.json","git_blob_sha1":"aa3ebc704e5cb874cb09430eccdc5fc616ebb1cc","size_bytes":1649,"raw_sha256":"1dd748ed7dce831128b42f6d5c1646952f5aaff2cff912071f2853e7e6ab1d23"},
)
ENTRYPOINT_IDENTITY = {"path":"scripts/h27_reviewed_control_bundle_creator.py","git_blob_sha1":"2091028d44bf9c8e1ab05b7d6656719ebc260832","size_bytes":44063,"raw_sha256":"0f0dd5867c82b1237736d03f48a6176171c4459b9106bca251ab53778092e42f"}
CREATOR_CONTRACT_IDENTITY = {"git_blob_sha1":"cee37fbececa8387266ba693ae915aeb8ce3ac4e","size_bytes":9920,"raw_sha256":"8decca47ec6947951fddfb8becdaa550609fa50e2c12e310d7a4476210f583da"}
CREATOR_BINDING_IDENTITY = {"git_blob_sha1":"b5ec9c1c65e1f15a8eff65fec7749d808c1193ae","size_bytes":3248,"raw_sha256":"54a31600aa1898d946b57bcda5330993e6740a642aec5f1a7ca35d5bb96b380c"}


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
    if type(value) is not list or len(value) != count:
        raise PermissionError(f"H27 {label} identity count mismatch.")
    result: list[dict[str, object]] = []
    for identity in value:
        if type(identity) is not dict:
            raise PermissionError(f"H27 malformed identity in {label}.")
        result.append(identity)
    return result


def embedded_predecessors(entrypoint: bytes) -> list[dict[str, object]]:
    try:
        tree = ast.parse(entrypoint.decode("utf-8"))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise PermissionError("H27 reviewed entrypoint is not parseable Python.") from exc
    encoded: list[str] = []
    for node in tree.body:
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and node.targets[0].id == "_IDENTITY_GRAPH_B85"
            and isinstance(node.value, ast.Constant)
            and type(node.value.value) is str
        ):
            encoded.append(node.value.value)
    if len(encoded) != 1:
        raise PermissionError("H27 embedded predecessor graph constant mismatch.")
    try:
        raw = zlib.decompress(base64.b85decode(encoded[0])).decode("ascii")
        value = json.loads(raw)
    except (ValueError, UnicodeDecodeError, zlib.error, json.JSONDecodeError) as exc:
        raise PermissionError("H27 embedded predecessor graph is invalid.") from exc
    return exact_identity_list(value, 130, "embedded predecessor")


def verify_identity_graph() -> dict[str, bytes]:
    roots: dict[str, bytes] = {}
    for identity in ROOT_IDENTITIES:
        raw = read_blob(str(identity["git_blob_sha1"]))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 root identity mismatch: {identity['path']}.")
        roots[str(identity["path"])] = raw

    binding = parse_object(roots[str(ROOT_IDENTITIES[0]["path"])], "source binding")
    seal = parse_object(roots[str(ROOT_IDENTITIES[1]["path"])], "source binding seal")
    if binding.get("implementation_entrypoint") != ENTRYPOINT_IDENTITY:
        raise PermissionError("H27 bound entrypoint identity mismatch.")
    if seal.get("identity_binding") != ROOT_IDENTITIES[0] or seal.get("implementation_entrypoint") != ENTRYPOINT_IDENTITY:
        raise PermissionError("H27 source binding seal mismatch.")
    if binding.get("bound_git_source", {}).get("source_git_object_database_exact") != str(GIT_DATABASE):
        raise PermissionError("H27 bound Git object database mismatch.")

    entrypoint = read_blob(str(ENTRYPOINT_IDENTITY["git_blob_sha1"]))
    if not identity_ok(ENTRYPOINT_IDENTITY, entrypoint):
        raise PermissionError("H27 reviewed entrypoint identity mismatch.")
    source_chain = exact_identity_list(binding.get("reviewed_source_contract_chain"), 4, "source chain")
    source_contract_raw = read_blob(str(source_chain[0].get("git_blob_sha1")))
    if not identity_ok(source_chain[0], source_contract_raw):
        raise PermissionError("H27 source contract identity mismatch.")
    source_contract = parse_object(source_contract_raw, "source contract")
    creator_chain = exact_identity_list(source_contract.get("reviewed_creator_chain"), 4, "creator chain")
    identities = [ENTRYPOINT_IDENTITY, *source_chain, *creator_chain, *embedded_predecessors(entrypoint)]
    paths = [identity.get("path") for identity in identities]
    if len(identities) != 139 or any(type(path) is not str for path in paths) or len(set(paths)) != 139:
        raise PermissionError("H27 requires exactly 139 unique reviewed identities.")

    verified: dict[str, bytes] = {}
    for identity in identities:
        path = str(identity["path"])
        raw = read_blob(str(identity.get("git_blob_sha1")))
        if not identity_ok(identity, raw):
            raise PermissionError(f"H27 identity mismatch: {path}.")
        verified[path] = raw
    return verified


def canonical_manifest() -> bytes:
    payload = {
        "schema_version": 1,
        "source_id": "H27_REVIEWED_CONTROL_BUNDLE_CREATOR_IMPLEMENTATION_SOURCE_V1",
        "reviewed_creator_contract_identity": CREATOR_CONTRACT_IDENTITY,
        "reviewed_creator_binding_identity": CREATOR_BINDING_IDENTITY,
        "root": str(FINAL_ROOT),
        "entrypoint": {
            "path": ENTRYPOINT_NAME,
            "git_blob_sha1": ENTRYPOINT_IDENTITY["git_blob_sha1"],
            "size_bytes": ENTRYPOINT_IDENTITY["size_bytes"],
            "raw_sha256": ENTRYPOINT_IDENTITY["raw_sha256"],
        },
    }
    raw = (json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    if raw.count(b"\n") != 1 or b"\r" in raw or raw.startswith(b"\xef\xbb\xbf"):
        raise AssertionError("H27 canonical manifest construction drift.")
    return raw


def require_environment() -> None:
    if sys.platform != "darwin" or os.environ.get(ACK_ENV) != "1" or len(sys.argv) != 1:
        raise PermissionError("H27 exact macOS one-shot acknowledgement required.")
    if not hasattr(os, "O_NOFOLLOW"):
        raise PermissionError("H27 no-follow access unavailable.")
    if GIT_DATABASE.resolve(strict=True) != GIT_DATABASE or GIT_DATABASE.is_symlink():
        raise PermissionError("H27 exact Git object database realpath mismatch.")


def open_verified_parent() -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(CREATOR_PARENT, flags)
    try:
        descriptor = os.fstat(fd)
        named = os.stat(CREATOR_PARENT, follow_symlinks=False)
        if (
            CREATOR_PARENT.resolve(strict=True) != CREATOR_PARENT
            or not stat.S_ISDIR(descriptor.st_mode)
            or not stat.S_ISDIR(named.st_mode)
            or (descriptor.st_dev, descriptor.st_ino) != (named.st_dev, named.st_ino)
            or CREATOR_PARENT.is_symlink()
        ):
            raise PermissionError("H27 creator parent realpath mismatch.")
        return fd
    except BaseException:
        os.close(fd)
        raise


def require_parent_fd_still_named(fd: int) -> None:
    descriptor = os.fstat(fd)
    named = os.stat(CREATOR_PARENT, follow_symlinks=False)
    if (
        not stat.S_ISDIR(descriptor.st_mode)
        or not stat.S_ISDIR(named.st_mode)
        or (descriptor.st_dev, descriptor.st_ino) != (named.st_dev, named.st_ino)
        or CREATOR_PARENT.resolve(strict=True) != CREATOR_PARENT
        or CREATOR_PARENT.is_symlink()
    ):
        raise PermissionError("H27 creator parent identity changed.")


def open_directory_at(parent_fd: int, name: str) -> int:
    flags = os.O_RDONLY | os.O_NOFOLLOW
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    fd = os.open(name, flags, dir_fd=parent_fd)
    descriptor = os.fstat(fd)
    if not stat.S_ISDIR(descriptor.st_mode):
        os.close(fd)
        raise PermissionError("H27 publication root is not a directory.")
    return fd


def write_exclusive(directory_fd: int, name: str, raw: bytes) -> None:
    fd = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o400, dir_fd=directory_fd)
    try:
        offset = 0
        while offset < len(raw):
            written = os.write(fd, raw[offset:])
            if written <= 0:
                raise OSError("H27 source write incomplete.")
            offset += written
        os.fsync(fd)
    finally:
        os.close(fd)


def read_verified_file(directory_fd: int, name: str, expected: bytes) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=directory_fd)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or before.st_size != len(expected):
            raise PermissionError("H27 published source file type mismatch.")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        stable_fields = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        if any(getattr(before, field) != getattr(after, field) for field in stable_fields) or raw != expected:
            raise PermissionError("H27 published source bytes changed or mismatched.")
        return raw
    finally:
        os.close(fd)


def verify_closed(root_fd: int, entrypoint: bytes, manifest: bytes) -> str:
    root_before = os.fstat(root_fd)
    actual = sorted(os.listdir(root_fd))
    if actual != sorted((ENTRYPOINT_NAME, MANIFEST_NAME)):
        raise PermissionError("H27 source path set is not closed.")
    expected = {ENTRYPOINT_NAME: entrypoint, MANIFEST_NAME: manifest}
    digest_lines = []
    for name in (ENTRYPOINT_NAME, MANIFEST_NAME):
        raw = read_verified_file(root_fd, name, expected[name])
        digest_lines.append(f"{name}\0{len(raw)}\0{sha256(raw)}\n")
    root_after = os.fstat(root_fd)
    if (
        sorted(os.listdir(root_fd)) != actual
        or (root_before.st_dev, root_before.st_ino, root_before.st_mtime_ns, root_before.st_ctime_ns)
        != (root_after.st_dev, root_after.st_ino, root_after.st_mtime_ns, root_after.st_ctime_ns)
    ):
        raise PermissionError("H27 source directory changed during verification.")
    return sha256("".join(digest_lines).encode("utf-8"))


def require_absent_at(parent_fd: int, name: str) -> None:
    try:
        os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        return
    raise FileExistsError(errno.EEXIST, "H27 source final or staging root already exists.", name)


def publish() -> dict[str, object]:
    require_environment()
    verified = verify_identity_graph()
    entrypoint = verified[ENTRYPOINT_IDENTITY["path"]]
    manifest = canonical_manifest()
    parent_fd = open_verified_parent()
    staging_fd: Optional[int] = None
    final_fd: Optional[int] = None
    try:
        # First and only pre-publication observation of the two roots, relative
        # to the already verified and now stable parent directory identity.
        require_absent_at(parent_fd, FINAL_NAME)
        require_absent_at(parent_fd, STAGING_NAME)

        # First irreversible effect.  No cleanup or retry follows any failure.
        require_parent_fd_still_named(parent_fd)
        os.mkdir(STAGING_NAME, mode=0o700, dir_fd=parent_fd)
        staging_fd = open_directory_at(parent_fd, STAGING_NAME)
        write_exclusive(staging_fd, ENTRYPOINT_NAME, entrypoint)
        write_exclusive(staging_fd, MANIFEST_NAME, manifest)
        os.fsync(staging_fd)
        staged_digest = verify_closed(staging_fd, entrypoint, manifest)
        staged_identity = os.fstat(staging_fd)

        libc = ctypes.CDLL(None, use_errno=True)
        renameatx_np = libc.renameatx_np
        renameatx_np.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
        renameatx_np.restype = ctypes.c_int
        if renameatx_np(parent_fd, os.fsencode(STAGING_NAME), parent_fd, os.fsencode(FINAL_NAME), RENAME_EXCL) != 0:
            error = ctypes.get_errno()
            raise OSError(error, os.strerror(error), FINAL_NAME)
        os.fsync(parent_fd)
        final_fd = open_directory_at(parent_fd, FINAL_NAME)
        final_identity = os.fstat(final_fd)
        if (final_identity.st_dev, final_identity.st_ino) != (staged_identity.st_dev, staged_identity.st_ino):
            raise PermissionError("H27 final directory identity mismatch.")
        final_digest = verify_closed(final_fd, entrypoint, manifest)
        if final_digest != staged_digest:
            raise PermissionError("H27 final source digest mismatch.")
        require_parent_fd_still_named(parent_fd)
    finally:
        if final_fd is not None:
            os.close(final_fd)
        if staging_fd is not None:
            os.close(staging_fd)
        os.close(parent_fd)
    return {
        "status": "H27_REVIEWED_CREATOR_SOURCE_PUBLISHED_TERMINAL_SUCCESS",
        "identity_count": 139,
        "entrypoint_git_blob_sha1": ENTRYPOINT_IDENTITY["git_blob_sha1"],
        "entrypoint_size_bytes": len(entrypoint),
        "entrypoint_raw_sha256": sha256(entrypoint),
        "manifest_size_bytes": len(manifest),
        "manifest_raw_sha256": sha256(manifest),
        "closed_source_digest": final_digest,
        "creator_entrypoint_executed": False,
        "registry_opened": False,
        "science_or_locked_test": False,
    }


if __name__ == "__main__":
    print(json.dumps(publish(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
