"""Dormant canonical-codec and identifier primitives for H26 execution.

This module deliberately contains no issuer, filesystem claim slot, observer
invocation, receipt writer, or scientific execution path.  It only implements
the deterministic byte and identifier rules approved by the declarative H26
runtime-execution authority contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple


EXECUTION_AUTHORITY_CONTRACT_COMMIT = (
    "e0e070b8b75e85fb8ef78c7d6950a13f2c69ceae"
)
EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA = (
    "5ab6ff43980c0dc0f32308d3f8cee14a90351ec7"
)
EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256 = (
    "c7f6da697d74f710b957ab7ad32bef0fc184bb4f16ffaef16d2e2e1abafc63f9"
)
EXTERNAL_SEAL_COMMIT = "d60df11a461c545bd40b4754b99290258443bc06"
EXTERNAL_SEAL_GIT_BLOB_SHA = "90819f501bf1679782b071a72f681d6b7d4db0c8"
APPROVED_DORMANT_PRIMITIVES_COMMIT = (
    "48d3e6015a2adaded0b27769271ebb8d70ddb98a"
)
APPROVED_DORMANT_PRIMITIVES_GIT_BLOB_SHA = (
    "9c347a6c9fe081e0d2ac963311ea766eb5fc62f9"
)
_APPROVED_EXECUTION_AUTHORITY_CONTRACT_COMMIT = (
    "e0e070b8b75e85fb8ef78c7d6950a13f2c69ceae"
)
_APPROVED_EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA = (
    "5ab6ff43980c0dc0f32308d3f8cee14a90351ec7"
)
_APPROVED_EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256 = (
    "c7f6da697d74f710b957ab7ad32bef0fc184bb4f16ffaef16d2e2e1abafc63f9"
)
_APPROVED_EXTERNAL_SEAL_COMMIT = "d60df11a461c545bd40b4754b99290258443bc06"
_APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA = (
    "90819f501bf1679782b071a72f681d6b7d4db0c8"
)
RUNTIME_QUALIFICATION_CONTRACT_COMMIT = (
    "89cc0659de3afb5194afcf8e7ea9ac6c300e1f92"
)
RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA = (
    "c3a021872dfd3a99b6977fdef1302d5edc755fea"
)
RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256 = (
    "eec08691f12f673f86ed3839379865cbe6087e974a6745b1a4ef6cecea839736"
)
APPROVED_DORMANT_QUALIFIER_COMMIT = (
    "25a08630d6ad99d5e3432a277b99b9603990458a"
)
APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA = (
    "ef24d9ebdc4ae834b3b872175fb7e098330a68bf"
)

_CLAIM_DOMAIN = b"H26_RUNTIME_QUALIFICATION_CLAIM_ID_V1"
_CLAIM_PREFIX = "h26-runtime-claim-v1-"
_ENTRY_DOMAIN = b"H26_RUNTIME_QUALIFICATION_OBSERVER_ENTRY_ID_V1"
_ENTRY_PREFIX = "h26-runtime-entry-v1-"
_LOWER_SHA256_RE = re.compile(r"[0-9a-f]{64}\Z")
_CLAIM_ID_RE = re.compile(r"h26-runtime-claim-v1-[0-9a-f]{64}\Z")

AUTHORITY_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_identity", "schema_version", "execution_authority_contract_commit",
    "execution_authority_contract_raw_sha256",
    "runtime_qualification_contract_commit",
    "runtime_qualification_contract_git_blob_sha",
    "runtime_qualification_contract_raw_sha256", "qualifier_commit",
    "qualifier_git_blob_sha", "materialization_authority_contract_commit",
    "materialization_authority_contract_git_blob_sha", "target_runtime_role",
    "authority_id", "single_use", "maximum_claims_per_authority",
    "maximum_observer_invocations", "authority_consumed_by_first_claim_creation",
    "retry_allowed", "execution_authorized", "issued_at", "issuer_identity",
)
CLAIM_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_identity", "schema_version", "claim_id", "authority_id",
    "authority_raw_sha256", "execution_authority_contract_commit",
    "execution_authority_contract_raw_sha256",
    "runtime_qualification_contract_commit",
    "runtime_qualification_contract_git_blob_sha",
    "runtime_qualification_contract_raw_sha256", "qualifier_commit",
    "qualifier_git_blob_sha", "target_runtime_role", "single_use",
    "maximum_claims_per_authority", "maximum_observer_invocations",
    "authority_consumed", "claim_consumed", "retry_allowed",
)
OBSERVER_ENTRY_EVIDENCE_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_identity", "schema_version", "observer_entry_evidence_id",
    "authority_id", "authority_raw_sha256", "claim_id", "claim_raw_sha256",
    "qualifier_commit", "qualifier_git_blob_sha", "observer_entry_ordinal",
)
RECEIPT_REQUIRED_FIELDS: Tuple[str, ...] = (
    "schema_identity", "schema_version", "claim_id", "claim_raw_sha256",
    "authority_id", "authority_raw_sha256", "qualifier_commit",
    "qualifier_git_blob_sha", "runtime_qualification_contract_commit",
    "runtime_qualification_contract_raw_sha256", "observer_entered",
    "observer_entry_evidence_id", "observer_entry_evidence_raw_sha256",
    "runtime_record_exists", "runtime_record_raw_sha256", "terminal_status",
    "observer_invocation_count", "claim_consumed", "retry_allowed",
)


def _execution_contract_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "harmonic_censoring_h26_runtime_qualification_execution_authority_contract.json"
    )


def _external_seal_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "configs"
        / "harmonic_censoring_h26_runtime_qualification_execution_authority_contract_external_seal.json"
    )


def _canonical_git_text_bytes(raw: bytes) -> bytes:
    if b"\r" in raw:
        if b"\r" in raw.replace(b"\r\n", b""):
            raise ValueError("contract contains a non-CRLF carriage return")
        raw = raw.replace(b"\r\n", b"\n")
    return raw


def _git_blob_sha(raw: bytes) -> str:
    canonical = _canonical_git_text_bytes(raw)
    header = f"blob {len(canonical)}\0".encode("ascii")
    return hashlib.sha1(header + canonical).hexdigest()


def _strict_contract_json(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("execution contract is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("execution contract has a forbidden BOM")

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"floating-point JSON value forbidden: {value}")

    try:
        payload = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("invalid execution contract JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("execution contract must be an object")
    return payload


def load_runtime_execution_contract(path: Optional[Path] = None) -> Mapping[str, Any]:
    """Load only the exact reviewed declarative execution contract."""
    if (
        EXECUTION_AUTHORITY_CONTRACT_COMMIT
        != _APPROVED_EXECUTION_AUTHORITY_CONTRACT_COMMIT
    ):
        raise ValueError("runtime execution contract commit binding mismatch")
    if (
        EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA
        != _APPROVED_EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA
    ):
        raise ValueError("runtime execution contract blob binding mismatch")
    raw = _read_exact_execution_contract_bytes(path)
    payload = _strict_contract_json(raw)
    expected_top = {
        "schema_version": 1,
        "purpose": (
            "H26_DORMANT_RUNTIME_QUALIFICATION_EXECUTION_AUTHORITY_"
            "CLAIM_AND_RECEIPT_CONTRACT"
        ),
        "status": (
            "DECLARATIVE_DORMANT_NO_AUTHORITY_NO_CLAIM_NO_EXECUTION_"
            "NO_RECORD_NO_RECEIPT"
        ),
    }
    for key, expected in expected_top.items():
        if type(payload.get(key)) is not type(expected) or payload.get(key) != expected:
            raise ValueError(f"execution contract {key} mismatch")
    bindings = payload.get("bindings")
    if not isinstance(bindings, dict):
        raise ValueError("execution contract bindings must be an object")
    expected_bindings = {
        "runtime_qualification_contract_commit": RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
        "runtime_qualification_contract_git_blob_sha": RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA,
        "runtime_qualification_contract_raw_sha256": RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
        "approved_dormant_qualifier_commit": APPROVED_DORMANT_QUALIFIER_COMMIT,
        "approved_dormant_qualifier_git_blob_sha": APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA,
    }
    for key, expected in expected_bindings.items():
        if bindings.get(key) != expected:
            raise ValueError(f"execution contract binding {key} mismatch")
    return MappingProxyType(payload)


def _read_exact_execution_contract_bytes(path: Optional[Path] = None) -> bytes:
    resolved = (path or _execution_contract_path()).resolve(strict=True)
    raw = resolved.read_bytes()
    if _git_blob_sha(raw) != EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("runtime execution contract Git blob mismatch")
    return _canonical_git_text_bytes(raw)


def canonical_execution_contract_raw_sha256(path: Optional[Path] = None) -> str:
    """Hash the exact canonical Git text bytes of the sealed contract."""
    if (
        EXECUTION_AUTHORITY_CONTRACT_COMMIT
        != _APPROVED_EXECUTION_AUTHORITY_CONTRACT_COMMIT
    ):
        raise ValueError("runtime execution contract commit binding mismatch")
    if (
        EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA
        != _APPROVED_EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA
    ):
        raise ValueError("runtime execution contract blob binding mismatch")
    if (
        EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256
        != _APPROVED_EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256
    ):
        raise ValueError("runtime execution contract raw SHA256 binding mismatch")
    raw = _read_exact_execution_contract_bytes(path)
    digest = hashlib.sha256(raw).hexdigest()
    if digest != EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256:
        raise ValueError("runtime execution contract raw SHA256 mismatch")
    return digest


def load_runtime_execution_external_seal(
    path: Optional[Path] = None,
    *,
    execution_contract_path: Optional[Path] = None,
) -> Mapping[str, Any]:
    """Load the reviewed seal and rebind it to the exact contract bytes."""
    if EXTERNAL_SEAL_COMMIT != _APPROVED_EXTERNAL_SEAL_COMMIT:
        raise ValueError("runtime execution external seal commit binding mismatch")
    if EXTERNAL_SEAL_GIT_BLOB_SHA != _APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA:
        raise ValueError("runtime execution external seal blob binding mismatch")
    resolved = (path or _external_seal_path()).resolve(strict=True)
    raw = resolved.read_bytes()
    if _git_blob_sha(raw) != EXTERNAL_SEAL_GIT_BLOB_SHA:
        raise ValueError("runtime execution external seal Git blob mismatch")
    payload = _strict_contract_json(_canonical_git_text_bytes(raw))
    expected_scalars = {
        "schema_identity": (
            "H26_RUNTIME_QUALIFICATION_EXECUTION_AUTHORITY_CONTRACT_"
            "EXTERNAL_SEAL_V1"
        ),
        "schema_version": 1,
        "status": "DECLARATIVE_EXTERNAL_SEAL_ONLY_NO_EXECUTION_AUTHORITY",
        "execution_contract_commit": EXECUTION_AUTHORITY_CONTRACT_COMMIT,
        "execution_contract_git_blob_sha": EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        "execution_contract_raw_sha256": EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256,
        "approved_primitives_commit": APPROVED_DORMANT_PRIMITIVES_COMMIT,
        "approved_primitives_git_blob_sha": APPROVED_DORMANT_PRIMITIVES_GIT_BLOB_SHA,
        "seal_contains_own_raw_sha256": False,
    }
    for key, expected in expected_scalars.items():
        if type(payload.get(key)) is not type(expected) or payload.get(key) != expected:
            raise ValueError(f"runtime execution external seal {key} mismatch")
    expected_state = {
        "issuer_exists": False,
        "authority_exists": False,
        "claim_exists": False,
        "claim_consumed": False,
        "observer_entry_evidence_exists": False,
        "observer_invoked": False,
        "runtime_record_exists": False,
        "receipt_exists": False,
        "runtime_execution_authorized": False,
        "materialization_authorized": False,
        "scientific_execution_authorized": False,
        "current_authority_id": None,
        "current_claim_id": None,
        "current_runtime_record_raw_sha256": None,
        "current_receipt_raw_sha256": None,
    }
    if payload.get("authorization_state") != expected_state:
        raise ValueError("runtime execution external seal operational state mismatch")
    digest = canonical_execution_contract_raw_sha256(execution_contract_path)
    if digest != payload["execution_contract_raw_sha256"]:
        raise ValueError("external seal does not bind the exact execution contract bytes")
    return MappingProxyType(payload)


def _encode_json_string(value: str) -> bytes:
    chunks = [b'"']
    short = {8: b"\\b", 9: b"\\t", 10: b"\\n", 12: b"\\f", 13: b"\\r"}
    for char in value:
        code = ord(char)
        if 0xD800 <= code <= 0xDFFF:
            raise ValueError("isolated surrogate input is forbidden")
        if code == 0x22:
            chunks.append(b'\\"')
        elif code == 0x5C:
            chunks.append(b"\\\\")
        elif code in short:
            chunks.append(short[code])
        elif code <= 0x1F:
            chunks.append(f"\\u{code:04x}".encode("ascii"))
        elif 0x20 <= code <= 0x7E:
            chunks.append(bytes((code,)))
        elif code <= 0xFFFF:
            chunks.append(f"\\u{code:04x}".encode("ascii"))
        else:
            adjusted = code - 0x10000
            high = 0xD800 + (adjusted >> 10)
            low = 0xDC00 + (adjusted & 0x3FF)
            chunks.append(f"\\u{high:04x}\\u{low:04x}".encode("ascii"))
    chunks.append(b'"')
    return b"".join(chunks)


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize the supported JSON data model to exact H26 canonical bytes."""
    active: set[int] = set()

    def encode(item: Any) -> bytes:
        if item is None:
            return b"null"
        if item is True:
            return b"true"
        if item is False:
            return b"false"
        if type(item) is int:
            return str(item).encode("ascii")
        if isinstance(item, float):
            raise ValueError("all floating-point values are forbidden")
        if isinstance(item, str):
            return _encode_json_string(item)
        if isinstance(item, Mapping):
            identity = id(item)
            if identity in active:
                raise ValueError("cyclic JSON object is forbidden")
            active.add(identity)
            try:
                keys = list(item.keys())
                if any(not isinstance(key, str) for key in keys):
                    raise ValueError("JSON object keys must be strings")
                keys.sort()
                body = b",".join(
                    _encode_json_string(key) + b":" + encode(item[key])
                    for key in keys
                )
                return b"{" + body + b"}"
            finally:
                active.remove(identity)
        if isinstance(item, list):
            identity = id(item)
            if identity in active:
                raise ValueError("cyclic JSON array is forbidden")
            active.add(identity)
            try:
                return b"[" + b",".join(encode(element) for element in item) + b"]"
            finally:
                active.remove(identity)
        raise ValueError(f"unsupported canonical JSON type: {type(item).__name__}")

    return encode(value) + b"\n"


