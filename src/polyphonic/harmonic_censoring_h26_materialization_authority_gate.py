"""Dormant H26 materialization authority gate."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Mapping, Optional
from .harmonic_censoring_h26_materialization_operationalization_contract_seal import load_materialization_operationalization_contract_external_seal
from .harmonic_censoring_h26_materialization_runtime_execution_proof import validate_artificial_materialization_runtime_execution_proof
from .harmonic_censoring_h26_materialization_authority_artifact import validate_artificial_materialization_authority_artifact

@dataclass(frozen=True)
class H26DormantMaterializationPlan:
    authority_id: str
    authority_raw_sha256: str
    destination: str
    runtime_terminal_status: str

def plan_h26_materialization(*, materialization_authority: Mapping[str,Any], runtime_authority: Mapping[str,Any], runtime_claim: Mapping[str,Any], runtime_evidence: Mapping[str,Any], runtime_receipt: Mapping[str,Any], runtime_authority_raw_sha256: str, runtime_claim_raw_sha256: str, runtime_evidence_raw_sha256: str, runtime_receipt_raw_sha256: str, runtime_record: Optional[Any]) -> H26DormantMaterializationPlan:
    load_materialization_operationalization_contract_external_seal()
    proof=validate_artificial_materialization_runtime_execution_proof(runtime_authority,runtime_claim,runtime_evidence,runtime_receipt,runtime_authority_raw_sha256,runtime_claim_raw_sha256,runtime_evidence_raw_sha256,runtime_receipt_raw_sha256,runtime_record)
    validated=validate_artificial_materialization_authority_artifact(materialization_authority,runtime_authority=runtime_authority,runtime_claim=runtime_claim,runtime_evidence=runtime_evidence,runtime_receipt=runtime_receipt,runtime_authority_raw_sha256=runtime_authority_raw_sha256,runtime_claim_raw_sha256=runtime_claim_raw_sha256,runtime_evidence_raw_sha256=runtime_evidence_raw_sha256,runtime_receipt_raw_sha256=runtime_receipt_raw_sha256,runtime_record=runtime_record)
    return H26DormantMaterializationPlan(validated.authority_id,validated.raw_sha256,str(materialization_authority["absolute_destination"]),proof.runtime_execution_terminal_status)

__all__=["H26DormantMaterializationPlan","plan_h26_materialization"]
