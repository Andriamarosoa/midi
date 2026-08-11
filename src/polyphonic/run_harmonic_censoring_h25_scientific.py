"""Dormant one-shot H25 scientific runner.

The complete lifecycle is present, but no reviewed seal, activation or OS
binding exists.  The public entry therefore remains dormant before NumPy and
before the published population is opened.
"""
from __future__ import annotations

from dataclasses import dataclass, replace
import hashlib
import importlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
from types import MappingProxyType
from typing import Mapping, Sequence

from .harmonic_censoring_h25_recomputer import recompute_h25_persisted_evidence
from .harmonic_censoring_h25_scientific_engine import (
    H25CausalReplayTrace,
    H25DormantScientificPlan,
    H25EvidenceProducerContext,
    H25_EXACT_EVIDENCE_PRODUCER_REGISTRY,
    canonical_json_bytes,
    load_h25_dormant_scientific_plan,
)
from .harmonic_censoring_h25_scientific_capability import (
    AttestedH25ScientificCapability,
    _claim_h25_scientific_execution,
    _issue_h25_scientific_authority,
    require_attested_h25_scientific_capability,
    require_claimed_h25_scientific_capability,
)


H25_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED = True
H25_PHASE_ORDER = ("P0", "P1", "P2")
H25_PHASE_FAILURE_STATUS = {
    "P0": "H25_SYNTHETIC_HYPOTHESIS_KILLED",
    "P1": "H25_IDENTIFIABILITY_NOT_DEMONSTRATED",
    "P2": "H25_PRETRAIN_READINESS_NOT_DEMONSTRATED",
}
H25_SUCCESS_STATUS = "H25_SYNTHETIC_PRETRAIN_EVIDENCE_PASSED"
H25_INCONCLUSIVE_STATUS = "H25_EXECUTION_INCONCLUSIVE_CONSUMED"
_ZERO_SHA = "0" * 64
_RECORD_STATES = {
    "EVIDENCE_PERSISTED",
    "OPERATIONAL_ERROR",
    "NOT_RUN_BY_KILL_RULE",
    "NOT_RUN_BY_OPERATIONAL_FAILURE",
}
_RECORD_KEYS = {
    "schema_version", "sequence_index", "test_id", "phase", "record_state",
    "previous_record_sha256", "evidence_path", "evidence_byte_count",
    "evidence_raw_sha256", "operational_error_class",
    "operational_error_message_sha256",
}


@dataclass(frozen=True)
class H25DormantRunnerPlan:
    scientific_plan: H25DormantScientificPlan
    ordered_test_ids: tuple[str, ...]
    population_bindings: Mapping[str, str]
    phase_order: tuple[str, ...]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return canonical_json_bytes(value, line=True)


def _reject_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H25 persisted JSON duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H25 persisted JSON forbids {token!r}.")


def _parse(raw: bytes, label: str) -> dict[str, object]:
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


def _atomic_json(path: Path, payload: Mapping[str, object]) -> Path:
    raw = _canonical(dict(payload))
    temporary = path.with_name(path.name + ".part")
    if path.exists() or temporary.exists():
        raise FileExistsError("H25 terminal or staging path already exists.")
    _write_new(temporary, raw)
    os.replace(temporary, path)
    _fsync_parent(path.parent)
    if path.read_bytes() != raw:
        raise ValueError("H25 atomic JSON changed during publication.")
    return path


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


