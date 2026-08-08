from __future__ import annotations

from dataclasses import replace
from types import SimpleNamespace
import unittest

import numpy as np

from src.polyphonic.causal_event_metrics import ReferenceNote
from src.polyphonic.decoder_candidate_labels import (
    ALLOWED_UNINSTRUMENTED_NOTEON_REASONS,
    DECODER_CANDIDATE_TARGET_FIELD,
    DecoderCandidateMiningCounters,
    candidate_feature_names,
    causal_reference_notes_from_label_arrays,
    decoder_event_time_s,
    label_emitted_decoder_candidates,
    require_candidate_mining_baseline_decoder_config,
)
from src.polyphonic.decoder_candidate_mining import (
    CAUSAL_FEATURES,
    POST_GATE_METADATA_FIELDS,
    PROVENANCE_FIELDS,
    DecoderCandidateAttempt,
    DecoderCandidateBatch,
)


def _attempt(
    *,
    frame_index: int = 0,
    pitch: int = 60,
    event_id: str = "decoder-noteon-v2:0",
    gate_eligible: bool = True,
    emitted_noteon: bool = True,
    source_id: str = "source",
    dataset_id: str = "corpus",
    capture_id: str = "capture",
    partition: str = "fit",
) -> DecoderCandidateAttempt:
    return DecoderCandidateAttempt(
        source_id=source_id,
        dataset_id=dataset_id,
        group_id="group",
        capture_id=capture_id,
        leakage_group_key="corpus:group:group",
        partition=partition,
        frame_index=frame_index,
        pitch=pitch,
        candidate_reason="model_onset",
        candidate_score=0.8,
        frame_probability=0.7,
        onset_probability=0.8,
        harmonic_support=0.2,
        audio_onset_available=True,
        audio_onset_recent=True,
        active_polyphony=1,
        gate_eligible=gate_eligible,
        post_gate_rank=0 if emitted_noteon else None,
        post_gate_selected=emitted_noteon,
        emitted_noteon=emitted_noteon,
        event_id=event_id if emitted_noteon else None,
    )


def _batch(*attempts: DecoderCandidateAttempt, dropped_attempts: int = 0) -> DecoderCandidateBatch:
    identity = (
        attempts[0].dataset_id,
        attempts[0].source_id,
        attempts[0].capture_id,
    ) if attempts else ("corpus", "source", "capture")
    partition = attempts[0].partition if attempts else "fit"
    return DecoderCandidateBatch(
        attempts=tuple(attempts),
        total_attempts=len(attempts) + dropped_attempts,
        dropped_attempts=dropped_attempts,
        manifest_sha256="a" * 64,
        partition_plan_sha256="b" * 64,
        recording_identity=identity,
        partition=partition,
    )


def _note_on(
    frame_index: int,
    pitch: int,
    reason: str = "model_onset",
) -> SimpleNamespace:
    return SimpleNamespace(
        kind="note_on", frame_index=frame_index, pitch=pitch, reason=reason
    )


