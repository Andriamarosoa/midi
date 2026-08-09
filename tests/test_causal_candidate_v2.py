from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.decoder import (
    CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON,
    CausalCandidateGateInput,
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
)


class CausalCandidateV2Tests(unittest.TestCase):
    @staticmethod
    def _config() -> PolyphonicDecoderConfig:
        return PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=62,
            frame_on_threshold=0.5,
            strong_frame_threshold=0.8,
            frame_off_threshold=0.25,
            onset_threshold=0.5,
            activation_frames=1,
            release_frames=2,
            minimum_retrigger_frames=3,
            silence_release_frames=2,
            maximum_polyphony=2,
            harmonic_support_threshold=0.0,
            chord_release_grace_frames=7,
            chord_formation_frames=1,
        )

    @staticmethod
    def _decoder_state(decoder: PolyphonicDecoder) -> dict[str, object]:
        state: dict[str, object] = {}
        for name, value in vars(decoder).items():
            if name in {
                "_causal_candidate_gate",
                "_causal_candidate_gate_placement",
            }:
                continue
            if isinstance(value, np.ndarray):
                state[name] = (value.dtype.str, value.shape, value.tobytes())
            elif isinstance(value, list):
                state[name] = tuple(value)
            else:
                state[name] = value
        return state

    @staticmethod
    def _three_ranked_candidates() -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        return (
            np.asarray([0.99, 0.90, 0.80], dtype=np.float32),
            np.asarray([0.99, 0.90, 0.80], dtype=np.float32),
            np.zeros((3, 1), dtype=np.float32),
        )

    def test_unknown_v2_placement_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "Unknown causal candidate gate placement"):
            PolyphonicDecoder(
                self._config(),
                causal_candidate_gate_placement="after_noteon",
            )

    def test_disabled_v2_is_strictly_identical_in_audio_and_legacy_paths(self) -> None:
        for audio_aware in (False, True):
            with self.subTest(audio_aware=audio_aware):
                reference = PolyphonicDecoder(self._config())
                v2_disabled = PolyphonicDecoder(
                    self._config(),
                    causal_candidate_gate_placement=(
                        CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
                    ),
                )
                generator = np.random.default_rng(20260810)
                for frame_index in range(12):
                    frame = generator.random(3, dtype=np.float32)
                    onset = generator.random(3, dtype=np.float32)
                    harmonic = generator.random((3, 1), dtype=np.float32)
                    kwargs: dict[str, object] = {
                        "audio_active": frame_index != 9,
                        "audio_hop_index": frame_index,
                    }
                    if audio_aware:
                        kwargs["audio_onset"] = frame_index % 3 == 0
                        kwargs["audio_onset_hop_index"] = (
                            frame_index if frame_index % 3 == 0 else None
                        )
                    self.assertEqual(
                        reference.step(frame, onset, harmonic, **kwargs),
                        v2_disabled.step(frame, onset, harmonic, **kwargs),
                    )
                    self.assertEqual(
                        self._decoder_state(reference),
                        self._decoder_state(v2_disabled),
                    )

    def test_default_v1_gate_remains_pre_ranking(self) -> None:
        seen: list[CausalCandidateGateInput] = []

        def reject_only_top(values: CausalCandidateGateInput) -> bool:
            seen.append(values)
            return values.candidate_score > 1.9

        decoder = PolyphonicDecoder(
            self._config(), causal_candidate_gate=reject_only_top
        )
        frame, onset, harmonic = self._three_ranked_candidates()

        events = decoder.step(frame, onset, harmonic, audio_onset=True)

        self.assertEqual([event.pitch for event in events], [61, 62])
        self.assertEqual(len(seen), 3)
        self.assertFalse(bool(decoder.active[0]))
        self.assertEqual(int(decoder.activation_count[0]), 0)

    def test_v2_audio_gate_follows_selection_preserves_evidence_and_no_backfill(
        self,
    ) -> None:
        seen: list[CausalCandidateGateInput] = []

        def reject_only_top(values: CausalCandidateGateInput) -> bool:
            seen.append(values)
            return values.candidate_score > 1.9

        decoder = PolyphonicDecoder(
            self._config(),
            causal_candidate_gate=reject_only_top,
            causal_candidate_gate_placement=(
                CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
            ),
        )
        frame, onset, harmonic = self._three_ranked_candidates()

        events = decoder.step(frame, onset, harmonic, audio_onset=True)

        self.assertEqual([event.pitch for event in events], [61])
        self.assertEqual([round(item.candidate_score, 2) for item in seen], [1.98, 1.8])
        self.assertEqual([item.active_polyphony for item in seen], [0, 0])
        self.assertTrue(all(item.candidate_reason == "model_onset" for item in seen))
        self.assertFalse(bool(decoder.active[0]))
        self.assertTrue(bool(decoder.active[1]))
        self.assertFalse(bool(decoder.active[2]))
        self.assertEqual(int(decoder.activation_count[0]), 1)
        self.assertTrue(bool(decoder.attack_activation_pending[0]))
        self.assertEqual(int(decoder.activation_count[2]), 1)
        self.assertTrue(bool(decoder.attack_activation_pending[2]))
        self.assertEqual(int(decoder.chord_release_grace[1]), 0)

    def test_v2_legacy_gate_follows_selection_and_preserves_evidence(self) -> None:
        seen: list[CausalCandidateGateInput] = []

        def reject_only_top(values: CausalCandidateGateInput) -> bool:
            seen.append(values)
            return values.candidate_score > 1.9

        decoder = PolyphonicDecoder(
            self._config(),
            causal_candidate_gate=reject_only_top,
            causal_candidate_gate_placement=(
                CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
            ),
        )
        frame, onset, harmonic = self._three_ranked_candidates()

        events = decoder.step(frame, onset, harmonic)

        self.assertEqual([event.pitch for event in events], [61])
        self.assertEqual([round(item.candidate_score, 2) for item in seen], [1.98, 1.8])
        self.assertTrue(all(not item.audio_onset_available for item in seen))
        self.assertTrue(all(item.candidate_reason == "legacy" for item in seen))
        self.assertFalse(bool(decoder.active[0]))
        self.assertTrue(bool(decoder.active[1]))
        self.assertFalse(bool(decoder.active[2]))
        self.assertEqual(int(decoder.activation_count[0]), 1)
        self.assertFalse(bool(decoder.attack_activation_pending[0]))
        self.assertEqual(int(decoder.activation_count[2]), 1)
        self.assertFalse(bool(decoder.attack_activation_pending[2]))

    def test_v2_uses_the_pre_ranking_snapshot_after_harmonic_reason_changes(
        self,
    ) -> None:
        seen: list[CausalCandidateGateInput] = []

        def accept_and_capture(values: CausalCandidateGateInput) -> bool:
            seen.append(values)
            return False

        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            frame_on_threshold=0.5,
            strong_frame_threshold=0.8,
            frame_off_threshold=0.25,
            onset_threshold=0.5,
            activation_frames=1,
            release_frames=2,
            minimum_retrigger_frames=3,
            silence_release_frames=2,
            maximum_polyphony=2,
            harmonic_support_threshold=0.6,
            harmonic_suppression_strength=0.25,
        )
        decoder = PolyphonicDecoder(
            config,
            causal_candidate_gate=accept_and_capture,
            causal_candidate_gate_placement=(
                CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
            ),
        )
        frame = np.zeros(13, dtype=np.float32)
        onset = np.zeros(13, dtype=np.float32)
        harmonic = np.zeros((13, 2), dtype=np.float32)
        frame[0], onset[0] = 0.90, 0.90
        frame[12], onset[12] = 0.86, 0.10
        harmonic[0, 1] = 0.80

        events = decoder.step(frame, onset, harmonic, audio_onset=True)

        emitted = {event.pitch: event for event in events}
        self.assertEqual(emitted[72].reason, "harmonic_strong_frame")
        self.assertEqual(len(seen), 1)
        snapshot = seen[0]
        self.assertEqual(snapshot.candidate_reason, "frame_attack")
        self.assertAlmostEqual(snapshot.candidate_score, 0.96, places=6)
        self.assertAlmostEqual(snapshot.harmonic_support, 0.80, places=6)
        self.assertEqual(snapshot.active_polyphony, 0)


if __name__ == "__main__":
    unittest.main()
