"""Dormant H24 scientific runner and persisted-proof finalizer.

Evidence production is intentionally unavailable in this commit.  The public
entry therefore fails before the durable scientific claim.  Transcript,
evidence and finalizer primitives are implemented for static/mock review only.
"""
from __future__ import annotations

import hashlib
import importlib
import json
import os
from pathlib import Path
from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping, Sequence

from .harmonic_censoring_h24 import H24DormantHarnessPlan, load_h24_dormant_harness_plan
from .harmonic_censoring_h24_operators import recompute_h24_persisted_evidence
from .harmonic_censoring_h24_scientific_capability import (
    AttestedH24ScientificExecutionCapability,
    claim_h24_scientific_execution,
    issue_h24_scientific_execution_capability,
    require_attested_h24_scientific_capability,
    require_claimed_h24_scientific_capability,
)


H24_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED = True
H24_EVIDENCE_PRODUCER_REGISTRY_IMPLEMENTED = False
H24_SUCCESS_STATUS = "AUTHORIZED_TO_PREPARE_H24_TRAIN_PROTOCOL"
H24_P0_KILL_STATUS = "H24_SYNTHETIC_HYPOTHESIS_KILLED"
H24_READINESS_STATUS = "H24_PRETRAIN_READINESS_NOT_DEMONSTRATED"
H24_INCONCLUSIVE_STATUS = "H24_EXECUTION_INCONCLUSIVE_CONSUMED"
_ZERO_SHA = "0" * 64
_RECORD_KEYS = {
    "evidence_byte_count",
    "evidence_path",
    "evidence_raw_sha256",
    "operational_error_class",
    "operational_error_message_sha256",
    "phase",
    "previous_record_sha256",
    "record_state",
    "schema_version",
    "sequence_index",
    "test_id",
}
_TERMINAL_KEYS = {
    "executed_evidence_record_count",
    "final_record_sha256",
    "first_failed_sequence_index",
    "first_failed_test_id",
    "not_run_by_kill_rule_count",
    "not_run_by_operational_failure_count",
    "operational_error_count",
    "ordered_evidence_bindings_sha256",
    "ordered_test_ids_sha256",
    "passed_test_count",
    "population_index_sha256",
    "population_marker_sha256",
    "population_receipt_sha256",
    "population_terminal_sha256",
    "schema_version",
    "scientific_execution_claim_sha256",
    "scientific_status",
    "transcript_byte_count",
    "transcript_raw_sha256",
    "transcript_record_count",
    "transcript_validation_status",
}


@dataclass(frozen=True)
class _H24ScientificContext:
    fixture_specs: Mapping[str, Mapping[str, object]]
    fixture_targets: Mapping[str, Mapping[str, object]]
    fixture_waveforms: Mapping[str, object]


_H24_EVIDENCE_PRODUCER_REGISTRY: Mapping[str, object] = MappingProxyType({})


def _require_complete_producer_registry(plan: H24DormantHarnessPlan) -> Mapping[str, object]:
    if tuple(_H24_EVIDENCE_PRODUCER_REGISTRY) != plan.test_ids:
        raise PermissionError(
            "H24 evidence producers remain dormant; scientific claim is forbidden."
        )
    if any(not callable(value) for value in _H24_EVIDENCE_PRODUCER_REGISTRY.values()):
        raise PermissionError("H24 evidence producer registry contains a non-callable.")
    return _H24_EVIDENCE_PRODUCER_REGISTRY


def _canonical(value: object, *, line: bool = True) -> bytes:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return raw + (b"\n" if line else b"")


def _reject_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H24 persisted JSON duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H24 persisted JSON forbids {token!r}.")


def _parse(raw: bytes, label: str, *, canonical_line: bool = True) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H24 {label} must be UTF-8 LF without BOM.")
    if canonical_line and (not raw.endswith(b"\n") or raw.endswith(b"\n\n")):
        raise ValueError(f"H24 {label} must end in exactly one LF.")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict or _canonical(value, line=canonical_line) != raw:
        raise ValueError(f"H24 {label} is not canonical.")
    return value


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _fsync_parent(path: Path) -> None:
    if os.name == "nt":
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    _fsync_parent(path.parent)


