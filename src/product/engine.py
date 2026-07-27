"""Hardware-independent causal audio-to-MIDI product engine."""

from __future__ import annotations

import time
from dataclasses import dataclass

import numpy as np

from src.product.decoder import DecoderFrame, StreamingTransitionDecoder
from src.product.tflite_runtime import PitchPrediction, ProductBundle
from src.stream.onset_detector import AdaptiveOnsetDetector, OnsetResult
from src.stream.ring_buffer import MonoRingBuffer


@dataclass(frozen=True)
class EngineFrame:
    frame_index: int
    calibrated: bool
    visible_window: int
    onset: OnsetResult
    prediction: PitchPrediction | None
    decoder: DecoderFrame | None
    loop_ms: float


@dataclass(frozen=True)
class InferenceRequest:
    frame_index: int
    visible_window: int
    onset: OnsetResult
    waveform: np.ndarray
    stream_features: dict[str, float]
    frontend_ms: float


class GuitarMidiEngine:
    def __init__(
        self,
        bundle: ProductBundle,
        pitch_model,
        transition_gate,
        calibration_s: float = 1.0,
        audio_gain: float = 1.0,
        onset_rearm_ratio: float | None = None,
        progressive_on_active_onset: bool | None = None,
        retrigger_confidence_threshold: float | None = None,
        minimum_retrigger_ms: float | None = None,
        progressive_windows_enabled: bool | None = None,
        require_joint_onset_evidence: bool | None = None,
        onset_peak_rearm: bool | None = None,
    ) -> None:
        metadata = bundle.metadata
        self.sample_rate = int(metadata["sample_rate"])
        self.hop_samples = int(metadata["hop_samples"])
        self.max_window = int(metadata["max_window_samples"])
        self.windows = tuple(int(value) for value in metadata["progressive_windows"])
        self.audio_gain = float(audio_gain)
        if self.audio_gain <= 0.0:
            raise ValueError("audio_gain doit etre positif.")
        self.pitch_model = pitch_model
        self.progressive_on_active_onset = bool(
            metadata.get("progressive_on_active_onset", False)
            if progressive_on_active_onset is None else progressive_on_active_onset
        )
        self.progressive_windows_enabled = bool(
            metadata.get("progressive_windows_enabled", True)
            if progressive_windows_enabled is None else progressive_windows_enabled
        )
        self.ring = MonoRingBuffer(self.max_window)
        self.window = np.zeros(self.max_window, dtype=np.float32)
        self.onset_detector = AdaptiveOnsetDetector(
            sample_rate=self.sample_rate,
            hop_samples=self.hop_samples,
            fft_size=512,
            calibration_s=calibration_s,
            rearm_ratio=float(
                metadata.get("onset_rearm_ratio", 1.35)
                if onset_rearm_ratio is None else onset_rearm_ratio
            ),
            require_joint_temporal_evidence=bool(
                metadata.get("require_joint_onset_evidence", False)
                if require_joint_onset_evidence is None
                else require_joint_onset_evidence
            ),
            enable_peak_rearm=bool(
                metadata.get("onset_peak_rearm", False)
                if onset_peak_rearm is None else onset_peak_rearm
            ),
        )
        hop_ms = self.hop_samples / self.sample_rate * 1000.0
        self.decoder = StreamingTransitionDecoder(
            gate_predict=transition_gate,
            min_pitch=int(metadata["min_pitch"]),
            max_pitch=int(metadata["max_pitch"]),
            active_threshold=float(metadata["active_threshold"]),
            transition_threshold=float(metadata["transition_threshold"]),
            hop_ms=hop_ms,
            required_frames=int(metadata["stability_frames"]),
            minimum_retrigger_ms=float(
                metadata["minimum_retrigger_ms"]
                if minimum_retrigger_ms is None else minimum_retrigger_ms
            ),
            retrigger_confidence_threshold=float(
                metadata.get("retrigger_confidence_threshold", 0.5)
                if retrigger_confidence_threshold is None
                else retrigger_confidence_threshold
            ),
        )
        self.total_samples = 0
        self.last_onset_sample: int | None = None
        self.window_onset_sample: int | None = None
        self.was_calibrated = False

    def reset(self) -> None:
        self.ring.reset()
        self.onset_detector.reset()
        self.decoder.reset()
        self.total_samples = 0
        self.last_onset_sample = None
        self.window_onset_sample = None
        self.was_calibrated = False

    def reset_continuity(self) -> None:
        """Drop temporal context after an audio gap without recalibrating noise."""
        self.ring.reset()
        self.onset_detector.reset_continuity()
        self.decoder.reset()
        self.last_onset_sample = None
        self.window_onset_sample = None
        self.was_calibrated = self.onset_detector.calibrated

    def process_frontend(
        self, hop: np.ndarray
    ) -> EngineFrame | InferenceRequest:
        started = time.perf_counter()
        samples = np.asarray(hop, dtype=np.float32).reshape(-1).copy()
        if samples.shape != (self.hop_samples,):
            raise ValueError(f"Hop de {self.hop_samples} echantillons requis.")
        if self.audio_gain != 1.0:
            samples *= self.audio_gain
            np.clip(samples, -1.0, 1.0, out=samples)
        self.ring.write(samples)
        self.total_samples += self.hop_samples
        onset = self.onset_detector.process(samples)
        if onset.is_onset:
            self.last_onset_sample = self.total_samples
            if self.progressive_windows_enabled and (
                self.progressive_on_active_onset or self.decoder.current < 0
            ):
                self.window_onset_sample = self.total_samples
        visible = self.max_window
        onset_age = 1.0
        if self.last_onset_sample is not None:
            age_samples = self.total_samples - self.last_onset_sample
            onset_age = float(np.clip(
                age_samples / self.sample_rate / 0.5, 0.0, 1.0
            ))
        if self.window_onset_sample is not None:
            window_age_samples = self.total_samples - self.window_onset_sample
            visible = next(
                (window for window in self.windows if window_age_samples <= window),
                self.windows[-1],
            )
        self.ring.copy_latest_into(self.window)
        available_window = max(
            (window for window in self.windows if window <= self.ring.available),
            default=0,
        )
        if onset.calibrated:
            if not self.was_calibrated:
                self.decoder.reset()
            if available_window == 0:
                result = EngineFrame(
                    frame_index=onset.tick_index - 1,
                    calibrated=True,
                    visible_window=self.ring.available,
                    onset=onset,
                    prediction=None,
                    decoder=None,
                    loop_ms=(time.perf_counter() - started) * 1000.0,
                )
                self.was_calibrated = True
                return result
            visible = min(visible, available_window)
            stream_features = {
                "detected_onset": float(onset.is_onset),
                "onset_confidence": float(onset.confidence),
                "onset_age": onset_age,
                "rms_level": float(np.clip((onset.rms_dbfs + 100.0) / 100.0, 0.0, 1.0)),
                "rms_growth_ratio": float(np.clip(
                    onset.rms_growth / max(onset.rms, 1e-8), 0.0, 1.0
                )),
                "spectral_flux": float(np.tanh(onset.spectral_flux)),
            }
            result: EngineFrame | InferenceRequest = InferenceRequest(
                frame_index=onset.tick_index - 1,
                visible_window=visible,
                onset=onset,
                waveform=self.window.copy(),
                stream_features=stream_features,
                frontend_ms=(time.perf_counter() - started) * 1000.0,
            )
        else:
            result = EngineFrame(
                frame_index=onset.tick_index - 1,
                calibrated=False,
                visible_window=visible,
                onset=onset,
                prediction=None,
                decoder=None,
                loop_ms=(time.perf_counter() - started) * 1000.0,
            )
        self.was_calibrated = onset.calibrated
        return result

    def process_inference(self, request: InferenceRequest) -> EngineFrame:
        started = time.perf_counter()
        prediction = self.pitch_model.infer(
            request.waveform, request.visible_window
        )
        decoded = self.decoder.step(
            prediction.active_probability,
            prediction.pitch_probability,
            prediction.harmonic_amplitude,
            request.stream_features,
        )
        return EngineFrame(
            frame_index=request.frame_index,
            calibrated=True,
            visible_window=request.visible_window,
            onset=request.onset,
            prediction=prediction,
            decoder=decoded,
            loop_ms=request.frontend_ms + (time.perf_counter() - started) * 1000.0,
        )

    def skip_inference(self, request: InferenceRequest) -> EngineFrame:
        decoded = self.decoder.skip(request.stream_features)
        return EngineFrame(
            frame_index=request.frame_index,
            calibrated=True,
            visible_window=request.visible_window,
            onset=request.onset,
            prediction=None,
            decoder=decoded,
            loop_ms=request.frontend_ms,
        )

    def process_hop(self, hop: np.ndarray) -> EngineFrame:
        result = self.process_frontend(hop)
        return (
            self.process_inference(result)
            if isinstance(result, InferenceRequest)
            else result
        )
