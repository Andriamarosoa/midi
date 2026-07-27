package com.guitarmidi.ai

import android.content.Context
import org.tensorflow.lite.Interpreter
import java.io.FileInputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.nio.MappedByteBuffer
import java.nio.channels.FileChannel
import java.security.MessageDigest

data class PolyPrediction(
    val frame: FloatArray,
    val onset: FloatArray,
    val harmonicAmplitude: FloatArray,
    val harmonicOffsetCents: FloatArray,
    val inferenceMs: Double,
)

private fun mapPolyAsset(context: Context, name: String): MappedByteBuffer {
    val descriptor = context.assets.openFd(name)
    FileInputStream(descriptor.fileDescriptor).use { input ->
        return input.channel.map(
            FileChannel.MapMode.READ_ONLY,
            descriptor.startOffset,
            descriptor.declaredLength,
        )
    }
}

private fun polyFloatBuffer(size: Int): ByteBuffer =
    ByteBuffer.allocateDirect(size * Float.SIZE_BYTES).order(ByteOrder.nativeOrder())

private fun assetSha256(context: Context, name: String): String {
    val digest = MessageDigest.getInstance("SHA-256")
    context.assets.open(name).use { input ->
        val block = ByteArray(64 * 1024)
        while (true) {
            val count = input.read(block)
            if (count < 0) break
            if (count > 0) digest.update(block, 0, count)
        }
    }
    return digest.digest().joinToString("") { "%02x".format(it) }
}

class PolyLiteRuntime(
    context: Context,
    val metadata: PolyModelMetadata = PolyModelMetadata.load(context),
) : AutoCloseable {
    private val interpreter: Interpreter
    private val audioInput = polyFloatBuffer(PolyContract.WINDOW)
    private val maskInput = polyFloatBuffer(PolyContract.WINDOW)
    private val frameOutput = polyFloatBuffer(PolyContract.PITCH_CLASSES)
    private val onsetOutput = polyFloatBuffer(PolyContract.PITCH_CLASSES)
    private val harmonicOutput = polyFloatBuffer(
        PolyContract.PITCH_CLASSES * PolyContract.HARMONICS,
    )
    private val offsetOutput = polyFloatBuffer(
        PolyContract.PITCH_CLASSES * PolyContract.HARMONICS,
    )

    init {
        require(assetSha256(context, metadata.modelAsset) == metadata.modelSha256) {
            "Le modele polyphonique Android ne correspond pas a ses metadonnees."
        }
        interpreter = Interpreter(
            mapPolyAsset(context, metadata.modelAsset),
            Interpreter.Options().setNumThreads(metadata.recommendedThreads),
        )
    }

    fun infer(window: FloatArray, visibleWindow: Int): PolyPrediction {
        require(window.size == PolyContract.WINDOW)
        val visible = visibleWindow.coerceIn(1, PolyContract.WINDOW)
        audioInput.clear()
        maskInput.clear()
        for (index in 0 until PolyContract.WINDOW) {
            val present = index >= PolyContract.WINDOW - visible
            audioInput.putFloat(
                if (present) {
                    (window[index] * metadata.normalizationGain).coerceIn(-1f, 1f)
                } else 0f,
            )
            maskInput.putFloat(if (present) 1f else 0f)
        }
        audioInput.rewind()
        maskInput.rewind()
        frameOutput.clear()
        onsetOutput.clear()
        harmonicOutput.clear()
        offsetOutput.clear()
        val started = System.nanoTime()
        interpreter.runSignature(
            mapOf("audio" to audioInput, "time_mask" to maskInput),
            mapOf(
                "frame" to frameOutput,
                "onset" to onsetOutput,
                "harmonic_amplitude" to harmonicOutput,
                "harmonic_offset_cents" to offsetOutput,
            ),
            "serving_default",
        )
        val inferenceMs = (System.nanoTime() - started) / 1_000_000.0
        frameOutput.rewind()
        onsetOutput.rewind()
        harmonicOutput.rewind()
        offsetOutput.rewind()
        return PolyPrediction(
            frame = FloatArray(PolyContract.PITCH_CLASSES) { frameOutput.float },
            onset = FloatArray(PolyContract.PITCH_CLASSES) { onsetOutput.float },
            harmonicAmplitude = FloatArray(
                PolyContract.PITCH_CLASSES * PolyContract.HARMONICS,
            ) { harmonicOutput.float },
            harmonicOffsetCents = FloatArray(
                PolyContract.PITCH_CLASSES * PolyContract.HARMONICS,
            ) { offsetOutput.float },
            inferenceMs = inferenceMs,
        )
    }

    override fun close() = interpreter.close()
}
