package com.guitarmidi.ai

import kotlin.math.*

data class OnsetFrame(
    val isOnset: Boolean,
    val calibrated: Boolean,
    val confidence: Float,
    val rms: Double,
    val rmsDbfs: Double,
    val rmsGrowth: Double,
    val spectralFlux: Double,
)

private class RunningStats(private val capacity: Int) {
    private val values = DoubleArray(capacity)
    var count = 0
        private set
    private var index = 0

    fun reset() { values.fill(0.0); count = 0; index = 0 }
    fun add(value: Double) {
        values[index] = value
        index = (index + 1) % capacity
        count = min(count + 1, capacity)
    }
    fun median(default: Double): Double {
        if (count == 0) return default
        val copy = values.copyOf(count)
        copy.sort()
        return if (count % 2 == 1) copy[count / 2]
        else (copy[count / 2 - 1] + copy[count / 2]) * 0.5
    }
    fun robustSigma(minimum: Double): Double {
        if (count < 2) return minimum
        val center = median(0.0)
        val deviations = DoubleArray(count) { abs(values[it] - center) }
        deviations.sort()
        val mad = if (count % 2 == 1) deviations[count / 2]
        else (deviations[count / 2 - 1] + deviations[count / 2]) * 0.5
        return max(minimum, 1.4826 * mad)
    }
}

private object Fft512 {
    fun magnitude(input: DoubleArray): DoubleArray {
        val n = 512
        val real = input.copyOf()
        val imag = DoubleArray(n)
        var j = 0
        for (i in 1 until n) {
            var bit = n shr 1
            while (j and bit != 0) { j = j xor bit; bit = bit shr 1 }
            j = j xor bit
            if (i < j) {
                val r = real[i]; real[i] = real[j]; real[j] = r
            }
        }
        var length = 2
        while (length <= n) {
            val angle = -2.0 * Math.PI / length
            val baseR = cos(angle); val baseI = sin(angle)
            var start = 0
            while (start < n) {
                var wr = 1.0; var wi = 0.0
                for (offset in 0 until length / 2) {
                    val even = start + offset
                    val odd = even + length / 2
                    val tr = wr * real[odd] - wi * imag[odd]
                    val ti = wr * imag[odd] + wi * real[odd]
                    real[odd] = real[even] - tr; imag[odd] = imag[even] - ti
                    real[even] += tr; imag[even] += ti
                    val nextR = wr * baseR - wi * baseI
                    wi = wr * baseI + wi * baseR; wr = nextR
                }
                start += length
            }
            length = length shl 1
        }
        return DoubleArray(257) { hypot(real[it], imag[it]) }
    }
}

class OnsetDetector {
    private val calibrationHops = (Contract.SAMPLE_RATE / Contract.HOP.toDouble()).roundToInt()
    private val history = max(calibrationHops, (2.0 * Contract.SAMPLE_RATE / Contract.HOP).roundToInt())
    private val cooldownHops = max(1, (0.080 * Contract.SAMPLE_RATE / Contract.HOP).roundToInt())
    private val rmsStats = RunningStats(history)
    private val growthStats = RunningStats(history)
    private val fluxStats = RunningStats(history)
    private val analysis = DoubleArray(512)
    private val hann = DoubleArray(512) { 0.5 - 0.5 * cos(2.0 * Math.PI * it / 511.0) }
    private val previousSpectrum = DoubleArray(257)
    private var previousRms = 0.0
    private var hasSpectrum = false
    private var cooldown = 0
    private var armed = true

    val calibrated: Boolean get() = rmsStats.count >= calibrationHops

    fun reset() {
        rmsStats.reset(); growthStats.reset(); fluxStats.reset()
        analysis.fill(0.0); previousSpectrum.fill(0.0)
        previousRms = 0.0; hasSpectrum = false; cooldown = 0; armed = true
    }

    fun process(hop: FloatArray): OnsetFrame {
        require(hop.size == Contract.HOP)
        System.arraycopy(analysis, Contract.HOP, analysis, 0, 512 - Contract.HOP)
        for (i in hop.indices) analysis[512 - Contract.HOP + i] = hop[i].toDouble()
        val rms = sqrt(hop.sumOf { it.toDouble() * it.toDouble() } / hop.size + 1e-12)
        val rmsDbfs = 20.0 * log10(max(rms, 1e-12))
        val growth = max(0.0, rms - previousRms)
        val mean = analysis.average()
        val magnitude = Fft512.magnitude(DoubleArray(512) { (analysis[it] - mean) * hann[it] })
        val windowSum = hann.sum().coerceAtLeast(1e-12)
        val spectrum = DoubleArray(257) { ln1p(1000.0 * magnitude[it] / windowSum) }
        var flux = 0.0
        if (hasSpectrum) {
            for (i in spectrum.indices) {
                val difference = max(0.0, spectrum[i] - previousSpectrum[i])
                flux += difference * difference
            }
            flux = sqrt(flux / spectrum.size)
        } else hasSpectrum = true
        spectrum.copyInto(previousSpectrum)

        val minimumRms = 10.0.pow(-72.0 / 20.0)
        val rmsMedian = rmsStats.median(minimumRms)
        val growthMedian = growthStats.median(0.0)
        val fluxMedian = fluxStats.median(0.0)
        val rmsScale = rmsStats.robustSigma(max(minimumRms * 0.25, 1e-7))
        val growthScale = growthStats.robustSigma(max(minimumRms * 0.10, 1e-8))
        val fluxScale = fluxStats.robustSigma(1e-4)
        val rmsThreshold = max(minimumRms, rmsMedian + 5.0 * rmsScale)
        val growthThreshold = growthMedian + 4.0 * growthScale
        val fluxThreshold = fluxMedian + 4.0 * fluxScale
        if (!armed && cooldown == 0 && rms <= rmsThreshold * 1.35) armed = true
        fun excess(value: Double, threshold: Double, scale: Double) =
            if (value <= threshold) 0.0 else (value - threshold) / max(scale, 1e-12)
        val rmsExcess = excess(rms, rmsThreshold, rmsScale)
        val growthExcess = excess(growth, growthThreshold, growthScale)
        val fluxExcess = excess(flux, fluxThreshold, fluxScale)
        val score = 0.75 * min(rmsExcess, 6.0) +
            0.65 * min(growthExcess, 6.0) + 0.85 * min(fluxExcess, 6.0)
        val onset = calibrated && armed && cooldown == 0 && rms > rmsThreshold &&
            (growthExcess > 0.0 || fluxExcess > 0.0) && score >= 2.2
        if (onset) { cooldown = cooldownHops; armed = false }
        else if (cooldown > 0) cooldown--
        val update = !onset && (!calibrated || (
            armed && rms <= rmsThreshold * 1.25 && flux <= fluxThreshold * 1.25
        ))
        if (update) { rmsStats.add(rms); growthStats.add(growth); fluxStats.add(flux) }
        previousRms = rms
        return OnsetFrame(
            onset, calibrated, (score / 4.4).coerceIn(0.0, 1.0).toFloat(),
            rms, rmsDbfs, growth, flux,
        )
    }
}