def parse_canonical_json_bytes(raw: bytes) -> Any:
    """Parse exact canonical bytes, rejecting equivalent noncanonical spellings."""
    if type(raw) is not bytes:
        raise TypeError("canonical JSON input must be exact bytes")
    if raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("UTF-8 BOM is forbidden")
    if b"\r" in raw:
        raise ValueError("carriage return and CRLF are forbidden")
    if not raw.endswith(b"\n") or raw.endswith(b"\n\n"):
        raise ValueError("canonical JSON requires exactly one terminal LF")
    body = raw[:-1]
    if b"\n" in body:
        raise ValueError("whitespace outside strings is forbidden")
    try:
        text = body.decode("ascii")
    except UnicodeDecodeError as exc:
        raise ValueError("canonical JSON must be ASCII-safe") from exc

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"floating-point JSON value forbidden: {value}")

    try:
        value = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("invalid canonical JSON") from exc
    canonical = canonical_json_bytes(value)
    if canonical != raw:
        raise ValueError("incoming JSON bytes are not canonical")
    return value


def external_raw_sha256(raw: bytes) -> str:
    if type(raw) is not bytes:
        raise TypeError("raw SHA256 input must be exact bytes")
    return hashlib.sha256(raw).hexdigest()


def validate_authority_id(authority_id: str) -> str:
    if not isinstance(authority_id, str) or not authority_id:
        raise ValueError("authority_id must be a non-empty ASCII string")
    try:
        authority_id.encode("ascii")
    except UnicodeEncodeError as exc:
        raise ValueError("authority_id must be ASCII") from exc
    if authority_id != authority_id.strip():
        raise ValueError("authority_id has leading or trailing whitespace")
    return authority_id


