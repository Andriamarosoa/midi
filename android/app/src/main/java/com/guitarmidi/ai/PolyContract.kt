package com.guitarmidi.ai

import android.content.Context
import org.json.JSONObject

object PolyContract {
    const val PRODUCT_VERSION = "2.2.0"
    const val SAMPLE_RATE = 44_100
    const val HOP = 256
    const val WINDOW = 4096
    const val MIN_PITCH = 40
    const val MAX_PITCH = 76
    const val PITCH_CLASSES = MAX_PITCH - MIN_PITCH + 1
    const val HARMONICS = 20
    const val MAXIMUM_POLYPHONY = 6
    const val METADATA_ASSET = "polyphonic_metadata.json"
    const val MODEL_ASSET = "guitar_midi_polyphonic.tflite"

    val REQUIRED_OUTPUTS = setOf(
        "frame", "onset", "harmonic_amplitude", "harmonic_offset_cents",
    )
}

data class PolyModelMetadata(
    val productVersion: String,
    val normalizationGain: Float,
    val frameThreshold: Float,
    val onsetThreshold: Float,
    val recommendedThreads: Int,
    val modelAsset: String,
    val modelSha256: String,
    val decoder: PolyDecoderConfig,
) {
    companion object {
        fun load(context: Context): PolyModelMetadata {
            val text = context.assets.open(PolyContract.METADATA_ASSET)
                .bufferedReader(Charsets.UTF_8).use { it.readText() }
            val root = JSONObject(text)
            require(root.getInt("sample_rate") == PolyContract.SAMPLE_RATE)
            require(root.getInt("hop_samples") == PolyContract.HOP)
            require(root.getInt("max_window_samples") == PolyContract.WINDOW)
            require(root.getInt("min_pitch") == PolyContract.MIN_PITCH)
            require(root.getInt("max_pitch") == PolyContract.MAX_PITCH)
            require(root.getInt("maximum_polyphony") == PolyContract.MAXIMUM_POLYPHONY)
            require(root.getBoolean("polyphony_supported"))
            val outputs = root.getJSONArray("outputs")
            val names = (0 until outputs.length()).map { outputs.getString(it) }.toSet()
            require(names.containsAll(PolyContract.REQUIRED_OUTPUTS))
            val artifact = root.getJSONObject("artifact")
            val modelAsset = artifact.getString("tflite")
            require(modelAsset == PolyContract.MODEL_ASSET)
            val frameThreshold = root.getDouble("frame_threshold").toFloat()
            val onsetThreshold = root.getDouble("onset_threshold").toFloat()
            val decoderJson = root.optJSONObject("decoder")
            val decoder = if (decoderJson == null) {
                PolyDecoderConfig(
                    frameOnThreshold = frameThreshold,
                    strongFrameThreshold = kotlin.math.min(
                        0.95f, kotlin.math.max(0.80f, frameThreshold + 0.25f),
                    ),
                    frameOffThreshold = kotlin.math.max(0.05f, frameThreshold * 0.60f),
                    onsetThreshold = onsetThreshold,
                )
            } else {
                PolyDecoderConfig(
                    frameOnThreshold = decoderJson.getDouble("frame_on_threshold").toFloat(),
                    strongFrameThreshold = decoderJson.getDouble(
                        "strong_frame_threshold",
                    ).toFloat(),
                    frameOffThreshold = decoderJson.getDouble("frame_off_threshold").toFloat(),
                    onsetThreshold = decoderJson.getDouble("onset_threshold").toFloat(),
                    activationFrames = decoderJson.getInt("activation_frames"),
                    releaseFrames = decoderJson.getInt("release_frames"),
                    minimumRetriggerFrames = decoderJson.getInt(
                        "minimum_retrigger_frames",
                    ),
                    silenceReleaseFrames = decoderJson.getInt("silence_release_frames"),
                    maximumPolyphony = decoderJson.getInt("maximum_polyphony"),
                    harmonicSuppressionStrength = decoderJson.getDouble(
                        "harmonic_suppression_strength",
                    ).toFloat(),
                    harmonicToleranceCents = decoderJson.getDouble(
                        "harmonic_tolerance_cents",
                    ),
                )
            }
            return PolyModelMetadata(
                productVersion = root.getString("product_version"),
                normalizationGain = root.getDouble("normalization_gain").toFloat(),
                frameThreshold = frameThreshold,
                onsetThreshold = onsetThreshold,
                // Desktop benchmarking includes the Windows audio stack.  An
                // Android-specific value is deliberately separate so XNNPACK
                // workers do not contend with AudioRecord's priority thread.
                recommendedThreads = root.optInt(
                    "recommended_android_tflite_threads", 1,
                )
                    .coerceIn(1, 4),
                modelAsset = modelAsset,
                modelSha256 = artifact.getString("sha256").lowercase(),
                decoder = decoder,
            ).also {
                require(it.productVersion == PolyContract.PRODUCT_VERSION)
                require(it.normalizationGain > 0f)
                require(it.frameThreshold in 0f..1f)
                require(it.onsetThreshold in 0f..1f)
                require(it.modelSha256.matches(Regex("[0-9a-f]{64}")))
            }
        }
    }
}
