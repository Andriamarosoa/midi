"""Disposable administrative lifecycle qualification for the H25 successor.

This module is deliberately standard-library-only.  It never issues a
scientific capability, never opens a scientific population, and never imports
NumPy.  Its only purpose is to exercise the one-process control-flow shape in
an isolated ``h25-admin-*`` namespace before a future scientific contract may
exist.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import re
import signal
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


H25_ADMIN_SCHEMA_VERSION = 1
H25_ADMIN_SUCCESS = "H25_ADMIN_LIFECYCLE_QUALIFIED"
H25_ADMIN_FAILURE = "H25_ADMIN_LIFECYCLE_LOGICAL_FAILURE"
H25_ADMIN_INCONCLUSIVE = "H25_ADMIN_LIFECYCLE_INCONCLUSIVE_CONSUMED"
H25_ADMIN_PRECLAIM_ABORTED = "H25_ADMIN_LIFECYCLE_PRECLAIM_ABORTED_NOT_CONSUMED"
H25_ADMIN_FORENSIC_INCONCLUSIVE = "H25_ADMIN_LIFECYCLE_FORENSIC_INCONCLUSIVE_CONSUMED"

H25_ADMIN_BOUNDARIES = (
    "P0_boundary",
    "P1_boundary",
    "P2_boundary",
)

H25_ADMIN_FAULTS = (
    "NONE",
    "LOGICAL_FAILURE_AT_P1",
    "OPERATIONAL_ERROR_AT_P1",
    "EOF_BEFORE_SURROGATE_CLAIM",
    "EOF_AFTER_SURROGATE_CLAIM",
    "PARENT_SSH_DISCONNECT_AFTER_SURROGATE_CLAIM",
    "SIGINT_AFTER_SURROGATE_CLAIM",
    "TIMEOUT_PREFLIGHT",
    "TIMEOUT_SURROGATE_CLAIM",
    "TIMEOUT_P0",
    "TIMEOUT_P1",
    "TIMEOUT_P2",
    "TIMEOUT_SUCCESS_CLOSURE",
    "TIMEOUT_FAILURE_CLOSURE",
    "TIMEOUT_INCONCLUSIVE_CLOSURE",
    "EVIDENCE_WRITE_FAIL",
    "TRANSCRIPT_PUBLISH_FAIL",
    "TERMINAL_PUBLISH_FAIL",
    "SUCCESS_RENAME_FAIL",
)

H25_REAL_OS_PROBES = (
    "REAL_NOMINAL",
    "REAL_EOF_BEFORE_SURROGATE_CLAIM",
    "REAL_EOF_AFTER_SURROGATE_CLAIM",
    "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM",
    "REAL_SIGINT_AFTER_SURROGATE_CLAIM",
    "REAL_TIMEOUT_PREFLIGHT",
    "REAL_TIMEOUT_SURROGATE_CLAIM",
    "REAL_TIMEOUT_P0",
    "REAL_TIMEOUT_P1",
    "REAL_TIMEOUT_P2",
    "REAL_TIMEOUT_SUCCESS_CLOSURE",
    "REAL_TIMEOUT_FAILURE_CLOSURE",
    "REAL_TIMEOUT_INCONCLUSIVE_CLOSURE",
)

_REAL_TIMEOUT_STAGE = {
    "REAL_TIMEOUT_PREFLIGHT": "preflight",
    "REAL_TIMEOUT_SURROGATE_CLAIM": "surrogate_claim",
    "REAL_TIMEOUT_P0": "P0_boundary",
    "REAL_TIMEOUT_P1": "P1_boundary",
    "REAL_TIMEOUT_P2": "P2_boundary",
    "REAL_TIMEOUT_SUCCESS_CLOSURE": "success_closure",
    "REAL_TIMEOUT_FAILURE_CLOSURE": "failure_closure",
    "REAL_TIMEOUT_INCONCLUSIVE_CLOSURE": "inconclusive_closure",
}
_REAL_TO_SYNTHETIC_FAULT = {
    "REAL_NOMINAL": "NONE",
    "REAL_EOF_BEFORE_SURROGATE_CLAIM": "EOF_BEFORE_SURROGATE_CLAIM",
    "REAL_EOF_AFTER_SURROGATE_CLAIM": "EOF_AFTER_SURROGATE_CLAIM",
    "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM": "PARENT_SSH_DISCONNECT_AFTER_SURROGATE_CLAIM",
    "REAL_SIGINT_AFTER_SURROGATE_CLAIM": "SIGINT_AFTER_SURROGATE_CLAIM",
    "REAL_TIMEOUT_PREFLIGHT": "TIMEOUT_PREFLIGHT",
    "REAL_TIMEOUT_SURROGATE_CLAIM": "TIMEOUT_SURROGATE_CLAIM",
    "REAL_TIMEOUT_P0": "TIMEOUT_P0",
    "REAL_TIMEOUT_P1": "TIMEOUT_P1",
    "REAL_TIMEOUT_P2": "TIMEOUT_P2",
    "REAL_TIMEOUT_SUCCESS_CLOSURE": "TIMEOUT_SUCCESS_CLOSURE",
    "REAL_TIMEOUT_FAILURE_CLOSURE": "TIMEOUT_FAILURE_CLOSURE",
    "REAL_TIMEOUT_INCONCLUSIVE_CLOSURE": "TIMEOUT_INCONCLUSIVE_CLOSURE",
}

_PRECLAIM_FAULTS = {
    "EOF_BEFORE_SURROGATE_CLAIM",
    "TIMEOUT_PREFLIGHT",
    "TIMEOUT_SURROGATE_CLAIM",
}
_AFTER_CLAIM_IMMEDIATE_FAULTS = {
    "EOF_AFTER_SURROGATE_CLAIM",
    "PARENT_SSH_DISCONNECT_AFTER_SURROGATE_CLAIM",
    "SIGINT_AFTER_SURROGATE_CLAIM",
}
_BOUNDARY_TIMEOUTS = {
    "P0_boundary": "TIMEOUT_P0",
    "P1_boundary": "TIMEOUT_P1",
    "P2_boundary": "TIMEOUT_P2",
}
_ZERO_SHA = "0" * 64
_SCENARIO_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]{0,62}$")
_ROOT_PATTERN = re.compile(r"^h25-admin-[a-z0-9][a-z0-9-]{0,62}$")
_RECORD_KEYS = {
    "boundary",
    "detail_sha256",
    "event",
    "evidence_path",
    "evidence_sha256",
    "fault",
    "previous_record_sha256",
    "scenario_id",
    "schema_version",
    "sequence_index",
    "state",
}


@dataclass(frozen=True)
class H25AdministrativeQualificationScenario:
    scenario_id: str
    fault: str = "NONE"

    def __post_init__(self) -> None:
        if type(self.scenario_id) is not str or not _SCENARIO_PATTERN.fullmatch(
            self.scenario_id
        ):
            raise ValueError("H25 administrative scenario_id is invalid.")
        if type(self.fault) is not str or self.fault not in H25_ADMIN_FAULTS:
            raise ValueError("H25 administrative fault is not preregistered.")


@dataclass(frozen=True)
class H25AdministrativeQualificationResult:
    scenario_id: str
    fault: str
    status: str
    surrogate_claim_consumed: bool
    event_count: int
    root: Path
    claim_path: Path
    staging_directory: Path
    success_directory: Path
    transcript_path: Path
    terminal_path: Path
    forensic_path: Path


@dataclass(frozen=True)
class H25RealOSQualificationProbe:
    probe_id: str
    probe: str
    timeout_seconds: float = 0.20
    process_deadline_seconds: float = 10.0

    def __post_init__(self) -> None:
        if type(self.probe_id) is not str or not _SCENARIO_PATTERN.fullmatch(
            self.probe_id
        ):
            raise ValueError("H25 real-OS probe_id is invalid.")
        if type(self.probe) is not str or self.probe not in H25_REAL_OS_PROBES:
            raise ValueError("H25 real-OS probe is not preregistered.")
        for name, value in (
            ("timeout_seconds", self.timeout_seconds),
            ("process_deadline_seconds", self.process_deadline_seconds),
        ):
            if (
                type(value) not in {int, float}
                or isinstance(value, bool)
                or not math.isfinite(float(value))
                or value <= 0
            ):
                raise ValueError(f"H25 {name} must be positive.")
        if self.process_deadline_seconds <= self.timeout_seconds:
            raise ValueError("H25 process deadline must exceed the probe timeout.")


@dataclass(frozen=True)
class H25RealOSQualificationProbeResult:
    probe_id: str
    probe: str
    status: str
    child_pid: int
    child_exit_code: int
    child_process_alive: bool
    elapsed_seconds: float
    root: Path
    controller_receipt_path: Path


@dataclass(frozen=True)
class _Paths:
    root: Path
    claim: Path
    staging: Path
    success: Path
    transcript_staging: Path
    transcript_in_staging: Path
    transcript: Path
    evidence_staging: Path
    evidence: Path
    terminal: Path
    forensic: Path


class _InjectedAdministrativeFailure(RuntimeError):
    def __init__(self, fault: str, stage: str) -> None:
        super().__init__(f"{fault} at {stage}")
        self.fault = fault
        self.stage = stage


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H25 administrative JSON duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H25 administrative JSON forbids {token!r}.")


def _parse_canonical(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H25 {label} must be UTF-8 LF without BOM.")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict or _canonical(value) != raw:
        raise ValueError(f"H25 {label} is not canonical.")
    return value


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_new(path: Path, raw: bytes, *, mode: int = 0o600) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        mode,
    )
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("H25 administrative write made no progress.")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    _fsync_directory(path.parent)


def _atomic_write_new(path: Path, raw: bytes) -> None:
    temporary = path.with_name(path.name + ".part")
    if path.exists() or temporary.exists():
        raise FileExistsError(f"H25 administrative atomic path exists: {path}.")
    _write_new(temporary, raw)
    os.replace(temporary, path)
    _fsync_directory(path.parent)


def _derive_paths(root: Path) -> _Paths:
    candidate = Path(root)
    if not candidate.is_absolute():
        raise ValueError("H25 administrative root must be absolute.")
    if not _ROOT_PATTERN.fullmatch(candidate.name):
        raise ValueError("H25 administrative root must use h25-admin-*.")
    parent = candidate.parent.resolve(strict=True)
    resolved = parent / candidate.name
    if "harmonic_censoring_h24" in str(resolved).lower():
        raise ValueError("H25 administrative root overlaps the H24 namespace.")
    paths = _Paths(
        root=resolved,
        claim=parent / f"{candidate.name}.surrogate-claim.json",
        staging=parent / f"{candidate.name}.staging",
        success=resolved,
        transcript_staging=parent
        / f"{candidate.name}.staging"
        / "administrative_transcript.jsonl.part",
        transcript_in_staging=parent
        / f"{candidate.name}.staging"
        / "administrative_transcript.jsonl",
        transcript=resolved / "administrative_transcript.jsonl",
        evidence_staging=parent / f"{candidate.name}.staging" / "evidence",
        evidence=resolved / "evidence",
        terminal=parent / f"{candidate.name}.terminal.json",
        forensic=parent / f"{candidate.name}.forensic.json",
    )
    for path in (
        paths.claim,
        paths.staging,
        paths.success,
        paths.terminal,
        paths.forensic,
        paths.terminal.with_name(paths.terminal.name + ".part"),
        paths.forensic.with_name(paths.forensic.name + ".part"),
    ):
        if path.exists():
            raise FileExistsError(f"H25 administrative one-shot path exists: {path}.")
    return paths


def _claim_payload(scenario: H25AdministrativeQualificationScenario) -> dict[str, object]:
    return {
        "H17_population_used": False,
        "claim_state": "ADMINISTRATIVE_SURROGATE_CLAIMED",
        "locked_test_used": False,
        "model_or_checkpoint_used": False,
        "purpose": "h25_preclaim_administrative_lifecycle_surrogate_claim",
        "real_data_used": False,
        "scenario_id": scenario.scenario_id,
        "schema_version": H25_ADMIN_SCHEMA_VERSION,
        "scientific_capability_issued": False,
        "scientific_claim_created": False,
        "scientific_population_used": False,
        "training_authorized": False,
    }


def _terminal_payload(
    scenario: H25AdministrativeQualificationScenario,
    *,
    status: str,
    claim_raw: bytes | None,
    transcript_raw: bytes | None,
    final_record_sha256: str,
    event_count: int,
) -> dict[str, object]:
    return {
        "event_count": event_count,
        "fault": scenario.fault,
        "final_record_sha256": final_record_sha256,
        "locked_test_used": False,
        "purpose": "h25_preclaim_administrative_lifecycle_terminal",
        "real_data_used": False,
        "scenario_id": scenario.scenario_id,
        "schema_version": H25_ADMIN_SCHEMA_VERSION,
        "scientific_execution_used": False,
        "status": status,
        "surrogate_claim_consumed": claim_raw is not None,
        "surrogate_claim_sha256": None if claim_raw is None else _sha(claim_raw),
        "training_used": False,
        "transcript_sha256": None
        if transcript_raw is None
        else _sha(transcript_raw),
    }


class _Transcript:
    def __init__(
        self,
        paths: _Paths,
        scenario: H25AdministrativeQualificationScenario,
    ) -> None:
        paths.staging.mkdir()
        paths.evidence_staging.mkdir()
        self.paths = paths
        self.scenario = scenario
        self._stream = paths.transcript_staging.open("xb")
        self._count = 0
        self._previous = _ZERO_SHA
        self._published = False

    @property
    def count(self) -> int:
        return self._count

    @property
    def previous(self) -> str:
        return self._previous

    def append(
        self,
        event: str,
        *,
        boundary: str | None = None,
        state: str = "OBSERVED",
        detail: str | None = None,
        evidence_path: str | None = None,
        evidence_raw: bytes | None = None,
    ) -> None:
        if self._published:
            raise RuntimeError("H25 administrative transcript is published.")
        record = {
            "boundary": boundary,
            "detail_sha256": None
            if detail is None
            else _sha(detail.encode("utf-8")),
            "event": event,
            "evidence_path": evidence_path,
            "evidence_sha256": None
            if evidence_raw is None
            else _sha(evidence_raw),
            "fault": self.scenario.fault,
            "previous_record_sha256": self._previous,
            "scenario_id": self.scenario.scenario_id,
            "schema_version": H25_ADMIN_SCHEMA_VERSION,
            "sequence_index": self._count,
            "state": state,
        }
        raw = _canonical(record)
        self._stream.write(raw)
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._previous = _sha(raw)
        self._count += 1
        count, previous, _ = _recompute_transcript(self.paths.transcript_staging)
        if (count, previous) != (self._count, self._previous):
            raise ValueError("H25 transcript recomputation diverged after append.")

    def boundary(self, boundary: str) -> None:
        if boundary not in H25_ADMIN_BOUNDARIES:
            raise ValueError("H25 administrative boundary is unknown.")
        relative = f"evidence/{boundary}.json"
        evidence = {
            "boundary": boundary,
            "future_scientific_test_executed": False,
            "purpose": "h25_administrative_boundary_evidence",
            "scenario_id": self.scenario.scenario_id,
            "schema_version": H25_ADMIN_SCHEMA_VERSION,
        }
        raw = _canonical(evidence)
        if self.scenario.fault == "EVIDENCE_WRITE_FAIL" and boundary == "P0_boundary":
            raise _InjectedAdministrativeFailure("EVIDENCE_WRITE_FAIL", boundary)
        path = self.paths.staging / relative
        _write_new(path, raw)
        if path.read_bytes() != raw:
            raise ValueError("H25 boundary evidence changed after write.")
        self.append(
            "BOUNDARY_PASSED",
            boundary=boundary,
            evidence_path=relative,
            evidence_raw=raw,
        )

    def append_not_run_suffix(self, from_boundary: str) -> None:
        start = H25_ADMIN_BOUNDARIES.index(from_boundary)
        for boundary in H25_ADMIN_BOUNDARIES[start:]:
            self.append(
                "BOUNDARY_NOT_RUN",
                boundary=boundary,
                state="NOT_RUN_BY_PREREGISTERED_FAILURE",
            )

    def publish(self) -> bytes:
        self._stream.close()
        count, previous, raw = _recompute_transcript(self.paths.transcript_staging)
        if (count, previous) != (self._count, self._previous):
            raise ValueError("H25 transcript diverged before publication.")
        if self.scenario.fault == "TRANSCRIPT_PUBLISH_FAIL":
            raise _InjectedAdministrativeFailure(
                "TRANSCRIPT_PUBLISH_FAIL", "transcript_publish"
            )
        os.replace(self.paths.transcript_staging, self.paths.transcript_in_staging)
        _fsync_directory(self.paths.staging)
        if self.scenario.fault == "SUCCESS_RENAME_FAIL":
            raise _InjectedAdministrativeFailure(
                "SUCCESS_RENAME_FAIL", "success_rename"
            )
        os.replace(self.paths.staging, self.paths.success)
        _fsync_directory(self.paths.success.parent)
        self._published = True
        published = self.paths.transcript.read_bytes()
        if published != raw:
            raise ValueError("H25 transcript changed during atomic publication.")
        return published

    def close(self) -> None:
        if not self._stream.closed:
            self._stream.close()


def _recompute_transcript(path: Path) -> tuple[int, str, bytes]:
    raw = path.read_bytes()
    lines = raw.splitlines(keepends=True)
    if b"".join(lines) != raw:
        raise ValueError("H25 transcript line preservation failed.")
    previous = _ZERO_SHA
    scenario_id: str | None = None
    fault: str | None = None
    for index, line in enumerate(lines):
        record = _parse_canonical(line, f"transcript record {index}")
        if set(record) != _RECORD_KEYS:
            raise ValueError("H25 transcript record key set mismatch.")
        if (
            type(record["schema_version"]) is not int
            or record["schema_version"] != H25_ADMIN_SCHEMA_VERSION
            or type(record["sequence_index"]) is not int
            or record["sequence_index"] != index
            or record.get("previous_record_sha256") != previous
        ):
            raise ValueError("H25 transcript order/hash chain is invalid.")
        if index == 0:
            scenario_id = str(record["scenario_id"])
            fault = str(record["fault"])
        elif (record["scenario_id"], record["fault"]) != (scenario_id, fault):
            raise ValueError("H25 transcript scenario identity changed.")
        if (
            type(record["event"]) is not str
            or not record["event"]
            or type(record["state"]) is not str
            or not record["state"]
        ):
            raise ValueError("H25 transcript event/state is invalid.")
        previous = _sha(line)
    return len(lines), previous, raw


def _write_forensic(
    paths: _Paths,
    scenario: H25AdministrativeQualificationScenario,
    *,
    claim_raw: bytes,
    failure: BaseException,
    event_count: int,
    final_record_sha256: str,
) -> None:
    if paths.transcript.exists():
        staging_transcript = paths.transcript
    elif paths.transcript_staging.exists():
        staging_transcript = paths.transcript_staging
    else:
        staging_transcript = paths.transcript_in_staging
    transcript_raw = (
        staging_transcript.read_bytes() if staging_transcript.exists() else None
    )
    payload = {
        "event_count": event_count,
        "failure_class": f"{type(failure).__module__}.{type(failure).__qualname__}",
        "failure_message_sha256": _sha(str(failure).encode("utf-8")),
        "fault": scenario.fault,
        "final_record_sha256": final_record_sha256,
        "purpose": "h25_preclaim_administrative_lifecycle_forensic_receipt",
        "scenario_id": scenario.scenario_id,
        "schema_version": H25_ADMIN_SCHEMA_VERSION,
        "scientific_execution_used": False,
        "status": H25_ADMIN_FORENSIC_INCONCLUSIVE,
        "surrogate_claim_sha256": _sha(claim_raw),
        "transcript_sha256": None
        if transcript_raw is None
        else _sha(transcript_raw),
    }
    _atomic_write_new(paths.forensic, _canonical(payload))


def _result(
    paths: _Paths,
    scenario: H25AdministrativeQualificationScenario,
    status: str,
    consumed: bool,
    event_count: int,
) -> H25AdministrativeQualificationResult:
    return H25AdministrativeQualificationResult(
        scenario_id=scenario.scenario_id,
        fault=scenario.fault,
        status=status,
        surrogate_claim_consumed=consumed,
        event_count=event_count,
        root=paths.root,
        claim_path=paths.claim,
        staging_directory=paths.staging,
        success_directory=paths.success,
        transcript_path=paths.transcript,
        terminal_path=paths.terminal,
        forensic_path=paths.forensic,
    )


def run_h25_preclaim_administrative_lifecycle_qualification(
    root: Path,
    scenario: H25AdministrativeQualificationScenario,
) -> H25AdministrativeQualificationResult:
    """Run one disposable administrative scenario, never scientific work."""

    if type(scenario) is not H25AdministrativeQualificationScenario:
        raise TypeError("H25 qualification requires the exact scenario type.")
    paths = _derive_paths(root)

    if scenario.fault in _PRECLAIM_FAULTS:
        terminal = _terminal_payload(
            scenario,
            status=H25_ADMIN_PRECLAIM_ABORTED,
            claim_raw=None,
            transcript_raw=None,
            final_record_sha256=_ZERO_SHA,
            event_count=0,
        )
        _atomic_write_new(paths.terminal, _canonical(terminal))
        return _result(paths, scenario, H25_ADMIN_PRECLAIM_ABORTED, False, 0)

    claim_raw = _canonical(_claim_payload(scenario))
    _write_new(paths.claim, claim_raw)
    if paths.claim.read_bytes() != claim_raw:
        raise ValueError("H25 surrogate claim changed after durable write.")
    writer = _Transcript(paths, scenario)
    writer.append("PREFLIGHT_PASSED")
    writer.append("SURROGATE_CLAIM_ACQUIRED")

    try:
        if scenario.fault in _AFTER_CLAIM_IMMEDIATE_FAULTS:
            raise _InjectedAdministrativeFailure(
                scenario.fault, "after_surrogate_claim"
            )

        for boundary in H25_ADMIN_BOUNDARIES:
            if scenario.fault == _BOUNDARY_TIMEOUTS[boundary]:
                raise _InjectedAdministrativeFailure(scenario.fault, boundary)
            if scenario.fault in {
                "LOGICAL_FAILURE_AT_P1",
                "TIMEOUT_FAILURE_CLOSURE",
            } and boundary == "P1_boundary":
                writer.append(
                    "BOUNDARY_LOGICAL_FAILURE",
                    boundary=boundary,
                    state="FAILED",
                )
                writer.append_not_run_suffix("P2_boundary")
                if scenario.fault == "TIMEOUT_FAILURE_CLOSURE":
                    failure = _InjectedAdministrativeFailure(
                        "TIMEOUT_FAILURE_CLOSURE", "failure_closure"
                    )
                    writer.close()
                    _write_forensic(
                        paths,
                        scenario,
                        claim_raw=claim_raw,
                        failure=failure,
                        event_count=writer.count,
                        final_record_sha256=writer.previous,
                    )
                    return _result(
                        paths,
                        scenario,
                        H25_ADMIN_FORENSIC_INCONCLUSIVE,
                        True,
                        writer.count,
                    )
                transcript_raw = writer.publish()
                terminal = _terminal_payload(
                    scenario,
                    status=H25_ADMIN_FAILURE,
                    claim_raw=claim_raw,
                    transcript_raw=transcript_raw,
                    final_record_sha256=writer.previous,
                    event_count=writer.count,
                )
                _atomic_write_new(paths.terminal, _canonical(terminal))
                recompute_h25_administrative_lifecycle_result(paths.root)
                return _result(
                    paths, scenario, H25_ADMIN_FAILURE, True, writer.count
                )
            if scenario.fault in {
                "OPERATIONAL_ERROR_AT_P1",
                "TIMEOUT_INCONCLUSIVE_CLOSURE",
            } and boundary == "P1_boundary":
                raise _InjectedAdministrativeFailure(
                    "OPERATIONAL_ERROR_AT_P1", boundary
                )
            writer.boundary(boundary)

        if scenario.fault == "TIMEOUT_SUCCESS_CLOSURE":
            raise _InjectedAdministrativeFailure(
                "TIMEOUT_SUCCESS_CLOSURE", "success_closure"
            )
        transcript_raw = writer.publish()
        terminal = _terminal_payload(
            scenario,
            status=H25_ADMIN_SUCCESS,
            claim_raw=claim_raw,
            transcript_raw=transcript_raw,
            final_record_sha256=writer.previous,
            event_count=writer.count,
        )
        if scenario.fault == "TERMINAL_PUBLISH_FAIL":
            raise _InjectedAdministrativeFailure(
                "TERMINAL_PUBLISH_FAIL", "terminal_publish"
            )
        _atomic_write_new(paths.terminal, _canonical(terminal))
        recompute_h25_administrative_lifecycle_result(paths.root)
        return _result(paths, scenario, H25_ADMIN_SUCCESS, True, writer.count)
    except _InjectedAdministrativeFailure as failure:
        if scenario.fault == "TIMEOUT_INCONCLUSIVE_CLOSURE":
            writer.close()
            _write_forensic(
                paths,
                scenario,
                claim_raw=claim_raw,
                failure=failure,
                event_count=writer.count,
                final_record_sha256=writer.previous,
            )
            return _result(
                paths,
                scenario,
                H25_ADMIN_FORENSIC_INCONCLUSIVE,
                True,
                writer.count,
            )
        try:
            writer.append(
                "OPERATIONAL_ERROR",
                state="INCONCLUSIVE",
                detail=str(failure),
            )
            passed = {
                record.get("boundary")
                for record in _read_transcript_records(paths.transcript_staging)
                if record.get("event") == "BOUNDARY_PASSED"
            }
            for boundary in H25_ADMIN_BOUNDARIES:
                if boundary not in passed:
                    writer.append(
                        "BOUNDARY_NOT_RUN",
                        boundary=boundary,
                        state="NOT_RUN_BY_OPERATIONAL_FAILURE",
                    )
            if scenario.fault == "TIMEOUT_INCONCLUSIVE_CLOSURE":
                raise _InjectedAdministrativeFailure(
                    scenario.fault, "inconclusive_closure"
                )
            transcript_raw = writer.publish()
            terminal = _terminal_payload(
                scenario,
                status=H25_ADMIN_INCONCLUSIVE,
                claim_raw=claim_raw,
                transcript_raw=transcript_raw,
                final_record_sha256=writer.previous,
                event_count=writer.count,
            )
            if scenario.fault == "TERMINAL_PUBLISH_FAIL":
                raise _InjectedAdministrativeFailure(
                    scenario.fault, "terminal_publish"
                )
            _atomic_write_new(paths.terminal, _canonical(terminal))
            recompute_h25_administrative_lifecycle_result(paths.root)
            return _result(
                paths, scenario, H25_ADMIN_INCONCLUSIVE, True, writer.count
            )
        except (
            OSError,
            RuntimeError,
            _InjectedAdministrativeFailure,
            ValueError,
        ) as close_error:
            writer.close()
            _write_forensic(
                paths,
                scenario,
                claim_raw=claim_raw,
                failure=close_error,
                event_count=writer.count,
                final_record_sha256=writer.previous,
            )
            return _result(
                paths,
                scenario,
                H25_ADMIN_FORENSIC_INCONCLUSIVE,
                True,
                writer.count,
            )
    finally:
        writer.close()


def _read_transcript_records(path: Path) -> list[dict[str, object]]:
    raw = path.read_bytes()
    return [
        _parse_canonical(line, f"transcript record {index}")
        for index, line in enumerate(raw.splitlines(keepends=True))
    ]


def recompute_h25_administrative_lifecycle_result(root: Path) -> Mapping[str, object]:
    """Independently recompute one completed administrative result."""

    candidate = Path(root)
    if not candidate.is_absolute() or not _ROOT_PATTERN.fullmatch(candidate.name):
        raise ValueError("H25 recomputation root is invalid.")
    parent = candidate.parent.resolve(strict=True)
    success = parent / candidate.name
    claim = parent / f"{candidate.name}.surrogate-claim.json"
    terminal = parent / f"{candidate.name}.terminal.json"
    forensic = parent / f"{candidate.name}.forensic.json"
    staging = parent / f"{candidate.name}.staging"

    claim_raw = claim.read_bytes() if claim.exists() else None
    if claim_raw is not None:
        claim_payload = _parse_canonical(claim_raw, "surrogate claim")
        if (
            claim_payload.get("purpose")
            != "h25_preclaim_administrative_lifecycle_surrogate_claim"
            or claim_payload.get("claim_state")
            != "ADMINISTRATIVE_SURROGATE_CLAIMED"
            or claim_payload.get("scientific_capability_issued") is not False
            or claim_payload.get("scientific_claim_created") is not False
            or claim_payload.get("scientific_population_used") is not False
            or claim_payload.get("real_data_used") is not False
            or claim_payload.get("locked_test_used") is not False
            or claim_payload.get("training_authorized") is not False
        ):
            raise ValueError("H25 surrogate claim crosses the scientific boundary.")

    if terminal.exists():
        terminal_raw = terminal.read_bytes()
        payload = _parse_canonical(terminal_raw, "terminal")
        transcript_raw: bytes | None = None
        final_record = _ZERO_SHA
        count = 0
        if success.exists():
            transcript = success / "administrative_transcript.jsonl"
            count, final_record, transcript_raw = _recompute_transcript(transcript)
            records = _read_transcript_records(transcript)
            for record in records:
                relative = record.get("evidence_path")
                digest = record.get("evidence_sha256")
                if relative is None:
                    if digest is not None:
                        raise ValueError("H25 transcript has an unbound evidence digest.")
                    continue
                if type(relative) is not str or not relative.startswith("evidence/"):
                    raise ValueError("H25 evidence path is invalid.")
                evidence_path = (success / relative).resolve(strict=True)
                evidence_path.relative_to(success.resolve(strict=True))
                evidence_raw = evidence_path.read_bytes()
                _parse_canonical(evidence_raw, f"evidence {relative}")
                if digest != _sha(evidence_raw):
                    raise ValueError("H25 transcript evidence binding mismatch.")
            scenario_ids = {record["scenario_id"] for record in records}
            faults = {record["fault"] for record in records}
            if scenario_ids != {payload.get("scenario_id")} or faults != {
                payload.get("fault")
            }:
                raise ValueError("H25 terminal scenario differs from transcript.")
        if payload.get("surrogate_claim_sha256") != (
            None if claim_raw is None else _sha(claim_raw)
        ):
            raise ValueError("H25 terminal claim binding mismatch.")
        if payload.get("transcript_sha256") != (
            None if transcript_raw is None else _sha(transcript_raw)
        ):
            raise ValueError("H25 terminal transcript binding mismatch.")
        if payload.get("event_count") != count:
            raise ValueError("H25 terminal event count mismatch.")
        if payload.get("final_record_sha256") != final_record:
            raise ValueError("H25 terminal final hash mismatch.")
        if (
            payload.get("purpose")
            != "h25_preclaim_administrative_lifecycle_terminal"
            or payload.get("scientific_execution_used") is not False
            or payload.get("real_data_used") is not False
            or payload.get("locked_test_used") is not False
            or payload.get("training_used") is not False
            or payload.get("status")
            not in {
                H25_ADMIN_SUCCESS,
                H25_ADMIN_FAILURE,
                H25_ADMIN_INCONCLUSIVE,
                H25_ADMIN_PRECLAIM_ABORTED,
            }
        ):
            raise ValueError("H25 terminal semantics are invalid.")
        if staging.exists():
            raise ValueError("H25 terminal result retains staging.")
        return {
            "artifact": "terminal",
            "event_count": count,
            "fault": payload.get("fault"),
            "scenario_id": payload.get("scenario_id"),
            "status": payload.get("status"),
            "surrogate_claim_consumed": claim_raw is not None,
            "terminal_sha256": _sha(terminal_raw),
            "transcript_sha256": None
            if transcript_raw is None
            else _sha(transcript_raw),
        }

    if forensic.exists():
        forensic_raw = forensic.read_bytes()
        payload = _parse_canonical(forensic_raw, "forensic receipt")
        if claim_raw is None or payload.get("surrogate_claim_sha256") != _sha(
            claim_raw
        ):
            raise ValueError("H25 forensic claim binding mismatch.")
        transcript_candidates = (
            success / "administrative_transcript.jsonl",
            staging / "administrative_transcript.jsonl",
            staging / "administrative_transcript.jsonl.part",
        )
        transcript_path = next(
            (item for item in transcript_candidates if item.exists()), None
        )
        transcript_raw = None if transcript_path is None else transcript_path.read_bytes()
        if payload.get("transcript_sha256") != (
            None if transcript_raw is None else _sha(transcript_raw)
        ):
            raise ValueError("H25 forensic transcript binding mismatch.")
        if transcript_path is not None:
            count, final_record, _ = _recompute_transcript(transcript_path)
            if (
                payload.get("event_count") != count
                or payload.get("final_record_sha256") != final_record
            ):
                raise ValueError("H25 forensic transcript summary mismatch.")
        if (
            payload.get("purpose")
            != "h25_preclaim_administrative_lifecycle_forensic_receipt"
            or payload.get("scientific_execution_used") is not False
            or payload.get("status") != H25_ADMIN_FORENSIC_INCONCLUSIVE
        ):
            raise ValueError("H25 forensic semantics are invalid.")
        return {
            "artifact": "forensic",
            "event_count": payload.get("event_count"),
            "fault": payload.get("fault"),
            "scenario_id": payload.get("scenario_id"),
            "status": payload.get("status"),
            "surrogate_claim_consumed": True,
            "forensic_sha256": _sha(forensic_raw),
        }

    raise FileNotFoundError("H25 administrative result has no terminal or forensic receipt.")


class _RealOSInterruption(RuntimeError):
    pass


def _marker_path(root: Path, name: str) -> Path:
    return root.parent / f"{root.name}.{name}.json"


def _write_marker(root: Path, name: str, payload: Mapping[str, object]) -> Path:
    path = _marker_path(root, name)
    _atomic_write_new(
        path,
        _canonical(
            {
                "marker": name,
                "purpose": "h25_real_os_lifecycle_probe_marker",
                "schema_version": H25_ADMIN_SCHEMA_VERSION,
                **dict(payload),
            }
        ),
    )
    return path


def _wait_for_path(path: Path, deadline_seconds: float) -> None:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        if path.exists():
            return
        time.sleep(0.01)
    raise TimeoutError(f"H25 timed out waiting for {path.name}.")


def _read_control_byte(expected: bytes, label: str) -> None:
    value = sys.stdin.buffer.read(1)
    if value != expected:
        raise _RealOSInterruption(
            f"H25 control {label} expected {expected!r}, observed {value!r}."
        )


def _wait_real_timeout(
    root: Path,
    stage: str,
    timeout_seconds: float,
    probe: str,
) -> None:
    started = time.monotonic()
    _write_marker(
        root,
        f"timeout-{stage}-ready",
        {"probe": probe, "stage": stage},
    )
    _read_control_byte(b"T", f"timeout {stage}")
    elapsed = time.monotonic() - started
    if elapsed < timeout_seconds:
        raise ValueError("H25 timeout control arrived before the real deadline.")
    raise _InjectedAdministrativeFailure(probe, stage)


def _close_worker_inconclusive(
    paths: _Paths,
    scenario: H25AdministrativeQualificationScenario,
    writer: _Transcript,
    claim_raw: bytes,
    failure: BaseException,
    *,
    force_forensic: bool = False,
) -> str:
    if force_forensic:
        writer.close()
        _write_forensic(
            paths,
            scenario,
            claim_raw=claim_raw,
            failure=failure,
            event_count=writer.count,
            final_record_sha256=writer.previous,
        )
        return H25_ADMIN_FORENSIC_INCONCLUSIVE
    writer.append(
        "OPERATIONAL_ERROR",
        state="INCONCLUSIVE",
        detail=str(failure),
    )
    records = _read_transcript_records(paths.transcript_staging)
    passed = {
        record.get("boundary")
        for record in records
        if record.get("event") == "BOUNDARY_PASSED"
    }
    for boundary in H25_ADMIN_BOUNDARIES:
        if boundary not in passed:
            writer.append(
                "BOUNDARY_NOT_RUN",
                boundary=boundary,
                state="NOT_RUN_BY_OPERATIONAL_FAILURE",
            )
    transcript_raw = writer.publish()
    terminal = _terminal_payload(
        scenario,
        status=H25_ADMIN_INCONCLUSIVE,
        claim_raw=claim_raw,
        transcript_raw=transcript_raw,
        final_record_sha256=writer.previous,
        event_count=writer.count,
    )
    _atomic_write_new(paths.terminal, _canonical(terminal))
    recompute_h25_administrative_lifecycle_result(paths.root)
    return H25_ADMIN_INCONCLUSIVE


def _write_preclaim_worker_terminal(
    paths: _Paths,
    scenario: H25AdministrativeQualificationScenario,
) -> None:
    terminal = _terminal_payload(
        scenario,
        status=H25_ADMIN_PRECLAIM_ABORTED,
        claim_raw=None,
        transcript_raw=None,
        final_record_sha256=_ZERO_SHA,
        event_count=0,
    )
    _atomic_write_new(paths.terminal, _canonical(terminal))


def _run_h25_real_os_worker(config_path: Path) -> int:
    config_raw = Path(config_path).read_bytes()
    config = _parse_canonical(config_raw, "real-OS worker config")
    expected_keys = {
        "probe",
        "probe_id",
        "process_deadline_seconds",
        "purpose",
        "root",
        "schema_version",
        "timeout_seconds",
    }
    if set(config) != expected_keys:
        raise ValueError("H25 real-OS worker config key set mismatch.")
    if config["purpose"] != "h25_real_os_lifecycle_worker_config":
        raise ValueError("H25 real-OS worker config purpose mismatch.")
    probe = H25RealOSQualificationProbe(
        probe_id=str(config["probe_id"]),
        probe=str(config["probe"]),
        timeout_seconds=float(config["timeout_seconds"]),
        process_deadline_seconds=float(config["process_deadline_seconds"]),
    )
    root = Path(str(config["root"]))
    paths = _derive_paths(root)
    synthetic_fault = _REAL_TO_SYNTHETIC_FAULT[probe.probe]
    scenario = H25AdministrativeQualificationScenario(
        scenario_id=probe.probe_id,
        fault=synthetic_fault,
    )

    interrupted: list[str] = []

    def handle_signal(signum: int, _frame: object) -> None:
        interrupted.append(str(signum))
        raise _RealOSInterruption(f"real OS signal {signum}")

    previous_handlers: dict[int, object] = {}
    handled_signals = [signal.SIGINT]
    if hasattr(signal, "SIGBREAK"):
        handled_signals.append(signal.SIGBREAK)
    for item in handled_signals:
        previous_handlers[item] = signal.getsignal(item)
        signal.signal(item, handle_signal)

    writer: _Transcript | None = None
    claim_raw: bytes | None = None
    try:
        if probe.probe == "REAL_TIMEOUT_PREFLIGHT":
            try:
                _wait_real_timeout(
                    root, "preflight", probe.timeout_seconds, probe.probe
                )
            except _InjectedAdministrativeFailure:
                _write_preclaim_worker_terminal(paths, scenario)
                return 0

        _write_marker(
            root,
            "preclaim-ready",
            {"probe": probe.probe, "probe_id": probe.probe_id},
        )
        control = sys.stdin.buffer.read(1)
        if probe.probe == "REAL_EOF_BEFORE_SURROGATE_CLAIM":
            if control != b"":
                raise ValueError("H25 expected a real preclaim EOF.")
            _write_preclaim_worker_terminal(paths, scenario)
            return 0
        if control != b"C":
            raise _RealOSInterruption(
                f"preclaim transport ended unexpectedly with {control!r}"
            )

        if probe.probe == "REAL_TIMEOUT_SURROGATE_CLAIM":
            try:
                _wait_real_timeout(
                    root, "surrogate_claim", probe.timeout_seconds, probe.probe
                )
            except _InjectedAdministrativeFailure:
                _write_preclaim_worker_terminal(paths, scenario)
                return 0

        claim_raw = _canonical(_claim_payload(scenario))
        _write_new(paths.claim, claim_raw)
        writer = _Transcript(paths, scenario)
        writer.append("PREFLIGHT_PASSED")
        writer.append("SURROGATE_CLAIM_ACQUIRED")
        _write_marker(
            root,
            "after-claim-ready",
            {"probe": probe.probe, "probe_id": probe.probe_id},
        )

        if probe.probe in {
            "REAL_EOF_AFTER_SURROGATE_CLAIM",
            "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM",
            "REAL_SIGINT_AFTER_SURROGATE_CLAIM",
        }:
            try:
                control = sys.stdin.buffer.read(1)
                if probe.probe in {
                    "REAL_EOF_AFTER_SURROGATE_CLAIM",
                    "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM",
                } and control != b"":
                    raise ValueError("H25 expected a real postclaim EOF.")
                if probe.probe == "REAL_SIGINT_AFTER_SURROGATE_CLAIM":
                    raise ValueError("H25 SIGINT wait returned without a signal.")
                raise _RealOSInterruption("real postclaim transport EOF")
            except _RealOSInterruption as failure:
                _close_worker_inconclusive(
                    paths, scenario, writer, claim_raw, failure
                )
                return 0

        _read_control_byte(b"C", "postclaim continuation")

        timeout_stage = _REAL_TIMEOUT_STAGE.get(probe.probe)
        for boundary in H25_ADMIN_BOUNDARIES:
            if timeout_stage == boundary:
                try:
                    _wait_real_timeout(
                        root, boundary, probe.timeout_seconds, probe.probe
                    )
                except _InjectedAdministrativeFailure as failure:
                    _close_worker_inconclusive(
                        paths, scenario, writer, claim_raw, failure
                    )
                    return 0
            if timeout_stage == "failure_closure" and boundary == "P1_boundary":
                writer.append(
                    "BOUNDARY_LOGICAL_FAILURE",
                    boundary=boundary,
                    state="FAILED",
                )
                writer.append_not_run_suffix("P2_boundary")
                try:
                    _wait_real_timeout(
                        root,
                        "failure_closure",
                        probe.timeout_seconds,
                        probe.probe,
                    )
                except _InjectedAdministrativeFailure as failure:
                    _close_worker_inconclusive(
                        paths,
                        scenario,
                        writer,
                        claim_raw,
                        failure,
                        force_forensic=True,
                    )
                    return 0
            if timeout_stage == "inconclusive_closure" and boundary == "P1_boundary":
                failure = _InjectedAdministrativeFailure(
                    probe.probe, "P1_boundary"
                )
                writer.append(
                    "OPERATIONAL_ERROR",
                    state="INCONCLUSIVE",
                    detail=str(failure),
                )
                writer.append_not_run_suffix("P1_boundary")
                try:
                    _wait_real_timeout(
                        root,
                        "inconclusive_closure",
                        probe.timeout_seconds,
                        probe.probe,
                    )
                except _InjectedAdministrativeFailure as close_failure:
                    _close_worker_inconclusive(
                        paths,
                        scenario,
                        writer,
                        claim_raw,
                        close_failure,
                        force_forensic=True,
                    )
                    return 0
            writer.boundary(boundary)

        if timeout_stage == "success_closure":
            try:
                _wait_real_timeout(
                    root,
                    "success_closure",
                    probe.timeout_seconds,
                    probe.probe,
                )
            except _InjectedAdministrativeFailure as failure:
                _close_worker_inconclusive(
                    paths, scenario, writer, claim_raw, failure
                )
                return 0

        transcript_raw = writer.publish()
        terminal = _terminal_payload(
            scenario,
            status=H25_ADMIN_SUCCESS,
            claim_raw=claim_raw,
            transcript_raw=transcript_raw,
            final_record_sha256=writer.previous,
            event_count=writer.count,
        )
        _atomic_write_new(paths.terminal, _canonical(terminal))
        recompute_h25_administrative_lifecycle_result(root)
        return 0
    except _RealOSInterruption as failure:
        if writer is None or claim_raw is None:
            _write_preclaim_worker_terminal(paths, scenario)
        else:
            _close_worker_inconclusive(paths, scenario, writer, claim_raw, failure)
        return 0
    finally:
        if writer is not None:
            writer.close()
        for item, previous in previous_handlers.items():
            signal.signal(item, previous)


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        handle = ctypes.windll.kernel32.OpenProcess(
            process_query_limited_information, False, pid
        )
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not ctypes.windll.kernel32.GetExitCodeProcess(
                handle, ctypes.byref(exit_code)
            ):
                return False
            return exit_code.value == still_active
        finally:
            ctypes.windll.kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    return True


def _wait_for_pid_dead(pid: int, deadline_seconds: float) -> None:
    deadline = time.monotonic() + deadline_seconds
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return
        time.sleep(0.02)
    raise TimeoutError(f"H25 worker PID {pid} remained alive.")


def _worker_command(config_path: Path) -> list[str]:
    return [
        sys.executable,
        "-m",
        "src.polyphonic.harmonic_censoring_h25_lifecycle_qualification",
        "--worker",
        str(config_path),
    ]


def _new_process_group_flags() -> int:
    return (
        int(getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0))
        if os.name == "nt"
        else 0
    )


def _send_real_interrupt(process: subprocess.Popen[bytes]) -> None:
    if os.name == "nt":
        process.send_signal(signal.CTRL_BREAK_EVENT)
    else:
        process.send_signal(signal.SIGINT)


def _write_worker_exit_marker(config_path: Path, exit_code: int) -> None:
    config = _parse_canonical(config_path.read_bytes(), "worker exit config")
    root = Path(str(config["root"]))
    path = _marker_path(root, "worker-exited")
    if not path.exists():
        _atomic_write_new(
            path,
            _canonical(
                {
                    "exit_code": exit_code,
                    "probe": config["probe"],
                    "probe_id": config["probe_id"],
                    "purpose": "h25_real_os_lifecycle_worker_exit",
                    "schema_version": H25_ADMIN_SCHEMA_VERSION,
                    "worker_pid": os.getpid(),
                }
            ),
        )


def _run_transport_parent(config_path: Path) -> int:
    config = _parse_canonical(config_path.read_bytes(), "transport parent config")
    root = Path(str(config["root"]))
    log_path = _marker_path(root, "worker-log")
    pid_path = _marker_path(root, "worker-pid")
    with log_path.open("xb") as log:
        worker = subprocess.Popen(
            _worker_command(config_path),
            cwd=Path(__file__).resolve().parents[2],
            stdin=subprocess.PIPE,
            stdout=log,
            stderr=subprocess.STDOUT,
            creationflags=_new_process_group_flags(),
        )
        _atomic_write_new(
            pid_path,
            _canonical(
                {
                    "purpose": "h25_real_os_lifecycle_worker_pid",
                    "schema_version": H25_ADMIN_SCHEMA_VERSION,
                    "worker_pid": worker.pid,
                }
            ),
        )
        _wait_for_path(
            _marker_path(root, "preclaim-ready"),
            float(config.get("process_deadline_seconds", 10.0)),
        )
        assert worker.stdin is not None
        worker.stdin.write(b"C")
        worker.stdin.flush()
        _wait_for_path(
            _marker_path(root, "after-claim-ready"),
            float(config.get("process_deadline_seconds", 10.0)),
        )
        os._exit(0)


def run_h25_real_os_lifecycle_qualification_probe(
    parent: Path,
    probe: H25RealOSQualificationProbe,
) -> H25RealOSQualificationProbeResult:
    """Exercise one real process/transport/signal/timeout administrative probe."""

    if type(probe) is not H25RealOSQualificationProbe:
        raise TypeError("H25 real-OS qualification requires the exact probe type.")
    resolved_parent = Path(parent).resolve(strict=True)
    root = resolved_parent / f"h25-admin-{probe.probe_id}"
    config_path = resolved_parent / f"{root.name}.worker-config.json"
    controller_receipt = resolved_parent / f"{root.name}.controller-receipt.json"
    log_path = _marker_path(root, "worker-log")
    for path in (config_path, controller_receipt, log_path):
        if path.exists():
            raise FileExistsError(f"H25 real-OS controller path exists: {path}.")
    config = {
        "probe": probe.probe,
        "probe_id": probe.probe_id,
        "process_deadline_seconds": probe.process_deadline_seconds,
        "purpose": "h25_real_os_lifecycle_worker_config",
        "root": str(root),
        "schema_version": H25_ADMIN_SCHEMA_VERSION,
        "timeout_seconds": probe.timeout_seconds,
    }
    _write_new(config_path, _canonical(config))
    started = time.monotonic()
    child_pid = 0
    child_exit_code = -1

    if probe.probe == "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM":
        helper = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "src.polyphonic.harmonic_censoring_h25_lifecycle_qualification",
                "--transport-parent",
                str(config_path),
            ],
            cwd=Path(__file__).resolve().parents[2],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=_new_process_group_flags(),
        )
        helper.wait(timeout=probe.process_deadline_seconds)
        pid_payload = _parse_canonical(
            _marker_path(root, "worker-pid").read_bytes(), "worker pid"
        )
        child_pid = int(pid_payload["worker_pid"])
        exit_marker = _marker_path(root, "worker-exited")
        _wait_for_path(exit_marker, probe.process_deadline_seconds)
        exit_payload = _parse_canonical(exit_marker.read_bytes(), "worker exit")
        child_exit_code = int(exit_payload["exit_code"])
        _wait_for_pid_dead(child_pid, probe.process_deadline_seconds)
    else:
        with log_path.open("xb") as log:
            child = subprocess.Popen(
                _worker_command(config_path),
                cwd=Path(__file__).resolve().parents[2],
                stdin=subprocess.PIPE,
                stdout=log,
                stderr=subprocess.STDOUT,
                creationflags=_new_process_group_flags(),
            )
            child_pid = child.pid
            assert child.stdin is not None
            try:
                if probe.probe == "REAL_TIMEOUT_PREFLIGHT":
                    stage = "preflight"
                    _wait_for_path(
                        _marker_path(root, f"timeout-{stage}-ready"),
                        probe.process_deadline_seconds,
                    )
                    time.sleep(probe.timeout_seconds)
                    child.stdin.write(b"T")
                    child.stdin.flush()
                else:
                    _wait_for_path(
                        _marker_path(root, "preclaim-ready"),
                        probe.process_deadline_seconds,
                    )
                    if probe.probe == "REAL_EOF_BEFORE_SURROGATE_CLAIM":
                        child.stdin.close()
                    else:
                        child.stdin.write(b"C")
                        child.stdin.flush()
                        if probe.probe == "REAL_TIMEOUT_SURROGATE_CLAIM":
                            stage = "surrogate_claim"
                            _wait_for_path(
                                _marker_path(root, f"timeout-{stage}-ready"),
                                probe.process_deadline_seconds,
                            )
                            time.sleep(probe.timeout_seconds)
                            child.stdin.write(b"T")
                            child.stdin.flush()
                        else:
                            _wait_for_path(
                                _marker_path(root, "after-claim-ready"),
                                probe.process_deadline_seconds,
                            )
                            if probe.probe == "REAL_EOF_AFTER_SURROGATE_CLAIM":
                                child.stdin.close()
                            elif probe.probe == "REAL_SIGINT_AFTER_SURROGATE_CLAIM":
                                _send_real_interrupt(child)
                            else:
                                child.stdin.write(b"C")
                                child.stdin.flush()
                                timeout_stage = _REAL_TIMEOUT_STAGE.get(probe.probe)
                                if timeout_stage is not None:
                                    _wait_for_path(
                                        _marker_path(
                                            root,
                                            f"timeout-{timeout_stage}-ready",
                                        ),
                                        probe.process_deadline_seconds,
                                    )
                                    time.sleep(probe.timeout_seconds)
                                    child.stdin.write(b"T")
                                    child.stdin.flush()
                child_exit_code = child.wait(
                    timeout=probe.process_deadline_seconds
                )
            except BaseException:
                if child.poll() is None:
                    child.kill()
                    child.wait(timeout=probe.process_deadline_seconds)
                raise
            finally:
                if child.stdin is not None and not child.stdin.closed:
                    child.stdin.close()
        _wait_for_pid_dead(child_pid, probe.process_deadline_seconds)

    if child_exit_code != 0:
        diagnostic = log_path.read_text(encoding="utf-8", errors="replace")
        raise RuntimeError(
            f"H25 real-OS worker exited {child_exit_code}: {diagnostic}"
        )
    recomputed = recompute_h25_administrative_lifecycle_result(root)
    elapsed = time.monotonic() - started
    log_raw = log_path.read_bytes() if log_path.exists() else b""
    exit_marker_path = _marker_path(root, "worker-exited")
    exit_marker_raw = exit_marker_path.read_bytes()
    exit_marker = _parse_canonical(exit_marker_raw, "worker exit")
    if (
        exit_marker.get("worker_pid") != child_pid
        or exit_marker.get("exit_code") != child_exit_code
        or exit_marker.get("probe") != probe.probe
        or exit_marker.get("probe_id") != probe.probe_id
    ):
        raise ValueError("H25 worker exit marker differs from the process result.")
    receipt = {
        "child_exit_code": child_exit_code,
        "child_pid": child_pid,
        "child_process_alive": _pid_alive(child_pid),
        "config_sha256": _sha(config_path.read_bytes()),
        "elapsed_seconds": elapsed,
        "log_sha256": _sha(log_raw),
        "probe": probe.probe,
        "probe_id": probe.probe_id,
        "purpose": "h25_real_os_lifecycle_controller_receipt",
        "result_artifact": recomputed["artifact"],
        "result_status": recomputed["status"],
        "schema_version": H25_ADMIN_SCHEMA_VERSION,
        "worker_exit_marker_sha256": _sha(exit_marker_raw),
    }
    if receipt["child_process_alive"] is not False:
        raise RuntimeError("H25 real-OS worker remains alive after result.")
    _atomic_write_new(controller_receipt, _canonical(receipt))
    recompute_h25_real_os_lifecycle_probe_result(controller_receipt)
    return H25RealOSQualificationProbeResult(
        probe_id=probe.probe_id,
        probe=probe.probe,
        status=str(recomputed["status"]),
        child_pid=child_pid,
        child_exit_code=child_exit_code,
        child_process_alive=False,
        elapsed_seconds=elapsed,
        root=root,
        controller_receipt_path=controller_receipt,
    )


def recompute_h25_real_os_lifecycle_probe_result(
    controller_receipt_path: Path,
) -> Mapping[str, object]:
    path = Path(controller_receipt_path).resolve(strict=True)
    raw = path.read_bytes()
    payload = _parse_canonical(raw, "real-OS controller receipt")
    expected_keys = {
        "child_exit_code",
        "child_pid",
        "child_process_alive",
        "config_sha256",
        "elapsed_seconds",
        "log_sha256",
        "probe",
        "probe_id",
        "purpose",
        "result_artifact",
        "result_status",
        "schema_version",
        "worker_exit_marker_sha256",
    }
    if set(payload) != expected_keys:
        raise ValueError("H25 controller receipt key set mismatch.")
    if (
        payload["purpose"] != "h25_real_os_lifecycle_controller_receipt"
        or payload["schema_version"] != H25_ADMIN_SCHEMA_VERSION
        or payload["probe"] not in H25_REAL_OS_PROBES
        or type(payload["probe_id"]) is not str
        or not _SCENARIO_PATTERN.fullmatch(payload["probe_id"])
        or payload["child_exit_code"] != 0
        or payload["child_process_alive"] is not False
        or type(payload["child_pid"]) is not int
        or type(payload["child_pid"]) is bool
        or payload["child_pid"] <= 0
        or type(payload["elapsed_seconds"]) not in {int, float}
        or type(payload["elapsed_seconds"]) is bool
        or not math.isfinite(float(payload["elapsed_seconds"]))
        or payload["elapsed_seconds"] <= 0
    ):
        raise ValueError("H25 controller receipt process semantics are invalid.")
    root = path.parent / f"h25-admin-{payload['probe_id']}"
    config = path.parent / f"{root.name}.worker-config.json"
    log = _marker_path(root, "worker-log")
    exit_marker_path = _marker_path(root, "worker-exited")
    if _sha(config.read_bytes()) != payload["config_sha256"]:
        raise ValueError("H25 controller config binding mismatch.")
    if _sha(log.read_bytes() if log.exists() else b"") != payload["log_sha256"]:
        raise ValueError("H25 controller log binding mismatch.")
    exit_marker_raw = exit_marker_path.read_bytes()
    if _sha(exit_marker_raw) != payload["worker_exit_marker_sha256"]:
        raise ValueError("H25 controller exit marker binding mismatch.")
    exit_marker = _parse_canonical(exit_marker_raw, "worker exit")
    if (
        exit_marker.get("worker_pid") != payload["child_pid"]
        or exit_marker.get("exit_code") != payload["child_exit_code"]
        or exit_marker.get("probe") != payload["probe"]
        or exit_marker.get("probe_id") != payload["probe_id"]
    ):
        raise ValueError("H25 controller exit marker semantics mismatch.")
    recomputed = recompute_h25_administrative_lifecycle_result(root)
    if (
        payload["result_artifact"],
        payload["result_status"],
        payload["probe_id"],
        _REAL_TO_SYNTHETIC_FAULT[str(payload["probe"])],
    ) != (
        recomputed["artifact"],
        recomputed["status"],
        recomputed["scenario_id"],
        recomputed["fault"],
    ):
        raise ValueError("H25 controller result binding mismatch.")
    return payload


def _main(argv: Sequence[str] | None = None) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    if len(arguments) != 2 or arguments[0] not in {
        "--worker",
        "--transport-parent",
    }:
        raise SystemExit("H25 lifecycle module is not a public qualification CLI.")
    config_path = Path(arguments[1]).resolve(strict=True)
    if arguments[0] == "--transport-parent":
        return _run_transport_parent(config_path)
    exit_code = 1
    try:
        exit_code = _run_h25_real_os_worker(config_path)
        return exit_code
    finally:
        _write_worker_exit_marker(config_path, exit_code)


__all__ = [
    "H25_ADMIN_BOUNDARIES",
    "H25_ADMIN_FAILURE",
    "H25_ADMIN_FAULTS",
    "H25_ADMIN_FORENSIC_INCONCLUSIVE",
    "H25_ADMIN_INCONCLUSIVE",
    "H25_ADMIN_PRECLAIM_ABORTED",
    "H25_ADMIN_SUCCESS",
    "H25_REAL_OS_PROBES",
    "H25AdministrativeQualificationResult",
    "H25AdministrativeQualificationScenario",
    "H25RealOSQualificationProbe",
    "H25RealOSQualificationProbeResult",
    "recompute_h25_administrative_lifecycle_result",
    "recompute_h25_real_os_lifecycle_probe_result",
    "run_h25_preclaim_administrative_lifecycle_qualification",
    "run_h25_real_os_lifecycle_qualification_probe",
]


if __name__ == "__main__":
    raise SystemExit(_main())
