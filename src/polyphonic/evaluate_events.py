"""Continuous note-event evaluation for the causal polyphonic decoder."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Mapping, Sequence

import numpy as np

_FORCE_CPU = os.environ.get("MIDI_FORCE_CPU") == "1"
if _FORCE_CPU:
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"

import tensorflow as tf
import yaml

if _FORCE_CPU:
    tf.config.set_visible_devices([], "GPU")

from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.keras_compat import load_polyphonic_checkpoint
from src.polyphonic.audio_evidence import offline_audio_evidence_masks
from src.polyphonic.causal_event_metrics import (
    CausalMetricGate,
    ClipNoteOnData,
    DEFAULT_RECALL_DEADLINES_MS,
    NoteOnPrediction,
    ReferenceNote,
    compute_causal_note_on_metrics,
    evaluate_causal_event_metrics,
)
from src.polyphonic.data import (
    ManifestItem,
    PolyphonicCorpus,
    PolyphonicSequence,
    load_manifest,
)
from src.polyphonic.keras_compat import predict_compat
from src.polyphonic.decoder import (
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
    PolyphonicMidiEvent,
    default_decoder_config,
)
from src.polyphonic.event_diagnostics import diagnose_note_errors

INDEPENDENT_NOTE_DIAGNOSTIC_THRESHOLDS = (
    0.001, 0.005, 0.01, 0.02, 0.05, 0.10, 0.20, 0.50,
    0.60, 0.70, 0.80, 0.90,
)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@dataclass(frozen=True)
class NoteInterval:
    pitch: int
    start_s: float
    end_s: float


def _audio_duration_s(audio: np.ndarray, sample_rate: int) -> float:
    """Return the evaluated duration from real audio samples."""
    if sample_rate <= 0:
        raise ValueError("sample_rate must be positive.")
    values = np.asarray(audio)
    if values.ndim < 1:
        raise ValueError("audio must have a sample dimension.")
    return float(values.shape[0] / sample_rate)


def build_strictly_causal_noteon_clip(
    reference: Sequence[NoteInterval],
    estimated: Sequence[NoteInterval],
    *,
    clip_id: str,
    corpus_id: str,
    duration_s: float,
    recall_deadlines_ms: Sequence[float] = DEFAULT_RECALL_DEADLINES_MS,
) -> tuple[ClipNoteOnData, dict[str, object]]:
    """Convert historical intervals to an independently scored causal clip."""
    clip = ClipNoteOnData(
        clip_id=clip_id,
        corpus_id=corpus_id,
        duration_s=duration_s,
        reference=[
            ReferenceNote(note.pitch, note.start_s, note.end_s)
            for note in reference
        ],
        predictions=[
            NoteOnPrediction(note.pitch, note.start_s)
            for note in estimated
        ],
    )
    metrics = compute_causal_note_on_metrics(
        clip.reference,
        clip.predictions,
        duration_s=clip.duration_s,
        recall_deadlines_ms=recall_deadlines_ms,
    )
    return clip, metrics


def aggregate_strictly_causal_noteon_metrics(
    clips: Sequence[ClipNoteOnData],
    gate: CausalMetricGate | None = None,
) -> dict[str, object]:
    """Expose causal global/corpus metrics separately from historical F1."""
    if not clips:
        return {
            "available": False,
            "reason": "no_evaluation_recordings",
            "global": None,
            "by_corpus": {},
        }
    causal_report = evaluate_causal_event_metrics(clips, gate=gate)
    return {
        "available": True,
        "definition": (
            "Strictly causal NoteOn matching: same pitch, prediction at or "
            "after the reference onset, matched independently per recording."
        ),
        "policy": causal_report["policy"],
        "configuration": causal_report["configuration"],
        "global": causal_report["aggregate"],
        "by_corpus": causal_report["by_corpus"],
        "worst": causal_report["worst"],
        "gate": causal_report["gate"],
    }


def _recording_key(item: ManifestItem) -> tuple[str, ...]:
    """Return a stable total order for manifest recordings."""
    return (
        str(item.dataset_id), str(item.group_id), str(item.source_id),
        str(item.capture_id), str(item.audio_path), str(item.audio_member),
        str(item.labels_path),
    )


def select_evaluation_recordings(
    manifest_items: Sequence[ManifestItem],
    split: str,
    maximum_recordings: int | None = None,
    dataset_id: str | None = None,
) -> list[ManifestItem]:
    """Select a deterministic dataset- and group-stratified subset.

    Dataset round-robin keeps source domains balanced. Within each dataset,
    the globally least-used group is selected first. The global group count is
    intentional: paired captures such as Guitar-TECHS direct input and mic/amp
    do not consume the limited validation budget with the same performance
    while unused performances remain.
    """
    if maximum_recordings is not None and maximum_recordings < 1:
        raise ValueError("maximum_recordings must be positive.")
    eligible = sorted(
        (
            item for item in manifest_items
            if item.split == split
            and (dataset_id is None or item.dataset_id == dataset_id)
        ),
        key=_recording_key,
    )
    if not eligible:
        return []
    target = min(maximum_recordings or len(eligible), len(eligible))

    queues: dict[str, dict[str, list[ManifestItem]]] = {}
    for item in eligible:
        queues.setdefault(str(item.dataset_id), {}).setdefault(
            str(item.group_id), []
        ).append(item)

    selected: list[ManifestItem] = []
    group_usage: Counter[str] = Counter()
    dataset_order = sorted(queues)
    while len(selected) < target:
        progressed = False
        for current_dataset in dataset_order:
            groups = queues[current_dataset]
            available_groups = [
                group_id for group_id, rows in groups.items() if rows
            ]
            if not available_groups:
                continue
            chosen_group = min(
                available_groups,
                key=lambda group_id: (group_usage[group_id], group_id),
            )
            selected.append(groups[chosen_group].pop(0))
            group_usage[chosen_group] += 1
            progressed = True
            if len(selected) == target:
                break
        if not progressed:
            raise RuntimeError("Stratified recording selection made no progress.")
    return selected


def _selection_report(
    eligible: Sequence[ManifestItem],
    selected: Sequence[ManifestItem],
    maximum_recordings: int | None,
) -> dict[str, object]:
    eligible_by_dataset = Counter(str(item.dataset_id) for item in eligible)
    selected_by_dataset = Counter(str(item.dataset_id) for item in selected)
    selected_groups = {str(item.group_id) for item in selected}
    selected_sources = {
        (str(item.dataset_id), str(item.source_id)) for item in selected
    }
    groups_by_dataset = {
        dataset: len({
            str(item.group_id) for item in selected
            if str(item.dataset_id) == dataset
        })
        for dataset in sorted(selected_by_dataset)
    }
    sources_by_dataset = {
        dataset: len({
            str(item.source_id) for item in selected
            if str(item.dataset_id) == dataset
        })
        for dataset in sorted(selected_by_dataset)
    }
    return {
        "policy": (
            "Deterministic dataset round-robin with globally least-used "
            "group_id first."
        ),
        "manifest_order_independent": True,
        "maximum_recordings": maximum_recordings,
        "eligible_recordings": len(eligible),
        "selected_recordings": len(selected),
        "dataset_count": len(selected_by_dataset),
        "group_count": len(selected_groups),
        "source_count": len(selected_sources),
        "eligible_recordings_by_dataset": dict(sorted(eligible_by_dataset.items())),
        "selected_recordings_by_dataset": dict(sorted(selected_by_dataset.items())),
        "selected_groups_by_dataset": groups_by_dataset,
        "selected_sources_by_dataset": sources_by_dataset,
    }


def events_to_notes(
    events: list[PolyphonicMidiEvent],
    sample_rate: int,
    hop_size: int,
    final_frame: int,
) -> list[NoteInterval]:
    active: dict[int, float] = {}
    notes: list[NoteInterval] = []

    def time_s(frame_index: int) -> float:
        return (frame_index + 1) * hop_size / sample_rate

    for event in events:
        event_time = time_s(event.frame_index)
        if event.kind == "note_on":
            if event.pitch in active:
                notes.append(NoteInterval(
                    event.pitch, active[event.pitch], event_time
                ))
            active[event.pitch] = event_time
        elif event.kind == "note_off" and event.pitch in active:
            start = active.pop(event.pitch)
            if event_time > start:
                notes.append(NoteInterval(event.pitch, start, event_time))
    final_time = time_s(final_frame)
    notes.extend(
        NoteInterval(pitch, start, final_time)
        for pitch, start in active.items()
        if final_time > start
    )
    return sorted(notes, key=lambda note: (note.start_s, note.pitch, note.end_s))


def truth_notes(arrays: dict[str, np.ndarray]) -> list[NoteInterval]:
    required = {
        "note_pitch_midi", "note_start_s", "note_end_s",
        "note_evaluation_valid",
    }
    missing = required - set(arrays)
    if missing:
        raise ValueError(f"Event label arrays missing: {sorted(missing)}")
    return [
        NoteInterval(int(pitch), float(start), float(end))
        for pitch, start, end, valid in zip(
            arrays["note_pitch_midi"], arrays["note_start_s"],
            arrays["note_end_s"], arrays["note_evaluation_valid"],
        )
        if valid and end > start
    ]


def match_notes(
    reference: list[NoteInterval],
    estimated: list[NoteInterval],
    onset_tolerance_s: float = 0.050,
    require_offset: bool = False,
) -> list[tuple[int, int]]:
    candidates: list[tuple[float, float, int, int]] = []
    for reference_index, truth in enumerate(reference):
        for estimated_index, prediction in enumerate(estimated):
            if truth.pitch != prediction.pitch:
                continue
            onset_error = abs(prediction.start_s - truth.start_s)
            if onset_error > onset_tolerance_s:
                continue
            offset_error = abs(prediction.end_s - truth.end_s)
            if require_offset:
                tolerance = max(0.050, 0.20 * (truth.end_s - truth.start_s))
                if offset_error > tolerance:
                    continue
            candidates.append((onset_error, offset_error, reference_index, estimated_index))
    matched_reference: set[int] = set()
    matched_estimated: set[int] = set()
    matches: list[tuple[int, int]] = []
    for _, _, reference_index, estimated_index in sorted(candidates):
        if reference_index in matched_reference or estimated_index in matched_estimated:
            continue
        matched_reference.add(reference_index)
        matched_estimated.add(estimated_index)
        matches.append((reference_index, estimated_index))
    return matches


def note_metrics(
    reference: list[NoteInterval],
    estimated: list[NoteInterval],
    matches: list[tuple[int, int]],
) -> dict[str, float | int]:
    true_positive = len(matches)
    false_positive = len(estimated) - true_positive
    false_negative = len(reference) - true_positive
    precision = true_positive / max(len(estimated), 1)
    recall = true_positive / max(len(reference), 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    onset_errors = [
        (estimated[estimated_index].start_s - reference[reference_index].start_s)
        * 1000.0
        for reference_index, estimated_index in matches
    ]
    return {
        "reference_notes": len(reference),
        "estimated_notes": len(estimated),
        "matched_notes": true_positive,
        "false_positive_notes": false_positive,
        "missing_notes": false_negative,
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "onset_error_mean_ms": float(np.mean(onset_errors)) if onset_errors else 0.0,
        "onset_error_p95_absolute_ms": (
            float(np.percentile(np.abs(onset_errors), 95)) if onset_errors else 0.0
        ),
    }


_COUNT_METRICS = (
    "reference_notes", "estimated_notes", "matched_notes",
    "false_positive_notes", "missing_notes",
)


def _micro_metrics(rows: Sequence[Mapping[str, object]]) -> dict[str, float | int]:
    totals = {
        metric: sum(int(row[metric]) for row in rows)
        for metric in _COUNT_METRICS
    }
    precision = totals["matched_notes"] / max(totals["estimated_notes"], 1)
    recall = totals["matched_notes"] / max(totals["reference_notes"], 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        **totals,
        "precision": precision,
        "recall": recall,
        "f1": f1,
    }


def _mean_dataset_scores(
    per_dataset: Mapping[str, Mapping[str, object]],
    weights: Mapping[str, float],
) -> dict[str, object]:
    result: dict[str, object] = {"dataset_count": len(weights)}
    for metric_name in ("onset", "onset_offset"):
        result[metric_name] = {
            score: sum(
                float(per_dataset[dataset][metric_name][score]) * weight
                for dataset, weight in weights.items()
            )
            for score in ("precision", "recall", "f1")
        }
    return result


def aggregate_dataset_note_metrics(
    recording_reports: Sequence[Mapping[str, object]],
    validation_dataset_fractions: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Aggregate recording counts without letting long datasets set the score."""
    grouped: dict[str, list[Mapping[str, object]]] = {}
    for row in recording_reports:
        grouped.setdefault(str(row["dataset_id"]), []).append(row)

    per_dataset: dict[str, dict[str, object]] = {}
    for dataset, rows in sorted(grouped.items()):
        per_dataset[dataset] = {
            "recordings": len(rows),
            "onset": _micro_metrics([
                row["onset"] for row in rows
                if isinstance(row.get("onset"), Mapping)
            ]),
            "onset_offset": _micro_metrics([
                row["onset_offset"] for row in rows
                if isinstance(row.get("onset_offset"), Mapping)
            ]),
            "retriggers": sum(int(row.get("retriggers", 0)) for row in rows),
        }

    dataset_count = len(per_dataset)
    macro_weights = {
        dataset: 1.0 / dataset_count for dataset in per_dataset
    } if dataset_count else {}
    macro = _mean_dataset_scores(per_dataset, macro_weights)

    weighted: dict[str, object] | None = None
    if validation_dataset_fractions and per_dataset:
        configured = {
            str(dataset): max(float(value), 0.0)
            for dataset, value in validation_dataset_fractions.items()
        }
        configured_positive = {
            dataset: weight
            for dataset, weight in configured.items()
            if weight > 0.0
        }
        missing_configured = sorted(
            set(configured_positive) - set(per_dataset)
        )
        unconfigured_selected = sorted(set(per_dataset) - set(configured))
        selected_weight = sum(
            configured_positive.get(dataset, 0.0)
            for dataset in per_dataset
        )
        configured_total = sum(configured_positive.values())
        weighted = {
            "source": "train.validation_dataset_fractions",
            "available": False,
            "configured_weights": dict(sorted(configured.items())),
            # Keep the original field for report compatibility while making
            # both directions explicit.  A weighted score is only comparable
            # when the selected validation cohort covers every configured
            # dataset and contains no unconfigured one.
            "missing_selected_datasets": unconfigured_selected,
            "missing_configured_datasets": missing_configured,
            "unconfigured_selected_datasets": unconfigured_selected,
            "configured_weight_coverage": (
                selected_weight / configured_total
                if configured_total > 0.0 else 0.0
            ),
        }
        if (
            not missing_configured
            and not unconfigured_selected
            and selected_weight > 0.0
        ):
            effective = {
                dataset: configured_positive[dataset] / configured_total
                for dataset in configured_positive
            }
            weighted.update({
                "available": True,
                "effective_weights": dict(sorted(effective.items())),
                **_mean_dataset_scores(per_dataset, effective),
            })

    return {
        "aggregation": (
            "Micro counts within each dataset; macro or configured-weight "
            "mean across dataset scores."
        ),
        "per_dataset": per_dataset,
        "macro": macro,
        "weighted": weighted,
    }


