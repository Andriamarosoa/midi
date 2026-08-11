"""Dormant loader for the H26 runtime activation contract external seal.

Only reviewed declarative bytes are read and verified. No operational path,
activation, issuer, capability, runtime object, or scientific artifact is made.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple


EXTERNAL_SEAL_COMMIT = "ce4aa59f75d3ff3836bce91c6be9739a16448199"
EXTERNAL_SEAL_GIT_BLOB_SHA = "685915e6e15a760fb439089752402ccb29c142f7"
ACTIVATION_CONTRACT_COMMIT = "d8d71bad9aee560d3406e672e7ebc6c2cf11dbff"
ACTIVATION_CONTRACT_GIT_BLOB_SHA = "c6eac6ae2d05b99a1a5b88594dea473739904dd8"
ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH = 16050
ACTIVATION_CONTRACT_RAW_SHA256 = "ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01"

_APPROVED_EXTERNAL_SEAL_COMMIT = "ce4aa59f75d3ff3836bce91c6be9739a16448199"
_APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA = "685915e6e15a760fb439089752402ccb29c142f7"
_APPROVED_ACTIVATION_CONTRACT_COMMIT = "d8d71bad9aee560d3406e672e7ebc6c2cf11dbff"
_APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_SHA = "c6eac6ae2d05b99a1a5b88594dea473739904dd8"
_APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH = 16050
_APPROVED_ACTIVATION_CONTRACT_RAW_SHA256 = "ad3fd1a381022a8f0e79af2a2656daf327d3ef857a86a0cb55a611cb41e83c01"

_EXPECTED_STATE = {
    "activation_exists": False,
    "issuer_exists": False,
    "capability_exists": False,
    "administrative_root": None,
    "runtime_authority_exists": False,
    "claim_exists": False,
    "observer_entry_evidence_exists": False,
    "observer_invoked": False,
    "observer_invocation_count": 0,
    "runtime_record_exists": False,
    "receipt_exists": False,
    "runtime_execution_authorized": False,
    "materialization_authorized": False,
    "scientific_execution_authorized": False,
    "locked_test_used": False,
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
    return hashlib.sha1(
        f"blob {len(canonical)}\0".encode("ascii") + canonical
    ).hexdigest()


def _strict_json(raw: bytes, label: str) -> dict[str, Any]:
    canonical = _git_text_bytes(raw)
    try:
        text = canonical.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} is not UTF-8") from exc
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

    try:
        payload = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid {label} JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be an object")
    return payload


def _require_public_bindings() -> None:
    bindings = (
        (EXTERNAL_SEAL_COMMIT, _APPROVED_EXTERNAL_SEAL_COMMIT, "seal commit"),
        (EXTERNAL_SEAL_GIT_BLOB_SHA, _APPROVED_EXTERNAL_SEAL_GIT_BLOB_SHA, "seal blob"),
        (ACTIVATION_CONTRACT_COMMIT, _APPROVED_ACTIVATION_CONTRACT_COMMIT, "contract commit"),
        (ACTIVATION_CONTRACT_GIT_BLOB_SHA, _APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_SHA, "contract blob"),
        (ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH, _APPROVED_ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH, "contract length"),
        (ACTIVATION_CONTRACT_RAW_SHA256, _APPROVED_ACTIVATION_CONTRACT_RAW_SHA256, "contract raw SHA256"),
    )
    for actual, expected, label in bindings:
        if actual != expected:
            raise ValueError(f"{label} binding mismatch")


def load_runtime_qualification_operational_activation_contract_external_seal(
    seal_path: Optional[Path] = None,
    contract_path: Optional[Path] = None,
) -> Mapping[str, Any]:
    """Validate the exact external seal and its exact corrected contract bytes."""
    _require_public_bindings()
    root = _repo_root()
    resolved_seal = seal_path or (
        root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_contract_external_seal.json"
    )
    seal_raw = resolved_seal.resolve(strict=True).read_bytes()
    if _git_blob_sha(seal_raw) != EXTERNAL_SEAL_GIT_BLOB_SHA:
        raise ValueError("activation contract external seal Git blob mismatch")
    seal = _strict_json(seal_raw, "activation contract external seal")
    if type(seal.get("seal_schema_version")) is not int:
        raise ValueError("activation contract external seal schema version type mismatch")
    seal_state = seal.get("current_state")
    if not isinstance(seal_state, dict) or type(
        seal_state.get("observer_invocation_count")
    ) is not int:
        raise ValueError("activation contract external seal current state type mismatch")
    expected_seal = {
        "seal_schema_identity": "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_CONTRACT_EXTERNAL_SEAL_V1",
        "seal_schema_version": 1,
        "status": "DECLARATIVE_DORMANT_EXTERNAL_CONTRACT_SEAL_NO_ACTIVATION_NO_EXECUTION",
        "activation_contract_commit": ACTIVATION_CONTRACT_COMMIT,
        "activation_contract_git_blob_sha": ACTIVATION_CONTRACT_GIT_BLOB_SHA,
        "activation_contract_git_blob_byte_length": ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH,
        "activation_contract_raw_sha256": ACTIVATION_CONTRACT_RAW_SHA256,
        "raw_sha256_definition": "lowercase_hex(SHA256(exact bytes of the bound Git blob c6eac6ae2d05b99a1a5b88594dea473739904dd8))",
        "seal_contains_own_raw_sha256": False,
        "activation_contract_contains_own_raw_sha256": False,
        "current_state": _EXPECTED_STATE,
        "creation_authorized_now": False,
        "next_action": "External review of this declarative external seal only; no activation validator issuer capability filesystem runtime or science is authorized",
    }
    if seal != expected_seal:
        raise ValueError("activation contract external seal content mismatch")

    resolved_contract = contract_path or (
        root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_contract.json"
    )
    checkout_raw = resolved_contract.resolve(strict=True).read_bytes()
    contract_raw = _git_text_bytes(checkout_raw)
    if _git_blob_sha(checkout_raw) != ACTIVATION_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("activation contract Git blob mismatch")
    if len(contract_raw) != ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH:
        raise ValueError("activation contract Git blob byte length mismatch")
    if hashlib.sha256(contract_raw).hexdigest() != ACTIVATION_CONTRACT_RAW_SHA256:
        raise ValueError("activation contract raw SHA256 mismatch")
    contract = _strict_json(contract_raw, "activation contract")
    if contract.get("schema_identity") != "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_CONTRACT_V1":
        raise ValueError("activation contract schema mismatch")
    if type(contract.get("schema_version")) is not int or contract.get("schema_version") != 1:
        raise ValueError("activation contract schema version mismatch")
    if contract.get("current_state", {}).get("runtime_execution_authorized") is not False:
        raise ValueError("activation contract is not dormant")
    return MappingProxyType(seal)


__all__ = [
    "ACTIVATION_CONTRACT_COMMIT",
    "ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH",
    "ACTIVATION_CONTRACT_GIT_BLOB_SHA",
    "ACTIVATION_CONTRACT_RAW_SHA256",
    "EXTERNAL_SEAL_COMMIT",
    "EXTERNAL_SEAL_GIT_BLOB_SHA",
    "load_runtime_qualification_operational_activation_contract_external_seal",
]
