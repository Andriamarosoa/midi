package com.guitarmidi.ai

import kotlin.math.*

data class StreamFeatures(
    val detectedOnset: Float,
    val onsetConfidence: Float,
    val onsetAge: Float,
    val rmsLevel: Float,
    val rmsGrowthRatio: Float,
    val spectralFlux: Float,
)

data class MidiEvent(val on: Boolean, val pitch: Int, val velocity: Int)
data class DecoderResult(
    val active: Boolean,
    val pitch: Int,
    val rawPitch: Int,
    val retrigger: Boolean,
    val transitionScore: Float?,
    val transitionVeto: Boolean,
    val events: List<MidiEvent>,
)

class MidiDecoder(private val runtime: LiteRuntime) {
    var current = -1
        private set
    private var frame = -1
    private var currentSince = 0
    private var pending = -2
    private var pendingCount = 0
    private var blocked = -2
    private var lastNoteOn = Int.MIN_VALUE / 2
    private var previousPitch: FloatArray? = null
    private val minRetriggerFrames = ceil(
        Contract.MINIMUM_RETRIGGER_MS / (Contract.HOP * 1000.0 / Contract.SAMPLE_RATE)
    ).toInt()

    fun reset() {
        current = -1; frame = -1; currentSince = 0; pending = -2
        pendingCount = 0; blocked = -2; lastNoteOn = Int.MIN_VALUE / 2
        previousPitch = null
    }

    private fun argmax(values: FloatArray): Int {
        var best = 0
        for (index in 1 until values.size) if (values[index] > values[best]) best = index
        return best
    }

    private fun velocity(confidence: Float) = (30f + 97f * confidence)
        .roundToInt().coerceIn(1, 127)

    private fun features(
        candidate: Int,
        prediction: PitchPrediction,
        stream: StreamFeatures,
    ): FloatArray {
        val probabilities = prediction.pitch
        val previous = requireNotNull(previousPitch)
        val candidateClass = candidate - Contract.MIN_PITCH
        val currentClass = current - Contract.MIN_PITCH
        val sorted = probabilities.sorted()
        val candidateConfidence = probabilities[candidateClass]
        val currentConfidence = probabilities[currentClass]
        val second = sorted[sorted.lastIndex - 1]
        val interval = candidate - current
        var harmonicStrength = 0f
        var strongestMatch = 0f
        var overtoneMax = 0f
        if (prediction.harmonicAmplitude.size > 1) {
            overtoneMax = prediction.harmonicAmplitude.drop(1).max()
            if (interval > 0) {
                for (number in 2..prediction.harmonicAmplitude.size) {
                    val expected = (12.0 * log2(number.toDouble())).roundToInt()
                    if (expected == interval) harmonicStrength = max(
                        harmonicStrength, prediction.harmonicAmplitude[number - 1]
                    )
                }
                val strongest = prediction.harmonicAmplitude.drop(1)
                    .indices.maxBy { prediction.harmonicAmplitude[it + 1] } + 2
                strongestMatch = if ((12.0 * log2(strongest.toDouble())).roundToInt() == interval) 1f else 0f
            }
        }
        val range = (Contract.MAX_PITCH - Contract.MIN_PITCH).coerceAtLeast(1)
        return floatArrayOf(
            prediction.active,
            candidateConfidence,
            currentConfidence,
            candidateConfidence - second,
            (candidateConfidence - previous[candidateClass]).coerceIn(-1f, 1f),
            (previous[currentClass] - currentConfidence).coerceIn(-1f, 1f),
            (interval / 36f).coerceIn(-1f, 1f),
            (abs(interval) / 36f).coerceIn(0f, 1f),
            (current - Contract.MIN_PITCH) / range.toFloat(),
            (candidate - Contract.MIN_PITCH) / range.toFloat(),
            ((frame - currentSince) * Contract.HOP / Contract.SAMPLE_RATE.toFloat()).coerceIn(0f, 1f),
            stream.detectedOnset, stream.onsetConfidence, stream.onsetAge,
            stream.rmsLevel, stream.rmsGrowthRatio, stream.spectralFlux,
            harmonicStrength, strongestMatch, overtoneMax,
        )
    }

    fun step(prediction: PitchPrediction, stream: StreamFeatures): DecoderResult {
        frame++
        val rawPitch = argmax(prediction.pitch) + Contract.MIN_PITCH
        val desired = if (prediction.active >= Contract.ACTIVE_THRESHOLD) rawPitch else -1
        var score: Float? = null
        var veto = false
        var retrigger = false
        val events = mutableListOf<MidiEvent>()
        val previousState = current
        if (blocked != -2 && desired != blocked) blocked = -2
        if (desired == current) {
            pending = -2; pendingCount = 0; blocked = -2
            if (current >= 0 && stream.detectedOnset >= 0.5f &&
                stream.onsetConfidence >= Contract.RETRIGGER_CONFIDENCE_THRESHOLD &&
                frame - lastNoteOn >= minRetriggerFrames
            ) {
                retrigger = true
                events += MidiEvent(false, current, 0)
                events += MidiEvent(true, current, velocity(prediction.pitch.max()))
                lastNoteOn = frame
            }
        } else if (desired == blocked) {
            pending = -2; pendingCount = 0
        } else {
            if (desired == pending) pendingCount++ else { pending = desired; pendingCount = 1 }
            if (pendingCount >= Contract.STABILITY_FRAMES) {
                var allowed = true
                if (current >= 0 && desired >= 0) {
                    score = runtime.gate(features(desired, prediction, stream))
                    allowed = score >= Contract.TRANSITION_THRESHOLD
                }
                if (allowed) {
                    current = desired; currentSince = frame; blocked = -2
                    if (previousState >= 0) events += MidiEvent(false, previousState, 0)
                    if (current >= 0) {
                        events += MidiEvent(true, current, velocity(prediction.pitch.max()))
                        lastNoteOn = frame
                    }
                } else { blocked = desired; veto = true }
                pending = -2; pendingCount = 0
            }
        }
        previousPitch = prediction.pitch.copyOf()
        return DecoderResult(current >= 0, current, rawPitch, retrigger, score, veto, events)
    }
}
