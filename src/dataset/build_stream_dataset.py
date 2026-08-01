#!/usr/bin/env python3
"""Build a causal mono streaming dataset V2 from WAV + JAMS + harmonic CSV."""

from __future__ import annotations

import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

import numpy as np
import soundfile as sf

DEFAULT_WINDOWS = (512, 1024, 2048, 4096)
EPSILON = 1e-12


@dataclass(frozen=True)
class NoteEvent:
    note_id: int
    channel: int
    start_s: float
    end_s: float
    pitch_midi: int
    fundamental_hz: float
    detected_attack_time_s: float
    attack_confidence: float


def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((float(midi) - 69.0) / 12.0))


def cents_between(measured_hz: float, expected_hz: float) -> float:
    if measured_hz <= 0.0 or expected_hz <= 0.0:
        return 0.0
    return 1200.0 * math.log2(measured_hz / expected_hz)


def load_jams_notes(jams_path: Path) -> List[NoteEvent]:
    with jams_path.open("r", encoding="utf-8") as handle:
        jam = json.load(handle)

    notes: List[NoteEvent] = []
    note_id = 0

    for annotation in jam.get("annotations", []):
        if str(annotation.get("namespace", "")) != "note_midi":
            continue

        metadata = annotation.get("annotation_metadata") or {}
        try:
            channel = int(metadata.get("data_source", 0))
        except (TypeError, ValueError):
            channel = 0

        for item in annotation.get("data", []):
            start_s = float(item.get("time", 0.0))
            end_s = start_s + float(item.get("duration", 0.0))
            value = item.get("value")

            if isinstance(value, dict):
                midi_value = value.get("midi", value.get("note", value.get("pitch")))
            else:
                midi_value = value

            try:
                pitch_midi = int(round(float(midi_value)))
            except (TypeError, ValueError):
                continue

            if end_s <= start_s:
                continue

            notes.append(
                NoteEvent(
                    note_id=note_id,
                    channel=channel,
                    start_s=start_s,
                    end_s=end_s,
                    pitch_midi=pitch_midi,
                    fundamental_hz=midi_to_hz(pitch_midi),
                    detected_attack_time_s=start_s,
                    attack_confidence=0.0,
                )
            )
            note_id += 1

    return notes


def load_harmonic_csv(csv_path: Path, max_harmonics: int):
    note_meta: Dict[int, Dict[str, float]] = {}
    present: Dict[int, np.ndarray] = {}
    amplitude: Dict[int, np.ndarray] = {}
    offset_cents: Dict[int, np.ndarray] = {}

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "note_id", "channel", "start_s", "end_s", "fundamental_hz",
            "harmonic_number", "expected_hz", "measured_hz", "amplitude",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(f"Colonnes manquantes: {sorted(missing)}")

        for row in reader:
            note_id = int(float(row["note_id"]))
            harmonic_number = int(float(row["harmonic_number"]))
            index = harmonic_number - 1
            if not 0 <= index < max_harmonics:
                continue

            if note_id not in note_meta:
                note_meta[note_id] = {
                    "channel": int(float(row["channel"])),
                    "start_s": float(row["start_s"]),
                    "end_s": float(row["end_s"]),
                    "fundamental_hz": float(row["fundamental_hz"]),
                    "detected_attack_time_s": float(
                        row.get("detected_attack_time_s") or row["start_s"]
                    ),
                    "attack_confidence": float(row.get("attack_confidence") or 0.0),
                }
                present[note_id] = np.zeros(max_harmonics, dtype=np.float32)
                amplitude[note_id] = np.zeros(max_harmonics, dtype=np.float32)
                offset_cents[note_id] = np.zeros(max_harmonics, dtype=np.float32)

            measured_hz = float(row["measured_hz"])
            expected_hz = float(row["expected_hz"])
            amp = max(0.0, float(row["amplitude"]))

            present[note_id][index] = 1.0
            amplitude[note_id][index] = amp
            offset_cents[note_id][index] = cents_between(measured_hz, expected_hz)

    for note_id, values in amplitude.items():
        maximum = float(np.max(values))
        if maximum > EPSILON:
            amplitude[note_id] = values / maximum

    return note_meta, present, amplitude, offset_cents


