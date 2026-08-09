from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.decoder import (
    PROVISIONAL_CONFIRM,
    PROVISIONAL_HOLD,
    PROVISIONAL_REJECT,
    PolyphonicDecoder,
    PolyphonicDecoderConfig,
    ProvisionalObservation,
)


def _events(events) -> tuple[tuple[str, int, int, str], ...]:
    return tuple(
        (event.kind, event.pitch, event.frame_index, event.reason)
        for event in events
    )


class _Resolver:
    def __init__(self) -> None:
        self.decisions: dict[int, str] = {}
        self.calls: list[ProvisionalObservation] = []

    def __call__(self, state: ProvisionalObservation) -> str:
        self.calls.append(state)
        return self.decisions.get(state.pitch, PROVISIONAL_HOLD)


class DecoderProvisionalStateIsolationTests(unittest.TestCase):
    def test_provisional_slot_is_preempted_without_backfill_delay(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=61,
            activation_frames=2,
            release_frames=3,
            maximum_polyphony=1,
        )
        control_resolver = _Resolver()
        intervention_resolver = _Resolver()
        control = PolyphonicDecoder(
            config, provisional_state_resolver=control_resolver
        )
        intervention = PolyphonicDecoder(
            config, provisional_state_resolver=intervention_resolver
        )

        quiet = np.zeros(2, np.float32)
        false_note = quiet.copy()
        false_note[0] = 0.95
        self.assertEqual(control.step(quiet, quiet), [])
        self.assertEqual(
            _events(intervention.step(false_note, false_note)),
            (("note_on", 60, 0, "legacy"),),
        )
        self.assertEqual(tuple(intervention.active), (True, False))
        self.assertEqual(tuple(intervention.provisional_active), (True, False))
        self.assertEqual(tuple(intervention.contextual_active), (False, False))

        frame_t1 = np.asarray([0.90, 0.95], np.float32)
        onset_t1 = np.asarray([0.00, 0.95], np.float32)
        control_events = control.step(frame_t1, onset_t1)
        intervention_events = intervention.step(
            frame_t1.copy(), onset_t1.copy()
        )

        self.assertEqual(
            _events(control_events), (("note_on", 61, 1, "legacy"),)
        )
        self.assertEqual(
            _events(intervention_events),
            (
                ("note_off", 60, 1, "provisional_preempt"),
                ("note_on", 61, 1, "legacy"),
            ),
        )
        self.assertEqual(tuple(intervention.active), (False, True))
        self.assertEqual(tuple(intervention.provisional_active), (False, True))
        self.assertLessEqual(int(np.sum(intervention.active)), 1)

    def test_provisional_note_is_excluded_from_harmonic_context(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            release_frames=3,
            maximum_polyphony=2,
        )
        control = PolyphonicDecoder(
            config, provisional_state_resolver=_Resolver()
        )
        intervention_resolver = _Resolver()
        intervention = PolyphonicDecoder(
            config, provisional_state_resolver=intervention_resolver
        )
        quiet = np.zeros(13, np.float32)
        false_base = quiet.copy()
        false_base[0] = 0.95

        self.assertEqual(
            control.step(quiet, quiet, audio_hop_index=0, audio_onset=True),
            [],
        )
        self.assertEqual(
            _events(intervention.step(
                false_base,
                false_base,
                audio_hop_index=0,
                audio_onset=True,
            )),
            (("note_on", 60, 0, "model_onset"),),
        )

        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0
        self.assertEqual(
            control._harmonic_support(12, harmonic, control.contextual_active),
            0.0,
        )
        self.assertEqual(
            intervention._harmonic_support(
                12, harmonic, intervention.contextual_active
            ),
            0.0,
        )

        frame_t1 = quiet.copy()
        frame_t1[0] = 0.30
        frame_t1[12] = 0.85
        control_events = control.step(
            frame_t1,
            quiet,
            harmonic,
            audio_hop_index=1,
            audio_onset=False,
        )
        intervention_events = intervention.step(
            frame_t1.copy(),
            quiet.copy(),
            harmonic.copy(),
            audio_hop_index=1,
            audio_onset=False,
        )
        self.assertEqual(
            _events(control_events), (("note_on", 72, 1, "frame_attack"),)
        )
        self.assertEqual(
            _events(intervention_events),
            (("note_on", 72, 1, "frame_attack"),),
        )

        intervention_resolver.decisions[60] = PROVISIONAL_REJECT
        reject_events = intervention.step(
            frame_t1.copy(),
            quiet.copy(),
            harmonic.copy(),
            audio_hop_index=2,
            audio_onset=False,
        )
        self.assertEqual(
            _events(reject_events),
            (("note_off", 60, 2, "provisional_reject"),),
        )
        self.assertFalse(bool(intervention.active[0]))
        self.assertFalse(bool(intervention.provisional_active[0]))
        self.assertEqual(int(intervention.activation_count[0]), 0)
        self.assertEqual(int(intervention.release_count[0]), 0)
        self.assertFalse(bool(intervention.attack_activation_pending[0]))
        self.assertEqual(int(intervention.chord_release_grace[0]), 0)
        self.assertTrue(bool(intervention.active[12]))

    def test_confirm_preserves_note_without_second_noteon(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            release_frames=3,
            maximum_polyphony=2,
        )
        resolver = _Resolver()
        decoder = PolyphonicDecoder(
            config, provisional_state_resolver=resolver
        )
        quiet = np.zeros(13, np.float32)
        note = quiet.copy()
        note[0] = 0.95
        self.assertEqual(
            _events(decoder.step(note, note)),
            (("note_on", 60, 0, "legacy"),),
        )
        resolver.decisions[60] = PROVISIONAL_CONFIRM
        hold = quiet.copy()
        hold[0] = 0.30
        self.assertEqual(decoder.step(hold, quiet), [])
        self.assertTrue(bool(decoder.active[0]))
        self.assertFalse(bool(decoder.provisional_active[0]))
        self.assertTrue(bool(decoder.contextual_active[0]))
        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0
        self.assertEqual(
            decoder._harmonic_support(12, harmonic, decoder.contextual_active),
            1.0,
        )

    def test_invalid_resolution_fails_closed(self) -> None:
        config = PolyphonicDecoderConfig(midi_min=60, midi_max=60)

        def invalid(_state: ProvisionalObservation) -> str:
            return "MAYBE"

        decoder = PolyphonicDecoder(
            config, provisional_state_resolver=invalid
        )
        note = np.asarray([0.95], np.float32)
        decoder.step(note, note)
        with self.assertRaisesRegex(ValueError, "HOLD, CONFIRM, or REJECT"):
            decoder.step(note, note)


if __name__ == "__main__":
    unittest.main()
