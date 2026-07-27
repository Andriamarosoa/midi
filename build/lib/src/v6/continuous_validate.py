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

from src.stream.onset_detector import AdaptiveOnsetDetector
from src.v5.evaluate import topk_accuracy
from src.v5.external_data import (
    NoteEvent,
    causal_window,
    discover_guitarset,
    midi_to_hz,
    parse_recording_notes,
    read_recording_audio,
)
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401

from .evaluate import average_precision, binary_metrics


WINDOWS = (512, 1024, 2048, 4096)
HARMONIC_INTERVALS = {12, 19, 24, 28, 31, 36}


def frame_labels(
    notes: list[NoteEvent],
    frame_times_s: np.ndarray,
    min_pitch: int,
    max_pitch: int,
) -> tuple[list[tuple[int, ...]], np.ndarray, np.ndarray]:
    active_sets: list[tuple[int, ...]] = []
    evaluable = np.zeros(len(frame_times_s), dtype=bool)
    target_pitch = np.full(len(frame_times_s), -1, dtype=np.int32)
    for index, frame_time in enumerate(frame_times_s):
        pitches = tuple(sorted({
            int(note.pitch_midi)
            for note in notes
            if note.start_s <= frame_time < note.end_s
        }))
        active_sets.append(pitches)
        if not pitches:
            evaluable[index] = True
        elif len(pitches) == 1 and min_pitch <= pitches[0] <= max_pitch:
            evaluable[index] = True
            target_pitch[index] = pitches[0]
    return active_sets, evaluable, target_pitch


