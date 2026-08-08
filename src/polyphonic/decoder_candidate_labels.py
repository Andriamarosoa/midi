"""Pure labels and readiness counters for a future train-only candidate miner.

No decoder, audio reader, model, artifact writer, or command-line entry point
lives here.  The eventual miner must first bind its recording to a validated
full manifest snapshot, then pass the completed bounded collector batch and
the exact replay NoteOn events to these functions.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import math
import operator
import re
from typing import Iterable, Mapping, Protocol, Sequence

from .causal_event_metrics import (
    CausalNoteOnMatch,
    NoteOnPrediction,
    ReferenceNote,
    match_causal_note_ons,
)
from .decoder_candidate_mining import (
    CAUSAL_FEATURES,
    CAUSAL_MATCHING_POLICY,
    CAUSAL_MAX_LATENCY_MS,
    POST_GATE_METADATA_FIELDS,
    PROVENANCE_FIELDS,
    DecoderCandidateAttempt,
    DecoderCandidateBatch,
    select_trainable_emitted_events,
)


DECODER_CANDIDATE_LABEL_SCHEMA_VERSION = 1
DECODER_CANDIDATE_TARGET_FIELD = "causal_noteon_target"
DECODER_CANDIDATE_TIMESTAMP_POLICY = "decoder_event_frame_end_v1"
# Retriggers are emitted from an already-active note path and therefore have no
# pre-gate candidate decision to learn from.  They are counted explicitly, but
# every other uninstrumented NoteOn is a collection failure.
ALLOWED_UNINSTRUMENTED_NOTEON_REASONS = frozenset({"retrigger"})


class MidiEventLike(Protocol):
    """The immutable public event fields required for candidate verification."""

    kind: str
    pitch: int
    frame_index: int
    reason: str


def _validate_batch_provenance(
    *,
    manifest_sha256: str,
    partition_plan_sha256: str,
    recording_identity: tuple[str, str, str],
    partition: str,
) -> None:
    for name, value in (
        ("manifest_sha256", manifest_sha256),
        ("partition_plan_sha256", partition_plan_sha256),
    ):
        if not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value):
            raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    if (
        type(recording_identity) is not tuple
        or len(recording_identity) != 3
        or not all(isinstance(value, str) and value.strip() for value in recording_identity)
    ):
        raise ValueError(
            "recording_identity must be a non-empty (dataset_id, source_id, capture_id) tuple."
        )
    if partition not in ("fit", "dev", "calibration"):
        raise ValueError("partition must be a preassigned train partition.")


def decoder_event_time_s(
    frame_index: int,
    *,
    sample_rate: int,
    hop_size: int,
) -> float:
    """Use the existing decoder-event timing convention exactly.

    ``events_to_notes()`` reports a frame event at the end of its hop, not at
    its beginning.  The causal target must use the same convention so an event
    at frame zero is scored at ``hop_size / sample_rate``.
    """
    if type(frame_index) is not int or frame_index < 0:
        raise ValueError("frame_index must be a non-negative JSON-native integer.")
    if type(sample_rate) is not int or sample_rate <= 0:
        raise ValueError("sample_rate must be a positive JSON-native integer.")
    if type(hop_size) is not int or hop_size <= 0:
        raise ValueError("hop_size must be a positive JSON-native integer.")
    return float((frame_index + 1) * hop_size / sample_rate)


def require_candidate_mining_baseline_decoder_config(
    payload: Mapping[str, object],
) -> None:
    """Refuse a replay where the experimental independent-note gate is active."""
    if not isinstance(payload, Mapping):
        raise ValueError("decoder configuration must be a mapping.")
    if "independent_note_threshold" not in payload:
        raise ValueError(
            "decoder configuration must explicitly declare independent_note_threshold."
        )
    if payload["independent_note_threshold"] is not None:
        raise RuntimeError(
            "Fail closed: candidate mining requires independent_note_threshold=null."
        )


@dataclass(frozen=True)
class LabeledDecoderCandidateEvent:
    """One real emitted NoteOn with its causal ground-truth binary target."""

    attempt: DecoderCandidateAttempt
    causal_noteon_target: int
    matched_reference_index: int | None
    causal_latency_ms: float | None

    def __post_init__(self) -> None:
        if not isinstance(self.attempt, DecoderCandidateAttempt):
            raise ValueError("attempt must be DecoderCandidateAttempt.")
        if not self.attempt.gate_eligible or not self.attempt.emitted_noteon:
            raise ValueError("only gate-eligible emitted NoteOns may receive targets.")
        if type(self.causal_noteon_target) is not int or self.causal_noteon_target not in (0, 1):
            raise ValueError("causal_noteon_target must be the JSON-native integer 0 or 1.")
        if self.causal_noteon_target == 0:
            if self.matched_reference_index is not None or self.causal_latency_ms is not None:
                raise ValueError("a causal false NoteOn must not carry match diagnostics.")
            return
        if (
            type(self.matched_reference_index) is not int
            or self.matched_reference_index < 0
        ):
            raise ValueError("a causal positive requires a reference index.")
        if (
            isinstance(self.causal_latency_ms, bool)
            or not isinstance(self.causal_latency_ms, (int, float))
            or not math.isfinite(float(self.causal_latency_ms))
            or float(self.causal_latency_ms) < 0.0
            or float(self.causal_latency_ms) > CAUSAL_MAX_LATENCY_MS
        ):
            raise ValueError("a causal positive requires an admissible latency_ms.")

    def as_json(self) -> dict[str, object]:
        """Serialize one row while keeping target diagnostics out of features."""
        payload = self.attempt.as_json()
        payload.update({
            "schema_version": DECODER_CANDIDATE_LABEL_SCHEMA_VERSION,
            DECODER_CANDIDATE_TARGET_FIELD: self.causal_noteon_target,
            "matched_reference_index": self.matched_reference_index,
            "causal_latency_ms": self.causal_latency_ms,
        })
        return payload

    def model_features(self) -> dict[str, object]:
        """Project exactly the pre-gate features allowed to reach a future fit.

        The flat audit row intentionally contains label, provenance, and
        post-gate evidence.  A downstream writer must use this method rather
        than filtering an arbitrary mapping, so accidental target leakage is a
        schema error instead of a convention.
        """
        payload = self.attempt.as_json()
        features = {name: payload[name] for name in CAUSAL_FEATURES}
        if tuple(features) != CAUSAL_FEATURES:
            raise AssertionError("candidate feature projection changed its canonical order.")
        if set(features) != set(candidate_feature_names()):
            raise AssertionError("candidate feature projection leaked or omitted a field.")
        return features


@dataclass(frozen=True)
class CausalCandidateLabelBatch:
    """One complete recording-level target batch and its audit counters."""

    manifest_sha256: str
    partition_plan_sha256: str
    recording_identity: tuple[str, str, str]
    partition: str
    labels: tuple[LabeledDecoderCandidateEvent, ...]
    total_attempts: int
    retained_attempts: int
    dropped_attempts: int
    decoder_noteons: int
    instrumented_decoder_noteons: int
    uninstrumented_decoder_noteons: int
    uninstrumented_decoder_noteons_by_reason: tuple[tuple[str, int], ...]
    gate_eligible_emitted_noteons: int
    excluded_invalid_frame: int
    excluded_outside_audio: int
    reference_noteons: int
    matched_reference_noteons: int
    missed_reference_noteons: int

    def __post_init__(self) -> None:
        _validate_batch_provenance(
            manifest_sha256=self.manifest_sha256,
            partition_plan_sha256=self.partition_plan_sha256,
            recording_identity=self.recording_identity,
            partition=self.partition,
        )
        if type(self.labels) is not tuple or not all(
            isinstance(label, LabeledDecoderCandidateEvent) for label in self.labels
        ):
            raise ValueError("labels must be an immutable tuple of labeled candidates.")
        for name in (
            "total_attempts", "retained_attempts", "dropped_attempts",
            "decoder_noteons", "instrumented_decoder_noteons",
            "uninstrumented_decoder_noteons", "gate_eligible_emitted_noteons",
            "excluded_invalid_frame", "excluded_outside_audio",
            "reference_noteons", "matched_reference_noteons",
            "missed_reference_noteons",
        ):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative JSON-native integer.")
        if (
            type(self.uninstrumented_decoder_noteons_by_reason) is not tuple
            or tuple(sorted(self.uninstrumented_decoder_noteons_by_reason))
            != self.uninstrumented_decoder_noteons_by_reason
        ):
            raise ValueError("uninstrumented NoteOn reasons must be a sorted tuple.")
        reason_total = 0
        for reason, count in self.uninstrumented_decoder_noteons_by_reason:
            if not isinstance(reason, str) or not reason:
                raise ValueError("uninstrumented NoteOn reason must be non-empty.")
            if type(count) is not int or count <= 0:
                raise ValueError("uninstrumented NoteOn reason count must be positive.")
            reason_total += count
        if reason_total != self.uninstrumented_decoder_noteons:
            raise ValueError("uninstrumented NoteOn reasons must reconcile their count.")
        if self.total_attempts != self.retained_attempts + self.dropped_attempts:
            raise ValueError("attempt counters must reconcile retained plus dropped rows.")
        if self.decoder_noteons != (
            self.instrumented_decoder_noteons + self.uninstrumented_decoder_noteons
        ):
            raise ValueError("decoder NoteOn counters must reconcile instrumentation.")
        if self.gate_eligible_emitted_noteons != (
            len(self.labels)
            + self.excluded_invalid_frame
            + self.excluded_outside_audio
        ):
            raise ValueError("supervision counters must reconcile emitted NoteOns.")
        positives = sum(label.causal_noteon_target for label in self.labels)
        if self.matched_reference_noteons != positives:
            raise ValueError("matched reference count must equal positive targets.")
        if self.reference_noteons != (
            self.matched_reference_noteons + self.missed_reference_noteons
        ):
            raise ValueError("reference NoteOn counters must reconcile matches and misses.")
        event_ids = [label.attempt.event_id for label in self.labels]
        if any(event_id is None for event_id in event_ids) or len(set(event_ids)) != len(event_ids):
            raise ValueError("labeled candidate event_ids must be present and unique.")
        for label in self.labels:
            attempt = label.attempt
            if (
                attempt.dataset_id,
                attempt.source_id,
                attempt.capture_id,
            ) != self.recording_identity:
                raise ValueError("labeled candidates must share the batch recording identity.")
            if attempt.partition != self.partition:
                raise ValueError("labeled candidates must share the batch partition.")

    @property
    def positive_targets(self) -> int:
        return sum(label.causal_noteon_target for label in self.labels)

    @property
    def negative_targets(self) -> int:
        return len(self.labels) - self.positive_targets

    @property
    def complete(self) -> bool:
        return self.dropped_attempts == 0

    def require_complete(self) -> None:
        if self.dropped_attempts:
            raise RuntimeError("Decoder candidate collection overflowed; refuse this batch.")
        unexpected_reasons = set(
            reason for reason, _ in self.uninstrumented_decoder_noteons_by_reason
        ) - ALLOWED_UNINSTRUMENTED_NOTEON_REASONS
        if unexpected_reasons:
            raise RuntimeError(
                "Fail closed: decoder emitted uninstrumented NoteOns outside the "
                "documented retrigger exclusion: "
                f"{sorted(unexpected_reasons)!r}."
            )

    def require_full_decoder_noteon_coverage(self) -> None:
        """Optional stricter gate for a future experiment targeting every NoteOn.

        The current learning population intentionally excludes paths such as
        active-note retriggers, which have no pre-gate candidate decision.  They
        remain counted by reason but do not silently become negative labels.
        """
        self.require_complete()
        if self.uninstrumented_decoder_noteons:
            raise RuntimeError(
                "Decoder emitted NoteOns outside the instrumented candidate population."
            )


@dataclass(frozen=True)
class DecoderCandidateMiningCounters:
    """Run-level counters that decide whether a train-only artifact is usable."""

    manifest_sha256: str
    partition_plan_sha256: str
    recording_identities: tuple[tuple[str, str, str], ...]
    dataset_partition_target_counts: tuple[tuple[str, str, int, int], ...]
    recordings: int
    total_attempts: int
    retained_attempts: int
    dropped_attempts: int
    decoder_noteons: int
    instrumented_decoder_noteons: int
    uninstrumented_decoder_noteons: int
    uninstrumented_decoder_noteons_by_reason: tuple[tuple[str, int], ...]
    gate_eligible_emitted_noteons: int
    excluded_invalid_frame: int
    excluded_outside_audio: int
    supervised_noteons: int
    positive_targets: int
    negative_targets: int
    reference_noteons: int
    matched_reference_noteons: int
    missed_reference_noteons: int

    def __post_init__(self) -> None:
        _validate_batch_provenance(
            manifest_sha256=self.manifest_sha256,
            partition_plan_sha256=self.partition_plan_sha256,
            recording_identity=("run", "aggregate", "provenance"),
            partition="fit",
        )
        if (
            type(self.recording_identities) is not tuple
            or len(self.recording_identities) != self.recordings
            or tuple(sorted(self.recording_identities)) != self.recording_identities
        ):
            raise ValueError("recording_identities must be a sorted tuple matching recordings.")
        for identity in self.recording_identities:
            _validate_batch_provenance(
                manifest_sha256=self.manifest_sha256,
                partition_plan_sha256=self.partition_plan_sha256,
                recording_identity=identity,
                partition="fit",
            )
        if len(set(self.recording_identities)) != len(self.recording_identities):
            raise ValueError("recording_identities must be unique.")
        if (
            type(self.dataset_partition_target_counts) is not tuple
            or tuple(sorted(self.dataset_partition_target_counts))
            != self.dataset_partition_target_counts
        ):
            raise ValueError("dataset/partition/target counts must be a sorted tuple.")
        observed_targets = 0
        for dataset_id, partition, target, count in self.dataset_partition_target_counts:
            if not isinstance(dataset_id, str) or not dataset_id.strip():
                raise ValueError("dataset count entries require a dataset_id.")
            if partition not in ("fit", "dev", "calibration"):
                raise ValueError("dataset count entries require a train partition.")
            if type(target) is not int or target not in (0, 1):
                raise ValueError("dataset count entries require target 0 or 1.")
            if type(count) is not int or count <= 0:
                raise ValueError("dataset count entries require a positive count.")
            observed_targets += count
        if observed_targets != self.supervised_noteons:
            raise ValueError("dataset/partition/target counts must reconcile supervision.")
        numeric_fields = (
            "recordings",
            "total_attempts",
            "retained_attempts",
            "dropped_attempts",
            "decoder_noteons",
            "instrumented_decoder_noteons",
            "uninstrumented_decoder_noteons",
            "gate_eligible_emitted_noteons",
            "excluded_invalid_frame",
            "excluded_outside_audio",
            "supervised_noteons",
            "positive_targets",
            "negative_targets",
            "reference_noteons",
            "matched_reference_noteons",
            "missed_reference_noteons",
        )
        for name in numeric_fields:
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative JSON-native integer.")
        if self.recordings == 0:
            raise ValueError("recordings must be positive.")
        if self.total_attempts != self.retained_attempts + self.dropped_attempts:
            raise ValueError("attempt counters must reconcile retained plus dropped rows.")
        if self.decoder_noteons != (
            self.instrumented_decoder_noteons + self.uninstrumented_decoder_noteons
        ):
            raise ValueError("decoder NoteOn counters must reconcile instrumentation.")
        if (
            type(self.uninstrumented_decoder_noteons_by_reason) is not tuple
            or tuple(sorted(self.uninstrumented_decoder_noteons_by_reason))
            != self.uninstrumented_decoder_noteons_by_reason
        ):
            raise ValueError("uninstrumented NoteOn reasons must be a sorted tuple.")
        reason_total = 0
        for reason, count in self.uninstrumented_decoder_noteons_by_reason:
            if not isinstance(reason, str) or not reason:
                raise ValueError("uninstrumented NoteOn reason must be non-empty.")
            if type(count) is not int or count <= 0:
                raise ValueError("uninstrumented NoteOn reason count must be positive.")
            reason_total += count
        if reason_total != self.uninstrumented_decoder_noteons:
            raise ValueError("uninstrumented NoteOn reasons must reconcile their count.")
        if self.gate_eligible_emitted_noteons != (
            self.supervised_noteons
            + self.excluded_invalid_frame
            + self.excluded_outside_audio
        ):
            raise ValueError("supervision counters must reconcile emitted NoteOns.")
        if self.supervised_noteons != self.positive_targets + self.negative_targets:
            raise ValueError("supervised targets must reconcile positives and negatives.")
        if self.reference_noteons != (
            self.matched_reference_noteons + self.missed_reference_noteons
        ):
            raise ValueError("reference NoteOn counters must reconcile matches and misses.")
        if self.matched_reference_noteons != self.positive_targets:
            raise ValueError("matched references must equal positive targets.")

    @classmethod
    def from_batches(
        cls,
        batches: Iterable[CausalCandidateLabelBatch],
    ) -> "DecoderCandidateMiningCounters":
        values = tuple(batches)
        if not values:
            raise ValueError("at least one labeled candidate batch is required.")
        if not all(isinstance(batch, CausalCandidateLabelBatch) for batch in values):
            raise ValueError("batches must contain only CausalCandidateLabelBatch values.")
        for batch in values:
            batch.require_complete()
        manifest_sha256s = {batch.manifest_sha256 for batch in values}
        plan_sha256s = {batch.partition_plan_sha256 for batch in values}
        if len(manifest_sha256s) != 1 or len(plan_sha256s) != 1:
            raise RuntimeError(
                "Fail closed: candidate batches mix manifest or partition-plan provenance."
            )
        recording_identities = tuple(sorted(batch.recording_identity for batch in values))
        if len(set(recording_identities)) != len(recording_identities):
            raise RuntimeError(
                "Fail closed: candidate batches duplicate a recording identity."
            )
        event_ids = [
            str(label.attempt.event_id)
            for batch in values
            for label in batch.labels
        ]
        if len(set(event_ids)) != len(event_ids):
            raise RuntimeError(
                "Fail closed: candidate batches duplicate a trainable event_id."
            )
        reason_counts: Counter[str] = Counter()
        target_counts: Counter[tuple[str, str, int]] = Counter()
        for batch in values:
            reason_counts.update(dict(batch.uninstrumented_decoder_noteons_by_reason))
            target_counts.update(
                (batch.recording_identity[0], batch.partition, label.causal_noteon_target)
                for label in batch.labels
            )
        return cls(
            manifest_sha256=next(iter(manifest_sha256s)),
            partition_plan_sha256=next(iter(plan_sha256s)),
            recording_identities=recording_identities,
            dataset_partition_target_counts=tuple(
                sorted(
                    (dataset_id, partition, target, count)
                    for (dataset_id, partition, target), count in target_counts.items()
                )
            ),
            recordings=len(values),
            total_attempts=sum(batch.total_attempts for batch in values),
            retained_attempts=sum(batch.retained_attempts for batch in values),
            dropped_attempts=sum(batch.dropped_attempts for batch in values),
            decoder_noteons=sum(batch.decoder_noteons for batch in values),
            instrumented_decoder_noteons=sum(
                batch.instrumented_decoder_noteons for batch in values
            ),
            uninstrumented_decoder_noteons=sum(
                batch.uninstrumented_decoder_noteons for batch in values
            ),
            uninstrumented_decoder_noteons_by_reason=tuple(sorted(reason_counts.items())),
            gate_eligible_emitted_noteons=sum(
                batch.gate_eligible_emitted_noteons for batch in values
            ),
            excluded_invalid_frame=sum(batch.excluded_invalid_frame for batch in values),
            excluded_outside_audio=sum(batch.excluded_outside_audio for batch in values),
            supervised_noteons=sum(len(batch.labels) for batch in values),
            positive_targets=sum(batch.positive_targets for batch in values),
            negative_targets=sum(batch.negative_targets for batch in values),
            reference_noteons=sum(batch.reference_noteons for batch in values),
            matched_reference_noteons=sum(
                batch.matched_reference_noteons for batch in values
            ),
            missed_reference_noteons=sum(
                batch.missed_reference_noteons for batch in values
            ),
        )

    def require_authorizable_train_only_artifact(self) -> None:
        """Reject incomplete or one-class output before it can become an artifact."""
        if self.dropped_attempts:
            raise RuntimeError("Decoder candidate collection overflowed; refuse artifact.")
        unexpected_reasons = set(
            reason for reason, _ in self.uninstrumented_decoder_noteons_by_reason
        ) - ALLOWED_UNINSTRUMENTED_NOTEON_REASONS
        if unexpected_reasons:
            raise RuntimeError(
                "Fail closed: artifact contains uninstrumented NoteOns outside the "
                "documented retrigger exclusion."
            )
        if self.supervised_noteons == 0:
            raise RuntimeError("No trainable emitted NoteOns were supervised.")
        if self.positive_targets == 0 or self.negative_targets == 0:
            raise RuntimeError(
                "Train-only candidate artifact requires both causal target classes."
            )

    def require_full_decoder_noteon_coverage(self) -> None:
        """Optional stricter gate for an experiment that claims all NoteOns."""
        if self.uninstrumented_decoder_noteons:
            raise RuntimeError(
                "Decoder emitted NoteOns outside the instrumented candidate population."
            )


def _event_noteon_reasons(
    events: Sequence[MidiEventLike],
) -> dict[tuple[int, int], str]:
    reasons: dict[tuple[int, int], str] = {}
    for event in events:
        kind = getattr(event, "kind", None)
        pitch = getattr(event, "pitch", None)
        frame_index = getattr(event, "frame_index", None)
        if not isinstance(kind, str):
            raise ValueError("decoder event kind must be a string.")
        if type(pitch) is not int or not 0 <= pitch <= 127:
            raise ValueError("decoder event pitch must be a MIDI integer in [0, 127].")
        if type(frame_index) is not int or frame_index < 0:
            raise ValueError("decoder event frame_index must be a non-negative integer.")
        if kind == "note_on":
            reason = getattr(event, "reason", None)
            if not isinstance(reason, str) or not reason:
                raise ValueError("decoder NoteOn reason must be a non-empty string.")
            coordinate = (frame_index, pitch)
            if coordinate in reasons:
                raise RuntimeError(
                    "Fail closed: decoder emitted duplicate NoteOn frame/pitch coordinates."
                )
            reasons[coordinate] = reason
    return reasons


def _require_event_subset(
    attempts: Iterable[DecoderCandidateAttempt],
    event_coordinates: Counter[tuple[int, int]],
) -> Counter[tuple[int, int]]:
    observed = Counter(
        (attempt.frame_index, attempt.pitch)
        for attempt in attempts
        if attempt.emitted_noteon
    )
    for coordinate, count in observed.items():
        if count > event_coordinates[coordinate]:
            raise RuntimeError(
                "Fail closed: instrumented emitted candidate has no matching "
                "decoder NoteOn event."
            )
    return observed


def _matching_label(
    attempt: DecoderCandidateAttempt,
    match: CausalNoteOnMatch | None,
) -> LabeledDecoderCandidateEvent:
    if match is None:
        return LabeledDecoderCandidateEvent(
            attempt=attempt,
            causal_noteon_target=0,
            matched_reference_index=None,
            causal_latency_ms=None,
        )
    return LabeledDecoderCandidateEvent(
        attempt=attempt,
        causal_noteon_target=1,
        matched_reference_index=match.reference_index,
        causal_latency_ms=match.latency_ms,
    )


def _frame_is_valid(value: object) -> bool:
    """Accept only the 0/1 label encoding, including NumPy integer scalars."""
    if isinstance(value, bool):
        return value
    try:
        encoded = operator.index(value)
    except TypeError as exc:
        raise ValueError("frame_valid values must be boolean or integer 0/1.") from exc
    if encoded not in (0, 1):
        raise ValueError("frame_valid values must be boolean or integer 0/1.")
    return bool(encoded)


def label_emitted_decoder_candidates(
    batch: DecoderCandidateBatch,
    reference: Sequence[ReferenceNote],
    *,
    frame_valid: Sequence[object],
    sample_rate: int,
    hop_size: int,
    audio_frames: int,
    emitted_events: Sequence[MidiEventLike],
    candidate_collection_error: str | None,
) -> CausalCandidateLabelBatch:
    """Create causal 1/0 targets only for real, supervisable decoder NoteOns.

    Invalid and beyond-audio frames are counted as excluded rather than being
    mislabeled as false NoteOns.  The matcher is strictly causal and
    one-to-one; no future reference or symmetric onset tolerance is used.
    """
    if not isinstance(batch, DecoderCandidateBatch):
        raise ValueError("batch must be DecoderCandidateBatch.")
    if candidate_collection_error is not None:
        if not isinstance(candidate_collection_error, str) or not candidate_collection_error:
            raise ValueError(
                "candidate_collection_error must be None or a non-empty error string."
            )
        raise RuntimeError(
            "Fail closed: decoder candidate collection reported an error: "
            f"{candidate_collection_error}."
        )
    batch.require_complete()
    # Validate timing even for a recording which happens to emit no candidates.
    decoder_event_time_s(0, sample_rate=sample_rate, hop_size=hop_size)
    if type(audio_frames) is not int or audio_frames <= 0:
        raise ValueError("audio_frames must be a positive JSON-native integer.")
    if not all(isinstance(note, ReferenceNote) for note in reference):
        raise ValueError("reference must contain only ReferenceNote values.")
    valid = tuple(frame_valid)
    if not valid:
        raise ValueError("frame_valid must contain at least one frame.")
    event_reasons = _event_noteon_reasons(emitted_events)
    event_coordinates = Counter(event_reasons.keys())
    instrumented_coordinates = _require_event_subset(
        batch.attempts, event_coordinates
    )
    selected = select_trainable_emitted_events(batch.attempts)
    selected_coordinates = Counter(
        (attempt.frame_index, attempt.pitch) for attempt in selected
    )
    for coordinate, count in selected_coordinates.items():
        if count > event_coordinates[coordinate]:
            raise RuntimeError(
                "Fail closed: trainable emitted candidate has no matching decoder NoteOn."
            )

    supervised: list[DecoderCandidateAttempt] = []
    excluded_invalid_frame = 0
    excluded_outside_audio = 0
    for attempt in selected:
        if (
            attempt.frame_index >= len(valid)
            or not _frame_is_valid(valid[attempt.frame_index])
        ):
            excluded_invalid_frame += 1
            continue
        if (attempt.frame_index + 1) * hop_size > audio_frames:
            excluded_outside_audio += 1
            continue
        supervised.append(attempt)

    predictions = tuple(
        NoteOnPrediction(
            attempt.pitch,
            decoder_event_time_s(
                attempt.frame_index, sample_rate=sample_rate, hop_size=hop_size
            ),
        )
        for attempt in supervised
    )
    result = match_causal_note_ons(
        tuple(reference), predictions, max_latency_ms=CAUSAL_MAX_LATENCY_MS
    )
    by_prediction = {match.prediction_index: match for match in result.matches}
    false_indices = set(result.false_prediction_indices)
    expected_indices = set(range(len(predictions)))
    if set(by_prediction) & false_indices or set(by_prediction) | false_indices != expected_indices:
        raise AssertionError("causal matcher did not partition supervised predictions.")
    labels = tuple(
        _matching_label(attempt, by_prediction.get(index))
        for index, attempt in enumerate(supervised)
    )
    uninstrumented_coordinates = event_coordinates - instrumented_coordinates
    uninstrumented_reason_counts = Counter(
        event_reasons[coordinate] for coordinate in uninstrumented_coordinates
    )
    uninstrumented = sum(uninstrumented_coordinates.values())
    return CausalCandidateLabelBatch(
        manifest_sha256=batch.manifest_sha256,
        partition_plan_sha256=batch.partition_plan_sha256,
        recording_identity=batch.recording_identity,
        partition=batch.partition,
        labels=labels,
        total_attempts=batch.total_attempts,
        retained_attempts=len(batch.attempts),
        dropped_attempts=batch.dropped_attempts,
        decoder_noteons=len(event_reasons),
        instrumented_decoder_noteons=sum(instrumented_coordinates.values()),
        uninstrumented_decoder_noteons=uninstrumented,
        uninstrumented_decoder_noteons_by_reason=tuple(
            sorted(uninstrumented_reason_counts.items())
        ),
        gate_eligible_emitted_noteons=len(selected),
        excluded_invalid_frame=excluded_invalid_frame,
        excluded_outside_audio=excluded_outside_audio,
        reference_noteons=len(reference),
        matched_reference_noteons=len(result.matches),
        missed_reference_noteons=len(result.missed_reference_indices),
    )


def candidate_feature_names() -> tuple[str, ...]:
    """Return exactly the pre-gate causal model inputs allowed downstream."""
    prohibited = {
        DECODER_CANDIDATE_TARGET_FIELD,
        "matched_reference_index",
        "causal_latency_ms",
        "event_id",
        "gate_eligible",
        *POST_GATE_METADATA_FIELDS,
        *PROVENANCE_FIELDS,
    }
    if set(CAUSAL_FEATURES) & prohibited:
        raise AssertionError("candidate feature contract leaks target or decision metadata.")
    return tuple(CAUSAL_FEATURES)


def causal_reference_notes_from_label_arrays(
    arrays: Mapping[str, object],
) -> tuple[ReferenceNote, ...]:
    """Convert only evaluation-valid label intervals into causal references.

    This deliberately mirrors the event evaluator's ``truth_notes`` contract
    without importing its TensorFlow/model stack into the pure candidate-label
    protocol.  In particular, a row with ``note_evaluation_valid=0`` cannot
    become a positive target merely because it is temporally close.
    """
    if not isinstance(arrays, Mapping):
        raise ValueError("label arrays must be a mapping.")
    required = {
        "note_pitch_midi",
        "note_start_s",
        "note_end_s",
        "note_evaluation_valid",
    }
    missing = required - set(arrays)
    if missing:
        raise ValueError(f"Event label arrays missing: {sorted(missing)}")
    return tuple(
        ReferenceNote(int(pitch), float(start), float(end))
        for pitch, start, end, valid in zip(
            arrays["note_pitch_midi"],
            arrays["note_start_s"],
            arrays["note_end_s"],
            arrays["note_evaluation_valid"],
        )
        if valid and end > start
    )


__all__ = [
    "ALLOWED_UNINSTRUMENTED_NOTEON_REASONS",
    "CAUSAL_MATCHING_POLICY",
    "CAUSAL_MAX_LATENCY_MS",
    "CausalCandidateLabelBatch",
    "DECODER_CANDIDATE_LABEL_SCHEMA_VERSION",
    "DECODER_CANDIDATE_TARGET_FIELD",
    "DECODER_CANDIDATE_TIMESTAMP_POLICY",
    "DecoderCandidateMiningCounters",
    "LabeledDecoderCandidateEvent",
    "candidate_feature_names",
    "causal_reference_notes_from_label_arrays",
    "decoder_event_time_s",
    "label_emitted_decoder_candidates",
    "require_candidate_mining_baseline_decoder_config",
]