class DecoderCandidateLabelsTests(unittest.TestCase):
    def test_frame_zero_uses_end_of_hop_timing_and_never_credits_future_reference(self) -> None:
        attempt = _attempt(frame_index=0)
        result = label_emitted_decoder_candidates(
            _batch(attempt),
            [ReferenceNote(60, 0.1, 0.3)],
            frame_valid=[True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 60)],
            candidate_collection_error=None,
        )
        self.assertEqual(decoder_event_time_s(0, sample_rate=100, hop_size=10), 0.1)
        self.assertEqual(result.labels[0].causal_noteon_target, 1)
        self.assertEqual(result.labels[0].causal_latency_ms, 0.0)

        future_reference = label_emitted_decoder_candidates(
            _batch(attempt),
            [ReferenceNote(60, 0.101, 0.3)],
            frame_valid=[True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 60)],
            candidate_collection_error=None,
        )
        self.assertEqual(future_reference.labels[0].causal_noteon_target, 0)

    def test_causal_latency_boundary_and_latest_retrigger_reference_are_exact(self) -> None:
        at_boundary = _attempt(frame_index=30, event_id="decoder-noteon-v2:boundary")
        accepted = label_emitted_decoder_candidates(
            _batch(at_boundary),
            [ReferenceNote(60, 2.85, 3.5)],
            frame_valid=[True] * 31,
            sample_rate=100,
            hop_size=10,
            audio_frames=400,
            emitted_events=[_note_on(30, 60)],
            candidate_collection_error=None,
        )
        self.assertEqual(accepted.labels[0].causal_noteon_target, 1)
        self.assertAlmostEqual(accepted.labels[0].causal_latency_ms, 250.0)

        rejected = label_emitted_decoder_candidates(
            _batch(at_boundary),
            [ReferenceNote(60, 2.849, 3.5)],
            frame_valid=[True] * 31,
            sample_rate=100,
            hop_size=10,
            audio_frames=400,
            emitted_events=[_note_on(30, 60)],
            candidate_collection_error=None,
        )
        self.assertEqual(rejected.labels[0].causal_noteon_target, 0)

        first = _attempt(frame_index=10, event_id="decoder-noteon-v2:first")
        second = _attempt(frame_index=20, event_id="decoder-noteon-v2:second")
        retriggered = label_emitted_decoder_candidates(
            _batch(first, second),
            [
                ReferenceNote(60, 0.9, 1.05),
                ReferenceNote(60, 1.0, 1.2),
                ReferenceNote(60, 2.0, 2.2),
            ],
            frame_valid=[True] * 21,
            sample_rate=100,
            hop_size=10,
            audio_frames=300,
            emitted_events=[_note_on(10, 60), _note_on(20, 60)],
            candidate_collection_error=None,
        )
        self.assertEqual(
            [label.matched_reference_index for label in retriggered.labels], [1, 2]
        )
        self.assertEqual(retriggered.missed_reference_noteons, 1)

    def test_invalid_and_beyond_audio_frames_are_excluded_not_labeled_negative(self) -> None:
        invalid = _attempt(frame_index=0, event_id="decoder-noteon-v2:invalid")
        outside = _attempt(frame_index=3, event_id="decoder-noteon-v2:outside")
        result = label_emitted_decoder_candidates(
            _batch(invalid, outside),
            [],
            frame_valid=[False, True, True, True],
            sample_rate=100,
            hop_size=10,
            audio_frames=30,
            emitted_events=[_note_on(0, 60), _note_on(3, 60)],
            candidate_collection_error=None,
        )
        self.assertEqual(result.labels, ())
        self.assertEqual(result.excluded_invalid_frame, 1)
        self.assertEqual(result.excluded_outside_audio, 1)
        self.assertEqual(result.negative_targets, 0)

    def test_retrigger_is_counted_but_another_missing_trace_fails_closed(self) -> None:
        attempt = _attempt()
        retrigger_exclusion = label_emitted_decoder_candidates(
            _batch(attempt),
            [],
            frame_valid=[True, True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 60), _note_on(1, 61, "retrigger")],
            candidate_collection_error=None,
        )
        self.assertEqual(retrigger_exclusion.uninstrumented_decoder_noteons, 1)
        self.assertEqual(
            retrigger_exclusion.uninstrumented_decoder_noteons_by_reason,
            (("retrigger", 1),),
        )
        self.assertEqual(ALLOWED_UNINSTRUMENTED_NOTEON_REASONS, frozenset({"retrigger"}))
        retrigger_exclusion.require_complete()
        with self.assertRaisesRegex(RuntimeError, "outside the instrumented"):
            retrigger_exclusion.require_full_decoder_noteon_coverage()

        with self.assertRaisesRegex(RuntimeError, "documented retrigger"):
            label_emitted_decoder_candidates(
                _batch(attempt),
                [],
                frame_valid=[True, True],
                sample_rate=100,
                hop_size=10,
                audio_frames=100,
                emitted_events=[_note_on(0, 60), _note_on(1, 61, "model_onset")],
                candidate_collection_error=None,
            ).require_complete()

    def test_overflow_collection_error_and_missing_event_are_never_labeled(self) -> None:
        attempt = _attempt()
        with self.assertRaisesRegex(RuntimeError, "overflowed"):
            label_emitted_decoder_candidates(
                _batch(attempt, dropped_attempts=1),
                [],
                frame_valid=[True],
                sample_rate=100,
                hop_size=10,
                audio_frames=100,
                emitted_events=[_note_on(0, 60)],
                candidate_collection_error=None,
            )
        with self.assertRaisesRegex(RuntimeError, "collection reported an error"):
            label_emitted_decoder_candidates(
                _batch(attempt),
                [],
                frame_valid=[True],
                sample_rate=100,
                hop_size=10,
                audio_frames=100,
                emitted_events=[_note_on(0, 60)],
                candidate_collection_error="RuntimeError: collector is busy",
            )
        with self.assertRaisesRegex(RuntimeError, "no matching decoder NoteOn"):
            label_emitted_decoder_candidates(
                _batch(attempt),
                [],
                frame_valid=[True],
                sample_rate=100,
                hop_size=10,
                audio_frames=100,
                emitted_events=[],
                candidate_collection_error=None,
            )

    def test_run_counters_require_complete_two_class_train_only_output(self) -> None:
        positive = label_emitted_decoder_candidates(
            _batch(_attempt(
                event_id="decoder-noteon-v2:positive",
                source_id="positive-source",
                capture_id="positive-capture",
            )),
            [ReferenceNote(60, 0.1, 0.3)],
            frame_valid=[True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 60)],
            candidate_collection_error=None,
        )
        negative = label_emitted_decoder_candidates(
            _batch(_attempt(
                pitch=61,
                event_id="decoder-noteon-v2:negative",
                source_id="negative-source",
                capture_id="negative-capture",
            )),
            [],
            frame_valid=[True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 61)],
            candidate_collection_error=None,
        )
        counters = DecoderCandidateMiningCounters.from_batches((positive, negative))
        self.assertEqual(counters.positive_targets, 1)
        self.assertEqual(counters.negative_targets, 1)
        self.assertEqual(
            counters.dataset_partition_target_counts,
            (("corpus", "fit", 0, 1), ("corpus", "fit", 1, 1)),
        )
        counters.require_authorizable_train_only_artifact()

        with self.assertRaisesRegex(RuntimeError, "duplicate a recording"):
            DecoderCandidateMiningCounters.from_batches((positive, positive))
        with self.assertRaisesRegex(RuntimeError, "mix manifest"):
            DecoderCandidateMiningCounters.from_batches((
                positive,
                replace(negative, manifest_sha256="c" * 64),
            ))

        duplicate_event_other_recording = label_emitted_decoder_candidates(
            _batch(_attempt(
                event_id="decoder-noteon-v2:positive",
                source_id="other-source",
                capture_id="other-capture",
            )),
            [],
            frame_valid=[True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 60)],
            candidate_collection_error=None,
        )
        with self.assertRaisesRegex(RuntimeError, "duplicate a trainable event_id"):
            DecoderCandidateMiningCounters.from_batches((
                positive,
                duplicate_event_other_recording,
            ))

    def test_baseline_gate_and_feature_contract_fail_closed(self) -> None:
        require_candidate_mining_baseline_decoder_config(
            {"independent_note_threshold": None}
        )
        with self.assertRaisesRegex(RuntimeError, "threshold=null"):
            require_candidate_mining_baseline_decoder_config(
                {"independent_note_threshold": 0.01}
            )
        with self.assertRaisesRegex(ValueError, "explicitly declare"):
            require_candidate_mining_baseline_decoder_config({})
        features = candidate_feature_names()
        self.assertEqual(features, CAUSAL_FEATURES)
        self.assertNotIn(DECODER_CANDIDATE_TARGET_FIELD, features)
        self.assertFalse(set(features) & set(POST_GATE_METADATA_FIELDS))
        self.assertFalse(set(features) & set(PROVENANCE_FIELDS))
        labeled = label_emitted_decoder_candidates(
            _batch(_attempt()),
            [],
            frame_valid=[True],
            sample_rate=100,
            hop_size=10,
            audio_frames=100,
            emitted_events=[_note_on(0, 60)],
            candidate_collection_error=None,
        ).labels[0]
        self.assertEqual(tuple(labeled.model_features()), CAUSAL_FEATURES)
        self.assertEqual(set(labeled.model_features()), set(CAUSAL_FEATURES))

    def test_reference_conversion_excludes_not_evaluation_valid_intervals(self) -> None:
        references = causal_reference_notes_from_label_arrays({
            "note_pitch_midi": np.asarray([60, 61], dtype=np.int32),
            "note_start_s": np.asarray([0.1, 0.2], dtype=np.float32),
            "note_end_s": np.asarray([0.4, 0.5], dtype=np.float32),
            "note_evaluation_valid": np.asarray([0, 1], dtype=np.uint8),
        })
        self.assertEqual([note.pitch for note in references], [61])


if __name__ == "__main__":
    unittest.main()
