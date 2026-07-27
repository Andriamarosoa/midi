package com.guitarmidi.ai

object Contract {
    const val PRODUCT_VERSION = "1.0.0"
    const val SAMPLE_RATE = 44100
    const val HOP = 256
    const val WINDOW = 4096
    const val MIN_PITCH = 40
    const val MAX_PITCH = 76
    const val NORMALIZATION_GAIN = 1.4932045250002872f
    const val ACTIVE_THRESHOLD = 0.1572733223438263f
    const val TRANSITION_THRESHOLD = 0.2050777018070221f
    const val STABILITY_FRAMES = 2
    const val MINIMUM_RETRIGGER_MS = 80f
    const val RETRIGGER_CONFIDENCE_THRESHOLD = 0.5f
    val WINDOWS = intArrayOf(512, 1024, 2048, 4096)

    val FEATURE_NAMES = arrayOf(
        "active_probability", "candidate_confidence", "current_confidence",
        "pitch_margin", "candidate_probability_growth", "current_probability_drop",
        "interval_signed", "interval_absolute", "current_pitch_position",
        "candidate_pitch_position", "current_duration", "detected_onset",
        "onset_confidence", "onset_age", "rms_level", "rms_growth_ratio",
        "spectral_flux", "harmonic_match_strength", "strongest_harmonic_match",
        "max_overtone_strength",
    )
}
