from dataclasses import fields
import unittest

from src.polyphonic.decoder_candidate_mining import (
    CANDIDATE_REASON_ENCODING,
    CANDIDATE_REASON_VOCABULARY,
    CAUSAL_FEATURES,
    POST_GATE_METADATA_FIELDS,
    DecoderCandidateAttempt,
    DecoderCandidateBatch,
    DecoderCandidateCollector,
    collapse_emitted_candidate_episodes,
)
from src.polyphonic.decoder_reason_codes import NOTE_ON_REASON_CODES


class CandidateMiningContractTests(unittest.TestCase):
    @staticmethod
    def row(**overrides):
        values = dict(
            recording_key="r",
            leakage_group_key="g",
            corpus_id="c",
            frame_index=2,
            pitch=60,
            candidate_reason="model_onset",
            candidate_score=0.6,
            frame_probability=0.7,
            onset_probability=0.8,
            harmonic_support=0.8,
            audio_onset_available=True,
            audio_onset_recent=True,
            active_polyphony=2,
            gate_eligible=True,
            post_gate_rank=0,
            post_gate_selected=True,
            emitted_noteon=True,
            event_id="e",
        )
        values.update(overrides)
        return DecoderCandidateAttempt(**values)

    def test_masks_non_emitted_and_collapses_contiguous_episode(self):
        rows = [
            self.row(frame_index=2, candidate_score=0.6),
            self.row(frame_index=3, candidate_score=0.9),
            self.row(
                frame_index=4,
                candidate_score=0.99,
                post_gate_selected=False,
                post_gate_rank=None,
                emitted_noteon=False,
                event_id=None,
            ),
        ]
        result = collapse_emitted_candidate_episodes(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].frame_index, 3)

    def test_decreasing_scores_do_not_split_a_contiguous_episode(self):
        rows = [
            self.row(frame_index=2, candidate_score=0.9),
            self.row(frame_index=3, candidate_score=0.8),
            self.row(frame_index=4, candidate_score=0.7),
        ]
        result = collapse_emitted_candidate_episodes(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].frame_index, 2)

    def test_distinct_event_ids_are_distinct_episodes(self):
        result = collapse_emitted_candidate_episodes(
            [
                self.row(frame_index=2, event_id="e1"),
                self.row(frame_index=3, event_id="e2"),
            ]
        )
        self.assertEqual([row.event_id for row in result], ["e1", "e2"])

    def test_causal_features_exist_and_exclude_post_gate_metadata(self):
        declared = {field.name for field in fields(DecoderCandidateAttempt)}
        self.assertTrue(set(CAUSAL_FEATURES) <= declared)
        self.assertTrue(set(POST_GATE_METADATA_FIELDS) <= declared)
        self.assertFalse(set(CAUSAL_FEATURES) & set(POST_GATE_METADATA_FIELDS))

    def test_candidate_reason_encoding_is_fixed_and_immutable(self):
        expected = (
            "model_onset",
            "frame_attack",
            "frame_fallback",
            "legacy",
            "chord_completion",
        )
        self.assertEqual(CANDIDATE_REASON_VOCABULARY, expected)
        self.assertEqual(
            dict(CANDIDATE_REASON_ENCODING),
            {
                "model_onset": 1,
                "frame_attack": 2,
                "frame_fallback": 3,
                "legacy": 6,
                "chord_completion": 7,
            },
        )
        self.assertEqual(NOTE_ON_REASON_CODES["harmonic_strong_frame"], 4)
        self.assertEqual(NOTE_ON_REASON_CODES["retrigger"], 5)
        with self.assertRaises(TypeError):
            CANDIDATE_REASON_ENCODING["new_reason"] = len(expected)

    def test_collector_is_bounded_drainable_and_uses_stable_event_ids(self):
        collector = DecoderCandidateCollector(
            recording_key="r",
            leakage_group_key="g",
            corpus_id="c",
            maximum_attempts=2,
        )
        for name, value in (
            ("recording_key", "other"),
            ("leakage_group_key", "other"),
            ("corpus_id", "other"),
            ("maximum_attempts", 3),
        ):
            with self.assertRaises(AttributeError):
                setattr(collector, name, value)
        recorded = []
        for frame_index in range(3):
            recorded.append(collector.record_candidate(
                frame_index=frame_index,
                pitch=60,
                candidate_reason="legacy",
                candidate_score=0.6,
                frame_probability=0.7,
                onset_probability=0.8,
                harmonic_support=0.0,
                audio_onset_available=False,
                audio_onset_recent=False,
                active_polyphony=0,
                gate_eligible=False,
                post_gate_rank=0,
                post_gate_selected=True,
                emitted_noteon=True,
            ))

        self.assertEqual(collector.total_attempts, 3)
        self.assertEqual(collector.dropped_attempts, 1)
        self.assertEqual(
            [row.frame_index for row in collector.attempts], [1, 2]
        )
        batch = collector.drain()
        self.assertEqual(len(batch.attempts), 2)
        self.assertEqual(batch.total_attempts, 3)
        self.assertEqual(batch.dropped_attempts, 1)
        self.assertFalse(batch.complete)
        with self.assertRaisesRegex(RuntimeError, "overflowed"):
            batch.require_complete()
        self.assertEqual(collector.attempts, ())
        self.assertEqual(collector.total_attempts, 3)

        repeated_collector = DecoderCandidateCollector(
            recording_key="r",
            leakage_group_key="g",
            corpus_id="c",
        )
        repeated = repeated_collector.record_candidate(
            frame_index=0,
            pitch=60,
            candidate_reason="legacy",
            candidate_score=0.6,
            frame_probability=0.7,
            onset_probability=0.8,
            harmonic_support=0.0,
            audio_onset_available=False,
            audio_onset_recent=False,
            active_polyphony=0,
            gate_eligible=False,
            post_gate_rank=0,
            post_gate_selected=True,
            emitted_noteon=True,
        )
        self.assertEqual(repeated.event_id, recorded[0].event_id)
        self.assertTrue(repeated.event_id.startswith("decoder-noteon-v1:"))
        complete_batch = repeated_collector.drain()
        complete_batch.require_complete()
        self.assertTrue(complete_batch.complete)

        with self.assertRaisesRegex(ValueError, "retained plus dropped"):
            DecoderCandidateBatch(
                attempts=(), total_attempts=1, dropped_attempts=0
            )

    def test_row_invariants_fail_closed(self):
        invalid_rows = (
            {"frame_probability": 1.1},
            {"candidate_score": float("nan")},
            {"active_polyphony": 1.5},
            {"gate_eligible": 1},
            {"audio_onset_available": False, "audio_onset_recent": True},
            {"candidate_reason": "runtime_order_dependent_reason"},
            {"post_gate_rank": -1},
            {"post_gate_selected": False, "emitted_noteon": True},
            {"emitted_noteon": False, "event_id": "e"},
        )
        for overrides in invalid_rows:
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    self.row(**overrides)


if __name__ == "__main__":
    unittest.main()
