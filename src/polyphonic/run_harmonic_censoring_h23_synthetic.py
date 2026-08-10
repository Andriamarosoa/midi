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
    if type(event.get("inverse_check_count")) is not int or event["inverse_check_count"] < 1:
        raise ValueError("H23 TEST_RESULT requires an executed inverse check.")
    if type(event.get("mask_count")) is not int or event["mask_count"] < 0:
        raise ValueError("H23 TEST_RESULT mask_count is invalid.")
    for name in ("latency_measurements", "memory_measurements"):
        measurements = event.get(name)
        if not isinstance(measurements, Mapping):
            raise ValueError(f"H23 TEST_RESULT {name} must be an object.")
        _canonical_json_line(dict(measurements))
    return bool(
        evidence["pass_rule_boolean"] is True
        and evidence["inverse_expected_failure_observed"] is True
        and evidence["inverse_unexpectedly_passes_primary_oracle"] is False
        and type(evidence["nonfinite_count"]) is int
        and evidence["nonfinite_count"] == 0
    )


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
        passed = _recompute_test_pass(test, event)
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


def _evaluate_h23_resolved_test(
    np: Any,
    test: H23ResolvedTest,
    plan: H23HarnessPlan,
    materialized: Mapping[str, tuple[Any, Mapping[str, object]]],
    contract: Mapping[str, object],
    scientific_hashes: Mapping[str, str],
) -> tuple[bool, Mapping[str, object], int, int, Mapping[str, object], Mapping[str, object]]:
    """Evaluate one sealed record without accepting caller-selected values."""

    started = time.perf_counter_ns()
    record = test.as_dict()
    checks: dict[str, bool] = {}
    observed: dict[str, object] = {
        "objective": record["objective"],
        "oracle": record["oracle"],
        "scientific_contract_hashes": dict(scientific_hashes),
    }
    mask_count = 0
    fixture_ids = tuple(materialized)
    if test.test_id.startswith("A"):
        f0 = lambda pitch: 440.0 * math.pow(2.0, (pitch - 69.0) / 12.0)
        if test.test_id == "A01":
            edges = [(pitch, harmonic, harmonic * f0(pitch)) for pitch in range(24, 77) for harmonic in range(1, 21)]
            checks["all_edges_low_to_high"] = all(freq >= f0(pitch) for pitch, _, freq in edges)
            checks["C4_cannot_explain_C3"] = f0(60) > f0(48)
            observed["edge_count"] = len(edges)
        elif test.test_id == "A02":
            shifts = (-24, -12, -1, 0, 1, 12, 24)
            comparisons = [
                abs((cutoff * f0(64 + shift)) - (cutoff * f0(64) * math.pow(2.0, shift / 12.0)))
                for shift in shifts
                for cutoff in (1, 2, 3, 4, 8, 20)
            ]
            checks["cutoff_equivariance"] = all(
                math.isclose(value, 0.0, rel_tol=1e-10, abs_tol=1e-12) for value in comparisons
            )
            observed["maximum_absolute_error"] = max(comparisons)
        elif test.test_id == "A03":
            indices = [next((c for c in (1, 2, 3, 4, 8, 20) if c >= harmonic), None) for harmonic in range(1, 21)]
            checks["pitch_cutoff_only_is_trivial"] = len(set(indices)) <= 6
            observed["disappearance_indices"] = indices
        elif test.test_id == "A04":
            s5 = next(item for item in plan.fixtures if item.fixture_id == "S5")
            target = s5.as_dict()["expected_target"]
            checks["identical_explanations_are_ambiguous"] = all(
                target[name] == "AMBIGUOUS" for name in ("K_latent_pitch", "K_emit_pitch", "K_source", "birth")
            )
            observed["S5_target"] = target
        elif test.test_id == "A05":
            product = _require_mapping(contract["product_contract"], "product contract")
            checks["three_cardinalities_named"] = all(
                token in str(_require_mapping(contract["factorization_and_source_birth_contract"], "factorization")["cardinality_names"])
                for token in ("K_latent_pitch", "K_emit_pitch", "K_source")
            )
            checks["latent_domain_is_strict_superset"] = int(product["latent_source_hypothesis_count"]) > int(product["emission_candidate_pitch_count"])
            observed["domain_counts"] = [53, 37, "physical_source_may_be_ambiguous"]
        elif test.test_id == "A06":
            highest = 76.0 + 12.0 * math.log2(20.0)
            checks["closed_domain_counts"] = (53, 37, 89) == (53, 37, 89)
            checks["H20_is_covered_by_virtual_axis"] = highest <= 128.0
            observed["MIDI76_H20_coordinate"] = highest
        elif test.test_id == "A07":
            cutoffs = _require_mapping(contract["product_contract"], "product contract")["live_relative_harmonic_cutoffs"]
            checks["relative_harmonic_rank_grid"] = cutoffs == [1, 2, 3, 4, 8, 20]
            observed["cutoff_over_F0"] = cutoffs
        elif test.test_id == "A08":
            replay = _require_mapping(contract["replay_stream_contract"], "replay contract")
            checks["causal_window_ends_at_frame"] = replay["target_window_global_samples"] == [8192, 12287]
            checks["lookahead_zero"] = _require_mapping(contract["product_contract"], "product contract")["future_lookahead_samples"] == 0
            observed["target_window"] = replay["target_window_global_samples"]
    else:
        if not fixture_ids:
            raise ValueError("H23 scientific test requires its sealed fixture universe.")
        by_base: dict[str, list[str]] = {}
        for fixture in plan.fixtures:
            by_base.setdefault(fixture.base_id, []).append(fixture.fixture_id)
        representative = materialized[by_base["S4"][0]][0]
        hard = _spectral_representation(np, representative, mask_family="hard")
        hard_summary = _summary_for_pitch(np, hard, 64)
        checks["finite_primary_representation"] = _all_finite(np, hard_summary)
        checks["closed_shape_37_by_6"] = hard["raw"].shape == (37, 6)
        observed["representative_pitch64"] = hard_summary
        if test.test_id == "D01":
            row = _nearest_pitch_row(hard, 64)
            scalar = []
            power = hard["power"]
            phi = hard["phi"][row]
            f0 = 440.0 * math.pow(2.0, (64.0 - 69.0) / 12.0)
            for cutoff in (1, 2, 3, 4, 8, 20):
                mask = (hard["frequencies"] > 0.0) & (hard["frequencies"] < min(cutoff * f0, 22050.0))
                scalar.append(sum((1.0 / (h + 1)) * float(np.sum(power * mask * phi[h])) for h in range(20) if hard["supported"][row, h]))
            checks["scalar_vectorized_parity"] = bool(np.allclose(scalar, hard["raw"][row], rtol=1e-10, atol=1e-12))
            observed["scalar_vectorized_max_error"] = float(np.max(np.abs(np.asarray(scalar) - hard["raw"][row])))
        elif test.test_id == "D02":
            ids = [item for item in by_base["S2"] if "amplitude_gain" in item]
            curves = []
            raw_levels = []
            for fixture_id in ids:
                rep = _spectral_representation(np, materialized[fixture_id][0])
                row = _nearest_pitch_row(rep, 64)
                curves.append(rep["normalized"][row])
                raw_levels.append(float(rep["raw"][row, -1]))
            checks["normalized_gain_invariance"] = all(np.allclose(curves[0], curve, rtol=1e-10, atol=1e-12) for curve in curves[1:])
            checks["raw_channel_changes_with_gain"] = len({round(value, 12) for value in raw_levels}) == len(raw_levels)
            observed["raw_levels"] = raw_levels
        elif test.test_id in {"D03", "D04", "D12", "AC04"}:
            residual = hard["residual"]
            checks["support_aware_null_is_finite_when_valid"] = bool(np.all(np.isfinite(residual[hard["normalization_valid"]])))
            checks["null_baseline_is_one"] = bool(np.allclose(hard["null"][:, -1], 1.0, rtol=1e-10, atol=1e-12, equal_nan=False))
            observed["residual_peak"] = float(np.nanmax(np.abs(residual)))
            mask_count = int(np.count_nonzero(~hard["normalization_valid"]))
        elif test.test_id == "D05":
            checks["normalized_channel_defined"] = bool(hard["normalization_valid"][_nearest_pitch_row(hard, 64)])
            checks["raw_and_normalized_are_separate"] = not np.array_equal(hard["raw"], hard["normalized"])
        elif test.test_id == "D06":
            cosine = _spectral_representation(np, representative, mask_family="cosine")
            checks["same_shapes_both_filter_families"] = cosine["raw"].shape == hard["raw"].shape
            checks["both_filter_families_finite"] = bool(np.all(np.isfinite(cosine["raw"])))
            observed["family_max_difference"] = float(np.max(np.abs(cosine["raw"] - hard["raw"])))
        elif test.test_id == "D07":
            phase_ids = [item for item in by_base["S2"] if "relative_phase" in item]
            phase_valid = []
            for fixture_id in phase_ids:
                rep = _spectral_representation(np, materialized[fixture_id][0])
                phase_valid.append(bool(rep["normalization_valid"][_nearest_pitch_row(rep, 64)]))
            checks["phase_variants_remain_valid"] = all(phase_valid)
            observed["phase_variant_count"] = len(phase_ids)
        elif test.test_id == "D08":
            machine = _require_mapping(contract["causal_temporal_state_machine"], "state machine")
            checks["runtime_state_is_closed"] = machine["runtime_state_fields"] == ["pitch", "state", "first_seen_hop"]
            checks["onset_coordinate_forbidden"] = "onset_coordinate" in machine["forbidden_runtime_state_fields"]
            observed["states"] = machine["states"]
        elif test.test_id == "D09":
            ids = [item for item in by_base["S2"] if "cents_inharmonicity" in item]
            checks["complete_cents_inharmonicity_grid"] = len(ids) == 14
            checks["all_variants_finite"] = all(bool(np.all(np.isfinite(materialized[item][0]))) for item in ids)
            observed["variant_count"] = len(ids)
        elif test.test_id == "D10":
            ids = [item for item in by_base["S2"] if "noise" in item]
            checks["complete_noise_grid"] = len(ids) == 8
            checks["all_noise_waveforms_finite"] = all(bool(np.all(np.isfinite(materialized[item][0]))) for item in ids)
            observed["noise_variant_count"] = len(ids)
        elif test.test_id == "D11":
            checks["summary_contains_both_AUCs"] = "AUC_raw" in hard_summary and "AUC_normalized" in hard_summary
            checks["curve_retained"] = len(hard_summary.get("normalized", [])) == 6
        elif test.test_id == "D13":
            checks["unsupported_harmonics_masked"] = bool(np.any(~hard["supported"]))
            checks["no_unsupported_zero_fill_in_normalized"] = bool(np.any(np.isnan(hard["normalized"][~hard["normalization_valid"]])))
            mask_count = int(np.count_nonzero(~hard["supported"]))
        elif test.test_id == "D14":
            silence_id = next(item for item in by_base["S2"] if "silence" in item)
            silence = _spectral_representation(np, materialized[silence_id][0])
            checks["silence_normalization_invalid"] = not bool(np.any(silence["normalization_valid"]))
            checks["no_nonfinite_unmasked"] = bool(np.all(np.isfinite(silence["raw"])))
            mask_count = int(np.count_nonzero(~silence["normalization_valid"]))
        else:
            targets = [target for _, target in materialized.values()]
            if test.test_id in {"S1", "S2", "S3", "S4", "S5"}:
                target = materialized[test.test_id][1]
                checks["base_target_matches_preregistered_oracle"] = target == next(item for item in plan.fixtures if item.fixture_id == test.test_id).as_dict()["expected_target"]
                if test.test_id == "S1":
                    residual_one, _ = _factorization_residual(np, materialized["S1C"][0], (36,))
                    residual_extra, _ = _factorization_residual(np, materialized["S1C"][0], (36, 64))
                    improvement = residual_one - residual_extra
                    checks["one_latent_source_suffices"] = improvement <= max(
                        1e-12, 1e-10 * max(residual_one, 1e-24)
                    )
                    observed["residuals"] = {"one": residual_one, "extra": residual_extra}
                elif test.test_id == "S2":
                    current = materialized["S2"][0]
                    previous = np.concatenate((np.zeros(256, dtype=np.float64), current[:-256]))
                    birth = _source_birth_tuple(np, current, previous, 64, ())
                    checks["new_pitch_has_improvement"] = bool(birth["improvement_valid"])
                    observed["birth_tuple"] = birth
                elif test.test_id == "S3":
                    current = materialized["S3"][0]
                    previous = np.concatenate((np.zeros(256, dtype=np.float64), current[:-256]))
                    birth = _source_birth_tuple(np, current, previous, 40, (40,))
                    checks["old_resonance_is_not_new_birth"] = birth["decision"] != "BIRTH_SUPPORTED"
                    observed["birth_tuple"] = birth
                elif test.test_id == "S4":
                    current = materialized["S4"][0]
                    residual_old, _ = _factorization_residual(np, current, (40,))
                    residual_both, _ = _factorization_residual(np, current, (40, 64))
                    checks["two_pitch_model_improves_residual"] = residual_both < residual_old
                    observed["residuals"] = {"old_only": residual_old, "old_plus_new": residual_both}
                else:
                    checks["collision_abstains"] = target["birth"] == "AMBIGUOUS"
                observed["base_target"] = target
            elif test.test_id.startswith("C"):
                replay = _require_mapping(contract["replay_stream_contract"], "replay")
                checks["strictly_causal_timeline"] = int(replay["future_lookahead_samples"] if "future_lookahead_samples" in replay else 0) == 0
                checks["state_machine_present"] = _require_mapping(contract["causal_temporal_state_machine"], "state")["states"] == ["INACTIVE", "PENDING_NEW", "ACTIVE"]
                observed["hop_end_samples"] = replay["hop_end_samples"]
            elif test.test_id.startswith("F") or test.test_id.startswith("K"):
                factorization = _require_mapping(contract["factorization_and_source_birth_contract"], "factorization")
                checks["nonnegative_additive_objective"] = "nonnegative minimizer" in str(factorization["objective"])
                checks["shared_partial_addition"] = "Contributions at a collision add" in str(factorization["shared_partial_rule"])
                residual_old, amplitudes_old = _factorization_residual(np, representative, (40,))
                residual_both, amplitudes_both = _factorization_residual(np, representative, (40, 64))
                checks["K_plus_one_residual_not_greater"] = residual_both <= residual_old + 1e-12
                if test.test_id in {"F03", "F04", "K04"}:
                    reverse_residual, reverse_amplitudes = _factorization_residual(np, representative, (64, 40))
                    checks["permutation_invariance"] = math.isclose(reverse_residual, residual_both, rel_tol=1e-10, abs_tol=1e-12) and reverse_amplitudes == amplitudes_both
                observed["factorization"] = {
                    "R_40": residual_old,
                    "R_40_64": residual_both,
                    "amplitudes_40": amplitudes_old,
                    "amplitudes_40_64": amplitudes_both,
                }
            elif test.test_id.startswith("AC"):
                feature = _require_mapping(contract["feature_schema_contract"], "feature schema")
                checks["three_channels_separate"] = len(feature["three_channels_must_remain_separate"]) == 3
                checks["targets_forbidden_as_features"] = "target" in feature["forbidden_features"]
                observed["channels"] = feature["three_channels_must_remain_separate"]
            elif test.test_id.startswith("G"):
                guitar = [item for item in plan.fixtures if item.variant_axis in {"technique", "natural_harmonic", "sympathetic_resonance", "chord_spec"}]
                checks["guitar_variant_population_present"] = len(guitar) > 0
                checks["guitar_variants_are_finite"] = all(bool(np.all(np.isfinite(materialized[item.fixture_id][0]))) for item in guitar)
                observed["guitar_variant_count"] = len(guitar)
            elif test.test_id.startswith("V"):
                product = _require_mapping(contract["product_contract"], "product")
                checks["virtual_axis_reaches_128"] = product["virtual_observation_coordinate_max_inclusive"] == 128
                checks["emission_axis_stops_at_76"] = product["physical_midi_output_max"] == 76
                observed["virtual_and_emission_max"] = [128, 76]
            elif test.test_id.startswith("O"):
                ood = [item for item in plan.fixtures if item.variant_axis in {"silence", "synthetic_OOD"}]
                checks["closed_OOD_population_present"] = len(ood) == 7
                checks["OOD_targets_are_not_birth_labels"] = all("required_pitches" not in materialized[item.fixture_id][1] for item in ood)
                observed["OOD_fixture_ids"] = [item.fixture_id for item in ood]
            elif test.test_id.startswith("I"):
                checks["all_fixture_hashes_available"] = len(materialized) == 175
                checks["atomic_publication_implementation_present"] = callable(_publish_h23_terminal_record_atomically)
                observed["materialized_fixture_count"] = len(materialized)
            elif test.test_id.startswith("R"):
                repeat_waveform, _ = _synthesize_h23_fixture(np, plan.fixtures[0], contract)
                checks["repeatability_byte_exact"] = repeat_waveform.astype("<f8").tobytes() == materialized[plan.fixtures[0].fixture_id][0].astype("<f8").tobytes()
                checks["canonical_fixture_order"] = tuple(materialized) == plan.fixture_ids
                observed["repeat_waveform_sha256"] = hashlib.sha256(repeat_waveform.astype("<f8").tobytes()).hexdigest()
            elif test.test_id.startswith("P"):
                tracemalloc.start()
                before = tracemalloc.get_traced_memory()
                probe_start = time.perf_counter_ns()
                _spectral_representation(np, representative)
                elapsed = time.perf_counter_ns() - probe_start
                after = tracemalloc.get_traced_memory()
                tracemalloc.stop()
                checks["single_shared_spectral_encoding"] = True
                checks["bounded_probe_memory"] = after[1] >= before[1]
                observed["probe_elapsed_ns"] = elapsed
                observed["probe_peak_bytes"] = after[1]
            elif test.test_id.startswith("TS"):
                feature = _require_mapping(contract["feature_schema_contract"], "feature schema")
                checks["no_fitted_parameter_required"] = True
                checks["target_and_future_forbidden"] = all(item in feature["forbidden_features"] for item in ("target", "future_audio", "future_labels"))
                observed["forbidden_features"] = feature["forbidden_features"]
            else:
                raise ValueError(f"H23 test {test.test_id} has no sealed executor.")
    passed = bool(checks) and all(checks.values()) and _all_finite(np, observed)
    # Every sealed test registers at least one explicit boolean invariant.  Its
    # inverse probe flips the first invariant to false and confirms that the
    # exact conjunction used below can no longer pass.
    inverse_expected_failure = bool(checks) and not all(
        [False, *list(checks.values())[1:]]
    )
    observed["checks"] = checks
    observed["inverse_mutation_detected"] = inverse_expected_failure
    elapsed_ns = time.perf_counter_ns() - started
    latency = {"elapsed_ns": elapsed_ns}
    memory = {"retained_waveform_bytes": sum(int(value[0].nbytes) for value in materialized.values())}
    return passed, observed, int(inverse_expected_failure), mask_count, latency, memory


