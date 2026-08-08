"""Contracts for leakage-safe, causal decoder-candidate mining.

This module intentionally performs no mining.  It defines the immutable row
schema and episode reduction that the future train-only miner must use.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Iterable


@dataclass(frozen=True)
class DecoderCandidateAttempt:
    recording_key: str
    leakage_group_key: str
    corpus_id: str
    frame_index: int
    pitch: int
    candidate_reason: str
    candidate_score: float
    frame_probability: float
    onset_probability: float
    harmonic_support: float
    audio_onset_available: bool
    audio_onset_recent: bool
    active_polyphony: int
    gate_eligible: bool
    post_gate_rank: int | None
    post_gate_selected: bool
    emitted_noteon: bool
    event_id: str | None

    def __post_init__(self) -> None:
        for field_name in (
            "recording_key",
            "leakage_group_key",
            "corpus_id",
            "candidate_reason",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string.")
        for field_name in ("frame_index", "pitch", "active_polyphony"):
            if type(getattr(self, field_name)) is not int:
                raise ValueError(f"{field_name} must be a JSON-native integer.")
        for field_name in (
            "audio_onset_available",
            "audio_onset_recent",
            "gate_eligible",
            "post_gate_selected",
            "emitted_noteon",
        ):
            if type(getattr(self, field_name)) is not bool:
                raise ValueError(f"{field_name} must be a JSON-native boolean.")
        if self.frame_index < 0:
            raise ValueError("frame_index must be non-negative.")
        if not 0 <= self.pitch <= 127:
            raise ValueError("pitch must be a valid MIDI note in [0, 127].")
        if self.active_polyphony < 0:
            raise ValueError("active_polyphony must be non-negative.")
        for field_name in (
            "candidate_score",
            "frame_probability",
            "onset_probability",
            "harmonic_support",
        ):
            raw_value = getattr(self, field_name)
            if isinstance(raw_value, bool) or not isinstance(raw_value, (int, float)):
                raise ValueError(f"{field_name} must be a JSON-native number.")
            value = float(raw_value)
            if field_name == "candidate_score":
                if not math.isfinite(value):
                    raise ValueError("candidate_score must be finite.")
                continue
            if not math.isfinite(value) or not 0.0 <= value <= 1.0:
                raise ValueError(f"{field_name} must be finite and in [0, 1].")
        if self.audio_onset_recent and not self.audio_onset_available:
            raise ValueError("audio_onset_recent requires audio_onset_available.")
        if self.post_gate_rank is not None:
            if type(self.post_gate_rank) is not int or self.post_gate_rank < 0:
                raise ValueError(
                    "post_gate_rank must be a non-negative JSON-native integer "
                    "when present."
                )
        if self.post_gate_selected and self.post_gate_rank is None:
            raise ValueError("post_gate_selected requires post_gate_rank.")
        if self.emitted_noteon and not self.post_gate_selected:
            raise ValueError("emitted_noteon requires post_gate_selected.")
        if self.emitted_noteon and (
            not isinstance(self.event_id, str) or not self.event_id.strip()
        ):
            raise ValueError("emitted_noteon requires a non-empty event_id.")
        if not self.emitted_noteon and self.event_id is not None:
            raise ValueError("Non-emitted rows must not carry an event_id.")

    def as_json(self) -> dict[str, object]:
        return asdict(self)


def collapse_emitted_candidate_episodes(
    attempts: Iterable[DecoderCandidateAttempt],
) -> list[DecoderCandidateAttempt]:
    """Keep one strongest row per contiguous emitted NoteOn attempt episode.

    Non-emitted rows are deliberately masked in the first experiment: they
    were never an event error and receive no direct event label.
    """
    selected = sorted(
        (row for row in attempts if row.gate_eligible and row.emitted_noteon),
        key=lambda row: (
            row.recording_key,
            row.leakage_group_key,
            row.corpus_id,
            row.pitch,
            row.event_id or "",
            row.frame_index,
        ),
    )
    episodes: list[DecoderCandidateAttempt] = []
    best_row: DecoderCandidateAttempt | None = None
    last_frame_index: int | None = None
    for row in selected:
        contiguous = best_row is not None and last_frame_index is not None and (
            row.recording_key == best_row.recording_key
            and row.leakage_group_key == best_row.leakage_group_key
            and row.corpus_id == best_row.corpus_id
            and row.pitch == best_row.pitch
            and row.event_id == best_row.event_id
            and row.frame_index <= last_frame_index + 1
        )
        if not contiguous:
            if best_row is not None:
                episodes.append(best_row)
            best_row = row
        elif row.candidate_score > best_row.candidate_score:
            best_row = row
        last_frame_index = row.frame_index
    if best_row is not None:
        episodes.append(best_row)
    return sorted(
        episodes,
        key=lambda row: (
            row.recording_key,
            row.frame_index,
            row.pitch,
            row.event_id or "",
        ),
    )


CAUSAL_MATCHING_POLICY = "latest_causal_same_pitch_one_to_one"
CAUSAL_MAX_LATENCY_MS = 250.0
CAUSAL_FEATURES = (
    "frame_probability", "onset_probability", "candidate_score",
    "candidate_reason", "harmonic_support",
    "audio_onset_available", "audio_onset_recent", "active_polyphony",
)
POST_GATE_METADATA_FIELDS = (
    "post_gate_rank",
    "post_gate_selected",
    "emitted_noteon",
    "event_id",
)
