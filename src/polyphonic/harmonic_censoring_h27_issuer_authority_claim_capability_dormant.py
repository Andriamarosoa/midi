"""Dormant H27 issuer/authority/claim/capability boundary.

The public production edge is an immutable native barrier.  The private
sandbox lifecycle exists only so the future one-shot mechanics can be reviewed
and tested with temporary directories.  It cannot construct the capability
type accepted by the H27 production materializer and it rejects the real H27
administrative root.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Callable, Mapping, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_ADMINISTRATIVE_ROOT = Path("/Users/amcarene/h27-admin")
_AUTHORITY_LOGICAL_PATH = "/Users/amcarene/h27-admin/authority/h27-materialization-v1.json"
_CLAIM_LOGICAL_PATH = "/Users/amcarene/h27-admin/claims/h27-synthetic-v1.consumed.json"
_ISSUER_IDENTITY = "h27-execution-codex-mac-primary"
_POPULATION_NAMESPACE = "H27_SYNTHETIC_V1"

_IDENTITY_BINDING = (
    "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding.json",
    "a32721107c1ff65697661cfa7a2a235811884fc6",
    4609,
    "a752721a022433ac1d9fddccb29b9e56cbd5c1bc0566762ca50acd2f9b01a9fc",
)
_IDENTITY_BINDING_SEAL = (
    "configs/harmonic_censoring_h27_activation_capable_materializer_identity_binding_external_seal.json",
    "be17bda1d7da5144758606ed4b4f1b56708ebf3d",
    1760,
    "a7aa1f6d844fb25e2f633db8bd2817f6741bfe194418985c8419bda64573b3be",
)
_MATERIALIZER_SEAL = (
    "configs/harmonic_censoring_h27_activation_capable_production_materializer_external_review_seal.json",
    "d5b852e63676b59a75b938ef17c51f9247dd5e68",
    3057,
    "68751aede0f11ce04763eb7398f4c071db91310c62c9a58c11667b908b58f95f",
)
_MATERIALIZER = (
    "src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py",
    "79f399359e366781f9526098c98a93cca71b1b49",
    32243,
    "02bf7e9a8e7d0e8f292adb7b00742c83c19ab56eb89e35adc5da9c1c3144ff70",
)
_ACTIVATION_CONTRACT = (
    "configs/harmonic_censoring_h27_materialization_activation_contract.json",
    "2df0e53637cc31d97c01e75b88cb47c2e866c187",
    11131,
    "a1e679e4357552bd88640d3d67a6f17bd9feaad38e8f26e4ed68539f167980c4",
)
_ACTIVATION_SEAL = (
    "configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json",
    "0ef61aa7ada69b619a8e7acd7138151a36496089",
    3122,
    "2174570372df3e8349a425d62ce8e1d084238757fb944968ad8539d9dcabac9d",
)
_AUTHORITY_CONTRACT = (
    "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract.json",
    "e7ff1b71bdd62adf8341dbd824302f1eb57e69c6",
    7358,
    "da96c338d4a99e848ab5fa63d717442c3af27fab6268bb9abae99c1f76321dab",
)
_AUTHORITY_CONTRACT_SEAL = (
    "configs/harmonic_censoring_h27_activation_capable_materializer_authority_contract_external_seal.json",
    "d34da25095581694ce4ca928734bb9b01d2e357c",
    1245,
    "8bb92ad437331528adf744388e77b445c8477a2e7dcbc87f4b84d602a147102b",
)


def _git_blob(raw: bytes) -> str:
    if b"\r" in raw:
        raise ValueError("H27 sealed JSON must use canonical LF bytes.")
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _load_exact(binding: tuple[str, str, int, str]) -> tuple[bytes, Mapping[str, object]]:
    relative, blob, size, sha256 = binding
    raw = (_ROOT / relative).resolve(strict=True).read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 dormant issuer binding drift: {relative}.")
    value = json.loads(raw)
    if type(value) is not dict:
        raise ValueError(f"H27 bound JSON must be an object: {relative}.")
    return raw, value


def validate_h27_dormant_issuer_bindings() -> Mapping[str, Mapping[str, object]]:
    """Validate every reviewed input without creating authority or a claim."""

    loaded = {
        "identity_binding": _load_exact(_IDENTITY_BINDING),
        "identity_binding_seal": _load_exact(_IDENTITY_BINDING_SEAL),
        "materializer_seal": _load_exact(_MATERIALIZER_SEAL),
        "activation_contract": _load_exact(_ACTIVATION_CONTRACT),
        "activation_seal": _load_exact(_ACTIVATION_SEAL),
        "authority_contract": _load_exact(_AUTHORITY_CONTRACT),
        "authority_contract_seal": _load_exact(_AUTHORITY_CONTRACT_SEAL),
    }
    materializer_raw = (_ROOT / _MATERIALIZER[0]).resolve(strict=True).read_bytes()
    if (
        len(materializer_raw) != _MATERIALIZER[2]
        or _git_blob(materializer_raw) != _MATERIALIZER[1]
        or hashlib.sha256(materializer_raw).hexdigest() != _MATERIALIZER[3]
    ):
        raise PermissionError("H27 reviewed materializer identity drift.")

    binding = loaded["identity_binding"][1]
    binding_seal = loaded["identity_binding_seal"][1]
    materializer_seal = loaded["materializer_seal"][1]
    activation = loaded["activation_contract"][1]
    authority_contract = loaded["authority_contract"][1]
    if (
        binding["reviewed_materializer"]["git_blob_sha1"] != _MATERIALIZER[1]
        or binding["materializer_external_review_seal"]["git_blob_sha1"] != _MATERIALIZER_SEAL[1]
        or binding_seal["identity_binding"]["git_blob_sha1"] != _IDENTITY_BINDING[1]
        or materializer_seal["implementation"]["git_blob_sha1"] != _MATERIALIZER[1]
        or activation["population_namespace"] != _POPULATION_NAMESPACE
        or authority_contract["population_namespace"] != _POPULATION_NAMESPACE
    ):
        raise PermissionError("H27 dormant issuer cross-binding drift.")
    return {key: value for key, (_, value) in loaded.items()}


def build_h27_future_authority_payload_template(invocation_nonce: str, issued_at_utc: str) -> bytes:
    """Build deterministic non-operational authority-template bytes."""

    if re.fullmatch(r"[0-9a-f]{64}", invocation_nonce) is None:
        raise ValueError("H27 invocation nonce must be 64 lowercase hexadecimal characters.")
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", issued_at_utc) is None:
        raise ValueError("H27 issued_at_utc must be canonical UTC seconds.")
    sources = validate_h27_dormant_issuer_bindings()
    activation = sources["activation_contract"]
    publication = activation["atomic_publication"]
    payload = {
        "schema_version": 1,
        "artifact_id": "H27_MATERIALIZATION_AUTHORITY_V1_DORMANT_TEMPLATE",
        "status": "DORMANT_TEMPLATE_NOT_OPERATIONAL_AUTHORITY",
        "authority_exists": False,
        "issuer_identity": _ISSUER_IDENTITY,
        "issued_at_utc": issued_at_utc,
        "invocation_nonce": invocation_nonce,
        "administrative_root": _ADMINISTRATIVE_ROOT.as_posix(),
        "logical_authority_path": _AUTHORITY_LOGICAL_PATH,
        "logical_claim_path": _CLAIM_LOGICAL_PATH,
        "population_namespace": _POPULATION_NAMESPACE,
        "identity_binding": {"git_blob_sha1": _IDENTITY_BINDING[1], "raw_sha256": _IDENTITY_BINDING[3]},
        "identity_binding_seal": {"git_blob_sha1": _IDENTITY_BINDING_SEAL[1], "raw_sha256": _IDENTITY_BINDING_SEAL[3]},
        "materializer": {"git_blob_sha1": _MATERIALIZER[1], "raw_sha256": _MATERIALIZER[3]},
        "materializer_seal": {"git_blob_sha1": _MATERIALIZER_SEAL[1], "raw_sha256": _MATERIALIZER_SEAL[3]},
        "activation_contract": {"git_blob_sha1": _ACTIVATION_CONTRACT[1], "raw_sha256": _ACTIVATION_CONTRACT[3]},
        "activation_contract_seal": {"git_blob_sha1": _ACTIVATION_SEAL[1], "raw_sha256": _ACTIVATION_SEAL[3]},
        "authority_contract": {"git_blob_sha1": _AUTHORITY_CONTRACT[1], "raw_sha256": _AUTHORITY_CONTRACT[3]},
        "authority_contract_seal": {"git_blob_sha1": _AUTHORITY_CONTRACT_SEAL[1], "raw_sha256": _AUTHORITY_CONTRACT_SEAL[3]},
        "activation_artifact": {"exists": False, "required_path": activation["future_activation"]["activation_path"]},
        "runtime_exact": copy.deepcopy(activation["runtime_exact"]),
        "process_environment_exact": copy.deepcopy(activation["process_environment_exact"]),
        "sealed_h27_inputs": copy.deepcopy(activation["sealed_h27_inputs"]),
        "expected_counts": {
            "record_count": publication["expected_record_count"],
            "baseline_record_count": publication["expected_baseline_record_count"],
            "p2_record_count": publication["expected_p2_record_count"],
        },
        "fixed_destinations": {
            "final": publication["final_destination"],
            "staging": publication["staging_destination"],
        },
        "materialization_authorized": False,
        "scientific_execution_authorized": False,
        "locked_test_used": False,
    }
    return _canonical_json_bytes(payload)


def validate_h27_future_authority_payload_template(raw: bytes) -> Mapping[str, object]:
    """Validate exact deterministic template semantics; never grants authority."""

    if not raw.endswith(b"\n") or b"\r" in raw:
        raise ValueError("H27 authority template must be canonical UTF-8/LF JSON.")
    value = json.loads(raw)
    if type(value) is not dict:
        raise ValueError("H27 authority template must be an object.")
    rebuilt = build_h27_future_authority_payload_template(str(value.get("invocation_nonce")), str(value.get("issued_at_utc")))
    if raw != rebuilt:
        raise PermissionError("H27 authority template is not the exact deterministic payload.")
    if any(value[field] is not False for field in ("authority_exists", "materialization_authorized", "scientific_execution_authorized", "locked_test_used")):
        raise PermissionError("H27 dormant authority template cannot authorize execution.")
    return value


def _require_sandbox_root(root: Path) -> Path:
    resolved = root.resolve(strict=True)
    temporary = Path(tempfile.gettempdir()).resolve(strict=True)
    try:
        resolved.relative_to(temporary)
    except ValueError as exc:
        raise PermissionError("H27 dormant lifecycle is restricted to the system temporary directory.") from exc
    if resolved == temporary or resolved == _ADMINISTRATIVE_ROOT or "h27-dormant" not in resolved.name:
        raise PermissionError("H27 dormant lifecycle requires a dedicated h27-dormant sandbox.")
    return resolved


def _is_link_or_reparse(path: Path) -> bool:
    information = path.lstat()
    if stat.S_ISLNK(information.st_mode):
        return True
    attributes = getattr(information, "st_file_attributes", 0)
    reparse = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)
    return bool(attributes & reparse)


def _require_safe_sandbox_parent(root: Path, parent: Path) -> Path:
    if parent.exists() or parent.is_symlink():
        if _is_link_or_reparse(parent):
            raise PermissionError("H27 dormant sandbox parent cannot be a symlink or reparse point.")
    else:
        parent.mkdir(mode=0o700)
    resolved = parent.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise PermissionError("H27 dormant sandbox parent escaped the sandbox.") from exc
    if _is_link_or_reparse(resolved):
        raise PermissionError("H27 dormant sandbox resolved parent cannot be redirected.")
    return resolved


def _write_durable_new(root: Path, path: Path, raw: bytes) -> None:
    parent = _require_safe_sandbox_parent(root, path.parent)
    target = parent / path.name
    if target.is_symlink():
        raise PermissionError("H27 dormant sandbox target cannot be a symlink.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(target), flags, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            descriptor = -1
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    finally:
        if descriptor >= 0:
            os.close(descriptor)
    _fsync_directory(parent)


def _fsync_directory(path: Path) -> None:
    # Windows cannot open a directory with os.open.  Production is sealed to
    # Darwin; Windows runs only the dormant sandbox tests.
    if os.name == "nt":
        return
    directory = os.open(str(path), os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


class _H27DormantBoundaryCapability:
    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object) -> "_H27DormantBoundaryCapability":
        del cls, args, kwargs
        raise PermissionError("H27 dormant boundary capability has no public constructor.")

    def __copy__(self) -> "_H27DormantBoundaryCapability":
        del self
        raise TypeError("H27 dormant boundary capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> "_H27DormantBoundaryCapability":
        del self, memo
        raise TypeError("H27 dormant boundary capability cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H27 dormant boundary capability cannot be serialized.")


class _CapabilityBinding(NamedTuple):
    authority_sha256: str
    claim_sha256: str
    materializer_blob: str
    invocation_nonce: str
    process_id: int
    code_identity_sha256: str


class _DormantSandboxSession(NamedTuple):
    capability: object
    binding: _CapabilityBinding
    authority_path: Path
    claim_path: Path
    consume_attested: object


def _attested_single_use_consumer(
    exact_capability: object,
    exact_binding: _CapabilityBinding,
    identity_path: str,
    identity_open_flags: int,
    native_getpid: Callable[[], int],
    native_open: Callable[..., int],
    native_read: Callable[[int, int], bytes],
    native_close: Callable[[int], None],
    native_sha256: Callable[[bytes], object],
) -> object:
    """Consume once only after all attestations pass in the same generator step."""

    request = yield
    if type(request) is not tuple or len(request) != 2:
        raise PermissionError("H27 dormant consumption requires an exact capability/binding pair.")
    candidate, candidate_binding = request
    if candidate is not exact_capability or candidate_binding is not exact_binding:
        raise PermissionError("H27 dormant capability or binding identity mismatch.")
    if native_getpid() != exact_binding.process_id:
        raise PermissionError("H27 dormant capability cannot cross a process boundary.")
    descriptor = native_open(identity_path, identity_open_flags)
    chunks = []
    try:
        while True:
            chunk = native_read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        native_close(descriptor)
    observed_identity = native_sha256(b"".join(chunks)).hexdigest()
    if observed_identity != exact_binding.code_identity_sha256:
        raise PermissionError("H27 dormant issuer code identity drift after claim.")
    yield exact_binding


def _claim_payload(authority_sha256: str, invocation_nonce: str) -> bytes:
    return _canonical_json_bytes({
        "schema_version": 1,
        "claim_id": "H27_SYNTHETIC_V1_DORMANT_SANDBOX_CLAIM",
        "status": "DORMANT_SANDBOX_CONSUMED_NOT_OPERATIONAL",
        "logical_claim_path": _CLAIM_LOGICAL_PATH,
        "authority_sha256": authority_sha256,
        "activation_contract_sha256": _ACTIVATION_CONTRACT[3],
        "identity_binding_sha256": _IDENTITY_BINDING[3],
        "materializer_blob": _MATERIALIZER[1],
        "materializer_seal_sha256": _MATERIALIZER_SEAL[3],
        "population_namespace": _POPULATION_NAMESPACE,
        "final_destination": "/Users/amcarene/h27-admin/population/h27-synthetic-v1",
        "staging_destination": "/Users/amcarene/h27-admin/population/.h27-synthetic-v1.staging",
        "invocation_nonce": invocation_nonce,
        "scientific_execution_authorized": False,
    })


def _issue_dormant_sandbox_session(
    sandbox_root: Path,
    invocation_nonce: str,
    issued_at_utc: str,
    identity_path: Path | None = None,
    expected_process_id: int | None = None,
) -> _DormantSandboxSession:
    """Exercise the future lifecycle only inside a dedicated temporary sandbox."""

    root = _require_sandbox_root(sandbox_root)
    authority_raw = build_h27_future_authority_payload_template(invocation_nonce, issued_at_utc)
    validate_h27_future_authority_payload_template(authority_raw)
    authority_path = root / "authority" / "h27-materialization-v1.json"
    claim_path = root / "claims" / "h27-synthetic-v1.consumed.json"
    if authority_path.exists() or claim_path.exists():
        raise FileExistsError("H27 dormant sandbox authority or claim already exists.")

    sealed_identity_path = (identity_path or Path(__file__)).resolve(strict=True)
    expected_identity = hashlib.sha256(sealed_identity_path.read_bytes()).hexdigest()
    _write_durable_new(root, authority_path, authority_raw)
    authority_written = authority_path.read_bytes()
    if authority_written != authority_raw:
        raise PermissionError("H27 sandbox authority bytes changed after durable write.")
    authority_sha256 = hashlib.sha256(authority_written).hexdigest()
    claim_raw = _claim_payload(authority_sha256, invocation_nonce)
    _write_durable_new(root, claim_path, claim_raw)
    claim_written = claim_path.read_bytes()
    if claim_written != claim_raw:
        raise PermissionError("H27 sandbox claim bytes changed after durable write.")
    claim_sha256 = hashlib.sha256(claim_written).hexdigest()

    capability = object.__new__(_H27DormantBoundaryCapability)
    binding = _CapabilityBinding(
        authority_sha256=authority_sha256,
        claim_sha256=claim_sha256,
        materializer_blob=_MATERIALIZER[1],
        invocation_nonce=invocation_nonce,
        process_id=os.getpid() if expected_process_id is None else expected_process_id,
        code_identity_sha256=expected_identity,
    )
    one_shot_iterator = _attested_single_use_consumer(
        capability,
        binding,
        str(sealed_identity_path),
        os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0),
        os.getpid,
        os.open,
        os.read,
        os.close,
        hashlib.sha256,
    )
    next(one_shot_iterator)
    return _DormantSandboxSession(
        capability=capability,
        binding=binding,
        authority_path=authority_path,
        claim_path=claim_path,
        consume_attested=one_shot_iterator.send,
    )


_DORMANT_NATIVE_BARRIER = ().__getitem__
issue_h27_materialization_authority_and_capability = _DORMANT_NATIVE_BARRIER


__all__ = [
    "build_h27_future_authority_payload_template",
    "issue_h27_materialization_authority_and_capability",
    "validate_h27_dormant_issuer_bindings",
    "validate_h27_future_authority_payload_template",
]
