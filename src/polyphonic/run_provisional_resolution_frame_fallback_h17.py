"""Sealed one-shot real H17 frame-fallback risk execution.

Import is zero-science. TensorFlow, project data readers, decoder, targets and
metrics stay behind the irrevocable H20 consumption boundary.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import traceback
from typing import Any, Mapping, Sequence


EXECUTION_CONTRACT_RELATIVE = Path(
    "configs/provisional_resolution_frame_fallback_h22_execution_contract.json"
)
H21_RELATIVE = Path(
    "configs/provisional_resolution_frame_fallback_h21_zero_science_preflight.json"
)
H20_RELATIVE = Path(
    "configs/provisional_resolution_frame_fallback_h20_real_execution_contract.json"
)
H21_RAW_SHA256 = "acb8ced104ec99afd7f6f966be17b84ce4d436e5582137b6ec6048a90dfe3331"
H21_GIT_BLOB = "838c8b491b5fb3e92fd2e5822d329bd875cec115"
H20_GIT_BLOB = "65c64ddb031839facb26e5b9fb8b1844883449e0"
CHECKPOINT_SHA256 = "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
MODEL_CONFIG_SHA256 = "245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804"
DECODER_CONFIG_SHA256 = "c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96"
AUDIO_POLICY_SHA256 = "45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e"
EXPECTED_RECORDINGS = 146
EXPECTED_GROUPS = 51
PHASES = ("opening", "inference", "decoder", "target", "reconciliation", "metrics", "publication")
_SCIENCE_TERMS = re.compile(
    r"(?i)(?:candidate_reason|frame_fallback|true_noteon|false_noteon|target|rd_false|bootstrap|probabilit|score|class_balance)"
)


def _sha256(path: Path) -> tuple[int, str]:
    resolved = Path(path).resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.R_OK):
        raise RuntimeError("sealed input is missing or unreadable")
    digest = hashlib.sha256()
    size = 0
    with resolved.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            size += len(block)
            digest.update(block)
    if size != resolved.stat().st_size:
        raise RuntimeError("sealed input changed during hashing")
    return size, digest.hexdigest()


def _canonical_bytes(payload: object) -> bytes:
    return (json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _write_json_atomic(path: Path, payload: object) -> None:
    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=str(destination.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(_canonical_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, destination)
    finally:
        temporary.unlink(missing_ok=True)


def _git(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, encoding="utf-8"
    ).strip()


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def _bounded_message(error: BaseException) -> str:
    message = " ".join(str(error).split())
    if _SCIENCE_TERMS.search(message):
        return "[redacted_non_operational_exception_message]"
    return message[:512]


def _bounded_traceback(error: BaseException) -> list[dict[str, object]]:
    return [
        {"file": Path(frame.filename).name, "function": frame.name, "line": frame.lineno}
        for frame in traceback.extract_tb(error.__traceback__)[-32:]
    ]


@dataclass(frozen=True)
class SealedH17Recording:
    recording_key: str
    leakage_group_key: str
    corpus_category: str
    audio_path: Path
    audio_member: str
    audio_size_bytes: int
    audio_sha256: str
    label_path: Path
    label_size_bytes: int
    label_sha256: str


@dataclass(frozen=True)
class H17Paths:
    repository: Path
    execution_contract: Path
    h20: Path
    h21: Path
    model_config: Path
    decoder_config: Path
    audio_policy: Path
    checkpoint: Path
    destination: Path
    marker: Path
    claimed: Path
    state: Path
    phase: Path
    failure: Path


def _load_canonical(path: Path, *, label: str) -> tuple[bytes, dict[str, Any]]:
    raw = path.read_bytes()
    payload = json.loads(raw)
    if raw != _canonical_bytes(payload):
        raise RuntimeError(f"{label} is not canonical JSON")
    if not isinstance(payload, dict):
        raise RuntimeError(f"{label} root is not an object")
    return raw, payload


def _paths(repository: Path) -> H17Paths:
    repo = Path(repository).resolve(strict=True)
    h21_path = repo / H21_RELATIVE
    _raw, h21 = _load_canonical(h21_path, label="H21")
    future = h21.get("future_paths")
    checkpoint = h21.get("checkpoint")
    if not isinstance(future, dict) or not isinstance(checkpoint, dict):
        raise RuntimeError("H21 paths are incomplete")
    marker = Path(str(future["future_authorization_marker_path"]))
    destination = Path(str(future["future_result_destination"]))
    return H17Paths(
        repository=repo,
        execution_contract=repo / EXECUTION_CONTRACT_RELATIVE,
        h20=repo / H20_RELATIVE,
        h21=h21_path,
        model_config=repo / "configs/polyphonic_dual_stream_bass_independent_note.yaml",
        decoder_config=repo / "configs/independent_note_decoder_reference.json",
        audio_policy=repo / "configs/polyphonic_audio_evidence_adaptive_temporal.json",
        checkpoint=Path(str(checkpoint["resolved_path"])),
        destination=destination,
        marker=marker,
        claimed=Path(str(marker) + ".claimed"),
        state=Path(str(marker) + ".state.json"),
        phase=Path(str(marker) + ".phase.json"),
        failure=Path(str(destination) + ".failure.json"),
    )


def _require_blob(repo: Path, relative: str, expected: str) -> None:
    if _git(repo, "rev-parse", f"HEAD:{relative}") != expected:
        raise RuntimeError("sealed Git source binding mismatch")


def _runtime_identity() -> dict[str, object]:
    return {
        "python_executable": sys.executable,
        "python_version": platform.python_version(),
        "python_implementation": platform.python_implementation(),
        "os_system": platform.system(),
        "os_release": platform.release(),
        "machine": platform.machine(),
        "numpy_distribution_version": _package_version("numpy"),
        "tensorflow_distribution_version": _package_version("tensorflow"),
        "keras_distribution_version": _package_version("keras"),
        "MIDI_FORCE_CPU": os.environ.get("MIDI_FORCE_CPU"),
    }


def _load_and_verify_preflight(repository: Path) -> tuple[H17Paths, tuple[SealedH17Recording, ...], tuple[str, ...], dict[str, Any], str]:
    paths = _paths(repository)
    if _git(paths.repository, "status", "--porcelain"):
        raise RuntimeError("H17 execution requires a clean worktree")
    contract_raw, contract = _load_canonical(paths.execution_contract, label="H22 execution contract")
    contract_sha = hashlib.sha256(contract_raw).hexdigest()
    if contract.get("status") != "provisional_resolution_frame_fallback_h22_execution_contract_sealed":
        raise RuntimeError("H22 execution contract status mismatch")
    if contract.get("h21_raw_sha256") != H21_RAW_SHA256:
        raise RuntimeError("H22 does not bind exact H21 bytes")
    _require_blob(paths.repository, str(H20_RELATIVE).replace("\\", "/"), H20_GIT_BLOB)
    _require_blob(paths.repository, str(H21_RELATIVE).replace("\\", "/"), H21_GIT_BLOB)
    runner_blob = contract.get("runner_git_blob")
    if not isinstance(runner_blob, str) or len(runner_blob) != 40:
        raise RuntimeError("H22 runner blob is missing")
    _require_blob(paths.repository, "src/polyphonic/run_provisional_resolution_frame_fallback_h17.py", runner_blob)
    bindings = contract.get("scientific_git_blobs")
    if not isinstance(bindings, dict):
        raise RuntimeError("H22 scientific bindings are missing")
    for relative, expected in bindings.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RuntimeError("H22 scientific binding is malformed")
        _require_blob(paths.repository, relative, expected)

    h21_size, h21_sha = _sha256(paths.h21)
    if h21_sha != H21_RAW_SHA256 or h21_size != 152080:
        raise RuntimeError("H21 raw-byte identity mismatch")
    _raw, h21 = _load_canonical(paths.h21, label="H21")
    population = h21.get("population")
    flags = h21.get("flags")
    if not isinstance(population, dict) or not isinstance(flags, dict):
        raise RuntimeError("H21 population or flags are missing")
    if (
        population.get("recording_count") != EXPECTED_RECORDINGS
        or population.get("leakage_group_count") != EXPECTED_GROUPS
        or population.get("classification") != "fresh_discovery_only_not_independent_validation"
        or flags.get("fresh_population_consumed") is not False
        or flags.get("locked_test_used") is not False
    ):
        raise RuntimeError("H21 population identity mismatch")

    inventory = population.get("inventory")
    if not isinstance(inventory, list) or len(inventory) != EXPECTED_RECORDINGS:
        raise RuntimeError("H21 inventory length mismatch")
    raw_cache: dict[Path, tuple[int, str]] = {}
    recordings: list[SealedH17Recording] = []
    for item in inventory:
        if not isinstance(item, dict):
            raise RuntimeError("H21 inventory row is malformed")
        audio = Path(str(item["audio_resolved_path"])).resolve(strict=True)
        label = Path(str(item["label_resolved_path"])).resolve(strict=True)
        for path, size, digest in (
            (audio, item["audio_size_bytes"], item["audio_sha256"]),
            (label, item["label_size_bytes"], item["label_sha256"]),
        ):
            evidence = raw_cache.get(path)
            if evidence is None:
                evidence = _sha256(path)
                raw_cache[path] = evidence
            if evidence != (size, digest):
                raise RuntimeError("H21 asset raw-byte mismatch")
        recordings.append(SealedH17Recording(
            recording_key=str(item["recording_key"]),
            leakage_group_key=str(item["leakage_group_key"]),
            corpus_category=str(item["corpus_category"]),
            audio_path=audio,
            audio_member=str(item.get("audio_member", "")),
            audio_size_bytes=int(item["audio_size_bytes"]),
            audio_sha256=str(item["audio_sha256"]),
            label_path=label,
            label_size_bytes=int(item["label_size_bytes"]),
            label_sha256=str(item["label_sha256"]),
        ))
    recordings.sort(key=lambda row: row.recording_key)
    if len({row.recording_key for row in recordings}) != EXPECTED_RECORDINGS:
        raise RuntimeError("H21 recording identities are not unique")
    groups = tuple(sorted({row.leakage_group_key for row in recordings}))
    if len(groups) != EXPECTED_GROUPS or list(groups) != population.get("leakage_group_universe"):
        raise RuntimeError("H21 leakage-group universe mismatch")

    for path, expected in (
        (paths.checkpoint, CHECKPOINT_SHA256),
        (paths.model_config, MODEL_CONFIG_SHA256),
        (paths.decoder_config, DECODER_CONFIG_SHA256),
        (paths.audio_policy, AUDIO_POLICY_SHA256),
    ):
        if _sha256(path)[1] != expected:
            raise RuntimeError("sealed runtime input SHA-256 mismatch")
    runtime = _runtime_identity()
    expected_runtime = contract.get("runtime_identity")
    if runtime != expected_runtime:
        raise RuntimeError("sealed runtime identity mismatch")
    for guarded in (paths.destination, paths.claimed, paths.state, paths.phase, paths.failure):
        if guarded.exists():
            raise FileExistsError("one-shot output or state path already exists")
    if not paths.marker.is_file():
        raise PermissionError("one-shot authorization marker is absent")
    return paths, tuple(recordings), groups, contract, contract_sha


def _claim_marker(paths: H17Paths, contract_sha: str) -> dict[str, Any]:
    _raw, payload = _load_canonical(paths.marker, label="H17 authorization marker")
    expected = {
        "purpose": "provisional_resolution_frame_fallback_h17_one_shot_authorization",
        "execution_contract_sha256": contract_sha,
        "execution_commit": _git(paths.repository, "rev-parse", "HEAD"),
        "scientific_execution_authorized": True,
        "single_use": True,
        "automatic_retry": False,
        "locked_test_used": False,
    }
    if payload != expected:
        raise PermissionError("one-shot authorization marker payload mismatch")
    os.replace(paths.marker, paths.claimed)
    return payload


class _ScientificAdapter:
    def __init__(self, paths: H17Paths) -> None:
        self.paths = paths
        self.model: Any = None
        self.config: dict[str, Any] | None = None
        self.decoder_config: dict[str, Any] | None = None
        self.audio_policy: dict[str, Any] | None = None

    def _load_model(self) -> None:
        if self.model is not None:
            return
        if os.environ.get("MIDI_FORCE_CPU") != "1":
            raise RuntimeError("H17 requires MIDI_FORCE_CPU=1")
        import tensorflow as tf
        import yaml
        from .mine_decoder_candidates import _load_inference_model
        tf.config.set_visible_devices([], "GPU")
        if tf.config.list_logical_devices("GPU"):
            raise RuntimeError("H17 exposed a TensorFlow GPU")
        self.config = yaml.safe_load(self.paths.model_config.read_text(encoding="utf-8"))
        self.decoder_config = json.loads(self.paths.decoder_config.read_text(encoding="utf-8"))
        self.audio_policy = json.loads(self.paths.audio_policy.read_text(encoding="utf-8"))
        if self.decoder_config.get("independent_note_threshold") is not None:
            raise RuntimeError("H17 baseline independent-note gate must be disabled")
        if self.audio_policy != {"onset_adapt_temporal_background": True}:
            raise RuntimeError("H17 audio evidence policy mismatch")
        self.model = _load_inference_model(self.paths.checkpoint, tf)

    @staticmethod
    def _manifest_item(record: SealedH17Recording) -> Any:
        from .manifest_snapshot import ManifestItem
        parts = record.recording_key.split("|")
        if len(parts) != 4 or parts[0] != record.corpus_category:
            raise RuntimeError("H17 recording identity cannot be reconstructed")
        dataset_id, group_id, source_id, capture_id = parts
        return ManifestItem(
            source_id=source_id, dataset_id=dataset_id, player_id="", group_id=group_id,
            split="validation", audio_path=record.audio_path, audio_member=record.audio_member,
            labels_path=record.label_path, capture_id=capture_id, license_id="",
        )

    def process(
        self,
        record: SealedH17Recording,
        *,
        record_phase: Any,
        recording_index: int,
    ) -> tuple[tuple[Any, ...], dict[str, object]]:
        import numpy as np
        from .audio_evidence import offline_audio_evidence_masks
        from .causal_event_metrics import ReferenceNote
        from .data import PolyphonicCorpus, PolyphonicSequence
        from .decoder import PolyphonicDecoder, PolyphonicDecoderConfig
        from .evaluate_events import truth_notes
        from .keras_compat import predict_compat
        from .provisional_resolution_age1 import extract_exact_causal_age1_targets
        from .provisional_resolution_frame_fallback_h19 import (
            PassiveFrameFallbackExposureCollector,
            join_h19_exposures_and_targets,
        )
        corpus = PolyphonicCorpus((self._manifest_item(record),))
        with corpus as opened:
            record_phase("inference", recording_index, record.recording_key)
            self._load_model()
            arrays = opened.labels[0].arrays
            frame_count = len(arrays["active_bits"])
            refs = np.column_stack((np.zeros(frame_count, np.int32), np.arange(frame_count, dtype=np.int32)))
            dataset = self.config["dataset"]
            train = self.config["train"]
            sequence = PolyphonicSequence(
                opened, batch_size=int(train["batch_size"]),
                input_samples=int(dataset["input_samples"]),
                normalization_gain=float(dataset["normalization_gain"]),
                seed=0, refs=refs, shuffle=False,
            )
            prediction = predict_compat(self.model, sequence, verbose=0, workers=1)
            if not isinstance(prediction, Mapping) or set(prediction) != {"frame", "onset", "harmonic_amplitude"}:
                raise RuntimeError("H17 inference output contract mismatch")
            prediction = {name: np.asarray(values) for name, values in prediction.items()}
            if any(values.shape[0] != frame_count for values in prediction.values()):
                raise RuntimeError("H17 inference frame count mismatch")
            record_phase("decoder", recording_index, record.recording_key)
            audio = opened.audio(0)
            active, onset, _ = offline_audio_evidence_masks(
                audio, opened.sample_rate, opened.hop_size, frame_count=frame_count,
                metadata={"audio_evidence": dict(self.audio_policy)},
            )
            collector = PassiveFrameFallbackExposureCollector()
            decoder = PolyphonicDecoder(
                PolyphonicDecoderConfig(**dict(self.decoder_config)),
                provisional_state_resolver=None, causal_candidate_gate=None,
            )
            events: list[Any] = []
            for frame_index in range(frame_count):
                current = decoder.step(
                    prediction["frame"][frame_index], prediction["onset"][frame_index],
                    prediction["harmonic_amplitude"][frame_index],
                    audio_active=bool(active[frame_index]), audio_hop_index=frame_index,
                    audio_onset=bool(onset[frame_index]),
                    audio_onset_hop_index=(frame_index if bool(onset[frame_index]) else None),
                )
                collector.observe_emitted_noteons(current)
                events.extend(current)
            events.extend(decoder.panic(reason="h17_frame_fallback_end"))
            references = tuple(
                ReferenceNote(note.pitch, note.start_s, note.end_s)
                for note in truth_notes(arrays)
            )
            record_phase("target", recording_index, record.recording_key)
            targets = extract_exact_causal_age1_targets(
                events, references, frame_valid=arrays["valid"],
                sample_rate=opened.sample_rate, hop_size=opened.hop_size,
                audio_frames=int(arrays["audio_frames"]),
            )
        record_phase("reconciliation", recording_index, record.recording_key)
        rows = join_h19_exposures_and_targets(
            collector.records, targets, recording_key=record.recording_key,
            corpus_category=record.corpus_category,
            leakage_group_key=record.leakage_group_key,
        )
        counts: dict[str, int] = {}
        for row in rows:
            counts[row.candidate_reason_at_noteon] = counts.get(row.candidate_reason_at_noteon, 0) + 1
        frame_fallback_eligible = sum(
            row.candidate_reason_at_noteon == "frame_fallback" and row.false_noteon is not None
            for row in rows
        )
        comparator_eligible = sum(
            row.candidate_reason_at_noteon in {"model_onset", "frame_attack", "chord_completion"}
            and row.false_noteon is not None
            for row in rows
        )
        audio_aware = sum(
            row.candidate_reason_at_noteon in {"model_onset", "frame_attack", "chord_completion", "frame_fallback"}
            for row in rows
        )
        return rows, {
            "recording_key": record.recording_key,
            "corpus_category": record.corpus_category,
            "leakage_group_key": record.leakage_group_key,
            "emitted_noteons_initially_considered": len(rows),
            "audio_aware_activation_noteons_in_h17_population": audio_aware,
            "frame_fallback_eligible_count": frame_fallback_eligible,
            "comparator_eligible_count": comparator_eligible,
            "excluded_harmonic_strong_frame_count": counts.get("harmonic_strong_frame", 0),
            "excluded_legacy_count": counts.get("legacy", 0),
            "excluded_retrigger_count": counts.get("retrigger", 0),
            "target_unmatchable_or_excluded_count": audio_aware - frame_fallback_eligible - comparator_eligible,
            "malformed_reason_count": 0,
            "malformed_or_nonfinite_target_count": 0,
            "counts_per_frozen_reason": dict(sorted(counts.items())),
        }


def _metric_payload(report: Any, rows: Sequence[Any], groups: Sequence[str]) -> dict[str, object]:
    from .provisional_resolution_frame_fallback_h19 import risk_difference_false
    eligible = [row for row in rows if row.false_noteon is not None]
    exposed = [row for row in eligible if row.frame_fallback_indicator == 1]
    comparator = [row for row in eligible if row.frame_fallback_indicator == 0]
    per_corpus: dict[str, object] = {}
    for corpus in sorted({row.corpus_category for row in rows}):
        subset = [row for row in eligible if row.corpus_category == corpus]
        if {row.frame_fallback_indicator for row in subset} == {0, 1}:
            per_corpus[corpus] = {"eligible_noteons": len(subset), "rd_false": risk_difference_false(subset)}
        else:
            per_corpus[corpus] = {"eligible_noteons": len(subset), "rd_false": None}
    payload = asdict(report)
    payload.update({
        "frame_fallback_share_of_eligible_population": (len(exposed) / len(eligible) if eligible else None),
        "risk_ratio_when_defined": (
            report.false_rate_frame_fallback / report.false_rate_comparator
            if report.false_rate_comparator not in (None, 0.0) else None
        ),
        "per_corpus_rd_false": per_corpus,
        "sealed_group_universe": list(groups),
    })
    return payload


def _publish(destination: Path, rows: Sequence[Any], attrition: Mapping[str, object], metric: Mapping[str, object], provenance: Mapping[str, object]) -> None:
    staging = destination.parent / f".{destination.name}.staging-{os.getpid()}"
    if destination.exists() or staging.exists():
        raise FileExistsError("H17 publication path already exists")
    try:
        staging.mkdir(parents=True)
        for name, payload in (
            ("grouped_scientific_rows.json", [asdict(row) for row in rows]),
            ("attrition_report.json", attrition),
            ("h17_metric_and_verdict_report.json", metric),
            ("execution_provenance.json", provenance),
        ):
            (staging / name).write_bytes(_canonical_bytes(payload))
        os.replace(staging, destination)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise


def run() -> dict[str, object]:
    repository = Path(__file__).resolve().parents[2]
    paths, recordings, groups, contract, contract_sha = _load_and_verify_preflight(repository)
    marker_payload = _claim_marker(paths, contract_sha)
    current_phase: dict[str, object] = {"phase": "claimed", "recording_index": None, "recording_key": None}
    consumed = False

    def phase(name: str, index: int | None = None, key: str | None = None) -> None:
        nonlocal current_phase
        if name not in PHASES:
            raise RuntimeError("invalid H17 operational phase")
        current_phase = {
            "phase": name, "recording_index": index, "recording_key": key,
            "execution_contract_sha256": contract_sha, "state": "claimed_running",
        }
        _write_json_atomic(paths.phase, current_phase)

    try:
        # Irrevocable H20 boundary: all zero-science checks and marker claim
        # succeeded; persist consumption before the first corpus/model opening.
        _write_json_atomic(paths.state, {
            "fresh_population_consumed": True,
            "execution_contract_sha256": contract_sha,
            "execution_commit": marker_payload["execution_commit"],
            "state": "claimed_running",
            "automatic_retry_allowed": False,
        })
        consumed = True
        adapter = _ScientificAdapter(paths)
        all_rows: list[Any] = []
        per_recording: list[dict[str, object]] = []
        for index, record in enumerate(recordings):  # deliberately no retry loop
            phase("opening", index, record.recording_key)
            rows, summary = adapter.process(
                record, record_phase=phase, recording_index=index
            )
            all_rows.extend(rows)
            per_recording.append(summary)
            print(
                f"H17_PROGRESS processed={index + 1} total={EXPECTED_RECORDINGS}",
                flush=True,
            )
        if len(per_recording) != EXPECTED_RECORDINGS:
            raise RuntimeError("H17 partial cohort before metrics")
        phase("metrics")
        from .provisional_resolution_frame_fallback_h19 import evaluate_h19_synthetic_metrics
        report = evaluate_h19_synthetic_metrics(all_rows, cohort_group_universe=groups)
        metric = _metric_payload(report, all_rows, groups)
        required = {
            "emitted_noteons_initially_considered": report.emitted_noteons_initially_considered,
            "audio_aware_activation_noteons_in_h17_population": report.audio_aware_activation_noteons_in_h17_population,
            "frame_fallback_eligible_count": report.frame_fallback_noteons,
            "comparator_eligible_count": report.comparator_noteons,
            "excluded_harmonic_strong_frame_count": report.excluded_harmonic_strong_frame_count,
            "excluded_legacy_count": report.excluded_legacy_count,
            "excluded_retrigger_count": report.excluded_retrigger_count,
            "target_unmatchable_or_excluded_count": report.target_unmatchable_or_excluded_count,
            "malformed_reason_count": report.malformed_reason_count,
            "malformed_or_nonfinite_target_count": report.malformed_or_nonfinite_target_count,
        }
        if required["emitted_noteons_initially_considered"] != (
            required["audio_aware_activation_noteons_in_h17_population"]
            + required["excluded_harmonic_strong_frame_count"]
            + required["excluded_legacy_count"] + required["excluded_retrigger_count"]
        ):
            raise RuntimeError("H17 reason attrition does not reconcile")
        if required["audio_aware_activation_noteons_in_h17_population"] != (
            required["frame_fallback_eligible_count"] + required["comparator_eligible_count"]
            + required["target_unmatchable_or_excluded_count"]
        ):
            raise RuntimeError("H17 target attrition does not reconcile")
        attrition = {"required_counts": required, "per_recording": per_recording}
        phase("publication")
        provenance = {
            "status": "complete_atomic_result",
            "execution_commit": marker_payload["execution_commit"],
            "execution_contract_sha256": contract_sha,
            "h21_raw_sha256": H21_RAW_SHA256,
            "fresh_population_consumed": True,
            "processed_recordings": len(per_recording),
            "leakage_groups": len(groups),
            "runtime": _runtime_identity(),
            "locked_test_used": False,
            "automatic_retry_allowed": False,
        }
        _publish(paths.destination, all_rows, attrition, metric, provenance)
        _write_json_atomic(paths.state, {**provenance, "state": "completed"})
        print(json.dumps(metric, ensure_ascii=False, sort_keys=True, separators=(",", ":")), flush=True)
        return metric
    except Exception as error:
        if not paths.failure.exists():
            _write_json_atomic(paths.failure, {
                "status": "frame_fallback_execution_invalid",
                "state": "failed",
                "fresh_population_consumed": consumed,
                "automatic_retry_allowed": False,
                "phase": current_phase.get("phase"),
                "recording_index": current_phase.get("recording_index"),
                "recording_key": current_phase.get("recording_key"),
                "error_type": type(error).__name__,
                "error_message": _bounded_message(error),
                "operational_traceback": _bounded_traceback(error),
            })
        raise


def main() -> None:
    if len(sys.argv) != 1:
        raise SystemExit("sealed H17 runner accepts no arguments")
    run()


if __name__ == "__main__":
    main()
