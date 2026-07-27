from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.evaluate_frames import binary_metrics, select_threshold


class PolyphonicEvaluateTests(unittest.TestCase):
    def test_binary_metrics_flatten_notes_and_frames(self) -> None:
        truth = np.asarray([[1, 0], [0, 1]], np.float32)
        probability = np.asarray([[0.9, 0.6], [0.1, 0.8]], np.float32)
        metrics = binary_metrics(truth, probability, 0.5)
        self.assertEqual(metrics["true_positive"], 2)
        self.assertEqual(metrics["false_positive"], 1)
        self.assertAlmostEqual(metrics["f1"], 0.8)

    def test_threshold_is_selected_only_from_given_data(self) -> None:
        truth = np.asarray([1, 0, 1, 0], np.float32)
        probability = np.asarray([0.8, 0.4, 0.7, 0.1], np.float32)
        threshold, metrics = select_threshold(
            truth, probability, np.asarray([0.3, 0.5, 0.9])
        )
        self.assertEqual(threshold, 0.5)
        self.assertEqual(metrics["f1"], 1.0)


if __name__ == "__main__":
    unittest.main()
