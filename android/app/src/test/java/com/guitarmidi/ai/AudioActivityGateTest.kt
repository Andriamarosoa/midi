package com.guitarmidi.ai

import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test
import kotlin.math.pow

class AudioActivityGateTest {
    private fun rms(dbfs: Double): Double = 10.0.pow(dbfs / 20.0)

    @Test fun stableSilenceCalibratesThenGuitarOpensTheGate() {
        val gate = CalibratedAudioActivityGate(
            sampleRate = 100,
            hopSamples = 1,
            calibrationSeconds = 1.0,
            calibrationTailSeconds = 0.4,
            maximumCalibrationSeconds = 3.0,
        )
        repeat(100) { gate.processRms(rms(-80.0)) }
        assertTrue(gate.calibrated)
        assertFalse(gate.active)
        assertTrue(gate.processRms(rms(-40.0)).active)
    }

    @Test fun hysteresisKeepsActivityUntilCloseThreshold() {
        val gate = CalibratedAudioActivityGate(
            sampleRate = 10,
            hopSamples = 1,
            calibrationSeconds = 1.0,
            calibrationTailSeconds = 0.4,
            maximumCalibrationSeconds = 3.0,
        )
        repeat(10) { gate.processRms(rms(-80.0)) }
        assertTrue(gate.processRms(rms(-60.0)).active)
        assertTrue(gate.processRms(rms(-73.0)).active)
        assertFalse(gate.processRms(rms(-76.0)).active)
    }

    @Test fun unstableCalibrationIsBounded() {
        val gate = CalibratedAudioActivityGate(
            sampleRate = 10,
            hopSamples = 1,
            calibrationSeconds = 1.0,
            calibrationTailSeconds = 0.4,
            maximumCalibrationSeconds = 3.0,
        )
        repeat(29) {
            gate.processRms(rms(if (it % 2 == 0) -80.0 else -30.0))
        }
        assertFalse(gate.calibrated)
        val result = gate.processRms(rms(-80.0))
        assertTrue(result.calibrated)
        assertFalse(requireNotNull(result.calibrationStable))
    }
}
