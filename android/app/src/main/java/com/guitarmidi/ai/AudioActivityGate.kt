package com.guitarmidi.ai

import kotlin.math.ceil
import kotlin.math.floor
import kotlin.math.log10
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

data class AudioActivityFrame(
    val active: Boolean,
    val calibrated: Boolean,
    val calibrationStable: Boolean?,
    val rmsDbfs: Double,
    val openThresholdDbfs: Double?,
    val closeThresholdDbfs: Double?,
)

/** Frozen, session-calibrated RMS gate matching the desktop live policy. */
class CalibratedAudioActivityGate(
    sampleRate: Int = PolyContract.SAMPLE_RATE,
    hopSamples: Int = PolyContract.HOP,
    calibrationSeconds: Double = 1.0,
    calibrationTailSeconds: Double = 0.4,
    maximumCalibrationSeconds: Double = 3.0,
    private val maximumTailSpreadDb: Double = 8.0,
    private val openQuantile: Double = 0.99,
    private val closeQuantile: Double = 0.90,
    private val minimumOpenDbfs: Double = -72.0,
    private val minimumCloseDbfs: Double = -75.0,
    private val minimumHysteresisDb: Double = 0.75,
) {
    val minimumCalibrationHops: Int
    val tailHops: Int
    val maximumCalibrationHops: Int
    private val calibration = mutableListOf<Double>()
    private var stable: Boolean? = null
    private var openThreshold: Double? = null
    private var closeThreshold: Double? = null
    var calibrated: Boolean = false
        private set
    var active: Boolean = false
        private set

    init {
        require(sampleRate > 0 && hopSamples > 0)
        require(calibrationSeconds > 0.0 && calibrationTailSeconds > 0.0)
        require(maximumCalibrationSeconds >= calibrationSeconds)
        require(closeQuantile > 0.0 && closeQuantile < openQuantile)
        require(openQuantile < 1.0)
        require(maximumTailSpreadDb > 0.0 && minimumHysteresisDb > 0.0)
        require(minimumCloseDbfs < minimumOpenDbfs)
        val hopsPerSecond = sampleRate.toDouble() / hopSamples
        minimumCalibrationHops = max(
            4, (calibrationSeconds * hopsPerSecond).roundToInt(),
        )
        tailHops = max(
            4,
            min(
                minimumCalibrationHops,
                (calibrationTailSeconds * hopsPerSecond).roundToInt(),
            ),
        )
        maximumCalibrationHops = max(
            minimumCalibrationHops,
            (maximumCalibrationSeconds * hopsPerSecond).roundToInt(),
        )
    }

    private fun quantile(values: List<Double>, probability: Double): Double {
        require(values.isNotEmpty())
        val sorted = values.sorted()
        val position = (sorted.size - 1) * probability
        val lower = floor(position).toInt()
        val upper = ceil(position).toInt()
        if (lower == upper) return sorted[lower]
        val weight = position - lower
        return sorted[lower] * (1.0 - weight) + sorted[upper] * weight
    }

    private fun finishCalibration(isStable: Boolean) {
        val tail = calibration.takeLast(tailHops)
        val open = max(minimumOpenDbfs, quantile(tail, openQuantile))
        var close = max(minimumCloseDbfs, quantile(tail, closeQuantile))
        close = min(close, open - minimumHysteresisDb)
        openThreshold = open
        closeThreshold = close
        stable = isStable
        calibrated = true
        active = false
    }

    fun processRms(rms: Double): AudioActivityFrame {
        require(rms.isFinite() && rms >= 0.0)
        val rmsDbfs = 20.0 * log10(max(rms, 1e-12))
        if (!calibrated) {
            calibration += rmsDbfs
            if (calibration.size >= minimumCalibrationHops) {
                val tail = calibration.takeLast(tailHops)
                val spread = quantile(tail, 0.95) - quantile(tail, 0.05)
                val isStable = spread <= maximumTailSpreadDb
                if (isStable || calibration.size >= maximumCalibrationHops) {
                    finishCalibration(isStable)
                }
            }
        } else if (active) {
            if (rmsDbfs < requireNotNull(closeThreshold)) active = false
        } else if (rmsDbfs >= requireNotNull(openThreshold)) {
            active = true
        }
        return AudioActivityFrame(
            active, calibrated, stable, rmsDbfs, openThreshold, closeThreshold,
        )
    }

    fun resetContinuity() {
        active = false
    }

    fun reset() {
        calibration.clear()
        stable = null
        openThreshold = null
        closeThreshold = null
        calibrated = false
        active = false
    }
}
