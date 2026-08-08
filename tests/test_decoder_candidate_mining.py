from dataclasses import fields
import unittest

from src.polyphonic.decoder_candidate_mining import (
    CAUSAL_FEATURES,
    POST_GATE_METADATA_FIELDS,
    DecoderCandidateAttempt,
    collapse_emitted_candidate_episodes,
)


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

    def test_row_invariants_fail_closed(self):
        invalid_rows = (
            {"frame_probability": 1.1},
            {"candidate_score": float("nan")},
            {"active_polyphony": 1.5},
            {"gate_eligible": 1},
            {"audio_onset_available": False, "audio_onset_recent": True},
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
