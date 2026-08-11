"""Dormant dependency-injected H26 runtime one-shot orchestrator."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Mapping, Optional

from . import harmonic_censoring_h26_runtime_execution_primitives as primitives
from .harmonic_censoring_h26_runtime_one_shot_orchestration_contract_seal import (
    load_runtime_one_shot_orchestration_contract_external_seal,
)
from .harmonic_censoring_h26_runtime_qualification_operational_activation import (
    validate_artificial_runtime_qualification_operational_activation,
)

ObserverEntryEvidenceFactory = Callable[[], tuple[Mapping[str, Any], str]]
ObserverBoundary = Callable[[Callable[[], None]], None]


@dataclass(frozen=True)
class H26DormantRuntimeOrchestrationTrace:
    steps: tuple[str, ...]
    observer_invocations: int
    terminal: bool


def orchestrate_h26_runtime_with_injected_observer(
    *,
    activation: Mapping[str, Any],
    authority: Mapping[str, Any],
    claim: Mapping[str, Any],
    receipt: Mapping[str, Any],
    authority_raw_sha256: str,
    claim_raw_sha256: str,
    preflight: Callable[[], None],
    enter_observer_boundary: ObserverBoundary,
    observer_entry_evidence_factory: ObserverEntryEvidenceFactory,
    observer: Callable[[], Optional[Any]],
) -> H26DormantRuntimeOrchestrationTrace:
    """Exercise the corrected order using fake, injected callables only."""
    load_runtime_one_shot_orchestration_contract_external_seal()
    steps: list[str] = []
    validate_artificial_runtime_qualification_operational_activation(activation)
    steps.append("validate_activation")
    preflight()
    steps.append("preflight")
    primitives.validate_artificial_authority(authority)
    steps.append("validate_authority")
    primitives.validate_artificial_claim(authority, claim, authority_raw_sha256)
    steps.append("validate_claim")

    boundary_invocations = 0
    observer_invocations = 0
    evidence: Optional[Mapping[str, Any]] = None
    evidence_raw_sha256: Optional[str] = None
    runtime_record: Optional[Any] = None

    def execute_inside_observer_boundary() -> None:
        nonlocal boundary_invocations, observer_invocations
        nonlocal evidence, evidence_raw_sha256, runtime_record
        boundary_invocations += 1
        if boundary_invocations != 1:
            raise ValueError("observer boundary callback must execute exactly once")
        steps.append("enter_observer_boundary")

        created_evidence, created_evidence_raw_sha256 = (
            observer_entry_evidence_factory()
        )
        evidence = created_evidence
        evidence_raw_sha256 = created_evidence_raw_sha256
        steps.append("create_observer_entry_evidence_inside_boundary")
        primitives.validate_artificial_observer_entry_evidence(
            authority,
            claim,
            evidence,
            authority_raw_sha256,
            claim_raw_sha256,
        )
        steps.append("validate_observer_entry_evidence")

        observer_invocations += 1
        if observer_invocations != 1:
            raise ValueError("observer must execute exactly once")
        runtime_record = observer()
        steps.append("invoke_observer_exactly_once")
        steps.append("capture_optional_runtime_record")

    enter_observer_boundary(execute_inside_observer_boundary)
    if boundary_invocations != 1:
        raise ValueError("observer boundary must enter exactly once")
    if observer_invocations != 1 or evidence is None or evidence_raw_sha256 is None:
        raise ValueError("observer boundary did not complete its sole attempt")

    primitives.validate_artificial_terminal_execution_receipt(
        authority,
        claim,
        evidence,
        receipt,
        authority_raw_sha256,
        claim_raw_sha256,
        evidence_raw_sha256,
        runtime_record,
    )
    steps.append("validate_terminal_receipt")
    return H26DormantRuntimeOrchestrationTrace(
        steps=tuple(steps),
        observer_invocations=observer_invocations,
        terminal=True,
    )


__all__ = [
    "H26DormantRuntimeOrchestrationTrace",
    "ObserverBoundary",
    "ObserverEntryEvidenceFactory",
    "orchestrate_h26_runtime_with_injected_observer",
]