def _expected_path(index: int, test_id: str) -> str:
    return f"evidence/{index:02d}_{test_id}.json"


class _H24TranscriptWriter:
    """Private, append-only writer usable only with a claimed capability."""

    __slots__ = ("_capability", "_plan", "_stream", "_next", "_previous", "_published")

    def __init__(self, plan: H24DormantHarnessPlan, capability: object) -> None:
        checked = require_claimed_h24_scientific_capability(capability)
        if plan.test_ids != checked.ordered_test_ids:
            raise ValueError("H24 transcript plan order differs from capability.")
        checked.staging_directory.parent.mkdir(parents=True, exist_ok=True)
        checked.staging_directory.mkdir()
        checked.transcript_staging_path.parent.mkdir(parents=True, exist_ok=True)
        self._stream = checked.transcript_staging_path.open("xb")
        self._capability = checked
        self._plan = plan
        self._next = 0
        self._previous = _ZERO_SHA
        self._published = False

    @property
    def next_index(self) -> int:
        return self._next

    def _append(self, state: str, *, evidence_path: str | None = None, evidence_raw: bytes | None = None, error_class: str | None = None, error_message: str | None = None) -> None:
        if self._published or self._next >= 72:
            raise RuntimeError("H24 transcript cannot accept another record.")
        test = self._plan.tests[self._next]
        if state == "EVIDENCE_PERSISTED":
            if evidence_path != _expected_path(self._next, test.test_id) or evidence_raw is None:
                raise ValueError("H24 evidence binding is not deterministic.")
            evidence_count: int | None = len(evidence_raw)
            evidence_sha: str | None = _sha(evidence_raw)
            error_type = None
            error_sha = None
        elif state == "OPERATIONAL_ERROR":
            if not error_class or error_message is None:
                raise ValueError("H24 operational error evidence is incomplete.")
            evidence_path = None
            evidence_count = None
            evidence_sha = None
            error_type = error_class
            error_sha = _sha(error_message.encode("utf-8"))
        elif state in {"NOT_RUN_BY_KILL_RULE", "NOT_RUN_BY_OPERATIONAL_FAILURE"}:
            evidence_path = None
            evidence_count = None
            evidence_sha = None
            error_type = None
            error_sha = None
        else:
            raise ValueError("H24 transcript state is not sealed.")
        record = {
            "evidence_byte_count": evidence_count,
            "evidence_path": evidence_path,
            "evidence_raw_sha256": evidence_sha,
            "operational_error_class": error_type,
            "operational_error_message_sha256": error_sha,
            "phase": test.phase,
            "previous_record_sha256": self._previous,
            "record_state": state,
            "schema_version": 1,
            "sequence_index": self._next,
            "test_id": test.test_id,
        }
        raw = _canonical(record)
        self._stream.write(raw)
        self._stream.flush()
        os.fsync(self._stream.fileno())
        self._previous = _sha(raw)
        self._next += 1

    def append_evidence(self, evidence: Mapping[str, object]) -> Path:
        if "pass" in evidence or "verdict" in evidence:
            raise ValueError("H24 producer verdict fields are forbidden.")
        test = self._plan.tests[self._next]
        relative = _expected_path(self._next, test.test_id)
        raw = _canonical(dict(evidence))
        path = self._capability.staging_directory / relative
        _write_new(path, raw)
        self._append("EVIDENCE_PERSISTED", evidence_path=relative, evidence_raw=raw)
        return path

    def append_operational_error(self, error: BaseException) -> None:
        self._append(
            "OPERATIONAL_ERROR",
            error_class=f"{type(error).__module__}.{type(error).__qualname__}",
            error_message=str(error),
        )

    def fill_kill_suffix(self) -> None:
        while self._next < 72:
            self._append("NOT_RUN_BY_KILL_RULE")

    def fill_operational_suffix(self) -> None:
        while self._next < 72:
            self._append("NOT_RUN_BY_OPERATIONAL_FAILURE")

    def publish(self) -> Path:
        if self._next != 72:
            raise ValueError("H24 finalized transcript requires exactly 72 records.")
        self._stream.close()
        os.replace(self._capability.transcript_staging_path, self._capability.staging_directory / "scientific_transcript.jsonl")
        _fsync_parent(self._capability.staging_directory)
        if self._capability.success_directory.exists():
            raise FileExistsError("H24 scientific success directory already exists.")
        os.replace(self._capability.staging_directory, self._capability.success_directory)
        _fsync_parent(self._capability.success_directory.parent)
        self._published = True
        if self._capability.transcript_path.read_bytes() == b"":
            raise ValueError("H24 published transcript is empty.")
        return self._capability.transcript_path

    def close(self) -> None:
        if not self._stream.closed:
            self._stream.close()