def progressive_windows(
    waveform: np.ndarray,
    sample_rate: int,
    hop_samples: int,
    end_samples: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    detector = AdaptiveOnsetDetector(
        sample_rate=sample_rate,
        hop_samples=hop_samples,
        fft_size=512,
        calibration_s=1.0,
    )
    visible = np.full(len(end_samples), 4096, dtype=np.int32)
    onset = np.zeros(len(end_samples), dtype=bool)
    last_onset_sample: int | None = None
    for index, end_sample in enumerate(end_samples):
        start_sample = max(0, int(end_sample) - hop_samples)
        hop = waveform[start_sample:int(end_sample)]
        if len(hop) < hop_samples:
            hop = np.pad(hop, (hop_samples - len(hop), 0))
        result = detector.process(hop)
        if result.is_onset:
            onset[index] = True
            last_onset_sample = int(end_sample)
        if last_onset_sample is not None:
            age = int(end_sample) - last_onset_sample
            visible[index] = next(
                (window for window in WINDOWS if age <= window), WINDOWS[-1]
            )
    return visible, onset


def decode_events(
    predicted_active: np.ndarray,
    predicted_pitch: np.ndarray,
    frame_times_s: np.ndarray,
    duration_s: float,
    retrigger: np.ndarray | None = None,
) -> list[dict[str, float | int]]:
    events: list[dict[str, float | int]] = []
    current_pitch: int | None = None
    start_index = 0
    retrigger = (
        np.zeros(len(frame_times_s), dtype=bool)
        if retrigger is None
        else np.asarray(retrigger, dtype=bool)
    )
    for index in range(len(frame_times_s)):
        desired = int(predicted_pitch[index]) if predicted_active[index] else None
        if desired == current_pitch and not (
            current_pitch is not None and retrigger[index]
        ):
            continue
        if current_pitch is not None:
            events.append({
                "start_index": start_index,
                "end_index": index,
                "start_s": float(frame_times_s[start_index]),
                "end_s": float(frame_times_s[index]),
                "pitch_midi": current_pitch,
            })
        current_pitch = desired
        start_index = index
    if current_pitch is not None:
        events.append({
            "start_index": start_index,
            "end_index": len(frame_times_s),
            "start_s": float(frame_times_s[start_index]),
            "end_s": float(duration_s),
            "pitch_midi": current_pitch,
        })
    return events


def stabilize_predictions(
    predicted_active: np.ndarray,
    predicted_pitch: np.ndarray,
    detected_onset: np.ndarray,
    hop_ms: float,
    required_frames: int = 2,
    minimum_retrigger_ms: float = 80.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Causal anti-chattering state with controlled same-MIDI retriggers."""
    if required_frames < 1:
        raise ValueError("required_frames doit etre positif.")
    active = np.asarray(predicted_active, dtype=bool)
    pitch = np.asarray(predicted_pitch, dtype=np.int32)
    onset = np.asarray(detected_onset, dtype=bool)
    output_active = np.zeros(len(active), dtype=bool)
    output_pitch = np.full(len(active), -1, dtype=np.int32)
    retrigger = np.zeros(len(active), dtype=bool)
    current = -1
    pending = -2
    pending_count = 0
    last_note_on = -10**9
    minimum_retrigger_frames = max(
        1, int(math.ceil(minimum_retrigger_ms / hop_ms))
    )

    for index in range(len(active)):
        desired = int(pitch[index]) if active[index] else -1
        if desired == current:
            pending = -2
            pending_count = 0
            if (
                current >= 0
                and onset[index]
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
            if pending_count >= required_frames:
                current = desired
                pending = -2
                pending_count = 0
                if current >= 0:
                    last_note_on = index
        if current >= 0:
            output_active[index] = True
            output_pitch[index] = current
    return output_active, output_pitch, retrigger


def _spectral_support_ratio(
    waveform: np.ndarray,
    end_sample: int,
    pitch_midi: int,
    sample_rate: int,
    min_pitch: int,
    max_pitch: int,
) -> float:
    frame = causal_window(waveform, end_sample, 4096).astype(np.float64)
    frame -= float(np.mean(frame))
    magnitude = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
    hz_per_bin = sample_rate / float(len(frame))

    def score(midi: int) -> float:
        center = int(round(midi_to_hz(midi) / hz_per_bin))
        low = max(0, center - 1)
        high = min(len(magnitude), center + 2)
        return float(np.max(magnitude[low:high])) if high > low else 0.0

    denominator = max(
        max(score(midi) for midi in range(min_pitch, max_pitch + 1)), 1e-12
    )
    return score(pitch_midi) / denominator


def _classified_event_rows(
    events: list[dict[str, float | int]],
    active_sets: list[tuple[int, ...]],
    waveform: np.ndarray,
    end_samples: np.ndarray,
    sample_rate: int,
    min_pitch: int,
    max_pitch: int,
) -> tuple[list[dict[str, object]], Counter[str]]:
    rows: list[dict[str, object]] = []
    classes: Counter[str] = Counter()
    for event_id, event in enumerate(events):
        start_index = int(event["start_index"])
        end_index = int(event["end_index"])
        pitch = int(event["pitch_midi"])
        frame_sets = active_sets[start_index:end_index]
        support = float(np.mean([pitch in pitches for pitches in frame_sets]))
        harmonic_suspect = support == 0.0 and any(
            any(pitch - reference in HARMONIC_INTERVALS for reference in pitches)
            for pitches in frame_sets
        )
        if support >= 0.5:
            classification = "supported"
        elif support > 0.0:
            classification = "weak"
        elif harmonic_suspect:
            classification = "harmonic_suspect"
        else:
            classification = "unsupported"
        classes[classification] += 1
        rows.append({
            "event_id": event_id,
            "start_s": event["start_s"],
            "end_s": event["end_s"],
            "duration_ms": (
                float(event["end_s"]) - float(event["start_s"])
            ) * 1000.0,
            "pitch_midi": pitch,
            "annotation_support_ratio": support,
            "spectral_support_ratio": _spectral_support_ratio(
                waveform,
                int(end_samples[start_index]),
                pitch,
                sample_rate,
                min_pitch,
                max_pitch,
            ),
            "classification": classification,
        })
    return rows, classes


def _infer(
    model,
    waveform: np.ndarray,
    end_samples: np.ndarray,
    visible_windows: np.ndarray,
    gain: float,
    batch_size: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
    active_parts: list[np.ndarray] = []
    pitch_parts: list[np.ndarray] = []
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
        active_parts.append(np.asarray(raw["active"], dtype=np.float32).reshape(-1))
        pitch_parts.append(np.asarray(raw["pitch"], dtype=np.float32))
    elapsed_s = time.perf_counter() - started
    active = np.concatenate(active_parts)
    pitch_probabilities = np.concatenate(pitch_parts)
    pitch = np.argmax(pitch_probabilities, axis=1).astype(np.int32)
    return active, pitch_probabilities, pitch, elapsed_s


def _benchmark_batch_one(
    model,
    waveform: np.ndarray,
    gain: float,
    iterations: int,
) -> dict[str, object]:
    import tensorflow as tf

    if iterations <= 0:
        return {"skipped": True}

    frame = causal_window(waveform, min(len(waveform), 4096), 4096)
    audio = np.clip(frame * gain, -1.0, 1.0)[None, :, None]
    mask = np.ones((1, 4096), dtype=np.float32)
    inputs = {"audio": audio, "time_mask": mask}
    compiled = tf.function(
        lambda audio_value, mask_value: model(
            {"audio": audio_value, "time_mask": mask_value}, training=False
        ),
        autograph=False,
    )

    def measure(callable_) -> dict[str, float]:
        for _ in range(10):
            raw = callable_()
            for value in raw.values():
                np.asarray(value)
        timings: list[float] = []
        for _ in range(iterations):
            started = time.perf_counter()
            raw = callable_()
            for value in raw.values():
                np.asarray(value)
            timings.append((time.perf_counter() - started) * 1000.0)
        values = np.asarray(timings, dtype=np.float64)
        return {
            "mean_ms": float(np.mean(values)),
            "p50_ms": float(np.percentile(values, 50)),
            "p95_ms": float(np.percentile(values, 95)),
            "max_ms": float(np.max(values)),
        }

    return {
        "iterations_each": int(iterations),
        "keras_eager": measure(lambda: model(inputs, training=False)),
        "tf_function": measure(lambda: compiled(audio, mask)),
    }


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    if not rows:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def evaluate_policy(
    output_dir: Path,
    policy: str,
    waveform: np.ndarray,
    sample_rate: int,
    hop_samples: int,
    notes: list[NoteEvent],
    model,
    gain: float,
    threshold: float,
    min_pitch: int,
    max_pitch: int,
    batch_size: int,
) -> dict[str, object]:
    end_samples = np.arange(hop_samples, len(waveform) + 1, hop_samples)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    if policy == "fixed_4096":
        visible = np.full(len(end_samples), 4096, dtype=np.int32)
        detected_onsets = np.zeros(len(end_samples), dtype=bool)
    elif policy == "detected_progressive":
        visible, detected_onsets = progressive_windows(
            waveform, sample_rate, hop_samples, end_samples
        )
    else:
        raise ValueError(f"Politique inconnue: {policy}")

    active_probability, pitch_probability, pitch_class, elapsed_s = _infer(
        model, waveform, end_samples, visible, gain, batch_size
    )
    predicted_active = active_probability >= threshold
    predicted_pitch = pitch_class + min_pitch
    target_active = target_pitch >= 0
    active_metrics = binary_metrics(
        active_probability[evaluable], target_active[evaluable], threshold
    )
    active_metrics["average_precision"] = average_precision(
        active_probability[evaluable], target_active[evaluable]
    )
    positive = evaluable & target_active
    pitch_targets = target_pitch[positive] - min_pitch
    pitch_metrics = {
        "frames": int(np.sum(positive)),
        "top1": topk_accuracy(pitch_probability[positive], pitch_targets, 1),
        "top3": topk_accuracy(pitch_probability[positive], pitch_targets, 3),
    }
    pitch_correct = predicted_pitch == target_pitch
    joint_correct = (
        (evaluable & ~target_active & ~predicted_active)
        | (positive & predicted_active & pitch_correct)
    )
    joint_accuracy = float(np.sum(joint_correct) / max(int(np.sum(evaluable)), 1))

    events = decode_events(
        predicted_active, predicted_pitch, frame_times, len(waveform) / sample_rate
    )
    event_rows, event_classes = _classified_event_rows(
        events,
        active_sets,
        waveform,
        end_samples,
        sample_rate,
        min_pitch,
        max_pitch,
    )

    reference_rows: list[dict[str, object]] = []
    onset_latencies: list[float] = []
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
        correct = predicted_active[indices] & (
            predicted_pitch[indices] == note.pitch_midi
        )
        correct_indices = indices[correct]
        coverage = float(np.mean(correct))
        latency_ms = None
        if len(correct_indices):
            latency_ms = max(
                0.0, (float(frame_times[correct_indices[0]]) - note.start_s) * 1000.0
            )
            onset_latencies.append(latency_ms)
        reference_rows.append({
            "note_id": note.note_id,
            "start_s": note.start_s,
            "end_s": note.end_s,
            "pitch_midi": note.pitch_midi,
            "evaluable_frames": int(len(indices)),
            "coverage_ratio": coverage,
            "onset_latency_ms": "" if latency_ms is None else latency_ms,
        })

    retriggers = 0
    unsupported_retriggers = 0
    by_pitch: dict[int, list[dict[str, object]]] = {}
    for row in event_rows:
        by_pitch.setdefault(int(row["pitch_midi"]), []).append(row)
    reference_onsets = np.asarray([note.start_s for note in notes], dtype=np.float64)
    for pitch_events in by_pitch.values():
        for previous, current in zip(pitch_events, pitch_events[1:]):
            gap = float(current["start_s"]) - float(previous["end_s"])
            if gap <= 0.1:
                retriggers += 1
                if not np.any(np.abs(reference_onsets - float(current["start_s"])) <= 0.05):
                    unsupported_retriggers += 1

    hop_ms = hop_samples / sample_rate * 1000.0
    stable_active, stable_pitch, stable_retrigger = stabilize_predictions(
        predicted_active,
        predicted_pitch,
        detected_onsets,
        hop_ms,
        required_frames=2,
    )
    stable_events = decode_events(
        stable_active,
        stable_pitch,
        frame_times,
        len(waveform) / sample_rate,
        retrigger=stable_retrigger,
    )
    stable_event_rows, stable_event_classes = _classified_event_rows(
        stable_events,
        active_sets,
        waveform,
        end_samples,
        sample_rate,
        min_pitch,
        max_pitch,
    )
    stable_metrics = binary_metrics(
        stable_active[evaluable].astype(np.float32),
        target_active[evaluable],
        0.5,
    )
    stable_pitch_correct = stable_pitch == target_pitch
    stable_joint = (
        (evaluable & ~target_active & ~stable_active)
        | (positive & stable_active & stable_pitch_correct)
    )
    stable_retrigger_indices = np.flatnonzero(stable_retrigger)
    unsupported_stable_retriggers = int(sum(
        not np.any(np.abs(reference_onsets - frame_times[index]) <= 0.05)
        for index in stable_retrigger_indices
    ))

    debug_rows: list[dict[str, object]] = []
    for index in range(len(frame_times)):
        debug_rows.append({
            "frame": index,
            "time_s": float(frame_times[index]),
            "visible_window": int(visible[index]),
            "detected_onset": int(detected_onsets[index]),
            "annotated_count": len(active_sets[index]),
            "annotated_midis": ";".join(map(str, active_sets[index])),
            "evaluable": int(evaluable[index]),
            "target_active": int(target_active[index]),
            "target_pitch": int(target_pitch[index]),
            "active_probability": float(active_probability[index]),
            "predicted_active": int(predicted_active[index]),
            "predicted_pitch": int(predicted_pitch[index]),
            "pitch_confidence": float(np.max(pitch_probability[index])),
            "stable_active": int(stable_active[index]),
            "stable_pitch": int(stable_pitch[index]),
            "stable_retrigger": int(stable_retrigger[index]),
        })

    output_dir.mkdir(parents=True, exist_ok=True)
    _write_csv(output_dir / "debug_frames.csv", debug_rows)
    _write_csv(output_dir / "events.csv", event_rows)
    _write_csv(output_dir / "stable_events.csv", stable_event_rows)
    _write_csv(output_dir / "reference_notes.csv", reference_rows)

    duration_minutes = len(waveform) / sample_rate / 60.0
    latency_array = np.asarray(onset_latencies, dtype=np.float64)
    missing = int(sum(float(row["coverage_ratio"]) == 0.0 for row in reference_rows))
    report: dict[str, object] = {
        "policy": policy,
        "duration_s": len(waveform) / sample_rate,
        "frames": int(len(frame_times)),
        "evaluable_frames": int(np.sum(evaluable)),
        "excluded_polyphonic_or_range_frames": int(np.sum(~evaluable)),
        "active": active_metrics,
        "pitch_on_true_monophonic_active": pitch_metrics,
        "joint_frame_accuracy": joint_accuracy,
        "active_audio_ticks_with_no_active_prediction": int(
            np.sum(positive & ~predicted_active)
        ),
        "events": {
            "generated": len(events),
            **{name: int(event_classes[name]) for name in (
                "supported", "weak", "harmonic_suspect", "unsupported"
            )},
            "ghost_events_per_minute": float(
                (event_classes["harmonic_suspect"] + event_classes["unsupported"])
                / max(duration_minutes, 1e-12)
            ),
            "same_midi_retriggers": retriggers,
            "unsupported_same_midi_retriggers": unsupported_retriggers,
        },
        "stable_decoder": {
            "required_consecutive_frames": 2,
            "maximum_added_note_on_or_off_delay_ms": hop_ms,
            "active": stable_metrics,
            "joint_frame_accuracy": float(
                np.sum(stable_joint) / max(int(np.sum(evaluable)), 1)
            ),
            "gated_correct_pitch_recall": float(
                np.sum(positive & stable_active & stable_pitch_correct)
                / max(int(np.sum(positive)), 1)
            ),
            "active_audio_ticks_with_no_active_prediction": int(
                np.sum(positive & ~stable_active)
            ),
            "events": {
                "generated": len(stable_events),
                **{name: int(stable_event_classes[name]) for name in (
                    "supported", "weak", "harmonic_suspect", "unsupported"
                )},
                "ghost_events_per_minute": float(
                    (
                        stable_event_classes["harmonic_suspect"]
                        + stable_event_classes["unsupported"]
                    ) / max(duration_minutes, 1e-12)
                ),
                "controlled_same_midi_retriggers": int(
                    len(stable_retrigger_indices)
                ),
                "unsupported_same_midi_retriggers": unsupported_stable_retriggers,
            },
        },
        "reference_notes": {
            "evaluable": len(reference_rows),
            "covered_any": int(len(reference_rows) - missing),
            "covered_majority": int(sum(
                float(row["coverage_ratio"]) >= 0.5 for row in reference_rows
            )),
            "missing": missing,
            "onset_latency_mean_ms": (
                float(np.mean(latency_array)) if len(latency_array) else None
            ),
            "onset_latency_p95_ms": (
                float(np.percentile(latency_array, 95)) if len(latency_array) else None
            ),
        },
        "detected_onsets": int(np.sum(detected_onsets)),
        "offline_batch_inference": {
            "batch_size": batch_size,
            "elapsed_s": elapsed_s,
            "frames_per_second": len(frame_times) / max(elapsed_s, 1e-12),
        },
        "latency_contract": {
            "algorithmic_lookahead_ms": 0.0,
            "hop_ms": hop_ms,
            "maximum_past_context_ms": 4096 / sample_rate * 1000.0,
        },
    }
    (output_dir / "report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument(
        "--policies",
        nargs="+",
        choices=("fixed_4096", "detected_progressive"),
        default=("fixed_4096", "detected_progressive"),
    )
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--benchmark-iterations", type=int, default=50)
    args = parser.parse_args()

    import tensorflow as tf

    run_dir = args.run_dir.resolve()
    selection = json.loads(
        (run_dir / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    checkpoint = run_dir / selection["selected_checkpoint"]
    threshold = float(selection["active_threshold"])
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    dataset = config["dataset"]
    sample_rate = int(dataset["sample_rate"])
    hop_samples = int(dataset["hop_size"])
    min_pitch = int(dataset["min_pitch"])
    max_pitch = int(dataset["max_pitch"])
    gain = float(
        json.loads((run_dir / "normalization.json").read_text(encoding="utf-8"))[
            "gain"
        ]
    )

    recordings = {
        recording.source_id: recording
        for recording in discover_guitarset("data/GuitarSet")
    }
    if args.source_id not in recordings:
        raise ValueError(f"Source GuitarSet inconnue: {args.source_id}")
    recording = recordings[args.source_id]
    if recording.player_id != "05":
        raise ValueError("La validation continue V6.0 doit utiliser le joueur test 05.")

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
        model, waveform, gain, args.benchmark_iterations
    )

    root = run_dir / "continuous_validation" / args.source_id
    reports = {
        policy: evaluate_policy(
            root / policy,
            policy,
            waveform,
            sample_rate,
            hop_samples,
            notes,
            model,
            gain,
            threshold,
            min_pitch,
            max_pitch,
            args.batch_size,
        )
        for policy in args.policies
    }
    summary = {
        "source_id": args.source_id,
        "player_id": recording.player_id,
        "checkpoint": checkpoint.name,
        "active_threshold_validation_only": threshold,
        "sample_rate": sample_rate,
        "hop_samples": hop_samples,
        "notes": len(notes),
        "maximum_annotation_polyphony": max(
            (len(pitches) for pitches in frame_labels(
                notes,
                np.arange(hop_samples, len(waveform) + 1, hop_samples)
                / sample_rate,
                min_pitch,
                max_pitch,
            )[0]),
            default=0,
        ),
        "batch_one_inference": benchmark,
        "real_time_hop_budget_ms": hop_samples / sample_rate * 1000.0,
        "policies": reports,
    }
    root.mkdir(parents=True, exist_ok=True)
    (root / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