def load_harmonic_csv_supervision(
    csv_path: Path,
    max_harmonics: int,
    *,
    presence_floor_db: float = -60.0,
):
    """Load explicit harmonic presence, strength, and reliability targets.

    A missing CSV row means supervision is unavailable. A measured row below
    ``presence_floor_db`` is instead an observed absent harmonic and remains a
    valid negative target. ``relative_db`` is retained verbatim and converted
    to a stable per-note linear strength after subtracting the strongest
    supervised partial. This preserves ratios even when a CSV contains values
    above 0 dB. ``frames_measured`` is retained verbatim and supplies the soft
    reliability ``sqrt(n / (n + 1))``.
    """
    if max_harmonics < 1:
        raise ValueError("max_harmonics must be positive")
    if not math.isfinite(presence_floor_db) or presence_floor_db >= 0.0:
        raise ValueError("presence_floor_db must be finite and negative")

    note_meta: Dict[int, Dict[str, float]] = {}
    present: Dict[int, np.ndarray] = {}
    amplitude: Dict[int, np.ndarray] = {}
    offset_cents: Dict[int, np.ndarray] = {}
    supervised: Dict[int, np.ndarray] = {}
    reliability: Dict[int, np.ndarray] = {}
    relative_db_by_note: Dict[int, np.ndarray] = {}
    frames_measured_by_note: Dict[int, np.ndarray] = {}
    seen_rows: set[tuple[int, int]] = set()

    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        required = {
            "note_id", "channel", "start_s", "end_s", "fundamental_hz",
            "harmonic_number", "expected_hz", "measured_hz", "relative_db",
            "frames_measured",
        }
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError(
                "Colonnes de supervision harmonique manquantes: "
                f"{sorted(missing)}"
            )

        for row in reader:
            note_id_value = float(row["note_id"])
            harmonic_number_value = float(row["harmonic_number"])
            if (
                not math.isfinite(note_id_value)
                or not note_id_value.is_integer()
                or note_id_value < 0.0
                or not math.isfinite(harmonic_number_value)
                or not harmonic_number_value.is_integer()
            ):
                raise ValueError("note_id and harmonic_number must be integers")
            note_id = int(note_id_value)
            harmonic_number = int(harmonic_number_value)
            index = harmonic_number - 1
            if not 0 <= index < max_harmonics:
                continue

            row_key = (note_id, harmonic_number)
            if row_key in seen_rows:
                raise ValueError(
                    f"Duplicate harmonic row note_id={note_id} "
                    f"harmonic_number={harmonic_number}"
                )
            seen_rows.add(row_key)

            if note_id not in note_meta:
                note_meta[note_id] = {
                    "channel": int(float(row["channel"])),
                    "start_s": float(row["start_s"]),
                    "end_s": float(row["end_s"]),
                    "fundamental_hz": float(row["fundamental_hz"]),
                    "detected_attack_time_s": float(
                        row.get("detected_attack_time_s") or row["start_s"]
                    ),
                    "attack_confidence": float(
                        row.get("attack_confidence") or 0.0
                    ),
                }
                present[note_id] = np.zeros(max_harmonics, dtype=np.float32)
                amplitude[note_id] = np.zeros(max_harmonics, dtype=np.float32)
                offset_cents[note_id] = np.zeros(
                    max_harmonics, dtype=np.float32
                )
                supervised[note_id] = np.zeros(
                    max_harmonics, dtype=np.float32
                )
                reliability[note_id] = np.zeros(
                    max_harmonics, dtype=np.float32
                )
                relative_db_by_note[note_id] = np.full(
                    max_harmonics, np.nan, dtype=np.float32
                )
                frames_measured_by_note[note_id] = np.zeros(
                    max_harmonics, dtype=np.int32
                )

            relative_db = float(row["relative_db"])
            frames_value = float(row["frames_measured"])
            if (
                not math.isfinite(relative_db)
                or not math.isfinite(frames_value)
                or not frames_value.is_integer()
                or frames_value < 0.0
            ):
                raise ValueError(
                    f"Invalid harmonic supervision for note_id={note_id}, "
                    f"harmonic_number={harmonic_number}"
                )
            frames_measured = int(frames_value)
            relative_db_by_note[note_id][index] = relative_db
            frames_measured_by_note[note_id][index] = frames_measured
            if frames_measured == 0:
                continue

            measured_hz = float(row["measured_hz"])
            expected_hz = float(row["expected_hz"])
            if (
                not math.isfinite(measured_hz)
                or measured_hz <= 0.0
                or not math.isfinite(expected_hz)
                or expected_hz <= 0.0
            ):
                raise ValueError(
                    f"Invalid harmonic frequencies for note_id={note_id}, "
                    f"harmonic_number={harmonic_number}"
                )
            supervised[note_id][index] = 1.0
            reliability[note_id][index] = math.sqrt(
                frames_measured / float(frames_measured + 1)
            )
            present[note_id][index] = float(
                relative_db >= presence_floor_db
            )
            offset_cents[note_id][index] = cents_between(
                measured_hz, expected_hz
            )

    for note_id, supervised_values in supervised.items():
        valid = supervised_values > 0.0
        if not np.any(valid):
            continue
        raw_db = relative_db_by_note[note_id]
        strongest_db = float(np.max(raw_db[valid]))
        amplitude[note_id][valid] = np.power(
            np.float32(10.0),
            (raw_db[valid] - strongest_db) / np.float32(20.0),
            dtype=np.float32,
        )

    return (
        note_meta,
        present,
        amplitude,
        offset_cents,
        supervised,
        reliability,
        relative_db_by_note,
        frames_measured_by_note,
    )