def _read_transcript(plan: H24DormantHarnessPlan, capability: object) -> tuple[list[dict[str, object]], bytes, str]:
    checked = require_claimed_h24_scientific_capability(capability)
    raw = checked.transcript_path.read_bytes()
    lines = raw.splitlines(keepends=True)
    if len(lines) != 72 or b"".join(lines) != raw:
        raise ValueError("H24 transcript must contain exactly 72 preserved lines.")
    previous = _ZERO_SHA
    records: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        record = _parse(line, f"transcript record {index}")
        if set(record) != _RECORD_KEYS:
            raise ValueError("H24 transcript record key set mismatch.")
        test = plan.tests[index]
        if type(record["schema_version"]) is not int or type(record["sequence_index"]) is not int:
            raise ValueError("H24 transcript integer fields have wrong types.")
        if (record["schema_version"], record["sequence_index"], record["test_id"], record["phase"], record["previous_record_sha256"]) != (1, index, test.test_id, test.phase, previous):
            raise ValueError("H24 transcript identity/order/hash chain mismatch.")
        state = record["record_state"]
        evidence_fields = (
            record["evidence_path"],
            record["evidence_byte_count"],
            record["evidence_raw_sha256"],
        )
        error_fields = (
            record["operational_error_class"],
            record["operational_error_message_sha256"],
        )
        if state == "EVIDENCE_PERSISTED":
            if (
                type(evidence_fields[0]) is not str
                or type(evidence_fields[1]) is not int
                or type(evidence_fields[1]) is bool
                or evidence_fields[1] <= 0
                or type(evidence_fields[2]) is not str
                or len(evidence_fields[2]) != 64
                or any(item not in "0123456789abcdef" for item in evidence_fields[2])
                or error_fields != (None, None)
            ):
                raise ValueError("H24 EVIDENCE_PERSISTED record fields mismatch.")
        elif state == "OPERATIONAL_ERROR":
            if (
                evidence_fields != (None, None, None)
                or type(error_fields[0]) is not str
                or not error_fields[0]
                or type(error_fields[1]) is not str
                or len(error_fields[1]) != 64
            ):
                raise ValueError("H24 OPERATIONAL_ERROR record fields mismatch.")
        elif state in {"NOT_RUN_BY_KILL_RULE", "NOT_RUN_BY_OPERATIONAL_FAILURE"}:
            if evidence_fields != (None, None, None) or error_fields != (None, None):
                raise ValueError("H24 NOT_RUN record fields mismatch.")
        else:
            raise ValueError("H24 transcript state is unknown.")
        previous = _sha(line)
        records.append(record)
    return records, raw, previous


def _read_evidence(capability: AttestedH24ScientificExecutionCapability, record: Mapping[str, object]) -> tuple[dict[str, object], bytes]:
    index = int(record["sequence_index"])
    expected = _expected_path(index, str(record["test_id"]))
    if record["evidence_path"] != expected:
        raise ValueError("H24 evidence path differs from sealed derivation.")
    path = capability.success_directory / expected
    path.resolve(strict=True).relative_to(capability.success_directory.resolve(strict=True))
    raw = path.read_bytes()
    if len(raw) != record["evidence_byte_count"] or _sha(raw) != record["evidence_raw_sha256"]:
        raise ValueError("H24 evidence byte binding mismatch.")
    return _parse(raw, f"evidence {record['test_id']}"), raw


