from __future__ import annotations

from dataclasses import FrozenInstanceError, fields
import unittest

import numpy as np

from src.polyphonic.decoder import (
    CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON,
    CAUSAL_CANDIDATE_GATE_PRE_RANKING,
    PROVISIONAL_CONFIRM,
    PROVISIONAL_HOLD,
    PROVISIONAL_REJECT,
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
    ProvisionalObservation,
)


EXPECTED_OBSERVATION_FIELDS = (
    "pitch",
    "note_on_frame",
    "current_frame",
    "age_frames",
    "candidate_reason_at_noteon",
    "candidate_score_at_noteon",
    "frame_probability_at_noteon",
    "onset_probability_at_noteon",
    "current_frame_probability",
    "current_onset_probability",
    "audio_onset_available",
    "audio_onset_recent",
    "harmonic_support",
    "emitted_polyphony",
    "contextual_polyphony",
)


def _events(events) -> tuple[tuple[str, int, int, str], ...]:
    return tuple(
        (event.kind, event.pitch, event.frame_index, event.reason)
        for event in events
    )


class _RecordingResolver:
    def __init__(self) -> None:
        self.decisions: dict[int, str] = {}
        self.observations: list[ProvisionalObservation] = []

    def __call__(self, observation: ProvisionalObservation) -> str:
        self.observations.append(observation)
        return self.decisions.get(observation.pitch, PROVISIONAL_HOLD)


def _two_note_decoder(resolver) -> PolyphonicDecoder:
    return PolyphonicDecoder(
        PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=64,
            activation_frames=1,
            release_frames=3,
            maximum_polyphony=2,
        ),
        provisional_state_resolver=resolver,
    )


def _emit_two_provisionals(decoder: PolyphonicDecoder) -> None:
    probability = np.asarray([0.95, 0.0, 0.0, 0.0, 0.95], np.float32)
    events = decoder.step(probability, probability)
    if {event.pitch for event in events if event.kind == "note_on"} != {60, 64}:
        raise AssertionError("Synthetic setup did not emit both provisional notes.")