class _H25TranscriptWriter:
    __slots__ = ("capability", "plan", "stream", "next_index", "previous", "published")

    def __init__(self, plan: H25DormantScientificPlan, capability: object) -> None:
        checked = require_claimed_h25_scientific_capability(capability)
        if plan.test_ids != checked.ordered_test_ids:
            raise ValueError("H25 transcript plan differs from capability.")
        checked.staging_directory.parent.mkdir(parents=True, exist_ok=True)
        checked.staging_directory.mkdir()
        (checked.staging_directory / "evidence").mkdir()
        self.stream = (checked.staging_directory / "scientific_transcript.jsonl.part").open("xb")
        self.capability = checked
        self.plan = plan
        self.next_index = 0
        self.previous = _ZERO_SHA
        self.published = False

    def _append(
        self,
        state: str,
        *,
        evidence_path: str | None = None,
        evidence_raw: bytes | None = None,
        error: BaseException | None = None,
    ) -> None:
        if state not in _RECORD_STATES or self.published or self.next_index >= 27:
            raise RuntimeError("H25 transcript append is invalid.")
        test = self.plan.tests[self.next_index]
        record = {
            "schema_version": 1,
            "sequence_index": self.next_index,
            "test_id": test.test_id,
            "phase": test.phase,
            "record_state": state,
            "previous_record_sha256": self.previous,
            "evidence_path": evidence_path,
            "evidence_byte_count": None if evidence_raw is None else len(evidence_raw),
            "evidence_raw_sha256": None if evidence_raw is None else _sha(evidence_raw),
            "operational_error_class": None if error is None else f"{type(error).__module__}.{type(error).__qualname__}",
            "operational_error_message_sha256": None if error is None else _sha(str(error).encode("utf-8")),
        }
        raw = _canonical(record)
        self.stream.write(raw)
        self.stream.flush()
        os.fsync(self.stream.fileno())
        self.previous = _sha(raw)
        self.next_index += 1

    def append_evidence(self, evidence: Mapping[str, object]) -> Path:
        if "pass" in evidence or "verdict" in evidence:
            raise ValueError("H25 producer verdict fields are forbidden.")
        test = self.plan.tests[self.next_index]
        relative = f"evidence/{self.next_index:02d}_{test.test_id}.json"
        raw = _canonical(dict(evidence))
        path = self.capability.staging_directory / relative
        _write_new(path, raw)
        self._append("EVIDENCE_PERSISTED", evidence_path=relative, evidence_raw=raw)
        return path

    def fill_kill_suffix(self) -> None:
        while self.next_index < 27:
            self._append("NOT_RUN_BY_KILL_RULE")

    def fill_operational_suffix(self, error: BaseException) -> None:
        if self.next_index < 27:
            self._append("OPERATIONAL_ERROR", error=error)
        while self.next_index < 27:
            self._append("NOT_RUN_BY_OPERATIONAL_FAILURE")

    def publish(self) -> Path:
        if self.next_index != 27:
            raise ValueError("H25 transcript requires exactly 27 records.")
        self.stream.close()
        source = self.capability.staging_directory / "scientific_transcript.jsonl.part"
        target = self.capability.staging_directory / "scientific_transcript.jsonl"
        os.replace(source, target)
        _fsync_parent(self.capability.staging_directory)
        os.replace(self.capability.staging_directory, self.capability.success_directory)
        _fsync_parent(self.capability.success_directory.parent)
        self.published = True
        return self.capability.success_directory / "scientific_transcript.jsonl"

    def close(self) -> None:
        if not self.stream.closed:
            self.stream.close()


