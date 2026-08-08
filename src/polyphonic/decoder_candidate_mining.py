"""Contracts for leakage-safe, causal decoder-candidate mining.

This module intentionally performs no mining.  It defines the immutable row
schema and explicit real-NoteOn learning unit that a future train-only miner
must use.
"""
from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
import hashlib
import json
import math
import re
from threading import Lock
from typing import Iterable, Mapping

from .decoder_candidate_provenance import (
    DecoderCandidateProvenance,
    ManifestItemLike,
    ValidatedDecoderCandidateManifestSnapshot,
    _require_validated_manifest_snapshot,
)
from .decoder_reason_codes import (
    CANDIDATE_REASON_ENCODING,
    CANDIDATE_REASON_VOCABULARY,
)


@dataclass(frozen=True)
class DecoderCandidateAttempt:
    source_id: str
    dataset_id: str
    group_id: str
    capture_id: str
    leakage_group_key: str
    partition: str
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
            "source_id",
            "dataset_id",
            "group_id",
            "capture_id",
            "leakage_group_key",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string.")
        DecoderCandidateProvenance(
            source_id=self.source_id,
            dataset_id=self.dataset_id,
            group_id=self.group_id,
            capture_id=self.capture_id,
            leakage_group_key=self.leakage_group_key,
            partition=self.partition,
        )
        if not isinstance(self.candidate_reason, str) or not self.candidate_reason:
            raise ValueError("candidate_reason must be a non-empty string.")
        if self.candidate_reason not in CANDIDATE_REASON_ENCODING:
            raise ValueError(
                "candidate_reason must use the fixed pre-gate vocabulary."
            )
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


