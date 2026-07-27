"""Offline WAV-to-MIDI application using the exact causal live engine."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from src.product.engine import GuitarMidiEngine
from src.product.midi_file import write_midi
from src.product.tflite_runtime import (
    ProductBundle,
    TFLitePitchModel,
    TFLiteTransitionGate,
)


@dataclass(frozen=True)
class WaveformTranscription:
    active: np.ndarray
    pitch: np.ndarray
    retrigger: np.ndarray
    events: list[dict[str, int | float | str]]
    inference_ms: np.ndarray


def load_mono(path: Path, sample_rate: int) -> np.ndarray:
    audio, actual_rate = sf.read(path, always_2d=True, dtype="float32")
    actual_rate = int(actual_rate)
    if actual_rate != sample_rate:
        divisor = math.gcd(actual_rate, sample_rate)
        audio = resample_poly(
            audio, sample_rate // divisor, actual_rate // divisor, axis=0
        ).astype(np.float32, copy=False)
    return np.mean(audio, axis=1, dtype=np.float32)


def transcribe_waveform(
    engine: GuitarMidiEngine,
    waveform: np.ndarray,
    include_padded_tail: bool = True,
) -> WaveformTranscription:
    values = np.asarray(waveform, dtype=np.float32).reshape(-1)
    engine.reset()
    silence = np.zeros(engine.hop_samples, dtype=np.float32)
    # Calibration is part of both offline and live operation.  The final
    # calibration hop becomes decoder frame zero and maps to source time zero.
    for _ in range(engine.onset_detector.calibration_hops):
        engine.process_hop(silence)
    frame_count = (
        int(math.ceil(len(values) / engine.hop_samples))
        if include_padded_tail else len(values) // engine.hop_samples
    )
    active = np.zeros(frame_count, dtype=bool)
    pitch = np.full(frame_count, -1, dtype=np.int32)
    retrigger = np.zeros(frame_count, dtype=bool)
    events: list[dict[str, int | float | str]] = []
    inference_ms = np.zeros(frame_count, dtype=np.float32)
    for index in range(frame_count):
        hop = values[index * engine.hop_samples:(index + 1) * engine.hop_samples]
        if len(hop) < engine.hop_samples:
            hop = np.pad(hop, (0, engine.hop_samples - len(hop)))
        frame = engine.process_hop(hop)
        if frame.decoder is None or frame.prediction is None:
            raise RuntimeError("Le moteur n'est pas calibre apres le preambule.")
        active[index] = frame.decoder.active
        pitch[index] = frame.decoder.pitch
        retrigger[index] = frame.decoder.retrigger
        inference_ms[index] = frame.prediction.inference_ms
        for event in frame.decoder.events:
            events.append({
                "kind": event.kind,
                "pitch": event.pitch,
                "velocity": event.velocity,
                "time_s": event.frame_index * engine.hop_samples / engine.sample_rate,
            })
    duration_s = len(values) / engine.sample_rate
    if engine.decoder.current >= 0:
        events.append({
            "kind": "note_off",
            "pitch": engine.decoder.current,
            "velocity": 0,
            "time_s": duration_s,
        })
    return WaveformTranscription(active, pitch, retrigger, events, inference_ms)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transcription causale d'une guitare mono WAV vers MIDI"
    )
    parser.add_argument("input_wav", type=Path)
    parser.add_argument("output_midi", type=Path)
    parser.add_argument(
        "--artifacts", type=Path,
        default=Path("artifacts/guitar_midi_v1_0_0"),
    )
    parser.add_argument("--threads", type=int, choices=(1, 2, 4))
    parser.add_argument("--audio-gain", type=float, default=1.0)
    parser.add_argument("--midi-channel", type=int, default=1)
    parser.add_argument("--program", type=int, default=0)
    parser.add_argument("--report-json", type=Path)
    args = parser.parse_args()
    if not args.input_wav.is_file():
        parser.error(f"WAV absent: {args.input_wav}")
    if not 1 <= args.midi_channel <= 16 or not 0 <= args.program <= 127:
        parser.error("Canal/programme MIDI invalide")
    bundle = ProductBundle(args.artifacts)
    pitch_model = TFLitePitchModel(bundle, threads=args.threads)
    gate = TFLiteTransitionGate(bundle)
    engine = GuitarMidiEngine(
        bundle, pitch_model, gate, calibration_s=1.0, audio_gain=args.audio_gain
    )
    waveform = load_mono(args.input_wav, engine.sample_rate)
    result = transcribe_waveform(engine, waveform)
    args.output_midi.parent.mkdir(parents=True, exist_ok=True)
    write_midi(
        args.output_midi, result.events,
        channel=args.midi_channel - 1, program=args.program,
    )
    note_ons = sum(event["kind"] == "note_on" for event in result.events)
    report = {
        "input_wav": str(args.input_wav.resolve()),
        "output_midi": str(args.output_midi.resolve()),
        "duration_s": len(waveform) / engine.sample_rate,
        "note_on_events": note_ons,
        "event_count": len(result.events),
        "mean_inference_ms": float(np.mean(result.inference_ms)),
        "p95_inference_ms": float(np.percentile(result.inference_ms, 95.0)),
        "events": result.events,
    }
    report_path = args.report_json or args.output_midi.with_suffix(".json")
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps({key: value for key, value in report.items() if key != "events"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
