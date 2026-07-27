"""Build the causal V5.2 mono dataset from GuitarSet, IDMT and Guitar-TECHS.

Only examples with exactly one annotated active note at prediction time are
kept. This preserves the single-softmax V5 contract while using a real mono
mix that matches the future live input more closely.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import re
import struct
import xml.etree.ElementTree as ET
import zlib
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from zipfile import ZipFile

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from src.dataset.build_stream_dataset import load_harmonic_csv
from src.process.harmonic import measure_note_harmonics


DEFAULT_WINDOWS = (512, 1024, 2048, 4096)
DEFAULT_SUSTAIN_MS = (120.0, 220.0)
DEFAULT_RELEASE_MS = (20.0, 50.0)
MAX_HARMONICS = 20
HARMONIC_FRAME_SIZE = 4096
HARMONIC_HOP_SIZE = 1024
HARMONIC_SEARCH_CENTS = 35.0
MIN_HARMONIC_SAMPLES = 64
SILENCE_EPSILON = 1e-8
MAX_FUNDAMENTAL_ALIGNMENT_CENTS = 50.0


@dataclass(frozen=True)
class NoteEvent:
    note_id: int
    start_s: float
    end_s: float
    pitch_midi: int
    expression: str = ""


@dataclass(frozen=True)
class SourceRecording:
    dataset_id: str
    source_id: str
    audio_path: Path
    annotation_path: Path
    annotation_format: str
    player_id: str
    group_id: str
    capture_id: str
    split: str
    license_id: str
    audio_member: str = ""
    harmonic_csv_path: Path | None = None


def _slug(value: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if not clean:
        raise ValueError(f"Identifiant vide après normalisation: {value!r}")
    return clean


def midi_to_hz(midi: int) -> float:
    return 440.0 * (2.0 ** ((int(midi) - 69) / 12.0))


def _read_vlq(data: bytes, index: int) -> tuple[int, int]:
    value = 0
    while True:
        if index >= len(data):
            raise ValueError("VLQ MIDI tronqué.")
        byte = data[index]
        index += 1
        value = (value << 7) | (byte & 0x7F)
        if not byte & 0x80:
            return value, index


def parse_midi_notes(path: str | Path) -> list[NoteEvent]:
    """Parse note events from a Standard MIDI File without extra dependency."""
    path = Path(path)
    data = path.read_bytes()
    if data[:4] != b"MThd" or len(data) < 14:
        raise ValueError(f"En-tête MIDI invalide: {path}")

    header_size = int.from_bytes(data[4:8], "big")
    _, track_count, division = struct.unpack(">HHH", data[8:14])
    if division & 0x8000:
        raise ValueError(f"Division SMPTE MIDI non prise en charge: {path}")

    position = 8 + header_size
    raw_notes: list[tuple[int, int, int]] = []
    tempo_by_tick: dict[int, int] = {0: 500_000}

    for _ in range(track_count):
        if data[position:position + 4] != b"MTrk":
            raise ValueError(f"Chunk MTrk absent: {path}")
        track_size = int.from_bytes(data[position + 4:position + 8], "big")
        track = data[position + 8:position + 8 + track_size]
        position += 8 + track_size

        index = 0
        tick = 0
        running_status: int | None = None
        active: dict[tuple[int, int], list[int]] = defaultdict(list)

        while index < len(track):
            delta, index = _read_vlq(track, index)
            tick += delta
            status = track[index]
            if status < 0x80:
                if running_status is None:
                    raise ValueError(f"Running status MIDI invalide: {path}")
                status = running_status
            else:
                index += 1
                if status < 0xF0:
                    running_status = status

            if status == 0xFF:
                meta_type = track[index]
                index += 1
                length, index = _read_vlq(track, index)
                payload = track[index:index + length]
                index += length
                if meta_type == 0x51 and length == 3:
                    tempo_by_tick[tick] = int.from_bytes(payload, "big")
                continue

            if status in (0xF0, 0xF7):
                length, index = _read_vlq(track, index)
                index += length
                running_status = None
                continue

            event_type = status & 0xF0
            channel = status & 0x0F
            if event_type in (0xC0, 0xD0):
                index += 1
                continue

            first = track[index]
            second = track[index + 1]
            index += 2
            key = (channel, first)
            if event_type == 0x90 and second > 0:
                active[key].append(tick)
            elif event_type == 0x80 or (event_type == 0x90 and second == 0):
                if active[key]:
                    raw_notes.append((active[key].pop(0), tick, first))

    tempo_changes = sorted(tempo_by_tick.items())

    def tick_to_seconds(target_tick: int) -> float:
        seconds = 0.0
        previous_tick = 0
        tempo = 500_000
        for change_tick, new_tempo in tempo_changes:
            if change_tick > target_tick:
                break
            seconds += (change_tick - previous_tick) * tempo / division / 1_000_000.0
            previous_tick = change_tick
            tempo = new_tempo
        return seconds + (target_tick - previous_tick) * tempo / division / 1_000_000.0

    converted = [
        (tick_to_seconds(start), tick_to_seconds(end), pitch)
        for start, end, pitch in raw_notes
        if end > start
    ]
    converted.sort(key=lambda item: (item[0], item[2], item[1]))
    return [
        NoteEvent(note_id=i, start_s=start, end_s=end, pitch_midi=pitch)
        for i, (start, end, pitch) in enumerate(converted)
    ]


def parse_idmt_notes(path: str | Path) -> list[NoteEvent]:
    root = ET.parse(path).getroot()
    notes: list[NoteEvent] = []
    for event in root.findall(".//event"):
        try:
            pitch = int(round(float(event.findtext("pitch", ""))))
            start = float(event.findtext("onsetSec", ""))
            end = float(event.findtext("offsetSec", ""))
        except ValueError:
            continue
        if end <= start:
            continue
        notes.append(
            NoteEvent(
                note_id=len(notes),
                start_s=start,
                end_s=end,
                pitch_midi=pitch,
                expression=event.findtext("expressionStyle", ""),
            )
        )
    return notes


def parse_guitarset_notes(path: str | Path) -> list[NoteEvent]:
    content = json.loads(Path(path).read_text(encoding="utf-8"))
    notes: list[NoteEvent] = []
    for annotation in content.get("annotations", []):
        if annotation.get("namespace") != "note_midi":
            continue
        for item in annotation.get("data", []):
            value = item.get("value")
            if isinstance(value, dict):
                value = value.get("midi", value.get("pitch", value.get("note")))
            try:
                start = float(item["time"])
                end = start + float(item["duration"])
                pitch = int(round(float(value)))
            except (KeyError, TypeError, ValueError):
                continue
            if end > start:
                notes.append(NoteEvent(len(notes), start, end, pitch))
    notes.sort(key=lambda item: (item.start_s, item.pitch_midi, item.end_s))
    return [
        NoteEvent(i, note.start_s, note.end_s, note.pitch_midi, note.expression)
        for i, note in enumerate(notes)
    ]


def parse_recording_notes(recording: SourceRecording) -> list[NoteEvent]:
    if recording.annotation_format == "midi":
        return parse_midi_notes(recording.annotation_path)
    if recording.annotation_format == "idmt_xml":
        return parse_idmt_notes(recording.annotation_path)
    if recording.annotation_format == "guitarset_jams":
        return parse_guitarset_notes(recording.annotation_path)
    raise ValueError(f"Format d'annotation inconnu: {recording.annotation_format}")


def maximum_polyphony(notes: Iterable[NoteEvent]) -> int:
    timeline: list[tuple[float, int]] = []
    for note in notes:
        timeline.extend(((note.start_s, 1), (note.end_s, -1)))
    current = 0
    maximum = 0
    for _, change in sorted(timeline, key=lambda item: (item[0], item[1])):
        current += change
        maximum = max(maximum, current)
    return maximum


def _find_idmt_audio(annotation_path: Path) -> Path | None:
    root = ET.parse(annotation_path).getroot()
    declared = (root.findtext(".//audioFileName") or "").replace("\\", "/")
    declared = declared.rsplit("/", 1)[-1]
    parent = annotation_path.parent
    while parent != parent.parent:
        audio_dir = parent / "audio"
        if audio_dir.is_dir():
            candidates = [audio_dir / f"{annotation_path.stem}.wav"]
            if declared:
                candidates.insert(0, audio_dir / declared)
            return next((item for item in candidates if item.is_file()), None)
        parent = parent.parent
    return None


def discover_idmt(root: str | Path) -> list[SourceRecording]:
    root = Path(root)
    recordings: list[SourceRecording] = []

    dataset1 = root / "dataset1"
    for setup in sorted(item for item in dataset1.iterdir() if item.is_dir()):
        if "chords" in setup.name.lower():
            continue
        for annotation in sorted((setup / "annotation").glob("*.xml")):
            audio = _find_idmt_audio(annotation)
            if audio is None:
                raise FileNotFoundError(f"Audio IDMT absent pour {annotation}")
            setup_id = _slug(setup.name)
            recordings.append(SourceRecording(
                dataset_id="idmt_d1_mono",
                source_id=f"idmt_d1_{setup_id}_{_slug(annotation.stem)}",
                audio_path=audio,
                annotation_path=annotation,
                annotation_format="idmt_xml",
                player_id=f"idmt_d1_{setup_id}",
                group_id=f"idmt_d1_session_{setup_id}",
                capture_id="mono",
                split="train",
                license_id="CC-BY-NC-ND-4.0",
            ))

    dataset2 = root / "dataset2" / "annotation"
    for annotation in sorted(dataset2.glob("*.xml")):
        notes = parse_idmt_notes(annotation)
        if not notes or maximum_polyphony(notes) > 1:
            continue
        if any(note.expression != "NO" for note in notes):
            continue
        audio = _find_idmt_audio(annotation)
        if audio is None:
            raise FileNotFoundError(f"Audio IDMT absent pour {annotation}")
        recordings.append(SourceRecording(
            dataset_id="idmt_d2_mono",
            source_id=f"idmt_d2_{_slug(annotation.stem)}",
            audio_path=audio,
            annotation_path=annotation,
            annotation_format="idmt_xml",
            player_id="idmt_christian_kehling",
            group_id="idmt_d2_christian_kehling",
            capture_id="mono",
            split="train",
            license_id="CC-BY-NC-ND-4.0",
        ))
    return recordings


def discover_guitar_techs(root: str | Path) -> list[SourceRecording]:
    root = Path(root)
    recordings: list[SourceRecording] = []
    categories = (
        "P1_singlenotes", "P1_scales",
        "P2_singlenotes", "P2_scales",
    )
    for category in categories:
        category_root = root / category
        player = category[:2].lower()
        for midi in sorted((category_root / "midi").glob("*.mid")):
            key = midi.stem.removeprefix("midi_")
            group_id = f"gtech_{player}_{_slug(category)}_{_slug(key)}"
            for capture in ("directinput", "micamp"):
                audio = category_root / "audio" / capture / f"{capture}_{key}.wav"
                if not audio.is_file():
                    raise FileNotFoundError(f"Capture Guitar-TECHS absente: {audio}")
                recordings.append(SourceRecording(
                    dataset_id="guitar_techs_mono",
                    source_id=f"{group_id}_{capture}",
                    audio_path=audio,
                    annotation_path=midi,
                    annotation_format="midi",
                    player_id=f"gtech_{player}",
                    group_id=group_id,
                    capture_id=capture,
                    split="train",
                    license_id="CC-BY-4.0",
                ))
    return recordings


def discover_guitarset(root: str | Path) -> list[SourceRecording]:
    root = Path(root)
    annotation_root = root / "annotation"
    split_by_player = {
        **{f"{value:02d}": "train" for value in range(4)},
        "04": "validation",
        "05": "test",
    }
    mono_archive = root / "audio_mono-pickup_mix.zip"
    audio_sources: list[tuple[str, Path, str, str]] = []
    if mono_archive.is_file():
        with ZipFile(mono_archive) as archive:
            for member in archive.namelist():
                if not member.lower().endswith("_mix.wav"):
                    continue
                original_id = Path(member).stem.removesuffix("_mix")
                audio_sources.append(
                    (original_id, mono_archive, member, "mono_pickup_mix")
                )
    else:
        audio_root = root / "audio_hex-pickup_debleeded"
        for audio in audio_root.glob("*_hex_cln.wav"):
            original_id = audio.stem.removesuffix("_hex_cln")
            audio_sources.append(
                (original_id, audio, "", "debleeded_mean_mix")
            )

    recordings: list[SourceRecording] = []
    for original_id, audio, audio_member, capture_id in sorted(audio_sources):
        annotation = annotation_root / f"{original_id}.jams"
        if not annotation.is_file():
            raise FileNotFoundError(f"JAMS GuitarSet absent pour {audio}")
        player = original_id[:2]
        if player not in split_by_player:
            raise ValueError(f"Joueur GuitarSet inconnu: {original_id}")
        recordings.append(SourceRecording(
            dataset_id="guitarset_mono_mix",
            source_id=f"gsmono_{_slug(original_id)}",
            audio_path=audio,
            annotation_path=annotation,
            annotation_format="guitarset_jams",
            player_id=player,
            group_id=f"guitarset_{_slug(original_id)}",
            capture_id=capture_id,
            split=split_by_player[player],
            license_id="GuitarSet",
            audio_member=audio_member,
            harmonic_csv_path=(
                root.parent / "processed" / f"{original_id}_hex_cln.csv"
            ),
        ))
    return recordings


def causal_window(waveform: np.ndarray, end_sample: int, max_window: int) -> np.ndarray:
    output = np.zeros(max_window, dtype=np.float32)
    end_sample = max(0, min(len(waveform), int(end_sample)))
    start_sample = max(0, end_sample - max_window)
    count = end_sample - start_sample
    if count:
        output[-count:] = waveform[start_sample:end_sample]
    return output


def read_recording_audio(recording: SourceRecording) -> tuple[np.ndarray, int]:
    if not recording.audio_member:
        return sf.read(recording.audio_path, always_2d=True, dtype="float32")

    with ZipFile(recording.audio_path) as archive:
        payload = archive.read(recording.audio_member)
    return sf.read(io.BytesIO(payload), always_2d=True, dtype="float32")


def longest_monophonic_interval(
    note: NoteEvent,
    notes: Iterable[NoteEvent],
) -> tuple[float, float] | None:
    boundaries = {note.start_s, note.end_s}
    note_list = list(notes)
    for candidate in note_list:
        if candidate.end_s <= note.start_s or candidate.start_s >= note.end_s:
            continue
        boundaries.add(max(note.start_s, candidate.start_s))
        boundaries.add(min(note.end_s, candidate.end_s))

    solo_intervals: list[tuple[float, float]] = []
    ordered = sorted(boundaries)
    for start_s, end_s in zip(ordered, ordered[1:]):
        if end_s <= start_s:
            continue
        midpoint = (start_s + end_s) / 2.0
        active = [
            candidate for candidate in note_list
            if candidate.start_s <= midpoint < candidate.end_s
        ]
        if len(active) == 1 and active[0].note_id == note.note_id:
            solo_intervals.append((start_s, end_s))

    if not solo_intervals:
        return None
    return max(solo_intervals, key=lambda interval: interval[1] - interval[0])


def extract_harmonic_labels(
    recording: SourceRecording,
    waveform: np.ndarray,
    notes: list[NoteEvent],
    selected_note_ids: set[int],
    sample_rate: int,
    max_harmonics: int = MAX_HARMONICS,
    frame_size: int = HARMONIC_FRAME_SIZE,
    hop_size: int = HARMONIC_HOP_SIZE,
    search_cents: float = HARMONIC_SEARCH_CENTS,
) -> tuple[dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]], str]:
    """Return GuitarSet-compatible per-note harmonic pseudo-labels.

    GuitarSet uses its existing per-string CSV measurements. Other sources use
    the same FFT measurement kernel on the longest strictly monophonic region.
    The fourth array is an explicit validity mask; zero outside that mask means
    unknown rather than an absent harmonic.
    """
    labels: dict[int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]] = {}
    sources: set[str] = set()
    timing_tolerance_s = 1.0 / sample_rate + 1e-6

    harmonic_csv = recording.harmonic_csv_path
    if harmonic_csv is not None and harmonic_csv.is_file():
        metadata, present, amplitude, offset = load_harmonic_csv(
            harmonic_csv, max_harmonics
        )
        for note in notes:
            if note.note_id not in selected_note_ids or note.note_id not in metadata:
                continue
            note_metadata = metadata[note.note_id]
            timing_matches = (
                abs(float(note_metadata["start_s"]) - note.start_s) <= timing_tolerance_s
                and abs(float(note_metadata["end_s"]) - note.end_s) <= timing_tolerance_s
            )
            expected_fundamental = midi_to_hz(note.pitch_midi)
            frequency_matches = abs(
                1200.0 * math.log2(
                    max(float(note_metadata["fundamental_hz"]), SILENCE_EPSILON)
                    / expected_fundamental
                )
            ) <= MAX_FUNDAMENTAL_ALIGNMENT_CENTS
            if not timing_matches or not frequency_matches:
                continue
            raw_present = np.asarray(present[note.note_id] > 0.5)
            raw_amplitude = np.asarray(amplitude[note.note_id], dtype=np.float32)
            raw_offset = np.asarray(offset[note.note_id], dtype=np.float32)
            valid_bool = (
                raw_present
                & np.isfinite(raw_amplitude)
                & np.isfinite(raw_offset)
                & (np.abs(raw_offset) <= search_cents)
            )
            if not np.any(valid_bool):
                continue
            valid = np.asarray(valid_bool, dtype=np.float32)
            filtered_amplitude = np.where(valid_bool, raw_amplitude, 0.0).astype(np.float32)
            maximum = float(np.max(filtered_amplitude))
            if maximum > SILENCE_EPSILON:
                filtered_amplitude /= maximum
            labels[note.note_id] = (
                valid.copy(),
                filtered_amplitude,
                np.where(valid_bool, raw_offset, 0.0).astype(np.float32),
                valid,
            )
            sources.add("guitarset_csv")

    for note in notes:
        if note.note_id not in selected_note_ids or note.note_id in labels:
            continue
        interval = longest_monophonic_interval(note, notes)
        if interval is None:
            continue
        start_sample = max(0, int(round(interval[0] * sample_rate)))
        end_sample = min(len(waveform), int(round(interval[1] * sample_rate)))
        if end_sample - start_sample < MIN_HARMONIC_SAMPLES:
            continue
        segment = np.asarray(waveform[start_sample:end_sample], dtype=np.float32)
        trim = min(int(0.02 * sample_rate), len(segment) // 5)
        if trim > 0 and len(segment) - trim >= MIN_HARMONIC_SAMPLES:
            segment = segment[trim:]
        if len(segment) < MIN_HARMONIC_SAMPLES:
            continue
        if float(np.sqrt(np.mean(np.square(segment, dtype=np.float64)))) <= SILENCE_EPSILON:
            continue

        rows = measure_note_harmonics(
            segment,
            sample_rate,
            midi_to_hz(note.pitch_midi),
            max_harmonics,
            frame_size,
            hop_size,
            search_cents,
        )
        harmonic_present = np.zeros(max_harmonics, dtype=np.float32)
        harmonic_amplitude = np.zeros(max_harmonics, dtype=np.float32)
        harmonic_offset = np.zeros(max_harmonics, dtype=np.float32)
        harmonic_valid = np.zeros(max_harmonics, dtype=np.float32)
        for row in rows:
            index = int(row["harmonic_number"]) - 1
            if not 0 <= index < max_harmonics:
                continue
            cents_error = float(row["cents_error"])
            if not math.isfinite(cents_error) or abs(cents_error) > search_cents:
                continue
            harmonic_present[index] = 1.0
            harmonic_amplitude[index] = max(0.0, float(row["amplitude"]))
            harmonic_offset[index] = cents_error
            harmonic_valid[index] = 1.0
        maximum = float(np.max(harmonic_amplitude))
        if maximum > SILENCE_EPSILON:
            harmonic_amplitude /= maximum
            labels[note.note_id] = (
                harmonic_present,
                harmonic_amplitude,
                harmonic_offset,
                harmonic_valid,
            )
            sources.add("audio_fft")

    return labels, "+".join(sorted(sources)) if sources else "unavailable"


def build_recording_arrays(
    recording: SourceRecording,
    min_pitch: int,
    max_pitch: int,
    sample_rate: int = 44_100,
    max_window: int = 4096,
    windows: tuple[int, ...] = DEFAULT_WINDOWS,
    sustain_ms: tuple[float, ...] = DEFAULT_SUSTAIN_MS,
    include_inactive: bool = False,
    release_ms: tuple[float, ...] = DEFAULT_RELEASE_MS,
    silence_per_recording: int = 32,
    silence_guard_ms: float = 80.0,
    seed: int = 42,
    extract_harmonics: bool = False,
    harmonic_frame_size: int = HARMONIC_FRAME_SIZE,
    harmonic_hop_size: int = HARMONIC_HOP_SIZE,
    harmonic_search_cents: float = HARMONIC_SEARCH_CENTS,
) -> tuple[dict[str, np.ndarray], dict[str, int | float | str]]:
    audio, actual_rate = read_recording_audio(recording)
    original_rate = int(actual_rate)
    if original_rate != sample_rate:
        divisor = math.gcd(original_rate, sample_rate)
        audio = resample_poly(
            audio,
            sample_rate // divisor,
            original_rate // divisor,
            axis=0,
        ).astype(np.float32, copy=False)
    waveform = np.mean(audio, axis=1, dtype=np.float32)
    duration_s = len(waveform) / sample_rate
    parsed_notes = parse_recording_notes(recording)
    notes = [
        NoteEvent(note.note_id, note.start_s, min(note.end_s, duration_s), note.pitch_midi, note.expression)
        for note in parsed_notes
        if note.start_s >= 0.0 and note.start_s < duration_s and note.end_s > note.start_s
    ]

    store: dict[str, list] = {
        "audio": [], "visible_window": [], "prediction_age_ms": [],
        "attack_age_ms": [], "pitch_midi": [], "fundamental_hz": [],
        "onset": [], "attack_phase": [], "release_phase": [],
        "active": [], "channel": [], "note_id": [],
    }
    selected_notes: set[int] = set()
    rejected_polyphonic = 0
    rejected_range = 0
    rejected_timing = len(parsed_notes) - len(notes)

    for note in notes:
        if not min_pitch <= note.pitch_midi <= max_pitch:
            rejected_range += 1
            continue
        requests = [
            (window, window / sample_rate * 1000.0, index == 0, True)
            for index, window in enumerate(windows)
        ]
        requests.extend((max_window, age, False, False) for age in sustain_ms)
        note_selected = False

        for visible_window, age_ms, is_onset, is_attack in requests:
            prediction_time = note.start_s + age_ms / 1000.0
            if prediction_time >= note.end_s or prediction_time >= duration_s:
                continue
            active = [
                candidate for candidate in notes
                if candidate.start_s <= prediction_time < candidate.end_s
            ]
            if len(active) != 1 or active[0].note_id != note.note_id:
                rejected_polyphonic += 1
                continue

            sample = causal_window(
                waveform,
                int(round(prediction_time * sample_rate)),
                max_window,
            )
            store["audio"].append(sample)
            store["visible_window"].append(visible_window)
            store["prediction_age_ms"].append(age_ms)
            store["attack_age_ms"].append(age_ms)
            store["pitch_midi"].append(note.pitch_midi)
            store["fundamental_hz"].append(midi_to_hz(note.pitch_midi))
            store["onset"].append(float(is_onset))
            store["attack_phase"].append(float(is_attack))
            store["release_phase"].append(0.0)
            store["active"].append(1.0)
            store["channel"].append(0)
            store["note_id"].append(note.note_id)
            selected_notes.add(note.note_id)
            note_selected = True

        if include_inactive and note_selected:
            for offset_ms in release_ms:
                prediction_time = note.end_s + offset_ms / 1000.0
                if prediction_time >= duration_s:
                    continue
                active_at_prediction = [
                    candidate for candidate in notes
                    if candidate.start_s <= prediction_time < candidate.end_s
                ]
                if active_at_prediction:
                    continue

                sample = causal_window(
                    waveform,
                    int(round(prediction_time * sample_rate)),
                    max_window,
                )
                store["audio"].append(sample)
                store["visible_window"].append(max_window)
                store["prediction_age_ms"].append(offset_ms)
                store["attack_age_ms"].append(offset_ms)
                store["pitch_midi"].append(note.pitch_midi)
                store["fundamental_hz"].append(midi_to_hz(note.pitch_midi))
                store["onset"].append(0.0)
                store["attack_phase"].append(0.0)
                store["release_phase"].append(1.0)
                store["active"].append(0.0)
                store["channel"].append(0)
                store["note_id"].append(note.note_id)

    if include_inactive and silence_per_recording > 0:
        guard_s = silence_guard_ms / 1000.0
        guarded_intervals = [
            (max(0.0, note.start_s - guard_s), min(duration_s, note.end_s + guard_s))
            for note in notes
        ]
        stable_seed = (int(seed) + zlib.crc32(recording.source_id.encode("utf-8"))) & 0xFFFFFFFF
        rng = np.random.default_rng(stable_seed)
        accepted = 0
        attempts = 0
        minimum_time = max_window / sample_rate
        maximum_attempts = max(100, silence_per_recording * 200)
        while accepted < silence_per_recording and attempts < maximum_attempts:
            attempts += 1
            if duration_s <= minimum_time:
                break
            prediction_time = float(rng.uniform(minimum_time, duration_s))
            if any(start <= prediction_time <= end for start, end in guarded_intervals):
                continue

            sample = causal_window(
                waveform,
                int(round(prediction_time * sample_rate)),
                max_window,
            )
            store["audio"].append(sample)
            store["visible_window"].append(max_window)
            store["prediction_age_ms"].append(-1.0)
            store["attack_age_ms"].append(-1.0)
            store["pitch_midi"].append(-1)
            store["fundamental_hz"].append(0.0)
            store["onset"].append(0.0)
            store["attack_phase"].append(0.0)
            store["release_phase"].append(0.0)
            store["active"].append(0.0)
            store["channel"].append(0)
            store["note_id"].append(-1)
            accepted += 1

    count = len(store["audio"])
    harmonic_labels: dict[
        int, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]
    ] = {}
    harmonic_label_source = "disabled"
    if extract_harmonics and selected_notes:
        harmonic_labels, harmonic_label_source = extract_harmonic_labels(
            recording,
            waveform,
            notes,
            selected_notes,
            sample_rate,
            MAX_HARMONICS,
            harmonic_frame_size,
            harmonic_hop_size,
            harmonic_search_cents,
        )

    harmonic_present = np.zeros((count, MAX_HARMONICS), dtype=np.float32)
    harmonic_amplitude = np.zeros((count, MAX_HARMONICS), dtype=np.float32)
    harmonic_offset_cents = np.zeros((count, MAX_HARMONICS), dtype=np.float32)
    harmonic_label_valid = np.zeros((count, MAX_HARMONICS), dtype=np.float32)
    labeled_samples = 0
    for sample_index, note_id in enumerate(store["note_id"]):
        label = harmonic_labels.get(int(note_id))
        if label is None:
            continue
        harmonic_present[sample_index] = label[0]
        harmonic_amplitude[sample_index] = label[1]
        harmonic_offset_cents[sample_index] = label[2]
        harmonic_label_valid[sample_index] = label[3]
        labeled_samples += 1

    arrays = {
        "audio": np.asarray(store["audio"], dtype=np.float32).reshape(count, max_window),
        "visible_window": np.asarray(store["visible_window"], dtype=np.int32),
        "prediction_age_ms": np.asarray(store["prediction_age_ms"], dtype=np.float32),
        "attack_age_ms": np.asarray(store["attack_age_ms"], dtype=np.float32),
        "pitch_midi": np.asarray(store["pitch_midi"], dtype=np.int16),
        "fundamental_hz": np.asarray(store["fundamental_hz"], dtype=np.float32),
        "onset": np.asarray(store["onset"], dtype=np.float32),
        "attack_phase": np.asarray(store["attack_phase"], dtype=np.float32),
        "release_phase": np.asarray(store["release_phase"], dtype=np.float32),
        "active": np.asarray(store["active"], dtype=np.float32),
        "channel": np.asarray(store["channel"], dtype=np.int8),
        "note_id": np.asarray(store["note_id"], dtype=np.int32),
        "harmonic_present": harmonic_present,
        "harmonic_amplitude": harmonic_amplitude,
        "harmonic_offset_cents": harmonic_offset_cents,
    }
    if extract_harmonics:
        arrays["harmonic_label_valid"] = harmonic_label_valid
    report: dict[str, int | float | str] = {
        "source_id": recording.source_id,
        "dataset_id": recording.dataset_id,
        "notes_total": len(parsed_notes),
        "notes_selected": len(selected_notes),
        "samples": count,
        "active_samples": int(np.sum(arrays["active"] > 0.5)),
        "inactive_samples": int(np.sum(arrays["active"] <= 0.5)),
        "onset_samples": int(np.sum(arrays["onset"] > 0.5)),
        "release_samples": int(np.sum(arrays["release_phase"] > 0.5)),
        "silence_samples": int(np.sum(
            (arrays["active"] <= 0.5) & (arrays["release_phase"] <= 0.5)
        )),
        "rejected_polyphonic_requests": rejected_polyphonic,
        "rejected_pitch_notes": rejected_range,
        "rejected_timing_notes": rejected_timing,
        "audio_duration_s": duration_s,
        "audio_channels": int(audio.shape[1]),
        "source_sample_rate": original_rate,
        "resampled": int(original_rate != sample_rate),
        "harmonic_label_source": harmonic_label_source,
        "harmonic_labeled_notes": len(harmonic_labels),
        "harmonic_labeled_samples": labeled_samples,
        "harmonic_valid_values": int(np.sum(harmonic_label_valid > 0.5)),
    }
    return arrays, report


def _manifest_row(
    recording: SourceRecording,
    output_path: Path,
    report: dict[str, int | float | str],
) -> dict[str, str | int | float]:
    return {
        "source_id": recording.source_id,
        "npz_path": str(output_path),
        "dataset_id": recording.dataset_id,
        "player_id": recording.player_id,
        "group_id": recording.group_id,
        "capture_id": recording.capture_id,
        "split": recording.split,
        "license_id": recording.license_id,
        "audio_source": (
            f"{recording.audio_path}::{recording.audio_member}"
            if recording.audio_member else str(recording.audio_path)
        ),
        "annotation_source": str(recording.annotation_path),
        "examples": int(report["samples"]),
        "active_examples": int(report["active_samples"]),
        "inactive_examples": int(report["inactive_samples"]),
        "onset_examples": int(report["onset_samples"]),
        "release_examples": int(report["release_samples"]),
        "silence_examples": int(report["silence_samples"]),
        "notes": int(report["notes_selected"]),
        "harmonic_label_source": str(report["harmonic_label_source"]),
        "harmonic_labeled_notes": int(report["harmonic_labeled_notes"]),
        "harmonic_labeled_samples": int(report["harmonic_labeled_samples"]),
        "sample_rate": 44_100,
        "max_window": 4096,
    }


def build_dataset(
    recordings: Iterable[SourceRecording],
    output_dir: str | Path,
    min_pitch: int,
    max_pitch: int,
    overwrite: bool = False,
    include_inactive: bool = False,
    sustain_ms: tuple[float, ...] = DEFAULT_SUSTAIN_MS,
    release_ms: tuple[float, ...] = DEFAULT_RELEASE_MS,
    silence_per_recording: int = 32,
    silence_guard_ms: float = 80.0,
    seed: int = 42,
    extract_harmonics: bool = False,
    harmonic_frame_size: int = HARMONIC_FRAME_SIZE,
    harmonic_hop_size: int = HARMONIC_HOP_SIZE,
    harmonic_search_cents: float = HARMONIC_SEARCH_CENTS,
) -> dict[str, object]:
    output_dir = Path(output_dir)
    temporal_expanded = (
        tuple(float(value) for value in sustain_ms) != DEFAULT_SUSTAIN_MS
        or tuple(float(value) for value in release_ms) != DEFAULT_RELEASE_MS
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    rows: list[dict[str, str | int | float]] = []
    reports: list[dict[str, int | float | str]] = []

    for index, recording in enumerate(recordings, start=1):
        output_path = output_dir / f"{recording.source_id}.npz"
        if output_path.exists() and not overwrite:
            raise FileExistsError(
                f"Sortie déjà présente: {output_path}. Utiliser --overwrite."
            )
        arrays, report = build_recording_arrays(
            recording,
            min_pitch,
            max_pitch,
            include_inactive=include_inactive,
            sustain_ms=sustain_ms,
            release_ms=release_ms,
            silence_per_recording=silence_per_recording,
            silence_guard_ms=silence_guard_ms,
            seed=seed,
            extract_harmonics=extract_harmonics,
            harmonic_frame_size=harmonic_frame_size,
            harmonic_hop_size=harmonic_hop_size,
            harmonic_search_cents=harmonic_search_cents,
        )
        reports.append(report)
        if int(report["samples"]) == 0:
            print(
                f"[{index}] {recording.dataset_id} {recording.source_id}: "
                "ignoré (aucune fenêtre monophonique dans la plage)"
            )
            continue
        temporary = output_path.with_suffix(".tmp.npz")
        np.savez_compressed(temporary, **arrays)
        temporary.replace(output_path)
        rows.append(_manifest_row(recording, output_path, report))
        print(
            f"[{index}] {recording.dataset_id} {recording.source_id}: "
            f"{report['samples']} exemples"
        )

    fieldnames = [
        "source_id", "npz_path", "dataset_id", "player_id", "group_id",
        "capture_id", "split", "license_id", "examples", "notes",
        "active_examples", "inactive_examples", "onset_examples",
        "release_examples", "silence_examples",
        "harmonic_label_source", "harmonic_labeled_notes",
        "harmonic_labeled_samples", "audio_source", "annotation_source",
        "sample_rate", "max_window",
    ]
    manifest_path = output_dir / "manifest.csv"
    with manifest_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    summary: dict[str, object] = {
        "dataset_version": 6 if include_inactive else (3 if extract_harmonics else 2),
        "dataset_revision": (
            "v6.1-mono-active-harmonics-temporal-1"
            if include_inactive and extract_harmonics and temporal_expanded
            else
            "v6.0-mono-active-harmonics-1"
            if include_inactive and extract_harmonics
            else "v6.0-mono-active-1"
            if include_inactive
            else "v5.3-multisource-harmonics-1"
            if extract_harmonics
            else "v5.2-multisource-mono-1"
        ),
        "extract_harmonics": extract_harmonics,
        "include_inactive": bool(include_inactive),
        "sustain_ms": [float(value) for value in sustain_ms],
        "release_ms": [float(value) for value in release_ms],
        "min_pitch": min_pitch,
        "max_pitch": max_pitch,
        "recordings_considered": len(reports),
        "recordings": len(rows),
        "recordings_skipped_zero_samples": len(reports) - len(rows),
        "samples": sum(int(item["samples"]) for item in reports),
        "active_samples": sum(int(item["active_samples"]) for item in reports),
        "inactive_samples": sum(int(item["inactive_samples"]) for item in reports),
        "onset_samples": sum(int(item["onset_samples"]) for item in reports),
        "release_samples": sum(int(item["release_samples"]) for item in reports),
        "silence_samples": sum(int(item["silence_samples"]) for item in reports),
        "by_dataset": {},
        "files": reports,
    }
    by_dataset: dict[str, dict[str, int]] = {}
    for item in reports:
        group = by_dataset.setdefault(str(item["dataset_id"]), {
            "recordings_considered": 0,
            "recordings": 0,
            "recordings_skipped_zero_samples": 0,
            "samples": 0,
            "active_samples": 0,
            "inactive_samples": 0,
            "harmonic_labeled_notes": 0,
            "harmonic_labeled_samples": 0,
        })
        group["recordings_considered"] += 1
        if int(item["samples"]) > 0:
            group["recordings"] += 1
        else:
            group["recordings_skipped_zero_samples"] += 1
        group["samples"] += int(item["samples"])
        group["active_samples"] += int(item["active_samples"])
        group["inactive_samples"] += int(item["inactive_samples"])
        group["harmonic_labeled_notes"] += int(item["harmonic_labeled_notes"])
        group["harmonic_labeled_samples"] += int(item["harmonic_labeled_samples"])
    summary["by_dataset"] = by_dataset
    (output_dir / "build_report.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return summary


def _limit_recordings(
    recordings: list[SourceRecording],
    maximum_per_dataset: int,
) -> list[SourceRecording]:
    if maximum_per_dataset <= 0:
        return recordings
    counts: dict[str, int] = defaultdict(int)
    selected: list[SourceRecording] = []
    for recording in recordings:
        if counts[recording.dataset_id] >= maximum_per_dataset:
            continue
        selected.append(recording)
        counts[recording.dataset_id] += 1
    return selected


def main() -> int:
    parser = argparse.ArgumentParser(description="Construit le dataset mono multi-source V5.2.")
    parser.add_argument("--guitarset-root", type=Path, default=Path("data/GuitarSet"))
    parser.add_argument(
        "--idmt-root", type=Path,
        default=Path("data/IDMT-SMT-Guitar/IDMT-SMT-GUITAR_V2"),
    )
    parser.add_argument("--guitar-techs-root", type=Path, default=Path("data/Guitar-TECHS"))
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--max-pitch", type=int, default=76)
    parser.add_argument("--max-recordings-per-dataset", type=int, default=0)
    parser.add_argument("--skip-guitarset", action="store_true")
    parser.add_argument("--skip-idmt", action="store_true")
    parser.add_argument("--skip-guitar-techs", action="store_true")
    parser.add_argument("--extract-harmonics", action="store_true")
    parser.add_argument("--include-inactive", action="store_true")
    parser.add_argument(
        "--sustain-age-ms",
        type=float,
        nargs="+",
        default=list(DEFAULT_SUSTAIN_MS),
    )
    parser.add_argument(
        "--release-offset-ms",
        type=float,
        nargs="+",
        default=list(DEFAULT_RELEASE_MS),
    )
    parser.add_argument("--silence-per-recording", type=int, default=32)
    parser.add_argument("--silence-guard-ms", type=float, default=80.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--harmonic-frame-size", type=int, default=HARMONIC_FRAME_SIZE)
    parser.add_argument("--harmonic-hop-size", type=int, default=HARMONIC_HOP_SIZE)
    parser.add_argument("--harmonic-search-cents", type=float, default=HARMONIC_SEARCH_CENTS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    if args.min_pitch > args.max_pitch:
        parser.error("--min-pitch doit être <= --max-pitch")

    if args.harmonic_frame_size < MIN_HARMONIC_SAMPLES:
        parser.error(f"--harmonic-frame-size doit etre >= {MIN_HARMONIC_SAMPLES}")
    if args.harmonic_hop_size < 1:
        parser.error("--harmonic-hop-size doit etre >= 1")
    if args.harmonic_search_cents <= 0.0:
        parser.error("--harmonic-search-cents doit etre > 0")
    if any(value < 0.0 for value in args.release_offset_ms):
        parser.error("--release-offset-ms doit contenir des valeurs >= 0")
    if any(value <= 0.0 for value in args.sustain_age_ms):
        parser.error("--sustain-age-ms doit contenir des valeurs > 0")
    if args.silence_per_recording < 0:
        parser.error("--silence-per-recording doit etre >= 0")
    if args.silence_guard_ms < 0.0:
        parser.error("--silence-guard-ms doit etre >= 0")
    if args.output_dir is None:
        if args.include_inactive:
            args.output_dir = Path("data/dataset/v6_0_active")
        else:
            args.output_dir = Path(
                "data/dataset/v5_3_harmonics"
                if args.extract_harmonics else "data/dataset/v5_2"
            )

    recordings: list[SourceRecording] = []
    if not args.skip_guitarset:
        recordings.extend(discover_guitarset(args.guitarset_root))
    if not args.skip_idmt:
        recordings.extend(discover_idmt(args.idmt_root))
    if not args.skip_guitar_techs:
        recordings.extend(discover_guitar_techs(args.guitar_techs_root))
    recordings.sort(key=lambda item: (item.dataset_id, item.source_id))
    recordings = _limit_recordings(recordings, args.max_recordings_per_dataset)

    counts: dict[str, int] = defaultdict(int)
    split_counts: dict[str, int] = defaultdict(int)
    for recording in recordings:
        counts[recording.dataset_id] += 1
        split_counts[recording.split] += 1
    print(f"Enregistrements admissibles: {len(recordings)}")
    print(f"Par dataset: {dict(sorted(counts.items()))}")
    print(f"Par split: {dict(sorted(split_counts.items()))}")
    if args.dry_run:
        return 0

    summary = build_dataset(
        recordings,
        args.output_dir,
        args.min_pitch,
        args.max_pitch,
        overwrite=args.overwrite,
        include_inactive=args.include_inactive,
        sustain_ms=tuple(float(value) for value in args.sustain_age_ms),
        release_ms=tuple(float(value) for value in args.release_offset_ms),
        silence_per_recording=args.silence_per_recording,
        silence_guard_ms=args.silence_guard_ms,
        seed=args.seed,
        extract_harmonics=args.extract_harmonics,
        harmonic_frame_size=args.harmonic_frame_size,
        harmonic_hop_size=args.harmonic_hop_size,
        harmonic_search_cents=args.harmonic_search_cents,
    )
    print(f"Manifest: {args.output_dir / 'manifest.csv'}")
    print(f"Exemples: {summary['samples']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
