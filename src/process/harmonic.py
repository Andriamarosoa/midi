#!/usr/bin/env python3
"""Extract harmonic measurements from a multichannel WAV using JAMS note annotations.

The script reads ``note_midi`` annotations from a JAMS file.  For each note,
it analyses the corresponding WAV channel (taken from
``annotation_metadata.data_source`` when available) and writes one CSV row per
note/harmonic to ``data/processed/<wav-title>.csv``.

Example:
    python -m src.process.harmonic data/GuitarSet/<audio>.wav data/GuitarSet/<annotation>.jams
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import soundfile as sf


DEFAULT_OUTPUT_DIR = Path("data/processed")
DEFAULT_MAX_HARMONICS = 20
DEFAULT_FRAME_SIZE = 4096
DEFAULT_HOP_SIZE = 1024
DEFAULT_SEARCH_CENTS = 35.0
EPSILON = 1e-12


def midi_to_hz(midi: float) -> float:
    return 440.0 * (2.0 ** ((midi - 69.0) / 12.0))


def hz_to_midi(hz: float) -> float:
    if hz <= 0:
        return float("nan")
    return 69.0 + 12.0 * math.log2(hz / 440.0)


def load_note_annotations(jams_path: Path) -> list[dict[str, Any]]:
    with jams_path.open("r", encoding="utf-8") as handle:
        document = json.load(handle)

    notes: list[dict[str, Any]] = []
    note_id = 0

    for annotation_index, annotation in enumerate(document.get("annotations", [])):
        if annotation.get("namespace") != "note_midi":
            continue

        metadata = annotation.get("annotation_metadata") or {}
        source = metadata.get("data_source")
        try:
            channel = int(source)
        except (TypeError, ValueError):
            channel = annotation_index // 2

        data = annotation.get("data") or []
        if not isinstance(data, list):
            continue

        for item in data:
            try:
                start = float(item["time"])
                duration = float(item["duration"])
                midi = float(item["value"])
            except (KeyError, TypeError, ValueError):
                continue

            if duration <= 0:
                continue

            notes.append(
                {
                    "note_id": note_id,
                    "annotation_index": annotation_index,
                    "channel": channel,
                    "start_s": start,
                    "duration_s": duration,
                    "end_s": start + duration,
                    "midi": midi,
                    "confidence": item.get("confidence"),
                }
            )
            note_id += 1

    notes.sort(key=lambda note: (note["start_s"], note["channel"], note["midi"]))
    for note_id, note in enumerate(notes):
        note["note_id"] = note_id
    return notes


def frame_signal(signal: np.ndarray, frame_size: int, hop_size: int) -> Iterable[np.ndarray]:
    if len(signal) == 0:
        return

    if len(signal) <= frame_size:
        frame = np.zeros(frame_size, dtype=np.float64)
        frame[: len(signal)] = signal
        yield frame
        return

    last_start = len(signal) - frame_size
    starts = list(range(0, last_start + 1, hop_size))
    if starts[-1] != last_start:
        starts.append(last_start)

    for start in starts:
        yield signal[start : start + frame_size]


def parabolic_peak(magnitudes: np.ndarray, index: int) -> tuple[float, float]:
    if index <= 0 or index >= len(magnitudes) - 1:
        return float(index), float(magnitudes[index])

    left = float(magnitudes[index - 1])
    center = float(magnitudes[index])
    right = float(magnitudes[index + 1])
    denominator = left - 2.0 * center + right

    if abs(denominator) < EPSILON:
        return float(index), center

    offset = 0.5 * (left - right) / denominator
    offset = float(np.clip(offset, -1.0, 1.0))
    peak_index = index + offset
    peak_magnitude = center - 0.25 * (left - right) * offset
    return peak_index, max(float(peak_magnitude), 0.0)


def measure_note_harmonics(
    signal: np.ndarray,
    sample_rate: int,
    fundamental_hz: float,
    max_harmonics: int,
    frame_size: int,
    hop_size: int,
    search_cents: float,
) -> list[dict[str, float | int]]:
    if fundamental_hz <= 0:
        return []

    nyquist = sample_rate / 2.0
    harmonic_count = min(max_harmonics, int(nyquist // fundamental_hz))
    if harmonic_count < 1:
        return []

    window = np.hanning(frame_size)
    coherent_gain = max(float(window.sum()) / 2.0, EPSILON)
    bin_hz = sample_rate / frame_size
    search_ratio = 2.0 ** (search_cents / 1200.0)

    per_harmonic: list[list[tuple[float, float]]] = [
        [] for _ in range(harmonic_count)
    ]

    for frame in frame_signal(signal, frame_size, hop_size):
        frame = np.asarray(frame, dtype=np.float64)
        frame = frame - float(frame.mean())
        spectrum = np.abs(np.fft.rfft(frame * window)) / coherent_gain

        for harmonic_index in range(1, harmonic_count + 1):
            expected_hz = fundamental_hz * harmonic_index
            low_hz = expected_hz / search_ratio
            high_hz = expected_hz * search_ratio
            low_bin = max(1, int(math.floor(low_hz / bin_hz)))
            high_bin = min(len(spectrum) - 2, int(math.ceil(high_hz / bin_hz)))
            if high_bin < low_bin:
                continue

            local_index = int(np.argmax(spectrum[low_bin : high_bin + 1]))
            peak_bin = low_bin + local_index
            refined_bin, magnitude = parabolic_peak(spectrum, peak_bin)
            measured_hz = refined_bin * bin_hz
            per_harmonic[harmonic_index - 1].append((measured_hz, magnitude))

    fundamental_amplitudes = [value[1] for value in per_harmonic[0]]
    fundamental_reference = (
        float(np.median(fundamental_amplitudes))
        if fundamental_amplitudes
        else EPSILON
    )
    fundamental_reference = max(fundamental_reference, EPSILON)

    rows: list[dict[str, float | int]] = []
    for harmonic_index, measurements in enumerate(per_harmonic, start=1):
        if not measurements:
            continue

        frequencies = np.asarray([item[0] for item in measurements], dtype=float)
        amplitudes = np.asarray([item[1] for item in measurements], dtype=float)
        expected_hz = fundamental_hz * harmonic_index
        measured_hz = float(np.median(frequencies))
        amplitude = float(np.median(amplitudes))
        relative_db = 20.0 * math.log10(max(amplitude, EPSILON) / fundamental_reference)
        cents_error = 1200.0 * math.log2(measured_hz / expected_hz)

        rows.append(
            {
                "harmonic_number": harmonic_index,
                "expected_hz": expected_hz,
                "measured_hz": measured_hz,
                "measured_midi": hz_to_midi(measured_hz),
                "cents_error": cents_error,
                "amplitude": amplitude,
                "relative_db": relative_db,
                "frames_measured": len(measurements),
            }
        )

    return rows


def analyse(
    wav_path: Path,
    jams_path: Path,
    output_path: Path,
    max_harmonics: int,
    frame_size: int,
    hop_size: int,
    search_cents: float,
) -> tuple[int, int]:
    audio, sample_rate = sf.read(wav_path, always_2d=True, dtype="float64")
    notes = load_note_annotations(jams_path)
    if not notes:
        raise ValueError(f"No note_midi annotations found in {jams_path}")

    output_path.parent.mkdir(parents=True, exist_ok=True)

    fieldnames = [
        "note_id",
        "channel",
        "start_s",
        "end_s",
        "duration_s",
        "annotated_midi",
        "annotated_midi_rounded",
        "fundamental_hz",
        "harmonic_number",
        "expected_hz",
        "measured_hz",
        "measured_midi",
        "cents_error",
        "amplitude",
        "relative_db",
        "frames_measured",
    ]

    row_count = 0
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()

        for note in notes:
            channel = int(note["channel"])
            if channel < 0 or channel >= audio.shape[1]:
                print(
                    f"warning: skipping note {note['note_id']}: channel {channel} "
                    f"is outside WAV channel range 0..{audio.shape[1] - 1}",
                    file=sys.stderr,
                )
                continue

            start_sample = max(0, int(round(note["start_s"] * sample_rate)))
            end_sample = min(
                len(audio), int(round(note["end_s"] * sample_rate))
            )
            if end_sample <= start_sample:
                continue

            # Avoid onset transients when possible, but retain short notes.
            segment = audio[start_sample:end_sample, channel]
            trim = min(int(0.02 * sample_rate), len(segment) // 5)
            if trim > 0 and len(segment) - trim >= 64:
                segment = segment[trim:]

            fundamental_hz = midi_to_hz(float(note["midi"]))
            harmonic_rows = measure_note_harmonics(
                segment,
                sample_rate,
                fundamental_hz,
                max_harmonics,
                frame_size,
                hop_size,
                search_cents,
            )

            for harmonic in harmonic_rows:
                writer.writerow(
                    {
                        "note_id": note["note_id"],
                        "channel": channel,
                        "start_s": f"{note['start_s']:.9f}",
                        "end_s": f"{note['end_s']:.9f}",
                        "duration_s": f"{note['duration_s']:.9f}",
                        "annotated_midi": f"{note['midi']:.6f}",
                        "annotated_midi_rounded": round(note["midi"]),
                        "fundamental_hz": f"{fundamental_hz:.6f}",
                        "harmonic_number": harmonic["harmonic_number"],
                        "expected_hz": f"{harmonic['expected_hz']:.6f}",
                        "measured_hz": f"{harmonic['measured_hz']:.6f}",
                        "measured_midi": f"{harmonic['measured_midi']:.6f}",
                        "cents_error": f"{harmonic['cents_error']:.3f}",
                        "amplitude": f"{harmonic['amplitude']:.10f}",
                        "relative_db": f"{harmonic['relative_db']:.3f}",
                        "frames_measured": harmonic["frames_measured"],
                    }
                )
                row_count += 1

    return len(notes), row_count


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Measure harmonics for JAMS note annotations in a WAV file."
    )
    parser.add_argument("wav", type=Path, help="Input WAV file")
    parser.add_argument("jams", type=Path, help="Matching JAMS annotation file")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Output CSV path (default: data/processed/<wav-title>.csv)",
    )
    parser.add_argument(
        "--max-harmonics",
        type=int,
        default=DEFAULT_MAX_HARMONICS,
        help=f"Maximum harmonics per note (default: {DEFAULT_MAX_HARMONICS})",
    )
    parser.add_argument(
        "--frame-size",
        type=int,
        default=DEFAULT_FRAME_SIZE,
        help=f"FFT frame size (default: {DEFAULT_FRAME_SIZE})",
    )
    parser.add_argument(
        "--hop-size",
        type=int,
        default=DEFAULT_HOP_SIZE,
        help=f"FFT hop size (default: {DEFAULT_HOP_SIZE})",
    )
    parser.add_argument(
        "--search-cents",
        type=float,
        default=DEFAULT_SEARCH_CENTS,
        help=f"Peak search radius in cents (default: {DEFAULT_SEARCH_CENTS})",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()

    if not args.wav.is_file():
        print(f"error: WAV file not found: {args.wav}", file=sys.stderr)
        return 2
    if not args.jams.is_file():
        print(f"error: JAMS file not found: {args.jams}", file=sys.stderr)
        return 2
    if args.max_harmonics < 1:
        print("error: --max-harmonics must be >= 1", file=sys.stderr)
        return 2
    if args.frame_size < 64:
        print("error: --frame-size must be >= 64", file=sys.stderr)
        return 2
    if args.hop_size < 1:
        print("error: --hop-size must be >= 1", file=sys.stderr)
        return 2
    if args.search_cents <= 0:
        print("error: --search-cents must be > 0", file=sys.stderr)
        return 2

    output_path = args.output or DEFAULT_OUTPUT_DIR / f"{args.wav.stem}.csv"

    try:
        note_count, row_count = analyse(
            args.wav,
            args.jams,
            output_path,
            args.max_harmonics,
            args.frame_size,
            args.hop_size,
            args.search_cents,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(
        f"Created {output_path} with {row_count} harmonic rows "
        f"from {note_count} annotated notes."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
