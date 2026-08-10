"""Dormant administrative runner shell for H23 synthetic evaluation.

The scientific fixture synthesizer and P0/P1/P2 executor are intentionally
absent.  This module defines the sealed phase/outcome reconciliation that a
later implementation must use, but no public call can cross the one-shot claim
in the present commit.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import tempfile
from typing import Mapping, Sequence

from .harmonic_censoring_h23 import H23HarnessPlan, H23ResolvedTest
from .harmonic_censoring_h23_execution_capability import (
    AttestedH23SyntheticExecutionCapability,
    H23_CONSUMPTION_CLAIM_IMPLEMENTED,
    issue_h23_synthetic_execution_capability,
    require_attested_h23_synthetic_execution_capability,
    require_claimed_h23_synthetic_execution_capability,
)


PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED = False
H23_POSITIVE_STATUS = "AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL"
H23_P0_KILL_STATUS = "H23_SYNTHETIC_HYPOTHESIS_KILLED"
H23_READINESS_FAILURE_STATUS = "H23_PRETRAIN_READINESS_NOT_DEMONSTRATED"
H23_INCONCLUSIVE_STATUS = "H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED"
H23_NOT_RUN_STATUS = "NOT_RUN_BY_KILL_RULE"


class H23AdministrativePhase(str, Enum):
    ZERO_SCIENCE_PREFLIGHT = "zero_science_preflight"
    CAPABILITY_ISSUED = "capability_issued"
    CONSUMPTION_CLAIMED = "consumption_claimed"
    P0 = "P0"
    P1 = "P1"
    P2 = "P2"
    TERMINAL_OUTCOME_PUBLISHED = "terminal_outcome_published"


@dataclass(frozen=True)
class H23AdministrativeTestResult:
    test_id: str
    phase: str
    passed: bool
    evidence: Mapping[str, object]

    def __post_init__(self) -> None:
        if not isinstance(self.test_id, str) or not self.test_id:
            raise ValueError("H23 result test_id must be non-empty.")
        if self.phase not in {"P0", "P1", "P2"}:
            raise ValueError("H23 result phase must be P0, P1 or P2.")
        if type(self.passed) is not bool:
            raise ValueError("H23 result passed must be boolean.")
        json.dumps(self.evidence, allow_nan=False, sort_keys=True)


def _expected_prefix(
    plan: H23HarnessPlan, results: Sequence[H23AdministrativeTestResult]
) -> tuple[H23ResolvedTest, ...]:
    expected = plan.tests[: len(results)]
    for contract, result in zip(expected, results):
        if result.test_id != contract.test_id or result.phase != contract.phase:
            raise ValueError("H23 executed tests are not the exact preregistered prefix.")
    if len(results) > len(plan.tests):
        raise ValueError("H23 result count exceeds preregistered tests.")
    failed = [index for index, result in enumerate(results) if not result.passed]
    if len(failed) > 1 or (failed and failed[0] != len(results) - 1):
        raise ValueError("H23 execution must stop exactly at its first failed test.")
    return expected


def build_h23_scientific_terminal_record(
    plan: H23HarnessPlan,
    results: Sequence[H23AdministrativeTestResult],
) -> dict[str, object]:
    """Build a non-authoritative success/failure draft from an exact prefix."""

    _expected_prefix(plan, results)
    if not results:
        raise ValueError("H23 scientific terminal requires at least one result.")
    first_failure = next((item for item in results if not item.passed), None)
    if first_failure is None:
        if len(results) != len(plan.tests):
            raise ValueError("H23 success requires all 72 preregistered tests.")
        status = H23_POSITIVE_STATUS
        not_run: list[dict[str, object]] = []
    else:
        status = (
            H23_P0_KILL_STATUS
            if first_failure.phase == "P0"
            else H23_READINESS_FAILURE_STATUS
        )
        not_run = [
            {
                "test_id": item.test_id,
                "phase": item.phase,
                "status": H23_NOT_RUN_STATUS,
            }
            for item in plan.tests[len(results) :]
        ]
    return {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h23_terminal_scientific_draft",
        "authoritative": False,
        "proposed_global_go_status": status,
        "synthetic_population_consumed": False,
        "fixture_manifest_sha256": plan.fixture_manifest_sha256,
        "resolved_test_manifest_sha256": plan.resolved_test_manifest_sha256,
        "executed_results": [
            {
                "test_id": item.test_id,
                "phase": item.phase,
                "passed": item.passed,
                "evidence": dict(item.evidence),
            }
            for item in results
        ],
        "first_failed_test_id": None if first_failure is None else first_failure.test_id,
        "not_run_tests": not_run,
        "real_data_used": False,
        "H17_population_used": False,
        "locked_test_used": False,
        "fit_performed": False,
        "training_authorized": False,
    }


def build_h23_operational_terminal_record(
    plan: H23HarnessPlan,
    results: Sequence[H23AdministrativeTestResult],
    *,
    error_type: str,
    error_message: str,
) -> dict[str, object]:
    """Build an inconclusive record without converting an incident to science."""

    _expected_prefix(plan, results)
    if not error_type or not error_message:
        raise ValueError("H23 operational terminal requires explicit error evidence.")
    return {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h23_terminal_operational_draft",
        "authoritative": False,
        "proposed_global_go_status": H23_INCONCLUSIVE_STATUS,
        "scientific_verdict": None,
        "synthetic_population_consumed": False,
        "fixture_manifest_sha256": plan.fixture_manifest_sha256,
        "resolved_test_manifest_sha256": plan.resolved_test_manifest_sha256,
        "known_executed_test_ids": [item.test_id for item in results],
        "operational_error": {"type": error_type, "message": error_message},
        "real_data_used": False,
        "H17_population_used": False,
        "locked_test_used": False,
        "fit_performed": False,
        "training_authorized": False,
    }


def _publish_h23_terminal_record_atomically(
    destination: Path, payload: Mapping[str, object]
) -> Path:
    """Publish one administrative terminal directory by same-filesystem rename."""

    destination = Path(destination).resolve()
    if destination.exists():
        raise FileExistsError(f"H23 terminal destination already exists: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    try:
        raw = (
            json.dumps(
                payload,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
                indent=2,
            )
            + "\n"
        ).encode("utf-8")
        report = staging / "terminal_report.json"
        with report.open("xb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(staging, destination)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return destination / "terminal_report.json"


def finalize_and_publish_h23_terminal_record(
    plan: H23HarnessPlan,
    draft: Mapping[str, object],
    capability: object,
) -> Path:
    """Create authority only from a claimed capability and its real marker."""

    if (
        not PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED
        or not H23_CONSUMPTION_CLAIM_IMPLEMENTED
    ):
        raise PermissionError(
            "H23 terminal finalization is dormant until a separately reviewed "
            "scientific executor and claim boundary exist."
        )
    checked = require_claimed_h23_synthetic_execution_capability(capability)
    if (
        plan.contract_sha256 != checked.contract_sha256
        or plan.fixture_manifest_sha256 != checked.fixture_manifest_sha256
        or plan.resolved_test_manifest_sha256 != checked.resolved_test_manifest_sha256
    ):
        raise ValueError("H23 terminal plan differs from the claimed capability.")
    if not checked.authorization_marker.is_file():
        raise FileNotFoundError("H23 claimed consumption marker is missing.")
    marker_raw = checked.authorization_marker.read_bytes()
    marker_sha256 = hashlib.sha256(marker_raw).hexdigest()
    try:
        marker = json.loads(marker_raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("H23 consumption marker is not valid JSON.") from exc
    expected_marker = {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h23_synthetic_population_consumption",
        "synthetic_population_consumed": True,
        "authorization_seal_sha256": checked.authorization_seal_sha256,
        "implementation_commit": checked.implementation_commit,
        "fixture_manifest_sha256": checked.fixture_manifest_sha256,
        "resolved_test_manifest_sha256": checked.resolved_test_manifest_sha256,
        "approved_harness_git_blob": checked.approved_harness_git_blob,
    }
    if marker != expected_marker:
        raise ValueError("H23 consumption marker content does not match capability.")
    purpose = draft.get("purpose")
    if purpose not in {
        "harmonic_censoring_h23_terminal_scientific_draft",
        "harmonic_censoring_h23_terminal_operational_draft",
    }:
        raise ValueError("H23 terminal draft purpose is invalid.")
    if draft.get("authoritative") is not False:
        raise ValueError("H23 terminal input must be a non-authoritative draft.")
    if purpose == "harmonic_censoring_h23_terminal_scientific_draft":
        rows = draft.get("executed_results")
        if not isinstance(rows, list):
            raise ValueError("H23 scientific draft results must be an array.")
        reconstructed: list[H23AdministrativeTestResult] = []
        for row in rows:
            if not isinstance(row, Mapping) or set(row) != {
                "test_id",
                "phase",
                "passed",
                "evidence",
            }:
                raise ValueError("H23 scientific draft result schema mismatch.")
            evidence = row["evidence"]
            if not isinstance(evidence, Mapping):
                raise ValueError("H23 scientific draft evidence must be an object.")
            reconstructed.append(
                H23AdministrativeTestResult(
                    test_id=row["test_id"],  # type: ignore[arg-type]
                    phase=row["phase"],  # type: ignore[arg-type]
                    passed=row["passed"],  # type: ignore[arg-type]
                    evidence=evidence,
                )
            )
        expected_draft = build_h23_scientific_terminal_record(plan, reconstructed)
    else:
        known_ids = draft.get("known_executed_test_ids")
        error = draft.get("operational_error")
        if (
            not isinstance(known_ids, list)
            or any(not isinstance(item, str) for item in known_ids)
            or not isinstance(error, Mapping)
            or set(error) != {"type", "message"}
            or not isinstance(error["type"], str)
            or not isinstance(error["message"], str)
        ):
            raise ValueError("H23 operational draft schema mismatch.")
        reconstructed = [
            H23AdministrativeTestResult(
                test_id=item.test_id,
                phase=item.phase,
                passed=True,
                evidence={},
            )
            for item in plan.tests[: len(known_ids)]
        ]
        if known_ids != [item.test_id for item in reconstructed]:
            raise ValueError("H23 operational draft is not an exact test prefix.")
        expected_draft = build_h23_operational_terminal_record(
            plan,
            reconstructed,
            error_type=error["type"],
            error_message=error["message"],
        )
    if dict(draft) != expected_draft:
        raise ValueError("H23 terminal draft was mutated after construction.")
    proposed = draft.get("proposed_global_go_status")
    allowed = {
        H23_POSITIVE_STATUS,
        H23_P0_KILL_STATUS,
        H23_READINESS_FAILURE_STATUS,
        H23_INCONCLUSIVE_STATUS,
    }
    if proposed not in allowed:
        raise ValueError("H23 terminal draft proposed status is invalid.")
    if proposed == H23_POSITIVE_STATUS:
        if len(draft.get("executed_results", [])) != 72 or draft.get("not_run_tests") != []:
            raise ValueError("H23 positive finalization requires the complete 72-test draft.")
        destination = checked.success_destination
    else:
        destination = checked.terminal_record_destination
    final = dict(draft)
    final.pop("proposed_global_go_status")
    final["purpose"] = "harmonic_censoring_h23_terminal_authoritative_result"
    final["authoritative"] = True
    final["global_go_status"] = proposed
    final["synthetic_population_consumed"] = True
    final["consumption_marker_sha256"] = marker_sha256
    final["authorization_seal_sha256"] = checked.authorization_seal_sha256
    final["implementation_commit"] = checked.implementation_commit
    return _publish_h23_terminal_record_atomically(destination, final)


def run_authorized_h23_synthetic_execution(
    repository_root: Path,
    capability: object,
) -> Mapping[str, object]:
    """Remain dormant even for an attested object; do not claim or synthesize."""

    del repository_root
    require_attested_h23_synthetic_execution_capability(capability)
    if not PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED:
        raise PermissionError(
            "H23 runner is dormant: the production synthetic executor is absent; "
            "the capability has not been claimed and no waveform was synthesized."
        )
    raise AssertionError("unreachable until a separately reviewed executor exists")


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments:
        raise ValueError("H23 sealed runner accepts no CLI arguments.")
    repository = Path(__file__).resolve().parents[2]
    capability: AttestedH23SyntheticExecutionCapability = (
        issue_h23_synthetic_execution_capability(repository)
    )
    run_authorized_h23_synthetic_execution(repository, capability)
    return 0


__all__ = [
    "H23AdministrativePhase",
    "H23AdministrativeTestResult",
    "H23_INCONCLUSIVE_STATUS",
    "H23_NOT_RUN_STATUS",
    "H23_P0_KILL_STATUS",
    "H23_POSITIVE_STATUS",
    "H23_READINESS_FAILURE_STATUS",
    "PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED",
    "build_h23_operational_terminal_record",
    "build_h23_scientific_terminal_record",
    "finalize_and_publish_h23_terminal_record",
    "main",
    "run_authorized_h23_synthetic_execution",
]


if __name__ == "__main__":
    raise SystemExit(main())
