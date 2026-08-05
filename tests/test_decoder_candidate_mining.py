import unittest

from src.polyphonic.decoder_candidate_mining import (
    DecoderCandidateAttempt, collapse_emitted_candidate_episodes,
)


class CandidateMiningContractTests(unittest.TestCase):
    def test_masks_non_emitted_and_collapses_contiguous_episode(self):
        base = dict(recording_key="r", leakage_group_key="g", corpus_id="c", pitch=60,
                    reason="model_onset", harmonic_support=.8, gate_eligible=True,
                    rank=0, selected=True)
        rows = [
            DecoderCandidateAttempt(frame_index=2, score=.6, emitted_noteon=True, event_id="e", **base),
            DecoderCandidateAttempt(frame_index=3, score=.9, emitted_noteon=True, event_id="e", **base),
            DecoderCandidateAttempt(frame_index=4, score=.99, emitted_noteon=False, event_id=None, **base),
        ]
        result = collapse_emitted_candidate_episodes(rows)
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0].frame_index, 3)


if __name__ == "__main__":
    unittest.main()
