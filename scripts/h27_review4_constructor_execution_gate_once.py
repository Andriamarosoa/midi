#!/usr/bin/env python3
"""Dormant fail-closed one-shot gate for the reviewed H27 constructor.

This file is implementation-only until a distinct external review authorizes
its exact bytes.  Importing it is inert.  A real execution requires the exact
macOS checkout and the dedicated acknowledgement environment variable.
"""
from __future__ import annotations

import datetime
import hashlib
import json
import os
from pathlib import Path
import secrets
import stat
import subprocess
import sys
from types import ModuleType


ACK = "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE"
TARGET_TEXT = "/Users/amcarene/midi-worker/repository"
TARGET = Path(TARGET_TEXT)
GIT_DATABASE = TARGET / ".git"
REQUIRED_HEAD = "46a6bdf81a56a7a7a10524d4e55092301a452207"
CONTROL_BUNDLE_TEXT = "/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1"
CONTROL_BUNDLE = Path(CONTROL_BUNDLE_TEXT)
REGISTRY = Path("/Users/amcarene/h27-admin/registry/h27-real-publication-constructor-execution-authority-v1.jsonl")
DESTINATION_TEXT = "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json"
AUTHORITY_ID = "45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e"
ISSUER_ID = "h27-execution-codex-mac-primary"
CONSTRUCTOR_PATH = "src/polyphonic/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor.py"
CONSTRUCTOR_BLOB = "0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62"
CONSTRUCTOR_SIZE = 12599
CONSTRUCTOR_SHA256 = "0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807"
CLOSED_BUNDLE_DIGEST = "879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe"
RUNNER_NAME = "h27_review4_constructor_execution_gate_once.py"

BUNDLE_FILES = (
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract.json", "1bdc95411520793c2f1ff0c08ef2245e569ef2a0", 6387, "0134f4c459ac9d4e642da70dbcf257f34998db064e568ea0e039b58d5952f215"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_external_seal.json", "099703d92d9cfd761f5aa9065467fff1516d5a46", 1673, "6cd9cc7f67c60ea71804fd01137ee2fddd1947c0fb0e56d3bc7d0db362054778"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact.json", "fedcf0f1c2be368ddf619e8f1715a55f499815c8", 688, "dccc4afaf20390fe07226fbfd237c06b381b203d25f6f80908adc3753c985296"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_external_seal.json", "4f3e49d29e5777b1ad5174b24870ac21f348ac78", 1683, "5b2b985f694b1e360afc9aec84a6ba8329cf6bc7b4cfea106a67108ac550decc"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding.json", "fe89c67096bef9e41a0405a1e37a291be5fd1afa", 2986, "8e9549db0821ed3f0334aab369abb18373bc5e2141d656b8e0c0e5ba6a65a9da"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding_external_seal.json", "3d79c43ee50ccc9b2e87c3c07d63a2061b18edbf", 1431, "95892205cf7af0d84a5ec75b466467486eb50996d4040bdca7d25e4b9a58940c"),
)

TARGET_CHAIN_ROOTS = (
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding.json", "71439f93f56f5f499ba29d6ee7fe334ed2421735", 3340, "1907b841a9defa5a9b3ac61ffc3660be6fb5447d63044d0816e8b2c94aae5d4d"),
    ("configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding_external_seal.json", "ed4a944d70d49e33c66d0d73f04a2e3a682cb79c", 1530, "02c01af0276f98e91c992b566c95a33b8354ca57b80fa1cb3c056dc2a7954b06"),
)

# This older dormant implementation is mentioned for historical explanation in
# the graph but is deliberately not part of the normative 112-identity chain.
NON_NORMATIVE_IDENTITY_PATH = "src/polyphonic/harmonic_censoring_h27_production_materializer_dormant.py"

SEALED_CHAIN_IDENTITY = {
    "contract_git_blob_sha1": "40757fa14d3df8b2aca2e12924faf7be329b9687",
    "contract_size_bytes": 5300,
    "contract_raw_sha256": "c23b4ceaf67dba8dc9d16ab7b279906823ae1b1259ba07aa8e8e2a2bf23210bb",
    "binding_git_blob_sha1": "41bb902d99379c0a518181e97056b4232abbc143",
    "binding_size_bytes": 3369,
    "binding_raw_sha256": "400a1010c4be36cbec585de0399137abca8b0b61f218946498d19fad23739e55",
}
NAMESPACE = "H27_REAL_PUBLICATION_ONE_SHOT_AUTHORITY_INSTANCE_V1"


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
        raise ValueError(f"H27 non-RFC8259 constant: {value}")

    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=reject_constant)
    require(type(value) is dict, "H27 JSON root must be an object")
    return value


