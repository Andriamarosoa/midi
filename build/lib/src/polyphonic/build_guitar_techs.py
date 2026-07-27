"""Build leakage-safe polyphonic Guitar-TECHS audio and event labels."""

from __future__ import annotations

import argparse
import csv
import json
import re
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf

from src.polyphonic.build_gaps import empty_harmonics, resampled_pcm
from src.polyphonic.dataset_builder import (
    HOP_SIZE,
    MAX_POLYPHONY,
    MIDI_MAX,
    MIDI_MIN,
    ONSET_WIDTH_HOPS,
    SAMPLE_RATE,
    build_frame_labels,
    build_note_tables,
)
from src.v5.external_data import parse_midi_notes


@dataclass(frozen=True)
class GuitarTechsRecording:
    source_id: str
    group_id: str
    player_id: str
    split: str
    capture_id: str
    audio_path: Path
    annotation_path: Path


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def discover_guitar_techs(root: Path) -> list[GuitarTechsRecording]:
    split_by_player = {"P1": "train", "P2": "validation", "P3": "test"}
    recordings: list[GuitarTechsRecording] = []
    for category in sorted(path for path in root.iterdir() if path.is_dir()):
        player = category.name[:2].upper()
        if player not in split_by_player:
            continue
        for annotation in sorted((category / "midi").glob("*.mid")):
            key = annotation.stem.removeprefix("midi_")
            group_id = f"gtech_{_slug(category.name)}_{_slug(key)}"
            for capture_id in ("directinput", "micamp"):
                audio = (
                    category / "audio" / capture_id /
                    f"{capture_id}_{key}.wav"
                )
                if not audio.is_file():
                    raise FileNotFoundError(audio)
                recordings.append(GuitarTechsRecording(
                    source_id=f"{group_id}_{capture_id}",
                    group_id=group_id,
                    player_id=f"gtech_{player.lower()}",
                    split=split_by_player[player],
                    capture_id=capture_id,
                    audio_path=audio,
                    annotation_path=annotation,
                ))
    return recordings


def build_guitar_techs_dataset(
    data_root: Path,
    output_root: Path,
) -> dict[str, object]:
    recordings = discover_guitar_techs(data_root / "Guitar-TECHS")
    if not recordings:
        raise ValueError("No Guitar-TECHS recordings found.")
    output_root.mkdir(parents=True, exist_ok=True)
    audio_root = output_root / "audio_44100_mono_int16"
    labels_root = output_root / "labels"
    audio_root.mkdir(exist_ok=True)
    labels_root.mkdir(exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    recording_reports: list[dict[str, object]] = []

    for recording in recordings:
        output_audio = audio_root / f"{recording.source_id}.npy"
        if output_audio.is_file():
            pcm = np.load(output_audio, mmap_mode="r", allow_pickle=False)
            source = sf.info(recording.audio_path)
            audio_info = {
                "source_sample_rate": int(source.samplerate),
                "source_channels": int(source.channels),
            }
        else:
            pcm, audio_info = resampled_pcm(recording.audio_path)
            np.save(output_audio, pcm, allow_pickle=False)
        notes = parse_midi_notes(recording.annotation_path)
        frame_count = len(pcm) // HOP_SIZE
        labels = build_frame_labels(notes, frame_count)
        note_count = max((note.note_id for note in notes), default=-1) + 1
        note_tables = build_note_tables(
            notes, frame_count, labels["valid"] > 0
        )
        labels_path = labels_root / f"{recording.source_id}.npz"
        np.savez_compressed(
            labels_path,
            **labels,
            **empty_harmonics(note_count),
            **note_tables,
            sample_rate=np.int32(SAMPLE_RATE),
            hop_size=np.int32(HOP_SIZE),
            audio_frames=np.int64(len(pcm)),
            midi_min=np.int16(MIDI_MIN),
            midi_max=np.int16(MIDI_MAX),
            maximum_polyphony=np.int8(MAX_POLYPHONY),
            onset_width_hops=np.int8(ONSET_WIDTH_HOPS),
        )
        valid = labels["valid"] > 0
        recording_reports.append({
            "source_id": recording.source_id,
            "group_id": recording.group_id,
            "split": recording.split,
            "capture_id": recording.capture_id,
            "frames": frame_count,
            "valid_frames": int(np.sum(valid)),
            "active_frames": int(np.sum(valid & (labels["active_bits"] != 0))),
            "polyphonic_frames": int(np.sum(valid & (labels["polyphony"] > 1))),
            "onset_frames": int(np.sum(valid & (labels["onset_bits"] != 0))),
            "notes": len(notes),
            **audio_info,
        })
        manifest_rows.append({
            "source_id": recording.source_id,
            "dataset_id": f"guitar_techs_poly_{recording.capture_id}",
            "player_id": recording.player_id,
            "group_id": recording.group_id,
            "split": recording.split,
            "audio_path": str(output_audio),
            "audio_member": "",
            "labels_path": str(labels_path),
            "annotation_path": str(recording.annotation_path),
            "harmonic_csv_path": "",
            "capture_id": recording.capture_id,
            "license_id": "CC-BY-4.0",
        })

    manifest_path = output_root / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    split_groups = {
        split: sorted({
            row["group_id"] for row in recording_reports if row["split"] == split
        })
        for split in ("train", "validation", "test")
    }
    leaking_groups = {
        f"{left}_{right}": sorted(set(split_groups[left]) & set(split_groups[right]))
        for left, right in (("train", "validation"), ("train", "test"),
                            ("validation", "test"))
        if set(split_groups[left]) & set(split_groups[right])
    }
    report = {
        "schema_version": 1,
        "manifest": str(manifest_path),
        "recordings": len(recordings),
        "split_recordings": {
            split: sum(row["split"] == split for row in recording_reports)
            for split in ("train", "validation", "test")
        },
        "split_policy": "P1 train, P2 validation, P3 official product test",
        "capture_grouping": "directinput and micamp for one performance never split",
        "leaking_groups": leaking_groups,
        "harmonic_supervision": {
            "available": False,
            "reason": "No per-note partial annotation is supplied for mixed chords.",
            "training_behavior": "Masked; never inferred from neighbouring chord notes.",
        },
        "totals": {
            name: int(sum(int(row[name]) for row in recording_reports))
            for name in (
                "frames", "valid_frames", "active_frames", "polyphonic_frames",
                "onset_frames", "notes",
            )
        },
        "details": recording_reports,
        "passed": not leaking_groups,
    }
    (output_root / "build_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-root", type=Path,
        default=Path("data/dataset/polyphonic_v2_2_guitar_techs"),
    )
    args = parser.parse_args()
    report = build_guitar_techs_dataset(args.data_root, args.output_root)
    print(json.dumps({
        "manifest": report["manifest"],
        "recordings": report["recordings"],
        "split_recordings": report["split_recordings"],
        "harmonic_supervision": report["harmonic_supervision"],
        "totals": report["totals"],
        "passed": report["passed"],
    }, indent=2))


if __name__ == "__main__":
    main()
