"""Build V6.3.2 examples from transitions actually proposed by frozen V6.0."""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
from collections import Counter
from pathlib import Path

import numpy as np
from scipy.signal import resample_poly

from src.dataset.build_stream_dataset import load_harmonic_csv
from src.v5.external_data import (
    NoteEvent,
    SourceRecording,
    discover_guitarset,
    parse_recording_notes,
    read_recording_audio,
)
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401
from src.v6.continuous_validate import frame_labels
from src.v6.transition_gate import (
    FEATURE_NAMES,
    extract_transition_candidates,
    infer_v60_outputs,
    progressive_stream_features,
)


def _load_audio_and_notes(
    recording: SourceRecording, sample_rate: int
) -> tuple[np.ndarray, list[NoteEvent]]:
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


def _csv_harmonic_profiles(
    recording: SourceRecording,
    notes: list[NoteEvent],
    sample_rate: int,
) -> dict[int, np.ndarray]:
    path = recording.harmonic_csv_path
    if path is None or not path.is_file():
        return {}
    metadata, present, amplitude, _ = load_harmonic_csv(path, 20)
    tolerance_s = 1.0 / sample_rate + 1e-6
    profiles: dict[int, np.ndarray] = {}
    for note in notes:
        meta = metadata.get(note.note_id)
        if meta is None:
            continue
        if (
            abs(float(meta["start_s"]) - note.start_s) > tolerance_s
            or abs(float(meta["end_s"]) - note.end_s) > tolerance_s
        ):
            continue
        values = np.asarray(amplitude[note.note_id], dtype=np.float32).copy()
        values[np.asarray(present[note.note_id]) <= 0.5] = 0.0
        profiles[note.note_id] = values
    return profiles


def _csv_harmonic_strength(
    candidate_pitch: int,
    frame_time: float,
    notes: list[NoteEvent],
    profiles: dict[int, np.ndarray],
) -> float:
    strength = 0.0
    for note in notes:
        if not note.start_s <= frame_time < note.end_s:
            continue
        interval = int(candidate_pitch) - int(note.pitch_midi)
        if interval <= 0 or note.note_id not in profiles:
            continue
        values = profiles[note.note_id]
        for harmonic_number in range(2, len(values) + 1):
            expected = int(round(12.0 * math.log2(harmonic_number)))
            if expected == interval:
                strength = max(strength, float(values[harmonic_number - 1]))
    return strength


def extract_recording(
    model,
    recording: SourceRecording,
    sample_rate: int,
    hop_size: int,
    min_pitch: int,
    max_pitch: int,
    gain: float,
    active_threshold: float,
    batch_size: int,
    inference_function=None,
) -> tuple[dict[str, np.ndarray], dict[str, object]]:
    waveform, notes = _load_audio_and_notes(recording, sample_rate)
    end_samples = np.arange(hop_size, len(waveform) + 1, hop_size, dtype=np.int64)
    frame_times = end_samples.astype(np.float64) / sample_rate
    active_sets, evaluable, target_pitch = frame_labels(
        notes, frame_times, min_pitch, max_pitch
    )
    visible, stream = progressive_stream_features(
        waveform, sample_rate, hop_size, end_samples
    )
    predictions, inference_s = infer_v60_outputs(
        model, waveform, end_samples, visible, gain, batch_size,
        inference_function=inference_function,
    )
    candidates, _, _ = extract_transition_candidates(
        predictions["active"],
        predictions["pitch"],
        predictions["harmonic_amplitude"],
        stream,
        active_threshold,
        notes,
        active_sets,
        frame_times,
        min_pitch,
        max_pitch,
        hop_size / sample_rate * 1000.0,
    )
    profiles = _csv_harmonic_profiles(recording, notes, sample_rate)
    csv_strength = np.asarray([
        _csv_harmonic_strength(
            item.candidate_pitch,
            float(frame_times[item.frame_index]),
            notes,
            profiles,
        )
        for item in candidates
    ], dtype=np.float32)
    count = len(candidates)
    labels = np.asarray([item.label for item in candidates], dtype=np.float32)
    harmonic_suspect = np.asarray(
        [item.harmonic_suspect for item in candidates], dtype=np.int8
    )
    sample_weight = np.ones(count, dtype=np.float32)
    negative = labels <= 0.5
    sample_weight[negative] += np.maximum(
        harmonic_suspect[negative].astype(np.float32),
        csv_strength[negative],
    )
    arrays = {
        "features": np.asarray(
            [item.feature for item in candidates], dtype=np.float32
        ).reshape(count, len(FEATURE_NAMES)),
        "label": labels,
        "sample_weight": sample_weight,
        "frame_index": np.asarray(
            [item.frame_index for item in candidates], dtype=np.int32
        ),
        "frame_end_sample": np.asarray([
            end_samples[item.frame_index] for item in candidates
        ], dtype=np.int64),
        "current_pitch": np.asarray(
            [item.current_pitch for item in candidates], dtype=np.int16
        ),
        "candidate_pitch": np.asarray(
            [item.candidate_pitch for item in candidates], dtype=np.int16
        ),
        "annotation_support_ratio": np.asarray(
            [item.annotation_support_ratio for item in candidates], dtype=np.float32
        ),
        "target_note_id": np.asarray(
            [item.target_note_id for item in candidates], dtype=np.int32
        ),
        "recent_onset_note_id": np.asarray(
            [item.recent_onset_note_id for item in candidates], dtype=np.int32
        ),
        "harmonic_suspect": harmonic_suspect,
        "csv_harmonic_strength": csv_strength,
    }
    report: dict[str, object] = {
        "source_id": recording.source_id,
        "dataset_id": recording.dataset_id,
        "player_id": recording.player_id,
        "split": recording.split,
        "duration_s": len(waveform) / sample_rate,
        "frames": len(end_samples),
        "evaluable_frames": int(np.sum(evaluable)),
        "candidates": count,
        "allowed_labels": int(np.sum(labels > 0.5)),
        "rejected_labels": int(np.sum(labels <= 0.5)),
        "recent_onset_candidates": int(np.sum(
            arrays["recent_onset_note_id"] >= 0
        )),
        "harmonic_suspect_negatives": int(np.sum(
            negative & (harmonic_suspect > 0)
        )),
        "csv_harmonic_negatives": int(np.sum(
            negative & (csv_strength > 0.0)
        )),
        "csv_profile_notes": len(profiles),
        "v6_0_inference_s": inference_s,
    }
    return arrays, report


