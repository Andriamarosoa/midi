from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.evaluate_events import NoteInterval
from src.polyphonic.validate_live_input_level import (
    _capture_scaled_waveform,
    _valid_note_views,
)


class ValidateLiveInputLevelTests(unittest.TestCase):
    def test_capture_attenuation_normalizes_integer_audio(self) -> None:
        waveform = np.asarray([-32768, 0, 16384], np.int16)

        scaled, linear = _capture_scaled_waveform(waveform, -12.0)

        self.assertAlmostEqual(linear, 10.0 ** (-12.0 / 20.0))
        np.testing.assert_allclose(
            scaled,
            np.asarray([-1.0, 0.0, 0.5], np.float32) * linear,
            rtol=0.0,
            atol=1e-7,
        )

    def test_capture_experiment_rejects_positive_gain(self) -> None:
        with self.assertRaisesRegex(ValueError, "zero or negative"):
            _capture_scaled_waveform(
                np.zeros(4, np.float32),
                1.0,
            )

    def test_invalid_annotation_frames_are_not_counted_as_false_notes(self) -> None:
        reference = [
            NoteInterval(60, 0.10, 0.20),
            NoteInterval(62, 0.30, 0.40),
        ]
        estimated = [
            NoteInterval(60, 0.10, 0.20),
            NoteInterval(61, 0.20, 0.30),
        ]
        valid = np.asarray([True, False, True, True], np.bool_)

        (
            onset_reference,
            onset_estimated,
            offset_reference,
            offset_estimated,
            report,
        ) = _valid_note_views(
            reference,
            estimated,
            valid,
            sample_rate=100,
            hop_size=10,
        )

        self.assertEqual(
            [note.pitch for note in onset_reference],
            [60, 62],
        )
        self.assertEqual(
            [note.pitch for note in onset_estimated],
            [60],
        )
        self.assertEqual(offset_reference, [reference[1]])
        self.assertEqual(offset_estimated, [])
        self.assertEqual(report["invalid_estimated_onsets"], 1)
        self.assertEqual(report["invalid_reference_offsets"], 1)


if __name__ == "__main__":
    unittest.main()