def _validate_sha256(value: str, name: str) -> str:
    if not isinstance(value, str) or _LOWER_SHA256_RE.fullmatch(value) is None:
        raise ValueError(f"{name} must be exactly 64 lowercase hexadecimal digits")
    return value


def derive_claim_id(authority_id: str, authority_raw_sha256: str) -> str:
    authority = validate_authority_id(authority_id).encode("utf-8")
    authority_sha = _validate_sha256(
        authority_raw_sha256, "authority_raw_sha256"
    ).encode("ascii")
    digest = hashlib.sha256(
        _CLAIM_DOMAIN + b"\x00" + authority + b"\x00" + authority_sha
    ).hexdigest()
    return _CLAIM_PREFIX + digest


def derive_claim_slot_identity(authority_id: str, authority_raw_sha256: str) -> str:
    return derive_claim_id(authority_id, authority_raw_sha256)


def derive_observer_entry_evidence_id(
    authority_id: str,
    authority_raw_sha256: str,
    claim_id: str,
    claim_raw_sha256: str,
) -> str:
    authority = validate_authority_id(authority_id)
    authority_sha = _validate_sha256(authority_raw_sha256, "authority_raw_sha256")
    if not isinstance(claim_id, str) or _CLAIM_ID_RE.fullmatch(claim_id) is None:
        raise ValueError("claim_id has invalid canonical syntax")
    expected_claim_id = derive_claim_id(authority, authority_sha)
    if claim_id != expected_claim_id:
        raise ValueError("claim_id does not bind the supplied authority")
    claim_sha = _validate_sha256(claim_raw_sha256, "claim_raw_sha256")
    preimage = b"\x00".join(
        (
            _ENTRY_DOMAIN,
            authority.encode("utf-8"),
            authority_sha.encode("ascii"),
            claim_id.encode("utf-8"),
            claim_sha.encode("ascii"),
        )
    )
    return _ENTRY_PREFIX + hashlib.sha256(preimage).hexdigest()


