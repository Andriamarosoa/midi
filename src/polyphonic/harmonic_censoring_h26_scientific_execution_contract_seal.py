"""Dormant loader for the H26 scientific execution contract seal."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from types import MappingProxyType
from typing import Any

SEAL_BLOB="28d2906b02347b92511a758dfd4dcbd6e50382b6"; CONTRACT_BLOB="718a08fb3516d07c744d34f646b0715d0bc27516"; CONTRACT_LENGTH=2047; CONTRACT_SHA256="a9925212ee007d44f5ff3727397e59bef0be57451aa3010bebbeeca8a6040a4c"
def _canonical(raw):
    if b"\r" in raw.replace(b"\r\n",b""): raise ValueError("non-CRLF carriage return")
    return raw.replace(b"\r\n",b"\n")
def _blob(raw):
    raw=_canonical(raw); return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
def _deep_freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _deep_freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze_json(item) for item in value)
    return value
def load_scientific_execution_contract_external_seal():
    root=Path(__file__).resolve().parents[2]; raw=(root/"configs"/"harmonic_censoring_h26_scientific_execution_dormant_contract_external_seal.json").read_bytes()
    if _blob(raw)!=SEAL_BLOB: raise ValueError("scientific seal blob mismatch")
    seal=json.loads(_canonical(raw))
    if seal.get("seal_schema_identity")!="H26_SCIENTIFIC_EXECUTION_DORMANT_CONTRACT_EXTERNAL_SEAL_V1" or seal.get("creation_authorized_now") is not False or any(seal.get("current_state",{}).get(k) is not False for k in ("p0_executed","p1_executed","p2_executed","locked_test_used","scientific_execution_authorized")): raise ValueError("scientific seal content mismatch")
    contract_raw=(root/"configs"/"harmonic_censoring_h26_scientific_execution_dormant_contract.json").read_bytes(); canonical=_canonical(contract_raw)
    if _blob(contract_raw)!=CONTRACT_BLOB or len(canonical)!=CONTRACT_LENGTH or hashlib.sha256(canonical).hexdigest()!=CONTRACT_SHA256: raise ValueError("scientific contract binding mismatch")
    contract=json.loads(canonical); boundary=contract.get("implementation_boundary",{})
    if any(boundary.get(k) is not False for k in ("p0_authorized","p1_authorized","p2_authorized","locked_test_access_authorized","real_engine_import_or_invocation_authorized")): raise ValueError("scientific contract not dormant")
    return _deep_freeze_json(seal)
__all__=["load_scientific_execution_contract_external_seal"]
