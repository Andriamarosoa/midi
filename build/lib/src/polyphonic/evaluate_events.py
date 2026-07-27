"""Continuous note-event evaluation for the causal polyphonic decoder."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import tensorflow as tf

from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.data import (
    PolyphonicCorpus,
    PolyphonicSequence,
    load_manifest,
)
from src.polyphonic.decoder import (
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
    PolyphonicMidiEvent,
    default_decoder_config,
)


@dataclass(frozen=True)
class NoteInterval:
    pitch: int
    start_s: float
    end_s: float


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


def decode_probabilities(
    frame: np.ndarray,
    onset: np.ndarray,
    harmonic_amplitude: np.ndarray,
    config: PolyphonicDecoderConfig,
    sample_rate: int,
    hop_size: int,
) -> tuple[list[NoteInterval], int]:
    decoder = PolyphonicDecoder(config)
    events: list[PolyphonicMidiEvent] = []
    retriggers = 0
    for frame_index in range(len(frame)):
        emitted = decoder.step(
            frame[frame_index], onset[frame_index],
            harmonic_amplitude[frame_index], audio_active=True,
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
    return events_to_notes(
        events, sample_rate, hop_size, max(len(frame) - 1, 0)
    ), retriggers


def evaluate_events(
    run_dir: Path,
    split: str,
    maximum_recordings: int | None = None,
    dataset_id: str | None = None,
    checkpoint_path: Path | None = None,
    thresholds_path: Path | None = None,
    decoder_config_path: Path | None = None,
) -> dict[str, object]:
    config = json.loads((run_dir / "config.json").read_text(encoding="utf-8"))
    thresholds = json.loads(
        (thresholds_path or (run_dir / "thresholds.json")).read_text(
            encoding="utf-8"
        )
    )
    items = [
        item for item in load_manifest(Path(config["dataset"]["manifest"]))
        if item.split == split
        and (dataset_id is None or item.dataset_id == dataset_id)
    ]
    if maximum_recordings is not None:
        items = items[:maximum_recordings]
    default_checkpoint = (
        run_dir / "selected.keras"
        if (run_dir / "selected.keras").is_file()
        else run_dir / "best.keras"
    )
    checkpoint = checkpoint_path or default_checkpoint
    if not checkpoint.is_file():
        raise FileNotFoundError(checkpoint)
    model = tf.keras.models.load_model(checkpoint, compile=False)
    inference_model = tf.keras.Model(
        model.inputs,
        {
            "frame": model.get_layer("frame").output,
            "onset": model.get_layer("onset").output,
            "harmonic_amplitude": model.get_layer("harmonic_amplitude").output,
        },
    )
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

    all_reference: list[NoteInterval] = []
    all_estimated: list[NoteInterval] = []
    recording_reports: list[dict[str, object]] = []
    total_retriggers = 0
    for item in items:
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
            prediction = inference_model.predict(sequence, verbose=0, workers=1)
            estimated, retriggers = decode_probabilities(
                prediction["frame"], prediction["onset"],
                prediction["harmonic_amplitude"], decoder_config,
                corpus.sample_rate, corpus.hop_size,
            )
            reference = truth_notes(arrays)
        finally:
            corpus.close()
        onset_matches = match_notes(reference, estimated)
        offset_matches = match_notes(reference, estimated, require_offset=True)
        total_retriggers += retriggers
        recording_reports.append({
            "source_id": item.source_id,
            "onset": note_metrics(reference, estimated, onset_matches),
            "onset_offset": note_metrics(reference, estimated, offset_matches),
            "retriggers": retriggers,
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

    onset_matches = match_notes(all_reference, all_estimated)
    offset_matches = match_notes(all_reference, all_estimated, require_offset=True)
    report = {
        "run_dir": str(run_dir),
        "checkpoint": str(checkpoint),
        "split": split,
        "dataset_id": dataset_id,
        "recordings": len(items),
        "decoder": asdict(decoder_config),
        "latency": {
            "hop_ms": 1000.0 * 256 / 44_100,
            "direct_onset_added_hops": 0,
            "frame_fallback_added_hops": decoder_config.activation_frames - 1,
            "release_added_hops": decoder_config.release_frames,
        },
        "onset": note_metrics(all_reference, all_estimated, onset_matches),
        "onset_offset": note_metrics(all_reference, all_estimated, offset_matches),
        "retriggers": total_retriggers,
        "per_recording": recording_reports,
    }
    reports_root = run_dir / "reports"
    reports_root.mkdir(exist_ok=True)
    checkpoint_suffix = (
        f"_{checkpoint.stem}" if checkpoint_path is not None else ""
    )
    report_name = (
        f"{split}_{dataset_id}_events{checkpoint_suffix}.json" if dataset_id
        else f"{split}_events{checkpoint_suffix}.json"
    )
    (reports_root / report_name).write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--split", choices=("validation", "test"), required=True)
    parser.add_argument("--maximum-recordings", type=int)
    parser.add_argument("--dataset-id")
    parser.add_argument("--checkpoint", type=Path)
    parser.add_argument("--thresholds", type=Path)
    parser.add_argument("--decoder-config", type=Path)
    args = parser.parse_args()
    report = evaluate_events(
        args.run_dir, args.split, args.maximum_recordings, args.dataset_id,
        args.checkpoint, args.thresholds, args.decoder_config,
    )
    print(json.dumps({
        "split": report["split"],
        "recordings": report["recordings"],
        "onset": report["onset"],
        "onset_offset": report["onset_offset"],
        "retriggers": report["retriggers"],
        "latency": report["latency"],
    }, indent=2))


if __name__ == "__main__":
    main()
