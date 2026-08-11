"""Dormant in-memory validator for an artificial H26 runtime activation.

The module validates caller-supplied mappings only. It has no issuer,
capability, writer, path factory, runtime observer, or scientific entrypoint.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Tuple

from src.polyphonic import (
    harmonic_censoring_h26_runtime_execution_primitives as _runtime,
)
from src.polyphonic import (
    harmonic_censoring_h26_runtime_qualification_operational_activation_contract_seal
    as _seal,
)


ACTIVATION_CONTRACT_COMMIT = "d8d71bad9aee560d3406e672e7ebc6c2cf11dbff"
ACTIVATION_CONTRACT_GIT_BLOB_SHA = "c6eac6ae2d05b99a1a5b88594dea473739904dd8"
ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH = 16050
ACTIVATION_CONTRACT_RAW_SHA256 = "ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01"
EXTERNAL_SEAL_COMMIT = "ce4aa59f75d3ff3836bce91c6be9739a16448199"
EXTERNAL_SEAL_GIT_BLOB_SHA = "685915e6e15a760fb439089752402ccb29c142f7"
APPROVED_SEAL_LOADER_COMMIT = "37f5f2d502b4eae9d878c5c0f47155a7b26c856b"
APPROVED_SEAL_LOADER_GIT_BLOB_SHA = "feacb3c10c269b5f574e8d7efab8211be145b5d8"
SEAL_LOADER_REVIEW_CLOSURE_COMMIT = "f0f18f54439a643c4b49f77ee6126449290a02db"

_APPROVED_ACTIVATION_CONTRACT_COMMIT = "d8d71bad9aee560d3406e672e7ebc6c2cf11dbff"
_APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_SHA = "c6eac6ae2d05b99a1a5b88594dea473739904dd8"
_APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH = 16050
_APPROVED_ACTIVATION_CONTRACT_RAW_SHA256 = "ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01"
_APPROVED_EXTERNAL_SEAL_COMMIT = "ce4aa59f75d3ff3836bce91c6be9739a16448199"
_APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA = "685915e6e15a760fb439089752402ccb29c142f7"
_APPROVED_SEAL_LOADER_COMMIT_VALUE = "37f5f2d502b4eae9d878c5c0f47155a7b26c856b"
_APPROVED_SEAL_LOADER_GIT_BLOB_SHA_VALUE = "feacb3c10c269b5f574e8d7efab8211be145b5d8"
_APPROVED_SEAL_LOADER_REVIEW_CLOSURE_COMMIT = "f0f18f54439a643c4b49f77ee6126449290a02db"
_DOMAIN = b"H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ID_V1"
_ID_PREFIX = "h26-runtime-activation-v1-"


@dataclass(frozen=True)
class ValidatedH26RuntimeQualificationOperationalActivation:
    activation_id: str
    canonical_bytes: bytes
    raw_sha256: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git_text_bytes(raw: bytes) -> bytes:
    if b"\r" in raw:
        if b"\r" in raw.replace(b"\r\n", b""):
            raise ValueError("reviewed text contains a non-CRLF carriage return")
        raw = raw.replace(b"\r\n", b"\n")
    return raw


def _git_blob_sha(raw: bytes) -> str:
    canonical = _git_text_bytes(raw)
    return hashlib.sha1(
        f"blob {len(canonical)}\0".encode("ascii") + canonical
    ).hexdigest()


def _strict_json(raw: bytes) -> dict[str, Any]:
    canonical = _git_text_bytes(raw)
    try:
        text = canonical.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("activation contract is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("activation contract has a forbidden BOM")

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate activation contract JSON key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"floating-point activation contract value forbidden: {value}")

    try:
        payload = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("invalid activation contract JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("activation contract must be an object")
    return payload


def _require_reviewed_bindings() -> None:
    bindings = (
        ("activation contract commit", ACTIVATION_CONTRACT_COMMIT, _APPROVED_ACTIVATION_CONTRACT_COMMIT),
        ("activation contract blob", ACTIVATION_CONTRACT_GIT_BLOB_SHA, _APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_SHA),
        ("activation contract length", ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH, _APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH),
        ("activation contract SHA256", ACTIVATION_CONTRACT_RAW_SHA256, _APPROVED_ACTIVATION_CONTRACT_RAW_SHA256),
        ("external seal commit", EXTERNAL_SEAL_COMMIT, _APPROVED_EXTERNAL_SEAL_COMMIT),
        ("external seal blob", EXTERNAL_SEAL_GIT_BLOB_SHA, _APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA),
        ("approved seal loader commit", APPROVED_SEAL_LOADER_COMMIT, _APPROVED_SEAL_LOADER_COMMIT_VALUE),
        ("approved seal loader blob", APPROVED_SEAL_LOADER_GIT_BLOB_SHA, _APPROVED_SEAL_LOADER_GIT_BLOB_SHA_VALUE),
        ("seal loader review closure", SEAL_LOADER_REVIEW_CLOSURE_COMMIT, _APPROVED_SEAL_LOADER_REVIEW_CLOSURE_COMMIT),
    )
    for label, actual, expected in bindings:
        if actual != expected:
            raise ValueError(f"{label} binding mismatch")
    loader_raw = Path(_seal.__file__).resolve(strict=True).read_bytes()
    if _git_blob_sha(loader_raw) != APPROVED_SEAL_LOADER_GIT_BLOB_SHA:
        raise ValueError("approved activation seal loader Git blob mismatch")


def _activation_rules() -> tuple[tuple[str, ...], Mapping[str, str], Mapping[str, Any]]:
    _require_reviewed_bindings()
    _seal.load_runtime_qualification_operational_activation_contract_external_seal()
    path = (
        _repo_root()
        / "configs"
        / "harmonic_censoring_h26_runtime_qualification_operational_activation_contract.json"
    )
    checkout_raw = path.resolve(strict=True).read_bytes()
    raw = _git_text_bytes(checkout_raw)
    if _git_blob_sha(checkout_raw) != ACTIVATION_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("activation contract Git blob mismatch")
    if len(raw) != ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH:
        raise ValueError("activation contract Git byte length mismatch")
    if hashlib.sha256(raw).hexdigest() != ACTIVATION_CONTRACT_RAW_SHA256:
        raise ValueError("activation contract raw SHA256 mismatch")
    contract = _strict_json(raw)
    rules = contract.get("future_operational_activation")
    if not isinstance(rules, dict):
        raise ValueError("future operational activation rules missing")
    if rules.get("schema_identity") != "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_V1":
        raise ValueError("operational activation schema identity mismatch")
    if type(rules.get("schema_version")) is not int or rules.get("schema_version") != 1:
        raise ValueError("operational activation schema version mismatch")
    if rules.get("creation_authorized_now") is not False:
        raise ValueError("operational activation contract is not dormant")
    fields = rules.get("exact_keyset")
    types = rules.get("field_types")
    fixed = rules.get("fixed_values")
    if not isinstance(fields, list) or len(fields) != 26 or not all(
        type(field) is str for field in fields
    ):
        raise ValueError("operational activation keyset mismatch")
    if not isinstance(types, dict) or set(types) != set(fields):
        raise ValueError("operational activation field type contract mismatch")
    if not isinstance(fixed, dict):
        raise ValueError("operational activation fixed values missing")
    return tuple(fields), types, fixed


def _require_type(field: str, value: Any, kind: str) -> None:
    accepted = {
        "string": type(value) is str,
        "boolean": type(value) is bool,
        "integer_not_boolean": type(value) is int,
    }.get(kind)
    if accepted is not True:
        raise ValueError(f"activation field {field} type mismatch")


def _validate_administrative_root(value: str) -> None:
    if not value.startswith("/") or value.startswith("//") or value == "/":
        raise ValueError("administrative_root must be an absolute POSIX non-root path")
    if value.endswith("/") or "\0" in value:
        raise ValueError("administrative_root syntax mismatch")
    if any(part in ("", ".", "..") for part in value.split("/")[1:]):
        raise ValueError("administrative_root contains a forbidden segment")


def derive_runtime_qualification_operational_activation_id(
    activation: Mapping[str, Any],
) -> str:
    """Derive the only valid activation ID without creating an activation."""
    fields, _, _ = _activation_rules()
    if set(activation) != set(fields) or len(activation) != len(fields):
        raise ValueError("activation exact keyset mismatch")
    payload = dict(activation)
    payload.pop("activation_id")
    encoded = _runtime.canonical_json_bytes(payload)
    digest = hashlib.sha256(_DOMAIN + b"\0" + encoded).hexdigest()
    return _ID_PREFIX + digest


def validate_artificial_runtime_qualification_operational_activation(
    activation: Mapping[str, Any],
) -> ValidatedH26RuntimeQualificationOperationalActivation:
    """Validate one artificial activation and return immutable in-memory proof."""
    fields, types, fixed = _activation_rules()
    if set(activation) != set(fields) or len(activation) != len(fields):
        raise ValueError("activation exact keyset mismatch")
    for field in fields:
        _require_type(field, activation[field], types[field])
    for field, expected in fixed.items():
        if type(activation[field]) is not type(expected) or activation[field] != expected:
            raise ValueError(f"activation fixed field {field} mismatch")
    required_bindings = {
        "activation_contract_commit": ACTIVATION_CONTRACT_COMMIT,
        "activation_contract_raw_sha256": ACTIVATION_CONTRACT_RAW_SHA256,
    }
    for field, expected in required_bindings.items():
        if activation[field] != expected:
            raise ValueError(f"activation field {field} binding mismatch")
    _validate_administrative_root(activation["administrative_root"])
    derived = derive_runtime_qualification_operational_activation_id(activation)
    if activation["activation_id"] != derived:
        raise ValueError("activation_id derivation mismatch")
    canonical = _runtime.canonical_json_bytes(dict(activation))
    return ValidatedH26RuntimeQualificationOperationalActivation(
        activation_id=derived,
        canonical_bytes=canonical,
        raw_sha256=hashlib.sha256(canonical).hexdigest(),
    )


__all__ = [
    "ACTIVATION_CONTRACT_COMMIT",
    "ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH",
    "ACTIVATION_CONTRACT_GIT_BLOB_SHA",
    "ACTIVATION_CONTRACT_RAW_SHA256",
    "APPROVED_SEAL_LOADER_COMMIT",
    "APPROVED_SEAL_LOADER_GIT_BLOB_SHA",
    "EXTERNAL_SEAL_COMMIT",
    "EXTERNAL_SEAL_GIT_BLOB_SHA",
    "SEAL_LOADER_REVIEW_CLOSURE_COMMIT",
    "ValidatedH26RuntimeQualificationOperationalActivation",
    "derive_runtime_qualification_operational_activation_id",
    "validate_artificial_runtime_qualification_operational_activation",
]