def decode_probabilities(
    frame: np.ndarray,
    onset: np.ndarray,
    harmonic_amplitude: np.ndarray,
    config: PolyphonicDecoderConfig,
    sample_rate: int,
    hop_size: int,
    audio_active: np.ndarray | None = None,
    audio_onset: np.ndarray | None = None,
    independent_note: np.ndarray | None = None,
    independent_note_gate_diagnostics: dict[str, object] | None = None,
    independent_note_diagnostic_thresholds: tuple[float, ...] = (),
) -> tuple[list[NoteInterval], int]:
    decoder = PolyphonicDecoder(
        config,
        independent_note_diagnostic_thresholds=independent_note_diagnostic_thresholds,
    )
    events: list[PolyphonicMidiEvent] = []
    retriggers = 0
    if audio_active is None:
        activity = np.ones(len(frame), dtype=np.bool_)
    else:
        activity = np.asarray(audio_active, dtype=np.bool_)
        if activity.shape != (len(frame),):
            raise ValueError("audio_active must have one value per frame.")
    if audio_onset is None:
        attacks = None
    else:
        attacks = np.asarray(audio_onset, dtype=np.bool_)
        if attacks.shape != (len(frame),):
            raise ValueError("audio_onset must have one value per frame.")
    if independent_note is not None:
        independent = np.asarray(independent_note, dtype=np.float32)
        if independent.shape != frame.shape:
            raise ValueError("independent_note must match frame probabilities.")
    else:
        independent = None
    for frame_index in range(len(frame)):
        emitted = decoder.step(
            frame[frame_index], onset[frame_index],
            harmonic_amplitude[frame_index],
            independent_note_probability=(
                None if independent is None else independent[frame_index]
            ),
            audio_active=bool(activity[frame_index]),
            audio_hop_index=frame_index,
            audio_onset=(
                None if attacks is None else bool(attacks[frame_index])
            ),
            audio_onset_hop_index=(
                frame_index
                if attacks is not None and bool(attacks[frame_index])
                else None
            ),
        )
        if len(emitted) >= 2:
            retriggers += sum(
                emitted[index].kind == "note_off"
                and emitted[index + 1].kind == "note_on"
                and emitted[index].pitch == emitted[index + 1].pitch
                for index in range(len(emitted) - 1)
            )
        events.extend(emitted)
    events.extend(decoder.panic())
    if independent_note_gate_diagnostics is not None:
        independent_note_gate_diagnostics.update(
            decoder.independent_note_gate_diagnostics
        )
    return events_to_notes(
        events, sample_rate, hop_size, max(len(frame) - 1, 0)
    ), retriggers