def _load_population_after_claim(np: object, capability: object, plan: H25DormantScientificPlan) -> H25EvidenceProducerContext:
    checked = require_claimed_h25_scientific_capability(capability)
    root = checked.population_directory
    bound = {
        "population_index.jsonl": checked.population_index_sha256,
        "runtime_provenance.json": checked.population_provenance_sha256,
        "population_receipt.json": checked.population_receipt_sha256,
    }
    for name, expected in bound.items():
        if _sha((root / name).read_bytes()) != expected:
            raise ValueError(f"H25 published population binding changed for {name}.")
    lines = (root / "population_index.jsonl").read_bytes().splitlines(keepends=True)
    if len(lines) != 36:
        raise ValueError("H25 population index count changed after claim.")
    waveforms: dict[str, object] = {}
    fixture_records: dict[str, Mapping[str, object]] = {}
    traces: dict[str, H25CausalReplayTrace] = {}
    for ordinal, line in enumerate(lines):
        row = _parse(line, f"population index {ordinal}")
        fixture_id = str(row["fixture_id"])
        if fixture_id != plan.fixture_ids[ordinal] or row["ordinal"] != ordinal:
            raise ValueError("H25 population index order changed after claim.")
        artifacts: dict[str, bytes] = {}
        for stem in ("waveform", "fixture_record", "target_record"):
            relative = str(row[f"{stem}_path"])
            path = (root / relative).resolve(strict=True)
            path.relative_to(root.resolve(strict=True))
            raw = path.read_bytes()
            if len(raw) != row[f"{stem}_size_bytes"] or _sha(raw) != row[f"{stem}_sha256"]:
                raise ValueError(f"H25 {stem} binding changed for {fixture_id}.")
            artifacts[stem] = raw
        waveform = np.frombuffer(artifacts["waveform"], dtype="<f8").astype(np.float64, copy=True)
        if waveform.shape != (16640,) or not bool(np.all(np.isfinite(waveform))):
            raise ValueError("H25 waveform shape/finiteness mismatch.")
        record = _parse(artifacts["fixture_record"], f"fixture record {fixture_id}")
        source = record["source_fixture_record"]
        parameters = source.get("parameters", {})
        transitions: tuple[Mapping[str, object], ...] = ()
        old_pitch = parameters.get("old_pitch")
        if type(old_pitch) is int:
            transitions = (MappingProxyType({"sample_index": 8192, "kind": "note_on", "pitch": old_pitch}),)
        waveforms[fixture_id] = waveform
        fixture_records[fixture_id] = MappingProxyType(record)
        traces[fixture_id] = H25CausalReplayTrace(fixture_id, 16383, (), transitions)
    resource = importlib.import_module("resource")
    peak_rss_bytes = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
    return H25EvidenceProducerContext(
        np=np,
        plan=plan,
        waveforms=MappingProxyType(waveforms),
        fixture_records=MappingProxyType(fixture_records),
        causal_replay_traces=MappingProxyType(traces),
        started_ns=time.perf_counter_ns(),
        peak_rss_bytes=peak_rss_bytes,
        operational_counters=MappingProxyType({
            "GPU_device_count": 0,
            "scientific_process_count": 1,
            "model_inference_call_count": 0,
            "hidden_repeated_pitch_shift_inference_count": 0,
        }),
        observed_fixture_ids=plan.fixture_ids,
        observed_test_ids=plan.test_ids,
        observed_test_records=None,
    )


def _runtime_identity_for_current_process() -> Mapping[str, object]:
    executable = Path(sys.executable).resolve(strict=True)
    identity = {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "resolved_executable": str(executable),
        "executable_size_bytes": executable.stat().st_size,
        "executable_sha256": _sha(executable.read_bytes()),
        "command_sha256": _sha(_canonical([str(executable), "<current-process>"])),
        "observer_payload_path": str(Path(__file__).resolve(strict=True)),
        "observer_payload_size_bytes": Path(__file__).resolve(strict=True).stat().st_size,
        "observer_payload_sha256": _sha(Path(__file__).resolve(strict=True).read_bytes()),
    }
    return MappingProxyType(identity)


def _attach_runtime_identity(
    evidence: Mapping[str, object], runtime_identity: Mapping[str, object]
) -> dict[str, object]:
    result = dict(evidence)
    observation = dict(result["current_runtime_observation"])
    identity = dict(runtime_identity)
    observation["runtime_identity"] = identity
    observation["runtime_id"] = _sha(_canonical(identity))
    result["current_runtime_observation"] = observation
    return result


def _derive_recomputed_runtime_test_records(
    context: H25EvidenceProducerContext,
    runtime_identity: Mapping[str, object],
) -> Mapping[str, Mapping[str, object]]:
    """Run the exact producers as a P2-007 probe; never fabricate PASS rows."""

    seed = MappingProxyType({
        item.test_id: MappingProxyType({
            "test_id": item.test_id,
            "phase": item.phase,
            "fixture_ids": list(item.fixture_ids),
        })
        for item in context.plan.tests
    })
    probe = replace(context, observed_test_records=seed)
    records: dict[str, Mapping[str, object]] = {}
    for test in context.plan.tests:
        evidence = H25_EXACT_EVIDENCE_PRODUCER_REGISTRY[test.test_id](probe, test)
        if test.test_id == "H25-T-P2-007":
            evidence = _attach_runtime_identity(evidence, runtime_identity)
        persisted = _parse(_canonical(dict(evidence)), f"P2-007 probe {test.test_id}")
        outcome = recompute_h25_persisted_evidence(context.plan, test.test_id, persisted)
        records[test.test_id] = MappingProxyType({
            "test_id": test.test_id,
            "phase": test.phase,
            "fixture_ids": list(test.fixture_ids),
            "evidence": persisted,
            "recomputation": {
                "primary_pass": outcome.primary_pass,
                "inverse_pass": outcome.inverse_pass,
                "final_pass": outcome.final_pass,
            },
        })
    return MappingProxyType(records)


