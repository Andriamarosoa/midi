"""Build compact continuous labels for causal polyphonic training.

Waveforms stay in their original source (WAV or ZIP member).  The generated
NPZ files contain only frame targets and note-level harmonic measurements, so
we avoid duplicating a 4096-sample window at every 256-sample hop.
"""

from __future__ import annotations

import argparse
import bisect
import csv
import io
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence
from zipfile import ZipFile

import numpy as np
import soundfile as sf

from src.dataset.build_stream_dataset import (
    NoteEvent,
    load_harmonic_csv_supervision,
    load_jams_notes,
)


SAMPLE_RATE = 44_100
HOP_SIZE = 256
MIDI_MIN = 40
MIDI_MAX = 76
MAX_POLYPHONY = 6
MAX_HARMONICS = 20
ONSET_WIDTH_HOPS = 2
HARMONIC_SUPERVISION_SCHEMA_VERSION = 3
HARMONIC_PRESENCE_FLOOR_DB = -60.0
HARMONIC_RELIABILITY_FORMULA = "sqrt(n/(n+1))"


@dataclass(frozen=True)
class GuitarSetBuildItem:
    source_id: str
    player_id: str
    split: str
    annotation_path: Path
    harmonic_csv_path: Path
    audio_archive: Path
    audio_member: str


def _frame_span(
    note: NoteEvent,
    sample_rate: int,
    hop_size: int,
    frame_count: int,
) -> tuple[int, int]:
    start_sample = max(0, int(round(note.start_s * sample_rate)))
    end_sample = max(start_sample, int(round(note.end_s * sample_rate)))
    first = max(0, int(math.ceil(start_sample / hop_size)) - 1)
    last_exclusive = max(first, int(math.ceil(end_sample / hop_size)) - 1)
    return min(first, frame_count), min(last_exclusive, frame_count)


def build_frame_labels(
    notes: Sequence[NoteEvent],
    frame_count: int,
    sample_rate: int = SAMPLE_RATE,
    hop_size: int = HOP_SIZE,
    midi_min: int = MIDI_MIN,
    midi_max: int = MIDI_MAX,
    maximum_polyphony: int = MAX_POLYPHONY,
    onset_width_hops: int = ONSET_WIDTH_HOPS,
) -> dict[str, np.ndarray]:
    if midi_max - midi_min + 1 > 64:
        raise ValueError("The compact bit-mask supports at most 64 pitches.")
    if frame_count < 1 or maximum_polyphony < 1 or onset_width_hops < 1:
        raise ValueError("Invalid frame-label configuration.")

    active_bits = np.zeros(frame_count, dtype=np.uint64)
    onset_bits = np.zeros(frame_count, dtype=np.uint64)
    polyphony = np.zeros(frame_count, dtype=np.uint8)
    outside_scope = np.zeros(frame_count, dtype=np.bool_)
    duplicate_pitch = np.zeros(frame_count, dtype=np.bool_)
    slot_pitch = np.full(
        (frame_count, maximum_polyphony), -1, dtype=np.int8
    )
    slot_note_id = np.full(
        (frame_count, maximum_polyphony), -1, dtype=np.int32
    )
    stored = np.zeros(frame_count, dtype=np.uint8)

    for note in notes:
        first, last = _frame_span(note, sample_rate, hop_size, frame_count)
        if last <= first:
            continue
        span = slice(first, last)
        polyphony[span] = np.minimum(
            polyphony[span].astype(np.uint16) + 1, 255
        ).astype(np.uint8)

        pitch = int(note.pitch_midi)
        if not midi_min <= pitch <= midi_max:
            outside_scope[span] = True
            continue

        class_index = pitch - midi_min
        bit = np.uint64(1) << np.uint64(class_index)
        for frame_index in range(first, last):
            if active_bits[frame_index] & bit:
                duplicate_pitch[frame_index] = True
            else:
                active_bits[frame_index] |= bit
                slot_index = int(stored[frame_index])
                if slot_index < maximum_polyphony:
                    slot_pitch[frame_index, slot_index] = class_index
                    slot_note_id[frame_index, slot_index] = int(note.note_id)
                    stored[frame_index] += 1

        onset_last = min(last, first + onset_width_hops)
        onset_bits[first:onset_last] |= bit

    valid = (
        (polyphony <= maximum_polyphony)
        & ~outside_scope
        & ~duplicate_pitch
    )
    return {
        "active_bits": active_bits,
        "onset_bits": onset_bits,
        "polyphony": polyphony,
        "valid": valid.astype(np.uint8),
        "outside_scope": outside_scope.astype(np.uint8),
        "duplicate_pitch": duplicate_pitch.astype(np.uint8),
        "slot_pitch": slot_pitch,
        "slot_note_id": slot_note_id,
    }


