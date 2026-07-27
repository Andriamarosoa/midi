"""Stable cross-platform tensor and decoder contract."""

FEATURE_NAMES = (
    "active_probability",
    "candidate_confidence",
    "current_confidence",
    "pitch_margin",
    "candidate_probability_growth",
    "current_probability_drop",
    "interval_signed",
    "interval_absolute",
    "current_pitch_position",
    "candidate_pitch_position",
    "current_duration",
    "detected_onset",
    "onset_confidence",
    "onset_age",
    "rms_level",
    "rms_growth_ratio",
    "spectral_flux",
    "harmonic_match_strength",
    "strongest_harmonic_match",
    "max_overtone_strength",
)

PITCH_OUTPUTS = (
    "active", "pitch", "harmonic_amplitude", "harmonic_offset_cents",
)

