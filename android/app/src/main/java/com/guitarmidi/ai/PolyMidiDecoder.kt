package com.guitarmidi.ai

import kotlin.math.abs
import kotlin.math.log2
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

data class PolyDecoderConfig(
    val frameOnThreshold: Float,
    val strongFrameThreshold: Float,
    val frameOffThreshold: Float,
    val onsetThreshold: Float,
    val activationFrames: Int = 2,
    val releaseFrames: Int = 3,
    val minimumRetriggerFrames: Int = 14,
    val silenceReleaseFrames: Int = 2,
    val maximumPolyphony: Int = PolyContract.MAXIMUM_POLYPHONY,
    val harmonicSuppressionStrength: Float = 0.25f,
    val harmonicToleranceCents: Double = 35.0,
) {
    companion object {
        fun from(metadata: PolyModelMetadata) = metadata.decoder
    }
}

data class PolyDecoderResult(
    val activePitches: IntArray,
    val events: List<MidiEvent>,
    val frameIndex: Long,
)

class PolyMidiDecoder(private val config: PolyDecoderConfig) {
    private val active = BooleanArray(PolyContract.PITCH_CLASSES)
    private val activationCount = IntArray(PolyContract.PITCH_CLASSES)
    private val releaseCount = IntArray(PolyContract.PITCH_CLASSES)
    private val lastNoteOn = LongArray(PolyContract.PITCH_CLASSES) { -1_000_000_000L }
    private var frameIndex = -1L
    private var silenceCount = 0

    init {
        require(config.frameOffThreshold <= config.frameOnThreshold)
        require(config.frameOnThreshold <= config.strongFrameThreshold)
        require(config.maximumPolyphony in 1..PolyContract.PITCH_CLASSES)
        require(config.activationFrames > 0 && config.releaseFrames > 0)
    }

    fun reset() {
        active.fill(false)
        activationCount.fill(0)
        releaseCount.fill(0)
        lastNoteOn.fill(-1_000_000_000L)
        frameIndex = -1L
        silenceCount = 0
    }

    private fun activePitches(): IntArray = active.indices
        .filter { active[it] }
        .map { PolyContract.MIN_PITCH + it }
        .toIntArray()

    private fun velocity(frame: Float, onset: Float): Int =
        (35f + 92f * max(frame, onset)).roundToInt().coerceIn(1, 127)

    private fun harmonicNumber(basePitch: Int, candidatePitch: Int): Int? {
        if (candidatePitch <= basePitch) return null
        val ratio = 2.0.pow((candidatePitch - basePitch) / 12.0)
        val number = ratio.roundToInt()
        if (number < 2) return null
        val cents = abs(1200.0 * log2(ratio / number))
        return if (cents <= config.harmonicToleranceCents) number else null
    }

    private fun adaptiveOnThreshold(
        classIndex: Int,
        onsetProbability: Float,
        harmonics: FloatArray,
    ): Float {
        if (onsetProbability >= config.onsetThreshold) return config.frameOnThreshold
        val candidatePitch = PolyContract.MIN_PITCH + classIndex
        var support = 0f
        for (baseIndex in active.indices) {
            if (!active[baseIndex]) continue
            val number = harmonicNumber(
                PolyContract.MIN_PITCH + baseIndex, candidatePitch,
            ) ?: continue
            if (number > PolyContract.HARMONICS) continue
            support = max(
                support,
                harmonics[baseIndex * PolyContract.HARMONICS + number - 1],
            )
        }
        return min(
            config.strongFrameThreshold,
            config.frameOnThreshold + config.harmonicSuppressionStrength * support,
        )
    }

    fun step(prediction: PolyPrediction, audioActive: Boolean): PolyDecoderResult {
        require(prediction.frame.size == PolyContract.PITCH_CLASSES)
        require(prediction.onset.size == PolyContract.PITCH_CLASSES)
        require(
            prediction.harmonicAmplitude.size ==
                PolyContract.PITCH_CLASSES * PolyContract.HARMONICS,
        )
        frameIndex++
        if (!audioActive) {
            // Activation requires consecutive audible evidence.  Never allow
            // a quiet hop to complete a stale vote or emit a direct onset.
            activationCount.fill(0)
            silenceCount++
            if (silenceCount >= config.silenceReleaseFrames) {
                val events = panic()
                return PolyDecoderResult(activePitches(), events, frameIndex)
            }
            return PolyDecoderResult(activePitches(), emptyList(), frameIndex)
        }
        silenceCount = 0

        val events = mutableListOf<MidiEvent>()
        for (classIndex in active.indices) {
            if (!active[classIndex]) continue
            val pitch = PolyContract.MIN_PITCH + classIndex
            if (prediction.frame[classIndex] < config.frameOffThreshold) {
                releaseCount[classIndex]++
            } else {
                releaseCount[classIndex] = 0
            }
            if (releaseCount[classIndex] >= config.releaseFrames) {
                active[classIndex] = false
                releaseCount[classIndex] = 0
                activationCount[classIndex] = 0
                events += MidiEvent(false, pitch, 0)
                continue
            }
            if (
                prediction.onset[classIndex] >= config.onsetThreshold &&
                prediction.frame[classIndex] >= config.frameOnThreshold &&
                frameIndex - lastNoteOn[classIndex] >= config.minimumRetriggerFrames
            ) {
                val velocity = velocity(
                    prediction.frame[classIndex], prediction.onset[classIndex],
                )
                events += MidiEvent(false, pitch, 0)
                events += MidiEvent(true, pitch, velocity)
                lastNoteOn[classIndex] = frameIndex
            }
        }

        val available = config.maximumPolyphony - active.count { it }
        val candidates = mutableListOf<Pair<Float, Int>>()
        for (classIndex in active.indices) {
            if (active[classIndex]) continue
            val threshold = adaptiveOnThreshold(
                classIndex,
                prediction.onset[classIndex],
                prediction.harmonicAmplitude,
            )
            val directOnset =
                prediction.onset[classIndex] >= config.onsetThreshold &&
                    prediction.frame[classIndex] >= config.frameOnThreshold
            if (prediction.frame[classIndex] >= threshold) {
                activationCount[classIndex]++
            } else {
                activationCount[classIndex] = 0
            }
            val stableFrame =
                activationCount[classIndex] >= config.activationFrames &&
                    prediction.frame[classIndex] >= threshold
            if (directOnset || stableFrame) {
                candidates += Pair(
                    prediction.frame[classIndex] + prediction.onset[classIndex],
                    classIndex,
                )
            }
        }
        candidates.sortedByDescending { it.first }
            .take(max(0, available))
            .forEach { (_, classIndex) ->
                val pitch = PolyContract.MIN_PITCH + classIndex
                active[classIndex] = true
                activationCount[classIndex] = 0
                releaseCount[classIndex] = 0
                lastNoteOn[classIndex] = frameIndex
                events += MidiEvent(
                    true,
                    pitch,
                    velocity(prediction.frame[classIndex], prediction.onset[classIndex]),
                )
            }
        return PolyDecoderResult(activePitches(), events, frameIndex)
    }

    fun panic(): List<MidiEvent> {
        val events = active.indices.filter { active[it] }.map {
            MidiEvent(false, PolyContract.MIN_PITCH + it, 0)
        }
        active.fill(false)
        activationCount.fill(0)
        releaseCount.fill(0)
        return events
    }
}

private fun Double.pow(exponent: Double): Double = Math.pow(this, exponent)
