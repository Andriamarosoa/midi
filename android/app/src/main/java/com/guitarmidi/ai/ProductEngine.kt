package com.guitarmidi.ai

import android.content.Context
import kotlin.math.max
import kotlin.math.tanh

data class ProductFrame(
    val calibrated: Boolean,
    val decoder: DecoderResult?,
    val onset: OnsetFrame,
    val visibleWindow: Int,
    val inferenceMs: Double,
)

class ProductEngine(context: Context) : AutoCloseable {
    private val runtime = LiteRuntime(context)
    private val decoder = MidiDecoder(runtime)
    private val onsetDetector = OnsetDetector()
    private val ring = FloatArray(Contract.WINDOW)
    private val window = FloatArray(Contract.WINDOW)
    private var writeIndex = 0
    private var totalSamples = 0L
    private var lastOnsetSample: Long? = null
    private var windowOnsetSample: Long? = null
    private var wasCalibrated = false

    fun reset() {
        decoder.reset(); onsetDetector.reset(); ring.fill(0f); window.fill(0f)
        writeIndex = 0; totalSamples = 0; lastOnsetSample = null
        windowOnsetSample = null; wasCalibrated = false
    }

    private fun write(hop: FloatArray) {
        val first = minOf(hop.size, Contract.WINDOW - writeIndex)
        hop.copyInto(ring, writeIndex, 0, first)
        if (first < hop.size) hop.copyInto(ring, 0, first, hop.size)
        writeIndex = (writeIndex + hop.size) % Contract.WINDOW
    }

    private fun copyWindow() {
        val first = Contract.WINDOW - writeIndex
        ring.copyInto(window, 0, writeIndex, Contract.WINDOW)
        if (writeIndex > 0) ring.copyInto(window, first, 0, writeIndex)
    }

    fun process(hop: FloatArray): ProductFrame {
        require(hop.size == Contract.HOP)
        write(hop); totalSamples += Contract.HOP
        val onset = onsetDetector.process(hop)
        if (onset.isOnset) {
            lastOnsetSample = totalSamples
            if (decoder.current < 0) windowOnsetSample = totalSamples
        }
        var visible = Contract.WINDOW
        val onsetAge = lastOnsetSample?.let {
            ((totalSamples - it) / Contract.SAMPLE_RATE.toFloat() / 0.5f).coerceIn(0f, 1f)
        } ?: 1f
        windowOnsetSample?.let {
            val age = totalSamples - it
            visible = Contract.WINDOWS.firstOrNull { candidate -> age <= candidate }
                ?: Contract.WINDOW
        }
        copyWindow()
        if (!onset.calibrated) {
            wasCalibrated = false
            return ProductFrame(false, null, onset, visible, 0.0)
        }
        if (!wasCalibrated) decoder.reset()
        wasCalibrated = true
        val prediction = runtime.infer(window, visible)
        val stream = StreamFeatures(
            if (onset.isOnset) 1f else 0f,
            onset.confidence,
            onsetAge,
            ((onset.rmsDbfs + 100.0) / 100.0).coerceIn(0.0, 1.0).toFloat(),
            (onset.rmsGrowth / max(onset.rms, 1e-8)).coerceIn(0.0, 1.0).toFloat(),
            tanh(onset.spectralFlux).toFloat(),
        )
        return ProductFrame(true, decoder.step(prediction, stream), onset, visible, prediction.inferenceMs)
    }

    fun panicEvents(): List<MidiEvent> = if (decoder.current >= 0) {
        listOf(MidiEvent(false, decoder.current, 0))
    } else emptyList()

    override fun close() = runtime.close()
}
