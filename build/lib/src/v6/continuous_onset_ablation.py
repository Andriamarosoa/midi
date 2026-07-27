from __future__ import annotations

import argparse
import csv
import json
import math
import time
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from src.v5.external_data import (
    NoteEvent,
    causal_window,
    discover_guitarset,
    parse_recording_notes,
    read_recording_audio,
)
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401

from .continuous_validate import (
    _benchmark_batch_one,
    _classified_event_rows,
    decode_events,
    frame_labels,
    progressive_windows,
    stabilize_predictions,
)
from .evaluate import average_precision, binary_metrics


def strongest_harmonic_explains(
    current_pitch: int,
    candidate_pitch: int,
    harmonic_amplitude: np.ndarray,
) -> bool:
    """Conservative, threshold-free test using only the strongest overtone."""
    amplitudes = np.asarray(harmonic_amplitude, dtype=np.float32).reshape(-1)
    if candidate_pitch <= current_pitch or len(amplitudes) < 2:
        return False
    harmonic_number = int(np.argmax(amplitudes[1:])) + 2
    interval = int(round(12.0 * math.log2(harmonic_number)))
    return candidate_pitch - current_pitch == interval


def stabilize_with_model_onset(
    predicted_active: np.ndarray,
    predicted_pitch: np.ndarray,
    onset_probability: np.ndarray,
    onset_threshold: float,
    hop_ms: float,
    harmonic_amplitude: np.ndarray | None = None,
    retrigger_onset: np.ndarray | None = None,
    required_frames: int = 2,
    minimum_retrigger_ms: float = 80.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Gate active-to-active pitch changes with causal learned onset evidence."""
    if required_frames < 1:
        raise ValueError("required_frames doit etre positif.")
    active = np.asarray(predicted_active, dtype=bool)
    pitch = np.asarray(predicted_pitch, dtype=np.int32)
    onset = np.asarray(onset_probability, dtype=np.float32).reshape(-1)
    if not (len(active) == len(pitch) == len(onset)):
        raise ValueError("Longueurs incoherentes pour le decodeur onset.")
    harmonic = None
    if harmonic_amplitude is not None:
        harmonic = np.asarray(harmonic_amplitude, dtype=np.float32)
        if harmonic.ndim != 2 or len(harmonic) != len(active):
            raise ValueError("Shape harmonic_amplitude incoherente.")
    retrigger_evidence = onset >= float(onset_threshold)
    if retrigger_onset is not None:
        retrigger_evidence = np.asarray(retrigger_onset, dtype=bool).reshape(-1)
        if len(retrigger_evidence) != len(active):
            raise ValueError("Longueur retrigger_onset incoherente.")

    output_active = np.zeros(len(active), dtype=bool)
    output_pitch = np.full(len(active), -1, dtype=np.int32)
    retrigger = np.zeros(len(active), dtype=bool)
    harmonic_veto = np.zeros(len(active), dtype=bool)
    current = -1
    pending = -2
    pending_count = 0
    pending_has_onset = False
    pending_harmonic_veto = False
    last_note_on = -10**9
    minimum_retrigger_frames = max(
        1, int(math.ceil(minimum_retrigger_ms / hop_ms))
    )

    for index in range(len(active)):
        desired = int(pitch[index]) if active[index] else -1
        is_onset = bool(onset[index] >= float(onset_threshold))
        if desired == current:
            pending = -2
            pending_count = 0
            pending_has_onset = False
            pending_harmonic_veto = False
            if (
                current >= 0
                and retrigger_evidence[index]
                and index - last_note_on >= minimum_retrigger_frames
            ):
                retrigger[index] = True
                last_note_on = index
        else:
            if desired == pending:
                pending_count += 1
            else:
                pending = desired
                pending_count = 1
                pending_has_onset = False
                pending_harmonic_veto = False
            pending_has_onset = pending_has_onset or is_onset
            if harmonic is not None and current >= 0 and desired >= 0:
                pending_harmonic_veto = (
                    pending_harmonic_veto
                    or strongest_harmonic_explains(
                        current, desired, harmonic[index]
                    )
                )
            active_pitch_change = current >= 0 and desired >= 0
            allowed = (
                pending_count >= required_frames
                and (not active_pitch_change or pending_has_onset)
                and not pending_harmonic_veto
            )
            if pending_count >= required_frames and pending_harmonic_veto:
                harmonic_veto[index] = True
            if allowed:
                current = desired
                pending = -2
                pending_count = 0
                pending_has_onset = False
                pending_harmonic_veto = False
                if current >= 0:
                    last_note_on = index
        if current >= 0:
            output_active[index] = True
            output_pitch[index] = current
    return output_active, output_pitch, retrigger, harmonic_veto


def _infer_multitask(
    model,
    waveform: np.ndarray,
    end_samples: np.ndarray,
    visible_windows: np.ndarray,
    gain: float,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    active_parts: list[np.ndarray] = []
    pitch_parts: list[np.ndarray] = []
    onset_parts: list[np.ndarray] = []
    harmonic_parts: list[np.ndarray] = []
    started = time.perf_counter()
    for batch_start in range(0, len(end_samples), batch_size):
        batch_end = min(len(end_samples), batch_start + batch_size)
        count = batch_end - batch_start
        audio = np.zeros((count, 4096, 1), dtype=np.float32)
        mask = np.zeros((count, 4096), dtype=np.float32)
        for row, frame_index in enumerate(range(batch_start, batch_end)):
            end_sample = int(end_samples[frame_index])
            visible = int(visible_windows[frame_index])
            available = min(end_sample, visible)
            if available:
                audio[row, -available:, 0] = waveform[
                    end_sample - available:end_sample
                ]
                mask[row, -available:] = 1.0
        audio *= gain
        np.clip(audio, -1.0, 1.0, out=audio)
        raw = model({"audio": audio, "time_mask": mask}, training=False)
        required = {"active", "pitch", "onset", "harmonic_amplitude"}
        missing = required - set(raw)
        if missing:
            raise ValueError(f"Sorties V6.2 manquantes: {sorted(missing)}")
        active_parts.append(np.asarray(raw["active"], dtype=np.float32).reshape(-1))
        pitch_parts.append(np.asarray(raw["pitch"], dtype=np.float32))
        onset_parts.append(np.asarray(raw["onset"], dtype=np.float32).reshape(-1))
        harmonic_parts.append(
            np.asarray(raw["harmonic_amplitude"], dtype=np.float32)
        )
    return (
        np.concatenate(active_parts),
        np.concatenate(pitch_parts),
        np.concatenate(onset_parts),
        np.concatenate(harmonic_parts),
        time.perf_counter() - started,
    )


def _reference_onsets(
    notes: list[NoteEvent],
    frame_times: np.ndarray,
    evaluable: np.ndarray,
    target_pitch: np.ndarray,
    sample_rate: int,
    min_pitch: int,
    max_pitch: int,
) -> np.ndarray:
    targets = np.zeros(len(frame_times), dtype=bool)
    onset_age_s = 512.0 / sample_rate
    for note in notes:
        if not min_pitch <= note.pitch_midi <= max_pitch:
            continue
        desired_time = note.start_s + onset_age_s
        index = int(np.searchsorted(frame_times, desired_time, side="left"))
        if (
            index < len(frame_times)
            and evaluable[index]
            and target_pitch[index] == note.pitch_midi
        ):
            targets[index] = True
    return targets


def _reference_coverage(
    notes: list[NoteEvent],
    frame_times: np.ndarray,
    evaluable: np.ndarray,
    target_pitch: np.ndarray,
    active: np.ndarray,
    pitch: np.ndarray,
    min_pitch: int,
    max_pitch: int,
) -> dict[str, object]:
    coverage: list[float] = []
    latencies: list[float] = []
    for note in notes:
        if not min_pitch <= note.pitch_midi <= max_pitch:
            continue
        indices = np.flatnonzero(
            (frame_times >= note.start_s)
            & (frame_times < note.end_s)
            & evaluable
            & (target_pitch == note.pitch_midi)
        )
        if len(indices) == 0:
            continue
        correct = active[indices] & (pitch[indices] == note.pitch_midi)
        coverage.append(float(np.mean(correct)))
        correct_indices = indices[correct]
        if len(correct_indices):
            latencies.append(max(
                0.0,
                (float(frame_times[correct_indices[0]]) - note.start_s) * 1000.0,
            ))
    values = np.asarray(coverage, dtype=np.float64)
    return {
        "evaluable": int(len(values)),
        "covered_any": int(np.sum(values > 0.0)),
        "covered_majority": int(np.sum(values >= 0.5)),
        "missing": int(np.sum(values == 0.0)),
        "onset_latency_mean_ms": float(np.mean(latencies)) if latencies else None,
        "onset_latency_p95_ms": (
            float(np.percentile(latencies, 95)) if latencies else None
        ),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _variant_report(
    name: str,
    output_dir: Path,
    active: np.ndarray,
    pitch: np.ndarray,
    retrigger: np.ndarray,
    harmonic_veto: np.ndarray,
    active_sets: list[tuple[int, ...]],
    evaluable: np.ndarray,
    target_pitch: np.ndarray,
    notes: list[NoteEvent],
    frame_times: np.ndarray,
    waveform: np.ndarray,
    end_samples: np.ndarray,
    sample_rate: int,
    min_pitch: int,
    max_pitch: int,
) -> dict[str, object]:
    target_active = target_pitch >= 0
    positive = evaluable & target_active
    events = decode_events(
        active,
        pitch,
        frame_times,
        len(waveform) / sample_rate,
        retrigger=retrigger,
    )
    rows, classes = _classified_event_rows(
        events,
        active_sets,
        waveform,
        end_samples,
        sample_rate,
        min_pitch,
        max_pitch,
    )
    _write_csv(output_dir / f"{name}_events.csv", rows)
    active_metrics = binary_metrics(
        active[evaluable].astype(np.float32), target_active[evaluable], 0.5
    )
    pitch_correct = pitch == target_pitch
    joint = (
        (evaluable & ~target_active & ~active)
        | (positive & active & pitch_correct)
    )
    reference_starts = np.asarray([note.start_s for note in notes], dtype=np.float64)
    retrigger_indices = np.flatnonzero(retrigger)
    unsupported_retriggers = int(sum(
        not np.any(np.abs(reference_starts - frame_times[index]) <= 0.05)
        for index in retrigger_indices
    ))
    duration_minutes = len(waveform) / sample_rate / 60.0
    return {
        "active": active_metrics,
        "joint_frame_accuracy": float(
            np.sum(joint) / max(int(np.sum(evaluable)), 1)
        ),
        "gated_correct_pitch_recall": float(
            np.sum(positive & active & pitch_correct)
            / max(int(np.sum(positive)), 1)
        ),
        "active_audio_ticks_with_no_active_prediction": int(
            np.sum(positive & ~active)
        ),
        "events": {
            "generated": len(events),
            **{key: int(classes[key]) for key in (
                "supported", "weak", "harmonic_suspect", "unsupported"
            )},
            "ghost_events_per_minute": float(
                (classes["harmonic_suspect"] + classes["unsupported"])
                / max(duration_minutes, 1e-12)
            ),
            "controlled_same_midi_retriggers": int(len(retrigger_indices)),
            "unsupported_same_midi_retriggers": unsupported_retriggers,
            "harmonic_veto_frames": int(np.sum(harmonic_veto)),
        },
        "reference_notes": _reference_coverage(
            notes,
            frame_times,
            evaluable,
            target_pitch,
            active,
            pitch,
            min_pitch,
            max_pitch,
        ),
    }


def evaluate_source(
    run_dir: Path,
    source_id: str,
    batch_size: int,
    benchmark_iterations: int,
) -> dict[str, object]:
    import tensorflow as tf

    selection = json.loads(
        (run_dir / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    checkpoint = run_dir / selection["selected_checkpoint"]
    active_threshold = float(selection["active_threshold"])
    onset_threshold = float(selection["onset_threshold"])
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    dataset = config["dataset"]
    sample_rate = int(dataset["sample_rate"])
    hop_samples = int(dataset["hop_size"])
    min_pitch = int(dataset["min_pitch"])
    max_pitch = int(dataset["max_pitch"])
    gain = float(json.loads(
        (run_dir / "normalization.json").read_text(encoding="utf-8")
    )["gain"])

    recordings = {item.source_id: item for item in discover_guitarset("data/GuitarSet")}
    if source_id not in recordings:
        raise ValueError(f"Source GuitarSet inconnue: {source_id}")
    recording = recordings[source_id]
    if recording.player_id != "05":
        raise ValueError("L'ablation continue doit utiliser le joueur test 05.")
    audio, actual_rate = read_recording_audio(recording)
    if int(actual_rate) != sample_rate:
        divisor = math.gcd(int(actual_rate), sample_rate)
        audio = resample_poly(
            audio,
            sample_rate // divisor,
            int(actual_rate) // divisor,
            axis=0,
        ).astype(np.float32, copy=False)
    waveform = np.mean(audio, axis=1, dtype=np.float32)
    duration_s = len(waveform) / sample_rate
    notes = [
        NoteEvent(
            note.note_id,
            note.start_s,
            min(note.end_s, duration_s),
            note.pitch_midi,
            note.expression,
        )
        for note in parse_recording_notes(recording)
        if 0.0 <= note.start_s < duration_s and note.end_s > note.start_s
    ]
    model = tf.keras.models.load_model(checkpoint, compile=False)
    benchmark = _benchmark_batch_one(
        model, waveform, gain, benchmark_iterations
    )

    end_samples = np.arange(hop_samples, len(waveform) + 1, hop_samples)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    visible, detected_onset = progressive_windows(
        waveform, sample_rate, hop_samples, end_samples
    )
    (
        active_probability,
        pitch_probability,
        onset_probability,
        harmonic_amplitude,
        elapsed_s,
    ) = _infer_multitask(
        model, waveform, end_samples, visible, gain, batch_size
    )
    predicted_active = active_probability >= active_threshold
    predicted_pitch = np.argmax(pitch_probability, axis=1).astype(np.int32) + min_pitch
    hop_ms = hop_samples / sample_rate * 1000.0

    baseline_active, baseline_pitch, baseline_retrigger = stabilize_predictions(
        predicted_active,
        predicted_pitch,
        detected_onset,
        hop_ms,
        required_frames=2,
    )
    onset_active, onset_pitch, onset_retrigger, onset_veto = (
        stabilize_with_model_onset(
            predicted_active,
            predicted_pitch,
            onset_probability,
            onset_threshold,
            hop_ms,
            required_frames=2,
        )
    )
    harmonic_active, harmonic_pitch, harmonic_retrigger, harmonic_veto = (
        stabilize_with_model_onset(
            predicted_active,
            predicted_pitch,
            onset_probability,
            onset_threshold,
            hop_ms,
            harmonic_amplitude=harmonic_amplitude,
            required_frames=2,
        )
    )

    output_dir = run_dir / "continuous_onset_ablation" / source_id
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = {
        "baseline_detected_onset": _variant_report(
            "baseline_detected_onset", output_dir,
            baseline_active, baseline_pitch, baseline_retrigger,
            np.zeros(len(frame_times), dtype=bool), active_sets, evaluable,
            target_pitch, notes, frame_times, waveform, end_samples,
            sample_rate, min_pitch, max_pitch,
        ),
        "model_onset_gate": _variant_report(
            "model_onset_gate", output_dir,
            onset_active, onset_pitch, onset_retrigger, onset_veto,
            active_sets, evaluable, target_pitch, notes, frame_times,
            waveform, end_samples, sample_rate, min_pitch, max_pitch,
        ),
        "model_onset_harmonic_gate": _variant_report(
            "model_onset_harmonic_gate", output_dir,
            harmonic_active, harmonic_pitch, harmonic_retrigger, harmonic_veto,
            active_sets, evaluable, target_pitch, notes, frame_times,
            waveform, end_samples, sample_rate, min_pitch, max_pitch,
        ),
    }

    onset_targets = _reference_onsets(
        notes,
        frame_times,
        evaluable,
        target_pitch,
        sample_rate,
        min_pitch,
        max_pitch,
    )
    onset_eval_mask = evaluable
    onset_metrics = binary_metrics(
        onset_probability[onset_eval_mask],
        onset_targets[onset_eval_mask],
        onset_threshold,
    )
    onset_metrics["average_precision"] = average_precision(
        onset_probability[onset_eval_mask], onset_targets[onset_eval_mask]
    )

    debug_rows: list[dict[str, object]] = []
    for index, frame_time in enumerate(frame_times):
        debug_rows.append({
            "frame": index,
            "time_s": float(frame_time),
            "visible_window": int(visible[index]),
            "detected_onset": int(detected_onset[index]),
            "target_onset": int(onset_targets[index]),
            "model_onset_probability": float(onset_probability[index]),
            "model_onset": int(onset_probability[index] >= onset_threshold),
            "target_pitch": int(target_pitch[index]),
            "predicted_active": int(predicted_active[index]),
            "predicted_pitch": int(predicted_pitch[index]),
            "baseline_pitch": int(baseline_pitch[index]),
            "onset_gate_pitch": int(onset_pitch[index]),
            "harmonic_gate_pitch": int(harmonic_pitch[index]),
            "harmonic_veto": int(harmonic_veto[index]),
        })
    _write_csv(output_dir / "debug_frames.csv", debug_rows)

    summary = {
        "source_id": source_id,
        "checkpoint": checkpoint.name,
        "active_threshold_validation_only": active_threshold,
        "onset_threshold_validation_only": onset_threshold,
        "duration_s": duration_s,
        "frames": int(len(frame_times)),
        "onset_frame_metrics": onset_metrics,
        "batch_one_inference": benchmark,
        "offline_batch_inference": {
            "batch_size": batch_size,
            "elapsed_s": elapsed_s,
            "frames_per_second": len(frame_times) / max(elapsed_s, 1e-12),
        },
        "latency_contract": {
            "algorithmic_lookahead_ms": 0.0,
            "hop_ms": hop_ms,
            "maximum_stability_delay_ms": hop_ms,
            "onset_audio_context_ms": 512 / sample_rate * 1000.0,
        },
        "variants": variants,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--benchmark-iterations", type=int, default=50)
    args = parser.parse_args()
    result = evaluate_source(
        args.run_dir.resolve(),
        args.source_id,
        args.batch_size,
        args.benchmark_iterations,
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