class ProvisionalResolutionH5H6ConformanceTests(unittest.TestCase):
    def test_observation_is_frozen_and_has_exactly_fifteen_fields(self) -> None:
        self.assertEqual(
            tuple(field.name for field in fields(ProvisionalObservation)),
            EXPECTED_OBSERVATION_FIELDS,
        )
        resolver = _RecordingResolver()
        decoder = PolyphonicDecoder(
            PolyphonicDecoderConfig(
                midi_min=60,
                midi_max=60,
                activation_frames=1,
                release_frames=3,
            ),
            provisional_state_resolver=resolver,
        )
        emitted = np.asarray([0.95], np.float32)
        decoder.step(emitted, emitted)
        decoder.step(
            np.asarray([0.40], np.float32),
            np.asarray([0.10], np.float32),
        )
        observation = resolver.observations[-1]
        with self.assertRaises(FrozenInstanceError):
            observation.pitch = 61  # type: ignore[misc]

    def test_noteon_evidence_is_frozen_and_current_values_are_current_only(self) -> None:
        resolver = _RecordingResolver()
        decoder = PolyphonicDecoder(
            PolyphonicDecoderConfig(
                midi_min=60,
                midi_max=60,
                activation_frames=1,
                release_frames=4,
            ),
            provisional_state_resolver=resolver,
        )
        noteon = np.asarray([0.95], np.float32)
        decoder.step(noteon, noteon)
        decoder.step(
            np.asarray([0.40], np.float32),
            np.asarray([0.10], np.float32),
        )
        first = resolver.observations[-1]
        decoder.step(
            np.asarray([0.70], np.float32),
            np.asarray([0.20], np.float32),
        )
        second = resolver.observations[-1]

        self.assertEqual(first.note_on_frame, 0)
        self.assertEqual((first.current_frame, first.age_frames), (1, 1))
        self.assertEqual((second.current_frame, second.age_frames), (2, 2))
        self.assertEqual(first.candidate_reason_at_noteon, "legacy")
        self.assertAlmostEqual(first.candidate_score_at_noteon, 1.90, places=6)
        self.assertAlmostEqual(first.frame_probability_at_noteon, 0.95, places=6)
        self.assertAlmostEqual(first.onset_probability_at_noteon, 0.95, places=6)
        self.assertEqual(
            (
                first.candidate_reason_at_noteon,
                first.candidate_score_at_noteon,
                first.frame_probability_at_noteon,
                first.onset_probability_at_noteon,
            ),
            (
                second.candidate_reason_at_noteon,
                second.candidate_score_at_noteon,
                second.frame_probability_at_noteon,
                second.onset_probability_at_noteon,
            ),
        )
        self.assertAlmostEqual(first.current_frame_probability, 0.40, places=6)
        self.assertAlmostEqual(first.current_onset_probability, 0.10, places=6)
        self.assertAlmostEqual(second.current_frame_probability, 0.70, places=6)
        self.assertAlmostEqual(second.current_onset_probability, 0.20, places=6)
        # The immutable t1 object is unaffected by the later t2 inputs.
        self.assertAlmostEqual(first.current_frame_probability, 0.40, places=6)

    def test_audio_availability_describes_current_hop_not_historical_latch(self) -> None:
        resolver = _RecordingResolver()
        decoder = PolyphonicDecoder(
            PolyphonicDecoderConfig(
                midi_min=60,
                midi_max=60,
                activation_frames=1,
                release_frames=4,
            ),
            provisional_state_resolver=resolver,
        )
        noteon = np.asarray([0.95], np.float32)
        decoder.step(
            noteon,
            noteon,
            audio_hop_index=0,
            audio_onset=True,
        )
        hold = np.asarray([0.40], np.float32)
        zero = np.asarray([0.0], np.float32)
        decoder.step(hold, zero, audio_hop_index=1)
        stale_latch_observation = resolver.observations[-1]
        self.assertTrue(decoder.audio_onset_available)
        self.assertFalse(stale_latch_observation.audio_onset_available)
        self.assertFalse(stale_latch_observation.audio_onset_recent)

        decoder.step(
            hold,
            zero,
            audio_hop_index=2,
            audio_onset=False,
        )
        current_hop_observation = resolver.observations[-1]
        self.assertTrue(current_hop_observation.audio_onset_available)
        self.assertTrue(current_hop_observation.audio_onset_recent)

    def test_multi_note_success_commits_only_after_shared_snapshot(self) -> None:
        resolver = _RecordingResolver()
        decoder = _two_note_decoder(resolver)
        _emit_two_provisionals(decoder)
        resolver.decisions = {60: PROVISIONAL_CONFIRM, 64: PROVISIONAL_REJECT}
        hold = np.asarray([0.40, 0.0, 0.0, 0.0, 0.40], np.float32)
        events = decoder.step(hold, np.zeros(5, np.float32))

        observations = resolver.observations[-2:]
        self.assertEqual([item.pitch for item in observations], [60, 64])
        self.assertEqual(
            [(item.emitted_polyphony, item.contextual_polyphony) for item in observations],
            [(2, 0), (2, 0)],
        )
        self.assertEqual(
            _events(events), (("note_off", 64, 1, "provisional_reject"),)
        )
        self.assertTrue(bool(decoder.active[0]))
        self.assertFalse(bool(decoder.provisional_active[0]))
        self.assertFalse(bool(decoder.active[4]))
        self.assertFalse(bool(decoder.provisional_active[4]))

    def test_invalid_later_result_causes_no_partial_resolution(self) -> None:
        calls: list[int] = []

        def resolver(observation: ProvisionalObservation) -> str:
            calls.append(observation.pitch)
            return PROVISIONAL_CONFIRM if observation.pitch == 60 else "INVALID"

        decoder = _two_note_decoder(resolver)
        _emit_two_provisionals(decoder)
        before_active = decoder.active.copy()
        before_provisional = decoder.provisional_active.copy()
        hold = np.asarray([0.40, 0.0, 0.0, 0.0, 0.40], np.float32)
        with self.assertRaisesRegex(ValueError, "HOLD, CONFIRM, or REJECT"):
            decoder.step(hold, np.zeros(5, np.float32))
        self.assertEqual(calls, [60, 64])
        np.testing.assert_array_equal(decoder.active, before_active)
        np.testing.assert_array_equal(decoder.provisional_active, before_provisional)

    def test_later_resolver_exception_causes_no_partial_resolution(self) -> None:
        calls: list[int] = []

        def resolver(observation: ProvisionalObservation) -> str:
            calls.append(observation.pitch)
            if observation.pitch == 64:
                raise RuntimeError("synthetic resolver failure")
            return PROVISIONAL_REJECT

        decoder = _two_note_decoder(resolver)
        _emit_two_provisionals(decoder)
        before_active = decoder.active.copy()
        before_provisional = decoder.provisional_active.copy()
        hold = np.asarray([0.40, 0.0, 0.0, 0.0, 0.40], np.float32)
        with self.assertRaisesRegex(RuntimeError, "synthetic resolver failure"):
            decoder.step(hold, np.zeros(5, np.float32))
        self.assertEqual(calls, [60, 64])
        np.testing.assert_array_equal(decoder.active, before_active)
        np.testing.assert_array_equal(decoder.provisional_active, before_provisional)

    def test_nonfinite_observation_fails_before_resolver_or_mutation(self) -> None:
        resolver = _RecordingResolver()
        decoder = PolyphonicDecoder(
            PolyphonicDecoderConfig(
                midi_min=60,
                midi_max=60,
                activation_frames=1,
                release_frames=3,
            ),
            provisional_state_resolver=resolver,
        )
        noteon = np.asarray([0.95], np.float32)
        decoder.step(noteon, noteon)
        with self.assertRaisesRegex(ValueError, "must be finite"):
            decoder.step(
                np.asarray([np.nan], np.float32),
                np.asarray([0.0], np.float32),
            )
        self.assertEqual(resolver.observations, [])
        self.assertTrue(bool(decoder.active[0]))
        self.assertTrue(bool(decoder.provisional_active[0]))

    def test_same_frame_harmonic_and_polyphony_use_pre_resolution_snapshot(self) -> None:
        resolver = _RecordingResolver()
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            release_frames=3,
            maximum_polyphony=2,
        )
        decoder = PolyphonicDecoder(config, provisional_state_resolver=resolver)
        emitted = np.zeros(13, np.float32)
        emitted[0] = 0.95
        emitted[12] = 0.95
        decoder.step(emitted, emitted)
        resolver.decisions = {60: PROVISIONAL_CONFIRM, 72: PROVISIONAL_HOLD}
        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0
        hold = np.zeros(13, np.float32)
        hold[[0, 12]] = 0.40
        decoder.step(hold, np.zeros(13, np.float32), harmonic)

        observations = {item.pitch: item for item in resolver.observations[-2:]}
        self.assertEqual(observations[72].harmonic_support, 0.0)
        self.assertEqual(
            (observations[60].emitted_polyphony, observations[60].contextual_polyphony),
            (2, 0),
        )
        self.assertEqual(
            (observations[72].emitted_polyphony, observations[72].contextual_polyphony),
            (2, 0),
        )
        self.assertFalse(bool(decoder.provisional_active[0]))
        self.assertTrue(bool(decoder.provisional_active[12]))
        self.assertEqual(
            decoder._harmonic_support(12, harmonic, decoder.contextual_active),
            1.0,
        )

    def test_unsupported_existing_gate_compositions_fail_closed(self) -> None:
        config = PolyphonicDecoderConfig(midi_min=60, midi_max=60)
        resolver = _RecordingResolver()
        for placement in (
            CAUSAL_CANDIDATE_GATE_PRE_RANKING,
            CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON,
        ):
            with self.subTest(placement=placement), self.assertRaisesRegex(
                ValueError, "unsupported_pending_separate_contract"
            ):
                PolyphonicDecoder(
                    config,
                    causal_candidate_gate=lambda _observation: False,
                    causal_candidate_gate_placement=placement,
                    provisional_state_resolver=resolver,
                )
        independent_config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            independent_note_threshold=0.5,
        )
        with self.assertRaisesRegex(
            ValueError, "unsupported_pending_separate_contract"
        ):
            PolyphonicDecoder(
                independent_config,
                provisional_state_resolver=resolver,
            )
        with self.assertRaisesRegex(
            ValueError, "unsupported_pending_separate_contract"
        ):
            PolyphonicDecoder(
                independent_config,
                causal_candidate_gate=lambda _observation: False,
                provisional_state_resolver=resolver,
            )


if __name__ == "__main__":
    unittest.main()
