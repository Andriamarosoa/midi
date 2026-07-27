from __future__ import annotations

import unittest

import numpy as np

from src.polyphonic.validate_tflite_validation import (
    _empty_scope,
    _finish_scope,
    _scope_passes,
    _update_scope,
)


class TFLiteValidationAccumulatorTests(unittest.TestCase):
    def test_identical_runtime_passes_and_preserves_metrics(self) -> None:
        scope = _empty_scope()
        frame = np.asarray([[1.0, 0.0]], np.float32)
        onset = np.asarray([[1.0, 0.0]], np.float32)
        amplitude = np.asarray([[[0.5], [0.0]]], np.float32)
        offset = np.asarray([[[5.0], [0.0]]], np.float32)
        targets = {
            "frame": frame,
            "onset": onset,
            "harmonic_amplitude": np.concatenate(
                [amplitude, np.ones_like(amplitude)], axis=-1
            ),
            "harmonic_offset_cents": np.concatenate(
                [offset, np.ones_like(offset), amplitude], axis=-1
            ),
        }
        prediction = {
            "frame": np.asarray([[0.8, 0.1]], np.float32),
            "onset": np.asarray([[0.9, 0.1]], np.float32),
            "harmonic_amplitude": amplitude.copy(),
            "harmonic_offset_cents": offset.copy(),
        }
        _update_scope(
            scope, targets, prediction, prediction,
            0.5, 0.5, harmonic_count=1, offset_scale_cents=35.0,
        )
        report = _finish_scope(scope)
        self.assertEqual(report["frame"]["decision_mismatches"], 0)
        self.assertAlmostEqual(report["frame"]["keras"]["f1"], 1.0)
        self.assertTrue(_scope_passes(report))

    def test_f1_regression_fails_policy(self) -> None:
        scope = _empty_scope()
        target = np.asarray([[1.0]], np.float32)
        harmonic_target = np.zeros((1, 1, 3), np.float32)
        targets = {
            "frame": target,
            "onset": target,
            "harmonic_amplitude": np.zeros((1, 1, 2), np.float32),
            "harmonic_offset_cents": harmonic_target,
        }
        keras = {
            "frame": np.asarray([[0.9]], np.float32),
            "onset": np.asarray([[0.9]], np.float32),
            "harmonic_amplitude": np.zeros((1, 1, 1), np.float32),
            "harmonic_offset_cents": np.zeros((1, 1, 1), np.float32),
        }
        tflite = {**keras, "frame": np.asarray([[0.1]], np.float32)}
        _update_scope(scope, targets, keras, tflite, 0.5, 0.5, 1, 35.0)
        self.assertFalse(_scope_passes(_finish_scope(scope)))


if __name__ == "__main__":
    unittest.main()