def _load_published_population_after_claim(
    np: object, capability: object
) -> _H24ScientificContext:
    checked = require_claimed_h24_scientific_capability(capability)
    index_path = checked.population_directory / "population_index.jsonl"
    index_raw = index_path.read_bytes()
    if _sha(index_raw) != checked.population_index_sha256:
        raise ValueError("H24 population index changed after capability issuance.")
    bound = {
        relative: (size, digest)
        for relative, size, digest in checked.fixture_file_bindings
    }
    specs: dict[str, Mapping[str, object]] = {}
    targets: dict[str, Mapping[str, object]] = {}
    waveforms: dict[str, object] = {}
    lines = index_raw.splitlines(keepends=True)
    if len(lines) != 175:
        raise ValueError("H24 population index row count changed.")
    for ordinal, line in enumerate(lines):
        row = _parse(line, f"population row {ordinal}")
        fixture_id = row.get("fixture_id")
        if fixture_id != checked.ordered_fixture_ids[ordinal]:
            raise ValueError("H24 population fixture order changed after issuance.")
        if type(fixture_id) is not str:
            raise ValueError("H24 population fixture ID is invalid.")
        paths = (
            ("specification_path", "specification_sha256"),
            ("target_path", "target_sha256"),
            ("waveform_path", "waveform_sha256"),
        )
        payloads: dict[str, bytes] = {}
        for path_key, sha_key in paths:
            relative = row.get(path_key)
            if type(relative) is not str or relative not in bound:
                raise ValueError("H24 population path is not capability-bound.")
            path = (checked.population_directory / relative).resolve(strict=True)
            path.relative_to(checked.population_directory.resolve(strict=True))
            raw = path.read_bytes()
            size, digest = bound[relative]
            if len(raw) != size or _sha(raw) != digest or digest != row.get(sha_key):
                raise ValueError("H24 population file changed after issuance.")
            payloads[path_key] = raw
        specs[fixture_id] = MappingProxyType(
            _parse(payloads["specification_path"], f"spec {fixture_id}")
        )
        targets[fixture_id] = MappingProxyType(
            _parse(payloads["target_path"], f"target {fixture_id}")
        )
        waveform = np.frombuffer(payloads["waveform_path"], dtype="<f8").copy()
        if waveform.shape != (12544,) or not bool(np.all(np.isfinite(waveform))):
            raise ValueError("H24 decoded waveform shape or finiteness mismatch.")
        waveform.setflags(write=False)
        waveforms[fixture_id] = waveform
    if tuple(specs) != checked.ordered_fixture_ids:
        raise ValueError("H24 decoded population is incomplete or reordered.")
    return _H24ScientificContext(
        MappingProxyType(specs),
        MappingProxyType(targets),
        MappingProxyType(waveforms),
    )


def _atomic_terminal(path: Path, payload: Mapping[str, object]) -> Path:
    if set(payload) != _TERMINAL_KEYS:
        raise ValueError("H24 terminal key set mismatch.")
    raw = _canonical(dict(payload))
    temporary = path.with_name(path.name + ".part")
    if path.exists() or temporary.exists():
        raise FileExistsError("H24 terminal or its staging file already exists.")
    _write_new(temporary, raw)
    os.replace(temporary, path)
    _fsync_parent(path.parent)
    if path.read_bytes() != raw:
        raise ValueError("H24 terminal changed during publication.")
    return path