def derive_observer_entry_slot_identity(
    authority_id: str,
    authority_raw_sha256: str,
    claim_id: str,
    claim_raw_sha256: str,
) -> str:
    return derive_observer_entry_evidence_id(
        authority_id, authority_raw_sha256, claim_id, claim_raw_sha256
    )


def validate_exact_keyset(
    value: Mapping[str, Any], required_fields: Iterable[str], *, label: str
) -> None:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    required = frozenset(required_fields)
    actual = frozenset(value.keys())
    if any(not isinstance(key, str) for key in value.keys()):
        raise ValueError(f"{label} keys must be strings")
    if actual != required:
        missing = sorted(required - actual)
        extra = sorted(actual - required)
        raise ValueError(f"{label} key set mismatch: missing={missing}, extra={extra}")


def validate_authority_keyset(value: Mapping[str, Any]) -> None:
    validate_exact_keyset(value, AUTHORITY_REQUIRED_FIELDS, label="authority")


def validate_claim_keyset(value: Mapping[str, Any]) -> None:
    validate_exact_keyset(value, CLAIM_REQUIRED_FIELDS, label="claim")


def validate_observer_entry_evidence_keyset(value: Mapping[str, Any]) -> None:
    validate_exact_keyset(
        value, OBSERVER_ENTRY_EVIDENCE_REQUIRED_FIELDS, label="observer entry evidence"
    )


