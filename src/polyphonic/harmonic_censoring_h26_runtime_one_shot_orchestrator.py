"""Dormant dependency-injected H26 runtime one-shot orchestrator."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from .harmonic_censoring_h26_runtime_one_shot_orchestration_contract_seal import load_runtime_one_shot_orchestration_contract_external_seal
from .harmonic_censoring_h26_runtime_qualification_operational_activation import validate_artificial_runtime_qualification_operational_activation
from . import harmonic_censoring_h26_runtime_execution_primitives as primitives

@dataclass(frozen=True)
class H26DormantRuntimeOrchestrationTrace:
    steps: tuple[str, ...]
    observer_invocations: int
    terminal: bool

def orchestrate_h26_runtime_with_injected_observer(
    *, activation: Mapping[str, Any], authority: Mapping[str, Any],
    claim: Mapping[str, Any], evidence: Mapping[str, Any], receipt: Mapping[str, Any],
    authority_raw_sha256: str, claim_raw_sha256: str,
    evidence_raw_sha256: str, preflight: Callable[[], None],
    observer: Callable[[], Optional[Any]],
) -> H26DormantRuntimeOrchestrationTrace:
    """Validate and exercise the one-shot order using only injected callables."""
    load_runtime_one_shot_orchestration_contract_external_seal()
    steps=[]
    validate_artificial_runtime_qualification_operational_activation(activation); steps.append("activation")
    preflight(); steps.append("preflight")
    primitives.validate_artificial_authority(authority); steps.append("authority")
    primitives.validate_artificial_claim(authority,claim,authority_raw_sha256); steps.append("claim")
    primitives.validate_artificial_observer_entry_evidence(authority,claim,evidence,authority_raw_sha256,claim_raw_sha256); steps.append("observer_entry_evidence")
    runtime_record=observer(); steps.append("observer")
    primitives.validate_artificial_terminal_execution_receipt(authority,claim,evidence,receipt,authority_raw_sha256,claim_raw_sha256,evidence_raw_sha256,runtime_record); steps.append("terminal_receipt")
    return H26DormantRuntimeOrchestrationTrace(tuple(steps),1,True)

__all__=["H26DormantRuntimeOrchestrationTrace","orchestrate_h26_runtime_with_injected_observer"]