def _aggregate_independent_note_gate(
    recording_reports: list[dict[str, object]],
) -> dict[str, object]:
    values = [
        report.get("independent_note_gate")
        for report in recording_reports
        if report.get("independent_note_gate") is not None
    ]
    if not values:
        return {"enabled": False, "recordings": 0}
    gates = [value for value in values if isinstance(value, dict)]
    eligible = sum(int(gate["eligible_candidates"]) for gate in gates)
    weighted_sum = sum(
        int(gate["eligible_candidates"])
        * float(gate["eligible_probability_mean"])
        for gate in gates
        if gate["eligible_probability_mean"] is not None
    )
    minima = [
        float(gate["eligible_probability_min"])
        for gate in gates
        if gate["eligible_probability_min"] is not None
    ]
    maxima = [
        float(gate["eligible_probability_max"])
        for gate in gates
        if gate["eligible_probability_max"] is not None
    ]
    probabilities = np.asarray([
        value
        for gate in gates
        for value in gate.get("eligible_probability_values", [])
    ], dtype=np.float64)
    thresholds = gates[0].get("diagnostic_thresholds", [])
    return {
        "enabled": bool(gates[0]["enabled"]),
        "threshold": gates[0]["threshold"],
        "recordings": len(gates),
        "eligible_candidates": eligible,
        "rejected_candidates": sum(
            int(gate["rejected_candidates"]) for gate in gates
        ),
        "eligible_probability_min": None if not minima else min(minima),
        "eligible_probability_max": None if not maxima else max(maxima),
        "eligible_probability_mean": (
            None if eligible == 0 else weighted_sum / eligible
        ),
        "probability_quantiles": (
            {} if probabilities.size == 0 else {
                name: float(np.quantile(probabilities, percentile))
                for name, percentile in (
                    ("p01", 0.01), ("p05", 0.05), ("p50", 0.50),
                    ("p95", 0.95), ("p99", 0.99),
                )
            }
        ),
        "quantile_method": "numpy.linear",
        "would_reject": {
            f"{float(threshold):.3f}": int(
                np.count_nonzero(probabilities < float(threshold))
            )
            for threshold in thresholds
        },
    }


