"""Build a research-only, exercise-grouped polyphonic IDMT corpus."""

from __future__ import annotations

import argparse
import csv
import hashlib
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
from src.v5.external_data import _find_idmt_audio, parse_idmt_notes


@dataclass(frozen=True)
class IdmtRecording:
    source_id: str
    dataset_id: str
    group_id: str
    split: str
    player_id: str
    audio_path: Path
    annotation_path: Path


def _slug(value: str) -> str:
    return re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()


def exercise_group(relative: Path) -> str:
    """Collapse repeated dataset-1 instrument captures of one exercise."""
    dataset = relative.parts[0].lower()
    stem = relative.stem
    if dataset == "dataset1" and stem.startswith("G"):
        fields = stem.split("-")
        exercise = "-".join(fields[:3]) if len(fields) >= 3 else stem
    elif dataset == "dataset1":
        exercise = stem
    else:
        exercise = "/".join(relative.with_suffix("").parts)
    return f"idmt_{dataset}_{_slug(exercise)}"


def split_group(group_id: str, seed: int = 42) -> str:
    value = int(hashlib.sha256(f"{seed}:{group_id}".encode()).hexdigest()[:8], 16)
    bucket = value % 10
    return "train" if bucket < 8 else ("validation" if bucket == 8 else "test")


def discover_idmt(root: Path, seed: int = 42) -> list[IdmtRecording]:
    recordings: list[IdmtRecording] = []
    for annotation in sorted(root.rglob("*.xml")):
        notes = parse_idmt_notes(annotation)
        if not notes:
            continue
        audio = _find_idmt_audio(annotation)
        if audio is None:
            # A few distributed XML files name audio variants that are absent
            # from the archive. They cannot become training examples.
            continue
        relative = annotation.relative_to(root)
        dataset_part = relative.parts[0].lower()
        group_id = exercise_group(relative)
        setup = relative.parts[1] if len(relative.parts) > 1 else dataset_part
        recordings.append(IdmtRecording(
            source_id=f"idmt_{_slug('_'.join(relative.with_suffix('').parts))}",
            dataset_id=f"idmt_poly_{dataset_part}",
            group_id=group_id,
            split=split_group(group_id, seed),
            player_id=f"idmt_{_slug(setup)}",
            audio_path=audio,
            annotation_path=annotation,
        ))
    return recordings


def build_idmt_dataset(
    data_root: Path,
    output_root: Path,
    seed: int = 42,
) -> dict[str, object]:
    root = data_root / "IDMT-SMT-Guitar" / "IDMT-SMT-GUITAR_V2"
    recordings = discover_idmt(root, seed)
    if not recordings:
        raise ValueError("No annotated IDMT recordings found.")
    output_root.mkdir(parents=True, exist_ok=True)
    audio_root = output_root / "audio_44100_mono_int16"
    labels_root = output_root / "labels"
    audio_root.mkdir(exist_ok=True)
    labels_root.mkdir(exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    details: list[dict[str, object]] = []

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
        notes = parse_idmt_notes(recording.annotation_path)
        frame_count = len(pcm) // HOP_SIZE
        labels = build_frame_labels(notes, frame_count)
        note_count = max((note.note_id for note in notes), default=-1) + 1
        note_tables = build_note_tables(notes, frame_count, labels["valid"] > 0)
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
        details.append({
            "source_id": recording.source_id,
            "dataset_id": recording.dataset_id,
            "group_id": recording.group_id,
            "split": recording.split,
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
            "dataset_id": recording.dataset_id,
            "player_id": recording.player_id,
            "group_id": recording.group_id,
            "split": recording.split,
            "audio_path": str(output_audio),
            "audio_member": "",
            "labels_path": str(labels_path),
            "annotation_path": str(recording.annotation_path),
            "harmonic_csv_path": "",
            "capture_id": "idmt_mono_mix",
            "license_id": "CC-BY-NC-ND-4.0",
        })

    manifest_path = output_root / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    groups = {
        split: {row["group_id"] for row in details if row["split"] == split}
        for split in ("train", "validation", "test")
    }
    leaks = sorted(
        (groups["train"] & groups["validation"])
        | (groups["train"] & groups["test"])
        | (groups["validation"] & groups["test"])
    )
    report = {
        "schema_version": 1,
        "manifest": str(manifest_path),
        "recordings": len(recordings),
        "annotations_excluded_without_usable_pair": (
            len(list(root.rglob("*.xml"))) - len(recordings)
        ),
        "split_recordings": {
            split: sum(row["split"] == split for row in details)
            for split in ("train", "validation", "test")
        },
        "split_policy": (
            "Deterministic 80/10/10 hash over exercise groups; repeated dataset-1 "
            "instrument captures share one group."
        ),
        "leaking_groups": leaks,
        "license_scope": (
            "Research/non-commercial ablation only (CC-BY-NC-ND-4.0); "
            "not enabled in the deployable product configuration."
        ),
        "harmonic_supervision": {
            "available": False,
            "reason": "XML supplies note events, not per-note partial measurements.",
            "training_behavior": "Masked.",
        },
        "totals": {
            name: int(sum(int(row[name]) for row in details))
            for name in (
                "frames", "valid_frames", "active_frames", "polyphonic_frames",
                "onset_frames", "notes",
            )
        },
        "details": details,
        "passed": not leaks,
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
        default=Path("data/processed/polyphonic_v2_2_idmt_research"),
    )
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = build_idmt_dataset(args.data_root, args.output_root, args.seed)
    print(json.dumps({
        "manifest": report["manifest"],
        "recordings": report["recordings"],
        "split_recordings": report["split_recordings"],
        "license_scope": report["license_scope"],
        "totals": report["totals"],
        "passed": report["passed"],
    }, indent=2))


if __name__ == "__main__":
    main()