@dataclass(frozen=True)
class DecoderCandidateBatch:
    """One drained buffer plus the overflow evidence needed to trust it."""

    attempts: tuple[DecoderCandidateAttempt, ...]
    total_attempts: int
    dropped_attempts: int
    manifest_sha256: str
    partition_plan_sha256: str
    recording_identity: tuple[str, str, str]
    partition: str

    def __post_init__(self) -> None:
        if type(self.attempts) is not tuple:
            raise ValueError("attempts must be an immutable tuple.")
        for name in ("total_attempts", "dropped_attempts"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if self.total_attempts != len(self.attempts) + self.dropped_attempts:
            raise ValueError(
                "total_attempts must equal retained plus dropped attempts."
            )
        for name in ("manifest_sha256", "partition_plan_sha256"):
            value = getattr(self, name)
            if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
        if (
            type(self.recording_identity) is not tuple
            or len(self.recording_identity) != 3
            or not all(isinstance(value, str) and value.strip() for value in self.recording_identity)
        ):
            raise ValueError(
                "recording_identity must be a non-empty (dataset_id, source_id, capture_id) tuple."
            )
        if self.partition not in ("fit", "dev", "calibration"):
            raise ValueError("partition must be a preassigned train partition.")
        for attempt in self.attempts:
            if not isinstance(attempt, DecoderCandidateAttempt):
                raise ValueError("attempts must contain only DecoderCandidateAttempt values.")
            if (
                attempt.dataset_id,
                attempt.source_id,
                attempt.capture_id,
            ) != self.recording_identity:
                raise ValueError("batch attempts must share the recording identity.")
            if attempt.partition != self.partition:
                raise ValueError("batch attempts must share the preassigned partition.")

    @property
    def complete(self) -> bool:
        return self.dropped_attempts == 0

    def require_complete(self) -> None:
        if not self.complete:
            raise RuntimeError(
                "Decoder candidate batch overflowed; refuse this artifact."
            )


class DecoderCandidateCollector:
    """Bounded opt-in sink for immutable decoder-candidate observations.

    The decoder supplies causal values captured before its optional gate and
    completes each row only after ranking/emission.  Event identifiers live
    here rather than on :class:`PolyphonicMidiEvent`, so instrumentation cannot
    change the public MIDI event contract.
    """

    def __init__(
        self,
        *,
        validated_snapshot: ValidatedDecoderCandidateManifestSnapshot,
        manifest_item: ManifestItemLike,
        maximum_attempts: int = 4096,
    ) -> None:
        if not isinstance(
            validated_snapshot, ValidatedDecoderCandidateManifestSnapshot
        ):
            raise ValueError(
                "validated_snapshot must be "
                "ValidatedDecoderCandidateManifestSnapshot."
            )
        _require_validated_manifest_snapshot(validated_snapshot)
        if (
            type(maximum_attempts) is not int
            or maximum_attempts <= 0
        ):
            raise ValueError("maximum_attempts must be a positive integer.")
        self._provenance = validated_snapshot.provenance_for_snapshot_item(
            manifest_item
        )
        self._manifest_sha256 = validated_snapshot.manifest_sha256
        self._partition_plan_sha256 = validated_snapshot.partition_plan_sha256
        self._attempts: deque[DecoderCandidateAttempt] = deque(
            maxlen=maximum_attempts
        )
        self._lock = Lock()
        self._total_attempts = 0
        self._dropped_attempts = 0
        self._batch_total_attempts = 0
        self._batch_dropped_attempts = 0

    @property
    def provenance(self) -> DecoderCandidateProvenance:
        return self._provenance

    @property
    def source_id(self) -> str:
        return self._provenance.source_id

    @property
    def dataset_id(self) -> str:
        return self._provenance.dataset_id

    @property
    def group_id(self) -> str:
        return self._provenance.group_id

    @property
    def capture_id(self) -> str:
        return self._provenance.capture_id

    @property
    def leakage_group_key(self) -> str:
        return self._provenance.leakage_group_key

    @property
    def partition(self) -> str:
        return self._provenance.partition

    @property
    def maximum_attempts(self) -> int:
        maximum = self._attempts.maxlen
        if maximum is None:  # Construction above always sets a finite bound.
            raise RuntimeError("Decoder candidate collector lost its bound.")
        return maximum

    def _event_id(self, frame_index: int, pitch: int) -> str:
        canonical = json.dumps(
            (
                "decoder-noteon-v2",
                self.dataset_id,
                self.source_id,
                self.group_id,
                self.capture_id,
                self.leakage_group_key,
                frame_index,
                pitch,
            ),
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode("utf-8")
        return "decoder-noteon-v2:" + hashlib.sha256(canonical).hexdigest()

    def record_candidate(
        self,
        *,
        frame_index: int,
        pitch: int,
        candidate_reason: str,
        candidate_score: float,
        frame_probability: float,
        onset_probability: float,
        harmonic_support: float,
        audio_onset_available: bool,
        audio_onset_recent: bool,
        active_polyphony: int,
        gate_eligible: bool,
        post_gate_rank: int | None,
        post_gate_selected: bool,
        emitted_noteon: bool,
    ) -> DecoderCandidateAttempt:
        """Store one completed observation without retaining unbounded data."""
        return self.record_candidates(({
            "frame_index": frame_index,
            "pitch": pitch,
            "candidate_reason": candidate_reason,
            "candidate_score": candidate_score,
            "frame_probability": frame_probability,
            "onset_probability": onset_probability,
            "harmonic_support": harmonic_support,
            "audio_onset_available": audio_onset_available,
            "audio_onset_recent": audio_onset_recent,
            "active_polyphony": active_polyphony,
            "gate_eligible": gate_eligible,
            "post_gate_rank": post_gate_rank,
            "post_gate_selected": post_gate_selected,
            "emitted_noteon": emitted_noteon,
        },))[0]

    def record_candidates(
        self,
        rows: Iterable[Mapping[str, object]],
    ) -> tuple[DecoderCandidateAttempt, ...]:
        """Validate a frame batch, then commit it without waiting for a lock."""
        prepared: list[DecoderCandidateAttempt] = []
        for row in rows:
            values = dict(row)
            frame_index = values.get("frame_index")
            pitch = values.get("pitch")
            emitted_noteon = values.get("emitted_noteon")
            event_id = (
                self._event_id(frame_index, pitch)
                if (
                    type(frame_index) is int
                    and type(pitch) is int
                    and emitted_noteon is True
                )
                else None
            )
            prepared.append(DecoderCandidateAttempt(
                source_id=self.source_id,
                dataset_id=self.dataset_id,
                group_id=self.group_id,
                capture_id=self.capture_id,
                leakage_group_key=self.leakage_group_key,
                partition=self.partition,
                event_id=event_id,
                **values,
            ))
        if not prepared:
            return ()
        if not self._lock.acquire(blocking=False):
            raise RuntimeError(
                "Decoder candidate collector is busy; refuse this artifact."
            )
        try:
            for attempt in prepared:
                if len(self._attempts) == self._attempts.maxlen:
                    self._dropped_attempts += 1
                    self._batch_dropped_attempts += 1
                self._attempts.append(attempt)
                self._total_attempts += 1
                self._batch_total_attempts += 1
        finally:
            self._lock.release()
        return tuple(prepared)

    @property
    def attempts(self) -> tuple[DecoderCandidateAttempt, ...]:
        """Return an immutable point-in-time copy of the bounded buffer."""
        with self._lock:
            return tuple(self._attempts)

    @property
    def total_attempts(self) -> int:
        with self._lock:
            return self._total_attempts

    @property
    def dropped_attempts(self) -> int:
        with self._lock:
            return self._dropped_attempts

    def drain(self) -> DecoderCandidateBatch:
        """Atomically drain rows together with any overflow evidence."""
        with self._lock:
            batch = DecoderCandidateBatch(
                attempts=tuple(self._attempts),
                total_attempts=self._batch_total_attempts,
                dropped_attempts=self._batch_dropped_attempts,
                manifest_sha256=self._manifest_sha256,
                partition_plan_sha256=self._partition_plan_sha256,
                recording_identity=self._provenance.manifest_identity_key,
                partition=self._provenance.partition,
            )
            self._attempts.clear()
            self._batch_total_attempts = 0
            self._batch_dropped_attempts = 0
            return batch


def select_trainable_emitted_events(
    attempts: Iterable[DecoderCandidateAttempt],
) -> list[DecoderCandidateAttempt]:
    """Return the explicit first learning unit: one real emitted NoteOn.

    No temporal aggregation occurs here. A repeated NoteOn is a separate
    decoder decision and must remain separately matchable to causal ground
    truth. Duplicate event identifiers therefore indicate an invalid artifact,
    rather than a tie to resolve with a score-dependent heuristic.
    """
    selected = list(
        row for row in attempts if row.gate_eligible and row.emitted_noteon
    )
    event_ids = [row.event_id for row in selected]
    if any(event_id is None for event_id in event_ids):
        raise RuntimeError("Fail closed: emitted trainable event has no event_id.")
    if len(set(event_ids)) != len(event_ids):
        raise RuntimeError("Fail closed: duplicate trainable event_id.")
    return sorted(
        selected,
        key=lambda row: (
            row.partition,
            row.dataset_id,
            row.source_id,
            row.capture_id,
            row.leakage_group_key,
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
PROVENANCE_FIELDS = (
    "source_id",
    "dataset_id",
    "group_id",
    "capture_id",
    "leakage_group_key",
    "partition",
)
