from __future__ import annotations

import tensorflow as tf


def _masked_mean(values, weights):
    weights = tf.cast(weights, values.dtype)
    numerator = tf.reduce_sum(values * weights, axis=-1)
    denominator = tf.reduce_sum(weights, axis=-1)
    return tf.math.divide_no_nan(numerator, denominator)


@tf.keras.utils.register_keras_serializable(package="midi_v5")
class MaskedHarmonicAmplitudeLoss(tf.keras.losses.Loss):
    """L1 amplitude loss over measured partials only.

    ``y_true`` packs ``[amplitude, valid_mask]`` while the model emits only
    the amplitude vector. Keeping the validity mask in the target prevents an
    unknown zero from being treated as an absent harmonic.
    """

    def __init__(
        self,
        harmonic_count: int = 20,
        reduction: str = tf.keras.losses.Reduction.AUTO,
        name: str = "masked_harmonic_amplitude_loss",
    ) -> None:
        super().__init__(reduction=reduction, name=name)
        self.harmonic_count = int(harmonic_count)
        if self.harmonic_count < 1:
            raise ValueError("harmonic_count doit etre positif.")

    def call(self, y_true, y_pred):
        target = y_true[..., : self.harmonic_count]
        valid = y_true[..., self.harmonic_count : 2 * self.harmonic_count]
        return _masked_mean(tf.abs(y_pred - target), valid)

    def get_config(self):
        return {**super().get_config(), "harmonic_count": self.harmonic_count}


@tf.keras.utils.register_keras_serializable(package="midi_v5")
class AmplitudeWeightedHarmonicOffsetLoss(tf.keras.losses.Loss):
    """Robust offset loss weighted continuously by partial amplitude.

    ``y_true`` packs ``[offset_cents, valid_mask, amplitude]``. Weighting by
    amplitude avoids imposing a manual presence threshold and naturally
    suppresses frequency estimates dominated by weak spectral peaks.
    """

    def __init__(
        self,
        harmonic_count: int = 20,
        scale_cents: float = 35.0,
        reduction: str = tf.keras.losses.Reduction.AUTO,
        name: str = "amplitude_weighted_harmonic_offset_loss",
    ) -> None:
        super().__init__(reduction=reduction, name=name)
        self.harmonic_count = int(harmonic_count)
        self.scale_cents = float(scale_cents)
        if self.harmonic_count < 1:
            raise ValueError("harmonic_count doit etre positif.")
        if self.scale_cents <= 0.0:
            raise ValueError("scale_cents doit etre strictement positif.")

    def call(self, y_true, y_pred):
        count = self.harmonic_count
        target = y_true[..., :count]
        valid = y_true[..., count : 2 * count]
        amplitude = y_true[..., 2 * count : 3 * count]
        weights = valid * tf.maximum(amplitude, 0.0)
        normalized_error = tf.abs(y_pred - target) / self.scale_cents
        return _masked_mean(normalized_error, weights)

    def get_config(self):
        return {
            **super().get_config(),
            "harmonic_count": self.harmonic_count,
            "scale_cents": self.scale_cents,
        }