def build_harmonic_tables(
    notes: Sequence[NoteEvent],
    harmonic_csv: Path,
    maximum_harmonics: int = MAX_HARMONICS,
    presence_floor_db: float = HARMONIC_PRESENCE_FLOOR_DB,
) -> dict[str, np.ndarray]:
    (
        metadata,
        present,
        amplitude,
        offset,
        supervised,
        reliability,
        relative_db,
        frames_measured,
    ) = load_harmonic_csv_supervision(
        harmonic_csv,
        maximum_harmonics,
        presence_floor_db=presence_floor_db,
    )
    row_count = max((int(note.note_id) for note in notes), default=-1) + 1
    table_present = np.zeros((row_count, maximum_harmonics), dtype=np.uint8)
    table_amplitude = np.zeros((row_count, maximum_harmonics), dtype=np.float16)
    table_offset = np.zeros((row_count, maximum_harmonics), dtype=np.float16)
    table_supervised = np.zeros(
        (row_count, maximum_harmonics), dtype=np.uint8
    )
    table_reliability = np.zeros(
        (row_count, maximum_harmonics), dtype=np.float16
    )
    table_relative_db = np.full(
        (row_count, maximum_harmonics), np.nan, dtype=np.float32
    )
    table_frames_measured = np.zeros(
        (row_count, maximum_harmonics), dtype=np.int32
    )
    table_valid = np.zeros(row_count, dtype=np.uint8)

    candidates_by_channel: dict[int, list[tuple[float, int]]] = {}
    for csv_note_id, meta in metadata.items():
        candidates_by_channel.setdefault(int(meta["channel"]), []).append(
            (float(meta["start_s"]), int(csv_note_id))
        )
    for candidates in candidates_by_channel.values():
        candidates.sort()

    used_csv_note_ids: set[int] = set()
    for note in notes:
        note_id = int(note.note_id)
        candidates = candidates_by_channel.get(int(note.channel), [])
        if not candidates:
            continue
        starts = [item[0] for item in candidates]
        insertion = bisect.bisect_left(starts, float(note.start_s))
        nearby = candidates[max(0, insertion - 2):insertion + 3]
        ranked: list[tuple[float, float, int]] = []
        for _, csv_note_id in nearby:
            if csv_note_id in used_csv_note_ids:
                continue
            candidate = metadata[csv_note_id]
            expected_pitch = 69.0 + 12.0 * math.log2(
                max(float(candidate["fundamental_hz"]), 1e-8) / 440.0
            )
            timing_error = max(
                abs(float(candidate["start_s"]) - float(note.start_s)),
                abs(float(candidate["end_s"]) - float(note.end_s)),
            )
            pitch_error = abs(expected_pitch - note.pitch_midi)
            ranked.append((timing_error, pitch_error, csv_note_id))
        if not ranked:
            continue
        timing_error, pitch_error, csv_note_id = min(ranked)
        if timing_error > 0.010 or pitch_error > 0.5:
            continue
        meta = metadata[csv_note_id]
        table_present[note_id] = np.asarray(
            present[csv_note_id] > 0.5, np.uint8
        )
        table_amplitude[note_id] = np.asarray(
            amplitude[csv_note_id], np.float16
        )
        table_offset[note_id] = np.asarray(offset[csv_note_id], np.float16)
        table_supervised[note_id] = np.asarray(
            supervised[csv_note_id] > 0.5, np.uint8
        )
        table_reliability[note_id] = np.asarray(
            reliability[csv_note_id], np.float16
        )
        table_relative_db[note_id] = np.asarray(
            relative_db[csv_note_id], np.float32
        )
        table_frames_measured[note_id] = np.asarray(
            frames_measured[csv_note_id], np.int32
        )
        table_valid[note_id] = int(np.any(table_supervised[note_id]))
        used_csv_note_ids.add(csv_note_id)

    return {
        "note_harmonic_present": table_present,
        "note_harmonic_amplitude": table_amplitude,
        "note_harmonic_offset_cents": table_offset,
        "note_harmonic_supervised": table_supervised,
        "note_harmonic_reliability": table_reliability,
        "note_harmonic_relative_db": table_relative_db,
        "note_harmonic_frames_measured": table_frames_measured,
        "note_harmonic_valid": table_valid,
    }


