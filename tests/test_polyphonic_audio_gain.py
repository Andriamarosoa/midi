from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.audio_gain import (
    apply_manual_audio_gain,
    validate_manual_audio_gain,
)


class PolyphonicAudioGainTests(unittest.TestCase):
    def test_applies_gain_once_without_modifying_source(self) -> None:
        source = np.asarray([0.25, -0.6], dtype=np.float32)
        original = source.copy()

        captured, clipped = apply_manual_audio_gain(source, 2.0)

        np.testing.assert_array_equal(source, original)
        np.testing.assert_allclose(captured, [0.5, -1.0])
        self.assertEqual(clipped, 1)

    def test_rejects_nonfinite_or_nonpositive_gain(self) -> None:
        for gain in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(gain=gain):
                with self.assertRaisesRegex(ValueError, "finite and positive"):
                    validate_manual_audio_gain(gain)


if __name__ == "__main__":
    unittest.main()
