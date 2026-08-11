"""Dormant loader for the H26 issuer-implementation contract seal."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Optional

SEAL_COMMIT = "18702717b2ec0b78cef3326d6c7dffdffc6d1f76"
SEAL_GIT_BLOB_SHA = "fee203e4a719ff1477229befea279482a7e5cd9e"
CONTRACT_COMMIT = "e56776f65339b55c2fd4bd6900d4e5de38c422d4"
CONTRACT_GIT_BLOB_SHA = "25f9427d9bbd456924438baf14467fb856f7ec72"
CONTRACT_LENGTH = 2720
CONTRACT_RAW_SHA256 = "44ecdda5be6309443d7446f7a0a0bb5f5ea4cc37090a2ae4d0fba2d79e7eab4d"

def _canonical(raw: bytes) -> bytes:
    if b"\r" in raw.replace(b"\r\n", b""):
        raise ValueError("non-CRLF carriage return")
    return raw.replace(b"\r\n", b"\n")

def _blob(raw: bytes) -> str:
    raw = _canonical(raw)
    return hashlib.sha1(f"blob {len(raw)}\0".encode() + raw).hexdigest()

def _json(raw: bytes) -> dict[str, Any]:
    def hook(pairs):
        out = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("duplicate JSON key")
            out[key] = value
        return out
    return json.loads(_canonical(raw).decode("utf-8"), object_pairs_hook=hook, parse_float=lambda value: (_ for _ in ()).throw(ValueError("float forbidden")))

def load_issuer_implementation_contract_external_seal(seal_path: Optional[Path] = None, contract_path: Optional[Path] = None) -> Mapping[str, Any]:
    root = Path(__file__).resolve().parents[2]
    seal_file = seal_path or root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuer_dormant_implementation_contract_external_seal.json"
    seal_raw = seal_file.resolve(strict=True).read_bytes()
    if _blob(seal_raw) != SEAL_GIT_BLOB_SHA:
        raise ValueError("issuer implementation seal blob mismatch")
    seal = _json(seal_raw)
    if seal != {
        "seal_schema_identity": "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ISSUER_DORMANT_IMPLEMENTATION_CONTRACT_EXTERNAL_SEAL_V1",
        "seal_schema_version": 1,
        "status": "DECLARATIVE_DORMANT_IMPLEMENTATION_CONTRACT_SEAL_NO_INVOCATION_NO_OPERATIONAL_FILESYSTEM",
        "implementation_contract_commit": CONTRACT_COMMIT,
        "implementation_contract_git_blob_sha": CONTRACT_GIT_BLOB_SHA,
        "implementation_contract_git_blob_byte_length": CONTRACT_LENGTH,
        "implementation_contract_raw_sha256": CONTRACT_RAW_SHA256,
        "seal_contains_own_raw_sha256": False,
        "implementation_contract_contains_own_raw_sha256": False,
        "current_state": {"implementation_contract_exists": True, "planner_exists": False, "issuer_exists": False, "issuer_invoked": False, "activation_exists": False, "administrative_root": None, "operational_filesystem_touched": False, "runtime_execution_authorized": False, "materialization_authorized": False, "scientific_execution_authorized": False, "locked_test_used": False},
        "creation_authorized_now": False,
        "next_action": "Implement a dormant loader for this external seal",
    }:
        raise ValueError("issuer implementation seal content mismatch")
    contract_file = contract_path or root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuer_dormant_implementation_contract.json"
    raw = contract_file.resolve(strict=True).read_bytes(); canonical = _canonical(raw)
    if _blob(raw) != CONTRACT_GIT_BLOB_SHA or len(canonical) != CONTRACT_LENGTH or hashlib.sha256(canonical).hexdigest() != CONTRACT_RAW_SHA256:
        raise ValueError("issuer implementation contract binding mismatch")
    contract = _json(canonical)
    if contract.get("schema_identity") != "H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ISSUER_DORMANT_IMPLEMENTATION_CONTRACT_V1" or contract.get("implementation_boundary", {}).get("issuer_invocation_authorized") is not False:
        raise ValueError("issuer implementation contract is not dormant")
    return MappingProxyType(seal)

__all__ = ["load_issuer_implementation_contract_external_seal"]
