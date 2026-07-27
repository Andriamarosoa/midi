from __future__ import annotations

import unittest

from src.polyphonic.runtime_parity import parity_passes


def _metrics() -> dict[str, object]:
    return {
        "frame": {"maximum_absolute_error": 0.001},
        "onset": {"maximum_absolute_error": 0.001},
        "harmonic_amplitude": {"maximum_absolute_error": 0.001},
        "harmonic_offset_cents": {"maximum_absolute_error": 0.05},
        "frame_decision_agreement": 0.9995,
        "onset_decision_agreement": 1.0,
    }


class PolyphonicRuntimeParityTests(unittest.TestCase):
    def test_accepts_small_scale_aware_float16_drift(self) -> None:
        self.assertTrue(parity_passes(_metrics()))

    def test_rejects_probability_drift(self) -> None:
        metrics = _metrics()
        metrics["frame"] = {"maximum_absolute_error": 0.0021}
        self.assertFalse(parity_passes(metrics))

    def test_rejects_decision_drift(self) -> None:
        metrics = _metrics()
        metrics["onset_decision_agreement"] = 0.9989
        self.assertFalse(parity_passes(metrics))

    def test_harmonic_offsets_use_cents_tolerance(self) -> None:
        metrics = _metrics()
        metrics["harmonic_offset_cents"] = {"maximum_absolute_error": 0.101}
        self.assertFalse(parity_passes(metrics))


if __name__ == "__main__":
    unittest.main()
