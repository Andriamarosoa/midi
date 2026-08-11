"""Dormant pure validator for an artificial H26 materialization authority.

This module never constructs or publishes an authority or its external seal. It
only validates a caller-supplied in-memory artifact against reviewed contracts.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple

from src.polyphonic import harmonic_censoring_h26_materialization_authority_contract_seal as _seal
from src.polyphonic import harmonic_censoring_h26_materialization_runtime_execution_proof as _proof
from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as _runtime
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as _qualifier


ARTIFACT_CONTRACT_COMMIT = "dd24346e6bf6f50af13e10f8c5ca5d1281242088"
ARTIFACT_CONTRACT_GIT_BLOB_SHA = "b6b98b4cb205cb6c2f1c49e6f07b121e1e6b45f8"
APPROVED_SEAL_LOADER_COMMIT = "88593f7f065e7492af566e2ca90577c09916923e"
APPROVED_SEAL_LOADER_GIT_BLOB_SHA = "39316388a777ea34fb6b2b560809f2b679475732"
APPROVED_PROOF_VALIDATOR_COMMIT = "18b8d5a73e61ab9143b897cb68479ae571c62bca"
APPROVED_PROOF_VALIDATOR_GIT_BLOB_SHA = "fd5e40fb7307929e18fdc99d518692315b22f381"
LOADER_REVIEW_CLOSURE_COMMIT = "f51eac200ca83d02a2c6fd750e2ac4c90cf6865d"

_APPROVED_ARTIFACT_CONTRACT_COMMIT = "dd24346e6bf6f50af13e10f8c5ca5d1281242088"
_APPROVED_ARTIFACT_CONTRACT_GIT_BLOB_SHA = "b6b98b4cb205cb6c2f1c49e6f07b121e1e6b45f8"
_APPROVED_SEAL_LOADER_COMMIT = "88593f7f065e7492af566e2ca90577c09916923e"
_APPROVED_SEAL_LOADER_GIT_BLOB_SHA = "39316388a777ea34fb6b2b560809f2b679475732"
_APPROVED_PROOF_VALIDATOR_COMMIT = "18b8d5a73e61ab9143b897cb68479ae571c62bca"
_APPROVED_PROOF_VALIDATOR_GIT_BLOB_SHA = "fd5e40fb7307929e18fdc99d518692315b22f381"
_APPROVED_LOADER_REVIEW_CLOSURE_COMMIT = "f51eac200ca83d02a2c6fd750e2ac4c90cf6865d"
_DOMAIN = b"H26_MATERIALIZATION_AUTHORITY_ID_V1"
_ID_PREFIX = "h26-materialization-authority-v1-"
_ISSUER_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:@/-]{0,127}$", re.ASCII)
_ISSUED_AT_RE = re.compile(
    r"^[0-9]{4}-(0[1-9]|1[0-2])-([0-2][0-9]|3[0-1])T"
    r"([01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9]Z$",
    re.ASCII,
)


@dataclass(frozen=True)
class ValidatedH26MaterializationAuthorityArtifact:
    authority_id: str
    canonical_bytes: bytes
    raw_sha256: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _canonical_git_text_bytes(raw: bytes) -> bytes:
    if b"\r" in raw:
        if b"\r" in raw.replace(b"\r\n", b""):
            raise ValueError("reviewed text contains a non-CRLF carriage return")
        raw = raw.replace(b"\r\n", b"\n")
    return raw


def _git_blob_sha(raw: bytes) -> str:
    canonical = _canonical_git_text_bytes(raw)
    return hashlib.sha1(
        f"blob {len(canonical)}\0".encode("ascii") + canonical
    ).hexdigest()


def _strict_json(raw: bytes) -> dict[str, Any]:
    raw = _canonical_git_text_bytes(raw)
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("authority artifact contract is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("authority artifact contract has a forbidden BOM")

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
        raise ValueError("invalid authority artifact contract JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("authority artifact contract must be an object")
    return value


def _require_reviewed_bindings() -> None:
    bindings = (
        ("artifact contract commit", ARTIFACT_CONTRACT_COMMIT, _APPROVED_ARTIFACT_CONTRACT_COMMIT),
        ("artifact contract blob", ARTIFACT_CONTRACT_GIT_BLOB_SHA, _APPROVED_ARTIFACT_CONTRACT_GIT_BLOB_SHA),
        ("seal loader commit", APPROVED_SEAL_LOADER_COMMIT, _APPROVED_SEAL_LOADER_COMMIT),
        ("seal loader blob", APPROVED_SEAL_LOADER_GIT_BLOB_SHA, _APPROVED_SEAL_LOADER_GIT_BLOB_SHA),
        ("proof validator commit", APPROVED_PROOF_VALIDATOR_COMMIT, _APPROVED_PROOF_VALIDATOR_COMMIT),
        ("proof validator blob", APPROVED_PROOF_VALIDATOR_GIT_BLOB_SHA, _APPROVED_PROOF_VALIDATOR_GIT_BLOB_SHA),
        ("loader review closure", LOADER_REVIEW_CLOSURE_COMMIT, _APPROVED_LOADER_REVIEW_CLOSURE_COMMIT),
    )
    for label, actual, expected in bindings:
        if actual != expected:
            raise ValueError(f"{label} binding mismatch")
    paths = (
        (Path(_seal.__file__), APPROVED_SEAL_LOADER_GIT_BLOB_SHA, "seal loader"),
        (Path(_proof.__file__), APPROVED_PROOF_VALIDATOR_GIT_BLOB_SHA, "proof validator"),
    )
    for path, expected, label in paths:
        if _git_blob_sha(path.resolve(strict=True).read_bytes()) != expected:
            raise ValueError(f"{label} Git blob mismatch")


def load_materialization_authority_artifact_contract(
    path: Optional[Path] = None,
) -> Mapping[str, Any]:
    """Load only the exact reviewed dormant artifact contract."""
    _require_reviewed_bindings()
    _seal.load_materialization_authority_contract_external_seal()
    contract_path = path or (
        _repo_root()
        / "configs"
        / "harmonic_censoring_h26_materialization_authority_artifact_contract.json"
    )
    raw = contract_path.resolve(strict=True).read_bytes()
    if _git_blob_sha(raw) != ARTIFACT_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("authority artifact contract Git blob mismatch")
    payload = _strict_json(raw)
    expected_top = {
        "schema_identity": "H26_MATERIALIZATION_AUTHORITY_ARTIFACT_CANONICALIZATION_AND_VALIDATION_CONTRACT_V1",
        "schema_version": 1,
        "status": "DECLARATIVE_DORMANT_NO_ISSUER_NO_AUTHORITY_NO_CLAIM_NO_DESTINATION_NO_EXECUTION",
    }
    for key, expected in expected_top.items():
        if type(payload.get(key)) is not type(expected) or payload.get(key) != expected:
            raise ValueError(f"authority artifact contract {key} mismatch")
    chain = payload.get("approved_binding_chain")
    if not isinstance(chain, dict) or chain.get(
        "approved_external_contract_seal_loader_module_git_blob_sha"
    ) != APPROVED_SEAL_LOADER_GIT_BLOB_SHA or chain.get(
        "external_contract_seal_loader_review_closure_commit"
    ) != LOADER_REVIEW_CLOSURE_COMMIT:
        raise ValueError("authority artifact approved binding chain mismatch")
    state = payload.get("current_state")
    if not isinstance(state, dict) or any(value not in (False, None) for value in state.values()):
        raise ValueError("authority artifact contract is not dormant")
    return MappingProxyType(payload)


def _artifact_rules() -> tuple[tuple[str, ...], Mapping[str, str], Mapping[str, Any]]:
    contract = load_materialization_authority_artifact_contract()
    rules = contract.get("future_authority_artifact")
    if not isinstance(rules, dict):
        raise ValueError("future authority artifact rules missing")
    fields = rules.get("exact_keyset_in_contract_order")
    types = rules.get("field_types")
    fixed = rules.get("fixed_values")
    if not isinstance(fields, list) or not all(isinstance(x, str) for x in fields):
        raise ValueError("authority keyset contract mismatch")
    if not isinstance(types, dict) or set(types) != set(fields):
        raise ValueError("authority field type contract mismatch")
    if not isinstance(fixed, dict) or len(fixed) != 24:
        raise ValueError("authority fixed values contract mismatch")
    return tuple(fields), types, fixed


def _require_type(field: str, value: Any, kind: str) -> None:
    accepted = {
        "string": type(value) is str,
        "boolean": type(value) is bool,
        "integer_not_boolean": type(value) is int,
    }.get(kind)
    if accepted is not True:
        raise ValueError(f"authority field {field} type mismatch")


def derive_materialization_authority_id(authority: Mapping[str, Any]) -> str:
    """Purely derive the sole permitted ID from a complete 36-field object."""
    fields, _, _ = _artifact_rules()
    if set(authority) != set(fields):
        raise ValueError("authority exact keyset mismatch")
    payload = dict(authority)
    payload.pop("authority_id")
    encoded = _runtime.canonical_json_bytes(payload)
    digest = hashlib.sha256(_DOMAIN + b"\0" + encoded).hexdigest()
    return _ID_PREFIX + digest


def _validate_destination(value: str) -> None:
    if not value.startswith("/") or value.startswith("//") or value == "/":
        raise ValueError("absolute_destination must be an absolute POSIX non-root path")
    if value.endswith("/") or "\0" in value:
        raise ValueError("absolute_destination syntax mismatch")
    if any(part in ("", ".", "..") for part in value.split("/")[1:]):
        raise ValueError("absolute_destination contains a forbidden segment")


def _validate_issued_at(value: str) -> None:
    if _ISSUED_AT_RE.fullmatch(value) is None:
        raise ValueError("issued_at syntax mismatch")
    try:
        parsed = datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")
    except ValueError as exc:
        raise ValueError("issued_at is not a valid Gregorian UTC date-time") from exc
    if parsed.strftime("%Y-%m-%dT%H:%M:%SZ") != value:
        raise ValueError("issued_at canonical form mismatch")


def validate_artificial_materialization_authority_artifact(
    authority: Mapping[str, Any],
    *,
    runtime_authority: Mapping[str, Any],
    runtime_claim: Mapping[str, Any],
    runtime_evidence: Mapping[str, Any],
    runtime_receipt: Mapping[str, Any],
    runtime_authority_raw_sha256: str,
    runtime_claim_raw_sha256: str,
    runtime_evidence_raw_sha256: str,
    runtime_receipt_raw_sha256: str,
    runtime_record: Optional[_qualifier.H26RuntimeQualificationRecord],
) -> ValidatedH26MaterializationAuthorityArtifact:
    """Validate one artificial authority and return immutable canonical bytes."""
    fields, types, fixed = _artifact_rules()
    if set(authority) != set(fields) or len(authority) != len(fields):
        raise ValueError("authority exact keyset mismatch")
    for field in fields:
        _require_type(field, authority[field], types[field])
    for field, expected in fixed.items():
        if type(authority[field]) is not type(expected) or authority[field] != expected:
            raise ValueError(f"authority fixed field {field} mismatch")

    validated_proof = _proof.validate_artificial_materialization_runtime_execution_proof(
        runtime_authority,
        runtime_claim,
        runtime_evidence,
        runtime_receipt,
        runtime_authority_raw_sha256,
        runtime_claim_raw_sha256,
        runtime_evidence_raw_sha256,
        runtime_receipt_raw_sha256,
        runtime_record,
    )
    projection = asdict(validated_proof)
    for field, expected in projection.items():
        if authority[field] != expected:
            raise ValueError(f"authority runtime proof projection {field} mismatch")

    _validate_destination(authority["absolute_destination"])
    _validate_issued_at(authority["issued_at"])
    if _ISSUER_RE.fullmatch(authority["issuer_identity"]) is None:
        raise ValueError("issuer_identity syntax mismatch")
    derived = derive_materialization_authority_id(authority)
    if authority["authority_id"] != derived:
        raise ValueError("authority_id derivation mismatch")
    canonical = _runtime.canonical_json_bytes(dict(authority))
    return ValidatedH26MaterializationAuthorityArtifact(
        authority_id=derived,
        canonical_bytes=canonical,
        raw_sha256=_runtime.external_raw_sha256(canonical),
    )


__all__ = [
    "APPROVED_PROOF_VALIDATOR_COMMIT",
    "APPROVED_PROOF_VALIDATOR_GIT_BLOB_SHA",
    "APPROVED_SEAL_LOADER_COMMIT",
    "APPROVED_SEAL_LOADER_GIT_BLOB_SHA",
    "ARTIFACT_CONTRACT_COMMIT",
    "ARTIFACT_CONTRACT_GIT_BLOB_SHA",
    "LOADER_REVIEW_CLOSURE_COMMIT",
    "ValidatedH26MaterializationAuthorityArtifact",
    "derive_materialization_authority_id",
    "load_materialization_authority_artifact_contract",
    "validate_artificial_materialization_authority_artifact",
]
