"""Validate the exported WAV-to-MIDI product in both note-match directions."""

from __future__ import annotations

import argparse
import json
import math
import tempfile
from collections import Counter
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


HARMONIC_INTERVALS = {12, 19, 24, 28, 31, 36}


def _spectral_support_ratio(
    waveform: np.ndarray,
    end_sample: int,
    pitch_midi: int,
    sample_rate: int,
    midi_min: int = 40,
    midi_max: int = 76,
) -> float:
    end = min(max(int(end_sample), 0), len(waveform))
    start = max(0, end - 4096)
    frame = np.zeros(4096, np.float64)
    values = np.asarray(waveform[start:end], np.float64)
    if len(values):
        frame[-len(values):] = values
    frame -= float(np.mean(frame))
    magnitude = np.abs(np.fft.rfft(frame * np.hanning(len(frame))))
    hz_per_bin = sample_rate / float(len(frame))

    def score(midi: int) -> float:
        frequency = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        center = int(round(frequency / hz_per_bin))
        low = max(0, center - 1)
        high = min(len(magnitude), center + 2)
        return float(np.max(magnitude[low:high])) if high > low else 0.0

    denominator = max(
        max(score(midi) for midi in range(midi_min, midi_max + 1)), 1e-12
    )
    return score(pitch_midi) / denominator


def _ratio_summary(values: list[float]) -> dict[str, float | int]:
    array = np.asarray(values, np.float64)
    if not len(array):
        return {"count": 0, "mean": 0.0, "median": 0.0, "p10": 0.0}
    return {
        "count": int(len(array)),
        "mean": float(np.mean(array)),
        "median": float(np.median(array)),
        "p10": float(np.percentile(array, 10)),
    }


def spectral_inverse_diagnostics(
    waveform: np.ndarray,
    sample_rate: int,
    hop_size: int,
    reference: list[NoteInterval],
    estimated: list[NoteInterval],
    onset_matches: list[tuple[int, int]],
) -> tuple[dict[str, object], list[float], list[float]]:
    """Check both generated->WAV support and WAV->generated coverage.

    The spectral ratios are diagnostics only. Aligned dataset annotations stay
    the primary judge, and the short post-onset probes add no live latency.
    """
    matched_reference = {reference_index for reference_index, _ in onset_matches}
    matched_estimated = {estimated_index for _, estimated_index in onset_matches}

    def note_ratio(note: NoteInterval) -> float:
        onset_sample = int(round(note.start_s * sample_rate))
        return max(
            _spectral_support_ratio(
                waveform, onset_sample + offset * hop_size,
                note.pitch, sample_rate,
            )
            for offset in (0, 1, 2, 4)
        )

    classes: Counter[str] = Counter()
    generated_ratios: list[float] = []
    suspect_examples: list[dict[str, object]] = []
    for index, note in enumerate(estimated):
        ratio = note_ratio(note)
        generated_ratios.append(ratio)
        active_reference = [
            truth.pitch for truth in reference
            if truth.start_s <= note.start_s < truth.end_s
        ]
        harmonic_suspect = any(
            note.pitch - pitch in HARMONIC_INTERVALS
            for pitch in active_reference
        )
        if index in matched_estimated:
            classification = "annotation_supported"
        elif ratio >= 0.25:
            classification = "spectrally_supported_unmatched"
        elif ratio >= 0.10:
            classification = "weak"
        elif harmonic_suspect:
            classification = "harmonic_suspect"
        else:
            classification = "unsupported"
        classes[classification] += 1
        if classification in {"harmonic_suspect", "unsupported"}:
            suspect_examples.append({
                "pitch": note.pitch,
                "start_s": note.start_s,
                "duration_ms": 1000.0 * (note.end_s - note.start_s),
                "spectral_support_ratio": ratio,
                "classification": classification,
            })

    missing = [
        note for index, note in enumerate(reference)
        if index not in matched_reference
    ]
    missing_ratios = [note_ratio(note) for note in missing]
    return {
        "policy": (
            "Aligned annotations are primary; causal 4096-sample FFT probes at "
            "0/1/2/4 hops after onset are an independent diagnostic."
        ),
        "generated_to_wav": {
            "notes": len(estimated),
            "class_counts": dict(sorted(classes.items())),
            "spectral_ratio": _ratio_summary(generated_ratios),
            "suspect_examples": suspect_examples[:20],
        },
        "wav_to_generated": {
            "missing_annotation_notes": len(missing),
            "spectrally_strong_missing": int(np.sum(
                np.asarray(missing_ratios) >= 0.25
            )),
            "spectral_ratio": _ratio_summary(missing_ratios),
        },
        "latency_impact": (
            "Offline diagnostic only; zero added live algorithmic latency."
        ),
    }, generated_ratios, missing_ratios


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
    excluded_group_ids: set[str] | None = None,
) -> list[ManifestItem]:
    if maximum_recordings < 1:
        raise ValueError("maximum_recordings must be positive.")
    excluded = set(excluded_group_ids or ())
    test_items = [
        item for item in items
        if item.split == "test" and item.group_id not in excluded
    ]
    by_dataset: dict[str, list[ManifestItem]] = {}
    for item in test_items:
        by_dataset.setdefault(item.dataset_id, []).append(item)
    for rows in by_dataset.values():
        rows.sort(
            key=lambda item: (score(item), item.source_id), reverse=True,
        )
    target = min(maximum_recordings, len(test_items))
    selected: list[ManifestItem] = []
    used_groups: set[str] = set()
    while len(selected) < target:
        progressed = False
        for dataset_id in sorted(by_dataset):
            rows = by_dataset[dataset_id]
            candidate_index = next(
                (
                    index for index, item in enumerate(rows)
                    if item.group_id not in used_groups
                ),
                None,
            )
            if candidate_index is None:
                continue
            item = rows.pop(candidate_index)
            selected.append(item)
            used_groups.add(item.group_id)
            progressed = True
            if len(selected) == target:
                break
        if not progressed:
            break
    if len(selected) < target:
        raise ValueError(
            "Not enough distinct, uncontaminated test groups for evaluation."
        )
    return selected


