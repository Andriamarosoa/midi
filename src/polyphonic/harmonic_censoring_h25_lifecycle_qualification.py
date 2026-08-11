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
import os
import re
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
            "status": payload.get("status"),
            "surrogate_claim_consumed": True,
            "forensic_sha256": _sha(forensic_raw),
        }

    raise FileNotFoundError("H25 administrative result has no terminal or forensic receipt.")


__all__ = [
    "H25_ADMIN_BOUNDARIES",
    "H25_ADMIN_FAILURE",
    "H25_ADMIN_FAULTS",
    "H25_ADMIN_FORENSIC_INCONCLUSIVE",
    "H25_ADMIN_INCONCLUSIVE",
    "H25_ADMIN_PRECLAIM_ABORTED",
    "H25_ADMIN_SUCCESS",
    "H25AdministrativeQualificationResult",
    "H25AdministrativeQualificationScenario",
    "recompute_h25_administrative_lifecycle_result",
    "run_h25_preclaim_administrative_lifecycle_qualification",
]
