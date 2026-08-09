"""Fail-closed shell for the future independent V2 validation runner.

This module deliberately cannot execute the scientific job in its current
state.  A separately reviewed, identity-attested one-job capability is absent
by design.  Importing or calling ``main`` therefore performs only sealed
contract validation and fails before any manifest, asset, model, TensorFlow,
inference, or metric access.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import threading
from typing import Mapping, Protocol, Sequence
import weakref

from .causal_candidate_v2_independent_validation_execution_contract import (
    IndependentV2ExecutionContract,
    INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256,
    load_sealed_independent_v2_execution_contract,
    require_sealed_independent_v2_execution_contract,
)


_ONE_JOB_CAPABILITIES: dict[int, weakref.ReferenceType[object]] = {}
_CLAIMED_ONE_JOB_CAPABILITIES: dict[int, weakref.ReferenceType[object]] = {}
_ONE_JOB_CAPABILITY_CLAIM_LOCK = threading.Lock()

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


@dataclass(frozen=True)
class IndependentV2ExecutionPaths:
    """Canonical future-run paths, constructed only inside this runner."""
    repository_root: Path
    manifest_path: Path
    asset_evidence_path: Path
    checkpoint_path: Path
    model_path: Path
    standardizer_path: Path
    audio_evidence_config_path: Path
    evaluation_config_path: Path
    reference_decoder_config_path: Path
    destination: Path
    lock_path: Path

    def __post_init__(self) -> None:
        for field in self.__dataclass_fields__:
            object.__setattr__(self, field, Path(getattr(self, field)).resolve())


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
    _validate_report_hierarchy(report.get("hierarchy"), recordings, groups)


def _validate_metric_map(values: object) -> None:
    if not isinstance(values, Mapping) or set(values) != set(REPORT_METRICS):
        raise ValueError("future report metric map is incomplete")
    if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)) for value in values.values()):
        raise ValueError("future report metric map contains non-finite values")


def _validate_report_hierarchy(hierarchy: object, recordings: Sequence[object], groups: Sequence[object]) -> None:
    if not isinstance(hierarchy, Mapping) or tuple(hierarchy) != REPORT_VIEWS:
        raise ValueError("future report hierarchy views are incomplete")
    for view in REPORT_VIEWS:
        scopes = hierarchy[view]
        if not isinstance(scopes, Mapping) or tuple(scopes) != REPORT_GRANULARITIES:
            raise ValueError("future report hierarchy granularity is incomplete")
        _validate_metric_map(scopes["global"])
        for scope, identities in (("per_dataset", REPORT_DATASETS), ("per_recording", recordings), ("per_independent_leakage_group", groups)):
            values = scopes[scope]
            if not isinstance(values, Mapping) or set(values) != set(identities) or "guitarset_poly_mix" in values:
                raise ValueError("future report hierarchy identities are incomplete")
            for metric_map in values.values():
                _validate_metric_map(metric_map)


def classify_failure(state: OneShotStateMachine) -> str:
    return "premetric_infrastructure_failure" if state.phase == OneShotPhase.PRE_SCIENCE and not state.cohort_consumed else "scientific_or_metric_failure"


def evaluate_future_report_decision(
    reference: Mapping[str, object], candidate: Mapping[str, object], rules: Mapping[str, object]
) -> dict[str, object]:
    from .run_causal_candidate_v2_independent_validation import evaluate_independent_v2_decision
    return evaluate_independent_v2_decision(reference=reference, candidate=candidate, rules=rules)


class IndependentV2SystemProbe(Protocol):
    def git_head(self, root: Path) -> str: ...
    def worktree_clean(self, root: Path) -> bool: ...
    def read_bytes(self, path: Path) -> bytes: ...
    def destination_exists(self, path: Path) -> bool: ...
    def heavy_job_active(self, path: Path) -> bool: ...
    def acquire_lease(self, lock_path: Path, destination: Path): ...


class IndependentV2ScientificAdapter(Protocol):
    def manifest_snapshot(self, path: Path) -> object: ...
    def items(self, cohort: object, snapshot: object) -> Sequence[object]: ...
    def prepare_runtime_after_all_gates(self) -> None: ...
    def open_exact_item(self, item: object) -> object: ...
    def close_exact_item(self, opened: object) -> None: ...
    def infer_once(self, opened: object) -> object: ...
    def audio_masks_once(self, opened: object) -> object: ...
    def decode_ab(self, predictions: object, masks: object) -> object: ...
    def accumulate(self, result: object) -> None: ...
    def final_report(self) -> Mapping[str, object]: ...


class _ProductionRunLease:
    def __init__(self, lock_path: Path, destination: Path) -> None:
        self.lock_path = lock_path
        self.destination = destination
        self._fd: int | None = None

    def __enter__(self) -> "_ProductionRunLease":
        self._fd = os.open(self.lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        try:
            self.destination.mkdir(parents=False, exist_ok=False)
        except Exception:
            os.close(self._fd); self._fd = None; self.lock_path.unlink(missing_ok=True)
            raise
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        if self._fd is not None:
            os.close(self._fd); self._fd = None
        self.lock_path.unlink(missing_ok=True)


class _ProductionSystemProbe:
    def git_head(self, root: Path) -> str:
        return subprocess.run(["git", "-C", str(root), "rev-parse", "HEAD"], check=True, capture_output=True, text=True).stdout.strip()
    def worktree_clean(self, root: Path) -> bool:
        return not subprocess.run(["git", "-C", str(root), "status", "--porcelain"], check=True, capture_output=True, text=True).stdout.strip()
    def read_bytes(self, path: Path) -> bytes: return path.resolve(strict=True).read_bytes()
    def destination_exists(self, path: Path) -> bool: return path.exists()
    def heavy_job_active(self, path: Path) -> bool: return path.exists()
    def acquire_lease(self, lock_path: Path, destination: Path) -> _ProductionRunLease: return _ProductionRunLease(lock_path, destination)


class _ProductionScientificAdapter:
    """Lazy real A/B adapter; no scientific import occurs before first inference."""
    def __init__(self, paths: IndependentV2ExecutionPaths) -> None:
        self.paths = paths
        self._cohort: object | None = None
        self._records: list[Mapping[str, object]] = []
        self._current: object | None = None
        self._prediction: Mapping[str, object] | None = None
        self._dependencies: Mapping[str, object] | None = None
        self._runtime: Mapping[str, object] | None = None

    def manifest_snapshot(self, path: Path) -> object:
        # This reader is deliberately TensorFlow-free.  Importing ``data`` here
        # would import TensorFlow before the evidence and frozen-artifact gates.
        from .manifest_snapshot import load_manifest_snapshot
        return load_manifest_snapshot(path)

    def items(self, cohort: object, snapshot: object) -> Sequence[object]:
        from .causal_candidate_v2_independent_asset_evidence import canonical_recording_key
        self._cohort = cohort
        indexed = {canonical_recording_key(item): item for item in snapshot.items}
        return tuple(indexed[key] for key in cohort.recording_keys)

    def prepare_runtime_after_all_gates(self) -> None:
        """Configure CPU TensorFlow once, before any TF-bearing import."""

        if self._dependencies is not None:
            raise RuntimeError("independent V2 runtime was already prepared")
        if "tensorflow" in sys.modules:
            raise RuntimeError("TensorFlow was imported before all independent V2 gates")
        if os.environ.get("MIDI_FORCE_CPU") != "1":
            raise RuntimeError("independent V2 runtime requires MIDI_FORCE_CPU=1")
        from .causal_candidate_validation import configure_sealed_validation_cpu_tensorflow

        tf = configure_sealed_validation_cpu_tensorflow()
        # Every module below is imported only after the sealed CPU preflight.
        import numpy as np
        import yaml
        from .causal_candidate_fit import CAUSAL_FEATURES, ENCODED_FEATURES, FitStandardizer
        from .causal_candidate_validation import CausalCandidateGate
        from .data import PolyphonicCorpus, PolyphonicSequence
        from .evaluate_events import _load_evaluation_decoder_config
        from .keras_compat import load_polyphonic_checkpoint, predict_compat

        self._dependencies = {
            "tf": tf,
            "np": np,
            "yaml": yaml,
            "causal_features": CAUSAL_FEATURES,
            "encoded_features": ENCODED_FEATURES,
            "standardizer_type": FitStandardizer,
            "gate_type": CausalCandidateGate,
            "corpus_type": PolyphonicCorpus,
            "sequence_type": PolyphonicSequence,
            "load_decoder_config": _load_evaluation_decoder_config,
            "load_checkpoint": load_polyphonic_checkpoint,
            "predict": predict_compat,
        }

    def open_exact_item(self, item: object) -> object:
        if self._dependencies is None:
            raise RuntimeError("independent V2 runtime must be prepared before opening assets")
        PolyphonicCorpus = self._dependencies["corpus_type"]
        context = PolyphonicCorpus([item])
        corpus = context.__enter__()
        opened = {"item": item, "context": context, "corpus": corpus}
        self._current = opened
        return opened

    def close_exact_item(self, opened: object) -> None:
        if not isinstance(opened, Mapping) or "context" not in opened:
            raise ValueError("invalid independent V2 opened-item handle")
        opened["context"].__exit__(None, None, None)
        if self._current is opened:
            self._current = None
        self._prediction = None

    def _ensure_runtime(self) -> Mapping[str, object]:
        if self._runtime is not None:
            return self._runtime
        if self._dependencies is None:
            raise RuntimeError("independent V2 runtime dependencies were not prepared")
        dependencies = self._dependencies
        tf = dependencies["tf"]
        np = dependencies["np"]
        yaml = dependencies["yaml"]
        CAUSAL_FEATURES = dependencies["causal_features"]
        ENCODED_FEATURES = dependencies["encoded_features"]
        FitStandardizer = dependencies["standardizer_type"]
        CausalCandidateGate = dependencies["gate_type"]
        _load_evaluation_decoder_config = dependencies["load_decoder_config"]
        load_polyphonic_checkpoint = dependencies["load_checkpoint"]
        config = yaml.safe_load(self.paths.evaluation_config_path.read_text(encoding="utf-8"))
        if not isinstance(config, Mapping):
            raise ValueError("independent V2 evaluation YAML must be an object")
        standardizer_payload = json.loads(self.paths.standardizer_path.read_text(encoding="utf-8"))
        if not isinstance(standardizer_payload, Mapping):
            raise ValueError("independent V2 standardizer must be an object")
        if standardizer_payload.get("model_sha256") != INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256["model_sha256"]:
            raise ValueError("independent V2 standardizer is not bound to the frozen model")
        if tuple(standardizer_payload.get("causal_features", ())) != CAUSAL_FEATURES or tuple(standardizer_payload.get("encoded_features", ())) != ENCODED_FEATURES:
            raise ValueError("independent V2 standardizer feature contract changed")
        standardizer = FitStandardizer(
            mean=tuple(float(value) for value in standardizer_payload.get("mean", ())),
            scale=tuple(float(value) for value in standardizer_payload.get("scale", ())),
        )
        head = tf.keras.models.load_model(self.paths.model_path, compile=False)
        transcription = load_polyphonic_checkpoint(self.paths.checkpoint_path)
        outputs = {
            name: transcription.get_layer(name).output
            for name in ("frame", "onset", "harmonic_amplitude")
        }
        if "independent_note" in {layer.name for layer in transcription.layers}:
            outputs["independent_note"] = transcription.get_layer("independent_note").output
        inference_model = tf.keras.Model(transcription.inputs, outputs)

        def scorer(batch):
            values = head(np.asarray(batch, dtype=np.float32), training=False)
            return np.asarray(values.numpy(), dtype=np.float32)

        audio_policy = json.loads(self.paths.audio_evidence_config_path.read_text(encoding="utf-8"))
        if not isinstance(audio_policy, Mapping) or audio_policy.get("onset_adapt_temporal_background") is not True:
            raise ValueError("independent V2 audio-evidence policy changed")
        self._runtime = {
            "tf": tf,
            "config": config,
            "inference_model": inference_model,
            "decoder_config": _load_evaluation_decoder_config(
                self.paths.reference_decoder_config_path,
                thresholds_path=None,
                run_dir=self.paths.destination,
            ),
            "gate_type": CausalCandidateGate,
            "standardizer": standardizer,
            "scorer": scorer,
            "audio_metadata": {"audio_evidence": dict(audio_policy)},
        }
        return self._runtime

    def infer_once(self, opened: object) -> object:
        runtime = self._ensure_runtime()
        dependencies = self._dependencies
        np = dependencies["np"]
        PolyphonicSequence = dependencies["sequence_type"]
        predict_compat = dependencies["predict"]
        corpus = opened["corpus"]
        arrays = corpus.labels[0].arrays
        config = runtime["config"]
        refs = np.column_stack((np.zeros(len(arrays["active_bits"]), dtype=np.int32), np.arange(len(arrays["active_bits"]), dtype=np.int32)))
        sequence = PolyphonicSequence(
            corpus,
            batch_size=int(config["train"]["batch_size"]),
            input_samples=int(config["dataset"]["input_samples"]),
            normalization_gain=float(config["dataset"]["normalization_gain"]),
            seed=0, refs=refs, shuffle=False,
        )
        self._prediction = predict_compat(runtime["inference_model"], sequence, verbose=0, workers=1)
        return self._prediction

    def audio_masks_once(self, opened: object) -> object:
        from .audio_evidence import offline_audio_evidence_masks
        runtime = self._ensure_runtime()
        corpus = opened["corpus"]
        audio = corpus.audio(0)
        return offline_audio_evidence_masks(
            audio, corpus.sample_rate, corpus.hop_size,
            frame_count=len(self._prediction["frame"]),
            metadata=runtime["audio_metadata"],
        )

    def decode_ab(self, predictions: object, masks: object) -> object:
        from .causal_candidate_validation import CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
        from .evaluate_events import (
            _audio_duration_s, build_strictly_causal_noteon_clip,
            decode_probabilities, diagnose_note_errors, match_notes,
            note_metrics, truth_notes,
        )
        runtime = self._ensure_runtime()
        opened = self._current
        corpus = opened["corpus"]
        item = opened["item"]
        activity, onset, audio_report = masks
        reference_estimated, reference_retriggers = decode_probabilities(
            predictions["frame"], predictions["onset"], predictions["harmonic_amplitude"],
            runtime["decoder_config"], corpus.sample_rate, corpus.hop_size,
            activity, onset, predictions.get("independent_note"),
        )
        gate = runtime["gate_type"](
            standardizer=runtime["standardizer"], scorer=runtime["scorer"], threshold=0.31,
        )
        candidate_estimated, candidate_retriggers = decode_probabilities(
            predictions["frame"], predictions["onset"], predictions["harmonic_amplitude"],
            runtime["decoder_config"], corpus.sample_rate, corpus.hop_size,
            activity, onset, predictions.get("independent_note"), {}, (), gate,
            CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON,
        )
        truth = truth_notes(corpus.labels[0].arrays)
        duration = _audio_duration_s(corpus.audio(0), corpus.sample_rate)

        def branch(estimated, retriggers, gate_diagnostics):
            matches = match_notes(truth, estimated)
            offset_matches = match_notes(truth, estimated, require_offset=True)
            low_truth = [note for note in truth if 40 <= note.pitch <= 51]
            low_estimated = [note for note in estimated if 40 <= note.pitch <= 51]
            clip, causal = build_strictly_causal_noteon_clip(
                truth, estimated,
                clip_id=f"{item.source_id}::{item.capture_id}",
                corpus_id=str(item.dataset_id), duration_s=duration,
            )
            return {
                "onset": note_metrics(truth, estimated, matches),
                "onset_offset": note_metrics(truth, estimated, offset_matches),
                "strictly_causal_noteon": causal,
                "retriggers": retriggers,
                "diagnostics": diagnose_note_errors(truth, estimated, matches),
                "low_midi_40_51": note_metrics(
                    low_truth, low_estimated, match_notes(low_truth, low_estimated),
                ),
                "causal_candidate_gate": gate_diagnostics,
                "_estimated": estimated,
                "_causal_clip": clip,
            }

        return {
            "item": item, "truth": truth, "duration_s": duration,
            "audio_evidence": audio_report,
            "reference": branch(reference_estimated, reference_retriggers, None),
            "candidate": branch(candidate_estimated, candidate_retriggers, gate.diagnostics),
        }

    def accumulate(self, result: object) -> None:
        self._records.append(result)

    @staticmethod
    def _sum_diagnostics(rows: Sequence[Mapping[str, object]]) -> dict[str, int]:
        names = ("harmonic_interval_false_positives", "fragmented_reference_notes", "excess_fragments", "false_positive_without_active_reference")
        return {name: sum(int(row["diagnostics"].get(name, 0)) for row in rows) for name in names}

    def _aggregate_branch(self, records: Sequence[Mapping[str, object]], branch_name: str) -> dict[str, object]:
        from .evaluate_events import aggregate_dataset_note_metrics, aggregate_strictly_causal_noteon_metrics
        rows = []
        clips = []
        for record in records:
            branch = record[branch_name]
            item = record["item"]
            rows.append({
                "dataset_id": item.dataset_id,
                "onset": branch["onset"], "onset_offset": branch["onset_offset"],
                "retriggers": branch["retriggers"], "diagnostics": branch["diagnostics"],
            })
            clips.append(branch["_causal_clip"])
        onset = self._micro([row["onset"] for row in rows])
        onset_offset = self._micro([row["onset_offset"] for row in rows])
        return {
            "onset": onset,
            "onset_offset": onset_offset,
            "strictly_causal_noteon": aggregate_strictly_causal_noteon_metrics(clips),
            "dataset_metrics": aggregate_dataset_note_metrics(rows),
            "retriggers": sum(int(row["retriggers"]) for row in rows),
            "diagnostics": self._sum_diagnostics(rows),
            "per_recording": rows,
            "gate_eligible_count": sum(int((record[branch_name].get("causal_candidate_gate") or {}).get("eligible_candidates", 0)) for record in records),
            "gate_rejected_count": sum(int((record[branch_name].get("causal_candidate_gate") or {}).get("rejected_candidates", 0)) for record in records),
            "low_midi_40_51": self._micro([
                record[branch_name]["low_midi_40_51"] for record in records
            ]),
        }

    @staticmethod
    def _micro(rows: Sequence[Mapping[str, object]]) -> dict[str, float | int]:
        counts = {name: sum(int(row[name]) for row in rows) for name in ("reference_notes", "estimated_notes", "matched_notes", "false_positive_notes", "missing_notes")}
        precision = counts["matched_notes"] / max(counts["estimated_notes"], 1)
        recall = counts["matched_notes"] / max(counts["reference_notes"], 1)
        return {**counts, "precision": precision, "recall": recall, "f1": 2.0 * precision * recall / max(precision + recall, 1e-12), "onset_error_mean_ms": 0.0, "onset_error_p95_absolute_ms": 0.0}

    @staticmethod
    def _metric_map(branch: Mapping[str, object]) -> dict[str, float | int]:
        onset = branch["onset"]
        causal = branch["strictly_causal_noteon"]["global"]
        diagnostics = branch["diagnostics"]
        return {
            "estimated_noteons": onset["estimated_notes"],
            "matched_onset_noteons": onset["matched_notes"],
            "onset_false_positives": onset["false_positive_notes"],
            "onset_misses": onset["missing_notes"],
            "onset_precision": onset["precision"], "onset_recall": onset["recall"], "onset_f1": onset["f1"],
            "causal_false_noteons": causal["false_noteons"],
            "causal_false_noteons_per_minute": causal["false_noteons_per_min"],
            "causal_recall_within_250ms": causal["recall_within_max_latency"],
            "causal_latency_p50_ms": causal["latency_p50_ms"], "causal_latency_p90_ms": causal["latency_p90_ms"],
            "retriggers": branch["retriggers"], "excess_fragments": diagnostics["excess_fragments"],
            "midi_40_51": branch["low_midi_40_51"]["false_positive_notes"],
            "gate_eligible_count": branch["gate_eligible_count"], "gate_rejected_count": branch["gate_rejected_count"],
        }

    def final_report(self) -> Mapping[str, object]:
        from .causal_candidate_v2_independent_asset_evidence import canonical_recording_key
        from .decoder_candidate_provenance import leakage_group_key

        records = tuple(self._records)
        recording_keys = tuple(canonical_recording_key(record["item"]) for record in records)
        groups = tuple(sorted({leakage_group_key(record["item"]) for record in records}))

        def scoped(grouped):
            result = {}
            for key, subset in grouped.items():
                result[key] = {
                    branch: self._metric_map(self._aggregate_branch(subset, branch))
                    for branch in ("reference", "candidate")
                }
                result[key]["delta_candidate_minus_reference"] = {
                    name: result[key]["candidate"][name] - result[key]["reference"][name]
                    for name in REPORT_METRICS
                }
            return result

        datasets = {name: [record for record in records if record["item"].dataset_id == name] for name in REPORT_DATASETS}
        recordings = {canonical_recording_key(record["item"]): [record] for record in records}
        leakage = {group: [record for record in records if leakage_group_key(record["item"]) == group] for group in groups}
        global_branches = {name: self._aggregate_branch(records, name) for name in ("reference", "candidate")}
        global_maps = {name: self._metric_map(value) for name, value in global_branches.items()}
        global_maps["delta_candidate_minus_reference"] = {name: global_maps["candidate"][name] - global_maps["reference"][name] for name in REPORT_METRICS}
        scoped_maps = {
            "per_dataset": scoped(datasets), "per_recording": scoped(recordings),
            "per_independent_leakage_group": scoped(leakage),
        }
        hierarchy = {
            view: {
                "global": global_maps[view],
                **{scope: {key: values[view] for key, values in payload.items()} for scope, payload in scoped_maps.items()},
            }
            for view in REPORT_VIEWS
        }
        return {
            "views": REPORT_VIEWS, "granularity": REPORT_GRANULARITIES,
            "datasets": REPORT_DATASETS, "recording_count": len(recording_keys),
            "independent_group_count": len(groups), "metrics": REPORT_METRICS,
            "provenance": REPORT_PROVENANCE, "locked_test_used": False,
            "numeric_values": global_maps["candidate"],
            "recording_identities": recording_keys, "independent_leakage_groups": groups,
            "hierarchy": hierarchy,
            "decision_inputs": global_branches,
        }


def _build_production_execution_paths(repository_root: Path, capability: IndependentV2OneJobCapability) -> IndependentV2ExecutionPaths:
    root = Path(repository_root).resolve(strict=True)
    worker_root = root.parent
    from .run_causal_candidate_v2_train_dev_diagnostic import sealed_v2_diagnostic_paths
    prior = sealed_v2_diagnostic_paths(root, worker_root)
    return IndependentV2ExecutionPaths(
        repository_root=root,
        manifest_path=prior.manifest_path,
        asset_evidence_path=root / "tmp" / "local" / "causal_candidate_v2_independent_validation_asset_evidence_20260810.json",
        checkpoint_path=prior.checkpoint_path,
        model_path=prior.model_path,
        standardizer_path=prior.standardizer_path,
        audio_evidence_config_path=prior.audio_evidence_config_path,
        evaluation_config_path=prior.evaluation_config_path,
        reference_decoder_config_path=prior.decoder_config_path,
        destination=(
            Path(capability.destination)
            if Path(capability.destination).is_absolute()
            else root / Path(capability.destination)
        ),
        lock_path=root / "tmp" / "local" / "causal_candidate_v2_independent_validation.active.lock",
    )


def _run_sealed_independent_v2_execution(paths: IndependentV2ExecutionPaths, capability: object, *, system_probe: IndependentV2SystemProbe, scientific_adapter: IndependentV2ScientificAdapter) -> Mapping[str, object]:
    """Single direct future production sequence, injectable only for synthetic tests."""
    cap = require_claimed_sealed_one_job_capability(capability)
    contract = _require_execution_contract(paths.repository_root)
    capability_destination = Path(cap.destination)
    if not capability_destination.is_absolute():
        capability_destination = paths.repository_root / capability_destination
    if capability_destination.resolve() != paths.destination:
        raise ValueError("capability destination differs from sealed path")
    validate_runtime_preflight(contract, cap, repository_root=paths.repository_root, git_commit=system_probe.git_head(paths.repository_root), device="cpu", timeout_seconds=900, destination_exists=system_probe.destination_exists(paths.destination), heavy_job_active=system_probe.heavy_job_active(paths.lock_path), worktree_clean=system_probe.worktree_clean(paths.repository_root))
    from .run_causal_candidate_v2_independent_validation import load_sealed_independent_v2_validation_cohort, require_sealed_independent_v2_validation_cohort, validation_asset_evidence_requirement
    cohort = require_sealed_independent_v2_validation_cohort(load_sealed_independent_v2_validation_cohort(paths.repository_root, paths.manifest_path))
    requirement = validation_asset_evidence_requirement(cohort)
    snapshot = scientific_adapter.manifest_snapshot(paths.manifest_path)
    from .causal_candidate_v2_independent_asset_evidence import load_independent_v2_validation_asset_evidence, validate_independent_v2_validation_asset_evidence, verify_independent_v2_validation_audio_asset_for_item, verify_independent_v2_validation_label_asset_for_item
    persisted = load_independent_v2_validation_asset_evidence(paths.asset_evidence_path, cohort, requirement)
    evidence = validate_independent_v2_validation_asset_evidence(persisted, cohort, snapshot, requirement)
    artifact_paths = dict(zip(FROZEN_ARTIFACT_NAMES, (paths.checkpoint_path, paths.model_path, paths.standardizer_path, paths.audio_evidence_config_path, paths.evaluation_config_path, paths.reference_decoder_config_path)))
    validate_frozen_artifact_hashes({name: system_probe.read_bytes(path) for name, path in artifact_paths.items()})
    items = tuple(scientific_adapter.items(cohort, snapshot))
    from .causal_candidate_v2_independent_asset_evidence import canonical_recording_key
    from .decoder_candidate_provenance import leakage_group_key
    snapshot_by_key = {canonical_recording_key(item): item for item in snapshot.items}
    item_keys = tuple(canonical_recording_key(item) for item in items)
    if (
        len(items) != 30
        or len(set(item_keys)) != 30
        or item_keys != tuple(cohort.recording_keys)
        or any(snapshot_by_key.get(key) is not item for key, item in zip(item_keys, items))
    ):
        raise RuntimeError("independent V2 execution items differ from the sealed cohort")
    dataset_counts = Counter(str(item.dataset_id) for item in items)
    groups = tuple(sorted({leakage_group_key(item) for item in items}))
    if dataset_counts != Counter({name: 10 for name in REPORT_DATASETS}) or "guitarset_poly_mix" in dataset_counts:
        raise RuntimeError("independent V2 execution dataset counts differ from the sealed cohort")
    if len(groups) != 20 or groups != tuple(cohort.leakage_groups):
        raise RuntimeError("independent V2 execution leakage groups differ from the sealed cohort")
    state = OneShotStateMachine()
    with system_probe.acquire_lease(paths.lock_path, paths.destination):
        scientific_adapter.prepare_runtime_after_all_gates()
        for item in items:
            verify_independent_v2_validation_audio_asset_for_item(evidence, item)
            verify_independent_v2_validation_label_asset_for_item(evidence, item)
            if state.phase == OneShotPhase.PRE_SCIENCE: state.advance(OneShotPhase.SCIENTIFIC_ASSET_OPENED)
            opened = scientific_adapter.open_exact_item(item)
            try:
                if state.phase == OneShotPhase.SCIENTIFIC_ASSET_OPENED: state.advance(OneShotPhase.INFERENCE_STARTED)
                predictions = scientific_adapter.infer_once(opened)
                masks = scientific_adapter.audio_masks_once(opened)
                result = scientific_adapter.decode_ab(predictions, masks)
                if state.phase == OneShotPhase.INFERENCE_STARTED: state.advance(OneShotPhase.AB_METRIC_PRODUCED)
                if not state.cohort_consumed: raise AssertionError("first A/B result must consume cohort")
                scientific_adapter.accumulate(result)
            finally:
                scientific_adapter.close_exact_item(opened)
        report = dict(scientific_adapter.final_report())
        report["provenance_values"] = {
            "git_commit": cap.runner_commit,
            "worker_device": "cpu",
            "execution_contract_sha256": contract.contract_sha256,
            "closed_independent_protocol_sha256": contract.closed_independent_protocol_sha256,
            "asset_evidence_sha256": contract.asset_evidence_sha256,
            "asset_evidence_builder_protocol_sha256": contract.asset_evidence_builder_protocol_sha256,
            "manifest_sha256": snapshot.manifest_sha256,
            "historical_selection_sha256": cohort.historical_selection_sha256,
            "all_frozen_artifact_sha256": dict(INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256),
            "all_thirty_recording_identities_and_twenty_leakage_groups": {
                "recording_identities": item_keys, "independent_leakage_groups": groups,
            },
            "candidate_gate_placement": contract.candidate_gate_placement,
            "locked_test_used": False,
        }
        validate_future_report(report)
        decision_inputs = report.get("decision_inputs")
        if not isinstance(decision_inputs, Mapping):
            raise ValueError("independent V2 report lacks canonical decision inputs")
        decision = evaluate_future_report_decision(
            decision_inputs.get("reference"), decision_inputs.get("candidate"),
            dict(contract.decision_rules),
        )
        if decision.get("automatic_promotion") is not False or not isinstance(decision.get("checks"), Mapping):
            raise ValueError("independent V2 canonical decision is incomplete")
        report["decision"] = decision
        state.advance(OneShotPhase.COHORT_CONSUMED)
        report["terminal_state"] = OneShotPhase.REPORT_WRITTEN.value
        report["cohort_consumed"] = state.cohort_consumed
        report_path = paths.destination / "independent_v2_execution_report.json"
        temporary = report_path.with_suffix(".json.part")
        temporary.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        os.replace(temporary, report_path)
        state.advance(OneShotPhase.REPORT_WRITTEN)
        return report


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


def claim_sealed_one_job_capability(value: object) -> IndependentV2OneJobCapability:
    """Consume an attested authorization before any execution-side builder.

    A failed first attempt is still an attempt: the same identity-attested
    object can never be reused after a preflight, lease, or scientific error.
    """

    with _ONE_JOB_CAPABILITY_CLAIM_LOCK:
        checked = require_sealed_one_job_capability(value)
        reference = _CLAIMED_ONE_JOB_CAPABILITIES.get(id(checked))
        if reference is not None and reference() is checked:
            raise RuntimeError("Fail closed: independent V2 one-job capability was already claimed.")
        _CLAIMED_ONE_JOB_CAPABILITIES[id(checked)] = weakref.ref(checked)
        return checked


def require_claimed_sealed_one_job_capability(value: object) -> IndependentV2OneJobCapability:
    checked = require_sealed_one_job_capability(value)
    reference = _CLAIMED_ONE_JOB_CAPABILITIES.get(id(checked))
    if reference is None or reference() is not checked:
        raise RuntimeError("Fail closed: independent V2 one-job capability was not claimed.")
    return checked


def _require_execution_contract(repository_root: Path) -> IndependentV2ExecutionContract:
    contract = load_sealed_independent_v2_execution_contract(repository_root)
    return require_sealed_independent_v2_execution_contract(contract)


def run_authorized_independent_v2(
    repository_root: Path,
    capability: object,
) -> Mapping[str, object]:
    """Guard the future scientific path; the capability factory is absent."""

    checked = claim_sealed_one_job_capability(capability)
    paths = _build_production_execution_paths(repository_root, checked)
    probe = _ProductionSystemProbe()
    adapter = _ProductionScientificAdapter(paths)
    return _run_sealed_independent_v2_execution(
        paths, checked, system_probe=probe, scientific_adapter=adapter,
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
    "claim_sealed_one_job_capability",
    "classify_failure",
    "validate_frozen_artifact_hashes",
    "validate_future_report",
    "validate_runtime_preflight",
    "main",
    "require_sealed_one_job_capability",
    "run_authorized_independent_v2",
]