def validate(
    artifacts: Path,
    manifest: Path,
    output_dir: Path,
    maximum_recordings: int = 6,
    dataset_id: str | None = None,
    excluded_group_ids: set[str] | None = None,
) -> dict[str, object]:
    bundle = PolyphonicBundle(artifacts)
    if Path(str(bundle.metadata.get("source_checkpoint", ""))).name != "selected.keras":
        raise ValueError(
            "Inverse locked-test validation requires a validation-selected checkpoint."
        )
    items = load_manifest(manifest)
    if dataset_id is not None:
        items = [item for item in items if item.dataset_id == dataset_id]
    selected = select_held_out_recordings(
        items, maximum_recordings,
        excluded_group_ids=excluded_group_ids,
    )
    if not selected:
        raise ValueError("No held-out test recording matched the request.")
    output_dir.mkdir(parents=True, exist_ok=True)
    all_reference: list[NoteInterval] = []
    all_estimated: list[NoteInterval] = []
    per_recording: list[dict[str, object]] = []
    aggregate_spectral_classes: Counter[str] = Counter()
    aggregate_generated_ratios: list[float] = []
    aggregate_missing_ratios: list[float] = []
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
                sf.write(wav, waveform, corpus.sample_rate, subtype="FLOAT")
                midi = output_dir / f"{item.source_id}.mid"
                product_report = transcribe(wav, midi, artifacts, 0, 0)
                product_report["input_wav"] = str(item.audio_path)
                product_report["input_audio_member"] = item.audio_member
                product_report["validation_pcm_reencode"] = "FLOAT"
            estimated = _estimated_notes(midi)
        finally:
            corpus.close()
        onset_matches = match_notes(reference, estimated)
        offset_matches = match_notes(reference, estimated, require_offset=True)
        spectral, generated_ratios, missing_ratios = spectral_inverse_diagnostics(
            waveform, corpus.sample_rate, corpus.hop_size,
            reference, estimated, onset_matches,
        )
        aggregate_spectral_classes.update(
            spectral["generated_to_wav"]["class_counts"]
        )
        aggregate_generated_ratios.extend(generated_ratios)
        aggregate_missing_ratios.extend(missing_ratios)
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
            "spectral_inverse": spectral,
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
        "selection_policy": (
            "Dataset-balanced round-robin; highest valid polyphonic-frame "
            "counts first; distinct groups; contaminated groups excluded."
        ),
        "excluded_group_ids": sorted(excluded_group_ids or ()),
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
        "spectral_inverse": {
            "generated_to_wav": {
                "class_counts": dict(sorted(aggregate_spectral_classes.items())),
                "spectral_ratio": _ratio_summary(aggregate_generated_ratios),
            },
            "wav_to_generated": {
                "missing_annotation_notes": len(aggregate_missing_ratios),
                "spectrally_strong_missing": int(np.sum(
                    np.asarray(aggregate_missing_ratios) >= 0.25
                )),
                "spectral_ratio": _ratio_summary(aggregate_missing_ratios),
            },
            "latency_impact": (
                "Offline diagnostic only; zero added live algorithmic latency."
            ),
        },
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
    parser.add_argument("--exclusion-report", type=Path)
    args = parser.parse_args()
    excluded_group_ids: set[str] = set()
    if args.exclusion_report:
        exclusion = json.loads(args.exclusion_report.read_text(encoding="utf-8"))
        excluded_group_ids = set(exclusion["groups_to_exclude"])
    report = validate(
        args.artifacts, args.manifest, args.output_dir,
        args.maximum_recordings, args.dataset_id, excluded_group_ids,
    )
    print(json.dumps({
        "dataset_id": report["dataset_id"],
        "recordings": report["recordings"],
        "wav_to_midi_ghost_check": report["wav_to_midi_ghost_check"],
        "midi_to_wav_missing_check": report["midi_to_wav_missing_check"],
        "onset_offset": report["onset_offset"],
        "spectral_inverse": report["spectral_inverse"],
    }, indent=2))


if __name__ == "__main__":
    main()