def build_note_tables(
    notes: Sequence[NoteEvent],
    frame_count: int,
    valid_frames: np.ndarray,
) -> dict[str, np.ndarray]:
    row_count = max((int(note.note_id) for note in notes), default=-1) + 1
    pitch = np.full(row_count, -1, dtype=np.int16)
    channel = np.full(row_count, -1, dtype=np.int8)
    start_s = np.zeros(row_count, dtype=np.float32)
    end_s = np.zeros(row_count, dtype=np.float32)
    start_frame = np.full(row_count, -1, dtype=np.int32)
    end_frame = np.full(row_count, -1, dtype=np.int32)
    evaluation_valid = np.zeros(row_count, dtype=np.uint8)
    for note in notes:
        note_id = int(note.note_id)
        first, last = _frame_span(note, SAMPLE_RATE, HOP_SIZE, frame_count)
        pitch[note_id] = int(note.pitch_midi)
        channel[note_id] = int(getattr(note, "channel", -1))
        start_s[note_id] = float(note.start_s)
        end_s[note_id] = float(note.end_s)
        start_frame[note_id] = first
        end_frame[note_id] = last
        evaluation_valid[note_id] = int(
            MIDI_MIN <= note.pitch_midi <= MIDI_MAX
            and last > first
            and first < len(valid_frames)
            and bool(valid_frames[first])
        )
    return {
        "note_pitch_midi": pitch,
        "note_channel": channel,
        "note_start_s": start_s,
        "note_end_s": end_s,
        "note_start_frame": start_frame,
        "note_end_frame": end_frame,
        "note_evaluation_valid": evaluation_valid,
    }


def _archive_audio_members(archive_path: Path) -> dict[str, str]:
    with ZipFile(archive_path) as archive:
        return {
            Path(member).stem.removesuffix("_mix"): member
            for member in archive.namelist()
            if member.lower().endswith("_mix.wav")
        }


def discover_guitarset(data_root: Path) -> list[GuitarSetBuildItem]:
    guitarset = data_root / "GuitarSet"
    archive = guitarset / "audio_mono-pickup_mix.zip"
    members = _archive_audio_members(archive)
    split_by_player = {
        **{f"{player:02d}": "train" for player in range(4)},
        "04": "validation",
        "05": "test",
    }
    items: list[GuitarSetBuildItem] = []
    for source_id, member in sorted(members.items()):
        annotation = guitarset / "annotation" / f"{source_id}.jams"
        harmonic_csv = data_root / "processed" / f"{source_id}_hex_cln.csv"
        if not annotation.is_file() or not harmonic_csv.is_file():
            raise FileNotFoundError(f"Missing GuitarSet labels for {source_id}")
        player = source_id[:2]
        items.append(GuitarSetBuildItem(
            source_id=source_id,
            player_id=player,
            split=split_by_player[player],
            annotation_path=annotation,
            harmonic_csv_path=harmonic_csv,
            audio_archive=archive,
            audio_member=member,
        ))
    return items


def _audio_info(archive: ZipFile, member: str) -> tuple[int, int, int]:
    payload = archive.read(member)
    with sf.SoundFile(io.BytesIO(payload)) as audio:
        return int(audio.frames), int(audio.samplerate), int(audio.channels)


