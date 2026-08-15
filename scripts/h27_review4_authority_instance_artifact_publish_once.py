#!/usr/bin/env python3
"""Dormant one-shot publisher for the exact consumed H27 authority instance.

Importing this module is inert.  A real macOS execution is impossible without
the dedicated acknowledgement and a separately reviewed invocation.  The
publisher never calls a clock or random source: it can only publish the exact
882 bytes produced by the already-consumed constructor gate.
"""
from __future__ import annotations

import ctypes
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import sys


ACK = "H27_REVIEW4_AUTHORITY_INSTANCE_ARTIFACT_PUBLISH_EXECUTE"
TARGET_TEXT = "/Users/amcarene/midi-worker/repository"
TARGET = Path(TARGET_TEXT)
GIT_DATABASE = TARGET / ".git"
REQUIRED_HEAD = "46a6bdf81a56a7a7a10524d4e55092301a452207"
DESTINATION_TEXT = "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json"
DESTINATION = Path(DESTINATION_TEXT)
STAGING_NAME = ".h27-materialization-v1.json.authority-instance-publication-stage"
CONSTRUCTOR_REGISTRY = Path(
    "/Users/amcarene/h27-admin/registry/"
    "h27-real-publication-constructor-execution-authority-v1.jsonl"
)
PUBLICATION_REGISTRY = Path(
    "/Users/amcarene/h27-admin/registry/"
    "h27-review4-authority-instance-artifact-publication-v1.jsonl"
)
RUNNER_NAME = "h27_review4_authority_instance_artifact_publish_once.py"
RENAME_EXCL = 0x00000004

EXECUTION_AUTHORITY_ID = "45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e"
AUTHORITY_INSTANCE_ID = "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a"
ISSUER_ID = "h27-execution-codex-mac-primary"
ISSUED_AT_UTC = "2026-08-16T08:36:14Z"
INVOCATION_NONCE = "c8c7dc8162910a140bc1699b488478b8f9f343a855973453671f6cacdfcea165"
CANONICAL_SIZE = 882
CANONICAL_BLOB = "dc85ee260763f9f9e65bbafbd776bf8611a67d9c"
CANONICAL_SHA256 = "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2"
PUBLICATION_AUTHORITY_ID = hashlib.sha256(
    ("H27_REVIEW4_AUTHORITY_INSTANCE_ARTIFACT_PUBLICATION_V1\0" + AUTHORITY_INSTANCE_ID + "\0" + CANONICAL_SHA256).encode("ascii")
).hexdigest()

SEALED_CHAIN_IDENTITY = {
    "contract_git_blob_sha1": "40757fa14d3df8b2aca2e12924faf7be329b9687",
    "contract_size_bytes": 5300,
    "contract_raw_sha256": "c23b4ceaf67dba8dc9d16ab7b279906823ae1b1259ba07aa8e8e2a2bf23210bb",
    "binding_git_blob_sha1": "41bb902d99379c0a518181e97056b4232abbc143",
    "binding_size_bytes": 3369,
    "binding_raw_sha256": "400a1010c4be36cbec585de0399137abca8b0b61f218946498d19fad23739e55",
}

