"""Causal global-MIDI transition decoder shared by desktop runtimes."""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

import numpy as np

from src.product.contracts import FEATURE_NAMES


def harmonic_match_strength(
    current_pitch: int,
    candidate_pitch: int,
    amplitudes: np.ndarray,
) -> tuple[float, float, float]:
    values = np.asarray(amplitudes, dtype=np.float32).reshape(-1)
    overtone_max = float(np.max(values[1:])) if len(values) > 1 else 0.0
    interval = int(candidate_pitch) - int(current_pitch)
    if interval <= 0 or len(values) < 2:
        return 0.0, 0.0, overtone_max
    matching = []
    for harmonic_number in range(2, len(values) + 1):
        expected = int(round(12.0 * math.log2(harmonic_number)))
        if expected == interval:
            matching.append(float(values[harmonic_number - 1]))
    strength = max(matching, default=0.0)
    strongest_number = int(np.argmax(values[1:])) + 2
    strongest_interval = int(round(12.0 * math.log2(strongest_number)))
    return float(strength), float(strongest_interval == interval), overtone_max


def transition_feature_values(
    current_pitch: int,
    candidate_pitch: int,
    current_duration_frames: int,
    active_probability: float,
    pitch_probability: np.ndarray,
    previous_pitch_probability: np.ndarray,
    harmonic_amplitude: np.ndarray,
    stream_features: dict[str, float],
    min_pitch: int,
    max_pitch: int,
    hop_ms: float,
) -> np.ndarray:
    probabilities = np.asarray(pitch_probability, dtype=np.float32).reshape(-1)
    previous = np.asarray(previous_pitch_probability, dtype=np.float32).reshape(-1)
    expected_classes = int(max_pitch) - int(min_pitch) + 1
    if probabilities.shape != (expected_classes,) or previous.shape != probabilities.shape:
        raise ValueError("Shape pitch invalide pour la transition.")
    candidate_class = int(candidate_pitch) - int(min_pitch)
    current_class = int(current_pitch) - int(min_pitch)
    candidate_confidence = float(probabilities[candidate_class])
    current_confidence = float(probabilities[current_class])
    sorted_probabilities = np.sort(probabilities)
    second = float(sorted_probabilities[-2]) if len(probabilities) > 1 else 0.0
    interval = int(candidate_pitch) - int(current_pitch)
    harmonic_strength, strongest_match, overtone_max = harmonic_match_strength(
        current_pitch, candidate_pitch, harmonic_amplitude
    )
    pitch_range = max(int(max_pitch) - int(min_pitch), 1)
    values = np.asarray([
        active_probability,
        candidate_confidence,
        current_confidence,
        candidate_confidence - second,
        np.clip(candidate_confidence - float(previous[candidate_class]), -1.0, 1.0),
        np.clip(float(previous[current_class]) - current_confidence, -1.0, 1.0),
        np.clip(interval / 36.0, -1.0, 1.0),
        np.clip(abs(interval) / 36.0, 0.0, 1.0),
        (current_pitch - min_pitch) / pitch_range,
        (candidate_pitch - min_pitch) / pitch_range,
        np.clip(current_duration_frames * hop_ms / 1000.0, 0.0, 1.0),
        stream_features["detected_onset"],
        stream_features["onset_confidence"],
        stream_features["onset_age"],
        stream_features["rms_level"],
        stream_features["rms_growth_ratio"],
        stream_features["spectral_flux"],
        harmonic_strength,
        strongest_match,
        overtone_max,
    ], dtype=np.float32)
    if values.shape != (len(FEATURE_NAMES),) or not np.isfinite(values).all():
        raise ValueError("Feature de transition produit invalide.")
    return values


@dataclass(frozen=True)
class MidiEvent:
    kind: str
    pitch: int
    velocity: int
    frame_index: int


@dataclass(frozen=True)
class DecoderFrame:
    active: bool
    pitch: int
    raw_active: bool
    raw_pitch: int
    retrigger: bool
    transition_score: float | None
    transition_veto: bool
    events: tuple[MidiEvent, ...]