def build_dataset(
    v60_run: Path,
    output_dir: Path,
    batch_size: int,
    overwrite: bool,
    source_ids: set[str] | None = None,
    max_recordings: int | None = None,
    solo_only: bool = False,
) -> dict[str, object]:
    import tensorflow as tf

    v60_run = v60_run.resolve()
    selection = json.loads(
        (v60_run / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    dataset = json.loads(
        (v60_run / "config.json").read_text(encoding="utf-8")
    )["dataset"]
    gain = float(json.loads(
        (v60_run / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    model = tf.keras.models.load_model(
        v60_run / selection["selected_checkpoint"], compile=False
    )
    @tf.function(
        input_signature=[
            tf.TensorSpec((None, 4096, 1), tf.float32),
            tf.TensorSpec((None, 4096), tf.float32),
        ],
        autograph=False,
    )
    def compiled_inference(audio, mask):
        return model({"audio": audio, "time_mask": mask}, training=False)

    recordings = discover_guitarset("data/GuitarSet")
    if solo_only:
        recordings = [item for item in recordings if item.source_id.endswith("_solo")]
    if source_ids is not None:
        recordings = [item for item in recordings if item.source_id in source_ids]
        unknown = source_ids - {item.source_id for item in recordings}
        if unknown:
            raise ValueError(f"Sources inconnues: {sorted(unknown)}")
    if max_recordings is not None:
        recordings = recordings[:max_recordings]
    output_dir.mkdir(parents=True, exist_ok=True)
    reports: list[dict[str, object]] = []
    rows: list[dict[str, object]] = []
    for index, recording in enumerate(recordings, start=1):
        npz_path = output_dir / f"{recording.source_id}.npz"
        report_path = output_dir / f"{recording.source_id}.json"
        if npz_path.exists() and report_path.exists() and not overwrite:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        else:
            arrays, report = extract_recording(
                model,
                recording,
                int(dataset["sample_rate"]),
                int(dataset["hop_size"]),
                int(dataset["min_pitch"]),
                int(dataset["max_pitch"]),
                gain,
                float(selection["active_threshold"]),
                batch_size,
                inference_function=compiled_inference,
            )
            temporary = output_dir / f".{recording.source_id}.tmp.npz"
            np.savez_compressed(temporary, **arrays)
            os.replace(temporary, npz_path)
            report_path.write_text(
                json.dumps(report, indent=2), encoding="utf-8"
            )
        reports.append(report)
        rows.append({
            "source_id": recording.source_id,
            "npz_path": str(npz_path),
            "dataset_id": recording.dataset_id,
            "player_id": recording.player_id,
            "group_id": recording.group_id,
            "capture_id": recording.capture_id,
            "split": recording.split,
            "candidates": report["candidates"],
            "allowed_labels": report["allowed_labels"],
            "rejected_labels": report["rejected_labels"],
            "harmonic_suspect_negatives": report["harmonic_suspect_negatives"],
            "csv_harmonic_negatives": report["csv_harmonic_negatives"],
        })
        print(
            f"V6.3.2 dataset: {index}/{len(recordings)} "
            f"{recording.source_id} candidats={report['candidates']}",
            flush=True,
        )
    fields = list(rows[0]) if rows else []
    with (output_dir / "manifest.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)
    splits: dict[str, dict[str, int]] = {}
    for split in ("train", "validation", "test"):
        selected_reports = [item for item in reports if item["split"] == split]
        splits[split] = {
            "recordings": len(selected_reports),
            "candidates": sum(int(item["candidates"]) for item in selected_reports),
            "allowed_labels": sum(
                int(item["allowed_labels"]) for item in selected_reports
            ),
            "rejected_labels": sum(
                int(item["rejected_labels"]) for item in selected_reports
            ),
            "harmonic_suspect_negatives": sum(
                int(item["harmonic_suspect_negatives"]) for item in selected_reports
            ),
            "csv_harmonic_negatives": sum(
                int(item["csv_harmonic_negatives"]) for item in selected_reports
            ),
        }
    summary = {
        "contract": "v6.3.2_frozen_v6.0_transition_candidates",
        "v6_0_run": str(v60_run),
        "feature_names": list(FEATURE_NAMES),
        "active_threshold": float(selection["active_threshold"]),
        "batch_size": batch_size,
        "solo_only": bool(solo_only),
        "splits": splits,
    }
    (output_dir / "dataset_report.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--v60-run", type=Path, required=True)
    parser.add_argument(
        "--output-dir", type=Path,
        default=Path("data/dataset/v6_3_2_transition_gate"),
    )
    parser.add_argument("--batch-size", type=int, default=1024)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--source-id", action="append")
    parser.add_argument("--max-recordings", type=int)
    parser.add_argument("--solo-only", action="store_true")
    args = parser.parse_args()
    report = build_dataset(
        args.v60_run,
        args.output_dir,
        args.batch_size,
        args.overwrite,
        None if args.source_id is None else set(args.source_id),
        args.max_recordings,
        args.solo_only,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
