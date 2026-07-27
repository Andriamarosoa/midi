"""Compare the standalone V6.3 onset gate against the frozen V6.0 baseline."""

from __future__ import annotations

import argparse
import json
import math
import time
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
from src.v6.continuous_onset_ablation import (
    _variant_report,
    stabilize_with_model_onset,
)
from src.v6.continuous_validate import (
    _infer,
    frame_labels,
    progressive_windows,
    stabilize_predictions,
)
from src.v6.evaluate import average_precision, binary_metrics
from src.v6.onset_continuous_dataset import first_causal_frame_end, onset_frame_ends
from src.v6.train_continuous_onset import benchmark_batch_one, event_metrics


DEFAULT_SOURCES = (
    "gsmono_05_bn1_129_eb_solo",
    "gsmono_05_bn1_147_gb_solo",
    "gsmono_05_bn2_131_b_solo",
    "gsmono_05_bn3_119_g_solo",
)


def _infer_onset(
    model,
    waveform: np.ndarray,
    end_samples: np.ndarray,
    gain: float,
    batch_size: int,
) -> tuple[np.ndarray, float]:
    parts: list[np.ndarray] = []
    started = time.perf_counter()
    for start in range(0, len(end_samples), batch_size):
        selected = end_samples[start:start + batch_size]
        audio = np.asarray([
            causal_window(waveform, int(end_sample), 512)
            for end_sample in selected
        ], dtype=np.float32)
        audio *= gain
        np.clip(audio, -1.0, 1.0, out=audio)
        raw = model(audio[..., None], training=False)
        parts.append(np.asarray(raw, dtype=np.float32).reshape(-1))
    return np.concatenate(parts), time.perf_counter() - started