def merge_notes(jams_notes: Sequence[NoteEvent], harmonic_meta) -> List[NoteEvent]:
    merged: List[NoteEvent] = []
    for note in jams_notes:
        meta = harmonic_meta.get(note.note_id)
        if meta is None:
            merged.append(note)
            continue
        merged.append(
            NoteEvent(
                note_id=note.note_id,
                channel=int(meta["channel"]),
                start_s=float(meta["start_s"]),
                end_s=float(meta["end_s"]),
                pitch_midi=note.pitch_midi,
                fundamental_hz=float(meta["fundamental_hz"]),
                detected_attack_time_s=float(meta["detected_attack_time_s"]),
                attack_confidence=float(meta["attack_confidence"]),
            )
        )
    return merged


def choose_attack_time(note: NoteEvent, threshold: float) -> float:
    return note.detected_attack_time_s if note.attack_confidence >= threshold else note.start_s


def causal_window(audio: np.ndarray, end_sample: int, max_window: int) -> np.ndarray:
    output = np.zeros(max_window, dtype=np.float32)
    end_sample = max(0, min(len(audio), int(end_sample)))
    start_sample = max(0, end_sample - max_window)
    count = end_sample - start_sample
    if count:
        output[-count:] = audio[start_sample:end_sample]
    return output


def new_store():
    return {
        "audio": [],
        "visible_window": [],
        "prediction_age_ms": [],
        "attack_age_ms": [],
        "pitch_midi": [],
        "fundamental_hz": [],
        "onset": [],
        "attack_phase": [],
        "release_phase": [],
        "active": [],
        "channel": [],
        "note_id": [],
        "harmonic_present": [],
        "harmonic_amplitude": [],
        "harmonic_offset_cents": [],
    }


