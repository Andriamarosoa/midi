"""Low-latency global MIDI state machine for polyphonic frame predictions."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class PolyphonicMidiEvent:
    kind: str
    pitch: int
    velocity: int
    frame_index: int


@dataclass(frozen=True)
class PolyphonicDecoderConfig:
    midi_min: int = 40
    midi_max: int = 76
    frame_on_threshold: float = 0.50
    strong_frame_threshold: float = 0.80
    frame_off_threshold: float = 0.25
    onset_threshold: float = 0.50
    activation_frames: int = 2
    release_frames: int = 3
    minimum_retrigger_frames: int = 14
    silence_release_frames: int = 2
    maximum_polyphony: int = 6
    harmonic_suppression_strength: float = 0.25
    harmonic_tolerance_cents: float = 35.0

    def __post_init__(self) -> None:
        if self.midi_max < self.midi_min:
            raise ValueError("Invalid MIDI range.")
        if not 1 <= self.maximum_polyphony <= 16:
            raise ValueError("Invalid maximum polyphony.")
        if min(
            self.activation_frames,
            self.release_frames,
            self.minimum_retrigger_frames,
            self.silence_release_frames,
        ) < 1:
            raise ValueError("Decoder frame counts must be positive.")


def default_decoder_config(
    frame_threshold: float,
    onset_threshold: float,
    midi_min: int = 40,
    midi_max: int = 76,
    maximum_polyphony: int = 6,
) -> PolyphonicDecoderConfig:
    frame = float(frame_threshold)
    return PolyphonicDecoderConfig(
        midi_min=midi_min,
        midi_max=midi_max,
        frame_on_threshold=frame,
        strong_frame_threshold=min(0.95, max(0.80, frame + 0.25)),
        frame_off_threshold=max(0.05, frame * 0.60),
        onset_threshold=float(onset_threshold),
        maximum_polyphony=maximum_polyphony,
    )


def _harmonic_number(base_pitch: int, candidate_pitch: int) -> int | None:
    if candidate_pitch <= base_pitch:
        return None
    ratio = 2.0 ** ((candidate_pitch - base_pitch) / 12.0)
    number = int(round(ratio))
    if number < 2:
        return None
    error_cents = abs(1200.0 * math.log2(ratio / number))
    return number if error_cents <= 35.0 else None


class PolyphonicDecoder:
    """Own one global state per MIDI pitch; guitar strings never own notes."""

    def __init__(self, config: PolyphonicDecoderConfig) -> None:
        self.config = config
        self.classes = config.midi_max - config.midi_min + 1
        self.active = np.zeros(self.classes, dtype=np.bool_)
        self.activation_count = np.zeros(self.classes, dtype=np.int16)
        self.release_count = np.zeros(self.classes, dtype=np.int16)
        self.last_note_on = np.full(self.classes, -10**9, dtype=np.int64)
        self.frame_index = -1
        self.silence_count = 0

    def _velocity(self, frame_probability: float, onset_probability: float) -> int:
        confidence = max(float(frame_probability), float(onset_probability))
        return int(np.clip(round(35.0 + 92.0 * confidence), 1, 127))

    def _adaptive_on_threshold(
        self,
        class_index: int,
        onset_probability: float,
        harmonic_amplitude: np.ndarray | None,
    ) -> float:
        threshold = self.config.frame_on_threshold
        if onset_probability >= self.config.onset_threshold:
            return threshold
        if harmonic_amplitude is None:
            return threshold
        candidate_pitch = self.config.midi_min + class_index
        support = 0.0
        for base_index in np.flatnonzero(self.active):
            base_pitch = self.config.midi_min + int(base_index)
            number = _harmonic_number(base_pitch, candidate_pitch)
            if number is None or number > harmonic_amplitude.shape[1]:
                continue
            support = max(
                support, float(harmonic_amplitude[int(base_index), number - 1])
            )
        return min(
            self.config.strong_frame_threshold,
            threshold + self.config.harmonic_suppression_strength * support,
        )

    def step(
        self,
        frame_probability: np.ndarray,
        onset_probability: np.ndarray,
        harmonic_amplitude: np.ndarray | None = None,
        audio_active: bool = True,
    ) -> list[PolyphonicMidiEvent]:
        self.frame_index += 1
        frame = np.asarray(frame_probability, dtype=np.float32)
        onset = np.asarray(onset_probability, dtype=np.float32)
        if frame.shape != (self.classes,) or onset.shape != (self.classes,):
            raise ValueError(f"Expected {self.classes} frame/onset probabilities.")
        if harmonic_amplitude is not None:
            harmonic_amplitude = np.asarray(harmonic_amplitude, np.float32)
            if harmonic_amplitude.ndim != 2 or harmonic_amplitude.shape[0] != self.classes:
                raise ValueError("Invalid harmonic amplitude shape.")

        events: list[PolyphonicMidiEvent] = []
        if not audio_active:
            self.silence_count += 1
            if self.silence_count >= self.config.silence_release_frames:
                return self.panic()
            # Keep an already active note during the short silence grace
            # period, but never create a new note from a quiet/noisy hop.
            # Previously the first inactive hop continued through the
            # activation path and could emit a frame-only ghost note.
            return events
        else:
            self.silence_count = 0

        # Release/retrigger currently active notes first.
        for class_index in np.flatnonzero(self.active):
            class_index = int(class_index)
            pitch = self.config.midi_min + class_index
            if frame[class_index] < self.config.frame_off_threshold:
                self.release_count[class_index] += 1
            else:
                self.release_count[class_index] = 0
            if self.release_count[class_index] >= self.config.release_frames:
                self.active[class_index] = False
                self.release_count[class_index] = 0
                self.activation_count[class_index] = 0
                events.append(PolyphonicMidiEvent(
                    "note_off", pitch, 0, self.frame_index
                ))
                continue
            if (
                onset[class_index] >= self.config.onset_threshold
                and frame[class_index] >= self.config.frame_on_threshold
                and self.frame_index - self.last_note_on[class_index]
                >= self.config.minimum_retrigger_frames
            ):
                velocity = self._velocity(frame[class_index], onset[class_index])
                events.extend((
                    PolyphonicMidiEvent("note_off", pitch, 0, self.frame_index),
                    PolyphonicMidiEvent("note_on", pitch, velocity, self.frame_index),
                ))
                self.last_note_on[class_index] = self.frame_index

        available = self.config.maximum_polyphony - int(np.sum(self.active))
        candidates: list[tuple[float, int]] = []
        for class_index in np.flatnonzero(~self.active):
            class_index = int(class_index)
            threshold = self._adaptive_on_threshold(
                class_index, float(onset[class_index]), harmonic_amplitude
            )
            direct_onset = (
                onset[class_index] >= self.config.onset_threshold
                and frame[class_index] >= self.config.frame_on_threshold
            )
            if frame[class_index] >= threshold:
                self.activation_count[class_index] += 1
            else:
                self.activation_count[class_index] = 0
            stable_frame = (
                self.activation_count[class_index] >= self.config.activation_frames
                and frame[class_index] >= threshold
            )
            if direct_onset or stable_frame:
                score = float(frame[class_index] + onset[class_index])
                candidates.append((score, class_index))

        for _, class_index in sorted(candidates, reverse=True)[:max(0, available)]:
            pitch = self.config.midi_min + class_index
            velocity = self._velocity(frame[class_index], onset[class_index])
            self.active[class_index] = True
            self.activation_count[class_index] = 0
            self.release_count[class_index] = 0
            self.last_note_on[class_index] = self.frame_index
            events.append(PolyphonicMidiEvent(
                "note_on", pitch, velocity, self.frame_index
            ))
        return events

    def panic(self) -> list[PolyphonicMidiEvent]:
        events = [
            PolyphonicMidiEvent(
                "note_off", self.config.midi_min + int(index), 0,
                self.frame_index,
            )
            for index in np.flatnonzero(self.active)
        ]
        self.active[:] = False
        self.activation_count[:] = 0
        self.release_count[:] = 0
        return events
