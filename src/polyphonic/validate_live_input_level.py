"""Validation-only A/B test of the causal desktop input leveler."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from dataclasses import asdict
from pathlib import Path
from typing import Any

import numpy as np
import tensorflow as tf

from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.audio_evidence import offline_audio_evidence_masks
from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    load_manifest,
)
from src.polyphonic.decoder import PolyphonicDecoderConfig
from src.polyphonic.evaluate_events import (
    NoteInterval,
    _selection_report,
    aggregate_dataset_note_metrics,
    decode_probabilities,
    match_notes,
    note_metrics,
    select_evaluation_recordings,
    truth_notes,
)
from src.polyphonic.event_diagnostics import diagnose_note_errors
from src.polyphonic.input_level import offline_model_input_level_gains
from src.polyphonic.tflite_runtime import (
    PolyphonicBundle,
    TFLitePolyphonicModel,
)


OUTPUT_NAMES = ("frame", "onset", "harmonic_amplitude")


def _capture_scaled_waveform(
    waveform: np.ndarray,
    gain_db: float,
) -> tuple[np.ndarray, float]:
    """Normalize capture audio and apply a fixed weak-input attenuation.

    The attenuation is applied before both audio evidence and model input.
    Positive gain is deliberately rejected: this validation experiment tests
    robustness to a quiet interface rather than tuning boost from labels.
    """
    if not np.isfinite(gain_db):
        raise ValueError("capture_gain_db must be finite")
    if gain_db > 0.0:
        raise ValueError("capture_gain_db must be zero or negative")
    source = np.asarray(waveform).reshape(-1)
    normalized = np.asarray(source, dtype=np.float32)
    if np.issubdtype(source.dtype, np.integer):
        normalized /= float(max(abs(np.iinfo(source.dtype).min), 1))
    scale = float(10.0 ** (float(gain_db) / 20.0))
    return normalized * scale, scale


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _shifted(
    notes: list[NoteInterval],
    shift_s: float,
) -> list[NoteInterval]:
    return [
        NoteInterval(
            note.pitch,
            note.start_s + shift_s,
            note.end_s + shift_s,
        )
        for note in notes
    ]


def _evaluate_notes(
    onset_reference: list[NoteInterval],
    onset_estimated: list[NoteInterval],
    offset_reference: list[NoteInterval] | None = None,
    offset_estimated: list[NoteInterval] | None = None,
) -> dict[str, Any]:
    if offset_reference is None:
        offset_reference = onset_reference
    if offset_estimated is None:
        offset_estimated = onset_estimated
    onset_matches = match_notes(onset_reference, onset_estimated)
    offset_matches = match_notes(
        offset_reference,
        offset_estimated,
        require_offset=True,
    )
    return {
        "onset": note_metrics(
            onset_reference,
            onset_estimated,
            onset_matches,
        ),
        "onset_offset": note_metrics(
            offset_reference,
            offset_estimated,
            offset_matches,
        ),
        "diagnostics": diagnose_note_errors(
            onset_reference,
            onset_estimated,
            onset_matches,
        ),
    }


def _frame_for_time(
    time_s: float,
    sample_rate: int,
    hop_size: int,
    frame_count: int,
) -> int:
    sample = max(0, int(round(float(time_s) * sample_rate)))
    frame = max(0, int(np.ceil(sample / float(hop_size))) - 1)
    return min(frame, max(frame_count - 1, 0))


def _valid_note_views(
    reference: list[NoteInterval],
    estimated: list[NoteInterval],
    valid_frames: np.ndarray,
    sample_rate: int,
    hop_size: int,
) -> tuple[
    list[NoteInterval],
    list[NoteInterval],
    list[NoteInterval],
    list[NoteInterval],
    dict[str, int],
]:
    valid = np.asarray(valid_frames, dtype=np.bool_).reshape(-1)
    if len(valid) == 0:
        return [], [], [], [], {
            "invalid_reference_onsets": len(reference),
            "invalid_reference_offsets": len(reference),
            "invalid_estimated_onsets": len(estimated),
            "invalid_estimated_offsets": len(estimated),
        }

    def onset_valid(note: NoteInterval) -> bool:
        return bool(valid[_frame_for_time(
            note.start_s, sample_rate, hop_size, len(valid)
        )])

    def offset_valid(note: NoteInterval) -> bool:
        return bool(valid[_frame_for_time(
            note.end_s, sample_rate, hop_size, len(valid)
        )])

    onset_reference = [note for note in reference if onset_valid(note)]
    onset_estimated = [note for note in estimated if onset_valid(note)]
    offset_reference = [
        note for note in onset_reference if offset_valid(note)
    ]
    offset_estimated = [
        note for note in onset_estimated if offset_valid(note)
    ]
    return (
        onset_reference,
        onset_estimated,
        offset_reference,
        offset_estimated,
        {
            "invalid_reference_onsets": (
                len(reference) - len(onset_reference)
            ),
            "invalid_reference_offsets": (
                len(onset_reference) - len(offset_reference)
            ),
            "invalid_estimated_onsets": (
                len(estimated) - len(onset_estimated)
            ),
            "invalid_estimated_offsets": (
                len(onset_estimated) - len(offset_estimated)
            ),
        },
    )


def _delta(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, float | int]:
    result: dict[str, float | int] = {}
    for metric in (
        "estimated_notes",
        "matched_notes",
        "false_positive_notes",
        "missing_notes",
        "precision",
        "recall",
        "f1",
    ):
        result[metric] = candidate[metric] - baseline[metric]
    return result


def _diagnostic_delta(
    candidate: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    count_keys = (
        "false_positive_notes",
        "missing_notes",
        "false_positive_without_active_reference",
        "same_pitch_during_reference",
        "harmonic_interval_false_positives",
        "fragmented_reference_notes",
        "excess_fragments",
        "maximum_fragments_for_one_reference",
    )
    timing_keys = (
        "matched_onset_timing",
        "matched_offset_timing",
    )
    candidate_intervals = candidate["false_positive_interval_counts"]
    baseline_intervals = baseline["false_positive_interval_counts"]
    intervals = sorted(
        set(candidate_intervals) | set(baseline_intervals),
        key=int,
    )
    return {
        **{
            key: int(candidate[key]) - int(baseline[key])
            for key in count_keys
        },
        **{
            key: {
                metric: (
                    float(candidate[key][metric])
                    - float(baseline[key][metric])
                )
                for metric in ("median_ms", "p95_absolute_ms")
            }
            for key in timing_keys
        },
        "false_positive_interval_counts": {
            interval: (
                int(candidate_intervals.get(interval, 0))
                - int(baseline_intervals.get(interval, 0))
            )
            for interval in intervals
        },
    }


def validate(
    run_dir: Path,
    decoder_config_path: Path,
    maximum_recordings: int,
    output_path: Path | None = None,
    *,
    runtime_kind: str = "keras",
    artifacts: Path | None = None,
    minimum_gain_db: float = -12.0,
    capture_gain_db: float = 0.0,
) -> dict[str, Any]:
    """Compare baseline versus auto-level on validation; test is unavailable."""
    if maximum_recordings < 1:
        raise ValueError("maximum_recordings must be positive")
    if not np.isfinite(minimum_gain_db):
        raise ValueError("minimum_gain_db must be finite")
    if not np.isfinite(capture_gain_db) or capture_gain_db > 0.0:
        raise ValueError("capture_gain_db must be finite and zero or negative")
    run_dir = run_dir.resolve()
    config = json.loads(
        (run_dir / "config.json").read_text(encoding="utf-8")
    )
    checkpoint = run_dir / "selected.keras"
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    if runtime_kind not in {"keras", "tflite"}:
        raise ValueError("runtime_kind must be keras or tflite")
    decoder_config_path = decoder_config_path.resolve()
    decoder_config = PolyphonicDecoderConfig(**json.loads(
        decoder_config_path.read_text(encoding="utf-8")
    ))
    manifest_items = load_manifest(Path(config["dataset"]["manifest"]))
    eligible = [item for item in manifest_items if item.split == "validation"]
    items = select_evaluation_recordings(
        manifest_items,
        "validation",
        maximum_recordings,
    )
    inference_model = None
    runtime = None
    bundle = None
    if runtime_kind == "keras":
        model = tf.keras.models.load_model(checkpoint, compile=False)
        inference_model = tf.keras.Model(
            model.inputs,
            {
                name: model.get_layer(name).output
                for name in OUTPUT_NAMES
            },
        )
    else:
        if artifacts is None:
            raise ValueError("artifacts are required for TFLite validation")
        bundle = PolyphonicBundle(artifacts)
        if int(bundle.metadata["max_window_samples"]) != int(
            config["dataset"]["input_samples"]
        ):
            raise ValueError(
                "TFLite bundle input window does not match the run."
            )
        if not np.isclose(
            float(bundle.metadata["normalization_gain"]),
            float(config["dataset"]["normalization_gain"]),
            atol=1e-9,
        ):
            raise ValueError(
                "TFLite bundle normalization does not match the run."
            )
        runtime = TFLitePolyphonicModel(bundle)
    normalization_gain = float(config["dataset"]["normalization_gain"])
    input_samples = int(config["dataset"]["input_samples"])
    batch_size = int(config["train"]["batch_size"])
    modes = ("baseline", "automatic_input_level")
    per_mode_rows: dict[str, list[dict[str, Any]]] = {
        mode: [] for mode in modes
    }
    all_onset_reference: list[NoteInterval] = []
    all_offset_reference: list[NoteInterval] = []
    all_onset_estimated: dict[str, list[NoteInterval]] = {
        mode: [] for mode in modes
    }
    all_offset_estimated: dict[str, list[NoteInterval]] = {
        mode: [] for mode in modes
    }
    per_recording: list[dict[str, Any]] = []
    shift_s = 0.0
    inference_batch_ms: list[float] = []

    for item_index, item in enumerate(items):
        corpus = PolyphonicCorpus([item])
        if bundle is not None and (
            int(bundle.metadata["sample_rate"]) != corpus.sample_rate
            or int(bundle.metadata["hop_samples"]) != corpus.hop_size
        ):
            corpus.close()
            raise ValueError(
                "TFLite bundle sample rate/hop do not match the corpus."
            )
        arrays = corpus.labels[0].arrays
        refs = np.column_stack((
            np.zeros(len(arrays["active_bits"]), dtype=np.int32),
            np.arange(len(arrays["active_bits"]), dtype=np.int32),
        ))
        try:
            waveform = corpus.audio(0)
            capture_waveform, capture_scale = _capture_scaled_waveform(
                waveform,
                capture_gain_db,
            )
            activity, audio_onset, evidence_report = (
                offline_audio_evidence_masks(
                    capture_waveform,
                    corpus.sample_rate,
                    corpus.hop_size,
                    frame_count=len(refs),
                )
            )
            level_gains, level_report = offline_model_input_level_gains(
                capture_waveform,
                activity,
                corpus.sample_rate,
                corpus.hop_size,
                normalization_gain,
                input_samples=input_samples,
                minimum_gain_db=minimum_gain_db,
            )
            baseline_sequence = PolyphonicSequence(
                corpus,
                batch_size=batch_size,
                input_samples=input_samples,
                normalization_gain=(
                    normalization_gain
                    if runtime_kind == "keras" else 1.0
                ),
                seed=0,
                refs=refs,
                input_gain_by_frame=(
                    None
                    if capture_scale == 1.0
                    else [
                        np.full(
                            len(refs),
                            capture_scale,
                            dtype=np.float32,
                        )
                    ]
                ),
                full_context_from_start=True,
                shuffle=False,
            )
            leveled_sequence = PolyphonicSequence(
                corpus,
                batch_size=batch_size,
                input_samples=input_samples,
                normalization_gain=(
                    normalization_gain
                    if runtime_kind == "keras" else 1.0
                ),
                seed=0,
                refs=refs,
                input_gain_by_frame=[
                    level_gains * capture_scale
                ],
                full_context_from_start=True,
                shuffle=False,
            )
            parts: dict[str, dict[str, list[np.ndarray]]] = {
                mode: {name: [] for name in OUTPUT_NAMES}
                for mode in modes
            }
            for batch_index in range(len(baseline_sequence)):
                baseline_inputs, _ = baseline_sequence[batch_index]
                leveled_inputs, _ = leveled_sequence[batch_index]
                if runtime_kind == "keras":
                    baseline_rows = len(baseline_inputs["audio"])
                    combined_inputs = {
                        name: np.concatenate(
                            (baseline_inputs[name], leveled_inputs[name]),
                            axis=0,
                        )
                        for name in ("audio", "time_mask")
                    }
                    started = time.perf_counter()
                    raw = inference_model(
                        combined_inputs,
                        training=False,
                    )
                    inference_batch_ms.append(
                        (time.perf_counter() - started) * 1000.0
                    )
                    for name in OUTPUT_NAMES:
                        values = np.asarray(
                            raw[name],
                            dtype=np.float32,
                        )
                        parts["baseline"][name].append(
                            values[:baseline_rows]
                        )
                        parts["automatic_input_level"][name].append(
                            values[baseline_rows:]
                        )
                else:
                    for mode, inputs in (
                        ("baseline", baseline_inputs),
                        ("automatic_input_level", leveled_inputs),
                    ):
                        for row in range(len(inputs["audio"])):
                            prediction = runtime.infer(
                                inputs["audio"][row, :, 0],
                                input_samples,
                            )
                            inference_batch_ms.append(
                                prediction.inference_ms
                            )
                            parts[mode]["frame"].append(
                                prediction.frame_probability[None, :]
                            )
                            parts[mode]["onset"].append(
                                prediction.onset_probability[None, :]
                            )
                            parts[mode][
                                "harmonic_amplitude"
                            ].append(
                                prediction.harmonic_amplitude[None, :]
                            )
            predictions = {
                mode: {
                    name: np.concatenate(parts[mode][name], axis=0)
                    for name in OUTPUT_NAMES
                }
                for mode in modes
            }
            reference = truth_notes(arrays)
            recording_modes: dict[str, Any] = {}
            for mode in modes:
                estimated, retriggers = decode_probabilities(
                    predictions[mode]["frame"],
                    predictions[mode]["onset"],
                    predictions[mode]["harmonic_amplitude"],
                    decoder_config,
                    corpus.sample_rate,
                    corpus.hop_size,
                    activity,
                    audio_onset,
                )
                (
                    onset_reference,
                    onset_estimated,
                    offset_reference,
                    offset_estimated,
                    validity,
                ) = _valid_note_views(
                    reference,
                    estimated,
                    arrays["valid"],
                    corpus.sample_rate,
                    corpus.hop_size,
                )
                metrics = _evaluate_notes(
                    onset_reference,
                    onset_estimated,
                    offset_reference,
                    offset_estimated,
                )
                row = {
                    "source_id": item.source_id,
                    "dataset_id": item.dataset_id,
                    "group_id": item.group_id,
                    "capture_id": item.capture_id,
                    "onset": metrics["onset"],
                    "onset_offset": metrics["onset_offset"],
                    "retriggers": retriggers,
                    "diagnostics": metrics["diagnostics"],
                    "validity": validity,
                }
                per_mode_rows[mode].append(row)
                recording_modes[mode] = row
                all_onset_estimated[mode].extend(
                    _shifted(onset_estimated, shift_s)
                )
                all_offset_estimated[mode].extend(
                    _shifted(offset_estimated, shift_s)
                )
            all_onset_reference.extend(
                _shifted(onset_reference, shift_s)
            )
            all_offset_reference.extend(
                _shifted(offset_reference, shift_s)
            )
            duration_s = len(refs) * corpus.hop_size / corpus.sample_rate
            shift_s += duration_s + 1.0
        finally:
            corpus.close()

        per_recording.append({
            "source_id": item.source_id,
            "dataset_id": item.dataset_id,
            "group_id": item.group_id,
            "capture_id": item.capture_id,
            "audio_evidence": evidence_report,
            "automatic_input_level": level_report,
            "modes": recording_modes,
            "automatic_minus_baseline": {
                "onset": _delta(
                    recording_modes["automatic_input_level"]["onset"],
                    recording_modes["baseline"]["onset"],
                ),
                "onset_offset": _delta(
                    recording_modes["automatic_input_level"]["onset_offset"],
                    recording_modes["baseline"]["onset_offset"],
                ),
                "diagnostics": _diagnostic_delta(
                    recording_modes[
                        "automatic_input_level"
                    ]["diagnostics"],
                    recording_modes["baseline"]["diagnostics"],
                ),
            },
        })
        print(
            f"recording {item_index + 1}/{len(items)} "
            f"{item.dataset_id} {item.source_id}",
            flush=True,
        )

    aggregate: dict[str, Any] = {}
    validation_fractions = config["train"].get(
        "validation_dataset_fractions"
    )
    for mode in modes:
        metrics = _evaluate_notes(
            all_onset_reference,
            all_onset_estimated[mode],
            all_offset_reference,
            all_offset_estimated[mode],
        )
        aggregate[mode] = {
            **metrics,
            "dataset_metrics": aggregate_dataset_note_metrics(
                per_mode_rows[mode],
                validation_fractions,
            ),
            "retriggers": sum(
                int(row["retriggers"]) for row in per_mode_rows[mode]
            ),
        }
    report = {
        "purpose": (
            "Validation-only A/B of the causal model-input leveler; "
            "this report selects preprocessing policy, never model weights "
            "or test-set parameters."
        ),
        "split": "validation",
        "locked_test_used": False,
        "run_dir": str(run_dir),
        "checkpoint": str(checkpoint),
        "runtime_kind": runtime_kind,
        "capture_input": {
            "gain_db": float(capture_gain_db),
            "linear_gain": float(10.0 ** (capture_gain_db / 20.0)),
            "policy": (
                "unaltered_validation_capture"
                if capture_gain_db == 0.0
                else "fixed_validation_only_weak_input_simulation"
            ),
            "applied_before_audio_evidence_and_model": True,
            "label_leakage": False,
        },
        "automatic_input_level_candidate": {
            "minimum_gain_db": float(minimum_gain_db),
            "session_policy": (
                "amplification_only"
                if minimum_gain_db == 0.0
                else "bidirectional"
            ),
            "safety_attenuation_remains_enabled": True,
        },
        "artifacts": (
            None if artifacts is None else str(artifacts.resolve())
        ),
        "decoder_config_path": str(decoder_config_path),
        "decoder": asdict(decoder_config),
        "decoder_runtime_policy": {
            "unattacked_frame_threshold_enforced": True,
            "unattacked_frame_threshold": (
                decoder_config.unattacked_frame_threshold
            ),
            "recent_physical_attack_uses_frame_on_threshold": True,
            "pitch_specific_model_onset_remains_available": True,
        },
        "fingerprints": {
            "checkpoint_sha256": _sha256(checkpoint),
            "decoder_config_sha256": _sha256(decoder_config_path),
            "tflite_sha256": (
                None
                if bundle is None
                else _sha256(bundle.model_path)
            ),
        },
        "selection": _selection_report(
            eligible,
            items,
            maximum_recordings,
        ),
        "recordings": len(items),
        "aggregate": aggregate,
        "automatic_minus_baseline": {
            "onset": _delta(
                aggregate["automatic_input_level"]["onset"],
                aggregate["baseline"]["onset"],
            ),
            "onset_offset": _delta(
                aggregate["automatic_input_level"]["onset_offset"],
                aggregate["baseline"]["onset_offset"],
            ),
            "retriggers": (
                aggregate["automatic_input_level"]["retriggers"]
                - aggregate["baseline"]["retriggers"]
            ),
            "diagnostics": _diagnostic_delta(
                aggregate["automatic_input_level"]["diagnostics"],
                aggregate["baseline"]["diagnostics"],
            ),
        },
        "inference": {
            "meaning": (
                "Keras FP32 batched evaluation throughput, not live latency."
                if runtime_kind == "keras"
                else "Exact deployed TFLite float16 batch-1 inference latency."
            ),
            "measurement_unit": (
                "combined_keras_batch"
                if runtime_kind == "keras"
                else "single_tflite_inference"
            ),
            "measurements": len(inference_batch_ms),
            "combined_baseline_and_automatic_batches": len(
                inference_batch_ms
            ),
            "batch_ms_mean": float(np.mean(inference_batch_ms)),
            "batch_ms_p95": float(np.percentile(
                inference_batch_ms, 95
            )),
            "batch_ms_max": float(np.max(inference_batch_ms)),
        },
        "per_recording": per_recording,
    }
    output = (
        output_path.resolve()
        if output_path is not None
        else (
            run_dir
            / "reports"
            / (
                "validation_live_input_level_v2_2_1"
                f"_{runtime_kind}.json"
            )
        )
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    report["output"] = str(output)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument(
        "--decoder-config",
        type=Path,
        default=Path("configs/polyphonic_live_decoder_v2_2_1.json"),
    )
    parser.add_argument("--maximum-recordings", type=int, default=12)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--runtime",
        choices=("keras", "tflite"),
        default="keras",
    )
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=Path("artifacts/guitar_midi_polyphonic_v2_2_0"),
    )
    parser.add_argument(
        "--minimum-gain-db",
        type=float,
        default=-12.0,
        help=(
            "Minimum persistent session gain. Use 0 for the controlled "
            "amplification-only candidate; window safety may still attenuate."
        ),
    )
    parser.add_argument(
        "--capture-gain-db",
        type=float,
        default=0.0,
        help=(
            "Validation-only fixed input attenuation applied before the "
            "audio gate and model; must be <= 0 dB."
        ),
    )
    args = parser.parse_args()
    report = validate(
        args.run_dir,
        args.decoder_config,
        args.maximum_recordings,
        args.output,
        runtime_kind=args.runtime,
        artifacts=(args.artifacts if args.runtime == "tflite" else None),
        minimum_gain_db=args.minimum_gain_db,
        capture_gain_db=args.capture_gain_db,
    )
    summary = {
        "output": report["output"],
        "recordings": report["recordings"],
        "baseline_onset": report["aggregate"]["baseline"]["onset"],
        "automatic_onset": report["aggregate"][
            "automatic_input_level"
        ]["onset"],
        "automatic_minus_baseline": report[
            "automatic_minus_baseline"
        ],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