TARGET_CHAIN_ROOTS = (
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_contract.json",
        "40757fa14d3df8b2aca2e12924faf7be329b9687", 5300,
        "c23b4ceaf67dba8dc9d16ab7b279906823ae1b1259ba07aa8e8e2a2bf23210bb",
    ),
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_contract_external_seal.json",
        "3d644e8eb2bc0ca8c71cb7c9d7302feb1c1c28c2", 1484,
        "ef3d3c4bf4d54a5b64b2a928c3fb36d79c9c52956c24844f43a83e307d4efc83",
    ),
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_contract_identity_binding.json",
        "41bb902d99379c0a518181e97056b4232abbc143", 3369,
        "400a1010c4be36cbec585de0399137abca8b0b61f218946498d19fad23739e55",
    ),
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_contract_identity_binding_external_seal.json",
        "0b844d82a91ee25c2bd3a883ed2c52d33bf9f23c", 1474,
        "fc171b26ce58f8a93c643ae5f430c572a247f37e2efab4313a394a3653b0ea99",
    ),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def strict_json(raw: bytes) -> dict[str, object]:
    def pairs(values: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in values:
            require(type(key) is str and key not in result, "H27 duplicate JSON key")
            result[key] = value
        return result

    def reject_constant(value: str) -> object:
        raise ValueError("H27 non-RFC8259 constant: " + value)

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
    require(type(value) is dict, "H27 JSON root must be an object")
    return value


def canonical_artifact_bytes() -> bytes:
    value = {
        "schema_version": 1,
        "artifact_type": "h27_real_publication_one_shot_execution_authority_instance",
        "authority_instance_id": AUTHORITY_INSTANCE_ID,
        "issuer_id": ISSUER_ID,
        "issued_at_utc": ISSUED_AT_UTC,
        "invocation_nonce": INVOCATION_NONCE,
        "canonical_destination_path": DESTINATION_TEXT,
        "sealed_chain_identity": dict(SEALED_CHAIN_IDENTITY),
        "single_use": True,
        "consumed": False,
    }
    raw = (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    require((len(raw), git_blob(raw), sha256(raw)) == (CANONICAL_SIZE, CANONICAL_BLOB, CANONICAL_SHA256), "H27 canonical authority-instance bytes mismatch")
    return raw


def write_all(fd: int, raw: bytes, label: str) -> None:
    require(type(raw) is bytes and raw, "H27 non-empty bytes required for " + label)
    view = memoryview(raw)
    offset = 0
    while offset < len(raw):
        written = os.write(fd, view[offset:])
        require(type(written) is int and written > 0, "H27 zero/invalid write for " + label + "; terminal consumed failure")
        offset += written
    require(offset == len(raw), "H27 incomplete write for " + label + "; terminal consumed failure")


def clean_environment() -> dict[str, str]:
    environment = dict(os.environ)
    for key in tuple(environment):
        if key.startswith("GIT_"):
            del environment[key]
    environment.update({"GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0"})
    return environment


def git_read(*arguments: str, allowed: tuple[int, ...] = (0,)) -> subprocess.CompletedProcess[bytes]:
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-replace-objects", "-c", "core.hooksPath=/dev/null", "-C", TARGET_TEXT, *arguments],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=clean_environment(),
    )
    require(result.returncode in allowed, "H27 Git read failed: " + repr(arguments))
    return result


def stable_regular_bytes(path: Path, required_mode: int | None = None) -> bytes:
    require(hasattr(os, "O_NOFOLLOW"), "H27 O_NOFOLLOW unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode), "H27 non-regular file: " + str(path))
        require(before.st_nlink == 1, "H27 hard link forbidden: " + str(path))
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), "H27 descriptor mismatch: " + str(path))
        if required_mode is not None:
            require(stat.S_IMODE(before.st_mode) == required_mode, "H27 mode mismatch: " + str(path))
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        stable = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, key) == getattr(after, key) for key in stable), "H27 file changed while read: " + str(path))
        return raw
    finally:
        os.close(fd)


def stable_regular_bytes_at(parent_fd: int, name: str, required_mode: int | None = None) -> bytes:
    fd = os.open(name, os.O_RDONLY | os.O_NOFOLLOW, dir_fd=parent_fd)
    try:
        before = os.fstat(fd)
        named = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode), "H27 relative entry is not regular")
        require(before.st_nlink == 1, "H27 relative hard link forbidden")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), "H27 relative descriptor mismatch")
        if required_mode is not None:
            require(stat.S_IMODE(before.st_mode) == required_mode, "H27 relative mode mismatch")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        stable = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, key) == getattr(after, key) for key in stable), "H27 relative file changed while read")
        return raw
    finally:
        os.close(fd)


def require_platform_ack_and_zero_arguments() -> None:
    require(sys.platform == "darwin", "H27 exact macOS runner required")
    require(len(sys.argv) == 1, "H27 zero arguments required")
    require(os.environ.get(ACK) == "1", "H27 authority-instance publication ACK required")


