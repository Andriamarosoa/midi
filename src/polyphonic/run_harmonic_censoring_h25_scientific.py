"""Dormant H25 scientific runner skeleton.

The numerical engine, exact 27-entry producer registry, phase gate, and
independent recomputer are wired here.  There is intentionally no public CLI
and no scientific authority/capability/claim implementation.  Consequently
the runner fails before NumPy import and before population access.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

from .harmonic_censoring_h25_recomputer import recompute_h25_persisted_evidence
from .harmonic_censoring_h25_scientific_engine import (
    H25DormantScientificPlan,
    H25_EXACT_EVIDENCE_PRODUCER_REGISTRY,
    load_h25_dormant_scientific_plan,
    require_h25_scientific_execution_authorized,
)


H25_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED = True
H25_PHASE_ORDER = ("P0", "P1", "P2")
H25_PHASE_FAILURE_STATUS = {
    "P0": "H25_SYNTHETIC_HYPOTHESIS_KILLED",
    "P1": "H25_IDENTIFIABILITY_NOT_DEMONSTRATED",
    "P2": "H25_PRETRAIN_READINESS_NOT_DEMONSTRATED",
}
H25_SUCCESS_STATUS = "H25_SYNTHETIC_PRETRAIN_EVIDENCE_PASSED"


@dataclass(frozen=True)
class H25DormantRunnerPlan:
    scientific_plan: H25DormantScientificPlan
    ordered_test_ids: tuple[str, ...]
    population_bindings: Mapping[str, str]
    phase_order: tuple[str, ...]


def load_h25_dormant_runner_plan(repository_root: Path) -> H25DormantRunnerPlan:
    plan = load_h25_dormant_scientific_plan(repository_root)
    if tuple(H25_EXACT_EVIDENCE_PRODUCER_REGISTRY) != plan.test_ids:
        raise ValueError("H25 producer registry differs from the sealed 27-test order.")
    if any(not callable(value) for value in H25_EXACT_EVIDENCE_PRODUCER_REGISTRY.values()):
        raise ValueError("H25 producer registry contains a non-callable.")
    if tuple(item.phase for item in plan.tests) != ("P0",) * 9 + ("P1",) * 9 + ("P2",) * 9:
        raise ValueError("H25 test phase order is not P0 then P1 then P2.")
    return H25DormantRunnerPlan(
        scientific_plan=plan,
        ordered_test_ids=plan.test_ids,
        population_bindings=plan.population_bindings,
        phase_order=H25_PHASE_ORDER,
    )


def recompute_phase_prefix(
    plan: H25DormantScientificPlan,
    persisted_evidence: Mapping[str, Mapping[str, object]],
) -> tuple[str, tuple[str, ...], tuple[str, ...]]:
    """Recompute a prefix and derive the exact kill-rule suffix.

    This helper is usable only with TEST-ONLY evidence until a future reviewed
    authority activates the real runner.
    """

    executed: list[str] = []
    not_run: list[str] = []
    status = H25_SUCCESS_STATUS
    killed = False
    for test in plan.tests:
        if killed:
            not_run.append(test.test_id)
            continue
        if test.test_id not in persisted_evidence:
            raise ValueError("H25 evidence prefix omits a test before its kill boundary.")
        outcome = recompute_h25_persisted_evidence(plan, test.test_id, persisted_evidence[test.test_id])
        executed.append(test.test_id)
        if not outcome.final_pass:
            status = H25_PHASE_FAILURE_STATUS[test.phase]
            killed = True
    return status, tuple(executed), tuple(not_run)


def run_h25_scientific_execution(repository_root: Path, authority: object = None) -> None:
    """Dormant boundary: always fails before NumPy or population access."""

    load_h25_dormant_runner_plan(repository_root)
    require_h25_scientific_execution_authorized(authority)
    raise AssertionError("unreachable H25 dormant runner boundary")


__all__ = [
    "H25_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED",
    "H25DormantRunnerPlan",
    "load_h25_dormant_runner_plan",
    "recompute_phase_prefix",
    "run_h25_scientific_execution",
]