def _validate_recomputed_runtime_test_records(
    plan: H25DormantScientificPlan, raw_records: object
) -> None:
    if type(raw_records) is not list or len(raw_records) != len(plan.tests):
        raise ValueError("H25 secondary runtime test records are incomplete.")
    for test, raw_record in zip(plan.tests, raw_records):
        if type(raw_record) is not dict or set(raw_record) != {
            "test_id", "phase", "fixture_ids", "evidence", "recomputation"
        }:
            raise ValueError("H25 secondary runtime test record schema mismatch.")
        if (
            raw_record["test_id"] != test.test_id
            or raw_record["phase"] != test.phase
            or raw_record["fixture_ids"] != list(test.fixture_ids)
            or type(raw_record["evidence"]) is not dict
            or type(raw_record["recomputation"]) is not dict
        ):
            raise ValueError("H25 secondary runtime test record identity mismatch.")
        outcome = recompute_h25_persisted_evidence(
            plan, test.test_id, raw_record["evidence"]
        )
        expected = {
            "primary_pass": outcome.primary_pass,
            "inverse_pass": outcome.inverse_pass,
            "final_pass": outcome.final_pass,
        }
        if raw_record["recomputation"] != expected:
            raise ValueError("H25 secondary runtime test record recomputation mismatch.")