def stable_regular_bytes(path: Path, *, required_mode: int | None = None) -> bytes:
    require(hasattr(os, "O_NOFOLLOW"), "H27 O_NOFOLLOW unavailable")
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode) and stat.S_ISREG(named.st_mode), f"H27 non-regular file: {path}")
        require(before.st_nlink == 1, f"H27 hard link forbidden: {path}")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), f"H27 descriptor mismatch: {path}")
        if required_mode is not None:
            require(stat.S_IMODE(before.st_mode) == required_mode, f"H27 mode mismatch: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        raw = b"".join(chunks)
        after = os.fstat(fd)
        stable = ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns")
        require(all(getattr(before, key) == getattr(after, key) for key in stable), f"H27 file changed while read: {path}")
        return raw
    finally:
        os.close(fd)


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
    require(result.returncode in allowed, f"H27 Git read failed: {arguments!r}")
    return result


def require_platform_ack_and_zero_arguments() -> None:
    require(sys.platform == "darwin", "H27 exact macOS runner required")
    require(len(sys.argv) == 1, "H27 zero arguments required")
    require(os.environ.get(ACK) == "1", "H27 constructor execution ACK required")


def verify_control_bundle() -> tuple[str, dict[str, dict[str, object]]]:
    require(CONTROL_BUNDLE.resolve(strict=True) == CONTROL_BUNDLE, "H27 control bundle root mismatch")
    require(CONTROL_BUNDLE.is_dir() and not CONTROL_BUNDLE.is_symlink(), "H27 control bundle root type mismatch")
    actual = sorted(path.relative_to(CONTROL_BUNDLE).as_posix() for path in CONTROL_BUNDLE.rglob("*") if path.is_file())
    require(actual == sorted(item[0] for item in BUNDLE_FILES), "H27 closed bundle file set mismatch")
    for path in CONTROL_BUNDLE.rglob("*"):
        require(not path.is_symlink() and (path.is_dir() or path.is_file()), f"H27 bundle entry type mismatch: {path}")

    parsed: dict[str, dict[str, object]] = {}
    lines: list[str] = []
    for relative, blob_id, size, digest in BUNDLE_FILES:
        raw = stable_regular_bytes(CONTROL_BUNDLE / relative, required_mode=0o400)
        require((git_blob(raw), len(raw), sha256(raw)) == (blob_id, size, digest), f"H27 bundle identity mismatch: {relative}")
        parsed[relative] = strict_json(raw)
        lines.append(f"{relative}\0{blob_id}\0{size}\0{digest}\n")
    digest = sha256("".join(lines).encode("utf-8"))
    require(digest == CLOSED_BUNDLE_DIGEST, "H27 closed bundle digest mismatch")

    gate, gate_seal, authority, authority_seal, binding, binding_seal = (parsed[item[0]] for item in BUNDLE_FILES)
    require(gate.get("contract_id") == "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE_CONTRACT_V1", "H27 gate contract mismatch")
    require(gate.get("bound_authority") == {"execution_authority_artifact_id": AUTHORITY_ID, "expected_git_head": REQUIRED_HEAD, "single_use": True, "consumed": False}, "H27 gate authority mismatch")
    require(gate["future_runtime_source_model"]["target_checkout_root"] == TARGET_TEXT, "H27 target binding mismatch")
    require(gate["future_runtime_source_model"]["administrative_control_bundle_root"] == CONTROL_BUNDLE_TEXT, "H27 control binding mismatch")
    require(gate_seal.get("execution_authority_artifact_id") == AUTHORITY_ID and gate_seal.get("expected_git_head") == REQUIRED_HEAD, "H27 gate seal mismatch")
    require(authority.get("execution_authority_artifact_id") == AUTHORITY_ID and authority.get("expected_git_head") == REQUIRED_HEAD, "H27 authority mismatch")
    require(authority.get("single_use") is True and authority.get("consumed") is False, "H27 authority state mismatch")
    require(authority_seal.get("execution_authority_artifact_id") == AUTHORITY_ID and authority_seal.get("expected_git_head") == REQUIRED_HEAD, "H27 authority seal mismatch")
    require(binding.get("bound_artifact_values") == {"execution_authority_artifact_id": AUTHORITY_ID, "expected_git_head": REQUIRED_HEAD, "single_use": True, "consumed": False}, "H27 authority binding mismatch")
    require(binding_seal.get("artifact_id") == AUTHORITY_ID and binding_seal.get("expected_git_head") == REQUIRED_HEAD, "H27 authority binding seal mismatch")
    return digest, parsed


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


def _scan_identity_objects(value: object, pending: list[tuple[str, str, int, str]]) -> None:
    if type(value) is dict:
        mapping = value
        if {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(mapping):
            pending.append(_identity_tuple(mapping))
        for nested in mapping.values():
            _scan_identity_objects(nested, pending)
    elif type(value) is list:
        for nested in value:
            _scan_identity_objects(nested, pending)


def verify_one_hundred_twelve_target_identities() -> tuple[tuple[str, str, int, str], ...]:
    pending = list(TARGET_CHAIN_ROOTS)
    verified: dict[str, tuple[str, str, int, str]] = {}
    while pending:
        identity = pending.pop(0)
        relative, blob_id, size, digest = identity
        if relative == NON_NORMATIVE_IDENTITY_PATH:
            continue
        if relative in verified:
            require(verified[relative] == identity, f"H27 conflicting duplicate identity: {relative}")
            continue
        require(not relative.startswith("/") and ".." not in Path(relative).parts, f"H27 unsafe identity path: {relative}")
        path = TARGET / relative
        raw = stable_regular_bytes(path)
        require((git_blob(raw), len(raw), sha256(raw)) == (blob_id, size, digest), f"H27 target identity mismatch: {relative}")
        tree = git_read("ls-tree", REQUIRED_HEAD, relative).stdout.rstrip(b"\n").split(maxsplit=3)
        require(len(tree) == 4 and tree[1] == b"blob" and tree[2].decode("ascii") == blob_id, f"H27 target tree identity mismatch: {relative}")
        verified[relative] = identity
        if relative.endswith(".json"):
            _scan_identity_objects(strict_json(raw), pending)
    require(len(verified) == 112, "H27 target identity count mismatch")
    return tuple(verified[path] for path in sorted(verified))


def verify_constructor() -> bytes:
    tree = git_read("ls-tree", REQUIRED_HEAD, CONSTRUCTOR_PATH).stdout.rstrip(b"\n").split(maxsplit=3)
    require(len(tree) == 4 and tree[1] == b"blob" and tree[2].decode("ascii") == CONSTRUCTOR_BLOB, "H27 constructor tree identity mismatch")
    raw = stable_regular_bytes(TARGET / CONSTRUCTOR_PATH)
    require((git_blob(raw), len(raw), sha256(raw)) == (CONSTRUCTOR_BLOB, CONSTRUCTOR_SIZE, CONSTRUCTOR_SHA256), "H27 constructor byte identity mismatch")
    return raw


def require_no_active_processes() -> None:
    raw = subprocess.run(["/bin/ps", "-axo", "pid=,command="], check=True, stdout=subprocess.PIPE).stdout
    forbidden = (RUNNER_NAME.encode("ascii"), b"harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor", b"harmonic_censoring_h27_population_materializer", b"run_harmonic_censoring_h27")
    active: list[bytes] = []
    for line in raw.splitlines():
        fields = line.strip().split(maxsplit=1)
        require(len(fields) == 2 and fields[0].isdigit(), "H27 malformed process observation")
        if int(fields[0]) != os.getpid() and any(token in fields[1] for token in forbidden):
            active.append(line.strip())
    require(not active, "H27 competing constructor/materializer/science process active")


def canonical_runtime_inputs() -> tuple[str, str, str, bytes, str, str]:
    issued_at = datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    nonce = secrets.token_hex(32)
    digest_input = "\0".join((NAMESPACE, ISSUER_ID, issued_at, nonce, DESTINATION_TEXT, SEALED_CHAIN_IDENTITY["contract_raw_sha256"], SEALED_CHAIN_IDENTITY["binding_raw_sha256"]))
    instance_id = hashlib.sha256(digest_input.encode("ascii")).hexdigest()
    artifact = {
        "schema_version": 1,
        "artifact_type": "h27_real_publication_one_shot_execution_authority_instance",
        "authority_instance_id": instance_id,
        "issuer_id": ISSUER_ID,
        "issued_at_utc": issued_at,
        "invocation_nonce": nonce,
        "canonical_destination_path": DESTINATION_TEXT,
        "sealed_chain_identity": dict(SEALED_CHAIN_IDENTITY),
        "single_use": True,
        "consumed": False,
    }
    raw = (json.dumps(artifact, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")
    return issued_at, nonce, instance_id, raw, sha256(raw), AUTHORITY_ID


def preflight() -> dict[str, object]:
    require_platform_ack_and_zero_arguments()
    bundle_digest, _ = verify_control_bundle()
    verify_checkout()
    identities = verify_one_hundred_twelve_target_identities()
    constructor_raw = verify_constructor()
    require_no_active_processes()
    # Full second validation immediately before registry open.  No destination
    # path has been observed; the exclusive registry create is the first effect.
    require(verify_control_bundle()[0] == bundle_digest, "H27 control bundle drifted")
    verify_checkout()
    require(verify_one_hundred_twelve_target_identities() == identities, "H27 target identity set drifted")
    require(verify_constructor() == constructor_raw, "H27 constructor bytes drifted")
    require_no_active_processes()
    issued_at, nonce, instance_id, canonical_raw, canonical_sha, authority_id = canonical_runtime_inputs()
    return {
        "control_bundle_digest": bundle_digest,
        "verified_target_identities": len(identities),
        "verified_authority_identities": 4,
        "verified_total_identities_before_registry": 116,
        "issued_at_utc": issued_at,
        "invocation_nonce": nonce,
        "authority_instance_id": instance_id,
        "canonical_bytes": canonical_raw,
        "canonical_sha256": canonical_sha,
        "execution_authority_artifact_id": authority_id,
        "constructor_bytes": constructor_raw,
    }


def _canonical_line(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def _write_record_once(fd: int, value: dict[str, object]) -> None:
    raw = _canonical_line(value)
    require(os.write(fd, raw) == len(raw), "H27 partial registry write; terminal consumed failure")
    os.fsync(fd)


def open_verified_registry_parent() -> int:
    parent = REGISTRY.parent
    require(parent.resolve(strict=True) == parent, "H27 registry parent realpath mismatch")
    require(parent.is_dir() and not parent.is_symlink(), "H27 registry parent type mismatch")
    require(hasattr(os, "O_DIRECTORY") and hasattr(os, "O_NOFOLLOW"), "H27 directory FD safeguards unavailable")
    parent_fd = os.open(parent, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        descriptor = os.fstat(parent_fd)
        named = os.stat(parent, follow_symlinks=False)
        require(stat.S_ISDIR(descriptor.st_mode) and stat.S_ISDIR(named.st_mode), "H27 registry parent is not a directory")
        require((descriptor.st_dev, descriptor.st_ino) == (named.st_dev, named.st_ino), "H27 registry parent descriptor mismatch")
        return parent_fd
    except BaseException:
        os.close(parent_fd)
        raise


def open_and_reserve(context: dict[str, object], parent_fd: int) -> int:
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW
    fd = os.open(REGISTRY.name, flags, 0o600, dir_fd=parent_fd)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        if sys.platform == "darwin":
            require(stat.S_IMODE(os.fstat(fd).st_mode) == 0o600, "H27 registry mode mismatch; terminal consumed failure")
        descriptor = os.fstat(fd)
        named = os.stat(REGISTRY.name, dir_fd=parent_fd, follow_symlinks=False)
        require(stat.S_ISREG(descriptor.st_mode) and stat.S_ISREG(named.st_mode), "H27 registry entry type mismatch; terminal consumed failure")
        require(descriptor.st_nlink == 1, "H27 registry hard link forbidden; terminal consumed failure")
        require((descriptor.st_dev, descriptor.st_ino) == (named.st_dev, named.st_ino), "H27 registry descriptor mismatch; terminal consumed failure")
        _write_record_once(fd, {
            "schema_version": 1,
            "state": "reserved",
            "execution_authority_artifact_id": context["execution_authority_artifact_id"],
            "authority_instance_id": context["authority_instance_id"],
            "invocation_nonce": context["invocation_nonce"],
            "issued_at_utc": context["issued_at_utc"],
            "canonical_sha256": context["canonical_sha256"],
        })
        os.fsync(parent_fd)
        return fd
    except BaseException:
        os.close(fd)
        raise


def consume_authority(fd: int, context: dict[str, object]) -> None:
    _write_record_once(fd, {
        "schema_version": 1,
        "state": "consumed",
        "execution_authority_artifact_id": context["execution_authority_artifact_id"],
        "authority_instance_id": context["authority_instance_id"],
        "invocation_nonce": context["invocation_nonce"],
        "issued_at_utc": context["issued_at_utc"],
        "canonical_sha256": context["canonical_sha256"],
    })


def load_constructor_from_frozen_bytes(raw: bytes) -> ModuleType:
    require(type(raw) is bytes, "H27 frozen constructor bytes required")
    require((git_blob(raw), len(raw), sha256(raw)) == (CONSTRUCTOR_BLOB, CONSTRUCTOR_SIZE, CONSTRUCTOR_SHA256), "H27 frozen constructor identity mismatch")
    name = "_h27_review4_exact_constructor"
    module = ModuleType(name)
    module.__file__ = str(TARGET / CONSTRUCTOR_PATH)
    module.__package__ = ""
    sys.modules[name] = module
    code = compile(raw, module.__file__, "exec", dont_inherit=True, optimize=0)
    exec(code, module.__dict__)
    return module


def invoke_constructor(context: dict[str, object]) -> object:
    module = load_constructor_from_frozen_bytes(context["constructor_bytes"])
    probe = module.H27EffectFreeConstructorProbe(
        persistent_registry_checked=True,
        identity_available=True,
        nonce_available=True,
        reservation_attempted=False,
        destination_observed=False,
        create_attempted=False,
        write_attempted=False,
        expected_canonical_sha256=context["canonical_sha256"],
    )
    return module.construct_h27_real_publication_authority_instance_artifact(
        issuer_id=ISSUER_ID,
        issued_at_utc=context["issued_at_utc"],
        invocation_nonce=context["invocation_nonce"],
        canonical_destination_path=DESTINATION_TEXT,
        sealed_chain_identity=dict(SEALED_CHAIN_IDENTITY),
        probe=probe,
    )


def execute() -> dict[str, object]:
    context = preflight()
    parent_fd = open_verified_registry_parent()
    try:
        # First persistent effect and one-shot attempt boundary.  Any failure
        # from this relative O_EXCL create onward is terminal.  Never retry,
        # reconstruct, clean, or repair.
        fd = open_and_reserve(context, parent_fd)
        try:
            consume_authority(fd, context)
        finally:
            os.close(fd)
    finally:
        os.close(parent_fd)
    result = invoke_constructor(context)
    require(result.canonical_bytes == context["canonical_bytes"], "H27 constructor canonical bytes mismatch after consumption")
    require(result.canonical_sha256 == context["canonical_sha256"], "H27 constructor digest mismatch after consumption")
    require(result.authority_instance_id == context["authority_instance_id"], "H27 constructor instance identity mismatch after consumption")
    require(result.persistent_reservation_performed is False and result.destination_path is None, "H27 constructor effect boundary mismatch")
    require(result.authority_instance_artifact_exists is False and result.authority_instance_exists is False, "H27 constructor must remain effect-free")
    require(result.filesystem_effects == 0 and result.science_invocations == 0, "H27 constructor reported forbidden effects")
    return {
        "status": "H27_REVIEW4_CONSTRUCTOR_EXECUTION_GATE_TERMINAL_SUCCESS_STOP",
        "required_head": REQUIRED_HEAD,
        "control_bundle_digest": context["control_bundle_digest"],
        "verified_target_identities": 112,
        "verified_authority_identities": 4,
        "verified_total_identities_before_registry": 116,
        "execution_authority_artifact_id": AUTHORITY_ID,
        "authority_instance_id": context["authority_instance_id"],
        "invocation_nonce": context["invocation_nonce"],
        "issued_at_utc": context["issued_at_utc"],
        "canonical_sha256": context["canonical_sha256"],
        "registry_created": True,
        "authority_reserved": True,
        "authority_consumed": True,
        "constructor_invoked_once": True,
        "constructor_filesystem_effects": 0,
        "destination_observed": False,
        "authority_instance_artifact_exists": False,
        "materializer_invoked": False,
        "science_or_locked_test": False,
        "retry_authorized": False,
    }


if __name__ == "__main__":
    print(json.dumps(execute(), ensure_ascii=False, allow_nan=False, separators=(",", ":")))
