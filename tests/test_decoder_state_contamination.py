from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.decoder import PolyphonicDecoder, PolyphonicDecoderConfig


def _state(decoder: PolyphonicDecoder) -> dict[str, object]:
    return {
        "active": tuple(bool(value) for value in decoder.active),
        "activation_count": tuple(int(value) for value in decoder.activation_count),
        "release_count": tuple(int(value) for value in decoder.release_count),
        "last_note_on": tuple(int(value) for value in decoder.last_note_on),
        "chord_release_grace": tuple(
            int(value) for value in decoder.chord_release_grace
        ),
        "attack_activation_pending": tuple(
            bool(value) for value in decoder.attack_activation_pending
        ),
        "recovery_release_grace": int(decoder.recovery_release_grace),
    }


def _events(events) -> tuple[tuple[str, int, int, str], ...]:
    return tuple(
        (event.kind, event.pitch, event.frame_index, event.reason)
        for event in events
    )


class DecoderStateContaminationDiagnosticTests(unittest.TestCase):
    def test_false_noteon_contaminates_future_polyphony_budget(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=61,
            activation_frames=2,
            release_frames=3,
            maximum_polyphony=1,
        )
        control = PolyphonicDecoder(config)
        perturbed = PolyphonicDecoder(config)

        quiet = np.zeros(2, np.float32)
        false_note = quiet.copy()
        false_note[0] = 0.95

        self.assertEqual(control.step(quiet, quiet), [])
        t0_perturbed = perturbed.step(false_note, false_note)
        self.assertEqual(_events(t0_perturbed), (("note_on", 60, 0, "legacy"),))

        # From t1 onward both decoders receive byte-identical inputs.  Keeping
        # pitch 60 above its off threshold preserves only B's false active slot.
        frame_t1 = np.asarray([0.90, 0.95], np.float32)
        onset_t1 = np.asarray([0.00, 0.95], np.float32)
        self.assertEqual(frame_t1.tobytes(), frame_t1.copy().tobytes())
        control_events = control.step(frame_t1, onset_t1)
        perturbed_events = perturbed.step(frame_t1.copy(), onset_t1.copy())

        self.assertEqual(
            _events(control_events), (("note_on", 61, 1, "legacy"),)
        )
        self.assertEqual(perturbed_events, [])
        self.assertEqual(_state(control)["active"], (False, True))
        self.assertEqual(_state(perturbed)["active"], (True, False))
        self.assertEqual(int(control.last_note_on[1]), 1)
        self.assertLess(int(perturbed.last_note_on[1]), 0)

    def test_false_noteon_contaminates_future_harmonic_support(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=1,
            release_frames=3,
            maximum_polyphony=2,
        )
        control = PolyphonicDecoder(config)
        perturbed = PolyphonicDecoder(config)
        quiet = np.zeros(13, np.float32)
        false_base = quiet.copy()
        false_base[0] = 0.95

        self.assertEqual(
            control.step(
                quiet, quiet, audio_hop_index=0, audio_onset=True
            ),
            [],
        )
        t0_perturbed = perturbed.step(
            false_base,
            false_base,
            audio_hop_index=0,
            audio_onset=True,
        )
        self.assertEqual(
            _events(t0_perturbed), (("note_on", 60, 0, "model_onset"),)
        )

        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0  # MIDI 72 is H2 of the false MIDI 60 base.
        frame_t1 = quiet.copy()
        frame_t1[0] = 0.30  # Holds B's base; cannot propose a base in A.
        frame_t1[12] = 0.85
        onset_t1 = quiet.copy()

        control_support = control._harmonic_support(12, harmonic, control.active)
        perturbed_support = perturbed._harmonic_support(
            12, harmonic, perturbed.active
        )
        self.assertEqual(control_support, 0.0)
        self.assertEqual(perturbed_support, 1.0)

        control_events = control.step(
            frame_t1,
            onset_t1,
            harmonic,
            audio_hop_index=1,
            audio_onset=False,
        )
        perturbed_events = perturbed.step(
            frame_t1.copy(),
            onset_t1.copy(),
            harmonic.copy(),
            audio_hop_index=1,
            audio_onset=False,
        )

        self.assertEqual(
            _events(control_events), (("note_on", 72, 1, "frame_attack"),)
        )
        self.assertEqual(perturbed_events, [])
        self.assertTrue(bool(control.active[12]))
        self.assertFalse(bool(perturbed.active[12]))
        self.assertEqual(int(perturbed.release_count[0]), 0)


if __name__ == "__main__":
    unittest.main()