def _low_midi_metrics(
    reference: Sequence[NoteInterval], estimated: Sequence[NoteInterval],
) -> dict[str, object]:
    """Return event and diagnostic metrics restricted to MIDI 40--51."""
    low_reference = [note for note in reference if 40 <= note.pitch <= 51]
    low_estimated = [note for note in estimated if 40 <= note.pitch <= 51]
    matches = match_notes(low_reference, low_estimated)
    return {
        "midi_min": 40,
        "midi_max": 51,
        "onset": note_metrics(low_reference, low_estimated, matches),
        "diagnostics": diagnose_note_errors(
            low_reference, low_estimated, matches,
        ),
    }


def _load_paired_decoder_configs(
    reference_path: Path,
    candidate_path: Path,
) -> tuple[PolyphonicDecoderConfig, PolyphonicDecoderConfig]:
    """Load A/B configs and reject any difference except the gate threshold."""
    reference_values = json.loads(reference_path.read_text(encoding="utf-8"))
    candidate_values = json.loads(candidate_path.read_text(encoding="utf-8"))
    if not isinstance(reference_values, dict) or not isinstance(candidate_values, dict):
        raise ValueError("Paired decoder configurations must be JSON objects.")
    differing = {
        key for key in set(reference_values) | set(candidate_values)
        if reference_values.get(key) != candidate_values.get(key)
    }
    if differing != {"independent_note_threshold"}:
        raise ValueError(
            "Paired decoder configurations must differ only in "
            "independent_note_threshold."
        )
    if reference_values.get("independent_note_threshold") is not None:
        raise ValueError("Paired reference must disable independent_note_threshold.")
    if candidate_values.get("independent_note_threshold") is None:
        raise ValueError("Paired candidate must enable independent_note_threshold.")
    return (
        PolyphonicDecoderConfig(**reference_values),
        PolyphonicDecoderConfig(**candidate_values),
    )


