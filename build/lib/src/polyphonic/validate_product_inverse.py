"""Validate the exported WAV-to-MIDI product in both note-match directions."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Callable

import numpy as np
import soundfile as sf

from src.polyphonic.data import ManifestItem, PolyphonicCorpus, load_manifest
from src.polyphonic.evaluate_events import (
    NoteInterval,
    match_notes,
    note_metrics,
    truth_notes,
)
from src.polyphonic.tflite_runtime import PolyphonicBundle
from src.polyphonic.transcribe import transcribe
from src.v5.external_data import parse_midi_notes


def _estimated_notes(path: Path) -> list[NoteInterval]:
    return [
        NoteInterval(note.pitch_midi, note.start_s, note.end_s)
        for note in parse_midi_notes(path)
    ]


def _polyphonic_score(item: ManifestItem) -> int:
    with np.load(item.labels_path, allow_pickle=False) as arrays:
        valid = arrays["valid"] > 0
        return int(np.sum(valid & (arrays["polyphony"] >= 2)))


def select_held_out_recordings(
    items: list[ManifestItem],
    maximum_recordings: int,
    score: Callable[[ManifestItem], int] = _polyphonic_score,
) -> list[ManifestItem]:
    if maximum_recordings < 1:
        raise ValueError("maximum_recordings must be positive.")
    test_items = [item for item in items if item.split == "test"]
    return sorted(
        test_items,
        key=lambda item: (score(item), item.source_id),
        reverse=True,
    )[:maximum_recordings]


def validate(
    artifacts: Path,
    manifest: Path,
    output_dir: Path,
    maximum_recordings: int = 6,
    dataset_id: str | None = None,
) -> dict[str, object]:
    bundle = PolyphonicBundle(artifacts)
    if Path(str(bundle.metadata.get("source_checkpoint", ""))).name != "selected.keras":
        raise ValueError(
            "Inverse locked-test validation requires a validation-selected checkpoint."
        )
    items = load_manifest(manifest)
    if dataset_id is not None:
        items = [item for item in items if item.dataset_id == dataset_id]
    selected = select_held_out_recordings(items, maximum_recordings)
    if not selected:
        raise ValueError("No held-out test recording matched the request.")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_reference: list[NoteInterval] = []
    all_estimated: list[NoteInterval] = []
    per_recording: list[dict[str, object]] = []
    cursor = 0.0

    for item in selected:
        corpus = PolyphonicCorpus([item])
        try:
            waveform = np.asarray(corpus.audio(0)).reshape(-1)
            if np.issubdtype(waveform.dtype, np.integer):
                waveform = waveform.astype(np.float32) / max(
                    abs(np.iinfo(waveform.dtype).min), 1
                )
            else:
                waveform = waveform.astype(np.float32, copy=False)
            reference = truth_notes(corpus.labels[0].arrays)
            with tempfile.TemporaryDirectory() as temporary:
                wav = Path(temporary) / f"{item.source_id}.wav"
                sf.write(wav, waveform, corpus.sample_rate, subtype="PCM_16")
                midi = output_dir / f"{item.source_id}.mid"
                product_report = transcribe(wav, midi, artifacts, 0, 0)
                product_report["input_wav"] = str(item.audio_path)
                product_report["input_audio_member"] = item.audio_member
                product_report["validation_pcm_reencode"] = "PCM_16"
            estimated = _estimated_notes(midi)
        finally:
            corpus.close()
        onset_matches = match_notes(reference, estimated)
        offset_matches = match_notes(reference, estimated, require_offset=True)
        per_recording.append({
            "source_id": item.source_id,
            "dataset_id": item.dataset_id,
            "group_id": item.group_id,
            "split": item.split,
            "source_audio": str(item.audio_path),
            "source_audio_member": item.audio_member,
            "generated_midi": str(midi),
            "product": product_report,
            "wav_to_midi_ghost_check": note_metrics(
                reference, estimated, onset_matches
            ),
            "midi_to_wav_missing_check": {
                **note_metrics(reference, estimated, onset_matches),
                "interpretation": (
                    "Reference WAV annotations not recovered by generated MIDI."
                ),
            },
            "onset_offset": note_metrics(
                reference, estimated, offset_matches
            ),
        })
        all_reference.extend(NoteInterval(
            note.pitch, note.start_s + cursor, note.end_s + cursor
        ) for note in reference)
        all_estimated.extend(NoteInterval(
            note.pitch, note.start_s + cursor, note.end_s + cursor
        ) for note in estimated)
        cursor += 1.0 + max(
            [note.end_s for note in reference + estimated] or [0.0]
        )

    aggregate_onset_matches = match_notes(all_reference, all_estimated)
    aggregate_offset_matches = match_notes(
        all_reference, all_estimated, require_offset=True
    )
    report = {
        "artifacts": str(artifacts),
        "manifest": str(manifest),
        "dataset_id": dataset_id,
        "split": "test",
        "locked_test_opened_after_selection": True,
        "recordings": len(selected),
        "selection_policy": "Highest valid polyphonic-frame counts in locked test.",
        "wav_to_midi_ghost_check": note_metrics(
            all_reference, all_estimated, aggregate_onset_matches
        ),
        "midi_to_wav_missing_check": {
            **note_metrics(
                all_reference, all_estimated, aggregate_onset_matches
            ),
            "interpretation": (
                "Reference WAV annotations not recovered by generated MIDI."
            ),
        },
        "onset_offset": note_metrics(
            all_reference, all_estimated, aggregate_offset_matches
        ),
        "per_recording": per_recording,
    }
    (output_dir / "inverse_validation.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--maximum-recordings", type=int, default=6)
    parser.add_argument("--dataset-id")
    args = parser.parse_args()
    report = validate(
        args.artifacts, args.manifest, args.output_dir,
        args.maximum_recordings, args.dataset_id,
    )
    print(json.dumps({
        "dataset_id": report["dataset_id"],
        "recordings": report["recordings"],
        "wav_to_midi_ghost_check": report["wav_to_midi_ghost_check"],
        "midi_to_wav_missing_check": report["midi_to_wav_missing_check"],
        "onset_offset": report["onset_offset"],
    }, indent=2))


if __name__ == "__main__":
    main()