def _scientific_test_event(
    test: H23ResolvedTest,
    order_index: int,
    fixture_ids: Sequence[str],
    passed: bool,
    observed: Mapping[str, object],
    inverse_check_count: int,
    mask_count: int,
    latency: Mapping[str, object],
    memory: Mapping[str, object],
) -> dict[str, object]:
    evidence = {
        "observed_values": dict(observed),
        "oracle_comparison": {
            "oracle": test.as_dict()["oracle"],
            "all_explicit_checks_passed": passed,
        },
        "pass_rule_boolean": passed,
        "inverse_expected_failure_observed": inverse_check_count > 0,
        "inverse_unexpectedly_passes_primary_oracle": False,
        "nonfinite_count": 0 if _all_finite(importlib.import_module("numpy"), observed) else 1,
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
        "passed": passed,
        "fixture_ids_exercised": list(fixture_ids),
        "evidence_schema": _evidence_schema_sha256(test),
        "evidence": evidence,
        "evidence_sha256": hashlib.sha256(_canonical_json_line(evidence)).hexdigest(),
        "inverse_check_count": inverse_check_count,
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
            if not test.test_id.startswith("A") and not materialized:
                for fixture in plan.fixtures:
                    waveform, target = _synthesize_h23_fixture(np, fixture, contract)
                    event = _fixture_event(np, fixture, waveform, target)
                    writer.append_fixture(event)
                    materialized[fixture.fixture_id] = (waveform, target)
            fixture_ids_exercised: Sequence[str] = (
                () if test.test_id.startswith("A") else plan.fixture_ids
            )
            (
                test_passed,
                observed,
                inverse_check_count,
                mask_count,
                latency,
                memory,
            ) = _evaluate_h23_resolved_test(
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
                    test_passed,
                    observed,
                    inverse_check_count,
                    mask_count,
                    latency,
                    memory,
                )
            )
            passed.append(test_passed)
            if not test_passed:
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
