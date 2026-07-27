package com.guitarmidi.ai

import android.content.Context
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel

data class PitchPrediction(
    val active: Float,
    val pitch: FloatArray,
    val harmonicAmplitude: FloatArray,
    val harmonicOffsetCents: FloatArray,
    val inferenceMs: Double,
)

private fun mappedAsset(context: Context, name: String): MappedByteBuffer {
    val descriptor = context.assets.openFd(name)
    FileInputStream(descriptor.fileDescriptor).use { input ->
        return input.channel.map(
            FileChannel.MapMode.READ_ONLY,
            descriptor.startOffset,
            descriptor.declaredLength,
        )
    }
}

private fun floatBuffer(size: Int): ByteBuffer =
    ByteBuffer.allocateDirect(size * 4).order(ByteOrder.nativeOrder())

class LiteRuntime(context: Context) : AutoCloseable {
    private val pitchInterpreter = Interpreter(
        mappedAsset(context, "guitar_midi_pitch.tflite"),
        Interpreter.Options().setNumThreads(1),
    )
    private val gateInterpreter = Interpreter(
        mappedAsset(context, "guitar_midi_transition_gate.tflite"),
        Interpreter.Options().setNumThreads(1),
    )
    private val audioInput = floatBuffer(Contract.WINDOW)
    private val maskInput = floatBuffer(Contract.WINDOW)
    private val activeOutput = floatBuffer(1)
    private val pitchOutput = floatBuffer(Contract.MAX_PITCH - Contract.MIN_PITCH + 1)
    private val harmonicOutput = floatBuffer(20)
    private val offsetOutput = floatBuffer(20)
    private val gateInput = floatBuffer(20)
    private val gateOutput = floatBuffer(1)

    fun infer(window: FloatArray, visibleWindow: Int): PitchPrediction {
        val visible = visibleWindow.coerceIn(1, Contract.WINDOW)
        audioInput.clear()
        maskInput.clear()
        for (index in 0 until Contract.WINDOW) {
            val present = index >= Contract.WINDOW - visible
            val value = if (present) {
                (window[index] * Contract.NORMALIZATION_GAIN).coerceIn(-1f, 1f)
            } else 0f
            audioInput.putFloat(value)
            maskInput.putFloat(if (present) 1f else 0f)
        }
        audioInput.rewind()
        maskInput.rewind()
        activeOutput.clear(); pitchOutput.clear(); harmonicOutput.clear(); offsetOutput.clear()
        val started = System.nanoTime()
        pitchInterpreter.runSignature(
            mapOf("audio" to audioInput, "time_mask" to maskInput),
            mapOf(
                "active" to activeOutput,
                "pitch" to pitchOutput,
                "harmonic_amplitude" to harmonicOutput,
                "harmonic_offset_cents" to offsetOutput,
            ),
            "serving_default",
        )
        val elapsed = (System.nanoTime() - started) / 1_000_000.0
        activeOutput.rewind(); pitchOutput.rewind(); harmonicOutput.rewind(); offsetOutput.rewind()
        return PitchPrediction(
            activeOutput.float,
            FloatArray(37) { pitchOutput.float },
            FloatArray(20) { harmonicOutput.float },
            FloatArray(20) { offsetOutput.float },
            elapsed,
        )
    }

    fun gate(features: FloatArray): Float {
        require(features.size == 20)
        gateInput.clear()
        features.forEach(gateInput::putFloat)
        gateInput.rewind(); gateOutput.clear()
        gateInterpreter.runSignature(
            mapOf("features" to gateInput),
            mapOf("allow_transition" to gateOutput),
            "serving_default",
        )
        gateOutput.rewind()
        return gateOutput.float
    }

    override fun close() {
        gateInterpreter.close()
        pitchInterpreter.close()
    }
}
