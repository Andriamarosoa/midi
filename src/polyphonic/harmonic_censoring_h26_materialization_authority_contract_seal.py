"""Dormant fail-closed loader for the corrected H26 materialization seal.

This module only validates reviewed declarative bytes.  It does not issue an
authority, create a claim or destination, run the observer or materializer, or
perform any scientific calculation.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple


EXTERNAL_SEAL_COMMIT = "eb058ed2297997bd709ab0802913a62c68d5c427"
EXTERNAL_SEAL_GIT_BLOB_SHA = "8f5ab4f2aba65104f27a3eb8e1281b5df9ce9e92"
CORRECTED_CONTRACT_COMMIT = "84d1a196635c6ace7f3ea5ec9b7e338f5da70300"
CORRECTED_CONTRACT_GIT_BLOB_SHA = "94f255c583a52d660dc57f70df80b97173791296"
CORRECTED_CONTRACT_BYTE_LENGTH = 19310
CORRECTED_CONTRACT_RAW_SHA256 = (
    "a82b00cfe197dc927dcc7a34ee409b7ea8ab374f36b6e41ebdaea12710258002"
)
PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT = (
    "0ff5f5e4dffa30605292c293ff4f3a367fb41852"
)
APPROVED_PROOF_VALIDATOR_COMMIT = "18b8d5a73e61ab9143b897cb68479ae571c62bca"
APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA = (
    "fd5e40fb7307929e18fdc99d518692315b22f381"
)

_APPROVED_EXTERNAL_SEAL_COMMIT = EXTERNAL_SEAL_COMMIT
_APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA = EXTERNAL_SEAL_GIT_BLOB_SHA
_APPROVED_CORRECTED_CONTRACT_COMMIT = CORRECTED_CONTRACT_COMMIT
_APPROVED_CORRECTED_CONTRACT_GIT_BLOB_SHA = CORRECTED_CONTRACT_GIT_BLOB_SHA
_APPROVED_CORRECTED_CONTRACT_BYTE_LENGTH = CORRECTED_CONTRACT_BYTE_LENGTH
_APPROVED_CORRECTED_CONTRACT_RAW_SHA256 = CORRECTED_CONTRACT_RAW_SHA256
_APPROVED_PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT = (
    PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT
)
_APPROVED_PROOF_VALIDATOR_COMMIT = APPROVED_PROOF_VALIDATOR_COMMIT
_APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA = (
    APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA
)

_EXPECTED_AUTHORIZATION_STATE = {
    "issuer_exists": False,
    "materialization_authority_exists": False,
    "materialization_claim_exists": False,
    "materialization_claim_consumed": False,
    "runtime_execution_authorized": False,
    "runtime_execution_authority_exists": False,
    "runtime_execution_claim_exists": False,
    "runtime_execution_observer_entry_evidence_exists": False,
    "runtime_execution_receipt_exists": False,
    "runtime_record_exists": False,
    "materialization_authorized": False,
    "population_exists": False,
    "scientific_execution_authorized": False,
    "locked_test_used": False,
    "current_materialization_authority_id": None,
    "current_materialization_claim_id": None,
    "current_runtime_record_raw_sha256": None,
    "current_population_raw_sha256": None,
}


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _external_seal_path() -> Path:
    return (
        _repository_root()
        / "configs"
        / "harmonic_censoring_h26_population_materialization_authority_contract_external_seal.json"
    )


def _corrected_contract_path() -> Path:
    return (
        _repository_root()
        / "configs"
        / "harmonic_censoring_h26_population_materialization_authority_contract.json"
    )


def _proof_validator_path() -> Path:
    return (
        _repository_root()
        / "src"
        / "polyphonic"
        / "harmonic_censoring_h26_materialization_runtime_execution_proof.py"
    )


def _canonical_git_text_bytes(raw: bytes) -> bytes:
    if b"\r" in raw:
        if b"\r" in raw.replace(b"\r\n", b""):
            raise ValueError("text contains a non-CRLF carriage return")
        raw = raw.replace(b"\r\n", b"\n")
    return raw


def _git_blob_sha(raw: bytes) -> str:
    canonical = _canonical_git_text_bytes(raw)
    header = f"blob {len(canonical)}\0".encode("ascii")
    return hashlib.sha1(header + canonical).hexdigest()


def _strict_json(raw: bytes) -> dict[str, Any]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("materialization seal JSON is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("materialization seal JSON has a forbidden BOM")

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
        raise ValueError("invalid materialization seal JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("materialization seal must be an object")
    return payload


def _require_public_bindings() -> None:
    bindings = (
        (EXTERNAL_SEAL_COMMIT, _APPROVED_EXTERNAL_SEAL_COMMIT, "seal commit"),
        (
            EXTERNAL_SEAL_GIT_BLOB_SHA,
            _APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA,
            "seal Git blob",
        ),
        (
            CORRECTED_CONTRACT_COMMIT,
            _APPROVED_CORRECTED_CONTRACT_COMMIT,
            "corrected contract commit",
        ),
        (
            CORRECTED_CONTRACT_GIT_BLOB_SHA,
            _APPROVED_CORRECTED_CONTRACT_GIT_BLOB_SHA,
            "corrected contract Git blob",
        ),
        (
            CORRECTED_CONTRACT_BYTE_LENGTH,
            _APPROVED_CORRECTED_CONTRACT_BYTE_LENGTH,
            "corrected contract byte length",
        ),
        (
            CORRECTED_CONTRACT_RAW_SHA256,
            _APPROVED_CORRECTED_CONTRACT_RAW_SHA256,
            "corrected contract raw SHA256",
        ),
        (
            PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT,
            _APPROVED_PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT,
            "proof-validator closure commit",
        ),
        (
            APPROVED_PROOF_VALIDATOR_COMMIT,
            _APPROVED_PROOF_VALIDATOR_COMMIT,
            "proof-validator commit",
        ),
        (
            APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA,
            _APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA,
            "proof-validator module Git blob",
        ),
    )
    for current, approved, label in bindings:
        if type(current) is not type(approved) or current != approved:
            raise ValueError(f"H26 {label} binding mismatch")


def _read_exact_text_blob(path: Path, expected_blob_sha: str, label: str) -> bytes:
    raw = path.resolve(strict=True).read_bytes()
    if _git_blob_sha(raw) != expected_blob_sha:
        raise ValueError(f"H26 {label} Git blob mismatch")
    return _canonical_git_text_bytes(raw)


def canonical_corrected_materialization_authority_contract_bytes(
    path: Optional[Path] = None,
) -> bytes:
    """Return only the exact LF Git bytes of the corrected dormant contract."""
    _require_public_bindings()
    raw = _read_exact_text_blob(
        path or _corrected_contract_path(),
        CORRECTED_CONTRACT_GIT_BLOB_SHA,
        "corrected materialization authority contract",
    )
    if len(raw) != CORRECTED_CONTRACT_BYTE_LENGTH:
        raise ValueError("H26 corrected contract byte length mismatch")
    if hashlib.sha256(raw).hexdigest() != CORRECTED_CONTRACT_RAW_SHA256:
        raise ValueError("H26 corrected contract raw SHA256 mismatch")
    return raw


def canonical_corrected_materialization_authority_contract_raw_sha256(
    path: Optional[Path] = None,
) -> str:
    """Recalculate the sealed SHA256 from the exact corrected contract bytes."""
    raw = canonical_corrected_materialization_authority_contract_bytes(path)
    return hashlib.sha256(raw).hexdigest()


def load_materialization_authority_contract_external_seal(
    path: Optional[Path] = None,
    *,
    corrected_contract_path: Optional[Path] = None,
    proof_validator_path: Optional[Path] = None,
) -> Mapping[str, Any]:
    """Load the exact dormant seal and rebind every reviewed byte identity."""
    _require_public_bindings()

    # The exact seal blob is verified before any JSON interpretation.
    seal_raw = _read_exact_text_blob(
        path or _external_seal_path(),
        EXTERNAL_SEAL_GIT_BLOB_SHA,
        "materialization authority external seal",
    )
    payload = _strict_json(seal_raw)

    expected_scalars = {
        "schema_identity": (
            "H26_POPULATION_MATERIALIZATION_AUTHORITY_CONTRACT_EXTERNAL_SEAL_V1"
        ),
        "schema_version": 1,
        "status": "DECLARATIVE_EXTERNAL_SEAL_ONLY_NO_MATERIALIZATION_AUTHORITY",
        "corrected_materialization_authority_contract_commit": CORRECTED_CONTRACT_COMMIT,
        "corrected_materialization_authority_contract_git_blob_sha": CORRECTED_CONTRACT_GIT_BLOB_SHA,
        "corrected_materialization_authority_contract_git_blob_byte_length": CORRECTED_CONTRACT_BYTE_LENGTH,
        "corrected_materialization_authority_contract_raw_sha256": CORRECTED_CONTRACT_RAW_SHA256,
        "proof_validator_review_closure_commit": PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT,
        "approved_proof_validator_commit": APPROVED_PROOF_VALIDATOR_COMMIT,
        "approved_proof_validator_module_git_blob_sha": APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA,
        "seal_contains_own_raw_sha256": False,
    }
    for key, expected in expected_scalars.items():
        if type(payload.get(key)) is not type(expected) or payload.get(key) != expected:
            raise ValueError(f"H26 materialization authority seal {key} mismatch")
    if payload.get("authorization_state") != _EXPECTED_AUTHORIZATION_STATE:
        raise ValueError("H26 materialization authority seal operational state mismatch")

    contract_digest = canonical_corrected_materialization_authority_contract_raw_sha256(
        corrected_contract_path
    )
    if contract_digest != payload[
        "corrected_materialization_authority_contract_raw_sha256"
    ]:
        raise ValueError("H26 seal does not bind the exact corrected contract bytes")

    _read_exact_text_blob(
        proof_validator_path or _proof_validator_path(),
        APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA,
        "approved proof-validator module",
    )
    return MappingProxyType(payload)


__all__ = [
    "APPROVED_PROOF_VALIDATOR_COMMIT",
    "APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA",
    "CORRECTED_CONTRACT_BYTE_LENGTH",
    "CORRECTED_CONTRACT_COMMIT",
    "CORRECTED_CONTRACT_GIT_BLOB_SHA",
    "CORRECTED_CONTRACT_RAW_SHA256",
    "EXTERNAL_SEAL_COMMIT",
    "EXTERNAL_SEAL_GIT_BLOB_SHA",
    "PROOF_VALIDATOR_REVIEW_CLOSURE_COMMIT",
    "canonical_corrected_materialization_authority_contract_bytes",
    "canonical_corrected_materialization_authority_contract_raw_sha256",
    "load_materialization_authority_contract_external_seal",
]