def _secondary_runtime_observation(
    capability: object, plan: H25DormantScientificPlan
) -> Mapping[str, object]:
    checked = require_claimed_h25_scientific_capability(capability)
    completed = subprocess.run(
        list(checked.secondary_runtime_command),
        cwd=checked.repository_root,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
        timeout=checked.secondary_runtime_timeout_seconds,
    )
    if completed.returncode != 0 or not completed.stdout or completed.stderr:
        raise RuntimeError("H25 secondary runtime observation failed closed.")
    value = json.loads(
        completed.stdout.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict or set(value) != {
        "runtime_id", "runtime_identity", "fixture_measurements", "test_records"
    }:
        raise ValueError("H25 secondary runtime observation schema mismatch.")
    if completed.stdout != _canonical(value):
        raise ValueError("H25 secondary runtime observation is not canonical JSON.")
    if value["runtime_identity"] != dict(checked.secondary_runtime_identity):
        raise PermissionError("H25 secondary runtime identity differs from the sealed identity.")
    if value["runtime_id"] != _sha(_canonical(value["runtime_identity"])):
        raise PermissionError("H25 secondary runtime ID is not derived from its sealed identity.")
    _validate_recomputed_runtime_test_records(plan, value["test_records"])
    return value


def _read_transcript(capability: AttestedH25ScientificCapability) -> list[dict[str, object]]:
    raw = (capability.success_directory / "scientific_transcript.jsonl").read_bytes()
    lines = raw.splitlines(keepends=True)
    if len(lines) != 27 or b"".join(lines) != raw:
        raise ValueError("H25 transcript count is not 27.")
    previous = _ZERO_SHA
    records: list[dict[str, object]] = []
    for index, line in enumerate(lines):
        record = _parse(line, f"transcript record {index}")
        if set(record) != _RECORD_KEYS:
            raise ValueError("H25 transcript field set mismatch.")
        if (
            type(record["schema_version"]) is not int
            or record["schema_version"] != 1
            or type(record["sequence_index"]) is not int
            or record["sequence_index"] != index
            or record["test_id"] != capability.ordered_test_ids[index]
            or record["phase"] != capability.ordered_test_phases[index]
            or record["previous_record_sha256"] != previous
            or record["record_state"] not in _RECORD_STATES
        ):
            raise ValueError("H25 transcript order/hash chain mismatch.")
        evidence_fields = (
            record["evidence_path"], record["evidence_byte_count"],
            record["evidence_raw_sha256"],
        )
        error_fields = (
            record["operational_error_class"],
            record["operational_error_message_sha256"],
        )
        if record["record_state"] == "EVIDENCE_PERSISTED":
            if (
                type(evidence_fields[0]) is not str
                or type(evidence_fields[1]) is not int
                or type(evidence_fields[1]) is bool
                or evidence_fields[1] <= 0
                or type(evidence_fields[2]) is not str
                or len(evidence_fields[2]) != 64
                or error_fields != (None, None)
            ):
                raise ValueError("H25 evidence transcript fields mismatch.")
        elif record["record_state"] == "OPERATIONAL_ERROR":
            if evidence_fields != (None, None, None) or any(
                type(value) is not str or not value for value in error_fields
            ):
                raise ValueError("H25 operational transcript fields mismatch.")
        elif evidence_fields != (None, None, None) or error_fields != (None, None):
            raise ValueError("H25 NOT_RUN transcript fields mismatch.")
        previous = _sha(line)
        records.append(record)
    return records


def _finalize(capability: object, plan: H25DormantScientificPlan) -> Path:
    checked = require_claimed_h25_scientific_capability(capability)
    records = _read_transcript(checked)
    outcomes: list[bool] = []
    first_failure: int | None = None
    operational = False
    kill = False
    for index, record in enumerate(records):
        state = record["record_state"]
        if state == "EVIDENCE_PERSISTED":
            if kill or operational:
                raise ValueError("H25 evidence appears after terminal prefix.")
            evidence_path = checked.success_directory / str(record["evidence_path"])
            raw = evidence_path.read_bytes()
            if len(raw) != record["evidence_byte_count"] or _sha(raw) != record["evidence_raw_sha256"]:
                raise ValueError("H25 persisted evidence binding mismatch.")
            outcome = recompute_h25_persisted_evidence(plan, str(record["test_id"]), _parse(raw, str(record["test_id"])))
            outcomes.append(outcome.final_pass)
            if not outcome.final_pass:
                first_failure = index
                kill = True
        elif state == "OPERATIONAL_ERROR":
            if kill or operational:
                raise ValueError("H25 operational error placement mismatch.")
            operational = True
        elif state == "NOT_RUN_BY_KILL_RULE":
            if not kill or operational:
                raise ValueError("H25 kill suffix placement mismatch.")
        elif state == "NOT_RUN_BY_OPERATIONAL_FAILURE":
            if not operational:
                raise ValueError("H25 operational suffix placement mismatch.")
        else:
            raise ValueError("H25 transcript state mismatch.")
    if operational:
        status = H25_INCONCLUSIVE_STATUS
    elif first_failure is not None:
        status = H25_PHASE_FAILURE_STATUS[plan.tests[first_failure].phase]
    elif len(outcomes) == 27 and all(outcomes):
        status = H25_SUCCESS_STATUS
    else:
        raise ValueError("H25 transcript has no closed outcome.")
    transcript_raw = (checked.success_directory / "scientific_transcript.jsonl").read_bytes()
    terminal = {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h25_scientific_terminal",
        "scientific_status": status,
        "claim_sha256": _sha(checked.claim_path.read_bytes()),
        "transcript_sha256": _sha(transcript_raw),
        "transcript_record_count": 27,
        "executed_test_count": sum(item["record_state"] == "EVIDENCE_PERSISTED" for item in records),
        "passed_test_count": sum(outcomes),
        "first_failed_test_id": None if first_failure is None else plan.tests[first_failure].test_id,
        "not_run_by_kill_rule_count": sum(item["record_state"] == "NOT_RUN_BY_KILL_RULE" for item in records),
        "not_run_by_operational_failure_count": sum(item["record_state"] == "NOT_RUN_BY_OPERATIONAL_FAILURE" for item in records),
        "operational_error_count": sum(item["record_state"] == "OPERATIONAL_ERROR" for item in records),
        "population_index_sha256": checked.population_index_sha256,
        "population_provenance_sha256": checked.population_provenance_sha256,
        "population_receipt_sha256": checked.population_receipt_sha256,
        "locked_test_used": False,
        "real_data_used": False,
        "model_or_training_used": False,
        "forensic_error_class": None,
        "forensic_error_message_sha256": None,
    }
    return _atomic_json(checked.terminal_path, terminal)


def _publish_forensic_inconclusive(
    capability: object, error: BaseException
) -> Path:
    """Last-resort closure on a distinct path; preserves any primary .part."""

    checked = require_claimed_h25_scientific_capability(capability)
    candidates = (
        checked.success_directory / "scientific_transcript.jsonl",
        checked.staging_directory / "scientific_transcript.jsonl",
        checked.staging_directory / "scientific_transcript.jsonl.part",
    )
    transcript = next((path for path in candidates if path.is_file()), None)
    raw = b"" if transcript is None else transcript.read_bytes()
    terminal = {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h25_scientific_terminal",
        "scientific_status": H25_INCONCLUSIVE_STATUS,
        "claim_sha256": _sha(checked.claim_path.read_bytes()),
        "transcript_sha256": None if transcript is None else _sha(raw),
        "transcript_record_count": len(raw.splitlines()),
        "executed_test_count": None,
        "passed_test_count": None,
        "first_failed_test_id": None,
        "not_run_by_kill_rule_count": None,
        "not_run_by_operational_failure_count": None,
        "operational_error_count": None,
        "population_index_sha256": checked.population_index_sha256,
        "population_provenance_sha256": checked.population_provenance_sha256,
        "population_receipt_sha256": checked.population_receipt_sha256,
        "locked_test_used": False,
        "real_data_used": False,
        "model_or_training_used": False,
        "forensic_error_class": f"{type(error).__module__}.{type(error).__qualname__}",
        "forensic_error_message_sha256": _sha(str(error).encode("utf-8")),
    }
    return _atomic_json(checked.forensic_terminal_path, terminal)


def _execute_attested_h25_scientific_execution(
    capability: AttestedH25ScientificCapability,
) -> Path:
    checked = require_attested_h25_scientific_capability(capability)
    plan = load_h25_dormant_scientific_plan(checked.repository_root)
    if plan.test_ids != checked.ordered_test_ids or plan.fixture_ids != checked.ordered_fixture_ids:
        raise ValueError("H25 capability plan binding mismatch before claim.")
    claimed = _claim_h25_scientific_execution(checked)
    writer = _H25TranscriptWriter(plan, claimed)
    try:
        np = importlib.import_module("numpy")
        if getattr(np, "__version__", None) != "1.26.4":
            raise RuntimeError("H25 scientific runner requires exact NumPy 1.26.4.")
        context = _load_population_after_claim(np, claimed, plan)
        for test in plan.tests:
            if test.test_id == "H25-T-P2-007":
                current_identity = _runtime_identity_for_current_process()
                context = replace(
                    context,
                    observed_test_records=_derive_recomputed_runtime_test_records(
                        context, current_identity
                    ),
                )
            evidence = H25_EXACT_EVIDENCE_PRODUCER_REGISTRY[test.test_id](context, test)
            if test.test_id == "H25-T-P2-007":
                evidence = _attach_runtime_identity(evidence, current_identity)
                evidence["cross_runtime_observation"] = _secondary_runtime_observation(
                    claimed, plan
                )
            path = writer.append_evidence(evidence)
            persisted = _parse(path.read_bytes(), test.test_id)
            outcome = recompute_h25_persisted_evidence(plan, test.test_id, persisted)
            if not outcome.final_pass:
                writer.fill_kill_suffix()
                break
        writer.publish()
    except Exception as error:
        try:
            if writer.next_index < 27:
                writer.fill_operational_suffix(error)
            if not writer.published:
                writer.publish()
        except Exception as closure_error:
            writer.close()
            return _publish_forensic_inconclusive(claimed, closure_error)
    try:
        return _finalize(claimed, plan)
    except Exception as finalizer_error:
        return _publish_forensic_inconclusive(claimed, finalizer_error)


def run_h25_scientific_execution(repository_root: Path) -> Path:
    """Single reviewed boundary; dormant while no authority can be issued."""

    repository = Path(repository_root).resolve(strict=True)
    authority = _issue_h25_scientific_authority(repository)
    return authority.execute_once(repository)


__all__ = [
    "H25_DORMANT_SCIENTIFIC_RUNNER_IMPLEMENTED",
    "H25DormantRunnerPlan",
    "load_h25_dormant_runner_plan",
    "recompute_phase_prefix",
    "run_h25_scientific_execution",
]
