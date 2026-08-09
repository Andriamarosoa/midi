"""Fail-closed shell for the future independent V2 validation runner.

This module deliberately cannot execute the scientific job in its current
state.  A separately reviewed, identity-attested one-job capability is absent
by design.  Importing or calling ``main`` therefore performs only sealed
contract validation and fails before any manifest, asset, model, TensorFlow,
inference, or metric access.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import weakref

from .causal_candidate_v2_independent_validation_execution_contract import (
    IndependentV2ExecutionContract,
    load_sealed_independent_v2_execution_contract,
    require_sealed_independent_v2_execution_contract,
)


_ONE_JOB_CAPABILITIES: dict[int, weakref.ReferenceType[object]] = {}


@dataclass(frozen=True)
class IndependentV2OneJobCapability:
    """Placeholder for a future factory-attested execution authorization.

    No factory is provided in this commit.  Constructing this dataclass by
    hand is intentionally insufficient for authorization.
    """

    runner_commit: str
    execution_contract_sha256: str
    device: str
    wall_timeout_seconds: int
    job_id: str


def require_sealed_one_job_capability(value: object) -> IndependentV2OneJobCapability:
    if not isinstance(value, IndependentV2OneJobCapability):
        raise ValueError("one-job capability has an invalid type.")
    reference = _ONE_JOB_CAPABILITIES.get(id(value))
    if reference is None or reference() is not value:
        raise RuntimeError(
            "Fail closed: independent V2 one-job capability is not authorized."
        )
    return value


def _require_execution_contract(repository_root: Path) -> IndependentV2ExecutionContract:
    contract = load_sealed_independent_v2_execution_contract(repository_root)
    return require_sealed_independent_v2_execution_contract(contract)


def run_authorized_independent_v2(
    repository_root: Path,
    capability: object,
) -> None:
    """Guard the future scientific path; the capability factory is absent."""

    contract = _require_execution_contract(repository_root)
    require_sealed_one_job_capability(capability)
    if contract is None:  # pragma: no cover - defensive unreachable branch
        raise RuntimeError("Fail closed: missing execution contract.")
    raise RuntimeError(
        "Independent V2 execution is not enabled in this contract-only commit."
    )


def main(argv: list[str] | None = None) -> int:
    """Reject every invocation before any scientific access can occur."""

    del argv
    repository_root = Path(__file__).resolve().parents[2]
    _require_execution_contract(repository_root)
    raise RuntimeError(
        "Independent V2 runner is not authorized: no one-job capability exists."
    )


__all__ = [
    "IndependentV2OneJobCapability",
    "main",
    "require_sealed_one_job_capability",
    "run_authorized_independent_v2",
]
