"""Contracts for leakage-safe, causal decoder-candidate mining.

This module intentionally performs no mining.  It defines the immutable row
schema and episode reduction that the future train-only miner must use.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Iterable


@dataclass(frozen=True)
class DecoderCandidateAttempt:
    recording_key: str
    leakage_group_key: str
    corpus_id: str
    frame_index: int
    pitch: int
    reason: str
    score: float
    harmonic_support: float
    gate_eligible: bool
    rank: int | None
    selected: bool
    emitted_noteon: bool
    event_id: str | None

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
        key=lambda row: (row.recording_key, row.pitch, row.frame_index),
    )
    episodes: list[DecoderCandidateAttempt] = []
    current: DecoderCandidateAttempt | None = None
    for row in selected:
        contiguous = current is not None and (
            row.recording_key == current.recording_key
            and row.pitch == current.pitch
            and row.frame_index <= current.frame_index + 1
        )
        if not contiguous:
            if current is not None:
                episodes.append(current)
            current = row
        elif row.score > current.score:
            current = row
    if current is not None:
        episodes.append(current)
    return episodes


CAUSAL_MATCHING_POLICY = "latest_causal_same_pitch_one_to_one"
CAUSAL_MAX_LATENCY_MS = 250.0
CAUSAL_FEATURES = (
    "frame_probability", "onset_probability", "candidate_score",
    "candidate_reason", "harmonic_support", "rank", "selected",
    "audio_onset_available", "audio_onset_recent", "active_polyphony",
)