def validate_receipt_keyset(value: Mapping[str, Any]) -> None:
    validate_exact_keyset(value, RECEIPT_REQUIRED_FIELDS, label="receipt")


__all__ = [
    "APPROVED_DORMANT_QUALIFIER_COMMIT",
    "APPROVED_DORMANT_QUALIFIER_GIT_BLOB_SHA",
    "APPROVED_DORMANT_PRIMITIVES_COMMIT",
    "APPROVED_DORMANT_PRIMITIVES_GIT_BLOB_SHA",
    "AUTHORITY_REQUIRED_FIELDS",
    "CLAIM_REQUIRED_FIELDS",
    "EXECUTION_AUTHORITY_CONTRACT_COMMIT",
    "EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA",
    "EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256",
    "EXTERNAL_SEAL_COMMIT",
    "EXTERNAL_SEAL_GIT_BLOB_SHA",
    "OBSERVER_ENTRY_EVIDENCE_REQUIRED_FIELDS",
    "RECEIPT_REQUIRED_FIELDS",
    "RUNTIME_QUALIFICATION_CONTRACT_COMMIT",
    "RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA",
    "RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256",
    "canonical_json_bytes",
    "canonical_execution_contract_raw_sha256",
    "derive_claim_id",
    "derive_claim_slot_identity",
    "derive_observer_entry_evidence_id",
    "derive_observer_entry_slot_identity",
    "external_raw_sha256",
    "load_runtime_execution_contract",
    "load_runtime_execution_external_seal",
    "parse_canonical_json_bytes",
    "validate_authority_id",
    "validate_authority_keyset",
    "validate_claim_keyset",
    "validate_exact_keyset",
    "validate_observer_entry_evidence_keyset",
    "validate_receipt_keyset",
]