def evaluate_events(
    run_dir: Path,
    split: str,
    maximum_recordings: int | None = None,
    dataset_id: str | None = None,
    checkpoint_path: Path | None = None,
    thresholds_path: Path | None = None,
    decoder_config_path: Path | None = None,
    causal_gate: CausalMetricGate | None = None,
    audio_evidence_metadata: Mapping[str, object] | None = None,
    report_suffix: str | None = None,
    config_path: Path | None = None,
    allow_locked_test_after_final_selection: bool = False,
    final_selection_path: Path | None = None,
    paired_decoder_config_path: Path | None = None,
) -> dict[str, object]:
    if split == "test":
        if not allow_locked_test_after_final_selection or final_selection_path is None:
            raise PermissionError(
                "Locked test requires explicit final-selection authorization."
            )
        selection = json.loads(final_selection_path.read_text(encoding="utf-8"))
        if (
            selection.get("selected_on") != "validation_note_events"
            or selection.get("locked_test_used") is not False
        ):
            raise PermissionError("Final selection is missing or test-contaminated.")
    if report_suffix is not None and (
        not report_suffix
        or any(
            not (character.isalnum() or character in "_-")
            for character in report_suffix
        )
    ):
        raise ValueError(
            "report_suffix must contain only letters, digits, '_' or '-'."
        )
    resolved_config_path = config_path or (run_dir / "config.json")
    config_text = resolved_config_path.read_text(encoding="utf-8")
    config = (
        yaml.safe_load(config_text)
        if resolved_config_path.suffix.lower() in {".yaml", ".yml"}
        else json.loads(config_text)
    )
    if not isinstance(config, dict):
        raise ValueError("Evaluation config must be an object.")
    if config_path is not None:
        manifest = Path(str(config["dataset"]["manifest"]))
        if not manifest.is_absolute():
            # Config files live under <repo>/configs; manifests are repo-relative.
            config["dataset"]["manifest"] = str(
                (resolved_config_path.parent.parent / manifest).resolve()
            )
    thresholds = json.loads(
        (thresholds_path or (run_dir / "thresholds.json")).read_text(
            encoding="utf-8"
        )
    )
    manifest_items = load_manifest(Path(config["dataset"]["manifest"]))
    eligible_items = [
        item for item in manifest_items
        if item.split == split
        and (dataset_id is None or item.dataset_id == dataset_id)
    ]
    items = select_evaluation_recordings(
        manifest_items, split, maximum_recordings, dataset_id,
    )
    default_checkpoint = (
        run_dir / "selected.keras"
        if (run_dir / "selected.keras").is_file()
        else run_dir / "best.keras"
    )
    checkpoint = checkpoint_path or default_checkpoint
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    model = load_polyphonic_checkpoint(checkpoint)
    inference_outputs = {
        "frame": model.get_layer("frame").output,
        "onset": model.get_layer("onset").output,
        "harmonic_amplitude": model.get_layer("harmonic_amplitude").output,
    }
    if "independent_note" in {layer.name for layer in model.layers}:
        inference_outputs["independent_note"] = (
            model.get_layer("independent_note").output
        )
    inference_model = tf.keras.Model(model.inputs, inference_outputs)
    frame_threshold = float(thresholds["frame"])
    onset_threshold = float(thresholds["onset"])
    configured_decoder = decoder_config_path or (run_dir / "decoder_config.json")
    if configured_decoder.is_file():
        decoder_config = PolyphonicDecoderConfig(**json.loads(
            configured_decoder.read_text(encoding="utf-8")
        ))
    else:
        decoder_config = default_decoder_config(
            frame_threshold, onset_threshold,
        )
    paired_candidate_config: PolyphonicDecoderConfig | None = None
    if paired_decoder_config_path is not None:
        if not configured_decoder.is_file():
            raise ValueError("Paired evaluation requires a reference decoder config.")
        decoder_config, paired_candidate_config = _load_paired_decoder_configs(
            configured_decoder, paired_decoder_config_path,
        )
    all_reference: list[NoteInterval] = []
    all_estimated: list[NoteInterval] = []
    causal_clips: list[ClipNoteOnData] = []
    causal_recall_deadlines_ms = (
        tuple(DEFAULT_RECALL_DEADLINES_MS)
        + (
            causal_gate.required_deadlines_ms()
            if causal_gate is not None
            else ()
        )
    )
    recording_reports: list[dict[str, object]] = []
    total_retriggers = 0
    paired_reference: list[NoteInterval] = []
    paired_estimated: list[NoteInterval] = []
    paired_reports: list[dict[str, object]] = []
    paired_retriggers = 0
    for recording_index, item in enumerate(items):
        corpus = PolyphonicCorpus([item])
        arrays = corpus.labels[0].arrays
        refs = np.column_stack((
            np.zeros(len(arrays["active_bits"]), dtype=np.int32),
            np.arange(len(arrays["active_bits"]), dtype=np.int32),
        ))
        sequence = PolyphonicSequence(
            corpus,
            batch_size=int(config["train"]["batch_size"]),
            input_samples=int(config["dataset"]["input_samples"]),
            normalization_gain=float(config["dataset"]["normalization_gain"]),
            seed=0,
            refs=refs,
            shuffle=False,
        )
        try:
            prediction = predict_compat(
                inference_model, sequence, verbose=0, workers=1
            )
            audio = corpus.audio(0)
            audio_duration_s = _audio_duration_s(audio, corpus.sample_rate)
            activity_mask, onset_mask, audio_evidence_report = (
                offline_audio_evidence_masks(
                audio, corpus.sample_rate, corpus.hop_size,
                frame_count=len(prediction["frame"]),
                metadata=audio_evidence_metadata,
                )
            )
            independent_note_gate: dict[str, object] = {}
            estimated, retriggers = decode_probabilities(
                prediction["frame"], prediction["onset"],
                prediction["harmonic_amplitude"], decoder_config,
                corpus.sample_rate, corpus.hop_size,
                activity_mask,
                onset_mask,
                prediction.get("independent_note"),
                independent_note_gate,
                (
                    INDEPENDENT_NOTE_DIAGNOSTIC_THRESHOLDS
                    if split == "validation" else ()
                ),
            )
            reference = truth_notes(arrays)
            if paired_candidate_config is not None:
                candidate_gate: dict[str, object] = {}
                candidate_estimated, candidate_retriggers = decode_probabilities(
                    prediction["frame"], prediction["onset"],
                    prediction["harmonic_amplitude"], paired_candidate_config,
                    corpus.sample_rate, corpus.hop_size, activity_mask, onset_mask,
                    prediction.get("independent_note"), candidate_gate,
                )
        finally:
            corpus.close()
        onset_matches = match_notes(reference, estimated)
        offset_matches = match_notes(reference, estimated, require_offset=True)
        causal_clip, causal_metrics = build_strictly_causal_noteon_clip(
            reference,
            estimated,
            clip_id=(
                f"{item.source_id}::{item.capture_id}::"
                f"{recording_index:04d}"
            ),
            corpus_id=str(item.dataset_id),
            duration_s=audio_duration_s,
            recall_deadlines_ms=causal_recall_deadlines_ms,
        )
        causal_clips.append(causal_clip)
        total_retriggers += retriggers
        recording_reports.append({
            "source_id": item.source_id,
            "dataset_id": item.dataset_id,
            "group_id": item.group_id,
            "capture_id": item.capture_id,
            "duration_s": audio_duration_s,
            "onset": note_metrics(reference, estimated, onset_matches),
            "onset_offset": note_metrics(reference, estimated, offset_matches),
            "strictly_causal_noteon": causal_metrics,
            "retriggers": retriggers,
            "audio_evidence": audio_evidence_report,
            "independent_note_gate": independent_note_gate,
            "diagnostics": diagnose_note_errors(
                reference, estimated, onset_matches,
            ),
        })
        if paired_candidate_config is not None:
            candidate_matches = match_notes(reference, candidate_estimated)
            paired_retriggers += candidate_retriggers
            paired_reports.append({
                "source_id": item.source_id,
                "dataset_id": item.dataset_id,
                "group_id": item.group_id,
                "capture_id": item.capture_id,
                "duration_s": audio_duration_s,
                "onset": note_metrics(reference, candidate_estimated, candidate_matches),
                "retriggers": candidate_retriggers,
                "diagnostics": diagnose_note_errors(
                    reference, candidate_estimated, candidate_matches,
                ),
            })
        # Offset each recording in time so aggregate matching cannot cross files.
        shift = 1.0 + max(
            [note.end_s for note in all_reference + all_estimated] or [0.0]
        )
        all_reference.extend(NoteInterval(
            note.pitch, note.start_s + shift, note.end_s + shift
        ) for note in reference)
        all_estimated.extend(NoteInterval(
            note.pitch, note.start_s + shift, note.end_s + shift
        ) for note in estimated)
        if paired_candidate_config is not None:
            paired_reference.extend(NoteInterval(
                note.pitch, note.start_s + shift, note.end_s + shift
            ) for note in reference)
            paired_estimated.extend(NoteInterval(
                note.pitch, note.start_s + shift, note.end_s + shift
            ) for note in candidate_estimated)

    onset_matches = match_notes(all_reference, all_estimated)
    offset_matches = match_notes(all_reference, all_estimated, require_offset=True)
    validation_fractions = config.get("train", {}).get(
        "validation_dataset_fractions"
    )
    dataset_metrics = aggregate_dataset_note_metrics(
        recording_reports, validation_fractions,
    )
    causal_noteon_metrics = aggregate_strictly_causal_noteon_metrics(
        causal_clips, gate=causal_gate
    )
    independent_note_gate = _aggregate_independent_note_gate(recording_reports)
    for recording in recording_reports:
        gate = recording.get("independent_note_gate")
        if isinstance(gate, dict):
            gate.pop("eligible_probability_values", None)
    report = {
        "run_dir": str(run_dir),
        "checkpoint": str(checkpoint),
        "split": split,
        "locked_test_used": split == "test",
        "dataset_id": dataset_id,
        "recordings": len(items),
        "selection": _selection_report(
            eligible_items, items, maximum_recordings,
        ),
        "decoder": asdict(decoder_config),
        "latency": {
            "hop_ms": 1000.0 * 256 / 44_100,
            "direct_onset_added_hops": 0,
            "frame_fallback_added_hops": decoder_config.activation_frames - 1,
            "release_added_hops": decoder_config.release_frames,
        },
        "onset": note_metrics(all_reference, all_estimated, onset_matches),
        "onset_offset": note_metrics(all_reference, all_estimated, offset_matches),
        "dataset_metrics": dataset_metrics,
        "strictly_causal_noteon": causal_noteon_metrics,
        "retriggers": total_retriggers,
        "independent_note_gate": independent_note_gate,
        "audio_evidence_policy": (
            "shared_live_audio_evidence_with_synthetic_silence_priming"
        ),
        "audio_evidence_metadata": dict(audio_evidence_metadata or {}),
        "audio_evidence_label_leakage": False,
        "diagnostics": diagnose_note_errors(
            all_reference, all_estimated, onset_matches,
        ),
        "per_recording": recording_reports,
    }
    if paired_candidate_config is not None:
        candidate_matches = match_notes(paired_reference, paired_estimated)
        candidate_onset = note_metrics(
            paired_reference, paired_estimated, candidate_matches,
        )
        candidate_diagnostics = diagnose_note_errors(
            paired_reference, paired_estimated, candidate_matches,
        )
        reference_low = _low_midi_metrics(all_reference, all_estimated)
        candidate_low = _low_midi_metrics(paired_reference, paired_estimated)
        report["paired_ab"] = {
            "single_inference_per_recording": True,
            "reference_config": str(configured_decoder),
            "candidate_config": str(paired_decoder_config_path),
            "reference_config_sha256": _sha256_file(configured_decoder),
            "candidate_config_sha256": _sha256_file(paired_decoder_config_path),
            "reference": {
                "onset": report["onset"],
                "dataset_metrics": report["dataset_metrics"],
                "retriggers": report["retriggers"],
                "diagnostics": report["diagnostics"],
                "low_midi_40_51": reference_low,
            },
            "candidate": {
                "onset": candidate_onset,
                "dataset_metrics": aggregate_dataset_note_metrics(
                    paired_reports, validation_fractions,
                ),
                "retriggers": paired_retriggers,
                "diagnostics": candidate_diagnostics,
                "low_midi_40_51": candidate_low,
            },
            "delta_candidate_minus_reference": {
                "false_positive_notes": (
                    candidate_onset["false_positive_notes"]
                    - report["onset"]["false_positive_notes"]
                ),
                "matched_notes": candidate_onset["matched_notes"] - report["onset"]["matched_notes"],
                "missing_notes": candidate_onset["missing_notes"] - report["onset"]["missing_notes"],
                "f1": candidate_onset["f1"] - report["onset"]["f1"],
            },
        }
    reports_root = run_dir / "reports"
    reports_root.mkdir(exist_ok=True)
    checkpoint_suffix = (
        f"_{checkpoint.stem}" if checkpoint_path is not None else ""
    )
    variant_suffix = f"_{report_suffix}" if report_suffix else ""
    report_name = (
        f"{split}_{dataset_id}_events{checkpoint_suffix}{variant_suffix}.json"
        if dataset_id
        else f"{split}_events{checkpoint_suffix}{variant_suffix}.json"
    )
    (reports_root / report_name).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test"), required=True)
    parser.add_argument(
        "--allow-locked-test-after-final-selection",
        action="store_true",
        help="Autorisation explicite requise pour le split test verrouillé.",
    )
    parser.add_argument(
        "--final-selection",
        type=Path,
        help="selection.json validation-only requis avec le drapeau test.",
    )
    parser.add_argument("--maximum-recordings", type=int)
    parser.add_argument("--dataset-id")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument(
        "--config",
        type=Path,
        help="Configuration JSON/YAML explicite, indépendante du run-dir.",
    )
    parser.add_argument("--thresholds", type=Path)
    parser.add_argument("--decoder-config", type=Path)
    parser.add_argument(
        "--paired-decoder-config",
        type=Path,
        help="Configuration candidat A/B ; seule la porte note indépendante peut différer.",
    )
    parser.add_argument(
        "--audio-evidence-config",
        type=Path,
        help=(
            "JSON contenant uniquement les paramètres audio_evidence "
            "à tester sur le split demandé."
        ),
    )
    parser.add_argument(
        "--report-suffix",
        help="Suffixe sûr ajouté au rapport pour éviter tout écrasement.",
    )
    parser.add_argument(
        "--causal-gate",
        type=Path,
        help=(
            "JSON des seuils de promotion CausalMetricGate. Le rapport "
            "échoue explicitement chaque seuil non satisfait."
        ),
    )
    args = parser.parse_args()
    causal_gate = (
        CausalMetricGate(**json.loads(
            args.causal_gate.read_text(encoding="utf-8")
        ))
        if args.causal_gate is not None
        else None
    )
    if (
        causal_gate is not None
        and causal_gate.configured_check_count() == 0
    ):
        parser.error("--causal-gate doit contenir au moins un seuil.")
    audio_evidence_metadata = None
    if args.audio_evidence_config is not None:
        audio_evidence_values = json.loads(
            args.audio_evidence_config.read_text(encoding="utf-8")
        )
        if not isinstance(audio_evidence_values, dict):
            parser.error("--audio-evidence-config doit contenir un objet JSON.")
        audio_evidence_metadata = {
            "audio_evidence": audio_evidence_values,
        }
    report = evaluate_events(
        args.run_dir, args.split, args.maximum_recordings, args.dataset_id,
        args.checkpoint, args.thresholds, args.decoder_config,
        causal_gate, audio_evidence_metadata, args.report_suffix, args.config,
        args.allow_locked_test_after_final_selection, args.final_selection,
        args.paired_decoder_config,
    )
    print(json.dumps({
        "split": report["split"],
        "locked_test_used": report["locked_test_used"],
        "onset": report["onset"],
        "retriggers": report["retriggers"],
        "independent_note_gate": report["independent_note_gate"],
    }, indent=2))


if __name__ == "__main__":
    main()