def append_example(
    store, waveform, visible_window, age_ms, pitch_midi, fundamental_hz,
    onset, attack_phase, release_phase, active, channel, note_id,
    harmonic_present, harmonic_amplitude, harmonic_offset
):
    store["audio"].append(waveform)
    store["visible_window"].append(np.int32(visible_window))
    store["prediction_age_ms"].append(np.float32(age_ms))
    store["attack_age_ms"].append(np.float32(age_ms))
    store["pitch_midi"].append(np.int16(pitch_midi))
    store["fundamental_hz"].append(np.float32(fundamental_hz))
    store["onset"].append(np.float32(onset))
    store["attack_phase"].append(np.float32(attack_phase))
    store["release_phase"].append(np.float32(release_phase))
    store["active"].append(np.float32(active))
    store["channel"].append(np.int8(channel))
    store["note_id"].append(np.int32(note_id))
    store["harmonic_present"].append(harmonic_present)
    store["harmonic_amplitude"].append(harmonic_amplitude)
    store["harmonic_offset_cents"].append(harmonic_offset)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--jams", type=Path, required=True)
    parser.add_argument("--harmonic-csv", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("data/processed/stream"))
    parser.add_argument("--windows", type=int, nargs="+", default=list(DEFAULT_WINDOWS))
    parser.add_argument("--max-window", type=int, default=4096)
    parser.add_argument("--max-harmonics", type=int, default=20)
    parser.add_argument("--attack-confidence-threshold", type=float, default=0.60)
    parser.add_argument("--sustain-offset-ms", type=float, nargs="+", default=[120.0, 220.0])
    parser.add_argument("--release-offset-ms", type=float, nargs="+", default=[20.0, 50.0])
    parser.add_argument("--silence-per-channel", type=int, default=16)
    parser.add_argument("--silence-guard-ms", type=float, default=80.0)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    windows = tuple(sorted(set(args.windows)))
    if max(windows) > args.max_window:
        parser.error("--max-window doit couvrir toutes les fenêtres")

    audio, sample_rate = sf.read(args.wav, always_2d=True, dtype="float32")
    jams_notes = load_jams_notes(args.jams)
    meta, h_present, h_amplitude, h_offset = load_harmonic_csv(
        args.harmonic_csv, args.max_harmonics
    )
    notes = merge_notes(jams_notes, meta)
    store = new_store()
    zeros = np.zeros(args.max_harmonics, dtype=np.float32)

    for note in notes:
        if not 0 <= note.channel < audio.shape[1]:
            continue

        attack_time = choose_attack_time(note, args.attack_confidence_threshold)
        channel_audio = audio[:, note.channel]

        for index, visible_window in enumerate(windows):
            prediction_time = attack_time + visible_window / sample_rate
            if prediction_time > note.end_s:
                continue

            waveform = causal_window(
                channel_audio,
                int(round(prediction_time * sample_rate)),
                args.max_window,
            )
            append_example(
                store,
                waveform,
                visible_window,
                visible_window / sample_rate * 1000.0,
                note.pitch_midi,
                note.fundamental_hz,
                1.0 if index == 0 else 0.0,
                1.0,
                0.0,
                1.0,
                note.channel,
                note.note_id,
                h_present.get(note.note_id, zeros.copy()),
                h_amplitude.get(note.note_id, zeros.copy()),
                h_offset.get(note.note_id, zeros.copy()),
            )

        for offset_ms in args.sustain_offset_ms:
            prediction_time = attack_time + offset_ms / 1000.0
            if prediction_time >= note.end_s:
                continue

            waveform = causal_window(
                channel_audio,
                int(round(prediction_time * sample_rate)),
                args.max_window,
            )
            append_example(
                store, waveform, args.max_window, offset_ms,
                note.pitch_midi, note.fundamental_hz,
                0.0, 0.0, 0.0, 1.0,
                note.channel, note.note_id,
                h_present.get(note.note_id, zeros.copy()),
                h_amplitude.get(note.note_id, zeros.copy()),
                h_offset.get(note.note_id, zeros.copy()),
            )

        for release_ms in args.release_offset_ms:
            prediction_time = note.end_s + release_ms / 1000.0
            if prediction_time >= audio.shape[0] / sample_rate:
                continue

            waveform = causal_window(
                channel_audio,
                int(round(prediction_time * sample_rate)),
                args.max_window,
            )
            append_example(
                store, waveform, args.max_window, release_ms,
                note.pitch_midi, note.fundamental_hz,
                0.0, 0.0, 1.0, 0.0,
                note.channel, note.note_id,
                h_present.get(note.note_id, zeros.copy()),
                h_amplitude.get(note.note_id, zeros.copy()),
                h_offset.get(note.note_id, zeros.copy()),
            )

    rng = np.random.default_rng(args.seed)
    duration_s = audio.shape[0] / sample_rate
    guard_s = args.silence_guard_ms / 1000.0
    intervals_by_channel: Dict[int, List[Tuple[float, float]]] = {}

    for note in notes:
        intervals_by_channel.setdefault(note.channel, []).append(
            (note.start_s - guard_s, note.end_s + guard_s)
        )

    for channel in range(audio.shape[1]):
        intervals = intervals_by_channel.get(channel, [])
        accepted = 0
        attempts = 0
        while accepted < args.silence_per_channel and attempts < args.silence_per_channel * 100:
            attempts += 1
            prediction_time = float(rng.uniform(args.max_window / sample_rate, duration_s))
            if any(start <= prediction_time <= end for start, end in intervals):
                continue

            waveform = causal_window(
                audio[:, channel],
                int(round(prediction_time * sample_rate)),
                args.max_window,
            )
            append_example(
                store, waveform, args.max_window, -1.0,
                -1, 0.0,
                0.0, 0.0, 0.0, 0.0,
                channel, -1,
                zeros.copy(), zeros.copy(), zeros.copy(),
            )
            accepted += 1

    dataset = {key: np.asarray(values) for key, values in store.items()}
    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_path = args.output_dir / f"{args.wav.stem}.npz"
    np.savez_compressed(output_path, **dataset)

    manifest_path = args.output_dir / "manifest.csv"
    exists = manifest_path.exists()
    with manifest_path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "source_id", "npz_path", "examples", "onsets",
                "attack_phase", "sustain", "release", "silence",
                "sample_rate", "max_window",
            ],
        )
        if not exists:
            writer.writeheader()

        writer.writerow({
            "source_id": args.wav.stem,
            "npz_path": str(output_path),
            "examples": len(dataset["audio"]),
            "onsets": int(np.sum(dataset["onset"] > 0.5)),
            "attack_phase": int(np.sum(dataset["attack_phase"] > 0.5)),
            "sustain": int(np.sum((dataset["active"] > 0.5) & (dataset["attack_phase"] < 0.5))),
            "release": int(np.sum(dataset["release_phase"] > 0.5)),
            "silence": int(np.sum((dataset["active"] < 0.5) & (dataset["release_phase"] < 0.5))),
            "sample_rate": sample_rate,
            "max_window": args.max_window,
        })

    print("Dataset streaming V2 créé")
    print(f"  exemples      : {len(dataset['audio'])}")
    print(f"  onsets        : {int(np.sum(dataset['onset'] > 0.5))}")
    print(f"  attack phase  : {int(np.sum(dataset['attack_phase'] > 0.5))}")
    print(f"  release       : {int(np.sum(dataset['release_phase'] > 0.5))}")
    print(f"  sortie        : {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
