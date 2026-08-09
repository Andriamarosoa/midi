"""Fail-closed shell for the future independent V2 validation runner.

This module deliberately cannot execute the scientific job in its current
state.  A separately reviewed, identity-attested one-job capability is absent
by design.  Importing or calling ``main`` therefore performs only sealed
contract validation and fails before any manifest, asset, model, TensorFlow,
inference, or metric access.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import math
from pathlib import Path
from typing import Mapping, Sequence
import weakref

from .causal_candidate_v2_independent_validation_execution_contract import (
    IndependentV2ExecutionContract,
    INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256,
    load_sealed_independent_v2_execution_contract,
    require_sealed_independent_v2_execution_contract,
)


_ONE_JOB_CAPABILITIES: dict[int, weakref.ReferenceType[object]] = {}

REPORT_VIEWS = ("reference", "candidate", "delta_candidate_minus_reference")
REPORT_GRANULARITIES = ("global", "per_dataset", "per_recording", "per_independent_leakage_group")
REPORT_DATASETS = ("gaps_poly_mix", "guitar_techs_poly_directinput", "guitar_techs_poly_micamp")
REPORT_METRICS = (
    "estimated_noteons", "matched_onset_noteons", "onset_false_positives", "onset_misses",
    "onset_precision", "onset_recall", "onset_f1", "causal_false_noteons",
    "causal_false_noteons_per_minute", "causal_recall_within_250ms", "causal_latency_p50_ms",
    "causal_latency_p90_ms", "retriggers", "excess_fragments", "midi_40_51",
    "gate_eligible_count", "gate_rejected_count",
)
REPORT_PROVENANCE = (
    "git_commit", "worker_device", "execution_contract_sha256",
    "closed_independent_protocol_sha256", "asset_evidence_sha256",
    "asset_evidence_builder_protocol_sha256", "manifest_sha256",
    "historical_selection_sha256", "all_frozen_artifact_sha256",
    "all_thirty_recording_identities_and_twenty_leakage_groups",
    "candidate_gate_placement", "locked_test_used",
)
FROZEN_ARTIFACT_NAMES = (
    "transcription_checkpoint_sha256", "model_sha256", "standardizer_sha256",
    "audio_evidence_config_sha256", "evaluation_config_sha256", "reference_decoder_config_sha256",
)


class OneShotPhase(str, Enum):
    PRE_SCIENCE = "PRE_SCIENCE"
    SCIENTIFIC_ASSET_OPENED = "SCIENTIFIC_ASSET_OPENED"
    INFERENCE_STARTED = "INFERENCE_STARTED"
    AB_METRIC_PRODUCED = "AB_METRIC_PRODUCED"
    COHORT_CONSUMED = "COHORT_CONSUMED"
    REPORT_WRITTEN = "REPORT_WRITTEN"


@dataclass
class OneShotStateMachine:
    phase: OneShotPhase = OneShotPhase.PRE_SCIENCE
    cohort_consumed: bool = False

    def advance(self, phase: OneShotPhase) -> None:
        order = list(OneShotPhase)
        if self.cohort_consumed and phase in {OneShotPhase.PRE_SCIENCE, OneShotPhase.SCIENTIFIC_ASSET_OPENED}:
            raise RuntimeError("consumed cohort cannot return to pre-science")
        if order.index(phase) < order.index(self.phase):
            raise RuntimeError("one-shot state cannot move backwards")
        if order.index(phase) - order.index(self.phase) > 1:
            raise RuntimeError("one-shot state cannot skip phases")
        if phase == OneShotPhase.COHORT_CONSUMED:
            self.cohort_consumed = True
        if phase == OneShotPhase.AB_METRIC_PRODUCED:
            self.cohort_consumed = True
        self.phase = phase


def validate_runtime_preflight(
    contract: IndependentV2ExecutionContract,
    capability: object,
    *,
    repository_root: Path,
    git_commit: str,
    device: str,
    timeout_seconds: int,
    destination_exists: bool,
    heavy_job_active: bool,
    worktree_clean: bool,
) -> None:
    """Pure phase-0 checks; does not execute Git, workers, or scientific code."""
    cap = require_sealed_one_job_capability(capability)
    if cap.runner_commit != git_commit:
        raise ValueError("runner commit does not match one-job capability")
    if cap.execution_contract_sha256 != contract.contract_sha256:
        raise ValueError("execution contract SHA does not match capability")
    if cap.device != "cpu" or device != "cpu":
        raise ValueError("independent V2 runner requires CPU")
    if cap.wall_timeout_seconds != 900 or timeout_seconds != 900:
        raise ValueError("independent V2 timeout must be 900 seconds")
    if destination_exists or heavy_job_active or not worktree_clean:
        raise RuntimeError("runtime preflight failed closed")
    if contract.candidate_gate_placement != "post_ranking_pre_noteon":
        raise ValueError("candidate gate placement is not frozen")
    if repository_root is None:
        raise ValueError("repository root is required")


def validate_frozen_artifact_hashes(artifacts: Mapping[str, bytes]) -> None:
    for name in FROZEN_ARTIFACT_NAMES:
        if name not in artifacts:
            raise ValueError(f"missing frozen artifact: {name}")
        expected = INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256[name]
        if hashlib.sha256(artifacts[name]).hexdigest() != expected:
            raise ValueError(f"frozen artifact SHA mismatch: {name}")


def validate_future_report(report: Mapping[str, object]) -> None:
    """Validate the complete future report schema without opening any data."""
    if tuple(report.get("views", ())) != REPORT_VIEWS:
        raise ValueError("future report views are incomplete")
    if tuple(report.get("granularity", ())) != REPORT_GRANULARITIES:
        raise ValueError("future report granularity is incomplete")
    datasets = tuple(report.get("datasets", ()))
    if "guitarset_poly_mix" in datasets:
        raise ValueError("GuitarSet is forbidden in independent report")
    if datasets != REPORT_DATASETS:
        raise ValueError("future report datasets are incomplete")
    if report.get("recording_count") != 30 or report.get("independent_group_count") != 20:
        raise ValueError("future report cohort cardinality is invalid")
    metrics = report.get("metrics")
    if tuple(metrics or ()) != REPORT_METRICS:
        raise ValueError("future report metrics are incomplete")
    provenance = report.get("provenance")
    if tuple(provenance or ()) != REPORT_PROVENANCE:
        raise ValueError("future report provenance is incomplete")
    if report.get("locked_test_used") is not False:
        raise ValueError("locked test must remain unused")
    values = report.get("numeric_values")
    if not isinstance(values, Mapping) or set(values) != set(REPORT_METRICS) or any(
        isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value))
        for value in values.values()
    ):
        raise ValueError("future report contains missing or non-finite metrics")
    recordings = report.get("recording_identities")
    groups = report.get("independent_leakage_groups")
    if not isinstance(recordings, Sequence) or isinstance(recordings, (str, bytes)) or len(recordings) != 30 or len(set(recordings)) != 30:
        raise ValueError("future report recording identities are incomplete")
    if not isinstance(groups, Sequence) or isinstance(groups, (str, bytes)) or len(groups) != 20 or len(set(groups)) != 20:
        raise ValueError("future report leakage groups are incomplete")


def classify_failure(state: OneShotStateMachine) -> str:
    return "premetric_infrastructure_failure" if state.phase == OneShotPhase.PRE_SCIENCE and not state.cohort_consumed else "scientific_or_metric_failure"


def evaluate_future_report_decision(
    reference: Mapping[str, object], candidate: Mapping[str, object], rules: Mapping[str, object]
) -> dict[str, object]:
    from .run_causal_candidate_v2_independent_validation import evaluate_independent_v2_decision
    return evaluate_independent_v2_decision(reference=reference, candidate=candidate, rules=rules)


def phase_order() -> tuple[str, ...]:
    return (
        "authorization", "contract", "runtime", "cohort", "evidence",
        "asset_hashes", "artifact_hashes", "lazy_science", "open", "inference",
        "ab", "metrics", "report",
    )


@dataclass(frozen=True)
class IndependentV2ExecutionHooks:
    """Pure orchestration callbacks; scientific loading remains unreachable."""

    authorization: object
    contract: object
    runtime: object
    cohort: object
    evidence: object
    asset_hashes: object
    artifact_hashes: object
    lazy_science: object
    open: object
    inference: object
    ab: object
    metrics: object
    report: object


def run_phase_sequence(hooks: IndependentV2ExecutionHooks) -> tuple[str, ...]:
    """Invoke the sealed phase order and return observed callbacks.

    This is a testable orchestration seam.  Production scientific callbacks are
    intentionally absent until a separately reviewed capability factory exists.
    """
    observed: list[str] = []
    for name in phase_order():
        callback = getattr(hooks, name)
        if not callable(callback):
            raise TypeError(f"phase callback is not callable: {name}")
        callback()
        observed.append(name)
    return tuple(observed)


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
    destination: str
    stop_after_report: bool
    locked_test_used: bool
    single_execution_authorization: bool

    def __post_init__(self) -> None:
        if not isinstance(self.runner_commit, str) or len(self.runner_commit) != 40 or any(c not in "0123456789abcdef" for c in self.runner_commit):
            raise ValueError("runner_commit must be a lowercase 40-character SHA")
        if not isinstance(self.execution_contract_sha256, str) or len(self.execution_contract_sha256) != 64 or any(c not in "0123456789abcdef" for c in self.execution_contract_sha256):
            raise ValueError("execution_contract_sha256 must be a lowercase SHA-256")
        if self.device != "cpu" or self.wall_timeout_seconds != 900:
            raise ValueError("one-job capability must be CPU with a 900 second timeout")
        if not isinstance(self.job_id, str) or not self.job_id.strip() or not isinstance(self.destination, str) or not self.destination.strip():
            raise ValueError("job identity and destination are required")
        if self.stop_after_report is not True or self.locked_test_used is not False or self.single_execution_authorization is not True:
            raise ValueError("one-job capability flags are not sealed")


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

    require_sealed_one_job_capability(capability)
    contract = _require_execution_contract(repository_root)
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
    "OneShotPhase",
    "OneShotStateMachine",
    "REPORT_DATASETS",
    "REPORT_GRANULARITIES",
    "REPORT_METRICS",
    "REPORT_PROVENANCE",
    "REPORT_VIEWS",
    "evaluate_future_report_decision",
    "classify_failure",
    "phase_order",
    "IndependentV2ExecutionHooks",
    "run_phase_sequence",
    "validate_frozen_artifact_hashes",
    "validate_future_report",
    "validate_runtime_preflight",
    "main",
    "require_sealed_one_job_capability",
    "run_authorized_independent_v2",
]