def build_guitarset_dataset(
    data_root: Path,
    output_root: Path,
) -> dict[str, object]:
    output_root.mkdir(parents=True, exist_ok=True)
    labels_root = output_root / "labels"
    labels_root.mkdir(parents=True, exist_ok=True)
    manifest_path = output_root / "manifest.csv"
    rows: list[dict[str, object]] = []
    report_rows: list[dict[str, object]] = []
    items = discover_guitarset(data_root)

    with ZipFile(items[0].audio_archive) as archive:
        for item in items:
            audio_frames, sample_rate, channels = _audio_info(
                archive, item.audio_member
            )
            if sample_rate != SAMPLE_RATE or channels != 1:
                raise ValueError(
                    f"{item.source_id}: expected mono {SAMPLE_RATE} Hz, "
                    f"got {channels} channel(s) at {sample_rate} Hz"
                )
            frame_count = audio_frames // HOP_SIZE
            notes = load_jams_notes(item.annotation_path)
            labels = build_frame_labels(notes, frame_count)
            harmonics = build_harmonic_tables(notes, item.harmonic_csv_path)
            note_tables = build_note_tables(
                notes, frame_count, labels["valid"] > 0
            )
            labels_path = labels_root / f"{item.source_id}.npz"
            np.savez_compressed(
                labels_path,
                **labels,
                **harmonics,
                **note_tables,
                sample_rate=np.int32(sample_rate),
                hop_size=np.int32(HOP_SIZE),
                audio_frames=np.int64(audio_frames),
                midi_min=np.int16(MIDI_MIN),
                midi_max=np.int16(MIDI_MAX),
                maximum_polyphony=np.int8(MAX_POLYPHONY),
                onset_width_hops=np.int8(ONSET_WIDTH_HOPS),
                harmonic_supervision_schema_version=np.int8(
                    HARMONIC_SUPERVISION_SCHEMA_VERSION
                ),
                harmonic_presence_floor_db=np.float32(
                    HARMONIC_PRESENCE_FLOOR_DB
                ),
                harmonic_reliability_formula=np.asarray(
                    HARMONIC_RELIABILITY_FORMULA
                ),
            )
            valid = labels["valid"] > 0
            active = labels["active_bits"] != 0
            onset = labels["onset_bits"] != 0
            report_rows.append({
                "source_id": item.source_id,
                "split": item.split,
                "frames": frame_count,
                "valid_frames": int(np.sum(valid)),
                "invalid_frames": int(np.sum(~valid)),
                "active_frames": int(np.sum(valid & active)),
                "onset_frames": int(np.sum(valid & onset)),
                "polyphonic_frames": int(np.sum(valid & (labels["polyphony"] > 1))),
                "outside_scope_frames": int(np.sum(labels["outside_scope"])),
                "over_six_frames": int(np.sum(labels["polyphony"] > MAX_POLYPHONY)),
                "duplicate_pitch_frames": int(np.sum(labels["duplicate_pitch"])),
                "notes": len(notes),
                "notes_with_harmonics": int(np.sum(harmonics["note_harmonic_valid"])),
            })
            rows.append({
                "source_id": item.source_id,
                "dataset_id": "guitarset_poly_mix",
                "player_id": item.player_id,
                "group_id": f"guitarset_{item.source_id}",
                "split": item.split,
                "audio_path": str(item.audio_archive),
                "audio_member": item.audio_member,
                "labels_path": str(labels_path),
                "annotation_path": str(item.annotation_path),
                "harmonic_csv_path": str(item.harmonic_csv_path),
                "capture_id": "mono_pickup_mix",
                "license_id": "GuitarSet",
            })

    fieldnames = list(rows[0])
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    totals = {
        key: int(sum(int(row[key]) for row in report_rows))
        for key in (
            "frames", "valid_frames", "invalid_frames", "active_frames",
            "onset_frames", "polyphonic_frames", "outside_scope_frames",
            "over_six_frames", "duplicate_pitch_frames", "notes",
            "notes_with_harmonics",
        )
    }
    report = {
        "schema_version": 1,
        "dataset_id": "guitarset_poly_mix",
        "configuration": {
            "sample_rate": SAMPLE_RATE,
            "hop_size": HOP_SIZE,
            "midi_min": MIDI_MIN,
            "midi_max": MIDI_MAX,
            "maximum_polyphony": MAX_POLYPHONY,
            "maximum_harmonics": MAX_HARMONICS,
            "onset_width_hops": ONSET_WIDTH_HOPS,
            "harmonic_supervision_schema_version": (
                HARMONIC_SUPERVISION_SCHEMA_VERSION
            ),
            "harmonic_presence_floor_db": HARMONIC_PRESENCE_FLOOR_DB,
            "harmonic_reliability_formula": HARMONIC_RELIABILITY_FORMULA,
        },
        "manifest": str(manifest_path),
        "totals": totals,
        "recordings": report_rows,
    }
    (output_root / "build_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=Path("data"))
    parser.add_argument(
        "--output-root",
        type=Path,
        default=Path("data/processed/polyphonic_v2_0"),
    )
    args = parser.parse_args()
    report = build_guitarset_dataset(args.data_root, args.output_root)
    print(json.dumps({
        "manifest": report["manifest"],
        "configuration": report["configuration"],
        "totals": report["totals"],
    }, indent=2))


if __name__ == "__main__":
    main()
