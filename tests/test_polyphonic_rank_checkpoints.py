from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.rank_checkpoints import harmonic_metrics, pareto_candidates


class RankCheckpointsTests(unittest.TestCase):
    def test_pareto_keeps_tradeoffs_and_rejects_dominated_epochs(self) -> None:
        rows = [
            {"checkpoint": "frame", "frame_f1": 0.70, "onset_f1": 0.30,
             "harmonic_amplitude_mae": 0.10, "harmonic_offset_normalized_mae": 0.10},
            {"checkpoint": "onset", "frame_f1": 0.60, "onset_f1": 0.40,
             "harmonic_amplitude_mae": 0.10, "harmonic_offset_normalized_mae": 0.10},
            {"checkpoint": "dominated", "frame_f1": 0.59, "onset_f1": 0.29,
             "harmonic_amplitude_mae": 0.11, "harmonic_offset_normalized_mae": 0.11},
            {"checkpoint": "balanced", "frame_f1": 0.68, "onset_f1": 0.38,
             "harmonic_amplitude_mae": 0.10, "harmonic_offset_normalized_mae": 0.10},
        ]
        self.assertEqual(
            set(pareto_candidates(rows)), {"frame", "onset", "balanced"}
        )

    def test_harmonic_metrics_ignore_unlabelled_partials(self) -> None:
        targets = {
            "harmonic_amplitude": np.asarray([[[0.5, 0.0, 1.0, 0.0]]], np.float32),
            "harmonic_offset_cents": np.asarray(
                [[[7.0, 20.0, 1.0, 0.0, 0.5, 0.0]]], np.float32
            ),
        }
        prediction = {
            "harmonic_amplitude": np.asarray([[[0.7, 1.0]]], np.float32),
            "harmonic_offset_cents": np.asarray([[[14.0, -35.0]]], np.float32),
        }
        metrics = harmonic_metrics(
            targets, prediction, harmonic_count=2, offset_scale_cents=35.0
        )
        self.assertEqual(metrics["valid_partials"], 1)
        self.assertAlmostEqual(metrics["harmonic_amplitude_mae"], 0.2, places=6)
        self.assertAlmostEqual(
            metrics["harmonic_offset_normalized_mae"], 0.2, places=6
        )


if __name__ == "__main__":
    unittest.main()