def finalize_and_publish_h24_scientific_terminal(repository_root: Path, capability: object) -> Path:
    """Recompute the authoritative outcome from persisted bytes only."""

    checked = require_claimed_h24_scientific_capability(capability)
    repository = Path(repository_root).resolve(strict=True)
    if repository != checked.repository_root:
        raise ValueError("H24 finalizer repository differs from capability.")
    plan = load_h24_dormant_harness_plan(repository)
    records, transcript_raw, final_sha = _read_transcript(plan, checked)
    evidence_bindings: list[dict[str, object]] = []
    outcomes: list[bool] = []
    operational_index: int | None = None
    kill_started = False
    operational_suffix = False
    for index, record in enumerate(records):
        state = record["record_state"]
        if state == "EVIDENCE_PERSISTED":
            if kill_started or operational_index is not None:
                raise ValueError("H24 evidence appears after a terminal prefix state.")
            evidence, raw = _read_evidence(checked, record)
            recomputed = recompute_h24_persisted_evidence(plan, str(record["test_id"]), evidence)
            outcomes.append(recomputed.final_pass)
            evidence_bindings.append({
                "sequence_index": index,
                "test_id": record["test_id"],
                "evidence_path": record["evidence_path"],
                "evidence_byte_count": len(raw),
                "evidence_raw_sha256": _sha(raw),
            })
            if not recomputed.final_pass:
                kill_started = True
        elif state == "NOT_RUN_BY_KILL_RULE":
            if not kill_started or operational_index is not None:
                raise ValueError("H24 kill suffix is not after first scientific failure.")
        elif state == "OPERATIONAL_ERROR":
            if kill_started or operational_index is not None:
                raise ValueError("H24 operational error placement is invalid.")
            operational_index = index
            operational_suffix = True
        elif state == "NOT_RUN_BY_OPERATIONAL_FAILURE":
            if not operational_suffix:
                raise ValueError("H24 operational suffix lacks its error record.")
        else:
            raise ValueError("H24 transcript state is unknown.")
    if checked.staging_directory.exists():
        raise ValueError("H24 scientific staging directory remains after publication.")
    expected_evidence = {
        str(item.relative_to(checked.success_directory)).replace("\\", "/")
        for item in checked.evidence_directory.rglob("*")
        if item.is_file()
    }
    bound_evidence = {str(item["evidence_path"]) for item in evidence_bindings}
    if expected_evidence != bound_evidence:
        raise ValueError("H24 evidence directory contains missing or extra files.")
    first_failure = next((index for index, passed in enumerate(outcomes) if not passed), None)
    if operational_index is not None:
        status = H24_INCONCLUSIVE_STATUS
        failed_test_id = None
        failed_index = None
    elif first_failure is not None:
        failed_index = first_failure
        failed_test_id = plan.tests[first_failure].test_id
        status = H24_P0_KILL_STATUS if plan.tests[first_failure].phase == "P0" else H24_READINESS_STATUS
    elif len(outcomes) == 72:
        status = H24_SUCCESS_STATUS
        failed_test_id = None
        failed_index = None
    else:
        raise ValueError("H24 transcript has no valid terminal derivation.")
    claim_raw = checked.claim_path.read_bytes()
    terminal = {
        "executed_evidence_record_count": len(evidence_bindings),
        "final_record_sha256": final_sha,
        "first_failed_sequence_index": failed_index,
        "first_failed_test_id": failed_test_id,
        "not_run_by_kill_rule_count": sum(item["record_state"] == "NOT_RUN_BY_KILL_RULE" for item in records),
        "not_run_by_operational_failure_count": sum(item["record_state"] == "NOT_RUN_BY_OPERATIONAL_FAILURE" for item in records),
        "operational_error_count": sum(item["record_state"] == "OPERATIONAL_ERROR" for item in records),
        "ordered_evidence_bindings_sha256": _sha(_canonical(evidence_bindings, line=False)),
        "ordered_test_ids_sha256": _sha(_canonical(list(plan.test_ids), line=False)),
        "passed_test_count": sum(outcomes),
        "population_index_sha256": checked.population_index_sha256,
        "population_marker_sha256": checked.population_marker_sha256,
        "population_receipt_sha256": checked.population_receipt_sha256,
        "population_terminal_sha256": checked.population_terminal_sha256,
        "schema_version": 1,
        "scientific_execution_claim_sha256": _sha(claim_raw),
        "scientific_status": status,
        "transcript_byte_count": len(transcript_raw),
        "transcript_raw_sha256": _sha(transcript_raw),
        "transcript_record_count": len(records),
        "transcript_validation_status": "VALIDATED",
    }
    return _atomic_terminal(checked.terminal_path, terminal)


