package com.guitarmidi.ai

import android.content.Context

data class PolyProductFrame(
    val calibrated: Boolean,
    val decoder: PolyDecoderResult?,
    val onsetEvidence: OnsetFrame,
    val activityEvidence: AudioActivityFrame,
    val visibleWindow: Int,
    val inferenceMs: Double,
)

class PolyProductEngine(context: Context) : AutoCloseable {
    private val metadata = PolyModelMetadata.load(context)
    private val runtime = PolyLiteRuntime(context, metadata)
    private val decoder = PolyMidiDecoder(PolyDecoderConfig.from(metadata))
    private val onsetDetector = OnsetDetector()
    private val activityGate = CalibratedAudioActivityGate()
    private val ring = FloatArray(PolyContract.WINDOW)
    private val window = FloatArray(PolyContract.WINDOW)
    private var writeIndex = 0
    private var totalSamples = 0L
    private var wasCalibrated = false

    fun reset() {
        decoder.reset()
        onsetDetector.reset()
        activityGate.reset()
        ring.fill(0f)
        window.fill(0f)
        writeIndex = 0
        totalSamples = 0L
        wasCalibrated = false
    }

    private fun write(hop: FloatArray) {
        val first = minOf(hop.size, PolyContract.WINDOW - writeIndex)
        hop.copyInto(ring, writeIndex, 0, first)
        if (first < hop.size) hop.copyInto(ring, 0, first, hop.size)
        writeIndex = (writeIndex + hop.size) % PolyContract.WINDOW
    }

    private fun copyLatestWindow() {
        val first = PolyContract.WINDOW - writeIndex
        ring.copyInto(window, 0, writeIndex, PolyContract.WINDOW)
        if (writeIndex > 0) ring.copyInto(window, first, 0, writeIndex)
    }

    fun process(hop: FloatArray): PolyProductFrame {
        require(hop.size == PolyContract.HOP)
        write(hop)
        totalSamples += hop.size
        val onsetEvidence = onsetDetector.process(hop)
        val activityEvidence = activityGate.processRms(onsetEvidence.rms)
        val visibleWindow = totalSamples.coerceAtMost(PolyContract.WINDOW.toLong()).toInt()
        copyLatestWindow()
        if (!onsetEvidence.calibrated || !activityEvidence.calibrated) {
            wasCalibrated = false
            return PolyProductFrame(
                false, null, onsetEvidence, activityEvidence, visibleWindow, 0.0,
            )
        }
        if (!wasCalibrated) decoder.reset()
        wasCalibrated = true
        val prediction = runtime.infer(window, visibleWindow)
        val decoded = decoder.step(
            prediction, audioActive = activityEvidence.active,
        )
        return PolyProductFrame(
            true, decoded, onsetEvidence, activityEvidence,
            visibleWindow, prediction.inferenceMs,
        )
    }

    fun panicEvents(): List<MidiEvent> = decoder.panic()

    override fun close() = runtime.close()
}