def _load_waveform(recording, sample_rate: int) -> tuple[np.ndarray, list[NoteEvent]]:
    audio, actual_rate = read_recording_audio(recording)
    actual_rate = int(actual_rate)
    if actual_rate != sample_rate:
        divisor = math.gcd(actual_rate, sample_rate)
        audio = resample_poly(
            audio,
            sample_rate // divisor,
            actual_rate // divisor,
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
    return waveform, notes


def evaluate_source(
    v60_model,
    onset_model,
    recording,
    output_dir: Path,
    sample_rate: int,
    hop_size: int,
    min_pitch: int,
    max_pitch: int,
    v60_gain: float,
    active_threshold: float,
    onset_gain: float,
    onset_threshold: float,
    batch_size: int,
) -> dict[str, object]:
    waveform, notes = _load_waveform(recording, sample_rate)
    end_samples = np.arange(hop_size, len(waveform) + 1, hop_size, dtype=np.int64)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    visible, detected_onset = progressive_windows(
        waveform, sample_rate, hop_size, end_samples
    )
    active_probability, pitch_probability, pitch_class, v60_elapsed = _infer(
        v60_model, waveform, end_samples, visible, v60_gain, batch_size
    )
    onset_probability, onset_elapsed = _infer_onset(
        onset_model, waveform, end_samples, onset_gain, batch_size
    )
    predicted_active = active_probability >= active_threshold
    predicted_pitch = pitch_class.astype(np.int32) + min_pitch
    hop_ms = hop_size / sample_rate * 1000.0

    baseline_active, baseline_pitch, baseline_retrigger = stabilize_predictions(
        predicted_active,
        predicted_pitch,
        detected_onset,
        hop_ms,
        required_frames=2,
    )
    gated_active, gated_pitch, gated_retrigger, gated_veto = (
        stabilize_with_model_onset(
            predicted_active,
            predicted_pitch,
            onset_probability,
            onset_threshold,
            hop_ms,
            retrigger_onset=detected_onset,
            required_frames=2,
        )
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    variants = {
        "v6_0_baseline": _variant_report(
            "v6_0_baseline", output_dir,
            baseline_active, baseline_pitch, baseline_retrigger,
            np.zeros(len(frame_times), dtype=bool),
            active_sets, evaluable, target_pitch, notes, frame_times,
            waveform, end_samples, sample_rate, min_pitch, max_pitch,
        ),
        "v6_3_onset_gate": _variant_report(
            "v6_3_onset_gate", output_dir,
            gated_active, gated_pitch, gated_retrigger, gated_veto,
            active_sets, evaluable, target_pitch, notes, frame_times,
            waveform, end_samples, sample_rate, min_pitch, max_pitch,
        ),
    }
    targets = np.zeros(len(end_samples), dtype=np.float32)
    positive = onset_frame_ends(
        notes, sample_rate, hop_size, 2, len(waveform), min_pitch, max_pitch
    )
    lookup = {int(value): index for index, value in enumerate(end_samples)}
    for value in positive:
        index = lookup.get(int(value))
        if index is not None:
            targets[index] = 1.0
    onset_frame = binary_metrics(onset_probability, targets, onset_threshold)
    onset_frame["average_precision"] = average_precision(
        onset_probability, targets
    )
    first_groups: dict[int, list[NoteEvent]] = {}
    for note in notes:
        if not min_pitch <= note.pitch_midi <= max_pitch:
            continue
        first = first_causal_frame_end(
            int(round(note.start_s * sample_rate)), hop_size
        )
        first_groups.setdefault(first, []).append(note)
    reference_samples = np.asarray([
        min(int(round(note.start_s * sample_rate)) for note in grouped)
        for _, grouped in sorted(first_groups.items())
    ], dtype=np.int64)
    event_item = {
        "probabilities": onset_probability,
        "end_samples": end_samples,
        "reference_samples": reference_samples,
        "audio_duration_s": len(waveform) / sample_rate,
    }
    onset_event = event_metrics([event_item], onset_threshold, sample_rate)
    report = {
        "source_id": recording.source_id,
        "duration_s": len(waveform) / sample_rate,
        "frames": int(len(end_samples)),
        "onset_threshold_validation_only": onset_threshold,
        "onset_frame_metrics": onset_frame,
        "onset_event_metrics": onset_event,
        "offline_inference": {
            "v6_0_seconds": v60_elapsed,
            "v6_3_onset_seconds": onset_elapsed,
        },
        "latency_contract": {
            "algorithmic_lookahead_ms": 0.0,
            "hop_ms": hop_ms,
            "maximum_stability_delay_ms": hop_ms,
            "onset_past_context_ms": 512 / sample_rate * 1000.0,
        },
        "variants": variants,
    }
    (output_dir / "summary.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def aggregate_variant(
    reports: list[dict[str, object]], variant: str
) -> dict[str, object]:
    selected = [item["variants"][variant] for item in reports]
    active_counts = {
        key: sum(int(item["active"][key]) for item in selected)
        for key in ("tp", "fp", "tn", "fn")
    }
    precision = active_counts["tp"] / max(
        active_counts["tp"] + active_counts["fp"], 1
    )
    recall = active_counts["tp"] / max(
        active_counts["tp"] + active_counts["fn"], 1
    )
    count = sum(int(item["active"]["count"]) for item in selected)
    positives = sum(int(item["active"]["positives"]) for item in selected)
    duration_minutes = sum(float(item["duration_s"]) for item in reports) / 60.0
    events = {
        key: sum(int(item["events"][key]) for item in selected)
        for key in (
            "generated", "supported", "weak", "harmonic_suspect", "unsupported",
            "controlled_same_midi_retriggers", "unsupported_same_midi_retriggers",
        )
    }
    reference = {
        key: sum(int(item["reference_notes"][key]) for item in selected)
        for key in ("evaluable", "covered_any", "covered_majority", "missing")
    }
    return {
        "active_f1": float(
            2.0 * precision * recall / max(precision + recall, 1e-12)
        ),
        "joint_frame_accuracy": float(sum(
            float(item["joint_frame_accuracy"]) * int(item["active"]["count"])
            for item in selected
        ) / max(count, 1)),
        "gated_correct_pitch_recall": float(sum(
            float(item["gated_correct_pitch_recall"])
            * int(item["active"]["positives"])
            for item in selected
        ) / max(positives, 1)),
        "events": {
            **events,
            "ghost_events_per_minute": float(
                (events["harmonic_suspect"] + events["unsupported"])
                / max(duration_minutes, 1e-12)
            ),
        },
        "reference_notes": reference,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v60-run", type=Path, required=True)
    parser.add_argument("--onset-run", type=Path, required=True)
    parser.add_argument("--source-ids", nargs="+", default=DEFAULT_SOURCES)
    parser.add_argument("--batch-size", type=int, default=128)
    args = parser.parse_args()

    import tensorflow as tf

    v60_run = args.v60_run.resolve()
    onset_run = args.onset_run.resolve()
    v60_selection = json.loads(
        (v60_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    onset_selection_path = onset_run / "selected_checkpoint_corrected.json"
    if not onset_selection_path.exists():
        onset_selection_path = onset_run / "selected_checkpoint.json"
    onset_selection = json.loads(
        onset_selection_path.read_text(encoding="utf-8")
    )
    v60_config = json.loads(
        (v60_run / "config.json").read_text(encoding="utf-8")
    )["dataset"]
    sample_rate = int(v60_config["sample_rate"])
    hop_size = int(v60_config["hop_size"])
    min_pitch = int(v60_config["min_pitch"])
    max_pitch = int(v60_config["max_pitch"])
    v60_gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    onset_gain = float(json.loads(
        (onset_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    active_threshold = float(v60_selection["active_threshold"])
    onset_threshold = float(onset_selection["onset_threshold"])
    v60_model = tf.keras.models.load_model(
        v60_run / v60_selection["selected_checkpoint"], compile=False
    )
    onset_model = tf.keras.models.load_model(
        onset_run / onset_selection["selected_checkpoint"], compile=False
    )
    recordings = {
        item.source_id: item for item in discover_guitarset("data/GuitarSet")
    }
    unknown = set(args.source_ids) - set(recordings)
    if unknown:
        raise ValueError(f"Sources inconnues: {sorted(unknown)}")
    if any(recordings[source].player_id != "05" for source in args.source_ids):
        raise ValueError("L'ablation finale doit rester sur le joueur test 05.")
    root = onset_run / "continuous_decoder_ablation_v63"
    reports = [
        evaluate_source(
            v60_model, onset_model, recordings[source], root / source,
            sample_rate, hop_size, min_pitch, max_pitch,
            v60_gain, active_threshold, onset_gain, onset_threshold,
            args.batch_size,
        )
        for source in args.source_ids
    ]
    aggregate = {
        "sources": list(args.source_ids),
        "duration_s": sum(float(item["duration_s"]) for item in reports),
        "onset_threshold_validation_only": onset_threshold,
        "onset_latency_batch_one": benchmark_batch_one(onset_model),
        "variants": {
            name: aggregate_variant(reports, name)
            for name in ("v6_0_baseline", "v6_3_onset_gate")
        },
        "acceptance": {
            "v6_0_reference": {
                "ghost_events_per_minute_max": 52.18,
                "missing_notes_max": 3,
                "joint_frame_accuracy_min": 0.7950,
                "unsupported_retriggers_max": 0,
            },
        },
    }
    candidate = aggregate["variants"]["v6_3_onset_gate"]
    baseline = aggregate["variants"]["v6_0_baseline"]
    aggregate["acceptance"]["observed"] = {
        "ghosts_not_worse": (
            candidate["events"]["ghost_events_per_minute"]
            <= baseline["events"]["ghost_events_per_minute"]
        ),
        "missing_not_worse": (
            candidate["reference_notes"]["missing"]
            <= baseline["reference_notes"]["missing"]
        ),
        "joint_not_worse": (
            candidate["joint_frame_accuracy"]
            >= baseline["joint_frame_accuracy"]
        ),
        "unsupported_retriggers_not_worse": (
            candidate["events"]["unsupported_same_midi_retriggers"]
            <= baseline["events"]["unsupported_same_midi_retriggers"]
        ),
    }
    (root / "aggregate.json").write_text(
        json.dumps(aggregate, indent=2), encoding="utf-8"
    )
    print(json.dumps(aggregate, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
