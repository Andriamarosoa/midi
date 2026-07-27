"""Offline validation of the causal live audio-activity gate.

The validator deliberately reuses captured model probabilities.  It therefore
compares only the activity gate and its downstream decoder consequences; no
new neural-network inference (and no test-set selection) is involved.
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import soundfile as sf

from src.polyphonic.decoder import PolyphonicDecoder, PolyphonicDecoderConfig
from src.polyphonic.tflite_runtime import PolyphonicBundle
from src.stream.audio_activity_gate import CalibratedAudioActivityGate


EPSILON = 1e-12
REQUIRED_DEBUG_KEYS = (
    "frame_index",
    "time_s",
    "decoder_reset_before",
    "audio_active",
    "rms_dbfs",
    "frame_probability",
    "onset_probability",
    "harmonic_amplitude",
    "active_mask",
    "note_on_mask",
    "note_off_mask",
    "sample_rate",
    "hop_samples",
    "midi_min",
    "midi_max",
)


@dataclass(frozen=True)
class ReplayEvent:
    trace_index: int
    model_frame_index: int
    time_s: float
    kind: str
    pitch: int
    velocity: int
    retrigger: bool

    @property
    def key(self) -> tuple[int, str, int]:
        return (self.trace_index, self.kind, self.pitch)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ReplayResult:
    active_mask: np.ndarray
    note_on_mask: np.ndarray
    note_off_mask: np.ndarray
    events: tuple[ReplayEvent, ...]
    reset_note_offs: int
    final_active_pitches: tuple[int, ...]


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate the live causal audio-activity gate on a debug capture."
    )
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--debug-npz", type=Path, required=True)
    parser.add_argument("--artifacts", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args()


def _scalar(array: np.ndarray, name: str) -> int:
    values = np.asarray(array)
    if values.size != 1:
        raise ValueError(f"{name} must be scalar, got {values.shape}")
    return int(values.reshape(-1)[0])


def _load_debug(path: Path) -> dict[str, np.ndarray]:
    if not path.is_file():
        raise FileNotFoundError(path)
    with np.load(path, allow_pickle=False) as archive:
        missing = [key for key in REQUIRED_DEBUG_KEYS if key not in archive]
        if missing:
            raise ValueError(f"Missing debug arrays: {', '.join(missing)}")
        debug = {key: np.asarray(archive[key]) for key in archive.files}

    frames = len(debug["time_s"])
    if frames == 0:
        raise ValueError("The debug trace is empty.")
    for key in (
        "frame_index",
        "decoder_reset_before",
        "audio_active",
        "rms_dbfs",
        "frame_probability",
        "onset_probability",
        "harmonic_amplitude",
        "active_mask",
        "note_on_mask",
        "note_off_mask",
    ):
        if debug[key].shape[0] != frames:
            raise ValueError(f"{key} has {debug[key].shape[0]} rows, expected {frames}")
    return debug


def _load_audio(path: Path, expected_sample_rate: int) -> np.ndarray:
    if not path.is_file():
        raise FileNotFoundError(path)
    audio, sample_rate = sf.read(path, dtype="float32", always_2d=True)
    if int(sample_rate) != expected_sample_rate:
        raise ValueError(
            f"WAV sample rate is {sample_rate}, expected {expected_sample_rate}"
        )
    if audio.shape[1] != 1:
        raise ValueError(f"Expected mono WAV, got {audio.shape[1]} channels")
    values = np.asarray(audio[:, 0], np.float32)
    if not np.all(np.isfinite(values)):
        raise ValueError("WAV contains non-finite samples")
    return values


def _decoder_config(metadata: dict[str, Any]) -> PolyphonicDecoderConfig:
    raw = metadata.get("decoder")
    if not isinstance(raw, dict):
        raise ValueError("Artifact metadata does not contain a decoder contract")
    fields = PolyphonicDecoderConfig.__dataclass_fields__
    values = {name: raw[name] for name in fields if name in raw}
    missing = [name for name in fields if name not in values]
    if missing:
        raise ValueError(f"Decoder metadata is incomplete: {', '.join(missing)}")
    return PolyphonicDecoderConfig(**values)


def _map_trace_to_hops(
    time_s: np.ndarray,
    sample_rate: int,
    hop_samples: int,
    full_hops: int,
) -> tuple[np.ndarray, np.ndarray]:
    times = np.asarray(time_s, np.float64)
    hop_indices = np.rint(times * sample_rate / hop_samples).astype(np.int64) - 1
    if np.any(hop_indices < 0) or np.any(hop_indices >= full_hops):
        bad = hop_indices[(hop_indices < 0) | (hop_indices >= full_hops)][0]
        raise ValueError(f"Debug time maps outside WAV hops: {int(bad)}")
    if np.any(np.diff(hop_indices) <= 0):
        raise ValueError("Debug time_s must map to strictly increasing audio hops")
    mapped_times = (hop_indices + 1).astype(np.float64) * hop_samples / sample_rate
    errors = np.abs(mapped_times - times)
    tolerance = 0.51 / sample_rate
    if float(np.max(errors)) > tolerance:
        raise ValueError(
            f"Debug time mapping error {float(np.max(errors)):.9g}s exceeds {tolerance:.9g}s"
        )
    return hop_indices, errors


def _hop_rms(audio: np.ndarray, hop_samples: int) -> np.ndarray:
    complete = len(audio) // hop_samples
    hops = np.asarray(audio[: complete * hop_samples], np.float64).reshape(
        complete, hop_samples
    )
    return np.sqrt(np.mean(np.square(hops), axis=1))


def _replay_gate(
    rms: np.ndarray,
    sample_rate: int,
    hop_samples: int,
    reset_hops: set[int],
) -> tuple[np.ndarray, np.ndarray, np.ndarray, CalibratedAudioActivityGate]:
    gate = CalibratedAudioActivityGate(sample_rate, hop_samples)
    active = np.zeros(len(rms), np.bool_)
    calibrated = np.zeros(len(rms), np.bool_)
    rms_dbfs = np.zeros(len(rms), np.float64)
    for hop_index, value in enumerate(rms):
        if hop_index in reset_hops:
            gate.reset_continuity()
        result = gate.process_rms(float(value))
        active[hop_index] = result.active
        calibrated[hop_index] = result.calibrated
        rms_dbfs[hop_index] = result.rms_dbfs
    return active, calibrated, rms_dbfs, gate


def _replay_decoder(
    debug: dict[str, np.ndarray],
    audio_active: np.ndarray,
    config: PolyphonicDecoderConfig,
) -> ReplayResult:
    frames = len(debug["time_s"])
    classes = config.midi_max - config.midi_min + 1
    if np.asarray(audio_active).shape != (frames,):
        raise ValueError("audio_active has an invalid replay shape")
    for key in ("frame_probability", "onset_probability"):
        if debug[key].shape != (frames, classes):
            raise ValueError(f"{key} has shape {debug[key].shape}, expected {(frames, classes)}")
    if debug["harmonic_amplitude"].ndim != 3 or debug[
        "harmonic_amplitude"
    ].shape[:2] != (frames, classes):
        raise ValueError("harmonic_amplitude has an invalid replay shape")

    decoder = PolyphonicDecoder(config)
    active_mask = np.zeros((frames, classes), np.bool_)
    note_on_mask = np.zeros((frames, classes), np.bool_)
    note_off_mask = np.zeros((frames, classes), np.bool_)
    events: list[ReplayEvent] = []
    reset_note_offs = 0

    for trace_index in range(frames):
        if bool(debug["decoder_reset_before"][trace_index]):
            reset_note_offs += len(decoder.panic())
        emitted = decoder.step(
            debug["frame_probability"][trace_index],
            debug["onset_probability"][trace_index],
            debug["harmonic_amplitude"][trace_index],
            audio_active=bool(audio_active[trace_index]),
        )
        event_kinds = {(event.kind, event.pitch) for event in emitted}
        retrigger_pitches = {
            pitch
            for kind, pitch in event_kinds
            if kind == "note_on" and ("note_off", pitch) in event_kinds
        }
        for event in emitted:
            class_index = int(event.pitch) - config.midi_min
            if event.kind == "note_on":
                note_on_mask[trace_index, class_index] = True
            elif event.kind == "note_off":
                note_off_mask[trace_index, class_index] = True
            else:
                raise ValueError(f"Unknown decoder event: {event.kind}")
            events.append(
                ReplayEvent(
                    trace_index=trace_index,
                    model_frame_index=int(debug["frame_index"][trace_index]),
                    time_s=float(debug["time_s"][trace_index]),
                    kind=event.kind,
                    pitch=int(event.pitch),
                    velocity=int(event.velocity),
                    retrigger=int(event.pitch) in retrigger_pitches,
                )
            )
        active_mask[trace_index] = decoder.active

    final_active = tuple(
        config.midi_min + int(index) for index in np.flatnonzero(decoder.active)
    )
    return ReplayResult(
        active_mask=active_mask,
        note_on_mask=note_on_mask,
        note_off_mask=note_off_mask,
        events=tuple(events),
        reset_note_offs=reset_note_offs,
        final_active_pitches=final_active,
    )


def _mask_comparison(actual: np.ndarray, expected: np.ndarray) -> dict[str, Any]:
    actual_bool = np.asarray(actual, np.bool_)
    expected_bool = np.asarray(expected, np.bool_)
    if actual_bool.shape != expected_bool.shape:
        return {
            "exact": False,
            "actual_shape": list(actual_bool.shape),
            "expected_shape": list(expected_bool.shape),
            "mismatched_cells": None,
            "mismatched_frames": None,
        }
    mismatch = actual_bool != expected_bool
    if mismatch.ndim == 1:
        mismatched_frames = int(np.count_nonzero(mismatch))
    else:
        mismatched_frames = int(np.count_nonzero(np.any(mismatch, axis=1)))
    return {
        "exact": not bool(np.any(mismatch)),
        "actual_shape": list(actual_bool.shape),
        "expected_shape": list(expected_bool.shape),
        "mismatched_cells": int(np.count_nonzero(mismatch)),
        "mismatched_frames": mismatched_frames,
    }


def _event_counts(events: Iterable[ReplayEvent]) -> dict[str, Any]:
    rows = tuple(events)
    note_on = sum(event.kind == "note_on" for event in rows)
    note_off = sum(event.kind == "note_off" for event in rows)
    retrigger_pitches = {
        (event.trace_index, event.pitch)
        for event in rows
        if event.kind == "note_on" and event.retrigger
    }
    by_pitch: dict[str, dict[str, int]] = {}
    for pitch in sorted({event.pitch for event in rows}):
        by_pitch[str(pitch)] = {
            "note_on": sum(
                event.kind == "note_on" and event.pitch == pitch for event in rows
            ),
            "note_off": sum(
                event.kind == "note_off" and event.pitch == pitch for event in rows
            ),
        }
    return {
        "events": len(rows),
        "note_on": int(note_on),
        "note_off": int(note_off),
        "retriggers": len(retrigger_pitches),
        "by_pitch": by_pitch,
    }


def _event_difference(
    source: Iterable[ReplayEvent], other: Iterable[ReplayEvent]
) -> tuple[ReplayEvent, ...]:
    remaining = Counter(event.key for event in source)
    remaining.subtract(event.key for event in other)
    remaining = Counter({key: value for key, value in remaining.items() if value > 0})
    difference: list[ReplayEvent] = []
    for event in source:
        if remaining[event.key] > 0:
            difference.append(event)
            remaining[event.key] -= 1
    return tuple(difference)


def _quantiles(values: Iterable[float]) -> dict[str, float | None]:
    array = np.asarray(tuple(values), np.float64)
    if len(array) == 0:
        return {
            "minimum": None,
            "p05": None,
            "p25": None,
            "median": None,
            "p75": None,
            "p95": None,
            "maximum": None,
            "mean": None,
        }
    return {
        "minimum": float(np.min(array)),
        "p05": float(np.quantile(array, 0.05)),
        "p25": float(np.quantile(array, 0.25)),
        "median": float(np.quantile(array, 0.50)),
        "p75": float(np.quantile(array, 0.75)),
        "p95": float(np.quantile(array, 0.95)),
        "maximum": float(np.max(array)),
        "mean": float(np.mean(array)),
    }


class CausalSpectralSupport:
    """Harmonic-stack support using audio strictly before an event time."""

    def __init__(
        self,
        audio: np.ndarray,
        sample_rate: int,
        hop_samples: int,
        window_samples: int,
        midi_min: int,
        midi_max: int,
        tolerance_cents: float = 35.0,
        harmonics: int = 8,
    ) -> None:
        self.audio = audio
        self.sample_rate = sample_rate
        self.hop_samples = hop_samples
        self.window_samples = window_samples
        self.midi_min = midi_min
        self.midi_max = midi_max
        self.tolerance_cents = tolerance_cents
        self.harmonics = harmonics
        self.n_fft = max(16384, 1 << math.ceil(math.log2(window_samples * 4)))
        self.window = np.hanning(window_samples).astype(np.float64)
        self.bin_hz = sample_rate / self.n_fft
        self._cache: dict[int, tuple[np.ndarray, int]] = {}

    def _scores(self, hop_index: int) -> tuple[np.ndarray, int]:
        cached = self._cache.get(hop_index)
        if cached is not None:
            return cached
        end = min(len(self.audio), (hop_index + 1) * self.hop_samples)
        start = max(0, end - self.window_samples)
        segment = np.zeros(self.window_samples, np.float64)
        available = np.asarray(self.audio[start:end], np.float64)
        segment[-len(available) :] = available
        magnitude = np.abs(np.fft.rfft(segment * self.window, n=self.n_fft))
        nyquist = self.sample_rate / 2.0
        scores = np.zeros(self.midi_max - self.midi_min + 1, np.float64)
        cents_ratio = 2.0 ** (self.tolerance_cents / 1200.0) - 1.0

        for class_index, pitch in enumerate(range(self.midi_min, self.midi_max + 1)):
            fundamental = 440.0 * 2.0 ** ((pitch - 69.0) / 12.0)
            weighted_sum = 0.0
            weight_sum = 0.0
            for harmonic in range(1, self.harmonics + 1):
                frequency = fundamental * harmonic
                if frequency >= nyquist:
                    break
                center = int(round(frequency / self.bin_hz))
                radius = max(
                    1, int(math.ceil(frequency * cents_ratio / self.bin_hz))
                )
                low = max(0, center - radius)
                high = min(len(magnitude), center + radius + 1)
                weight = 1.0 / math.sqrt(harmonic)
                weighted_sum += weight * float(np.max(magnitude[low:high]))
                weight_sum += weight
            scores[class_index] = weighted_sum / max(weight_sum, EPSILON)
        best_pitch = self.midi_min + int(np.argmax(scores))
        result = (scores, best_pitch)
        self._cache[hop_index] = result
        return result

    def rows(
        self, events: Iterable[ReplayEvent], trace_hops: np.ndarray
    ) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for event in events:
            if event.kind != "note_on":
                continue
            hop_index = int(trace_hops[event.trace_index])
            scores, best_pitch = self._scores(hop_index)
            best_score = float(np.max(scores))
            event_score = float(scores[event.pitch - self.midi_min])
            ratio = event_score / max(best_score, EPSILON)
            rows.append(
                {
                    **event.to_dict(),
                    "audio_hop_index": hop_index,
                    "causal_window_end_sample": min(
                        len(self.audio), (hop_index + 1) * self.hop_samples
                    ),
                    "best_pitch": best_pitch,
                    "event_pitch_score": event_score,
                    "best_pitch_score": best_score,
                    "ratio_to_best_pitch": float(np.clip(ratio, 0.0, 1.0)),
                    "support_at_least_0_2": bool(ratio >= 0.2),
                }
            )
        return rows


def _spectral_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ratios = [float(row["ratio_to_best_pitch"]) for row in rows]
    supported = sum(bool(row["support_at_least_0_2"]) for row in rows)
    return {
        "note_on_count": len(rows),
        "support_at_least_0_2_count": int(supported),
        "support_at_least_0_2_rate": float(supported / len(rows)) if rows else None,
        "ratio_quantiles": _quantiles(ratios),
        "events": rows,
    }


def _activity_metrics(
    activity: np.ndarray,
    frame_probability: np.ndarray,
    strong_threshold: float,
) -> dict[str, Any]:
    active = np.asarray(activity, np.bool_)
    frame = np.asarray(frame_probability, np.float32)
    strong = frame >= strong_threshold
    vetoed_frames = (~active) & np.any(strong, axis=1)
    vetoed_candidates = (~active[:, None]) & strong
    return {
        "frames": len(active),
        "active_frames": int(np.count_nonzero(active)),
        "inactive_frames": int(np.count_nonzero(~active)),
        "active_percent": float(100.0 * np.mean(active)),
        "strong_frame_threshold": float(strong_threshold),
        "vetoed_strong_frames": int(np.count_nonzero(vetoed_frames)),
        "vetoed_strong_pitch_candidates": int(np.count_nonzero(vetoed_candidates)),
    }


def validate(
    wav_path: Path,
    debug_path: Path,
    artifacts_path: Path,
) -> dict[str, Any]:
    wav_path = wav_path.resolve()
    debug_path = debug_path.resolve()
    artifacts_path = artifacts_path.resolve()
    debug = _load_debug(debug_path)
    bundle = PolyphonicBundle(artifacts_path)
    metadata = bundle.metadata
    config = _decoder_config(metadata)

    sample_rate = _scalar(debug["sample_rate"], "sample_rate")
    hop_samples = _scalar(debug["hop_samples"], "hop_samples")
    midi_min = _scalar(debug["midi_min"], "midi_min")
    midi_max = _scalar(debug["midi_max"], "midi_max")
    expected_contract = (
        int(metadata["sample_rate"]),
        int(metadata["hop_samples"]),
        config.midi_min,
        config.midi_max,
    )
    actual_contract = (sample_rate, hop_samples, midi_min, midi_max)
    if actual_contract != expected_contract:
        raise ValueError(
            f"Debug/artifact contract mismatch: {actual_contract} != {expected_contract}"
        )

    audio = _load_audio(wav_path, sample_rate)
    rms = _hop_rms(audio, hop_samples)
    trace_hops, mapping_errors = _map_trace_to_hops(
        debug["time_s"], sample_rate, hop_samples, len(rms)
    )
    reset_hops = {
        int(trace_hops[index])
        for index in np.flatnonzero(debug["decoder_reset_before"])
    }
    full_activity, full_calibrated, full_rms_dbfs, gate = _replay_gate(
        rms, sample_rate, hop_samples, reset_hops
    )
    candidate_activity = full_activity[trace_hops]
    baseline_activity = np.asarray(debug["audio_active"], np.bool_)

    baseline = _replay_decoder(debug, baseline_activity, config)
    candidate = _replay_decoder(debug, candidate_activity, config)
    active_check = _mask_comparison(baseline.active_mask, debug["active_mask"])
    note_on_check = _mask_comparison(baseline.note_on_mask, debug["note_on_mask"])
    note_off_check = _mask_comparison(baseline.note_off_mask, debug["note_off_mask"])
    reproduction_passed = bool(
        active_check["exact"] and note_on_check["exact"] and note_off_check["exact"]
    )

    added = _event_difference(candidate.events, baseline.events)
    removed = _event_difference(baseline.events, candidate.events)
    spectral = CausalSpectralSupport(
        audio=audio,
        sample_rate=sample_rate,
        hop_samples=hop_samples,
        window_samples=int(metadata.get("max_window_samples", 4096)),
        midi_min=config.midi_min,
        midi_max=config.midi_max,
        tolerance_cents=config.harmonic_tolerance_cents,
    )
    baseline_spectral = spectral.rows(baseline.events, trace_hops)
    candidate_spectral = spectral.rows(candidate.events, trace_hops)
    added_spectral = spectral.rows(added, trace_hops)
    removed_spectral = spectral.rows(removed, trace_hops)

    debug_rms = np.asarray(debug["rms_dbfs"], np.float64)
    mapped_rms = full_rms_dbfs[trace_hops]
    gate_diagnostics = gate.diagnostics()
    calibrated_indices = np.flatnonzero(full_calibrated)
    first_calibrated_hop = (
        int(calibrated_indices[0]) if len(calibrated_indices) else None
    )
    baseline_counts = _event_counts(baseline.events)
    candidate_counts = _event_counts(candidate.events)
    candidate_gate_calibrated = bool(gate_diagnostics["calibrated"])

    return {
        "inputs": {
            "wav": str(wav_path),
            "debug_npz": str(debug_path),
            "artifacts": str(artifacts_path),
        },
        "contract": {
            "sample_rate": sample_rate,
            "hop_samples": hop_samples,
            "midi_min": midi_min,
            "midi_max": midi_max,
            "max_window_samples": int(metadata.get("max_window_samples", 4096)),
            "debug_frames": len(debug["time_s"]),
            "wav_samples": len(audio),
            "complete_wav_hops": len(rms),
        },
        "time_mapping": {
            "first_debug_hop": int(trace_hops[0]),
            "last_debug_hop": int(trace_hops[-1]),
            "mapped_hops": len(trace_hops),
            "unique_mapped_hops": int(len(np.unique(trace_hops))),
            "unmapped_wav_hops": int(len(rms) - len(trace_hops)),
            "maximum_absolute_time_error_s": float(np.max(mapping_errors)),
            "maximum_absolute_rms_dbfs_error": float(
                np.max(np.abs(mapped_rms - debug_rms))
            ),
        },
        "candidate_gate": {
            **gate_diagnostics,
            "first_calibrated_hop": first_calibrated_hop,
            "first_calibrated_time_s": (
                float((first_calibrated_hop + 1) * hop_samples / sample_rate)
                if first_calibrated_hop is not None
                else None
            ),
            "trace_frames_before_calibration": int(
                np.count_nonzero(~full_calibrated[trace_hops])
            ),
            "decoder_continuity_resets": len(reset_hops),
        },
        "baseline_reproduction": {
            "passed": reproduction_passed,
            "active_mask": active_check,
            "note_on_mask": note_on_check,
            "note_off_mask": note_off_check,
        },
        "activity": {
            "baseline": _activity_metrics(
                baseline_activity, debug["frame_probability"], config.strong_frame_threshold
            ),
            "candidate": _activity_metrics(
                candidate_activity,
                debug["frame_probability"],
                config.strong_frame_threshold,
            ),
            "changed_frames": int(np.count_nonzero(baseline_activity != candidate_activity)),
            "baseline_only_active_frames": int(
                np.count_nonzero(baseline_activity & ~candidate_activity)
            ),
            "candidate_only_active_frames": int(
                np.count_nonzero(candidate_activity & ~baseline_activity)
            ),
            "candidate_active_percent_delta": float(
                100.0 * (np.mean(candidate_activity) - np.mean(baseline_activity))
            ),
        },
        "decoder": {
            "baseline": {
                **baseline_counts,
                "reset_note_offs_not_in_trace_masks": baseline.reset_note_offs,
                "final_active_pitches": list(baseline.final_active_pitches),
            },
            "candidate": {
                **candidate_counts,
                "reset_note_offs_not_in_trace_masks": candidate.reset_note_offs,
                "final_active_pitches": list(candidate.final_active_pitches),
            },
            "delta": {
                "note_on": candidate_counts["note_on"] - baseline_counts["note_on"],
                "note_off": candidate_counts["note_off"] - baseline_counts["note_off"],
                "retriggers": candidate_counts["retriggers"]
                - baseline_counts["retriggers"],
            },
            "events_added": {
                **_event_counts(added),
                "items": [event.to_dict() for event in added],
            },
            "events_removed": {
                **_event_counts(removed),
                "items": [event.to_dict() for event in removed],
            },
            "candidate_active_mask_difference": _mask_comparison(
                candidate.active_mask, baseline.active_mask
            ),
        },
        "spectral_note_on_support": {
            "definition": {
                "causal": True,
                "window_samples": spectral.window_samples,
                "window_ms": float(1000.0 * spectral.window_samples / sample_rate),
                "window": "Hann",
                "n_fft": spectral.n_fft,
                "midi_search_min": spectral.midi_min,
                "midi_search_max": spectral.midi_max,
                "harmonics": spectral.harmonics,
                "harmonic_weight": "1/sqrt(harmonic_number)",
                "peak_tolerance_cents": spectral.tolerance_cents,
                "ratio": "event_pitch_harmonic_score / best_pitch_40_76_harmonic_score",
                "support_threshold": 0.2,
            },
            "baseline": _spectral_summary(baseline_spectral),
            "candidate": _spectral_summary(candidate_spectral),
            "added_events": _spectral_summary(added_spectral),
            "removed_events": _spectral_summary(removed_spectral),
        },
        "validation": {
            "baseline_reproduction_passed": reproduction_passed,
            "candidate_gate_calibrated": candidate_gate_calibrated,
            "candidate_gate_calibration_stable": gate_diagnostics[
                "calibration_stable"
            ],
            "passed": bool(reproduction_passed and candidate_gate_calibrated),
        },
    }


def main() -> int:
    args = _parse_args()
    report = validate(args.wav, args.debug_npz, args.artifacts)
    output = args.output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    summary = {
        "output": str(output),
        "passed": report["validation"]["passed"],
        "baseline_reproduced": report["baseline_reproduction"]["passed"],
        "baseline_active_percent": report["activity"]["baseline"]["active_percent"],
        "candidate_active_percent": report["activity"]["candidate"]["active_percent"],
        "baseline_note_on": report["decoder"]["baseline"]["note_on"],
        "candidate_note_on": report["decoder"]["candidate"]["note_on"],
        "events_added": report["decoder"]["events_added"]["events"],
        "events_removed": report["decoder"]["events_removed"]["events"],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if report["validation"]["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
