"""Offline WAV-to-polyphonic-MIDI using the exact live causal path."""

from __future__ import annotations

import argparse
from collections import Counter
import json
from pathlib import Path
import time

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from src.polyphonic.audio_gain import (
    apply_manual_audio_gain,
    validate_manual_audio_gain,
)
from src.polyphonic.audio_evidence import PolyphonicAudioEvidencePolicy
from src.polyphonic.input_level import CausalModelInputLeveler
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
    auto_level: bool | None = None,
    audio_gain: float = 1.0,
) -> dict[str, object]:
    audio_gain = validate_manual_audio_gain(audio_gain)
    bundle = PolyphonicBundle(artifacts)
    level_metadata = bundle.metadata.get(
        "automatic_model_input_level",
        {},
    )
    configured_auto_level = (
        bool(level_metadata.get("enabled_by_default", False))
        if isinstance(level_metadata, dict)
        else False
    )
    auto_level_enabled = (
        configured_auto_level
        if auto_level is None
        else bool(auto_level)
    )
    runtime = TFLitePolyphonicModel(bundle)
    decoder = _decoder(bundle)
    sample_rate = int(bundle.metadata["sample_rate"])
    hop = int(bundle.metadata["hop_samples"])
    window_size = int(bundle.metadata["max_window_samples"])
    warmup_window = np.zeros(window_size, np.float32)
    for _ in range(20):
        runtime.infer(warmup_window, window_size)
    waveform = _audio(input_wav, sample_rate)
    ring = MonoRingBuffer(window_size)
    window = np.zeros(window_size, np.float32)
    audio_evidence_policy = PolyphonicAudioEvidencePolicy.from_metadata(
        sample_rate,
        hop,
        bundle.metadata,
        calibration_s=1.0,
    )
    input_leveler = CausalModelInputLeveler.from_metadata(
        sample_rate,
        hop,
        float(bundle.metadata.get("normalization_gain", 1.0)),
        window_size,
        bundle.metadata,
    )
    silent_priming_hops = audio_evidence_policy.prime_silence()
    # Live calibration has already filled the causal window with captured
    # silence before the first playable hop.
    ring.write(np.zeros(window_size, dtype=np.float32))
    events: list[dict[str, object]] = []
    inference_ms: list[float] = []
    pipeline_ms: list[float] = []
    gain_induced_clipped_samples = 0
    audio_active_hops = 0
    audio_active_with_notes_hops = 0
    audio_active_empty_hops = 0
    current_audio_active_empty_hops = 0
    longest_audio_active_empty_hops = 0
    physical_onset_hops = 0
    active_midi: set[int] = set()
    event_reason_counts: Counter[str] = Counter()
    note_on_reason_counts: Counter[str] = Counter()
    for start in range(0, len(waveform), hop):
        pipeline_started = time.perf_counter()
        values = np.zeros(hop, np.float32)
        part = waveform[start:start + hop]
        values[:len(part)] = part
        capture_values, induced_clipping = apply_manual_audio_gain(
            values,
            audio_gain,
        )
        gain_induced_clipped_samples += induced_clipping
        ring.write(capture_values)
        audio_evidence = audio_evidence_policy.process(capture_values)
        audio_active_hops += int(audio_evidence.activity.active)
        physical_onset_hops += int(audio_evidence.onset.is_onset)
        level = input_leveler.process(
            capture_values,
            audio_active=bool(audio_evidence.activity.active),
        )
        ring.copy_latest_into(window)
        if auto_level_enabled and level.gain != 1.0:
            window *= level.gain
        prediction = runtime.infer(window, ring.available)
        inference_ms.append(prediction.inference_ms)
        decoded_events = decoder.step(
            prediction.frame_probability,
            prediction.onset_probability,
            prediction.harmonic_amplitude,
            audio_active=audio_evidence.activity.active,
            audio_hop_index=audio_evidence.audio_hop_index,
            audio_onset=bool(audio_evidence.onset.is_onset),
            audio_onset_hop_index=(
                audio_evidence.audio_hop_index
                if audio_evidence.onset.is_onset else None
            ),
        )
        for event in decoded_events:
            reason = event.reason or "unspecified"
            event_reason_counts[reason] += 1
            if event.kind == "note_on":
                note_on_reason_counts[reason] += 1
                active_midi.add(int(event.pitch))
            elif event.kind == "note_off":
                active_midi.discard(int(event.pitch))
            events.append({
                "kind": event.kind,
                "pitch": event.pitch,
                "velocity": event.velocity,
                "time_s": min(len(waveform) / sample_rate, (event.frame_index + 1) * hop / sample_rate),
                "reason": reason,
            })
        if audio_evidence.activity.active:
            if active_midi:
                audio_active_with_notes_hops += 1
                current_audio_active_empty_hops = 0
            else:
                audio_active_empty_hops += 1
                current_audio_active_empty_hops += 1
                longest_audio_active_empty_hops = max(
                    longest_audio_active_empty_hops,
                    current_audio_active_empty_hops,
                )
        else:
            current_audio_active_empty_hops = 0
        pipeline_ms.append(
            (time.perf_counter() - pipeline_started) * 1000.0
        )
    final_time = len(waveform) / sample_rate
    for event in decoder.panic():
        reason = event.reason or "unspecified"
        event_reason_counts[reason] += 1
        if event.kind == "note_on":
            note_on_reason_counts[reason] += 1
        events.append({
            "kind": event.kind,
            "pitch": event.pitch,
            "velocity": event.velocity,
            "time_s": final_time,
            "reason": reason,
        })
    output_midi.parent.mkdir(parents=True, exist_ok=True)
    write_midi(output_midi, events, channel=channel, program=program)
    values = np.asarray(inference_ms, np.float64)
    pipeline_values = np.asarray(pipeline_ms, np.float64)
    return {
        "input_wav": str(input_wav),
        "output_midi": str(output_midi),
        "duration_s": final_time,
        "events": len(events),
        "note_on_events": sum(event["kind"] == "note_on" for event in events),
        "capture_gain": audio_gain,
        "gain_induced_clipped_samples": gain_induced_clipped_samples,
        "silent_priming_hops": silent_priming_hops,
        "audio_active_hops": audio_active_hops,
        "audio_active_note_coverage": {
            "with_active_notes_hops": audio_active_with_notes_hops,
            "empty_active_audio_hops": audio_active_empty_hops,
            "empty_active_audio_percent": (
                100.0 * audio_active_empty_hops / max(audio_active_hops, 1)
            ),
            "longest_empty_active_audio_hops": longest_audio_active_empty_hops,
            "longest_empty_active_audio_ms": (
                1000.0
                * longest_audio_active_empty_hops
                * hop
                / sample_rate
            ),
            "interpretation": (
                "Audio-active hops without any emitted MIDI note; diagnostic "
                "coverage signal, not a count of missing ground-truth notes."
            ),
        },
        "physical_onset_hops": physical_onset_hops,
        "event_reason_counts": dict(sorted(event_reason_counts.items())),
        "note_on_reason_counts": dict(sorted(note_on_reason_counts.items())),
        "audio_evidence": audio_evidence_policy.diagnostics(),
        "automatic_model_input_level": (
            input_leveler.diagnostics()
            if auto_level_enabled else {"enabled": False}
        ),
        "inference_ms": {
            "mean": float(np.mean(values)),
            "p95": float(np.percentile(values, 95)),
            "max": float(np.max(values)),
        },
        "pipeline_ms": {
            "mean": float(np.mean(pipeline_values)),
            "p95": float(np.percentile(pipeline_values, 95)),
            "max": float(np.max(pipeline_values)),
            "hop_budget_ms": 1000.0 * hop / sample_rate,
            "meets_hop_budget_p95": bool(
                np.percentile(pipeline_values, 95)
                <= 1000.0 * hop / sample_rate
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_wav", type=Path)
    parser.add_argument("output_midi", type=Path)
    parser.add_argument(
        "--artifacts", type=Path,
        default=Path("artifacts/guitar_midi_polyphonic_v2_2_0"),
    )
    parser.add_argument("--midi-channel", type=int, default=1)
    parser.add_argument("--program", type=int, default=0)
    parser.add_argument("--report-json", type=Path)
    level_group = parser.add_mutually_exclusive_group()
    level_group.add_argument(
        "--auto-level",
        dest="auto_level",
        action="store_true",
        default=None,
    )
    level_group.add_argument(
        "--no-auto-level",
        dest="auto_level",
        action="store_false",
    )
    parser.add_argument(
        "--audio-gain",
        type=float,
        default=1.0,
        help=(
            "Gain manuel avant evidence et modele; garder 1 pour rejouer "
            "un WAV deja enregistre par le live."
        ),
    )
    args = parser.parse_args()
    try:
        validate_manual_audio_gain(args.audio_gain)
    except ValueError as error:
        parser.error(str(error))
    report = transcribe(
        args.input_wav, args.output_midi, args.artifacts,
        args.midi_channel - 1, args.program,
        auto_level=args.auto_level,
        audio_gain=args.audio_gain,
    )
    if args.report_json:
        args.report_json.parent.mkdir(parents=True, exist_ok=True)
        args.report_json.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
