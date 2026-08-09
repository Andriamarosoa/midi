"""Sealed, stateful A/B primitives for the causal-candidate V1 validation.

This module deliberately has no CLI and performs no corpus inference.  A later,
separately reviewed runner must call the preflight before importing TensorFlow
or opening a recording, then provide one shared transcription prediction stream
to :func:`decode_shared_prediction_ab`.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Callable, Mapping, Sequence

import numpy as np

from .causal_candidate_fit import CAUSAL_FEATURES, ENCODED_FEATURES, FitStandardizer
from .decoder import CausalCandidateGateInput, PolyphonicDecoder, PolyphonicDecoderConfig, PolyphonicMidiEvent


SEALED_POLICY_RELATIVE_PATH = Path("configs/causal_candidate_fit_v1_validation_ab_policy.json")
SEALED_SELECTION_RELATIVE_PATH = Path("configs/causal_candidate_fit_v1_validation_selection_12.json")
SEALED_POLICY_SHA256 = "750755910721fc5921f0507e794b20611d82b3f51ad07192d798ef369799f858"
SEALED_SELECTION_SHA256 = "8c3cf53c7f5dcf086b70767e28499c3164aa307059652a6d0a2fc87159f9dcbc"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _require_sha(path: Path, expected: str, name: str) -> None:
    if not path.is_file() or _sha256(path) != expected:
        raise ValueError(f"{name} SHA-256 mismatch.")


def configure_sealed_validation_cpu_tensorflow():
    """Import TensorFlow only after the eight-artifact A/B preflight."""
    if os.environ.get("MIDI_FORCE_CPU") != "1":
        raise RuntimeError("Fail closed: sealed causal validation requires MIDI_FORCE_CPU=1.")
    if "tensorflow" in sys.modules:
        raise RuntimeError(
            "Fail closed: TensorFlow must not be imported before the sealed A/B preflight."
        )
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    try:
        import tensorflow as tf
    except ImportError as error:
        raise RuntimeError("Sealed causal validation requires TensorFlow.") from error
    try:
        tf.config.set_visible_devices([], "GPU")
    except RuntimeError as error:
        raise RuntimeError(
            "Fail closed: TensorFlow GPU visibility was initialized before CPU preflight."
        ) from error
    if tf.config.list_logical_devices("GPU"):
        raise RuntimeError("Fail closed: sealed causal validation must not expose a GPU.")
    return tf


@dataclass(frozen=True)
class SealedValidationContract:
    policy: Mapping[str, object]
    selection: Mapping[str, object]
    standardizer: FitStandardizer
    artifact_sha256: Mapping[str, str]


def load_sealed_validation_contract(
    *,
    repository_root: Path,
    policy_path: Path,
    selection_path: Path,
    fit_report_path: Path,
    model_path: Path,
    standardizer_path: Path,
    manifest_path: Path,
    checkpoint_path: Path,
    evaluation_config_path: Path,
    decoder_config_path: Path,
) -> SealedValidationContract:
    """Validate every immutable A/B input before model or audio inference."""
    root = Path(repository_root).resolve(strict=True)
    expected_policy = (root / SEALED_POLICY_RELATIVE_PATH).resolve(strict=True)
    expected_selection = (root / SEALED_SELECTION_RELATIVE_PATH).resolve(strict=True)
    if Path(policy_path).resolve(strict=True) != expected_policy:
        raise ValueError("Validation policy must use the sealed repository path.")
    if Path(selection_path).resolve(strict=True) != expected_selection:
        raise ValueError("Validation selection must use the sealed repository path.")
    _require_sha(expected_policy, SEALED_POLICY_SHA256, "validation policy")
    _require_sha(expected_selection, SEALED_SELECTION_SHA256, "validation selection")
    policy = json.loads(expected_policy.read_text(encoding="utf-8"))
    selection = json.loads(expected_selection.read_text(encoding="utf-8"))
    if not isinstance(policy, dict) or not isinstance(selection, dict):
        raise ValueError("Sealed validation JSON must contain objects.")
    if policy.get("locked_test_used") is not False or selection.get("locked_test_used") is not False:
        raise PermissionError("The causal validation contract must keep locked test closed.")
    if policy.get("status") != "preregistered_not_executed":
        raise ValueError("Validation policy status is not preregistered.")
    cohort = policy.get("validation_cohort")
    artifacts = policy.get("fit_artifacts")
    contract = policy.get("ab_contract")
    if not isinstance(cohort, dict) or not isinstance(artifacts, dict) or not isinstance(contract, dict):
        raise ValueError("Validation policy is missing sealed sections.")
    if cohort.get("selection_sha256") != SEALED_SELECTION_SHA256:
        raise ValueError("Validation policy selection SHA-256 mismatch.")
    artifact_paths = {
        "model": (model_path, artifacts.get("model_sha256")),
        "standardizer": (standardizer_path, artifacts.get("standardizer_sha256")),
        "fit_report": (fit_report_path, artifacts.get("fit_report_sha256")),
        "manifest": (manifest_path, selection.get("manifest_sha256")),
        "selection": (expected_selection, SEALED_SELECTION_SHA256),
        "checkpoint": (checkpoint_path, selection.get("transcription_checkpoint_sha256")),
        "evaluation_config": (evaluation_config_path, selection.get("evaluation_config_sha256")),
        "reference_decoder_config": (decoder_config_path, selection.get("reference_decoder_config_sha256")),
    }
    required_report = policy.get("required_report")
    if not isinstance(required_report, dict) or tuple(required_report.get("artifact_sha256", ())) != tuple(artifact_paths):
        raise ValueError("Validation policy artifact report contract mismatch.")
    verified_artifact_sha256: dict[str, str] = {}
    # The fit report anchors the model/standardizer provenance and must reject
    # before either binary artifact can be loaded.
    preflight_order = ("fit_report",) + tuple(
        name for name in artifact_paths if name != "fit_report"
    )
    for name in preflight_order:
        path, expected = artifact_paths[name]
        if not isinstance(expected, str):
            raise ValueError(f"Validation policy has no SHA for {name}.")
        _require_sha(Path(path), expected, name)
        verified_artifact_sha256[name] = _sha256(Path(path))
    if cohort.get("recording_count") != 12 or len(selection.get("recording_keys", ())) != 12:
        raise ValueError("Validation A/B requires exactly the sealed 12 recordings.")
    if not all(bool(contract.get(name)) for name in (
        "single_transcription_inference_per_recording",
        "same_base_transcription_predictions",
        "same_base_decoder_configuration",
        "only_branch_specific_decoder_difference_is_causal_candidate_gate",
        "audio_evidence_override_forbidden",
        "audio_evidence_computed_once_per_recording",
        "same_audio_evidence_masks_reused_across_ab",
        "independent_decoder_state_after_gate_decisions",
        "candidate_features_computed_immediately_pre_gate_from_candidate_state",
    )):
        raise ValueError("Validation A/B state or audio contract is incomplete.")
    raw_standardizer = json.loads(Path(standardizer_path).read_text(encoding="utf-8"))
    if not isinstance(raw_standardizer, dict):
        raise ValueError("Causal candidate standardizer must be a JSON object.")
    if raw_standardizer.get("model_sha256") != artifacts["model_sha256"]:
        raise ValueError("Standardizer is not bound to the sealed model.")
    if tuple(raw_standardizer.get("causal_features", ())) != CAUSAL_FEATURES:
        raise ValueError("Standardizer causal feature contract mismatch.")
    if tuple(raw_standardizer.get("encoded_features", ())) != ENCODED_FEATURES:
        raise ValueError("Standardizer encoded feature contract mismatch.")
    standardizer = FitStandardizer(
        mean=tuple(float(value) for value in raw_standardizer.get("mean", ())),
        scale=tuple(float(value) for value in raw_standardizer.get("scale", ())),
    )
    return SealedValidationContract(policy, selection, standardizer, verified_artifact_sha256)


class CausalCandidateGate:
    """Score one candidate immediately before its decoder gate decision."""

    def __init__(
        self,
        *,
        standardizer: FitStandardizer,
        scorer: Callable[[np.ndarray], np.ndarray],
        threshold: float,
    ) -> None:
        if not 0.0 <= float(threshold) <= 1.0:
            raise ValueError("Causal candidate threshold must be in [0, 1].")
        self._standardizer = standardizer
        self._scorer = scorer
        self._threshold = float(threshold)
        self._probabilities: list[float] = []
        self._rejected = 0

    def __call__(self, values: CausalCandidateGateInput) -> bool:
        vector = np.asarray(self._standardizer.transform_pre_gate_values(
            frame_probability=values.frame_probability,
            onset_probability=values.onset_probability,
            candidate_score=values.candidate_score,
            candidate_reason=values.candidate_reason,
            harmonic_support=values.harmonic_support,
            audio_onset_available=values.audio_onset_available,
            audio_onset_recent=values.audio_onset_recent,
            active_polyphony=values.active_polyphony,
        ), dtype=np.float32)
        output = np.asarray(self._scorer(vector[None, :]), dtype=np.float64)
        if output.shape not in {(1,), (1, 1)}:
            raise ValueError("Causal candidate scorer must return one probability.")
        probability = float(output.reshape(-1)[0])
        if not math.isfinite(probability) or not 0.0 <= probability <= 1.0:
            raise ValueError("Causal candidate scorer returned an invalid probability.")
        self._probabilities.append(probability)
        rejected = probability < self._threshold
        self._rejected += int(rejected)
        return rejected

    @property
    def diagnostics(self) -> dict[str, object]:
        values = np.asarray(self._probabilities, dtype=np.float64)
        return {
            "enabled": True,
            "threshold": self._threshold,
            "eligible_candidates": len(self._probabilities),
            "rejected_candidates": self._rejected,
            "probability_min": None if not len(values) else float(values.min()),
            "probability_max": None if not len(values) else float(values.max()),
            "probability_mean": None if not len(values) else float(values.mean()),
        }


@dataclass(frozen=True)
class ABDecodedEvents:
    reference_events: tuple[PolyphonicMidiEvent, ...]
    candidate_events: tuple[PolyphonicMidiEvent, ...]
    reference_decoder: PolyphonicDecoder
    candidate_decoder: PolyphonicDecoder


def decode_shared_prediction_ab(
    *,
    frame: np.ndarray,
    onset: np.ndarray,
    harmonic_amplitude: np.ndarray,
    config: PolyphonicDecoderConfig,
    audio_active: np.ndarray,
    audio_onset: np.ndarray,
    candidate_gate: CausalCandidateGate,
) -> ABDecodedEvents:
    """Decode one shared prediction stream through independent A/B states."""
    frame = np.asarray(frame, dtype=np.float32)
    onset = np.asarray(onset, dtype=np.float32)
    harmonic_amplitude = np.asarray(harmonic_amplitude, dtype=np.float32)
    active = np.asarray(audio_active, dtype=np.bool_)
    attacks = np.asarray(audio_onset, dtype=np.bool_)
    if frame.ndim != 2 or onset.shape != frame.shape or active.shape != (len(frame),) or attacks.shape != (len(frame),):
        raise ValueError("A/B decoder inputs have incompatible frame dimensions.")
    reference = PolyphonicDecoder(config)
    candidate = PolyphonicDecoder(config, causal_candidate_gate=candidate_gate)
    reference_events: list[PolyphonicMidiEvent] = []
    candidate_events: list[PolyphonicMidiEvent] = []
    for index in range(len(frame)):
        kwargs = {
            "audio_active": bool(active[index]),
            "audio_hop_index": index,
            "audio_onset": bool(attacks[index]),
            "audio_onset_hop_index": index if bool(attacks[index]) else None,
        }
        reference_events.extend(reference.step(frame[index], onset[index], harmonic_amplitude[index], **kwargs))
        candidate_events.extend(candidate.step(frame[index], onset[index], harmonic_amplitude[index], **kwargs))
    reference_events.extend(reference.panic())
    candidate_events.extend(candidate.panic())
    return ABDecodedEvents(tuple(reference_events), tuple(candidate_events), reference, candidate)


def infer_once_then_decode_ab(
    *,
    transcription_inference: Callable[[], Mapping[str, np.ndarray]],
    config: PolyphonicDecoderConfig,
    audio_active: np.ndarray,
    audio_onset: np.ndarray,
    candidate_gate: CausalCandidateGate,
) -> ABDecodedEvents:
    """Invoke transcription exactly once, then fork only decoder state."""
    prediction = transcription_inference()
    if not isinstance(prediction, Mapping):
        raise ValueError("Transcription inference must return a mapping.")
    required = ("frame", "onset", "harmonic_amplitude")
    if any(name not in prediction for name in required):
        raise ValueError("Transcription prediction is missing a decoder output.")
    return decode_shared_prediction_ab(
        frame=np.asarray(prediction["frame"]),
        onset=np.asarray(prediction["onset"]),
        harmonic_amplitude=np.asarray(prediction["harmonic_amplitude"]),
        config=config,
        audio_active=audio_active,
        audio_onset=audio_onset,
        candidate_gate=candidate_gate,
    )


def evaluate_sealed_causal_candidate_ab(
    *,
    repository_root: Path,
    run_dir: Path,
    policy_path: Path,
    selection_path: Path,
    fit_report_path: Path,
    model_path: Path,
    standardizer_path: Path,
    manifest_path: Path,
    checkpoint_path: Path,
    evaluation_config_path: Path,
    decoder_config_path: Path,
    report_suffix: str,
) -> dict[str, object]:
    """Run only the sealed A/B evaluator after its preflight has succeeded.

    There is intentionally no CLI here: execution requires a separately
    reviewed worker invocation.  All file hashes are checked before either
    Keras model is loaded or :mod:`evaluate_events` can invoke transcription.
    """
    if not report_suffix:
        raise ValueError("Sealed causal candidate A/B requires a report suffix.")
    sealed = load_sealed_validation_contract(
        repository_root=repository_root,
        policy_path=policy_path,
        selection_path=selection_path,
        fit_report_path=fit_report_path,
        model_path=model_path,
        standardizer_path=standardizer_path,
        manifest_path=manifest_path,
        checkpoint_path=checkpoint_path,
        evaluation_config_path=evaluation_config_path,
        decoder_config_path=decoder_config_path,
    )
    gate_spec = sealed.policy["ab_contract"]
    if not isinstance(gate_spec, Mapping):
        raise ValueError("Sealed A/B gate section is invalid.")
    candidate = gate_spec.get("candidate")
    if not isinstance(candidate, Mapping):
        raise ValueError("Sealed A/B candidate section is invalid.")
    candidate_gate = candidate.get("causal_candidate_gate")
    if not isinstance(candidate_gate, Mapping):
        raise ValueError("Sealed A/B candidate gate is invalid.")
    threshold = candidate_gate.get("threshold")
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)):
        raise ValueError("Sealed A/B candidate threshold is invalid.")
    # This remains after all eight SHA-256 checks in the sealed contract.
    tf = configure_sealed_validation_cpu_tensorflow()
    from .evaluate_events import evaluate_events

    head = tf.keras.models.load_model(model_path, compile=False)

    def scorer(batch: np.ndarray) -> np.ndarray:
        output = head(np.asarray(batch, dtype=np.float32), training=False)
        return np.asarray(output.numpy(), dtype=np.float32)

    def gate_factory() -> CausalCandidateGate:
        return CausalCandidateGate(
            standardizer=sealed.standardizer,
            scorer=scorer,
            threshold=float(threshold),
        )

    report = evaluate_events(
        run_dir=run_dir,
        split="validation",
        maximum_recordings=12,
        checkpoint_path=checkpoint_path,
        decoder_config_path=decoder_config_path,
        report_suffix=report_suffix,
        config_path=evaluation_config_path,
        causal_candidate_gate_factory=gate_factory,
        causal_candidate_selection_path=selection_path,
        write_report=False,
    )
    paired = report.get("paired_ab")
    if not isinstance(paired, Mapping):
        raise RuntimeError("Sealed causal candidate A/B did not produce paired evidence.")
    reference = paired.get("reference")
    candidate_report = paired.get("candidate")
    if not isinstance(reference, Mapping) or not isinstance(candidate_report, Mapping):
        raise RuntimeError("Sealed causal candidate A/B report is incomplete.")
    rules = sealed.policy.get("decision_rules")
    if not isinstance(rules, Mapping):
        raise RuntimeError("Sealed causal candidate A/B rules are invalid.")
    report["causal_candidate_validation"] = {
        "policy_sha256": _sha256(Path(policy_path)),
        "artifact_sha256": dict(sealed.artifact_sha256),
        "audio_evidence_override_forbidden": True,
        "decision": evaluate_preregistered_ab_decision(
            reference=reference,
            candidate=candidate_report,
            rules=rules,
        ),
    }
    report_path = Path(run_dir) / "reports" / (
        f"validation_events_{Path(checkpoint_path).stem}_{report_suffix}.json"
    )
    if report_path.exists():
        raise FileExistsError(
            f"Sealed causal candidate A/B report destination already exists: {report_path}"
        )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def evaluate_preregistered_ab_decision(
    *,
    reference: Mapping[str, object],
    candidate: Mapping[str, object],
    rules: Mapping[str, object],
) -> dict[str, object]:
    """Apply all fixed decision rules; missing/non-finite metrics fail closed."""
    checks: dict[str, bool] = {}
    def number(payload: Mapping[str, object], key: str) -> float:
        value = payload.get(key)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"Missing or non-finite metric: {key}.")
        return float(value)
    ref_onset = reference.get("onset"); cand_onset = candidate.get("onset")
    ref_causal = reference.get("strictly_causal_noteon"); cand_causal = candidate.get("strictly_causal_noteon")
    if not all(isinstance(value, Mapping) for value in (ref_onset, cand_onset, ref_causal, cand_causal)):
        raise ValueError("A/B report is missing required metric sections.")
    ref_global = ref_causal.get("global"); cand_global = cand_causal.get("global")
    if not isinstance(ref_global, Mapping) or not isinstance(cand_global, Mapping):
        raise ValueError("A/B causal global metrics are unavailable.")
    checks["false_positive_notes"] = number(cand_onset, "false_positive_notes") - number(ref_onset, "false_positive_notes") <= number(rules, "candidate_false_positive_notes_delta_maximum")
    checks["onset_recall"] = number(cand_onset, "recall") - number(ref_onset, "recall") >= number(rules, "candidate_global_onset_recall_delta_minimum")
    checks["onset_f1"] = number(cand_onset, "f1") - number(ref_onset, "f1") >= number(rules, "candidate_global_onset_f1_delta_minimum")
    checks["causal_recall_within_max_latency"] = (
        number(cand_global, "recall_within_max_latency")
        - number(ref_global, "recall_within_max_latency")
        >= number(rules, "candidate_global_strictly_causal_recall_delta_minimum")
    )
    hop_ms = number(rules, "causal_latency_hop_ms")
    for percentile in ("p50", "p90"):
        delta_hops = (number(cand_global, f"latency_{percentile}_ms") - number(ref_global, f"latency_{percentile}_ms")) / hop_ms
        checks[f"causal_latency_{percentile}"] = delta_hops <= number(rules, f"candidate_strictly_causal_latency_{percentile}_delta_hops_maximum")
    checks["retriggers"] = number(candidate, "retriggers") - number(reference, "retriggers") <= number(rules, "candidate_retriggers_delta_maximum")
    ref_diag = reference.get("diagnostics"); cand_diag = candidate.get("diagnostics")
    if not isinstance(ref_diag, Mapping) or not isinstance(cand_diag, Mapping):
        raise ValueError("A/B diagnostics are unavailable.")
    checks["excess_fragments"] = number(cand_diag, "excess_fragments") - number(ref_diag, "excess_fragments") <= number(rules, "candidate_excess_fragments_delta_maximum")
    ref_datasets = reference.get("dataset_metrics"); cand_datasets = candidate.get("dataset_metrics")
    if not isinstance(ref_datasets, Mapping) or not isinstance(cand_datasets, Mapping):
        raise ValueError("A/B corpus metrics are unavailable.")
    ref_per = ref_datasets.get("per_dataset"); cand_per = cand_datasets.get("per_dataset")
    if not isinstance(ref_per, Mapping) or not isinstance(cand_per, Mapping) or set(ref_per) != set(cand_per) or not ref_per:
        raise ValueError("A/B corpus coverage differs or is empty.")
    limit = number(rules, "candidate_per_corpus_onset_f1_delta_minimum")
    for dataset in sorted(ref_per):
        left = ref_per[dataset]; right = cand_per[dataset]
        if not isinstance(left, Mapping) or not isinstance(right, Mapping):
            raise ValueError("A/B corpus metric row is invalid.")
        left_onset = left.get("onset"); right_onset = right.get("onset")
        if not isinstance(left_onset, Mapping) or not isinstance(right_onset, Mapping):
            raise ValueError("A/B corpus onset metric is unavailable.")
        checks[f"onset_f1:{dataset}"] = number(right_onset, "f1") - number(left_onset, "f1") >= limit
    ref_low = reference.get("low_midi_40_51"); cand_low = candidate.get("low_midi_40_51")
    if not isinstance(ref_low, Mapping) or not isinstance(cand_low, Mapping):
        raise ValueError("A/B low-MIDI metrics are unavailable.")
    ref_low_onset = ref_low.get("onset"); cand_low_onset = cand_low.get("onset")
    if not isinstance(ref_low_onset, Mapping) or not isinstance(cand_low_onset, Mapping):
        raise ValueError("A/B low-MIDI onset metric is unavailable.")
    checks["low_midi_onset_f1"] = number(cand_low_onset, "f1") - number(ref_low_onset, "f1") >= number(rules, "candidate_low_midi_40_51_onset_f1_delta_minimum")
    return {"all_rules_passed": all(checks.values()), "checks": checks}
