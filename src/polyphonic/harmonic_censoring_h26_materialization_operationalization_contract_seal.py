"""Dormant loader for the H26 materialization operationalization seal."""
from __future__ import annotations
import hashlib,json
from pathlib import Path
from types import MappingProxyType

SEAL_BLOB="aca5a562f7d581834ec04c1e98c57138e285cf32"
CONTRACT_BLOB="2d32b58cf5c7e2b34fd4d23ad02a4985e92f54cf"
CONTRACT_LENGTH=1857
CONTRACT_SHA256="69cceacd2b53ecf94115b6d0968e2bef02923c38da65596a3e277995e28f91f0"
def _canonical(raw):
    if b"\r" in raw.replace(b"\r\n",b""): raise ValueError("non-CRLF carriage return")
    return raw.replace(b"\r\n",b"\n")
def _blob(raw):
    raw=_canonical(raw); return hashlib.sha1(f"blob {len(raw)}\0".encode()+raw).hexdigest()
def load_materialization_operationalization_contract_external_seal():
    root=Path(__file__).resolve().parents[2]
    raw=(root/"configs"/"harmonic_censoring_h26_materialization_operationalization_dormant_contract_external_seal.json").read_bytes()
    if _blob(raw)!=SEAL_BLOB: raise ValueError("materialization seal blob mismatch")
    seal=json.loads(_canonical(raw))
    if seal.get("seal_schema_identity")!="H26_MATERIALIZATION_OPERATIONALIZATION_DORMANT_CONTRACT_EXTERNAL_SEAL_V1" or seal.get("creation_authorized_now") is not False or seal.get("current_state",{}).get("materializer_invoked") is not False: raise ValueError("materialization seal content mismatch")
    contract_raw=(root/"configs"/"harmonic_censoring_h26_materialization_operationalization_dormant_contract.json").read_bytes(); canonical=_canonical(contract_raw)
    if _blob(contract_raw)!=CONTRACT_BLOB or len(canonical)!=CONTRACT_LENGTH or hashlib.sha256(canonical).hexdigest()!=CONTRACT_SHA256: raise ValueError("materialization contract binding mismatch")
    contract=json.loads(canonical)
    if contract.get("implementation_boundary",{}).get("real_materializer_invocation_authorized") is not False: raise ValueError("materialization contract not dormant")
    return MappingProxyType(seal)
__all__=["load_materialization_operationalization_contract_external_seal"]
