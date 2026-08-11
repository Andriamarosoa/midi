"""Dormant loader for the H26 runtime one-shot orchestration seal."""
from __future__ import annotations
import hashlib, json
from pathlib import Path
from types import MappingProxyType
from typing import Mapping, Any

SEAL_GIT_BLOB_SHA="d298ab842ff385a2717fc38fa509cd2d2e8326ee"
CONTRACT_GIT_BLOB_SHA="a986570cea5b4dc31df40499f66f1cb6fbb8ab3c"
CONTRACT_LENGTH=2093
CONTRACT_RAW_SHA256="e1bd0060d6567c57ffac6e2b3b41d34eeb6790fb6dd85065f4f191bf4459afb2"

def _canonical(raw: bytes) -> bytes:
    if b"\r" in raw.replace(b"\r\n",b""): raise ValueError("non-CRLF carriage return")
    return raw.replace(b"\r\n",b"\n")

def _blob(raw: bytes) -> str:
    raw=_canonical(raw); return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()

def _parse(raw: bytes) -> dict[str,Any]:
    return json.loads(_canonical(raw).decode(),parse_float=lambda value:(_ for _ in ()).throw(ValueError("float forbidden")))

def load_runtime_one_shot_orchestration_contract_external_seal() -> Mapping[str,Any]:
    root=Path(__file__).resolve().parents[2]
    seal_raw=(root/"configs"/"harmonic_censoring_h26_runtime_one_shot_orchestration_dormant_contract_external_seal.json").read_bytes()
    if _blob(seal_raw)!=SEAL_GIT_BLOB_SHA: raise ValueError("orchestration seal blob mismatch")
    seal=_parse(seal_raw)
    expected={"seal_schema_identity":"H26_RUNTIME_ONE_SHOT_ORCHESTRATION_DORMANT_CONTRACT_EXTERNAL_SEAL_V1","seal_schema_version":1,"status":"DECLARATIVE_DORMANT_EXTERNAL_SEAL_NO_RUNTIME_INVOCATION","contract_commit":"697c77c8584816740039a9a5737617c647f0d32d","contract_git_blob_sha":CONTRACT_GIT_BLOB_SHA,"contract_git_blob_byte_length":CONTRACT_LENGTH,"contract_raw_sha256":CONTRACT_RAW_SHA256,"seal_contains_own_raw_sha256":False,"contract_contains_own_raw_sha256":False,"current_state":{"orchestration_contract_exists":True,"orchestrator_exists":False,"observer_invoked":False,"runtime_execution_authorized":False,"materialization_authorized":False,"scientific_execution_authorized":False,"locked_test_used":False},"creation_authorized_now":False}
    if seal!=expected: raise ValueError("orchestration seal content mismatch")
    raw=(root/"configs"/"harmonic_censoring_h26_runtime_one_shot_orchestration_dormant_contract.json").read_bytes(); canonical=_canonical(raw)
    if _blob(raw)!=CONTRACT_GIT_BLOB_SHA or len(canonical)!=CONTRACT_LENGTH or hashlib.sha256(canonical).hexdigest()!=CONTRACT_RAW_SHA256: raise ValueError("orchestration contract binding mismatch")
    contract=_parse(canonical)
    if contract.get("implementation_boundary",{}).get("real_observer_invocation_authorized") is not False or contract.get("creation_authorized_now") is not False: raise ValueError("orchestration contract not dormant")
    return MappingProxyType(seal)

__all__=["load_runtime_one_shot_orchestration_contract_external_seal"]
