"""Offline WAV-to-polyphonic-MIDI using the exact live causal path."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from src.polyphonic.live import _decoder
from src.polyphonic.tflite_runtime import PolyphonicBundle, TFLitePolyphonicModel
from src.product.midi_file import write_midi
from src.stream.ring_buffer import MonoRingBuffer


def _audio(path: Path, target_rate: int) -> np.ndarray:
    waveform, rate = sf.read(path, dtype="float32", always_2d=True)
    mono = np.mean(waveform, axis=1, dtype=np.float32)
    if int(rate) != target_rate:
        divisor = __import__("math").gcd(int(rate), target_rate)
        mono = resample_poly(
            mono, target_rate // divisor, int(rate) // divisor
        ).astype(np.float32)
    return mono


def transcribe(
    input_wav: Path,
    output_midi: Path,
    artifacts: Path,
    channel: int,
    program: int,
) -> dict[str, object]:
    bundle = PolyphonicBundle(artifacts)
    runtime = TFLitePolyphonicModel(bundle)
    decoder = _decoder(bundle)
    sample_rate = int(bundle.metadata["sample_rate"])
    hop = int(bundle.metadata["hop_samples"])
    window_size = int(bundle.metadata["max_window_samples"])
    waveform = _audio(input_wav, sample_rate)
    ring = MonoRingBuffer(window_size)
    window = np.zeros(window_size, np.float32)
    events: list[dict[str, object]] = []
    inference_ms: list[float] = []
    for start in range(0, len(waveform), hop):
        values = np.zeros(hop, np.float32)
        part = waveform[start:start + hop]
        values[:len(part)] = part
        ring.write(values)
        ring.copy_latest_into(window)
        prediction = runtime.infer(window, ring.available)
        inference_ms.append(prediction.inference_ms)
        rms = float(np.sqrt(np.mean(values * values) + 1e-12))
        for event in decoder.step(
            prediction.frame_probability,
            prediction.onset_probability,
            prediction.harmonic_amplitude,
            audio_active=rms > 1e-5,
        ):
            events.append({
                "kind": event.kind,
                "pitch": event.pitch,
                "velocity": event.velocity,
                "time_s": min(len(waveform) / sample_rate, (event.frame_index + 1) * hop / sample_rate),
            })
    final_time = len(waveform) / sample_rate
    events.extend({
        "kind": event.kind,
        "pitch": event.pitch,
        "velocity": event.velocity,
        "time_s": final_time,
    } for event in decoder.panic())
    output_midi.parent.mkdir(parents=True, exist_ok=True)
    write_midi(output_midi, events, channel=channel, program=program)
    values = np.asarray(inference_ms, np.float64)
    return {
        "input_wav": str(input_wav),
        "output_midi": str(output_midi),
        "duration_s": final_time,
        "events": len(events),
        "note_on_events": sum(event["kind"] == "note_on" for event in events),
        "inference_ms": {
            "mean": float(np.mean(values)),
            "p95": float(np.percentile(values, 95)),
            "max": float(np.max(values)),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_wav", type=Path)
    parser.add_argument("output_midi", type=Path)
    parser.add_argument(
        "--artifacts", type=Path,
        default=Path("artifacts/guitar_midi_polyphonic_v2_0_0"),
    )
    parser.add_argument("--midi-channel", type=int, default=1)
    parser.add_argument("--program", type=int, default=0)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    report = transcribe(
        args.input_wav, args.output_midi, args.artifacts,
        args.midi_channel - 1, args.program,
    )
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
