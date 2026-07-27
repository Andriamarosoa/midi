from __future__ import annotations

import unittest

from src.stream.audio_activity_gate import CalibratedAudioActivityGate


def _rms(dbfs: float) -> float:
    return 10.0 ** (float(dbfs) / 20.0)


class CalibratedAudioActivityGateTests(unittest.TestCase):
    def _gate(self, **kwargs) -> CalibratedAudioActivityGate:
        return CalibratedAudioActivityGate(
            1000,
            10,
            calibration_s=1.0,
            calibration_tail_s=0.4,
            maximum_calibration_s=3.0,
            **kwargs,
        )

    def _calibrate(self, gate, values) -> None:
        for value in values:
            gate.process_rms(_rms(value))

    def test_uses_stable_tail_instead_of_startup_zeros(self):
        gate = self._gate()
        values = [-110.0] * 60 + [-68.0 + 0.4 * (index % 3) for index in range(40)]
        self._calibrate(gate, values)
        self.assertTrue(gate.calibrated)
        self.assertTrue(gate.diagnostics()["calibration_stable"])
        self.assertGreater(gate.open_threshold_dbfs, -70.0)
        self.assertLess(gate.open_threshold_dbfs, -66.0)

    def test_thresholds_do_not_learn_a_long_guitar_sustain(self):
        gate = self._gate()
        self._calibrate(gate, [-68.0] * 100)
        before = (
            gate.open_threshold_dbfs,
            gate.close_threshold_dbfs,
        )
        for _ in range(1000):
            result = gate.process_rms(_rms(-35.0))
            self.assertTrue(result.active)
        self.assertEqual(
            before,
            (gate.open_threshold_dbfs, gate.close_threshold_dbfs),
        )

    def test_open_close_hysteresis(self):
        gate = self._gate()
        self._calibrate(gate, [-68.0] * 100)
        opened = gate.process_rms(_rms(-60.0))
        self.assertTrue(opened.active)
        between = (
            float(gate.open_threshold_dbfs)
            + float(gate.close_threshold_dbfs)
        ) / 2.0
        self.assertTrue(gate.process_rms(_rms(between)).active)
        self.assertFalse(
            gate.process_rms(_rms(float(gate.close_threshold_dbfs) - 1.0)).active
        )

    def test_unstable_tail_extends_calibration_until_silence_is_stable(self):
        gate = self._gate()
        contaminated = [-68.0, -35.0] * 20
        self._calibrate(gate, [-68.0] * 60 + contaminated)
        self.assertFalse(gate.calibrated)
        self._calibrate(gate, [-68.0] * 40)
        self.assertTrue(gate.calibrated)
        report = gate.diagnostics()
        self.assertTrue(report["calibration_stable"])
        self.assertGreater(report["calibration_extended_hops"], 0)

    def test_forces_bounded_calibration_in_a_persistently_unstable_room(self):
        gate = self._gate()
        self._calibrate(gate, [-68.0, -35.0] * 150)
        report = gate.diagnostics()
        self.assertTrue(gate.calibrated)
        self.assertFalse(report["calibration_stable"])
        self.assertEqual(report["calibration_hops_seen"], 300)

    def test_continuity_reset_closes_gate_but_keeps_thresholds(self):
        gate = self._gate()
        self._calibrate(gate, [-68.0] * 100)
        gate.process_rms(_rms(-40.0))
        self.assertTrue(gate.active)
        thresholds = (gate.open_threshold_dbfs, gate.close_threshold_dbfs)
        gate.reset_continuity()
        self.assertFalse(gate.active)
        self.assertTrue(gate.calibrated)
        self.assertEqual(
            thresholds,
            (gate.open_threshold_dbfs, gate.close_threshold_dbfs),
        )


if __name__ == "__main__":
    unittest.main()
