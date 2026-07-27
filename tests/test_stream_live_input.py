from __future__ import annotations

import unittest

import numpy as np

from src.stream.live_input import ProgressiveWindowStream, StreamConfig


class ProgressiveWindowStreamTests(unittest.TestCase):
    def test_gain_is_applied_before_causal_windows_are_copied(self) -> None:
        stream = ProgressiveWindowStream(StreamConfig(
            sample_rate=8_000,
            hop_samples=4,
            max_window_samples=8,
            windows=(4, 8),
        ))
        samples = np.asarray([[0.2], [-0.3], [0.6], [-0.8]], np.float32)
        stream.audio_callback(samples, 4, None, False)

        hop, windows = stream.process_next_hop(gain=2.0)

        expected = np.asarray([0.4, -0.6, 1.0, -1.0], np.float32)
        np.testing.assert_allclose(hop, expected)
        np.testing.assert_allclose(windows[4], expected)
        np.testing.assert_allclose(windows[8][-4:], expected)


if __name__ == "__main__":
    unittest.main()
