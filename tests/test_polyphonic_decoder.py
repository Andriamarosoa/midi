from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.decoder import PolyphonicDecoder, PolyphonicDecoderConfig


class PolyphonicDecoderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=72, activation_frames=2,
            release_frames=2, minimum_retrigger_frames=2,
            silence_release_frames=2,
            maximum_polyphony=6,
        )

    def test_simultaneous_onsets_emit_a_chord(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[[0, 4, 7]] = 0.9
        onset[[0, 4, 7]] = 0.9

        events = decoder.step(frame, onset)

        self.assertEqual(
            {event.pitch for event in events if event.kind == "note_on"},
            {60, 64, 67},
        )

    def test_harmonic_tail_is_suppressed_but_real_onset_is_not(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        base = np.zeros(13, np.float32)
        base[0] = 0.9
        onset = base.copy()
        decoder.step(base, onset)
        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0  # Octave partial of MIDI 60.
        candidate = base.copy()
        candidate[12] = 0.6
        no_onset = np.zeros(13, np.float32)

        first = decoder.step(candidate, no_onset, harmonic)
        second = decoder.step(candidate, no_onset, harmonic)
        self.assertFalse(any(event.pitch == 72 for event in first + second))

        real_onset = no_onset.copy()
        real_onset[12] = 0.9
        events = decoder.step(candidate, real_onset, harmonic)
        self.assertTrue(any(
            event.kind == "note_on" and event.pitch == 72 for event in events
        ))

    def test_recoverable_gap_preserves_notes_and_clears_weak_votes(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=61,
            release_frames=2,
            recovery_release_grace_frames=2,
            maximum_polyphony=2,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.9, 0.0], np.float32)
        onset = frame.copy()
        decoder.step(
            frame, onset, audio_hop_index=0, audio_onset=True
        )
        low = np.zeros(2, np.float32)
        decoder.step(low, low, audio_hop_index=1, audio_onset=False)
        self.assertEqual(int(decoder.release_count[0]), 1)

        preserved = decoder.reset_observation_continuity()

        self.assertEqual(preserved, (60,))
        self.assertTrue(bool(decoder.active[0]))
        self.assertEqual(int(decoder.release_count[0]), 0)
        self.assertFalse(decoder.recent_audio_onset)
        self.assertEqual(
            decoder.step(low, low, audio_hop_index=5, audio_onset=False),
            [],
        )
        self.assertEqual(
            decoder.step(low, low, audio_hop_index=6, audio_onset=False),
            [],
        )
        self.assertEqual(
            decoder.step(low, low, audio_hop_index=7, audio_onset=False),
            [],
        )
        released = decoder.step(
            low, low, audio_hop_index=8, audio_onset=False
        )
        self.assertEqual(
            [(event.kind, event.pitch) for event in released],
            [("note_off", 60)],
        )

    def test_simultaneous_independent_onsets_receive_short_release_grace(
        self,
    ) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=64,
            release_frames=1,
            chord_release_grace_frames=2,
            maximum_polyphony=5,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.zeros(5, np.float32)
        onset = np.zeros(5, np.float32)
        frame[[0, 4]] = 0.9
        onset[[0, 4]] = 0.9
        decoder.step(
            frame, onset, audio_hop_index=0, audio_onset=True
        )
        low = np.zeros(5, np.float32)

        self.assertEqual(
            decoder.step(
                low, low, audio_hop_index=1, audio_onset=False
            ),
            [],
        )
        self.assertEqual(
            decoder.step(
                low, low, audio_hop_index=2, audio_onset=False
            ),
            [],
        )
        released = decoder.step(
            low, low, audio_hop_index=3, audio_onset=False
        )
        self.assertEqual(
            {(event.kind, event.pitch) for event in released},
            {("note_off", 60), ("note_off", 64)},
        )

    def test_single_onset_does_not_receive_chord_release_grace(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            release_frames=1,
            chord_release_grace_frames=6,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.9], np.float32)
        decoder.step(
            frame, frame, audio_hop_index=0, audio_onset=True
        )
        low = np.zeros(1, np.float32)

        released = decoder.step(
            low, low, audio_hop_index=1, audio_onset=False
        )

        self.assertEqual(
            [(event.kind, event.pitch) for event in released],
            [("note_off", 60)],
        )

    def test_release_and_retrigger_are_global_per_pitch(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[0] = onset[0] = 0.9
        decoder.step(frame, onset)
        decoder.step(frame, np.zeros_like(onset))
        retrigger = decoder.step(frame, onset)
        self.assertEqual([event.kind for event in retrigger], ["note_off", "note_on"])

        silence = np.zeros(13, np.float32)
        self.assertEqual(decoder.step(silence, silence), [])
        released = decoder.step(silence, silence)
        self.assertTrue(any(event.kind == "note_off" for event in released))

    def test_inactive_audio_cannot_activate_a_new_note(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[9] = onset[9] = 0.99

        first = decoder.step(frame, onset, audio_active=False)
        second = decoder.step(frame, onset, audio_active=False)

        self.assertEqual(first, [])
        self.assertEqual(second, [])
        self.assertFalse(np.any(decoder.active))

    def test_silence_grace_holds_then_releases_an_active_note(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[0] = onset[0] = 0.9
        decoder.step(frame, onset)

        first = decoder.step(frame, onset, audio_active=False)
        second = decoder.step(frame, onset, audio_active=False)

        self.assertEqual(first, [])
        self.assertEqual(
            [(event.kind, event.pitch) for event in second],
            [("note_off", 60)],
        )
        self.assertFalse(np.any(decoder.active))

    def test_inactive_hop_breaks_pending_activation_votes(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[5] = 0.9

        self.assertEqual(decoder.step(frame, onset), [])
        self.assertEqual(int(decoder.activation_count[5]), 1)

        self.assertEqual(
            decoder.step(frame, onset, audio_active=False),
            [],
        )
        self.assertEqual(int(decoder.activation_count[5]), 0)

        # One audible hop after the gap is not consecutive with the vote that
        # preceded silence.  A second audible hop is still required.
        self.assertEqual(decoder.step(frame, onset), [])
        events = decoder.step(frame, onset)
        self.assertEqual(
            [(event.kind, event.pitch) for event in events],
            [("note_on", 65)],
        )

    def test_absolute_audio_hop_clock_counts_skipped_inferences(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60, midi_max=60, activation_frames=2,
            release_frames=2, minimum_retrigger_frames=4,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.9], np.float32)
        onset = np.asarray([0.9], np.float32)
        no_onset = np.zeros(1, np.float32)

        decoder.step(frame, onset, audio_hop_index=10)
        decoder.step(frame, no_onset, audio_hop_index=11)
        retrigger = decoder.step(frame, onset, audio_hop_index=14)

        self.assertEqual(
            [(event.kind, event.frame_index) for event in retrigger],
            [("note_off", 14), ("note_on", 14)],
        )

        # Backward-compatible offline calls still advance once per inference.
        offline = PolyphonicDecoder(config)
        offline.step(frame, onset)
        offline.step(frame, no_onset)
        self.assertEqual(offline.step(frame, onset), [])

    def test_skipped_audio_hop_breaks_activation_and_release_votes(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[5] = 0.9

        self.assertEqual(
            decoder.step(frame, onset, audio_hop_index=0),
            [],
        )
        self.assertEqual(int(decoder.activation_count[5]), 1)
        self.assertEqual(
            decoder.step(frame, onset, audio_hop_index=2),
            [],
        )
        self.assertEqual(int(decoder.activation_count[5]), 1)
        activated = decoder.step(frame, onset, audio_hop_index=3)
        self.assertEqual(
            [(event.kind, event.pitch) for event in activated],
            [("note_on", 65)],
        )

        low_frame = np.zeros(13, np.float32)
        self.assertEqual(
            decoder.step(low_frame, onset, audio_hop_index=4),
            [],
        )
        self.assertEqual(int(decoder.release_count[5]), 1)
        self.assertEqual(
            decoder.step(low_frame, onset, audio_hop_index=6),
            [],
        )
        self.assertEqual(int(decoder.release_count[5]), 1)
        released = decoder.step(low_frame, onset, audio_hop_index=7)
        self.assertEqual(
            [(event.kind, event.pitch) for event in released],
            [("note_off", 65)],
        )

    def test_physical_attack_is_required_for_retrigger_when_available(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            activation_frames=2,
            release_frames=2,
            minimum_retrigger_frames=2,
            audio_onset_lookback_frames=1,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.9], np.float32)
        onset = np.asarray([0.9], np.float32)
        no_onset = np.zeros(1, np.float32)

        decoder.step(frame, onset, audio_hop_index=0, audio_onset=True)
        decoder.step(frame, no_onset, audio_hop_index=1, audio_onset=False)
        without_attack = decoder.step(
            frame, onset, audio_hop_index=2, audio_onset=False
        )
        with_attack = decoder.step(
            frame,
            onset,
            audio_hop_index=3,
            audio_onset=True,
            audio_onset_hop_index=3,
        )

        self.assertEqual(without_attack, [])
        self.assertEqual(
            [(event.kind, event.reason) for event in with_attack],
            [("note_off", "retrigger"), ("note_on", "retrigger")],
        )

    def test_unattacked_frame_fallback_requires_its_strong_threshold(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            activation_frames=2,
            unattacked_frame_threshold=0.9,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.7], np.float32)
        no_onset = np.zeros(1, np.float32)

        self.assertEqual(decoder.step(frame, no_onset, audio_onset=False), [])
        self.assertEqual(
            decoder.step(frame, no_onset, audio_onset=False),
            [],
        )
        strong = np.asarray([0.92], np.float32)
        self.assertEqual(
            decoder.step(strong, no_onset, audio_onset=False),
            [],
        )
        activated = decoder.step(
            strong,
            no_onset,
            audio_onset=False,
        )

        self.assertEqual(
            [(event.kind, event.pitch, event.reason) for event in activated],
            [("note_on", 60, "frame_fallback")],
        )

    def test_physical_attack_is_recorded_as_frame_activation_reason(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            activation_frames=2,
            unattacked_frame_threshold=0.9,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.7], np.float32)
        no_onset = np.zeros(1, np.float32)

        decoder.step(frame, no_onset, audio_onset=True)
        events = decoder.step(frame, no_onset, audio_onset=False)

        self.assertEqual(
            [(event.pitch, event.reason) for event in events],
            [(60, "frame_attack")],
        )

    def test_chord_formation_finishes_a_vote_started_during_attack(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=64,
            frame_on_threshold=0.5,
            strong_frame_threshold=0.8,
            onset_threshold=0.5,
            activation_frames=2,
            audio_onset_lookback_frames=1,
            chord_formation_frames=4,
            unattacked_frame_threshold=0.9,
            maximum_polyphony=5,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.zeros(5, np.float32)
        onset = np.zeros(5, np.float32)
        frame[0] = onset[0] = 0.9
        decoder.step(
            frame, onset, audio_hop_index=0, audio_onset=True
        )

        chord_tone = np.zeros(5, np.float32)
        chord_tone[4] = 0.65
        self.assertEqual(
            decoder.step(
                chord_tone,
                np.zeros(5, np.float32),
                audio_hop_index=1,
                audio_onset=False,
            ),
            [],
        )
        completed = decoder.step(
            chord_tone,
            np.zeros(5, np.float32),
            audio_hop_index=2,
            audio_onset=False,
        )

        self.assertEqual(
            [(event.kind, event.pitch, event.reason) for event in completed],
            [("note_on", 64, "chord_completion")],
        )

    def test_new_late_chord_tone_requires_strong_frame_evidence(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=64,
            frame_on_threshold=0.5,
            strong_frame_threshold=0.8,
            onset_threshold=0.5,
            activation_frames=2,
            audio_onset_lookback_frames=1,
            chord_formation_frames=6,
            unattacked_frame_threshold=0.9,
            maximum_polyphony=5,
        )
        decoder = PolyphonicDecoder(config)
        root = np.zeros(5, np.float32)
        root[0] = 0.9
        decoder.step(
            root, root, audio_hop_index=0, audio_onset=True
        )
        weak = np.zeros(5, np.float32)
        weak[0] = 0.9
        weak[4] = 0.7
        self.assertEqual(
            decoder.step(
                weak, np.zeros(5, np.float32),
                audio_hop_index=2, audio_onset=False,
            ),
            [],
        )
        self.assertEqual(
            decoder.step(
                weak, np.zeros(5, np.float32),
                audio_hop_index=3, audio_onset=False,
            ),
            [],
        )

        strong = np.zeros(5, np.float32)
        strong[0] = 0.9
        strong[4] = 0.82
        self.assertEqual(
            decoder.step(
                strong, np.zeros(5, np.float32),
                audio_hop_index=4, audio_onset=False,
            ),
            [],
        )
        completed = decoder.step(
            strong,
            np.zeros(5, np.float32),
            audio_hop_index=5,
            audio_onset=False,
        )
        self.assertEqual(
            [(event.kind, event.pitch, event.reason) for event in completed],
            [("note_on", 64, "chord_completion")],
        )

    def test_chord_formation_memory_expires_before_resonance_tail(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=64,
            frame_on_threshold=0.5,
            strong_frame_threshold=0.8,
            onset_threshold=0.5,
            activation_frames=2,
            audio_onset_lookback_frames=1,
            chord_formation_frames=2,
            unattacked_frame_threshold=0.9,
            maximum_polyphony=5,
        )
        decoder = PolyphonicDecoder(config)
        root = np.zeros(5, np.float32)
        root[0] = 0.9
        decoder.step(
            root, root, audio_hop_index=0, audio_onset=True
        )
        tail = np.zeros(5, np.float32)
        tail[4] = 0.85

        self.assertEqual(
            decoder.step(
                tail, np.zeros(5, np.float32),
                audio_hop_index=3, audio_onset=False,
            ),
            [],
        )
        self.assertEqual(
            decoder.step(
                tail, np.zeros(5, np.float32),
                audio_hop_index=4, audio_onset=False,
            ),
            [],
        )
        self.assertFalse(bool(decoder.active[4]))

    def test_simultaneous_frame_only_octave_partial_is_suppressed(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=72,
            activation_frames=2,
            maximum_polyphony=2,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.zeros(13, np.float32)
        frame[[0, 12]] = 0.85
        no_onset = np.zeros(13, np.float32)
        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0

        decoder.step(frame, no_onset, harmonic, audio_onset=True)
        events = decoder.step(frame, no_onset, harmonic, audio_onset=False)

        self.assertEqual(
            [event.pitch for event in events if event.kind == "note_on"],
            [60],
        )

    def test_pitch_specific_onset_preserves_intentional_octave(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        frame = np.zeros(13, np.float32)
        onset = np.zeros(13, np.float32)
        frame[[0, 12]] = 0.85
        onset[12] = 0.9
        harmonic = np.zeros((13, 4), np.float32)
        harmonic[0, 1] = 1.0

        events = decoder.step(
            frame, onset, harmonic, audio_onset=True
        )

        self.assertTrue(any(
            event.kind == "note_on"
            and event.pitch == 72
            and event.reason == "model_onset"
            for event in events
        ))

    def test_silence_release_grace_is_fourteen_hops(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            silence_release_frames=14,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.9], np.float32)
        onset = np.asarray([0.9], np.float32)
        decoder.step(frame, onset)

        for _ in range(13):
            self.assertEqual(
                decoder.step(frame, onset, audio_active=False), []
            )
        released = decoder.step(frame, onset, audio_active=False)

        self.assertEqual(
            [(event.kind, event.reason) for event in released],
            [("note_off", "silence")],
        )

    def test_skipped_inference_does_not_restart_silence_grace(self) -> None:
        config = PolyphonicDecoderConfig(
            midi_min=60,
            midi_max=60,
            silence_release_frames=14,
            maximum_polyphony=1,
        )
        decoder = PolyphonicDecoder(config)
        frame = np.asarray([0.9], np.float32)
        onset = np.asarray([0.9], np.float32)
        decoder.step(frame, onset, audio_hop_index=0)

        for hop_index in range(1, 14):
            self.assertEqual(
                decoder.step(
                    frame,
                    onset,
                    audio_active=False,
                    audio_hop_index=hop_index,
                ),
                [],
            )
        released = decoder.step(
            frame,
            onset,
            audio_active=False,
            audio_hop_index=15,
        )

        self.assertEqual(
            [(event.kind, event.reason) for event in released],
            [("note_off", "silence")],
        )

    def test_panic_clears_old_physical_attack(self) -> None:
        decoder = PolyphonicDecoder(self.config)
        silence = np.zeros(13, np.float32)
        decoder.step(silence, silence, audio_onset=True)
        self.assertTrue(decoder.recent_audio_onset)

        decoder.panic()

        self.assertFalse(decoder.recent_audio_onset)


if __name__ == "__main__":
    unittest.main()
