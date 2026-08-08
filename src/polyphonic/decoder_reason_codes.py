"""Stable categorical codes shared by live traces and candidate features."""
from __future__ import annotations

from types import MappingProxyType


NOTE_ON_REASON_CODES = MappingProxyType({
    "model_onset": 1,
    "frame_attack": 2,
    "frame_fallback": 3,
    "harmonic_strong_frame": 4,
    "retrigger": 5,
    "legacy": 6,
    "chord_completion": 7,
})
"""Stable live/debug codes; zero means absent and 255 remains unknown."""

CANDIDATE_REASON_VOCABULARY = (
    "model_onset",
    "frame_attack",
    "frame_fallback",
    "legacy",
    "chord_completion",
)
"""Pre-gate feature vocabulary ordered by the existing stable live codes."""

CANDIDATE_REASON_ENCODING = MappingProxyType({
    reason: NOTE_ON_REASON_CODES[reason]
    for reason in CANDIDATE_REASON_VOCABULARY
})