def _publish_h24_finalizer_error_terminal(capability: object) -> Path:
    """Publish no scientific verdict when ordinary finalization fails."""

    checked = require_claimed_h24_scientific_capability(capability)
    transcript_raw = checked.transcript_path.read_bytes()
    lines = transcript_raw.splitlines(keepends=True)
    claim_raw = checked.claim_path.read_bytes()
    terminal = {
        "executed_evidence_record_count": None,
        "final_record_sha256": None if not lines else _sha(lines[-1]),
        "first_failed_sequence_index": None,
        "first_failed_test_id": None,
        "not_run_by_kill_rule_count": None,
        "not_run_by_operational_failure_count": None,
        "operational_error_count": None,
        "ordered_evidence_bindings_sha256": None,
        "ordered_test_ids_sha256": _sha(_canonical(list(checked.ordered_test_ids), line=False)),
        "passed_test_count": None,
        "population_index_sha256": checked.population_index_sha256,
        "population_marker_sha256": checked.population_marker_sha256,
        "population_receipt_sha256": checked.population_receipt_sha256,
        "population_terminal_sha256": checked.population_terminal_sha256,
        "schema_version": 1,
        "scientific_execution_claim_sha256": _sha(claim_raw),
        "scientific_status": H24_INCONCLUSIVE_STATUS,
        "transcript_byte_count": len(transcript_raw),
        "transcript_raw_sha256": _sha(transcript_raw),
        "transcript_record_count": len(lines),
        "transcript_validation_status": "FINALIZER_ERROR",
    }
    return _atomic_terminal(checked.terminal_path, terminal)


def _finalize_h24_ordinary_operational_failure(
    writer: _H24TranscriptWriter, error: BaseException
) -> Path:
    """Best-effort graceful closure for an ordinary post-claim error."""

    if writer.next_index >= 72:
        raise RuntimeError("H24 has no transcript slot for an operational error.")
    writer.append_operational_error(error)
    writer.fill_operational_suffix()
    writer.publish()
    try:
        return finalize_and_publish_h24_scientific_terminal(
            writer._capability.repository_root, writer._capability
        )
    except Exception:
        return _publish_h24_finalizer_error_terminal(writer._capability)


def run_authorized_h24_scientific_execution(repository_root: Path, capability: object) -> Path:
    """Future one-shot entry; fail before claim while producers are dormant."""

    checked = require_attested_h24_scientific_capability(capability)
    repository = Path(repository_root).resolve(strict=True)
    if repository != checked.repository_root:
        raise ValueError("H24 runner repository differs from capability.")
    plan = load_h24_dormant_harness_plan(repository)
    producers = _require_complete_producer_registry(plan)
    claimed = claim_h24_scientific_execution(checked)
    writer = _H24TranscriptWriter(plan, claimed)
    try:
        np = importlib.import_module("numpy")
        if getattr(np, "__version__", None) != "1.26.4":
            raise RuntimeError("H24 runner requires exact NumPy 1.26.4.")
        context = _load_published_population_after_claim(np, claimed)
        for test in plan.tests:
            producer = producers[test.test_id]
            evidence = producer(context, test)
            if type(evidence) is not dict:
                raise ValueError("H24 producer evidence must be a JSON object.")
            evidence_path = writer.append_evidence(evidence)
            persisted = _parse(evidence_path.read_bytes(), f"evidence {test.test_id}")
            outcome = recompute_h24_persisted_evidence(plan, test.test_id, persisted)
            if not outcome.final_pass:
                writer.fill_kill_suffix()
                break
        writer.publish()
    except Exception as error:
        if writer.next_index < 72:
            return _finalize_h24_ordinary_operational_failure(writer, error)
        try:
            writer.publish()
        except Exception:
            writer.close()
            raise
        return _publish_h24_finalizer_error_terminal(claimed)
    try:
        return finalize_and_publish_h24_scientific_terminal(repository, claimed)
    except Exception:
        return _publish_h24_finalizer_error_terminal(claimed)


def main(argv: list[str] | None = None) -> int:
    if argv:
        raise ValueError("H24 scientific runner accepts no caller arguments.")
    repository = Path.cwd().resolve(strict=True)
    checked = issue_h24_scientific_execution_capability(repository)
    run_authorized_h24_scientific_execution(repository, checked)
    return 0


__all__ = [
    "H24_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED",
    "H24_EVIDENCE_PRODUCER_REGISTRY_IMPLEMENTED",
    "finalize_and_publish_h24_scientific_terminal",
    "run_authorized_h24_scientific_execution",
]