class StreamingTransitionDecoder:
    """Stateful V6.0 stabilizer plus the accepted V6.3.3 transition gate."""

    def __init__(
        self,
        gate_predict: Callable[[np.ndarray], np.ndarray],
        min_pitch: int,
        max_pitch: int,
        active_threshold: float,
        transition_threshold: float,
        hop_ms: float,
        required_frames: int = 2,
        minimum_retrigger_ms: float = 80.0,
        retrigger_confidence_threshold: float = 0.5,
    ) -> None:
        self.gate_predict = gate_predict
        self.min_pitch = int(min_pitch)
        self.max_pitch = int(max_pitch)
        self.active_threshold = float(active_threshold)
        self.transition_threshold = float(transition_threshold)
        self.hop_ms = float(hop_ms)
        self.required_frames = int(required_frames)
        self.retrigger_confidence_threshold = float(
            retrigger_confidence_threshold
        )
        if not 0.0 <= self.retrigger_confidence_threshold <= 1.0:
            raise ValueError("Seuil de confiance retrigger invalide.")
        self.minimum_retrigger_frames = max(
            1, int(math.ceil(float(minimum_retrigger_ms) / self.hop_ms))
        )
        if self.required_frames < 1:
            raise ValueError("required_frames doit etre positif.")
        self.reset()

    def reset(self) -> None:
        self.frame_index = -1
        self.current = -1
        self.current_since = 0
        self.pending = -2
        self.pending_count = 0
        self.blocked = -2
        self.last_note_on = -10**9
        self.previous_pitch_probability: np.ndarray | None = None
        self.deferred_stream: dict[str, float] | None = None

    def _with_deferred_stream(
        self, stream_features: dict[str, float]
    ) -> dict[str, float]:
        values = {name: float(value) for name, value in stream_features.items()}
        if self.deferred_stream is None:
            return values
        for name in (
            "detected_onset", "onset_confidence", "rms_growth_ratio",
            "spectral_flux",
        ):
            values[name] = max(values[name], self.deferred_stream[name])
        values["onset_age"] = min(
            values["onset_age"], self.deferred_stream["onset_age"]
        )
        self.deferred_stream = None
        return values

    def skip(self, stream_features: dict[str, float]) -> DecoderFrame:
        """Advance one audio hop without inventing a model observation."""
        self.frame_index += 1
        self.pending = -2
        self.pending_count = 0
        values = {name: float(value) for name, value in stream_features.items()}
        if self.deferred_stream is None:
            self.deferred_stream = values
        else:
            for name in (
                "detected_onset", "onset_confidence", "rms_growth_ratio",
                "spectral_flux",
            ):
                self.deferred_stream[name] = max(
                    self.deferred_stream[name], values[name]
                )
            self.deferred_stream["onset_age"] = min(
                self.deferred_stream["onset_age"], values["onset_age"]
            )
            self.deferred_stream["rms_level"] = values["rms_level"]
        return DecoderFrame(
            active=self.current >= 0,
            pitch=self.current,
            raw_active=self.current >= 0,
            raw_pitch=self.current,
            retrigger=False,
            transition_score=None,
            transition_veto=False,
            events=(),
        )

    @staticmethod
    def _velocity(confidence: float) -> int:
        return int(np.clip(round(30.0 + 97.0 * confidence), 1, 127))

    def step(
        self,
        active_probability: float,
        pitch_probability: np.ndarray,
        harmonic_amplitude: np.ndarray,
        stream_features: dict[str, float],
    ) -> DecoderFrame:
        stream_features = self._with_deferred_stream(stream_features)
        self.frame_index += 1
        index = self.frame_index
        probabilities = np.asarray(pitch_probability, dtype=np.float32).reshape(-1)
        expected = self.max_pitch - self.min_pitch + 1
        if probabilities.shape != (expected,):
            raise ValueError(f"{expected} classes pitch attendues.")
        raw_active = float(active_probability) >= self.active_threshold
        raw_pitch = int(np.argmax(probabilities)) + self.min_pitch
        desired = raw_pitch if raw_active else -1
        transition_score: float | None = None
        transition_veto = False
        retrigger = False
        events: list[MidiEvent] = []
        previous_state = self.current

        if self.blocked != -2 and desired != self.blocked:
            self.blocked = -2
        if desired == self.current:
            self.pending = -2
            self.pending_count = 0
            self.blocked = -2
            if (
                self.current >= 0
                and bool(stream_features["detected_onset"] >= 0.5)
                and stream_features["onset_confidence"]
                >= self.retrigger_confidence_threshold
                and index - self.last_note_on >= self.minimum_retrigger_frames
            ):
                retrigger = True
                velocity = self._velocity(float(np.max(probabilities)))
                events.extend((
                    MidiEvent("note_off", self.current, 0, index),
                    MidiEvent("note_on", self.current, velocity, index),
                ))
                self.last_note_on = index
        elif desired == self.blocked:
            self.pending = -2
            self.pending_count = 0
        else:
            if desired == self.pending:
                self.pending_count += 1
            else:
                self.pending = desired
                self.pending_count = 1
            if self.pending_count >= self.required_frames:
                allowed = True
                if self.current >= 0 and desired >= 0:
                    if self.previous_pitch_probability is None:
                        raise RuntimeError("Probabilites precedentes absentes.")
                    feature = transition_feature_values(
                        self.current,
                        desired,
                        index - self.current_since,
                        float(active_probability),
                        probabilities,
                        self.previous_pitch_probability,
                        harmonic_amplitude,
                        stream_features,
                        self.min_pitch,
                        self.max_pitch,
                        self.hop_ms,
                    )
                    score = np.asarray(
                        self.gate_predict(feature[None, :]), dtype=np.float32
                    ).reshape(-1)
                    if score.size != 1 or not np.isfinite(score[0]):
                        raise ValueError("Score gate produit invalide.")
                    transition_score = float(score[0])
                    allowed = transition_score >= self.transition_threshold
                if allowed:
                    self.current = desired
                    self.current_since = index
                    self.blocked = -2
                    if previous_state >= 0:
                        events.append(MidiEvent("note_off", previous_state, 0, index))
                    if self.current >= 0:
                        velocity = self._velocity(float(np.max(probabilities)))
                        events.append(MidiEvent("note_on", self.current, velocity, index))
                        self.last_note_on = index
                else:
                    self.blocked = desired
                    transition_veto = True
                self.pending = -2
                self.pending_count = 0
        self.previous_pitch_probability = probabilities.copy()
        return DecoderFrame(
            active=self.current >= 0,
            pitch=self.current,
            raw_active=raw_active,
            raw_pitch=raw_pitch,
            retrigger=retrigger,
            transition_score=transition_score,
            transition_veto=transition_veto,
            events=tuple(events),
        )
