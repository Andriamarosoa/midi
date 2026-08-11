"""Dormant loader for the H26 activation issuance-contract external seal."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple

EXTERNAL_SEAL_COMMIT = "f738ced5e79316c162bc2822b2881703858cd146"
EXTERNAL_SEAL_GIT_BLOB_SHA = "975036e8182c22232f8dd0a2aa1f9a61c6022669"
ISSUANCE_CONTRACT_COMMIT = "2f933536fb40603e8a4f2b7c6e9810ec0e0d366a"
ISSUANCE_CONTRACT_GIT_BLOB_SHA = "05ec1c26edbd36cdf6d127f7e8361596f9a20958"
ISSUANCE_CONTRACT_GIT_BLOB_BYTE_LENGTH = 5624
ISSUANCE_CONTRACT_RAW_SHA256 = "e15dcb79da60a5e22a9d0f76c30786b05b90fbefc7e0b71f32a3cbe74052dbe7"
_APPROVED_BINDINGS = (EXTERNAL_SEAL_COMMIT, EXTERNAL_SEAL_GIT_BLOB_SHA, ISSUANCE_CONTRACT_COMMIT, ISSUANCE_CONTRACT_GIT_BLOB_SHA, ISSUANCE_CONTRACT_GIT_BLOB_BYTE_LENGTH, ISSUANCE_CONTRACT_RAW_SHA256)
_EXPECTED_STATE = {
    "issuance_contract_exists": True, "issuer_exists": False,
    "activation_exists": False, "capability_exists": False,
    "administrative_root": None, "runtime_authority_exists": False,
    "claim_exists": False, "observer_invoked": False,
    "runtime_execution_authorized": False, "materialization_authorized": False,
    "p0_executed": False, "p1_executed": False, "p2_executed": False,
    "scientific_execution_authorized": False, "locked_test_used": False,
}

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
    return hashlib.sha1(f"blob {len(canonical)}\0".encode("ascii") + canonical).hexdigest()

def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    text = _git_text_bytes(raw).decode("utf-8")
    if text.startswith("\ufeff"):
        raise ValueError(f"{label} has a forbidden BOM")
    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key in {label}: {key}")
            result[key] = value
        return result
    def reject_float(value: str) -> Any:
        raise ValueError(f"floating-point JSON value forbidden in {label}: {value}")
    payload = json.loads(text, object_pairs_hook=pairs_hook, parse_float=reject_float, parse_constant=reject_float)
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object")
    return payload

def _require_public_bindings() -> None:
    actual = (EXTERNAL_SEAL_COMMIT, EXTERNAL_SEAL_GIT_BLOB_SHA, ISSUANCE_CONTRACT_COMMIT, ISSUANCE_CONTRACT_GIT_BLOB_SHA, ISSUANCE_CONTRACT_GIT_BLOB_BYTE_LENGTH, ISSUANCE_CONTRACT_RAW_SHA256)
    if actual != _APPROVED_BINDINGS:
        raise ValueError("public binding mismatch")

def _deep_freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _deep_freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze_json(item) for item in value)
    return value

def load_runtime_qualification_operational_activation_issuance_contract_external_seal(seal_path: Optional[Path] = None, contract_path: Optional[Path] = None) -> Mapping[str, Any]:
    """Verify exact reviewed bytes and return an immutable seal mapping."""
    _require_public_bindings()
    root = _repo_root()
    resolved_seal = seal_path or root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract_external_seal.json"
    seal_raw = resolved_seal.resolve(strict=True).read_bytes()
    if _git_blob_sha(seal_raw) != EXTERNAL_SEAL_GIT_BLOB_SHA:
        raise ValueError("issuance contract external seal Git blob mismatch")
    seal = _strict_json(seal_raw, "issuance contract external seal")
    expected = {
        "seal_schema_identity": "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ISSUANCE_CONTRACT_EXTERNAL_SEAL_V1",
        "seal_schema_version": 1,
        "status": "DECLARATIVE_DORMANT_EXTERNAL_CONTRACT_SEAL_NO_ISSUER_NO_ACTIVATION_NO_EXECUTION",
        "issuance_contract_commit": ISSUANCE_CONTRACT_COMMIT,
        "issuance_contract_git_blob_sha": ISSUANCE_CONTRACT_GIT_BLOB_SHA,
        "issuance_contract_git_blob_byte_length": ISSUANCE_CONTRACT_GIT_BLOB_BYTE_LENGTH,
        "issuance_contract_raw_sha256": ISSUANCE_CONTRACT_RAW_SHA256,
        "raw_sha256_definition": "lowercase_hex(SHA256(exact bytes of the bound Git blob 05ec1c26edbd36cdf6d127f7e8361596f9a20958))",
        "seal_contains_own_raw_sha256": False,
        "issuance_contract_contains_own_raw_sha256": False,
        "current_state": _EXPECTED_STATE,
        "creation_authorized_now": False,
        "next_action": "External review of this declarative seal only",
    }
    if type(seal.get("seal_schema_version")) is not int or seal != expected:
        raise ValueError("issuance contract external seal content mismatch")
    resolved_contract = contract_path or root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract.json"
    checkout_raw = resolved_contract.resolve(strict=True).read_bytes()
    canonical = _git_text_bytes(checkout_raw)
    if _git_blob_sha(checkout_raw) != ISSUANCE_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("issuance contract Git blob mismatch")
    if len(canonical) != ISSUANCE_CONTRACT_GIT_BLOB_BYTE_LENGTH:
        raise ValueError("issuance contract Git blob byte length mismatch")
    if hashlib.sha256(canonical).hexdigest() != ISSUANCE_CONTRACT_RAW_SHA256:
        raise ValueError("issuance contract raw SHA256 mismatch")
    contract = _strict_json(canonical, "issuance contract")
    if contract.get("schema_identity") != "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ISSUANCE_CONTRACT_V1" or type(contract.get("schema_version")) is not int:
        raise ValueError("issuance contract schema mismatch")
    if contract.get("creation_authorized_now") is not False:
        raise ValueError("issuance contract is not dormant")
    return _deep_freeze_json(seal)

__all__ = ["EXTERNAL_SEAL_COMMIT", "EXTERNAL_SEAL_GIT_BLOB_SHA", "ISSUANCE_CONTRACT_COMMIT", "ISSUANCE_CONTRACT_GIT_BLOB_SHA", "ISSUANCE_CONTRACT_GIT_BLOB_BYTE_LENGTH", "ISSUANCE_CONTRACT_RAW_SHA256", "load_runtime_qualification_operational_activation_issuance_contract_external_seal"]
