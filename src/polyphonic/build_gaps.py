"""Build GAPS continuous labels and memory-mapped 44.1 kHz mono audio.

GAPS contains mixed polyphonic recordings.  Note-level harmonic targets cannot
be isolated reliably from those mixtures, so their harmonic masks remain zero;
the harmonic head is still supervised by GuitarSet's debleeded string tracks.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from src.polyphonic.dataset_builder import (
    HOP_SIZE,
    MAX_HARMONICS,
    MAX_POLYPHONY,
    MIDI_MAX,
    MIDI_MIN,
    ONSET_WIDTH_HOPS,
    SAMPLE_RATE,
    build_frame_labels,
    build_note_tables,
)
from src.v5.external_data import parse_midi_notes


def assign_splits(
    rows: list[dict[str, str]],
    validation_recordings: int = 30,
    seed: int = 42,
) -> tuple[dict[str, str], dict[str, object]]:
    eligible = [row for row in rows if (row.get("split") or "").strip() in {"train", "test"}]
    official_test = [row for row in eligible if row["split"].strip() == "test"]
    official_train = [row for row in eligible if row["split"].strip() == "train"]

    def group_key(row: dict[str, str]) -> str:
        return (row.get("scorehash") or "").strip() or row["id"]

    test_groups = {group_key(row) for row in official_test}
    train_groups: dict[str, list[dict[str, str]]] = {}
    for row in official_train:
        key = group_key(row)
        if key in test_groups:
            raise ValueError(f"GAPS train/test score leakage: {key}")
        train_groups.setdefault(key, []).append(row)
    ordered_groups = sorted(
        train_groups,
        key=lambda key: hashlib.sha256(f"{seed}:{key}".encode()).hexdigest(),
    )
    validation_groups: set[str] = set()
    selected = 0
    for key in ordered_groups:
        if selected >= validation_recordings:
            break
        validation_groups.add(key)
        selected += len(train_groups[key])

    split_by_id: dict[str, str] = {}
    for row in official_test:
        split_by_id[row["id"]] = "test"
    for row in official_train:
        split_by_id[row["id"]] = (
            "validation" if group_key(row) in validation_groups else "train"
        )
    counts = {
        split: sum(value == split for value in split_by_id.values())
        for split in ("train", "validation", "test")
    }
    return split_by_id, {
        "seed": seed,
        "group_key": "case-sensitive scorehash, falling back to id",
        "counts": counts,
        "validation_groups": sorted(validation_groups),
        "official_test_groups": sorted(test_groups),
        "group_overlap": sorted(validation_groups & test_groups),
        "unassigned_excluded": sum(
            not (row.get("split") or "").strip() for row in rows
        ),
    }


def resampled_pcm(audio_path: Path) -> tuple[np.ndarray, dict[str, int]]:
    audio, source_rate = sf.read(audio_path, dtype="float32", always_2d=True)
    source_channels = int(audio.shape[1])
    mono = np.mean(audio, axis=1, dtype=np.float32)
    if int(source_rate) != SAMPLE_RATE:
        divisor = math.gcd(int(source_rate), SAMPLE_RATE)
        mono = resample_poly(
            mono, SAMPLE_RATE // divisor, int(source_rate) // divisor
        ).astype(np.float32)
    pcm = np.asarray(
        np.round(np.clip(mono, -1.0, 1.0) * 32767.0), dtype=np.int16
    )
    return pcm, {
        "source_sample_rate": int(source_rate),
        "source_channels": source_channels,
    }


def empty_harmonics(note_count: int) -> dict[str, np.ndarray]:
    return {
        "note_harmonic_present": np.zeros((note_count, MAX_HARMONICS), np.uint8),
        "note_harmonic_amplitude": np.zeros((note_count, MAX_HARMONICS), np.float16),
        "note_harmonic_offset_cents": np.zeros((note_count, MAX_HARMONICS), np.float16),
        "note_harmonic_valid": np.zeros(note_count, np.uint8),
    }


def build_gaps_dataset(
    data_root: Path,
    output_root: Path,
    validation_recordings: int = 30,
    seed: int = 42,
) -> dict[str, object]:
    gaps_root = data_root / "GAPS"
    with (gaps_root / "gaps_metadata_with_splits.csv").open(
        "r", encoding="utf-8-sig", newline=""
    ) as handle:
        metadata = list(csv.DictReader(handle))
    split_by_id, split_report = assign_splits(
        metadata, validation_recordings, seed
    )
    output_root.mkdir(parents=True, exist_ok=True)
    audio_root = output_root / "audio_44100_mono_int16"
    labels_root = output_root / "labels"
    audio_root.mkdir(exist_ok=True)
    labels_root.mkdir(exist_ok=True)
    manifest_rows: list[dict[str, object]] = []
    reports: list[dict[str, object]] = []

    for row in metadata:
        source_id = row.get("id", "")
        if source_id not in split_by_id:
            continue
        source_audio = gaps_root.joinpath(*row["audio_path"].replace("\\", "/").split("/"))
        source_midi = gaps_root.joinpath(*row["midi_path"].replace("\\", "/").split("/"))
        output_audio = audio_root / f"{source_id}.npy"
        if output_audio.is_file():
            pcm = np.load(output_audio, mmap_mode="r", allow_pickle=False)
            source_info = sf.info(source_audio)
            audio_info = {
                "source_sample_rate": int(source_info.samplerate),
                "source_channels": int(source_info.channels),
            }
        else:
            pcm, audio_info = resampled_pcm(source_audio)
            np.save(output_audio, pcm, allow_pickle=False)

        notes = parse_midi_notes(source_midi)
        frame_count = len(pcm) // HOP_SIZE
        labels = build_frame_labels(notes, frame_count)
        note_count = max((note.note_id for note in notes), default=-1) + 1
        harmonics = empty_harmonics(note_count)
        note_tables = build_note_tables(notes, frame_count, labels["valid"] > 0)
        labels_path = labels_root / f"{source_id}.npz"
        np.savez_compressed(
            labels_path,
            **labels,
            **harmonics,
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
        reports.append({
            "source_id": source_id,
            "split": split_by_id[source_id],
            "frames": frame_count,
            "valid_frames": int(np.sum(valid)),
            "invalid_frames": int(np.sum(~valid)),
            "active_frames": int(np.sum(valid & (labels["active_bits"] != 0))),
            "polyphonic_frames": int(np.sum(valid & (labels["polyphony"] > 1))),
            "onset_frames": int(np.sum(valid & (labels["onset_bits"] != 0))),
            "outside_scope_frames": int(np.sum(labels["outside_scope"])),
            "over_six_frames": int(np.sum(labels["polyphony"] > MAX_POLYPHONY)),
            "notes": len(notes),
            **audio_info,
        })
        manifest_rows.append({
            "source_id": source_id,
            "dataset_id": "gaps_poly_mix",
            "player_id": (row.get("performer_name") or "gaps_unknown").strip(),
            "group_id": (row.get("scorehash") or source_id).strip(),
            "split": split_by_id[source_id],
            "audio_path": str(output_audio),
            "audio_member": "",
            "labels_path": str(labels_path),
            "annotation_path": str(source_midi),
            "harmonic_csv_path": "",
            "capture_id": "gaps_mixed_downmix",
            "license_id": "MIT",
        })

    manifest_path = output_root / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(manifest_rows[0]))
        writer.writeheader()
        writer.writerows(manifest_rows)
    totals = {
        key: int(sum(int(row[key]) for row in reports))
        for key in (
            "frames", "valid_frames", "invalid_frames", "active_frames",
            "polyphonic_frames", "onset_frames", "outside_scope_frames",
            "over_six_frames", "notes",
        )
    }
    report = {
        "schema_version": 1,
        "dataset_id": "gaps_poly_mix",
        "manifest": str(manifest_path),
        "split": split_report,
        "harmonic_supervision": {
            "available": False,
            "reason": "Mixed polyphonic audio cannot identify per-note partials without source separation.",
            "training_behavior": "Masked; GuitarSet retains full 20-partial supervision.",
        },
        "totals": totals,
        "recordings": reports,
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
        default=Path("data/processed/polyphonic_v2_1_gaps"),
    )
    parser.add_argument("--validation-recordings", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()
    report = build_gaps_dataset(
        args.data_root, args.output_root, args.validation_recordings, args.seed
    )
    print(json.dumps({
        "manifest": report["manifest"],
        "split": report["split"],
        "harmonic_supervision": report["harmonic_supervision"],
        "totals": report["totals"],
    }, indent=2))


if __name__ == "__main__":
    main()