def verify_checkout() -> None:
    require(TARGET.resolve(strict=True) == TARGET and TARGET.is_dir() and not TARGET.is_symlink(), "H27 checkout realpath mismatch")
    require(GIT_DATABASE.resolve(strict=True) == GIT_DATABASE and GIT_DATABASE.is_dir() and not GIT_DATABASE.is_symlink(), "H27 Git database realpath mismatch")
    require(git_read("rev-parse", "--verify", "HEAD").stdout.decode("ascii").strip() == REQUIRED_HEAD, "H27 HEAD mismatch")
    symbolic = git_read("symbolic-ref", "-q", "HEAD", allowed=(0, 1))
    require(symbolic.returncode == 1 and symbolic.stdout == b"", "H27 checkout must be detached")
    require(git_read("status", "--porcelain=v1", "--untracked-files=all").stdout == b"", "H27 checkout must be clean")
    require(not (GIT_DATABASE / "index.lock").exists(), "H27 index.lock must be absent")


def _identity_tuple(value: dict[str, object]) -> tuple[str, str, int, str]:
    require({"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(value), "H27 identity fields missing")
    identity = (value["path"], value["git_blob_sha1"], value["size_bytes"], value["raw_sha256"])
    require(type(identity[0]) is str and type(identity[1]) is str and type(identity[2]) is int and type(identity[3]) is str, "H27 identity native type mismatch")
    return identity  # type: ignore[return-value]


def _read_graph_json(relative: str) -> dict[str, object]:
    require(not relative.startswith("/") and ".." not in Path(relative).parts, "H27 unsafe graph path: " + relative)
    # Traverse only the immutable object selected by the sealed detached HEAD.
    # The corresponding checkout path is re-read and rehashed below before any
    # authority consumption, so a pathname race cannot steer graph discovery.
    raw = git_read("cat-file", "blob", REQUIRED_HEAD + ":" + relative).stdout
    return strict_json(raw)


def _sixty_four(execution_roots: list[dict[str, object]]) -> list[dict[str, object]]:
    execution_contract = _read_graph_json(_identity_tuple(execution_roots[0])[0])
    destination_roots = execution_contract["reviewed_and_sealed_destination_contract_chain"]
    require(type(destination_roots) is list and len(destination_roots) >= 3, "H27 destination roots malformed")
    destination_binding = _read_graph_json(_identity_tuple(destination_roots[2])[0])
    destination_contract = _read_graph_json(_identity_tuple(destination_binding["reviewed_contract"])[0])
    dormant_roots = destination_contract["reviewed_and_sealed_dormant_boundary"]
    require(type(dormant_roots) is list, "H27 dormant roots malformed")
    old_binding = _read_graph_json(destination_contract["transitive_identity_source"]["path"])
    activation_roots = old_binding["upstream_roots"]
    require(type(activation_roots) is list and activation_roots, "H27 activation roots malformed")
    execution_binding = _read_graph_json(_identity_tuple(activation_roots[0])[0])
    simulator = execution_binding["reviewed_and_sealed_dormant_publication_simulator"]
    require(type(simulator) is list and len(simulator) == 4, "H27 simulator roots malformed")
    inherited = [execution_binding["reviewed_contract"], execution_binding["contract_external_seal"], *simulator]
    older_binding = _read_graph_json(execution_binding["transitive_upstream_binding"]["path"])
    older = older_binding["upstream_entries"]
    require(type(older) is list and len(older) == 48, "H27 older roots malformed")
    return [*destination_roots, *dormant_roots, *activation_roots, *inherited, *older]


def _eighty(issuer_binding: dict[str, object]) -> list[dict[str, object]]:
    roots = issuer_binding["upstream_roots"]
    require(type(roots) is list and roots, "H27 issuer upstream roots malformed")
    implementation_binding = _read_graph_json(_identity_tuple(roots[0])[0])
    implementation_contract = _read_graph_json(_identity_tuple(implementation_binding["reviewed_contract"])[0])
    issuance_roots = implementation_contract["reviewed_and_sealed_issuance_artifact_contract_chain"]
    require(type(issuance_roots) is list and issuance_roots, "H27 issuance roots malformed")
    issuance_contract = _read_graph_json(_identity_tuple(issuance_roots[0])[0])
    authority_roots = issuance_contract["reviewed_and_sealed_one_shot_authority_chain"]
    require(type(authority_roots) is list and authority_roots, "H27 authority roots malformed")
    authority_contract = _read_graph_json(_identity_tuple(authority_roots[0])[0])
    execution_roots = authority_contract["reviewed_and_sealed_execution_authorization_chain"]
    require(type(execution_roots) is list and execution_roots, "H27 execution roots malformed")
    return [
        *roots,
        implementation_binding["reviewed_contract"], implementation_binding["contract_external_seal"],
        *issuance_roots, *authority_roots, *execution_roots, *_sixty_four(execution_roots),
    ]


def _eighty_four(binding: dict[str, object]) -> list[dict[str, object]]:
    contract = _read_graph_json(_identity_tuple(binding["reviewed_contract"])[0])
    issuer_roots = contract["reviewed_and_sealed_effect_free_issuer_chain"]
    require(type(issuer_roots) is list and len(issuer_roots) >= 3, "H27 effect-free issuer roots malformed")
    issuer_binding = _read_graph_json(_identity_tuple(issuer_roots[2])[0])
    return [*issuer_roots, *_eighty(issuer_binding)]


def _eighty_eight(contract: dict[str, object]) -> list[dict[str, object]]:
    roots = contract["reviewed_and_sealed_real_issuance_authorization_chain"]
    require(type(roots) is list and len(roots) >= 3, "H27 real issuance roots malformed")
    authorization_binding = _read_graph_json(_identity_tuple(roots[2])[0])
    return [*roots, *_eighty_four(authorization_binding)]


def verify_ninety_two_target_identities() -> tuple[tuple[str, str, int, str], ...]:
    contract = _read_graph_json(TARGET_CHAIN_ROOTS[0][0])
    roots = [
        {"path": item[0], "git_blob_sha1": item[1], "size_bytes": item[2], "raw_sha256": item[3]}
        for item in TARGET_CHAIN_ROOTS
    ]
    entries = [*roots, *_eighty_eight(contract)]
    require(len(entries) == 92, "H27 predecessor identity count mismatch")
    identities = [_identity_tuple(item) for item in entries]
    require(len({item[0] for item in identities}) == 92, "H27 predecessor paths must be unique")
    verified: dict[str, tuple[str, str, int, str]] = {}
    for identity in identities:
        relative, blob_id, size, digest = identity
        require(not relative.startswith("/") and ".." not in Path(relative).parts, "H27 unsafe identity path: " + relative)
        raw = stable_regular_bytes(TARGET / relative)
        require((git_blob(raw), len(raw), sha256(raw)) == (blob_id, size, digest), "H27 target identity mismatch: " + relative)
        tree = git_read("ls-tree", REQUIRED_HEAD, relative).stdout.rstrip(b"\n").split(maxsplit=3)
        require(len(tree) == 4 and tree[1] == b"blob" and tree[2].decode("ascii") == blob_id, "H27 target tree identity mismatch: " + relative)
        verified[relative] = identity
    return tuple(verified[path] for path in sorted(verified))


def expected_constructor_registry_bytes() -> bytes:
    common = {
        "execution_authority_artifact_id": EXECUTION_AUTHORITY_ID,
        "authority_instance_id": AUTHORITY_INSTANCE_ID,
        "invocation_nonce": INVOCATION_NONCE,
        "issued_at_utc": ISSUED_AT_UTC,
        "canonical_sha256": CANONICAL_SHA256,
    }
    records = [
        {"schema_version": 1, "state": "reserved", **common},
        {"schema_version": 1, "state": "consumed", **common},
    ]
    return b"".join((json.dumps(item, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8") for item in records)


def open_verified_parent(path: Path) -> int:
    require(path.resolve(strict=True) == path and path.is_dir() and not path.is_symlink(), "H27 parent path mismatch: " + str(path))
    require(hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW"), "H27 directory FD safeguards unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        descriptor = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISDIR(descriptor.st_mode) and stat.S_ISDIR(named.st_mode), "H27 parent is not a directory")
        require((descriptor.st_dev, descriptor.st_ino) == (named.st_dev, named.st_ino), "H27 parent descriptor mismatch")
        return fd
    except BaseException:
        os.close(fd)
        raise


def reverify_parent(fd: int, path: Path) -> None:
    descriptor = os.fstat(fd)
    named = os.stat(path, follow_symlinks=False)
    require(stat.S_ISDIR(descriptor.st_mode) and stat.S_ISDIR(named.st_mode), "H27 parent type drift")
    require((descriptor.st_dev, descriptor.st_ino) == (named.st_dev, named.st_ino), "H27 parent identity drift")


def verify_constructor_terminal(registry_parent_fd: int) -> None:
    raw = stable_regular_bytes_at(registry_parent_fd, CONSTRUCTOR_REGISTRY.name, required_mode=0o600)
    require(raw == expected_constructor_registry_bytes(), "H27 consumed constructor registry mismatch")


def require_no_active_processes() -> None:
    raw = subprocess.run(["/bin/ps", "-axo", "pid=,command="], check=True, stdout=subprocess.PIPE).stdout
    forbidden = (
        RUNNER_NAME.encode("ascii"), b"h27_review4_constructor_execution_gate_once.py",
        b"harmonic_censoring_h27_population_materializer", b"run_harmonic_censoring_h27",
    )
    active: list[bytes] = []
    for line in raw.splitlines():
        fields = line.strip().split(maxsplit=1)
        require(len(fields) == 2 and fields[0].isdigit(), "H27 malformed process observation")
        if int(fields[0]) != os.getpid() and any(token in fields[1] for token in forbidden):
            active.append(line.strip())
    require(not active, "H27 competing publisher/materializer/science process active")


def preflight(registry_parent_fd: int) -> dict[str, object]:
    canonical = canonical_artifact_bytes()
    verify_checkout()
    identities = verify_ninety_two_target_identities()
    verify_constructor_terminal(registry_parent_fd)
    require_no_active_processes()
    return {"canonical_bytes": canonical, "identities": identities}


def consume_publication_authority(registry_parent_fd: int) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(PUBLICATION_REGISTRY.name, flags, 0o600, dir_fd=registry_parent_fd)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        descriptor = os.fstat(fd)
        named = os.stat(PUBLICATION_REGISTRY.name, dir_fd=registry_parent_fd, follow_symlinks=False)
        require(stat.S_ISREG(descriptor.st_mode) and stat.S_ISREG(named.st_mode), "H27 publication registry is not regular; terminal consumed failure")
        require(descriptor.st_nlink == 1, "H27 publication registry hard link forbidden; terminal consumed failure")
        require((descriptor.st_dev, descriptor.st_ino) == (named.st_dev, named.st_ino), "H27 publication registry descriptor mismatch; terminal consumed failure")
        record = {
            "schema_version": 1,
            "state": "consumed",
            "publication_authority_id": PUBLICATION_AUTHORITY_ID,
            "authority_instance_id": AUTHORITY_INSTANCE_ID,
            "canonical_sha256": CANONICAL_SHA256,
            "retry_authorized": False,
        }
        raw = (json.dumps(record, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
        write_all(fd, raw, "publication registry")
        os.fsync(fd)
        os.fsync(registry_parent_fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def atomic_exclusive_rename_at(parent_fd: int, source_name: str, destination_name: str) -> None:
    require(sys.platform == "darwin", "H27 macOS exclusive rename required; terminal consumed failure")
    try:
        libc = ctypes.CDLL(None, use_errno=True)
        renameatx_np = libc.renameatx_np
    except (AttributeError, OSError) as error:
        raise PermissionError("H27 renameatx_np unavailable; terminal consumed failure") from error
    renameatx_np.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameatx_np.restype = ctypes.c_int
    result = renameatx_np(
        parent_fd,
        os.fsencode(source_name),
        parent_fd,
        os.fsencode(destination_name),
        RENAME_EXCL,
    )
    if result != 0:
        error_number = ctypes.get_errno()
        raise OSError(error_number, "H27 exclusive atomic rename failed; terminal consumed failure")


def first_destination_observation_and_publish(activation_parent_fd: int, raw: bytes) -> None:
    try:
        os.stat(DESTINATION.name, dir_fd=activation_parent_fd, follow_symlinks=False)
    except FileNotFoundError:
        pass
    else:
        raise FileExistsError("H27 authority-instance destination already exists; terminal consumed failure")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(STAGING_NAME, flags, 0o600, dir_fd=activation_parent_fd)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        descriptor = os.fstat(fd)
        staged = os.stat(STAGING_NAME, dir_fd=activation_parent_fd, follow_symlinks=False)
        require(stat.S_ISREG(descriptor.st_mode) and stat.S_ISREG(staged.st_mode), "H27 staging is not regular; terminal consumed failure")
        require(descriptor.st_nlink == 1, "H27 staging hard link forbidden; terminal consumed failure")
        require((descriptor.st_dev, descriptor.st_ino) == (staged.st_dev, staged.st_ino), "H27 staging descriptor mismatch; terminal consumed failure")
        write_all(fd, raw, "authority-instance artifact")
        os.fsync(fd)
        atomic_exclusive_rename_at(activation_parent_fd, STAGING_NAME, DESTINATION.name)
        published_stat = os.stat(DESTINATION.name, dir_fd=activation_parent_fd, follow_symlinks=False)
        descriptor_after = os.fstat(fd)
        require(stat.S_ISREG(published_stat.st_mode), "H27 published destination is not regular; terminal consumed failure")
        require(descriptor_after.st_nlink == 1, "H27 published destination hard link forbidden; terminal consumed failure")
        require((descriptor_after.st_dev, descriptor_after.st_ino) == (published_stat.st_dev, published_stat.st_ino), "H27 published destination descriptor mismatch; terminal consumed failure")
    finally:
        os.close(fd)
    os.fsync(activation_parent_fd)
    published = stable_regular_bytes_at(activation_parent_fd, DESTINATION.name, required_mode=0o600)
    require((len(published), git_blob(published), sha256(published)) == (CANONICAL_SIZE, CANONICAL_BLOB, CANONICAL_SHA256), "H27 published authority-instance identity mismatch; terminal consumed failure")
    os.fsync(activation_parent_fd)


def execute() -> dict[str, object]:
    require_platform_ack_and_zero_arguments()
    registry_parent_fd = open_verified_parent(CONSTRUCTOR_REGISTRY.parent)
    activation_parent_fd = -1
    publication_fd = -1
    try:
        context = preflight(registry_parent_fd)
        activation_parent_fd = open_verified_parent(DESTINATION.parent)

        # Full revalidation immediately before the one-shot consumption.  No
        # destination entry has been observed yet; exact canonical bytes are
        # already frozen in memory.
        verify_checkout()
        require(verify_ninety_two_target_identities() == context["identities"], "H27 predecessor graph drifted")
        verify_constructor_terminal(registry_parent_fd)
        require_no_active_processes()
        reverify_parent(registry_parent_fd, CONSTRUCTOR_REGISTRY.parent)
        reverify_parent(activation_parent_fd, DESTINATION.parent)

        # Irreversible one-shot boundary.  Any failure from this exclusive
        # registry create onward is terminal: no retry, cleanup, or repair.
        publication_fd = consume_publication_authority(registry_parent_fd)
        os.close(publication_fd)
        publication_fd = -1

        # Contractual first destination observation, followed by exclusive
        # publication through the same retained activation parent descriptor.
        first_destination_observation_and_publish(activation_parent_fd, context["canonical_bytes"])
        reverify_parent(activation_parent_fd, DESTINATION.parent)
    finally:
        if publication_fd >= 0:
            os.close(publication_fd)
        if activation_parent_fd >= 0:
            os.close(activation_parent_fd)
        os.close(registry_parent_fd)

    return {
        "status": "H27_REVIEW4_AUTHORITY_INSTANCE_ARTIFACT_PUBLICATION_TERMINAL_SUCCESS_STOP",
        "required_head": REQUIRED_HEAD,
        "verified_predecessor_identities": 92,
        "constructor_gate_terminal_verified": True,
        "publication_authority_id": PUBLICATION_AUTHORITY_ID,
        "publication_authority_consumed": True,
        "authority_instance_id": AUTHORITY_INSTANCE_ID,
        "canonical_size": CANONICAL_SIZE,
        "canonical_git_blob_sha1": CANONICAL_BLOB,
        "canonical_sha256": CANONICAL_SHA256,
        "destination_observed_after_consumption": True,
        "destination_created_exclusive": True,
        "destination_published_by_atomic_exclusive_rename": True,
        "materializer_invoked": False,
        "science_or_locked_test": False,
        "retry_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(execute(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
