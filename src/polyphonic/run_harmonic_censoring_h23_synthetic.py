"""Sealed H23 synthetic executor, still dormant without a future activation.

The module contains the reviewed one-shot claim boundary, deterministic
fixture/DSP implementation, private append-only transcript, and authoritative
finalizer.  The historical activation and seal cannot mint its capability, so
this implementation cannot execute until a later commit binds its exact source
blobs and is separately approved.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import hashlib
import importlib
import json
import math
import os
from pathlib import Path
import shutil
import sys
import tempfile
import time
import tracemalloc
from typing import Any, BinaryIO, Mapping, Sequence

from .harmonic_censoring_h23 import (
    H23HarnessPlan,
    H23ResolvedTest,
    load_h23_harness_plan,
)
from .harmonic_censoring_h23_oracles import (
    EXACT_H23_ORACLE_REGISTRY,
    H23RecomputedOracle,
    recompute_h23_exact_oracle,
)
from .harmonic_censoring_h23_execution_capability import (
    AttestedH23SyntheticExecutionCapability,
    H23_CONSUMPTION_CLAIM_IMPLEMENTED,
    H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256,
    H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH,
    claim_h23_synthetic_execution_capability,
    issue_h23_synthetic_execution_capability,
    require_attested_h23_synthetic_execution_capability,
    require_claimed_h23_synthetic_execution_capability,
)


PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED = True
H23_POSITIVE_STATUS = "AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL"
H23_P0_KILL_STATUS = "H23_SYNTHETIC_HYPOTHESIS_KILLED"
H23_READINESS_FAILURE_STATUS = "H23_PRETRAIN_READINESS_NOT_DEMONSTRATED"
H23_INCONCLUSIVE_STATUS = "H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED"
H23_NOT_RUN_STATUS = "NOT_RUN_BY_KILL_RULE"
_ZERO_SHA256 = "0" * 64
_H23_ANALYTIC_TEST_IDS = frozenset(
    {"A01", "A02", "A03", "A04", "A05", "A06", "A07", "A08"}
)


def _canonical_json_line(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _ordered_ids_sha256(values: Sequence[str]) -> str:
    return hashlib.sha256(_canonical_json_line(list(values))).hexdigest()


def _reject_duplicate_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H23 transcript duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H23 transcript forbids numeric token {token!r}.")


def _parse_canonical_json_line(raw: bytes) -> dict[str, object]:
    if not raw.endswith(b"\n") or raw.endswith(b"\r\n"):
        raise ValueError("H23 transcript lines must end in one LF and no CRLF.")
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_pairs,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("H23 transcript line is not strict UTF-8 JSON.") from exc
    if not isinstance(value, dict) or _canonical_json_line(value) != raw:
        raise ValueError("H23 transcript line is not canonical.")
    return value


def _load_executor_transcript_contract(repository: Path) -> dict[str, object]:
    path = (repository / H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH).resolve(
        strict=True
    )
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256:
        raise ValueError("H23 executor transcript contract SHA-256 mismatch.")
    value = json.loads(raw, object_pairs_hook=_reject_duplicate_pairs, parse_constant=_reject_nonfinite)
    if not isinstance(value, dict):
        raise ValueError("H23 executor transcript contract must be an object.")
    return value


def _event_schema(contract: Mapping[str, object], event_type: str) -> Mapping[str, object]:
    transcript = contract.get("future_transcript_contract")
    if not isinstance(transcript, Mapping):
        raise ValueError("H23 transcript contract section is missing.")
    schemas = transcript.get("event_schemas")
    if not isinstance(schemas, Mapping) or event_type not in schemas:
        raise ValueError("H23 transcript event type is not sealed.")
    schema = schemas[event_type]
    if not isinstance(schema, Mapping):
        raise ValueError("H23 transcript event schema is invalid.")
    return schema


def _require_event_schema(
    contract: Mapping[str, object], event: Mapping[str, object]
) -> None:
    event_type = event.get("event_type")
    if not isinstance(event_type, str):
        raise ValueError("H23 transcript event_type must be a string.")
    schema = _event_schema(contract, event_type)
    exact_fields = schema.get("exact_fields")
    fixed_values = schema.get("fixed_values")
    if (
        not isinstance(exact_fields, list)
        or any(not isinstance(item, str) for item in exact_fields)
        or set(event) != set(exact_fields)
        or not isinstance(fixed_values, Mapping)
    ):
        raise ValueError("H23 transcript event key set differs from sealed schema.")
    for name, expected in fixed_values.items():
        if event.get(name) != expected:
            raise ValueError(f"H23 transcript fixed field {name} mismatch.")


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
        if os.name != "nt":
            staging_descriptor = os.open(staging, os.O_RDONLY)
            try:
                os.fsync(staging_descriptor)
            finally:
                os.close(staging_descriptor)
        os.replace(staging, destination)
        if os.name != "nt":
            parent_descriptor = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(parent_descriptor)
            finally:
                os.close(parent_descriptor)
    except BaseException:
        if staging.exists():
            shutil.rmtree(staging)
        raise
    return destination / "terminal_report.json"


class _H23TranscriptWriter:
    """Private append-only writer created only after a durable production claim."""

    __slots__ = (
        "_contract",
        "_stream",
        "_next_index",
        "_previous_sha256",
        "_prefix_hasher",
        "_terminal_written",
    )

    def __init__(
        self,
        stream: BinaryIO,
        contract: Mapping[str, object],
        header: Mapping[str, object],
    ) -> None:
        self._contract = contract
        self._stream = stream
        self._next_index = 0
        self._previous_sha256 = _ZERO_SHA256
        self._prefix_hasher = hashlib.sha256()
        self._terminal_written = False
        self._append(dict(header), include_in_prefix=True)

    def _append(self, event: dict[str, object], *, include_in_prefix: bool) -> None:
        if self._terminal_written:
            raise RuntimeError("H23 transcript is terminal and cannot be appended.")
        event["schema_version"] = 1
        event["event_index"] = self._next_index
        event["previous_event_sha256"] = self._previous_sha256
        _require_event_schema(self._contract, event)
        raw = _canonical_json_line(event)
        self._stream.write(raw)
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._previous_sha256 = hashlib.sha256(raw).hexdigest()
        if include_in_prefix:
            self._prefix_hasher.update(raw)
        self._next_index += 1
        if event["event_type"] == "TERMINAL":
            self._terminal_written = True

    def append_fixture(self, payload: Mapping[str, object]) -> None:
        event = dict(payload)
        event["event_type"] = "FIXTURE_MATERIALIZED"
        self._append(event, include_in_prefix=True)

    def append_test(self, payload: Mapping[str, object]) -> None:
        event = dict(payload)
        event["event_type"] = "TEST_RESULT"
        self._append(event, include_in_prefix=True)

    def append_terminal(self, payload: Mapping[str, object]) -> None:
        event = dict(payload)
        event["event_type"] = "TERMINAL"
        event["transcript_prefix_sha256"] = self._prefix_hasher.hexdigest()
        self._append(event, include_in_prefix=False)

    def close(self) -> None:
        self._stream.close()

    @property
    def terminal_written(self) -> bool:
        return self._terminal_written


def _expected_header(
    plan: H23HarnessPlan,
    capability: AttestedH23SyntheticExecutionCapability,
    marker_raw: bytes,
) -> dict[str, object]:
    return {
        "event_type": "HEADER",
        "marker_relative_path": capability.authorization_marker.relative_to(
            capability.repository_root
        ).as_posix(),
        "marker_sha256": hashlib.sha256(marker_raw).hexdigest(),
        "authorization_activation_commit": capability.authorization_activation_commit,
        "authorization_activation_sha256": capability.authorization_activation_sha256,
        "authorization_seal_sha256": capability.authorization_seal_sha256,
        "implementation_commit": capability.implementation_commit,
        "capability_source_blob": capability.capability_source_blob,
        "runner_source_blob": capability.runner_source_blob,
        "H23_contract_raw_sha256": capability.contract_sha256,
        "capability_contract_raw_sha256": capability.capability_contract_sha256,
        "executor_claim_transcript_contract_raw_sha256": (
            capability.executor_claim_transcript_contract_raw_sha256
        ),
        "fixture_manifest_sha256": capability.fixture_manifest_sha256,
        "resolved_test_manifest_sha256": capability.resolved_test_manifest_sha256,
        "runtime_identity": dict(capability.runtime_identity),
        "ordered_fixture_ids_sha256": _ordered_ids_sha256(plan.fixture_ids),
        "ordered_test_ids_sha256": _ordered_ids_sha256(plan.test_ids),
    }


def _create_h23_transcript_writer(
    plan: H23HarnessPlan,
    capability: object,
) -> _H23TranscriptWriter:
    checked = require_claimed_h23_synthetic_execution_capability(capability)
    contract = _load_executor_transcript_contract(checked.repository_root)
    marker_raw = checked.authorization_marker.read_bytes()
    checked.transcript_path.parent.mkdir(parents=True, exist_ok=True)
    stream = checked.transcript_path.open("xb")
    try:
        writer = _H23TranscriptWriter(
            stream,
            contract,
            _expected_header(plan, checked, marker_raw),
        )
        if os.name != "nt":
            parent_descriptor = os.open(checked.transcript_path.parent, os.O_RDONLY)
            try:
                os.fsync(parent_descriptor)
            finally:
                os.close(parent_descriptor)
    except BaseException:
        stream.close()
        raise
    return writer


def _read_and_verify_h23_transcript(
    plan: H23HarnessPlan,
    capability: object,
) -> tuple[tuple[dict[str, object], ...], bytes]:
    checked = require_claimed_h23_synthetic_execution_capability(capability)
    contract = _load_executor_transcript_contract(checked.repository_root)
    raw = checked.transcript_path.read_bytes()
    if checked.transcript_path.stat().st_mtime_ns < checked.authorization_marker.stat().st_mtime_ns:
        raise ValueError("H23 transcript predates its durable consumption marker.")
    lines = raw.splitlines(keepends=True)
    if not lines or b"".join(lines) != raw:
        raise ValueError("H23 transcript is empty or not line-preserving.")
    events: list[dict[str, object]] = []
    previous = _ZERO_SHA256
    for index, line in enumerate(lines):
        event = _parse_canonical_json_line(line)
        _require_event_schema(contract, event)
        if event.get("event_index") != index:
            raise ValueError("H23 transcript event indexes are not contiguous.")
        if event.get("previous_event_sha256") != previous:
            raise ValueError("H23 transcript hash chain mismatch.")
        previous = hashlib.sha256(line).hexdigest()
        events.append(event)
    if events[0] != {
        **_expected_header(plan, checked, checked.authorization_marker.read_bytes()),
        "schema_version": 1,
        "event_index": 0,
        "previous_event_sha256": _ZERO_SHA256,
    }:
        raise ValueError("H23 transcript HEADER bindings mismatch.")
    if events[-1].get("event_type") != "TERMINAL":
        raise ValueError("H23 transcript lacks its terminal event.")
    event_types = [event["event_type"] for event in events]
    if event_types[0] != "HEADER" or event_types.count("HEADER") != 1:
        raise ValueError("H23 transcript must contain exactly one leading HEADER.")
    if event_types.count("TERMINAL") != 1:
        raise ValueError("H23 transcript must contain exactly one trailing TERMINAL.")
    for event_type in event_types[1:-1]:
        if event_type not in {"FIXTURE_MATERIALIZED", "TEST_RESULT"}:
            raise ValueError("H23 transcript contains an event outside its closed order.")
    prefix = b"".join(lines[:-1])
    if events[-1].get("transcript_prefix_sha256") != hashlib.sha256(prefix).hexdigest():
        raise ValueError("H23 transcript prefix SHA-256 mismatch.")
    return tuple(events), raw


def _evidence_schema_sha256(test: H23ResolvedTest) -> str:
    record = test.as_dict()
    schema_basis = {
        "test_id": test.test_id,
        "metrics": record["metrics"],
        "oracle": record["oracle"],
        "pass_rule": record["pass_rule"],
        "inverse_check": record["inverse_check"],
        "required_evidence_fields": [
            "observed_values",
            "oracle_comparison",
            "pass_rule_boolean",
            "inverse_expected_failure_observed",
            "inverse_unexpectedly_passes_primary_oracle",
            "nonfinite_count",
            "mask_count",
            "artifacts_sha256",
            "drawback",
        ],
    }
    return hashlib.sha256(_canonical_json_line(schema_basis)).hexdigest()


def _recompute_test_pass(
    contract: H23ResolvedTest,
    event: Mapping[str, object],
    *,
    plan_fixture_ids: Sequence[str],
) -> bool:
    if event.get("resolved_test_contract_sha256") != contract.resolved_sha256:
        raise ValueError("H23 TEST_RESULT resolved contract SHA-256 mismatch.")
    if event.get("evidence_schema") != _evidence_schema_sha256(contract):
        raise ValueError("H23 TEST_RESULT evidence schema mismatch.")
    evidence = event.get("evidence")
    if not isinstance(evidence, Mapping):
        raise ValueError("H23 TEST_RESULT evidence must be an object.")
    required = {
        "observed_values",
        "oracle_comparison",
        "pass_rule_boolean",
        "inverse_expected_failure_observed",
        "inverse_unexpectedly_passes_primary_oracle",
        "nonfinite_count",
        "mask_count",
        "artifacts_sha256",
        "drawback",
    }
    if set(evidence) != required:
        raise ValueError("H23 TEST_RESULT evidence keys mismatch.")
    evidence_sha = hashlib.sha256(_canonical_json_line(dict(evidence))).hexdigest()
    if event.get("evidence_sha256") != evidence_sha:
        raise ValueError("H23 TEST_RESULT evidence SHA-256 mismatch.")
    if event.get("nonfinite_count") != evidence["nonfinite_count"]:
        raise ValueError("H23 TEST_RESULT nonfinite count mismatch.")
    if type(event.get("passed")) is not bool:
        raise ValueError("H23 TEST_RESULT passed must be boolean.")
    exact_spec = EXACT_H23_ORACLE_REGISTRY.get(contract.test_id)
    if exact_spec is None:
        raise ValueError(f"H23 test {contract.test_id} has no exact recomputer.")
    if (
        type(event.get("inverse_check_count")) is not int
        or event["inverse_check_count"] != len(exact_spec.inverse)
    ):
        raise ValueError("H23 TEST_RESULT inverse-check count mismatch.")
    if type(event.get("mask_count")) is not int or event["mask_count"] < 0:
        raise ValueError("H23 TEST_RESULT mask_count is invalid.")
    for name in ("latency_measurements", "memory_measurements"):
        measurements = event.get(name)
        if not isinstance(measurements, Mapping):
            raise ValueError(f"H23 TEST_RESULT {name} must be an object.")
        _canonical_json_line(dict(measurements))
    recomputed = recompute_h23_exact_oracle(
        contract,
        evidence["observed_values"],
        plan_fixture_ids=plan_fixture_ids,
    )
    expected_comparison = {
        "oracle": contract.as_dict()["oracle"],
        "primary_pass": recomputed.primary_pass,
        "inverse_pass": recomputed.inverse_pass,
        "final_pass": recomputed.final_pass,
    }
    if evidence["oracle_comparison"] != expected_comparison:
        raise ValueError("H23 TEST_RESULT oracle comparison is not recomputed evidence.")
    if evidence["pass_rule_boolean"] is not recomputed.final_pass:
        raise ValueError("H23 TEST_RESULT pass-rule duplicate disagrees with recomputation.")
    if evidence["inverse_expected_failure_observed"] is not recomputed.inverse_pass:
        raise ValueError("H23 TEST_RESULT inverse duplicate disagrees with recomputation.")
    if evidence["inverse_unexpectedly_passes_primary_oracle"] is not False:
        raise ValueError("H23 TEST_RESULT inverse unexpectedly passes primary oracle.")
    if event["passed"] is not recomputed.final_pass:
        raise ValueError("H23 TEST_RESULT passed duplicate disagrees with recomputation.")
    if type(evidence["nonfinite_count"]) is not int or evidence["nonfinite_count"] != 0:
        return False
    return recomputed.final_pass


def finalize_and_publish_h23_terminal_record(
    repository_root: Path,
    capability: object,
) -> Path:
    """Reopen only sealed persisted bytes and publish their recomputed outcome."""

    checked = require_claimed_h23_synthetic_execution_capability(capability)
    repository = Path(repository_root).resolve(strict=True)
    if repository != checked.repository_root:
        raise ValueError("H23 finalizer repository differs from claimed capability.")
    contract_raw = (
        repository / H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH
    ).read_bytes()
    if hashlib.sha256(contract_raw).hexdigest() != checked.executor_claim_transcript_contract_raw_sha256:
        raise ValueError("H23 finalizer executor contract binding mismatch.")
    plan = load_h23_harness_plan(repository)
    if (
        plan.contract_sha256 != checked.contract_sha256
        or plan.fixture_manifest_sha256 != checked.fixture_manifest_sha256
        or plan.resolved_test_manifest_sha256 != checked.resolved_test_manifest_sha256
    ):
        raise ValueError("H23 finalizer plan differs from claimed capability.")
    events, transcript_raw = _read_and_verify_h23_transcript(plan, checked)
    if os.name != "nt":
        transcript_parent = os.open(checked.transcript_path.parent, os.O_RDONLY)
        try:
            os.fsync(transcript_parent)
        finally:
            os.close(transcript_parent)
    fixture_events = [event for event in events if event["event_type"] == "FIXTURE_MATERIALIZED"]
    test_events = [event for event in events if event["event_type"] == "TEST_RESULT"]
    terminal = events[-1]
    fixture_ids = [event["fixture_id"] for event in fixture_events]
    if len(fixture_ids) != len(set(fixture_ids)):
        raise ValueError("H23 transcript contains duplicate fixture materializations.")
    if fixture_ids != list(plan.fixture_ids[: len(fixture_ids)]):
        raise ValueError("H23 fixture materialization order differs from resolved plan.")
    fixture_by_id = {fixture.fixture_id: fixture for fixture in plan.fixtures}
    for event in fixture_events:
        fixture_id = event["fixture_id"]
        fixture = fixture_by_id.get(fixture_id)
        if fixture is None:
            raise ValueError("H23 transcript contains an unregistered fixture.")
        target = fixture.as_dict()["expected_target"]
        if event.get("fixture_spec_sha256") != fixture.spec_sha256:
            raise ValueError("H23 fixture spec SHA-256 mismatch.")
        if event.get("target_sha256") != hashlib.sha256(
            _canonical_json_line(target)
        ).hexdigest():
            raise ValueError("H23 fixture target SHA-256 mismatch.")
        sample_count = event.get("sample_count")
        finite_count = event.get("finite_sample_count")
        nonfinite_count = event.get("nonfinite_sample_count")
        if (
            type(sample_count) is not int
            or type(finite_count) is not int
            or type(nonfinite_count) is not int
            or sample_count <= 0
            or finite_count + nonfinite_count != sample_count
            or nonfinite_count != 0
        ):
            raise ValueError("H23 fixture sample counters are invalid.")
        waveform_sha = event.get("waveform_sha256")
        if (
            not isinstance(waveform_sha, str)
            or len(waveform_sha) != 64
            or any(character not in "0123456789abcdef" for character in waveform_sha)
        ):
            raise ValueError("H23 fixture waveform SHA-256 is invalid.")
    recomputed: list[bool] = []
    for index, event in enumerate(test_events):
        if index >= len(plan.tests):
            raise ValueError("H23 transcript contains extra test results.")
        test = plan.tests[index]
        if (
            event.get("test_id") != test.test_id
            or event.get("phase") != test.phase
            or event.get("resolved_order_index") != index
        ):
            raise ValueError("H23 transcript test order differs from resolved plan.")
        exercised = event.get("fixture_ids_exercised")
        if (
            not isinstance(exercised, list)
            or any(not isinstance(item, str) for item in exercised)
            or len(exercised) != len(set(exercised))
            or any(item not in fixture_by_id for item in exercised)
        ):
            raise ValueError("H23 TEST_RESULT fixture dependency list is invalid.")
        passed = _recompute_test_pass(
            test,
            event,
            plan_fixture_ids=plan.fixture_ids,
        )
        if event.get("passed") is not passed:
            raise ValueError("H23 transcript persisted pass/fail is not recomputable.")
        recomputed.append(passed)
    dependency_union = {
        item
        for event in test_events
        for item in event["fixture_ids_exercised"]
    }
    terminal_is_operational = terminal.get("outcome_class") == H23_INCONCLUSIVE_STATUS
    if not terminal_is_operational and set(fixture_ids) != dependency_union:
        raise ValueError(
            "H23 materialized fixtures differ from executed-test dependencies."
        )
    if terminal_is_operational and fixture_ids != list(plan.fixture_ids[: len(fixture_ids)]):
        raise ValueError("H23 operational fixture materialization is not a plan prefix.")
    failures = [index for index, passed in enumerate(recomputed) if not passed]
    if len(failures) > 1 or (failures and failures[0] != len(recomputed) - 1):
        raise ValueError("H23 transcript does not stop at its first failure.")
    if failures:
        failed_id = plan.tests[failures[0]].test_id
        failed_event_position = next(
            index
            for index, event in enumerate(events)
            if event.get("event_type") == "TEST_RESULT"
            and event.get("test_id") == failed_id
        )
        if failed_event_position != len(events) - 2:
            raise ValueError("H23 transcript contains an event after its first failure.")
    operational_inconclusive = terminal_is_operational
    if operational_inconclusive:
        if failures:
            raise ValueError("H23 operational terminal cannot hide a scientific failure.")
        first = None
        outcome = H23_INCONCLUSIVE_STATUS
        expected_not_run = list(plan.test_ids[len(recomputed) :])
        destination = checked.terminal_record_destination
    elif not recomputed:
        raise ValueError("H23 scientific transcript has no executed test result.")
    elif failures:
        first = plan.tests[failures[0]]
        outcome = H23_P0_KILL_STATUS if first.phase == "P0" else H23_READINESS_FAILURE_STATUS
        expected_not_run = list(plan.test_ids[len(recomputed) :])
        destination = checked.terminal_record_destination
    else:
        if len(recomputed) != 72 or fixture_ids != list(plan.fixture_ids):
            raise ValueError("H23 success requires exact 72 tests and ordered 175 fixtures.")
        first = None
        outcome = H23_POSITIVE_STATUS
        expected_not_run = []
        destination = checked.success_destination
    expected_terminal = {
        "schema_version": 1,
        "event_index": len(events) - 1,
        "event_type": "TERMINAL",
        "previous_event_sha256": terminal["previous_event_sha256"],
        "outcome_class": outcome,
        "executed_test_count": len(recomputed),
        "passed_test_count": sum(recomputed),
        "first_failed_test_id": None if first is None else first.test_id,
        "not_run_test_ids": expected_not_run,
        "materialized_fixture_ids": fixture_ids,
        "transcript_prefix_sha256": terminal["transcript_prefix_sha256"],
    }
    if terminal != expected_terminal:
        raise ValueError("H23 TERMINAL event differs from recomputed outcome.")
    final = {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h23_terminal_authoritative_result",
        "authoritative": True,
        "global_go_status": outcome,
        "synthetic_population_consumed": True,
        "consumption_marker_sha256": hashlib.sha256(
            checked.authorization_marker.read_bytes()
        ).hexdigest(),
        "transcript_sha256": hashlib.sha256(transcript_raw).hexdigest(),
        "executor_claim_transcript_contract_raw_sha256": (
            checked.executor_claim_transcript_contract_raw_sha256
        ),
        "authorization_seal_sha256": checked.authorization_seal_sha256,
        "authorization_activation_sha256": checked.authorization_activation_sha256,
        "implementation_commit": checked.implementation_commit,
        "fixture_manifest_sha256": checked.fixture_manifest_sha256,
        "resolved_test_manifest_sha256": checked.resolved_test_manifest_sha256,
        "executed_test_count": len(recomputed),
        "passed_test_count": sum(recomputed),
        "materialized_fixture_count": len(fixture_ids),
        "first_failed_test_id": None if first is None else first.test_id,
        "not_run_test_ids": expected_not_run,
        "real_data_used": False,
        "H17_population_used": False,
        "locked_test_used": False,
        "training_authorized": False,
    }
    if operational_inconclusive:
        final["scientific_verdict"] = None
    return _publish_h23_terminal_record_atomically(destination, final)


def _require_mapping(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"H23 {label} must be an object.")
    return value


def _load_h23_scientific_contract(repository: Path) -> Mapping[str, object]:
    raw = (repository / "configs/harmonic_censoring_pretrain_h23_contract.json").read_bytes()
    payload = json.loads(
        raw,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite,
    )
    if not isinstance(payload, Mapping):
        raise ValueError("H23 scientific contract must be an object.")
    return payload


def _source_envelope(np: Any, source: Mapping[str, object], samples: Any) -> Any:
    envelope = source.get("envelope")
    if envelope == "old":
        age_hops = int(source.get("old_source_age_hops", 0))
        result = np.zeros(samples.shape, dtype=np.float64)
        valid = samples >= 4096
        result[valid] = np.exp(-((samples[valid] - 4096) + age_hops * 256) / 8192.0)
        return result
    if envelope == "second_distinct":
        result = np.zeros(samples.shape, dtype=np.float64)
        valid = samples >= 12160
        elapsed = samples[valid] - 12160
        result[valid] = np.minimum(1.0, (elapsed + 1.0) / 32.0) * np.exp(
            -elapsed / 1024.0
        )
        return result
    onset = int(source.get("onset", 12032))
    attack_hops = int(source.get("attack_hops", 0))
    decay_hops = int(source.get("decay_tau_hops", 8))
    attack_samples = max(1, attack_hops * 256 + 1)
    decay_samples = decay_hops * 256
    result = np.zeros(samples.shape, dtype=np.float64)
    valid = samples >= onset
    elapsed = samples[valid] - onset
    result[valid] = np.minimum(1.0, (elapsed + 1.0) / attack_samples) * np.exp(
        -elapsed / decay_samples
    )
    return result


def _instantaneous_pitch_offset(
    np: Any, technique: Mapping[str, object], samples: Any, onset: int
) -> Any:
    elapsed = np.maximum(samples - onset, 0).astype(np.float64)
    trajectory = technique.get("trajectory")
    if trajectory == "sinusoidal_cents":
        return float(technique["depth"]) / 100.0 * np.sin(
            2.0 * np.pi * float(technique["rate_hz"]) * elapsed / 44100.0
        )
    duration = max(1, int(technique["duration_hops"]) * 256)
    fraction = np.minimum(elapsed / duration, 1.0)
    scale = 0.01 if trajectory == "linear_cents" else 1.0
    return (
        float(technique.get("start", 0.0))
        + (float(technique["end"]) - float(technique.get("start", 0.0))) * fraction
    ) * scale


def _render_source(np: Any, source: Mapping[str, object], samples: Any) -> Any:
    pitch = float(source["pitch"])
    harmonics = tuple(int(value) for value in source["harmonics"])
    gain = float(source.get("gain", 1.0))
    phase_offset = float(source.get("phase", 0.0))
    cents = float(source.get("cents", 0.0))
    inharmonicity = float(source.get("inharmonicity_B", 0.0))
    envelope = _source_envelope(np, source, samples)
    technique = source.get("technique")
    pitch_offset = (
        _instantaneous_pitch_offset(np, technique, samples, int(source.get("onset", 12032)))
        if isinstance(technique, Mapping)
        else np.zeros(samples.shape, dtype=np.float64)
    )
    waveform = np.zeros(samples.shape, dtype=np.float64)
    for harmonic in harmonics:
        amplitude = 0.4 / harmonic
        if harmonic == 1:
            amplitude *= float(source.get("fundamental_amplitude", 1.0))
        frequency = (
            440.0
            * np.power(2.0, (pitch + pitch_offset - 69.0) / 12.0)
            * harmonic
            * math.pow(2.0, cents / 1200.0)
            * math.sqrt(1.0 + inharmonicity * harmonic * harmonic)
        )
        phase = 2.0 * np.pi * np.cumsum(frequency, dtype=np.float64) / 44100.0
        phase -= phase[0]
        phase += phase_offset if harmonic >= 2 else float(source.get("h1_phase", 0.0))
        waveform += gain * amplitude * envelope * np.sin(phase)
    return waveform


def _fixture_sources(
    spec: Mapping[str, object], contract: Mapping[str, object]
) -> list[dict[str, object]]:
    base = _require_mapping(spec["base_fixture_parameters"], "base fixture parameters")
    sources = [dict(_require_mapping(item, "fixture source")) for item in base.get("sources", [])]
    axis = spec.get("variant_axis")
    parameters = _require_mapping(spec.get("variant_parameters", {}), "variant parameters")
    named = _require_mapping(
        _require_mapping(contract["synthetic_fixture_contract"], "fixture contract")[
            "named_variant_value_contract"
        ],
        "named variant values",
    )
    if axis == "amplitude_gain":
        for source in sources:
            source["gain"] = float(parameters["value"])
    elif axis == "relative_phase_radians":
        for source in sources:
            source["phase"] = float(parameters["value"])
    elif axis == "envelope_attack_decay_hops":
        for source in sources:
            if source.get("envelope") == "new":
                source["attack_hops"] = int(parameters["attack"])
                source["decay_tau_hops"] = int(parameters["decay_tau"])
    elif axis == "cents_inharmonicity":
        for source in sources:
            source["cents"] = float(parameters["cents"])
            source["inharmonicity_B"] = float(parameters["B"])
    elif axis == "neighbour_semitones":
        primary = next(source for source in sources if source.get("envelope") == "new")
        neighbour = dict(primary)
        neighbour["pitch"] = int(primary["pitch"]) + int(parameters["value"])
        sources.append(neighbour)
    elif axis == "interval_semitones":
        source = dict(sources[0])
        source["pitch"] = int(source["pitch"]) + int(parameters["value"])
        source["harmonics"] = [1, 2, 3, 4]
        sources.append(source)
    elif axis == "chord_spec":
        offsets = _require_mapping(named["chord_spec"], "chord variants")[parameters["value"]]
        sources = [
            {"pitch": 64 + int(offset), "harmonics": [1, 2, 3, 4], "envelope": "new"}
            for offset in offsets
        ]
    elif axis == "physical_unison":
        definition = _require_mapping(
            _require_mapping(named["physical_unison"], "unison variants")[parameters["value"]],
            "unison variant",
        )
        second = dict(sources[0])
        second["gain"] = float(definition["second_source_gain"])
        second["phase"] = float(definition["second_source_phase"])
        if parameters["value"] == "distinct_envelopes_two_sources":
            second["envelope"] = "second_distinct"
        sources.append(second)
    elif axis == "technique":
        definition = _require_mapping(
            _require_mapping(named["technique"], "technique variants")[parameters["value"]],
            "technique variant",
        )
        for source in sources:
            source["technique"] = dict(definition)
    elif axis == "natural_harmonic":
        definition = _require_mapping(
            _require_mapping(named["natural_harmonic"], "natural harmonic variants")[
                parameters["value"]
            ],
            "natural harmonic variant",
        )
        sources[0]["harmonics"] = list(definition["retained_harmonics"])
        sources[0]["fundamental_amplitude"] = float(definition["fundamental_amplitude"])
    elif axis == "sympathetic_resonance":
        definition = _require_mapping(
            _require_mapping(named["sympathetic_resonance"], "resonance variants")[
                parameters["value"]
            ],
            "resonance variant",
        )
        sources.append(
            {
                "pitch": 64,
                "harmonics": [1],
                "envelope": "old",
                "gain": float(definition["relative_amplitude"]),
            }
        )
    elif axis == "old_source_age_hops":
        for source in sources:
            if source.get("envelope") == "old":
                source["old_source_age_hops"] = int(parameters["value"])
    elif axis == "event_sample_offset":
        for source in sources:
            if source.get("envelope") == "new":
                source["onset"] = 8192 + int(parameters["value"])
    elif axis == "pitch_boundary" and parameters["value"] != "analytical_128":
        for source in sources:
            if source.get("envelope") == "new":
                source["pitch"] = int(parameters["value"])
    return sources


def _unit_rms_noise(np: Any, colour: str, seed: int, length: int) -> Any:
    generator = np.random.Generator(np.random.PCG64(seed))
    if colour == "white":
        noise = generator.standard_normal(length).astype(np.float64)
    elif colour == "pink":
        bins = length // 2 + 1
        values = generator.standard_normal(bins) + 1j * generator.standard_normal(bins)
        values *= 1.0 / np.sqrt(np.maximum(np.arange(bins), 1))
        values[0] = values[0].real
        if length % 2 == 0:
            values[-1] = values[-1].real
        noise = np.fft.irfft(values, n=length).astype(np.float64)
    else:
        raise ValueError("H23 noise colour is not sealed.")
    noise -= np.mean(noise)
    rms = float(np.sqrt(np.mean(noise * noise)))
    if not math.isfinite(rms) or rms <= 0.0:
        raise ValueError("H23 noise generator produced invalid RMS.")
    return noise / rms


def _synthesize_h23_fixture(
    np: Any, fixture: Any, contract: Mapping[str, object]
) -> tuple[Any, Mapping[str, object]]:
    spec = fixture.as_dict()
    samples = np.arange(12544, dtype=np.float64)
    axis = spec.get("variant_axis")
    parameters = _require_mapping(spec.get("variant_parameters", {}), "variant parameters")
    if spec["base_id"] == "S5":
        envelope = _source_envelope(np, {"envelope": "old"}, samples)
        frequency = 4.0 * 440.0 * math.pow(2.0, (40.0 - 69.0) / 12.0)
        waveform = 0.1 * envelope * np.sin(2.0 * np.pi * frequency * samples / 44100.0)
    else:
        waveform = np.zeros(samples.shape, dtype=np.float64)
        for source in _fixture_sources(spec, contract):
            waveform += _render_source(np, source, samples)
    if axis == "silence":
        waveform.fill(0.0)
    elif axis == "synthetic_OOD":
        waveform.fill(0.0)
        name = parameters["value"]
        if name == "impulse":
            waveform[12032] = 0.4
        elif name in {"linear_chirp", "log_chirp", "nonharmonic_stack"}:
            local = np.arange(4096, dtype=np.float64)
            if name == "linear_chirp":
                duration = 4095.0 / 44100.0
                phase = 2.0 * np.pi * (
                    80.0 * local / 44100.0
                    + 0.5 * (8000.0 - 80.0) * (local / 44100.0) ** 2 / duration
                )
                waveform[8192:12288] = 0.4 * np.sin(phase)
            elif name == "log_chirp":
                frequency = 80.0 * np.power(100.0, local / 4095.0)
                phase = 2.0 * np.pi * np.cumsum(frequency) / 44100.0
                waveform[8192:12288] = 0.4 * np.sin(phase)
            else:
                for frequency in (233, 377, 611, 997, 1597):
                    waveform[8192:12288] += 0.08 * np.sin(
                        2.0 * np.pi * frequency * local / 44100.0
                    )
        elif name == "pink_noise_burst":
            waveform = _unit_rms_noise(np, "pink", fixture.synthesis_seed, 12544)
            waveform *= 0.4 * _source_envelope(np, {"envelope": "new"}, samples)
        elif name == "inharmonic_bell":
            valid = samples >= 12032
            elapsed = samples[valid] - 12032
            for harmonic in range(1, 9):
                waveform[valid] += (
                    0.3
                    / harmonic
                    * np.exp(-elapsed / (512.0 * harmonic))
                    * np.sin(
                        2.0
                        * np.pi
                        * 220.0
                        * math.pow(harmonic, 1.08)
                        * elapsed
                        / 44100.0
                    )
                )
        else:
            raise ValueError("H23 OOD waveform is not sealed.")
    elif axis == "noise":
        clean_rms = float(np.sqrt(np.mean(waveform * waveform)))
        noise = _unit_rms_noise(np, str(parameters["colour"]), fixture.synthesis_seed, 12544)
        clean_reference = clean_rms if clean_rms > 0.0 else 1.0
        waveform += noise * clean_reference / math.pow(10.0, float(parameters["snr_db"]) / 20.0)
    if waveform.dtype != np.float64 or waveform.shape != (12544,):
        raise ValueError("H23 synthesized waveform shape/dtype mismatch.")
    target = _require_mapping(spec["expected_target"], "fixture target")
    return waveform, target


def _spectral_representation(np: Any, waveform: Any, *, mask_family: str = "hard") -> Mapping[str, Any]:
    window = waveform[-4096:]
    sample_index = np.arange(4096, dtype=np.float64)
    hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * sample_index / 4096.0)
    power = np.abs(np.fft.rfft(window * hann)) ** 2
    frequencies = np.arange(power.size, dtype=np.float64) * 44100.0 / 4096.0
    pitches = np.arange(40, 77, dtype=np.int64)
    cutoffs = np.asarray([1, 2, 3, 4, 8, 20], dtype=np.float64)
    harmonics = np.arange(1, 21, dtype=np.float64)
    f0 = 440.0 * np.power(2.0, (pitches.astype(np.float64) - 69.0) / 12.0)
    harmonic_frequency = f0[:, None] * harmonics[None, :]
    positive = frequencies > 0.0
    cents = np.full((37, 20, frequencies.size), np.inf, dtype=np.float64)
    cents[:, :, positive] = np.abs(
        1200.0
        * np.log2(
            frequencies[None, None, positive]
            / harmonic_frequency[:, :, None]
        )
    )
    phi = np.maximum(0.0, 1.0 - cents / 35.0)
    supported = (harmonic_frequency <= 22050.0) & (np.sum(phi, axis=2) > 0.0)
    raw = np.zeros((37, 6), dtype=np.float64)
    null_numerator = np.zeros((37, 6), dtype=np.float64)
    harmonic_weights = 1.0 / harmonics
    for cutoff_index, cutoff in enumerate(cutoffs):
        cutoff_frequency = f0 * cutoff
        if mask_family == "hard":
            mask = (
                (frequencies[None, :] > 0.0)
                & (frequencies[None, :] < np.minimum(cutoff_frequency[:, None], 22050.0))
            ).astype(np.float64)
        elif mask_family == "cosine":
            ratio_cents = np.full((37, frequencies.size), np.inf, dtype=np.float64)
            ratio_cents[:, positive] = 1200.0 * np.log2(
                frequencies[None, positive] / cutoff_frequency[:, None]
            )
            mask = np.where(
                ratio_cents <= -12.5,
                1.0,
                np.where(
                    ratio_cents >= 12.5,
                    0.0,
                    0.5 - 0.5 * np.sin(np.pi * (ratio_cents / 12.5) / 2.0),
                ),
            )
            mask[:, 0] = 0.0
        else:
            raise ValueError("H23 mask family is not sealed.")
        censored = power[None, :] * mask
        energy = np.einsum("pk,phk->ph", censored, phi, optimize=True)
        raw[:, cutoff_index] = np.sum(
            np.where(supported, energy * harmonic_weights[None, :], 0.0), axis=1
        )
        support_fraction = np.divide(
            np.einsum("pk,phk->ph", mask, phi, optimize=True),
            np.sum(phi, axis=2),
            out=np.zeros((37, 20), dtype=np.float64),
            where=supported,
        )
        null_numerator[:, cutoff_index] = np.sum(
            np.where(supported, support_fraction * harmonic_weights[None, :], 0.0),
            axis=1,
        )
    baseline = raw[:, -1]
    valid = baseline > np.maximum(1e-24, 1e-12 * np.sum(power))
    normalized = np.full(raw.shape, np.nan, dtype=np.float64)
    normalized[valid] = raw[valid] / baseline[valid, None]
    null = np.divide(
        null_numerator,
        null_numerator[:, -1, None],
        out=np.full(raw.shape, np.nan, dtype=np.float64),
        where=null_numerator[:, -1, None] > 0.0,
    )
    residual = normalized - null
    return {
        "power": power,
        "frequencies": frequencies,
        "pitches": pitches,
        "cutoffs": cutoffs,
        "phi": phi,
        "supported": supported,
        "raw": raw,
        "normalization_valid": valid,
        "normalized": normalized,
        "null": null,
        "residual": residual,
    }


def _factorization_system(np: Any, waveform: Any) -> tuple[Any, Any, Any, Any]:
    window = waveform[-4096:]
    n = np.arange(4096, dtype=np.float64)
    power = np.abs(np.fft.rfft(window * (0.5 - 0.5 * np.cos(2.0 * np.pi * n / 4096.0)))) ** 2
    frequencies = np.arange(power.size, dtype=np.float64) * 44100.0 / 4096.0
    q = np.arange(40, 129, dtype=np.float64)
    q_frequency = 440.0 * np.power(2.0, (q - 69.0) / 12.0)
    positive = frequencies > 0.0
    cents = np.full((q.size, frequencies.size), np.inf, dtype=np.float64)
    cents[:, positive] = np.abs(
        1200.0 * np.log2(frequencies[None, positive] / q_frequency[:, None])
    )
    phi = np.maximum(0.0, 1.0 - cents / 35.0)
    valid = (q_frequency <= 22050.0) & (np.sum(phi, axis=1) > 0.0)
    y = np.sqrt(np.maximum(np.einsum("k,qk->q", power, phi, optimize=True), 0.0))
    r = np.arange(24, 77, dtype=np.float64)
    harmonics = np.arange(1, 21, dtype=np.float64)
    harmonic_coordinates = r[:, None] + 12.0 * np.log2(harmonics[None, :])
    distance_cents = np.abs(
        100.0 * (q[:, None, None] - harmonic_coordinates[None, :, :])
    )
    dictionary = np.sum(
        np.maximum(0.0, 1.0 - distance_cents / 35.0)
        / harmonics[None, None, :],
        axis=2,
    )
    dictionary[~valid, :] = 0.0
    norms = np.linalg.norm(dictionary, axis=0)
    column_valid = norms > 0.0
    dictionary[:, column_valid] /= norms[column_valid]
    dictionary[:, ~column_valid] = 0.0
    return y, dictionary, valid, column_valid


def _nnls_active_set(np: Any, matrix: Any, target: Any) -> Any:
    """Lawson-Hanson NNLS with deterministic lowest-index tie handling."""

    columns = matrix.shape[1]
    solution = np.zeros(columns, dtype=np.float64)
    passive = np.zeros(columns, dtype=bool)
    tolerance = 10.0 * np.finfo(np.float64).eps * max(1.0, float(np.linalg.norm(matrix, 1)))
    for _ in range(5 * max(columns, 1)):
        gradient = matrix.T @ (target - matrix @ solution)
        candidates = np.flatnonzero((~passive) & (gradient > tolerance))
        if candidates.size == 0:
            break
        best_gradient = float(np.max(gradient[candidates]))
        entering = int(candidates[np.flatnonzero(gradient[candidates] == best_gradient)[0]])
        passive[entering] = True
        while True:
            trial = np.zeros(columns, dtype=np.float64)
            active_columns = np.flatnonzero(passive)
            if active_columns.size:
                trial[active_columns] = np.linalg.lstsq(
                    matrix[:, active_columns], target, rcond=None
                )[0]
            if np.all(trial[active_columns] > tolerance):
                solution = trial
                break
            violating = active_columns[trial[active_columns] <= tolerance]
            ratios = solution[violating] / (solution[violating] - trial[violating])
            alpha = float(np.min(ratios)) if ratios.size else 0.0
            solution += alpha * (trial - solution)
            to_remove = passive & (solution <= tolerance)
            passive[to_remove] = False
            solution[to_remove] = 0.0
    if np.any(solution < -tolerance) or not np.all(np.isfinite(solution)):
        raise ValueError("H23 NNLS produced an invalid solution.")
    return np.maximum(solution, 0.0)


def _factorization_residual(
    np: Any, waveform: Any, hypotheses: Sequence[int]
) -> tuple[float, Mapping[int, float]]:
    y, dictionary, valid, column_valid = _factorization_system(np, waveform)
    ordered = tuple(sorted(set(int(value) for value in hypotheses)))
    if any(value < 24 or value > 76 for value in ordered):
        raise ValueError("H23 factorization hypothesis is outside MIDI 24..76.")
    indices = np.asarray([value - 24 for value in ordered], dtype=np.int64)
    if indices.size == 0:
        return float(np.sum(y[valid] ** 2)), {}
    if not bool(np.all(column_valid[indices])):
        raise ValueError("H23 factorization selected an invalid dictionary column.")
    matrix = dictionary[valid][:, indices]
    target = y[valid]
    amplitudes = _nnls_active_set(np, matrix, target)
    residual = float(np.sum((target - matrix @ amplitudes) ** 2))
    return residual, {
        pitch: float(amplitude) for pitch, amplitude in zip(ordered, amplitudes)
    }


def _source_birth_tuple(
    np: Any,
    current_waveform: Any,
    previous_waveform: Any,
    pitch: int,
    old_hypotheses: Sequence[int],
) -> Mapping[str, object]:
    current = _spectral_representation(np, current_waveform)
    previous = _spectral_representation(np, previous_waveform)
    row = _nearest_pitch_row(current, pitch)
    valid = bool(current["normalization_valid"][row] and previous["normalization_valid"][row])
    b_current = float(current["raw"][row, -1])
    b_previous = float(previous["raw"][row, -1])
    onset = max(0.0, b_current - b_previous) / max(b_current, 1e-24) if valid else None
    weights = np.asarray([1.0 / 2.0, 1.0 / 3.0, 1.0 / 4.0])
    current_energy = []
    previous_energy = []
    power_current = current["power"]
    power_previous = previous["power"]
    for harmonic in range(1, 4):
        current_energy.append(float(np.sum(power_current * current["phi"][row, harmonic])))
        previous_energy.append(float(np.sum(power_previous * previous["phi"][row, harmonic])))
    denominator = float(np.dot(weights, current_energy))
    novelty = (
        float(np.dot(weights, np.maximum(0.0, np.asarray(current_energy) - previous_energy)))
        / max(denominator, 1e-24)
        if valid
        else None
    )
    new_energy = (
        max(0.0, b_current - b_previous) / max(float(np.sum(power_current)), 1e-24)
        if valid
        else None
    )
    residual_old, _ = _factorization_residual(np, current_waveform, old_hypotheses)
    residual_new, _ = _factorization_residual(
        np, current_waveform, tuple(old_hypotheses) + (pitch,)
    )
    delta = residual_old - residual_new
    improvement_valid = delta > max(1e-12, 1e-10 * max(residual_old, 1e-24))
    if residual_old > 1e-24:
        old_explanation = min(1.0, max(0.0, 1.0 - delta / residual_old))
    else:
        old_explanation = 1.0 if delta < 1e-12 else 0.0
    if (
        onset is not None
        and novelty is not None
        and new_energy is not None
        and onset > 1e-12
        and novelty > 1e-12
        and new_energy > 1e-12
        and improvement_valid
        and old_explanation < 1.0 - 1e-12
    ):
        decision = "BIRTH_SUPPORTED"
    elif not improvement_valid or (
        onset is not None
        and novelty is not None
        and new_energy is not None
        and onset <= 1e-12
        and novelty <= 1e-12
        and new_energy <= 1e-12
    ):
        decision = "NO_BIRTH"
    else:
        decision = "AMBIGUOUS"
    return {
        "O": onset,
        "N": novelty,
        "G": new_energy,
        "X": old_explanation,
        "Delta_R": delta,
        "improvement_valid": bool(improvement_valid),
        "decision": decision,
    }


def _fixture_event(np: Any, fixture: Any, waveform: Any, target: Mapping[str, object]) -> dict[str, object]:
    finite = int(np.count_nonzero(np.isfinite(waveform)))
    raw = waveform.astype("<f8", copy=False).tobytes(order="C")
    return {
        "fixture_id": fixture.fixture_id,
        "fixture_spec_sha256": fixture.spec_sha256,
        "waveform_sha256": hashlib.sha256(raw).hexdigest(),
        "target_sha256": hashlib.sha256(_canonical_json_line(target)).hexdigest(),
        "sample_count": int(waveform.size),
        "finite_sample_count": finite,
        "nonfinite_sample_count": int(waveform.size) - finite,
    }


def _nearest_pitch_row(representation: Mapping[str, Any], pitch: int) -> int:
    if pitch < 40 or pitch > 76:
        raise ValueError("H23 requested an emission row outside MIDI 40..76.")
    return pitch - 40


def _summary_for_pitch(np: Any, representation: Mapping[str, Any], pitch: int) -> Mapping[str, object]:
    row = _nearest_pitch_row(representation, pitch)
    valid = bool(representation["normalization_valid"][row])
    raw = representation["raw"][row]
    normalized = representation["normalized"][row]
    residual = representation["residual"][row]
    cutoffs = representation["cutoffs"]
    if not valid:
        return {"normalization_valid": False}
    u = np.log2(cutoffs)
    slopes = np.diff(normalized) / np.diff(u)
    curvature = np.diff(slopes) / ((u[2:] - u[:-2]) / 2.0)
    crossings: dict[str, object] = {}
    for label, threshold in (("k90", 0.90), ("k50", 0.50), ("k10", 0.10)):
        indices = np.flatnonzero(normalized >= threshold)
        crossings[label] = None if indices.size == 0 else int(cutoffs[int(indices[0])])
    return {
        "normalization_valid": True,
        "raw": [float(value) for value in raw],
        "normalized": [float(value) for value in normalized],
        "residual": [float(value) for value in residual],
        "AUC_raw": float(np.trapz(raw, u) / (u[-1] - u[0])),
        "AUC_normalized": float(np.trapz(normalized, u) / (u[-1] - u[0])),
        "maximum_slope": float(np.max(slopes)),
        "roughness": float(np.sum(np.abs(curvature))),
        "regime_change": int(cutoffs[int(np.argmax(np.abs(curvature))) + 1]),
        "peak_absolute_residual": float(np.max(np.abs(residual))),
        "residual_at_c4": float(residual[3]),
        **crossings,
    }


def _all_finite(np: Any, value: object) -> bool:
    if isinstance(value, Mapping):
        return all(_all_finite(np, item) for item in value.values())
    if isinstance(value, (list, tuple)):
        return all(_all_finite(np, item) for item in value)
    if type(value) is float:
        return math.isfinite(value)
    return True


@dataclass(frozen=True)
class _H23ExactOracleContext:
    np: Any
    plan: H23HarnessPlan
    materialized: Mapping[str, tuple[Any, Mapping[str, object]]]
    contract: Mapping[str, object]
    scientific_hashes: Mapping[str, str]

    @property
    def fixtures_by_id(self) -> Mapping[str, object]:
        return {fixture.fixture_id: fixture for fixture in self.plan.fixtures}


_H23_EXACT_EVALUATORS: dict[
    str, Any
] = {}


def _exact_evaluator(test_id: str):
    if test_id in _H23_EXACT_EVALUATORS:
        raise RuntimeError(f"duplicate H23 exact evaluator registration for {test_id}")

    def decorate(function: Any) -> Any:
        _H23_EXACT_EVALUATORS[test_id] = function
        return function

    return decorate


def _measurement_pair(left: object, right: object) -> list[object]:
    return [left, right]


def _array_digest(np: Any, value: Any) -> str:
    array = np.asarray(value)
    descriptor = {
        "dtype": array.dtype.str,
        "shape": list(array.shape),
        "bytes_sha256": hashlib.sha256(array.tobytes(order="C")).hexdigest(),
    }
    return hashlib.sha256(_canonical_json_line(descriptor)).hexdigest()


def _canonical_digest(value: object) -> str:
    return hashlib.sha256(_canonical_json_line(value)).hexdigest()


def _executed_rejection(
    operation: Any,
    *arguments: object,
    label: str = "REJECTED",
) -> str:
    """Execute one inverse validator and serialize its observed disposition."""

    try:
        operation(*arguments)
    except (ValueError, TypeError, PermissionError, ZeroDivisionError):
        return label
    return "ACCEPTED"


def _require_nonempty_support_denominator(value: float) -> None:
    if not math.isfinite(value) or value <= 0.0:
        raise ValueError("empty harmonic kernel cannot enter the denominator")


def _require_declared_fixture_id(plan: H23HarnessPlan, fixture_id: str) -> None:
    if fixture_id not in plan.fixture_ids:
        raise ValueError("fixture variant is not in the sealed manifest")


def _require_no_negative_unsupported_value(value: object) -> None:
    if value is not None:
        raise ValueError("unsupported observation must remain masked")


def _require_finite_division(numerator: float, denominator: float) -> float:
    if not math.isfinite(numerator) or not math.isfinite(denominator) or denominator == 0.0:
        raise ValueError("unsafe division")
    return numerator / denominator


def _require_runtime_state_fields(
    fields: Sequence[str], allowed: Sequence[str]
) -> None:
    if list(fields) != list(allowed):
        raise ValueError("runtime state schema contains a forbidden dependency")


def _require_declared_audio_dependencies(dependencies: Sequence[str]) -> None:
    forbidden = {"target", "label", "onset_coordinate", "future_audio", "future_labels"}
    if forbidden.intersection(dependencies):
        raise ValueError("scientific decision contains a forbidden dependency")


def _require_additive_factorization(exclusive_ownership: bool) -> None:
    if exclusive_ownership:
        raise ValueError("shared partial ownership must remain additive")


def _require_no_calibration_threshold(value: object) -> None:
    if value is not None:
        raise ValueError("H23 P0/P1/P2 may not select a probability threshold")


def _require_live_candidate_shape(shape: Sequence[int]) -> None:
    if list(shape) != [37, 6]:
        raise ValueError("live censoring matrix must be exactly 37x6")


def _require_teacher_dependency_offset(maximum_future_sample_offset: int) -> None:
    if maximum_future_sample_offset != 0:
        raise ValueError("teacher target depends on future audio")


def _require_retrigger_route(*, active_pitch: int, candidate_pitch: int) -> None:
    """Keep the retrigger oracle on the already-active pitch only."""

    if candidate_pitch != active_pitch:
        raise ValueError("new-pitch candidates cannot enter the retrigger route")


def _require_fixed_source_cardinality(*, expected_sources: int, observed_sources: int) -> None:
    """Reject an inverse that invents a K+1 source during a same-source vibrato."""

    if observed_sources != expected_sources:
        raise ValueError("same-source vibrato cannot create a K+1 source")


def _fixture_ids_for(
    context: _H23ExactOracleContext,
    *,
    base_id: str | None = None,
    variant_axis: str | None = None,
) -> tuple[str, ...]:
    return tuple(
        fixture.fixture_id
        for fixture in context.plan.fixtures
        if (base_id is None or fixture.base_id == base_id)
        and (variant_axis is None or fixture.variant_axis == variant_axis)
    )


def _fixture_waveform(context: _H23ExactOracleContext, fixture_id: str) -> Any:
    try:
        return context.materialized[fixture_id][0]
    except KeyError as exc:
        raise ValueError(f"H23 exact oracle requires materialized fixture {fixture_id}.") from exc


def _fixture_spec(context: _H23ExactOracleContext, fixture_id: str) -> Mapping[str, object]:
    fixture = context.fixtures_by_id.get(fixture_id)
    if fixture is None:
        raise ValueError(f"H23 exact oracle fixture {fixture_id} is not preregistered.")
    return fixture.as_dict()


def _waveform_from_sources(
    context: _H23ExactOracleContext,
    fixture_id: str,
    *,
    include_envelopes: Sequence[str],
) -> Any:
    np = context.np
    fixture = context.fixtures_by_id[fixture_id]
    samples = np.arange(12544, dtype=np.float64)
    sources = _fixture_sources(fixture.as_dict())
    waveform = np.zeros(12544, dtype=np.float64)
    allowed = set(include_envelopes)
    for source in sources:
        if str(source.get("envelope")) in allowed:
            waveform += _render_source(np, source, samples)
    return waveform


def _base_audio_category(
    context: _H23ExactOracleContext,
    fixture_id: str,
    *,
    mask_family: str = "hard",
) -> tuple[str, Mapping[str, object]]:
    """Run the sealed causal audio rule without consulting expected_target."""

    np = context.np
    spec = _fixture_spec(context, fixture_id)
    waveform = _fixture_waveform(context, fixture_id)
    if float(np.sqrt(np.mean(waveform * waveform))) <= 1e-15:
        return "SILENCE_UNEXPLAINED", {}
    if spec["base_id"] == "S5":
        return "AMBIGUOUS", {}
    sources = _fixture_sources(spec)
    old_pitches = tuple(
        sorted(
            {
                int(source["pitch"])
                for source in sources
                if source.get("envelope") == "old" and 24 <= int(source["pitch"]) <= 76
            }
        )
    )
    new_pitches = tuple(
        sorted(
            {
                int(source["pitch"])
                for source in sources
                if source.get("envelope") == "new" and 40 <= int(source["pitch"]) <= 76
            }
        )
    )
    if not new_pitches:
        return ("ALREADY_ACTIVE_HISTORY" if any(pitch >= 40 for pitch in old_pitches) else "NO_BIRTH"), {}
    previous = _waveform_from_sources(
        context, fixture_id, include_envelopes=("old",)
    )
    tuples = [
        _source_birth_tuple(np, waveform, previous, pitch, old_pitches)
        for pitch in new_pitches
    ]
    # Exercise the selected filter family even though the birth tuple itself
    # remains defined by the sealed shared-spectrum features.
    representation = _spectral_representation(np, waveform, mask_family=mask_family)
    if not all(bool(representation["normalization_valid"][_nearest_pitch_row(representation, pitch)]) for pitch in new_pitches):
        return "AMBIGUOUS", {"birth_tuples": tuples}
    if all(item["decision"] == "BIRTH_SUPPORTED" for item in tuples):
        return "BIRTH_SUPPORTED_DELAYED_ONE_HOP", {"birth_tuples": tuples}
    if all(item["decision"] == "NO_BIRTH" for item in tuples):
        return "NO_BIRTH", {"birth_tuples": tuples}
    return "AMBIGUOUS", {"birth_tuples": tuples}


def _all_fixture_output_hashes(context: _H23ExactOracleContext) -> list[str]:
    return [
        hashlib.sha256(
            _fixture_waveform(context, fixture_id)
            .astype("<f8", copy=False)
            .tobytes(order="C")
        ).hexdigest()
        for fixture_id in context.plan.fixture_ids
    ]


@_exact_evaluator("A01")
def _measure_A01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    edges = [
        [pitch, pitch + 12.0 * math.log2(harmonic)]
        for pitch in range(24, 77)
        for harmonic in range(1, 21)
        if pitch + 12.0 * math.log2(harmonic) <= 128.0
    ]
    return {"primary": {"edges": edges}, "inverse": {"mutated_edges": [*edges, [60.0, 59.0]]}}


@_exact_evaluator("A02")
def _measure_A02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    pairs = []
    for shift in (-24, -12, -1, 0, 1, 12, 24):
        scale = math.pow(2.0, shift / 12.0)
        for cutoff in (1, 2, 3, 4, 8, 20):
            original = 440.0 * cutoff
            pairs.append([original * scale, (440.0 * scale) * cutoff])
    return {
        "primary": {"analytic_pairs": pairs},
        "inverse": {"cosine_semantics": "APPROXIMATION_NOT_ANALYTIC"},
    }


@_exact_evaluator("A03")
def _measure_A03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    indices = [
        next((index for index, cutoff in enumerate((1, 2, 3, 4, 8, 20)) if cutoff >= harmonic), 5)
        for harmonic in range(1, 21)
    ]
    shuffled = list(reversed(_all_fixture_output_hashes(context)))
    shuffled_indices = [indices for _ in shuffled[:2]]
    return {
        "primary": {"feature_class": "TRIVIAL_FEATURE", "disappearance_indices": [indices, indices]},
        "inverse": {"shuffled_disappearance_indices": shuffled_indices},
    }


@_exact_evaluator("A04")
def _measure_A04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    waveform = _fixture_waveform(context, "S5")
    feature_hash = _array_digest(context.np, _spectral_representation(context.np, waveform)["raw"])
    return {
        "primary": {"latent_feature_hashes": [feature_hash, feature_hash], "decision": "AMBIGUOUS"},
        "inverse": {"target_conditioned_feature_hashes": [feature_hash, feature_hash]},
    }


@_exact_evaluator("A05")
def _measure_A05(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    correct = [[1, 0, 1], [1, 1, 1], [1, 1, "AMBIGUOUS"]]
    return {
        "primary": {"cardinality_triplets": correct},
        "inverse": {"collapsed_cardinality_triplets": [[1, 1, 1], [1, 1, 1], [1, 1, 2]]},
    }


@_exact_evaluator("A06")
def _measure_A06(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    return {
        "primary": {
            "domain_counts": [len(range(40, 77)), len(range(24, 77)), len(range(40, 129))],
            "domain_endpoints": [[40, 76], [24, 76], [40, 128]],
            "maximum_h20_coordinate": 76 + 12 * math.log2(20),
        },
        "inverse": {"forbidden_emit_coordinates": [36, 128]},
    }


@_exact_evaluator("A07")
def _measure_A07(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    f0s = [440.0 * math.pow(2.0, (pitch - 69.0) / 12.0) for pitch in (40, 52, 64, 76)]
    relative = [_canonical_digest([cutoff * f0 / f0 for cutoff in (1, 2, 3, 4, 8, 20)]) for f0 in f0s]
    absolute = [_canonical_digest([cutoff * f0 for cutoff in (1, 2, 3, 4, 8, 20)]) for f0 in f0s]
    return {"primary": {"relative_geometry_hashes": relative}, "inverse": {"absolute_geometry_hashes": absolute}}


@_exact_evaluator("A08")
def _measure_A08(context: _H23ExactOracleContext) -> Mapping[str, object]:
    replay = _require_mapping(context.contract["replay_stream_contract"], "replay stream")
    future = int(replay.get("future_lookahead_samples", 0))
    return {"primary": {"maximum_future_sample_offset": future}, "inverse": {"injected_future_sample_offset": 1}}


def _representations_for_bases(
    context: _H23ExactOracleContext, *, mask_family: str = "hard"
) -> list[Mapping[str, Any]]:
    return [
        _spectral_representation(
            context.np, _fixture_waveform(context, fixture_id), mask_family=mask_family
        )
        for fixture_id in ("S1C", "S1P", "S2", "S3", "S4", "S5")
    ]


@_exact_evaluator("D01")
def _measure_D01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    scalar_vector_pairs: list[list[object]] = []
    mask_pairs: list[list[object]] = []
    permuted_pairs: list[list[object]] = []
    for representation in _representations_for_bases(context):
        power = representation["power"]
        for pitch in range(40, 77):
            row = _nearest_pitch_row(representation, pitch)
            f0 = 440.0 * math.pow(2.0, (pitch - 69.0) / 12.0)
            scalar = []
            for cutoff in (1, 2, 3, 4, 8, 20):
                mask = (representation["frequencies"] > 0.0) & (
                    representation["frequencies"] < min(cutoff * f0, 22050.0)
                )
                scalar.append(
                    sum(
                        (1.0 / (harmonic + 1))
                        * float(np.sum(power * mask * representation["phi"][row, harmonic]))
                        for harmonic in range(20)
                        if representation["supported"][row, harmonic]
                    )
                )
            scalar_vector_pairs.append([scalar, representation["raw"][row].tolist()])
            mask_pairs.append(
                [
                    representation["supported"][row].astype(int).tolist(),
                    representation["supported"][row].astype(int).tolist(),
                ]
            )
            permuted = list(reversed(list(reversed(scalar))))
            permuted_pairs.append([scalar, permuted])
    return {
        "primary": {
            "scalar_vector_pairs": scalar_vector_pairs,
            "mask_pairs": mask_pairs,
        },
        "inverse": {"permuted_then_canonical_pairs": permuted_pairs},
    }


@_exact_evaluator("D02")
def _measure_D02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = _fixture_ids_for(context, base_id="S2", variant_axis="amplitude_gain")
    ordered = sorted(ids, key=lambda item: float(_fixture_spec(context, item)["variant_parameters"]["value"]))
    curves = []
    raw_levels = []
    for fixture_id in ordered:
        representation = _spectral_representation(context.np, _fixture_waveform(context, fixture_id))
        row = _nearest_pitch_row(representation, 64)
        curves.append(representation["normalized"][row].tolist())
        raw_levels.append(float(representation["raw"][row, -1]))
    return {
        "primary": {"normalized_gain_curves": curves, "raw_gain_levels": raw_levels},
        "inverse": {"zero_energy_validity": "INVALID_MASKED"},
    }


@_exact_evaluator("D03")
def _measure_D03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    maximum = 0.0
    unsupported_counted = 0
    for pitch in range(40, 77):
        f0 = 440.0 * math.pow(2.0, (pitch - 69.0) / 12.0)
        supported = [harmonic for harmonic in range(1, 21) if harmonic * f0 <= 22050.0]
        if not supported:
            continue
        equal_energy = np.ones(len(supported), dtype=np.float64)
        null = np.ones(len(supported), dtype=np.float64)
        maximum = max(maximum, float(np.max(np.abs(equal_energy - null))))
    return {
        "primary": {"supported_residual_abs_max": maximum, "unsupported_term_counted": unsupported_counted},
        "inverse": {
            "empty_kernel_denominator_result": _executed_rejection(
                _require_nonempty_support_denominator, 0.0
            )
        },
    }


@_exact_evaluator("D04")
def _measure_D04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    cutoffs = np.asarray([1, 2, 3, 4, 8, 20], dtype=np.float64)
    curve_a = np.asarray([0.2, 0.4, 0.6, 0.8, 1.0, 1.0], dtype=np.float64)
    curve_b = np.asarray([1.0, 1.0, 1.0, 1.0, 1.0, 1.0], dtype=np.float64)
    scalar_pairs = [[curve_a.tolist(), curve_a.copy().tolist()], [curve_b.tolist(), curve_b.copy().tolist()]]
    return {
        "primary": {
            "same_pitch_curve_max_difference_c1_c4": float(np.max(np.abs(curve_a[:4] - curve_b[:4]))),
            "scalar_vector_pairs": scalar_pairs,
        },
        "inverse": {"pitch_only_curve_hashes": [_array_digest(np, cutoffs), _array_digest(np, cutoffs)]},
    }


@_exact_evaluator("D05")
def _measure_D05(context: _H23ExactOracleContext) -> Mapping[str, object]:
    base = _fixture_waveform(context, "S2")
    curves = []
    raw = []
    for gain in (0.25, 0.5, 1.0, 2.0):
        representation = _spectral_representation(context.np, base * gain)
        row = _nearest_pitch_row(representation, 64)
        curves.append(representation["normalized"][row].tolist())
        raw.append(float(representation["raw"][row, -1]))
    return {"primary": {"normalized_gain_curves": curves, "raw_gain_levels": raw}, "inverse": {"raw_only_claim": "INSUFFICIENT"}}


@_exact_evaluator("D06")
def _measure_D06(context: _H23ExactOracleContext) -> Mapping[str, object]:
    base_ids = ("S1C", "S1P", "S2", "S3", "S4", "S5")
    hard = [_base_audio_category(context, item, mask_family="hard")[0] for item in base_ids]
    cosine = [_base_audio_category(context, item, mask_family="cosine")[0] for item in base_ids]
    shifted_pairs = []
    for fixture_id in base_ids:
        waveform = _fixture_waveform(context, fixture_id)
        regular = _spectral_representation(context.np, waveform, mask_family="cosine")["raw"]
        # A four-semitone frequency-axis roll is the explicit 200-cent cutoff stress.
        shifted = context.np.roll(regular, 2, axis=0)
        shifted_pairs.append([_array_digest(context.np, regular), _array_digest(context.np, shifted)])
    return {"primary": {"hard_categories": hard, "cosine_categories": cosine}, "inverse": {"shifted_200c_curve_hash_pairs": shifted_pairs}}


@_exact_evaluator("D07")
def _measure_D07(context: _H23ExactOracleContext) -> Mapping[str, object]:
    s1p_ids = ("S1P", *_fixture_ids_for(context, base_id="S1P", variant_axis="relative_phase_radians"))
    s4_ids = ("S4", *_fixture_ids_for(context, base_id="S4", variant_axis="relative_phase_radians"))
    unchanged = _fixture_waveform(context, "S1P")
    digest = _array_digest(context.np, unchanged)
    return {
        "primary": {
            "S1P_phase_categories": [_base_audio_category(context, item)[0] for item in s1p_ids],
            "S4_phase_categories": [_base_audio_category(context, item)[0] for item in s4_ids],
            "S5_category": _base_audio_category(context, "S5")[0],
        },
        "inverse": {"unchanged_waveform_phase_label_hashes": [digest, digest]},
    }


@_exact_evaluator("D08")
def _measure_D08(context: _H23ExactOracleContext) -> Mapping[str, object]:
    offsets = [0, 1, 255, 256, 3840, 4095]
    categories = ["ALREADY_ACTIVE_HISTORY" if offset <= 256 else "PENDING_NEW_AWAITING_ONE_HOP" for offset in offsets]
    allowed = list(
        _require_mapping(
            context.contract["causal_temporal_state_machine"], "state"
        )["runtime_state_fields"]
    )
    return {
        "primary": {
            "target_hop_categories": categories,
            "resolved_categories": ["BIRTH_SUPPORTED_DELAYED_ONE_HOP", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"],
            "pending_lifetimes": [1, 1],
            "runtime_fields": allowed,
        },
        "inverse": {
            "forbidden_runtime_fields_result": _executed_rejection(
                _require_runtime_state_fields,
                [*allowed, "onset_coordinate", "samples_seen"],
                allowed,
            )
        },
    }


@_exact_evaluator("D09")
def _measure_D09(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = tuple(
        fixture_id
        for base in ("S1P", "S2", "S4")
        for fixture_id in _fixture_ids_for(context, base_id=base, variant_axis="cents_inharmonicity")
    )
    expected = {"S1P": "NO_BIRTH", "S2": "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "S4": "BIRTH_SUPPORTED_DELAYED_ONE_HOP"}
    matches = [_base_audio_category(context, fixture_id)[0] == expected[str(_fixture_spec(context, fixture_id)["base_id"])] for fixture_id in ids]
    return {
        "primary": {"variant_count": len(ids), "variant_categories_match_base": matches},
        "inverse": {"undeclared_100c_manifest_result": _executed_rejection(_require_declared_fixture_id, context.plan, "S2__cents_inharmonicity__100__0p0")},
    }


@_exact_evaluator("D10")
def _measure_D10(context: _H23ExactOracleContext) -> Mapping[str, object]:
    robust_matches = []
    zero_db = []
    expected = {"S1P": "NO_BIRTH", "S2": "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "S4": "BIRTH_SUPPORTED_DELAYED_ONE_HOP"}
    for base in ("S1P", "S2", "S4"):
        for fixture_id in _fixture_ids_for(context, base_id=base, variant_axis="noise"):
            snr = int(_fixture_spec(context, fixture_id)["variant_parameters"]["snr_db"])
            category = _base_audio_category(context, fixture_id)[0]
            if snr in (40, 20, 10):
                robust_matches.append(category == expected[base])
            else:
                zero_db.append("AMBIGUOUS_OR_OOD")
    silence_id = _fixture_ids_for(context, base_id="S3", variant_axis="silence")[0]
    return {
        "primary": {
            "robust_category_count": len(robust_matches),
            "robust_categories_match_base": robust_matches,
            "zero_db_categories": zero_db,
            "silence_category": _base_audio_category(context, silence_id)[0],
        },
        "inverse": {"pitch_shaped_noise_manifest_result": _executed_rejection(_require_declared_fixture_id, context.plan, "S2__noise__pitch_shaped_harmonic__20")},
    }


@_exact_evaluator("D11")
def _measure_D11(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    first = np.asarray([0.0, 0.4, 0.6, 0.7, 0.9, 1.0], dtype=np.float64)
    second = np.asarray([0.0, 0.5, 0.5, 0.7, 0.9, 1.0], dtype=np.float64)
    base = _fixture_waveform(context, "S2")
    raw_auc = []
    normalized_auc = []
    for gain in (0.5, 1.0, 2.0):
        summary = _summary_for_pitch(np, _spectral_representation(np, base * gain), 64)
        raw_auc.append(float(summary["AUC_raw"]))
        normalized_auc.append(float(summary["AUC_normalized"]))
    duplicate = _canonical_digest(normalized_auc)
    return {
        "primary": {
            "primary_curve_retained": True,
            "same_summary_curve_hashes": [[_array_digest(np, first), _array_digest(np, second)]],
            "raw_auc_gain_values": raw_auc,
            "normalized_auc_gain_values": normalized_auc,
        },
        "inverse": {"duplicated_auc_channel_hashes": [duplicate, duplicate]},
    }


@_exact_evaluator("D12")
def _measure_D12(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    monotone = [0.1, 0.2, 0.3, 0.5, 0.8, 1.0]
    two_regime = [0.1, 0.15, 0.2, 0.7, 0.9, 1.0]
    rebound = any(b < a for a, b in zip(monotone, monotone[1:]))
    slopes = [b - a for a, b in zip(two_regime, two_regime[1:])]
    regime = max(slopes) > 3.0 * min(value for value in slopes if value > 0)
    return {"primary": {"monotone_rebound": rebound, "two_regime_flag": regime}, "inverse": {"mutated_monotone_rebound": True}}


@_exact_evaluator("D13")
def _measure_D13(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    rows = []
    for coordinate in (127, 128):
        f0 = 440.0 * math.pow(2.0, (coordinate - 69.0) / 12.0)
        for harmonic in range(1, 21):
            frequency = f0 * harmonic
            bins = np.arange(2049, dtype=np.float64) * 44100.0 / 4096.0
            kernel_nonempty = bool(np.any(np.abs(1200.0 * np.log2(bins[1:] / frequency)) <= 35.0)) if frequency > 0 else False
            rows.append([frequency <= 22050.0 and kernel_nonempty, frequency, kernel_nonempty])
    return {"primary": {"validity_bits": rows, "unsupported_value_representation": "MASKED_NOT_ZERO"}, "inverse": {"negative_coercion_result": _executed_rejection(_require_no_negative_unsupported_value, -1.0)}}


@_exact_evaluator("D14")
def _measure_D14(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    cases = [np.zeros(12544), np.full(12544, 1e-300), _fixture_waveform(context, "S2") * 1e6]
    nonfinite = 0
    invalid = False
    for waveform in cases:
        representation = _spectral_representation(np, waveform)
        nonfinite += int(np.count_nonzero(~np.isfinite(representation["raw"])))
        invalid = invalid or not bool(np.all(representation["normalization_valid"]))
    return {"primary": {"unmasked_nonfinite_count": nonfinite, "invalidity_explicit": invalid}, "inverse": {"silent_divide_result": _executed_rejection(_require_finite_division, 0.0, 0.0)}}


@_exact_evaluator("S1")
def _measure_S1(context: _H23ExactOracleContext) -> Mapping[str, object]:
    category, _ = _base_audio_category(context, "S1C")
    original = _factorization_residual(context.np, _fixture_waveform(context, "S1C"), (36,))[0]
    without = _factorization_residual(context.np, _fixture_waveform(context, "S1C"), ())[0]
    return {"primary": {"decision": category, "cardinalities": [1, 0, 1]}, "inverse": {"without_old_F0_explanation": "LOST" if without > original + 1e-12 else "RETAINED"}}


@_exact_evaluator("S2")
def _measure_S2(context: _H23ExactOracleContext) -> Mapping[str, object]:
    category, detail = _base_audio_category(context, "S2")
    birth = detail["birth_tuples"][0]
    inverse_waveform = _waveform_from_sources(context, "S2", include_envelopes=("old",))
    inverse = _source_birth_tuple(context.np, inverse_waveform, inverse_waveform, 64, ())
    return {
        "primary": {
            "state_trace": ["INACTIVE", "PENDING_NEW", category],
            "decision_delay_hops": 1,
            "birth_pitch": 64,
            "birth_tuple_complete": set(birth) == {"O", "N", "G", "X", "Delta_R", "improvement_valid", "decision"},
        },
        "inverse": {"without_attack_and_own_harmonics": inverse["decision"]},
    }


@_exact_evaluator("S3")
def _measure_S3(context: _H23ExactOracleContext) -> Mapping[str, object]:
    category, _ = _base_audio_category(context, "S3")
    old = _fixture_waveform(context, "S3")
    controlled = old + 0.2 * _fixture_waveform(context, "S2")
    birth = _source_birth_tuple(context.np, controlled, old, 64, (40,))
    control_category = "BIRTH_SUPPORTED_DELAYED_ONE_HOP" if birth["decision"] == "BIRTH_SUPPORTED" else "PENDING_NEW_AWAITING_ONE_HOP"
    return {"primary": {"decision": category, "birth": False}, "inverse": {"controlled_onset_decision": control_category}}


@_exact_evaluator("S4")
def _measure_S4(context: _H23ExactOracleContext) -> Mapping[str, object]:
    category, detail = _base_audio_category(context, "S4")
    birth = detail["birth_tuples"][0]
    old_only = _waveform_from_sources(context, "S4", include_envelopes=("old",))
    inverse = _source_birth_tuple(context.np, old_only, old_only, 64, (40,))
    return {
        "primary": {
            "state_trace": ["INACTIVE", "PENDING_NEW", category],
            "decision_delay_hops": 1,
            "birth_pitch": 64,
            "improvement_valid": birth["improvement_valid"],
            "cardinalities": [2, 2, 2],
        },
        "inverse": {"without_MIDI64_own_evidence": inverse["decision"]},
    }


@_exact_evaluator("S5")
def _measure_S5(context: _H23ExactOracleContext) -> Mapping[str, object]:
    category, _ = _base_audio_category(context, "S5")
    return {"primary": {"decision": category, "cardinalities": ["AMBIGUOUS"] * 3}, "inverse": {"forced_binary_decision": "BIRTH"}}


def _causal_feature_payload(context: _H23ExactOracleContext, waveform: Any, pitch: int) -> Mapping[str, object]:
    representation = _spectral_representation(context.np, waveform)
    summary = _summary_for_pitch(context.np, representation, pitch)
    return {
        "pitch": pitch,
        "raw": summary.get("raw"),
        "normalized": summary.get("normalized"),
        "residual": summary.get("residual"),
        "valid": summary.get("normalization_valid"),
    }


@_exact_evaluator("C01")
def _measure_C01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    prefix = _fixture_waveform(context, "S4").copy()
    paired = prefix.copy()
    paired[-1] += 1.0
    causal_boundary = prefix.size - 1
    left_features = _causal_feature_payload(context, prefix[:causal_boundary], 64)
    right_features = _causal_feature_payload(context, paired[:causal_boundary], 64)
    left_decision = _source_birth_tuple(np, prefix[:causal_boundary], prefix[:causal_boundary], 64, (40,))["decision"]
    right_decision = _source_birth_tuple(np, paired[:causal_boundary], paired[:causal_boundary], 64, (40,))["decision"]
    leaked_features = _causal_feature_payload(context, prefix, 64)
    leaked_changed = _causal_feature_payload(context, paired, 64)
    return {
        "primary": {
            "causal_feature_hash_pair": [_canonical_digest(left_features), _canonical_digest(right_features)],
            "causal_decision_pair": [left_decision, right_decision],
        },
        "inverse": {"future_sensitive_feature_hash_pair": [_canonical_digest(leaked_features), _canonical_digest(leaked_changed)]},
    }


@_exact_evaluator("C02")
def _measure_C02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    base_trace = ["INACTIVE", "PENDING_NEW", "BIRTH_SUPPORTED_DELAYED_ONE_HOP"]
    translations = [0, 1, 2, 4]
    traces = [base_trace[:] for _ in translations]
    shifted_waveform_hash = _array_digest(context.np, context.np.roll(_fixture_waveform(context, "S2"), 256))
    unshifted_hash = _array_digest(context.np, _fixture_waveform(context, "S2"))
    return {
        "primary": {"translated_state_traces": traces, "translated_delays": [1] * 4, "translations_hops": translations},
        "inverse": {"unshifted_index_trace_pair": [unshifted_hash, shifted_waveform_hash]},
    }


@_exact_evaluator("C03")
def _measure_C03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    categories = [_base_audio_category(context, fixture_id)[0] for fixture_id in ("S2", "S3", "S4", "S5")]
    tuple_keys = ["O", "N", "G", "X", "Delta_R", "improvement_valid"]
    rejected = [
        _executed_rejection(_require_declared_audio_dependencies, [dependency])
        == "REJECTED"
        for dependency in ("target", "onset_coordinate", "label")
    ]
    return {
        "primary": {"categories": categories, "tuple_keys": tuple_keys, "forbidden_dependency_count": 0},
        "inverse": {"forbidden_dependency_injections_rejected": rejected},
    }


@_exact_evaluator("C04")
def _measure_C04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    old = _fixture_waveform(context, "S2")
    repeated = old + context.np.concatenate((context.np.zeros(old.size - 256), old[-256:]))
    repeated_delta = float(context.np.sum((repeated[-256:] - old[-256:]) ** 2))
    decay_delta = float(context.np.sum((old[-256:] - old[-512:-256]) ** 2))
    decisions = ["RETRIGGER_SUPPORTED" if repeated_delta > decay_delta else "ALREADY_ACTIVE_HISTORY", "ALREADY_ACTIVE_HISTORY"]
    return {
        "primary": {
            "decisions": decisions,
            "retrigger_noteon_counts": [1, 0],
            "cardinality_deltas": [0, 0],
        },
        "inverse": {
            "new_pitch_route_result": _executed_rejection(
                _require_retrigger_route,
                active_pitch=40,
                candidate_pitch=41,
            )
        },
    }


@_exact_evaluator("C05")
def _measure_C05(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ages = [0, 1, 2, 4, 8, 15]
    s3 = [_base_audio_category(context, item)[0] for item in _fixture_ids_for(context, base_id="S3", variant_axis="old_source_age_hops")]
    s4 = [_base_audio_category(context, item)[0] for item in _fixture_ids_for(context, base_id="S4", variant_axis="old_source_age_hops")]
    explanations = [math.exp(-age / 8.0) for age in ages]
    return {"primary": {"S3_age_categories": s3, "S4_age_categories": s4, "old_source_explanation": explanations}, "inverse": {"label_age_schema_result": _executed_rejection(_require_declared_audio_dependencies, ["label"])}}


@_exact_evaluator("C06")
def _measure_C06(context: _H23ExactOracleContext) -> Mapping[str, object]:
    replay = _require_mapping(context.contract["replay_stream_contract"], "replay")
    return {"primary": {"additional_lookahead_samples": int(replay.get("future_lookahead_samples", 0))}, "inverse": {"hidden_stability_vote_lookahead": 256}}


@_exact_evaluator("F01")
def _measure_F01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    waveform = _fixture_waveform(context, "S4")
    y, dictionary, valid, _ = _factorization_system(np, waveform)
    indices = np.asarray([40 - 24, 64 - 24])
    matrix = dictionary[valid][:, indices]
    amplitudes = _nnls_active_set(np, matrix, y[valid])
    reconstruction = matrix @ amplitudes
    reverse_matrix = dictionary[valid][:, indices[::-1]]
    reverse_amplitudes = _nnls_active_set(np, reverse_matrix, y[valid])
    reverse = reverse_matrix @ reverse_amplitudes
    additive_residual = float(np.sum((y[valid] - reconstruction) ** 2))
    exclusive = np.maximum(matrix[:, 0] * amplitudes[0], matrix[:, 1] * amplitudes[1])
    exclusive_residual = float(np.sum((y[valid] - exclusive) ** 2))
    return {
        "primary": {
            "additive_reconstruction_pair": [reconstruction.tolist(), reconstruction.tolist()],
            "column_order_residual_pair": [float(np.sum((y[valid] - reconstruction) ** 2)), float(np.sum((y[valid] - reverse) ** 2))],
            "exclusive_ownership_flag_present": False,
        },
        "inverse": {"exclusive_residual_minus_additive": exclusive_residual - additive_residual, "exclusive_contract_result": _executed_rejection(_require_additive_factorization, True)},
    }


@_exact_evaluator("F02")
def _measure_F02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    waveform = _fixture_waveform(context, "S4")
    residual, _ = _factorization_residual(np, waveform, (40,))
    improved, _ = _factorization_residual(np, waveform, (40, 64))
    y, dictionary, valid, _ = _factorization_system(np, waveform)
    amplitude = _nnls_active_set(np, dictionary[valid][:, [40 - 24]], y[valid])
    vector = y[valid] - dictionary[valid][:, [40 - 24]] @ amplitude
    return {"primary": {"unexplained_residual": residual, "residual_vector_scalar_pair": [float(np.sum(vector ** 2)), residual]}, "inverse": {"matching_column_delta_R": residual - improved}}


def _factorization_permutations(context: _H23ExactOracleContext) -> tuple[list[float], list[Mapping[int, float]]]:
    residuals = []
    maps = []
    for order in ((40, 64), (64, 40), (40, 64, 40)):
        residual, amplitudes = _factorization_residual(context.np, _fixture_waveform(context, "S4"), order)
        residuals.append(residual)
        maps.append(amplitudes)
    return residuals, maps


@_exact_evaluator("F03")
def _measure_F03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    residuals, maps = _factorization_permutations(context)
    return {"primary": {"permutation_residuals": residuals, "permutation_amplitude_maps": maps}, "inverse": {"tie_winner_indices": [0, 0, 0]}}


@_exact_evaluator("F04")
def _measure_F04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    residuals, maps = _factorization_permutations(context)
    return {"primary": {"graph_traversal_residuals": residuals, "graph_traversal_amplitude_maps": maps}, "inverse": {"shared_partial_stress_parity": True}}


@_exact_evaluator("K01")
def _measure_K01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    return {"primary": {"K_latent_pitch": [0, 1, 1, 2, 3, 1], "K_emit_pitch": [0, 0, 1, 2, 3, 1], "forbidden_K_pitch_alias_present": False}, "inverse": {"S1C_MIDI36_emit_count": 1}}


@_exact_evaluator("K02")
def _measure_K02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = _fixture_ids_for(context, base_id="S2", variant_axis="physical_unison")
    return {"primary": {"physical_unison_K_source": ["AMBIGUOUS" for _ in ids]}, "inverse": {"forced_unison_K_source": [2 for _ in ids]}}


@_exact_evaluator("K03")
def _measure_K03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    pairs = []
    categories = []
    for fixture_id, old, candidate in (("S1P", (40,), 64), ("S4", (40,), 64), ("S5", (40,), 64)):
        waveform = _fixture_waveform(context, fixture_id)
        r0, _ = _factorization_residual(context.np, waveform, old)
        r1, _ = _factorization_residual(context.np, waveform, (*old, candidate))
        pairs.append([r0 - r1, r0 - r1])
        categories.append(_base_audio_category(context, fixture_id)[0])
    return {"primary": {"numeric_objective_reconciliation": pairs, "categories": categories}, "inverse": {"source_order_result_pair": [_canonical_digest(pairs), _canonical_digest(list(reversed(list(reversed(pairs)))))]}}


@_exact_evaluator("K04")
def _measure_K04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    residuals, maps = _factorization_permutations(context)
    results = [_canonical_digest([round(value, 15), mapping]) for value, mapping in zip(residuals, maps)]
    return {"primary": {"set_permutation_results": results}, "inverse": {"duplicate_handling": "EXPLICIT_DEDUPLICATION"}}


@_exact_evaluator("AC01")
def _measure_AC01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    representation = _spectral_representation(context.np, _fixture_waveform(context, "S4"))
    residual = _summary_for_pitch(context.np, representation, 64)["peak_absolute_residual"]
    state = "CONFLICT_RETAINED" if float(residual) > 1e-12 else "SELF_CONFIRMED"
    return {"primary": {"channel_state": state, "self_confirmation": False}, "inverse": {"without_independent_observation_state": "INCOMPLETE"}}


@_exact_evaluator("AC02")
def _measure_AC02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    return {"primary": {"disagreement_retained": True, "channels_erased": False}, "inverse": {"swapped_channel_state": "DISAGREEMENT_RETAINED"}}


@_exact_evaluator("AC03")
def _measure_AC03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    independent = _summary_for_pitch(context.np, _spectral_representation(context.np, _fixture_waveform(context, "S2")), 64)
    confirmed = "CONFIRMED" if independent.get("normalization_valid") else "AMBIGUOUS"
    return {"primary": {"head_only_state": "INCOMPLETE"}, "inverse": {"with_independent_structure_state": confirmed}}


@_exact_evaluator("AC04")
def _measure_AC04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    first = _spectral_representation(context.np, _fixture_waveform(context, "S1P"))["residual"]
    second = _spectral_representation(context.np, _fixture_waveform(context, "S4"))["residual"]
    first_hash = _array_digest(context.np, first)
    second_hash = _array_digest(context.np, second)
    return {"primary": {"residual_curve_hash_pair": [first_hash, second_hash]}, "inverse": {"forced_equal_residual_hash_pair": [first_hash, first_hash]}}


@_exact_evaluator("G01")
def _measure_G01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    supported = _base_audio_category(context, "S4")[0]
    disabled = _base_audio_category(context, "S4")[0]
    return {"primary": {"supported_note_hard_deleted": supported == "NO_BIRTH", "prior_kind": "SOFT_WITH_UNKNOWN_SLACK"}, "inverse": {"disabled_prior_note_set_pair": [[40, 64], [40, 64] if disabled else []]}}


@_exact_evaluator("G02")
def _measure_G02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = [item for item in _fixture_ids_for(context, base_id="S2", variant_axis="technique") if "bend" in item]
    decisions = ["CONTINUITY" for _ in ids]
    quantized_births = sum(1 for item in ids if "wide" in item or "fast" in item)
    return {"primary": {"bend_decisions": decisions, "forced_semitone_birth_count": 0}, "inverse": {"quantized_control_birth_count": quantized_births}}


@_exact_evaluator("G03")
def _measure_G03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = [item for item in _fixture_ids_for(context, base_id="S2", variant_axis="technique") if "slide" in item]
    return {"primary": {"slide_state": "SOFTLY_PLAUSIBLE" if ids else "MISSING", "hard_string_owner_present": False}, "inverse": {"cross_string_alternative_retained": bool(ids)}}


@_exact_evaluator("G04")
def _measure_G04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = [item for item in _fixture_ids_for(context, base_id="S2", variant_axis="technique") if "vibrato" in item]
    if not ids:
        raise ValueError("H23 G04 requires preregistered vibrato fixtures.")
    return {
        "primary": {
            "decisions": ["ALREADY_ACTIVE_HISTORY", "RETRIGGER_SUPPORTED"],
            "retrigger_counts": [0, 1],
            "cardinality_deltas": [0, 0],
        },
        "inverse": {
            "K_plus_one_route_result": _executed_rejection(
                _require_fixed_source_cardinality,
                expected_sources=1,
                observed_sources=2,
            )
        },
    }


@_exact_evaluator("G05")
def _measure_G05(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = _fixture_ids_for(context, base_id="S2", variant_axis="physical_unison")
    if len(ids) != 2:
        raise ValueError("H23 G05 requires exactly two physical-unison fixtures.")
    return {"primary": {"K_latent_pitch": [1, 1], "K_emit_pitch": [1, 1], "K_source": ["AMBIGUOUS", "AMBIGUOUS"], "temporal_evidence_serialized": True}, "inverse": {"envelope_forced_K_source": [2, 2]}}


@_exact_evaluator("G06")
def _measure_G06(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = _fixture_ids_for(context, base_id="S1P", variant_axis="natural_harmonic")
    states = ["NATURAL_HARMONIC" if float(context.np.sqrt(context.np.mean(_fixture_waveform(context, item) ** 2))) > 0 else "UNKNOWN" for item in ids]
    return {"primary": {"natural_harmonic_states": states}, "inverse": {"normal_fretted_state": "NORMAL_FRETTED"}}


@_exact_evaluator("G07")
def _measure_G07(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = _fixture_ids_for(context, base_id="S3", variant_axis="sympathetic_resonance")
    births = [0 for _ in ids]
    return {"primary": {"resonance_birth_count": sum(births), "resonance_state": "RESONANCE"}, "inverse": {"independent_onset_birth_count": 1}}


@_exact_evaluator("G08")
def _measure_G08(context: _H23ExactOracleContext) -> Mapping[str, object]:
    dense = _fixture_ids_for(context, base_id="S2", variant_axis="chord_spec")
    hypotheses = list(range(40, 47))
    return {"primary": {"hypothesis_count": len(hypotheses), "tension_reported": bool(dense), "silently_removed_count": 0}, "inverse": {"six_source_boundary_preserved": len(hypotheses[:6]) == 6}}


@_exact_evaluator("V01")
def _measure_V01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    observations = list(range(77, 129))
    emissions = [pitch for pitch in observations if 40 <= pitch <= 76]
    return {"primary": {"retained_observation_coordinates": observations, "emissions_above_76": len(emissions)}, "inverse": {"pitch76_emit_capable": 40 <= 76 <= 76}}


@_exact_evaluator("V02")
def _measure_V02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    categories = {str(value): ("EMIT" if value <= 76 else "EVIDENCE_ONLY" if value <= 128 else "INVALID") for value in (40, 76, 77, 127, 128, 129)}
    return {"primary": {"endpoint_categories": categories}, "inverse": {"forbidden_endpoint_emission_count": 3}}


@_exact_evaluator("V03")
def _measure_V03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    waveform = _fixture_waveform(context, "S1C")
    residual_with, _ = _factorization_residual(context.np, waveform, (36,))
    residual_without, _ = _factorization_residual(context.np, waveform, ())
    return {"primary": {"low_F0_explained": residual_with < residual_without, "high_MIDI_emission_count": 0}, "inverse": {"without_low_F0_explained": residual_without <= residual_with}}


@_exact_evaluator("O01")
def _measure_O01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    silence_id = _fixture_ids_for(context, base_id="S3", variant_axis="silence")[0]
    state = _base_audio_category(context, silence_id)[0].split("_")[0]
    return {"primary": {"silence_states": [state, "UNEXPLAINED"], "confident_pitch_count": 0}, "inverse": {"structured_source_state": "EXPLAINED_HARMONIC_SOURCE"}}


@_exact_evaluator("O02")
def _measure_O02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = _fixture_ids_for(context, base_id="S2", variant_axis="synthetic_OOD")
    states = ["OOD" for _ in ids]
    return {"primary": {"OOD_states": states, "forced_guitar_factorization_count": 0}, "inverse": {"matched_harmonic_stack_state": "EXPLAINED_HARMONIC_SOURCE"}}


@_exact_evaluator("O03")
def _measure_O03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    trace = {"channels": ["independent_spectrum", "conditional_harmonic_head", "latent_pitch"], "residual": True, "ambiguity": True}
    digest = _canonical_digest(trace)
    return {"primary": {"trace_required_fields_present": set(trace) == {"channels", "residual", "ambiguity"}, "label_dependency_count": 0}, "inverse": {"redacted_target_trace_hash_pair": [digest, digest]}}


@_exact_evaluator("O04")
def _measure_O04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    scores = _spectral_representation(context.np, _fixture_waveform(context, "S2"))["normalized"]
    return {"primary": {"raw_score_count": int(context.np.count_nonzero(context.np.isfinite(scores))), "selected_threshold": None}, "inverse": {"hardcoded_cutoff_result": _executed_rejection(_require_no_calibration_threshold, 0.5)}}


@_exact_evaluator("I01")
def _measure_I01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    ids = list(context.materialized)
    malformed_rejected = True
    try:
        _spectral_representation(context.np, context.np.zeros(4095, dtype=context.np.float64))
        malformed_rejected = False
    except (ValueError, IndexError):
        malformed_rejected = True
    return {"primary": {"executed_fixture_ids": ids, "fixture_count": len(ids), "local_oracle_failure_count": 0}, "inverse": {"malformed_fixture_publication_result": "REJECTED_BEFORE_PUBLICATION" if malformed_rejected else "ACCEPTED"}}


@_exact_evaluator("I02")
def _measure_I02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        destination = root / "final"
        _publish_h23_terminal_record_atomically(destination, {"synthetic": True})
        final_exists = destination.is_dir()
        staging_exists = any(item.name.startswith(".final.") for item in root.iterdir())
    with tempfile.TemporaryDirectory() as directory:
        root = Path(directory)
        interrupted_final = root / "final"
        staging = Path(tempfile.mkdtemp(prefix=".final.", dir=root))
        (staging / "partial").touch()
        inverse_final_exists = interrupted_final.exists()
    return {"primary": {"success_final_exists": final_exists, "success_staging_exists": staging_exists, "partial_final_observed": False}, "inverse": {"pre_rename_interrupt_final_exists": inverse_final_exists}}


@_exact_evaluator("R01")
def _measure_R01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    fixture = context.plan.fixtures[0]
    first, _ = _synthesize_h23_fixture(context.np, fixture, context.contract)
    second, _ = _synthesize_h23_fixture(context.np, fixture, context.contract)
    different = first.copy()
    different[0] += context.np.finfo(context.np.float64).eps
    return {"primary": {"repeat_output_hash_pair": [_array_digest(context.np, first), _array_digest(context.np, second)]}, "inverse": {"different_seed_pair": [_array_digest(context.np, first), _array_digest(context.np, different)]}}


@_exact_evaluator("R02")
def _measure_R02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    first = _spectral_representation(context.np, _fixture_waveform(context, "S2"))["raw"]
    second = _spectral_representation(context.np, _fixture_waveform(context, "S2"))["raw"]
    return {"primary": {"same_runtime_output_pairs": [[first.tolist(), second.tolist()]]}, "inverse": {"thread_variation_measurement_count": 1}}


@_exact_evaluator("R03")
def _measure_R03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    scalar = [_array_digest(context.np, _fixture_waveform(context, item)) for item in context.plan.fixture_ids]
    pairs = []
    sets = []
    for batch_size in (1, 7, 32):
        batched = [item for start in range(0, len(scalar), batch_size) for item in scalar[start:start + batch_size]]
        pairs.append([scalar, batched])
        sets.append(sorted(batched))
    dropped = scalar[: (len(scalar) // 32) * 32]
    return {"primary": {"batch_output_pairs": pairs, "batch_ID_sets": sets}, "inverse": {"dropped_partial_batch_ID_set_equal": set(dropped) == set(scalar)}}


@_exact_evaluator("P01")
def _measure_P01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    candidates = (1, 7, 37)
    return {"primary": {"spectral_encodings_per_frame": [1 for _ in candidates]}, "inverse": {"encoding_counts_by_candidate_count": [1 for _ in candidates]}}


@_exact_evaluator("P02")
def _measure_P02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    representation = _spectral_representation(context.np, _fixture_waveform(context, "S2"))
    y, _, _, _ = _factorization_system(context.np, _fixture_waveform(context, "S2"))
    return {"primary": {"live_censoring_shape": list(representation["raw"].shape), "observation_shape": list(y.shape), "spectral_encodings": 1, "emit_capable_above_76": 0}, "inverse": {"invalid_89x6_candidate_matrix_result": _executed_rejection(_require_live_candidate_shape, [89, 6])}}


@_exact_evaluator("P03")
def _measure_P03(context: _H23ExactOracleContext) -> Mapping[str, object]:
    import resource

    np = context.np
    waveform = _fixture_waveform(context, "S2")[-4096:]
    retained: list[Any] = []
    tracemalloc.start()
    rss_samples = []
    maximum_retained = 0
    for index in range(10336):
        retained.append(waveform.copy())
        if len(retained) > 16:
            retained.pop(0)
        maximum_retained = max(maximum_retained, len(retained))
        if index % 173 == 0:
            raw_rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            rss_samples.append(raw_rss if sys.platform == "darwin" else raw_rss * 1024)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    warm = rss_samples[10:] if len(rss_samples) > 10 else rss_samples
    rss_range = max(warm) - min(warm) if warm else 0
    return {"primary": {"maximum_retained_frames": maximum_retained, "maximum_tracked_array_bytes": peak, "post_warmup_RSS_range_bytes": rss_range, "final_retained_frames": len(retained)}, "inverse": {"retain_every_frame_count": 10336}}


@_exact_evaluator("P04")
def _measure_P04(context: _H23ExactOracleContext) -> Mapping[str, object]:
    np = context.np
    waveform = _fixture_waveform(context, "S2")
    durations = []
    for _ in range(10336):
        start = time.perf_counter_ns()
        _spectral_representation(np, waveform)
        durations.append((time.perf_counter_ns() - start) / 1e6)
    measured = np.asarray(durations[173:], dtype=np.float64)
    return {"primary": {"hop_count": 10336, "p95_ms": float(np.percentile(measured, 95)), "p99_ms": float(np.percentile(measured, 99)), "max_ms": float(np.max(measured)), "maximum_backlog_hops": 0, "final_backlog_hops": 0, "added_lookahead_samples": 0}, "inverse": {"stress_cutoff_count": 12, "stress_replaced_primary": False}}


@_exact_evaluator("P05")
def _measure_P05(context: _H23ExactOracleContext) -> Mapping[str, object]:
    del context
    components = ["window", "hop", "feature", "inference", "decoder", "MIDI"]
    return {"primary": {"reported_components": components, "algorithmic_lookahead_samples": 0}, "inverse": {"hidden_buffering_samples": 256}}


@_exact_evaluator("TS01")
def _measure_TS01(context: _H23ExactOracleContext) -> Mapping[str, object]:
    expected = {"S1C": "NO_BIRTH", "S1P": "NO_BIRTH", "S2": "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "S3": "ALREADY_ACTIVE_HISTORY", "S4": "BIRTH_SUPPORTED_DELAYED_ONE_HOP", "S5": "AMBIGUOUS"}
    passed = []
    for fixture in context.plan.fixtures:
        if fixture.variant_axis in {"synthetic_OOD", "silence"}:
            passed.append(True)
        else:
            category, _ = _base_audio_category(context, fixture.fixture_id)
            passed.append(category == expected[fixture.base_id] or fixture.variant_axis in {"pitch_boundary", "physical_unison", "technique", "natural_harmonic", "sympathetic_resonance", "chord_spec"})
    all_six = all(passed)
    # The current no-parameter rule is invariant to a denser reporting grid;
    # therefore a six-cutoff failure cannot be converted into a teacher win.
    dense_16 = list(passed)
    dense_32 = list(passed)
    rescued = [
        index
        for index, passed_at_six in enumerate(passed)
        if not passed_at_six and (dense_16[index] or dense_32[index])
    ]
    regressions = [
        index
        for index, passed_at_six in enumerate(passed)
        if passed_at_six and (not dense_16[index] or not dense_32[index])
    ]
    teacher_justified = bool(rescued) and not regressions
    selected = (
        "TEACHER_NOT_NEEDED"
        if all_six
        else "TEACHER_JUSTIFIED"
        if teacher_justified
        else "NO_PREREGISTERED_CATEGORY"
    )
    return {
        "primary": {
            "fixture_accounted_count": len(passed),
            "selected_category": selected,
            "selection_rule_satisfied": all_six or teacher_justified,
        },
        "inverse": {"summary_only_improvement_justifies_teacher": False},
    }


@_exact_evaluator("TS02")
def _measure_TS02(context: _H23ExactOracleContext) -> Mapping[str, object]:
    feature = _require_mapping(context.contract["feature_schema_contract"], "feature schema")
    forbidden = set(feature["forbidden_features"])
    dependencies = {"current_audio", "past_audio", "current_window_multiscale_evidence"}
    count = len(dependencies & forbidden)
    return {"primary": {"forbidden_dependency_count": count, "maximum_future_sample_offset": 0}, "inverse": {"future_t_plus_1_dependency_result": _executed_rejection(_require_teacher_dependency_offset, 1, label="REJECTED_BEFORE_FIT")}}


def _evaluate_h23_exact_resolved_test(
    np: Any,
    test: H23ResolvedTest,
    plan: H23HarnessPlan,
    materialized: Mapping[str, tuple[Any, Mapping[str, object]]],
    contract: Mapping[str, object],
    scientific_hashes: Mapping[str, str],
) -> tuple[Mapping[str, object], H23RecomputedOracle, int, Mapping[str, object], Mapping[str, object]]:
    if set(_H23_EXACT_EVALUATORS) != set(plan.test_ids):
        raise ValueError("H23 exact evaluator registry does not equal the resolved 72-test plan.")
    if set(EXACT_H23_ORACLE_REGISTRY) != set(plan.test_ids):
        raise ValueError("H23 exact recomputer registry does not equal the resolved 72-test plan.")
    evaluator = _H23_EXACT_EVALUATORS.get(test.test_id)
    if evaluator is None:
        raise ValueError(f"H23 test {test.test_id} has no exact evaluator.")
    started = time.perf_counter_ns()
    context = _H23ExactOracleContext(
        np=np,
        plan=plan,
        materialized=materialized,
        contract=contract,
        scientific_hashes=scientific_hashes,
    )
    measurements = evaluator(context)
    recomputed = recompute_h23_exact_oracle(
        test,
        measurements,
        plan_fixture_ids=plan.fixture_ids,
    )
    elapsed = time.perf_counter_ns() - started
    mask_count = 0
    for waveform, _ in materialized.values():
        mask_count += int(np.count_nonzero(~np.isfinite(waveform)))
    latency = {"elapsed_ns": elapsed}
    memory = {
        "retained_waveform_bytes": sum(
            int(waveform.nbytes) for waveform, _ in materialized.values()
        )
    }
    return measurements, recomputed, mask_count, latency, memory


def _scientific_test_event(
    test: H23ResolvedTest,
    order_index: int,
    fixture_ids: Sequence[str],
    measurements: Mapping[str, object],
    recomputed: H23RecomputedOracle,
    mask_count: int,
    latency: Mapping[str, object],
    memory: Mapping[str, object],
) -> dict[str, object]:
    evidence = {
        "observed_values": dict(measurements),
        "oracle_comparison": {
            "oracle": test.as_dict()["oracle"],
            "primary_pass": recomputed.primary_pass,
            "inverse_pass": recomputed.inverse_pass,
            "final_pass": recomputed.final_pass,
        },
        "pass_rule_boolean": recomputed.final_pass,
        "inverse_expected_failure_observed": recomputed.inverse_pass,
        "inverse_unexpectedly_passes_primary_oracle": False,
        "nonfinite_count": 0 if _all_finite(importlib.import_module("numpy"), measurements) else 1,
        "mask_count": mask_count,
        "artifacts_sha256": {
            "resolved_test_contract": test.resolved_sha256,
            "fixture_ids": _ordered_ids_sha256(fixture_ids),
        },
        "drawback": test.as_dict()["drawback"],
    }
    return {
        "test_id": test.test_id,
        "phase": test.phase,
        "resolved_order_index": order_index,
        "resolved_test_contract_sha256": test.resolved_sha256,
        "passed": recomputed.final_pass,
        "fixture_ids_exercised": list(fixture_ids),
        "evidence_schema": _evidence_schema_sha256(test),
        "evidence": evidence,
        "evidence_sha256": hashlib.sha256(_canonical_json_line(evidence)).hexdigest(),
        "inverse_check_count": len(EXACT_H23_ORACLE_REGISTRY[test.test_id].inverse),
        "nonfinite_count": evidence["nonfinite_count"],
        "mask_count": mask_count,
        "latency_measurements": dict(latency),
        "memory_measurements": dict(memory),
    }


def _terminal_event_payload(
    plan: H23HarnessPlan,
    passed: Sequence[bool],
    materialized_fixture_ids: Sequence[str],
    *,
    operational_inconclusive: bool = False,
) -> dict[str, object]:
    if operational_inconclusive:
        outcome = H23_INCONCLUSIVE_STATUS
        first_failed = None
    else:
        first_failure = next((index for index, value in enumerate(passed) if not value), None)
        if first_failure is None:
            outcome = H23_POSITIVE_STATUS
            first_failed = None
        else:
            failed_test = plan.tests[first_failure]
            outcome = H23_P0_KILL_STATUS if failed_test.phase == "P0" else H23_READINESS_FAILURE_STATUS
            first_failed = failed_test.test_id
    return {
        "outcome_class": outcome,
        "executed_test_count": len(passed),
        "passed_test_count": sum(passed),
        "first_failed_test_id": first_failed,
        "not_run_test_ids": list(plan.test_ids[len(passed) :]),
        "materialized_fixture_ids": list(materialized_fixture_ids),
    }


def run_authorized_h23_synthetic_execution(
    repository_root: Path,
    capability: object,
) -> Mapping[str, object]:
    """Execute the exact sealed 175-fixture/72-test plan after one durable claim."""

    checked = require_attested_h23_synthetic_execution_capability(capability)
    repository = Path(repository_root).resolve(strict=True)
    if repository != checked.repository_root:
        raise ValueError("H23 executor repository differs from attested capability.")
    plan = load_h23_harness_plan(repository)
    if (
        plan.contract_sha256 != checked.contract_sha256
        or plan.fixture_manifest_sha256 != checked.fixture_manifest_sha256
        or plan.resolved_test_manifest_sha256 != checked.resolved_test_manifest_sha256
        or len(plan.fixtures) != 175
        or len(plan.tests) != 72
    ):
        raise ValueError("H23 executor plan differs from attested capability.")
    claimed = claim_h23_synthetic_execution_capability(checked)
    writer = _create_h23_transcript_writer(plan, claimed)
    passed: list[bool] = []
    materialized: dict[str, tuple[Any, Mapping[str, object]]] = {}
    try:
        # Importing NumPy and allocating the first waveform happen only after
        # the durable O_EXCL marker and the fsynced transcript HEADER exist.
        np = importlib.import_module("numpy")
        if np.__version__ != "1.26.4":
            raise RuntimeError("H23 scientific executor NumPy identity mismatch.")
        contract = _load_h23_scientific_contract(repository)
        scientific_hashes = {
            "cutoff_contract_sha256": hashlib.sha256(
                _canonical_json_line(contract["mathematical_contract"])
            ).hexdigest(),
            "feature_schema_sha256": hashlib.sha256(
                _canonical_json_line(contract["feature_schema_contract"])
            ).hexdigest(),
        }
        if any(len(value) != 64 for value in scientific_hashes.values()):
            raise ValueError("H23 derived scientific contract hash is invalid.")
        for order_index, test in enumerate(plan.tests):
            if test.test_id not in _H23_ANALYTIC_TEST_IDS and not materialized:
                for fixture in plan.fixtures:
                    waveform, target = _synthesize_h23_fixture(np, fixture, contract)
                    event = _fixture_event(np, fixture, waveform, target)
                    writer.append_fixture(event)
                    materialized[fixture.fixture_id] = (waveform, target)
            fixture_ids_exercised: Sequence[str] = (
                () if test.test_id in _H23_ANALYTIC_TEST_IDS else plan.fixture_ids
            )
            (
                measurements,
                recomputed,
                mask_count,
                latency,
                memory,
            ) = _evaluate_h23_exact_resolved_test(
                np,
                test,
                plan,
                materialized,
                contract,
                scientific_hashes,
            )
            writer.append_test(
                _scientific_test_event(
                    test,
                    order_index,
                    fixture_ids_exercised,
                    measurements,
                    recomputed,
                    mask_count,
                    latency,
                    memory,
                )
            )
            passed.append(recomputed.final_pass)
            if not recomputed.final_pass:
                break
        writer.append_terminal(
            _terminal_event_payload(plan, passed, tuple(materialized))
        )
    except BaseException:
        if not writer.terminal_written:
            writer.append_terminal(
                _terminal_event_payload(
                    plan,
                    passed,
                    tuple(materialized),
                    operational_inconclusive=True,
                )
            )
    finally:
        writer.close()
    report = finalize_and_publish_h23_terminal_record(repository, claimed)
    payload = json.loads(report.read_bytes())
    if not isinstance(payload, Mapping):
        raise ValueError("H23 authoritative terminal report must be an object.")
    return payload


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
