"""Causal multi-label frame/onset model with harmonic supervision."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Any

import tensorflow as tf

from src.v5.model import MaskedAveragePooling1D, ScaledTanh


@tf.keras.utils.register_keras_serializable(package="midi_polyphonic")
class ClassWeightedBinaryCrossentropy(tf.keras.losses.Loss):
    def __init__(
        self,
        positive_weights: list[float] | tuple[float, ...],
        reduction: str = tf.keras.losses.Reduction.AUTO,
        name: str = "class_weighted_binary_crossentropy",
    ) -> None:
        super().__init__(reduction=reduction, name=name)
        self.positive_weights = tuple(float(value) for value in positive_weights)
        if not self.positive_weights or min(self.positive_weights) <= 0.0:
            raise ValueError("Positive class weights are required.")

    def call(self, y_true, y_pred):
        prediction = tf.clip_by_value(
            y_pred,
            tf.cast(tf.keras.backend.epsilon(), y_pred.dtype),
            tf.cast(1.0 - tf.keras.backend.epsilon(), y_pred.dtype),
        )
        weights = tf.cast(self.positive_weights, prediction.dtype)
        loss = -(
            y_true * weights * tf.math.log(prediction)
            + (1.0 - y_true) * tf.math.log(1.0 - prediction)
        )
        return tf.reduce_mean(loss, axis=-1)

    def get_config(self):
        return {
            **super().get_config(),
            "positive_weights": list(self.positive_weights),
        }


@tf.keras.utils.register_keras_serializable(package="midi_polyphonic")
class PolyphonicMaskedHarmonicAmplitudeLoss(tf.keras.losses.Loss):
    def __init__(
        self,
        harmonic_count: int = 20,
        reduction: str = tf.keras.losses.Reduction.AUTO,
        name: str = "polyphonic_masked_harmonic_amplitude_loss",
    ) -> None:
        super().__init__(reduction=reduction, name=name)
        self.harmonic_count = int(harmonic_count)

    def call(self, y_true, y_pred):
        count = self.harmonic_count
        target = y_true[..., :count]
        valid = tf.cast(y_true[..., count:2 * count], y_pred.dtype)
        error = tf.abs(y_pred - target) * valid
        return tf.math.divide_no_nan(
            tf.reduce_sum(error, axis=(-2, -1)),
            tf.reduce_sum(valid, axis=(-2, -1)),
        )

    def get_config(self):
        return {**super().get_config(), "harmonic_count": self.harmonic_count}


@tf.keras.utils.register_keras_serializable(package="midi_polyphonic")
class PolyphonicHarmonicOffsetLoss(tf.keras.losses.Loss):
    def __init__(
        self,
        harmonic_count: int = 20,
        scale_cents: float = 35.0,
        reduction: str = tf.keras.losses.Reduction.AUTO,
        name: str = "polyphonic_harmonic_offset_loss",
    ) -> None:
        super().__init__(reduction=reduction, name=name)
        self.harmonic_count = int(harmonic_count)
        self.scale_cents = float(scale_cents)

    def call(self, y_true, y_pred):
        count = self.harmonic_count
        target = y_true[..., :count]
        valid = tf.cast(y_true[..., count:2 * count], y_pred.dtype)
        amplitude = tf.cast(y_true[..., 2 * count:3 * count], y_pred.dtype)
        weights = valid * tf.maximum(amplitude, 0.0)
        error = tf.abs(y_pred - target) / self.scale_cents
        return tf.math.divide_no_nan(
            tf.reduce_sum(error * weights, axis=(-2, -1)),
            tf.reduce_sum(weights, axis=(-2, -1)),
        )

    def get_config(self):
        return {
            **super().get_config(),
            "harmonic_count": self.harmonic_count,
            "scale_cents": self.scale_cents,
        }


@tf.keras.utils.register_keras_serializable(package="midi_polyphonic")
class MicroF1(tf.keras.metrics.Metric):
    def __init__(self, threshold: float = 0.5, name: str = "micro_f1", **kwargs):
        super().__init__(name=name, **kwargs)
        self.threshold = float(threshold)
        self.true_positive = self.add_weight(name="tp", initializer="zeros")
        self.false_positive = self.add_weight(name="fp", initializer="zeros")
        self.false_negative = self.add_weight(name="fn", initializer="zeros")

    def update_state(self, y_true, y_pred, sample_weight=None):
        truth = tf.cast(y_true > 0.5, self.dtype)
        predicted = tf.cast(y_pred >= self.threshold, self.dtype)
        tp = tf.reduce_sum(truth * predicted)
        fp = tf.reduce_sum((1.0 - truth) * predicted)
        fn = tf.reduce_sum(truth * (1.0 - predicted))
        if sample_weight is not None:
            weight = tf.cast(tf.reduce_mean(sample_weight), self.dtype)
            tp, fp, fn = tp * weight, fp * weight, fn * weight
        self.true_positive.assign_add(tp)
        self.false_positive.assign_add(fp)
        self.false_negative.assign_add(fn)

    def result(self):
        return tf.math.divide_no_nan(
            2.0 * self.true_positive,
            2.0 * self.true_positive + self.false_positive + self.false_negative,
        )

    def reset_state(self):
        for variable in self.variables:
            variable.assign(0.0)

    def get_config(self):
        return {**super().get_config(), "threshold": self.threshold}


def build_polyphonic_model(
    pitch_classes: int = 37,
    input_samples: int = 4096,
    channels: int = 32,
    tcn_blocks: int = 4,
    dropout: float = 0.10,
    dense_units: int = 128,
    harmonic_count: int = 20,
    harmonic_offset_scale_cents: float = 35.0,
) -> tf.keras.Model:
    if not 1 <= pitch_classes <= 64:
        raise ValueError("pitch_classes must be in 1..64")
    audio = tf.keras.Input((input_samples, 1), dtype=tf.float32, name="audio")
    time_mask = tf.keras.Input((input_samples,), dtype=tf.float32, name="time_mask")
    mask = tf.keras.layers.Reshape(
        (input_samples, 1), name="expand_time_mask"
    )(time_mask)
    x = tf.keras.layers.Multiply(name="apply_time_mask")([audio, mask])
    x = tf.keras.layers.Conv1D(
        channels, 9, strides=4, padding="causal", activation="swish",
        name="frontend_conv_1",
    )(x)
    x = tf.keras.layers.LayerNormalization(name="frontend_norm_1")(x)
    pooled_mask = tf.keras.layers.MaxPooling1D(
        4, strides=4, padding="valid", name="mask_downsample_1"
    )(mask)
    tcn_channels = channels * 2
    x = tf.keras.layers.Conv1D(
        tcn_channels, 7, strides=4, padding="causal", activation="swish",
        name="frontend_conv_2",
    )(x)
    x = tf.keras.layers.LayerNormalization(name="frontend_norm_2")(x)
    pooled_mask = tf.keras.layers.MaxPooling1D(
        4, strides=4, padding="valid", name="mask_downsample_2"
    )(pooled_mask)

    for block_index in range(tcn_blocks):
        residual = x
        dilation = 2 ** block_index
        y = tf.keras.layers.Conv1D(
            tcn_channels, 3, dilation_rate=dilation, padding="causal",
            activation="swish", name=f"tcn_{block_index}_conv_1",
        )(x)
        y = tf.keras.layers.Dropout(
            dropout, name=f"tcn_{block_index}_dropout"
        )(y)
        y = tf.keras.layers.Conv1D(
            tcn_channels, 3, dilation_rate=dilation, padding="causal",
            name=f"tcn_{block_index}_conv_2",
        )(y)
        x = tf.keras.layers.Add(name=f"tcn_{block_index}_add")([residual, y])
        x = tf.keras.layers.LayerNormalization(
            name=f"tcn_{block_index}_norm"
        )(x)
        x = tf.keras.layers.Activation(
            "swish", name=f"tcn_{block_index}_activation"
        )(x)

    frontend_steps = math.ceil(math.ceil(input_samples / 4) / 4)
    last_step = tf.keras.layers.Cropping1D(
        cropping=(0, frontend_steps - 1), name="last_causal_step"
    )(x)
    last_state = tf.keras.layers.Flatten(name="last_causal_state")(last_step)
    average_state = MaskedAveragePooling1D(name="masked_average_state")(
        [x, pooled_mask]
    )
    pooled = tf.keras.layers.Concatenate(name="hybrid_pool")(
        [last_state, average_state]
    )
    pooled = tf.keras.layers.Dense(
        dense_units, activation="swish", name="pitch_dense"
    )(pooled)
    pooled = tf.keras.layers.Dropout(dropout, name="pitch_dropout")(pooled)

    frame = tf.keras.layers.Dense(
        pitch_classes, activation="sigmoid", name="frame"
    )(pooled)

    onset_window = min(512, input_samples)
    onset_audio = tf.keras.layers.Cropping1D(
        cropping=(input_samples - onset_window, 0),
        name="onset_last_512_samples",
    )(audio)
    onset_features = tf.keras.layers.Conv1D(
        max(8, channels // 2), 9, strides=4, padding="causal",
        activation="swish", name="onset_conv_1",
    )(onset_audio)
    onset_features = tf.keras.layers.LayerNormalization(
        name="onset_norm_1"
    )(onset_features)
    onset_features = tf.keras.layers.Conv1D(
        max(8, channels // 2) * 2, 7, strides=4, padding="causal",
        activation="swish", name="onset_conv_2",
    )(onset_features)
    onset_features = tf.keras.layers.GlobalAveragePooling1D(
        name="onset_pool"
    )(onset_features)
    onset_features = tf.keras.layers.Dense(
        min(32, dense_units), activation="swish", name="onset_dense"
    )(onset_features)
    onset_context = tf.keras.layers.Concatenate(
        name="onset_with_pitch_context"
    )([onset_features, pooled])
    onset = tf.keras.layers.Dense(
        pitch_classes, activation="sigmoid", name="onset"
    )(onset_context)

    harmonic_amplitude_flat = tf.keras.layers.Dense(
        pitch_classes * harmonic_count,
        activation="sigmoid",
        name="harmonic_amplitude_flat",
    )(pooled)
    harmonic_amplitude = tf.keras.layers.Reshape(
        (pitch_classes, harmonic_count), name="harmonic_amplitude"
    )(harmonic_amplitude_flat)
    harmonic_offset_flat = tf.keras.layers.Dense(
        pitch_classes * harmonic_count,
        name="harmonic_offset_logits",
    )(pooled)
    harmonic_offset_flat = ScaledTanh(
        harmonic_offset_scale_cents, name="harmonic_offset_scaled"
    )(harmonic_offset_flat)
    harmonic_offset = tf.keras.layers.Reshape(
        (pitch_classes, harmonic_count), name="harmonic_offset_cents"
    )(harmonic_offset_flat)

    return tf.keras.Model(
        inputs={"audio": audio, "time_mask": time_mask},
        outputs={
            "frame": frame,
            "onset": onset,
            "harmonic_amplitude": harmonic_amplitude,
            "harmonic_offset_cents": harmonic_offset,
        },
        name="causal_polyphonic_guitar_v2",
    )


def transfer_compatible_weights(
    model: tf.keras.Model,
    source_path: str | Path,
) -> dict[str, Any]:
    source = tf.keras.models.load_model(source_path, compile=False)
    transferred: list[str] = []
    skipped: list[str] = []
    for layer in model.layers:
        weights = layer.get_weights()
        if not weights:
            continue
        try:
            source_layer = source.get_layer(layer.name)
        except ValueError:
            skipped.append(layer.name)
            continue
        source_weights = source_layer.get_weights()
        if len(weights) != len(source_weights) or any(
            left.shape != right.shape
            for left, right in zip(weights, source_weights)
        ):
            skipped.append(layer.name)
            continue
        layer.set_weights(source_weights)
        transferred.append(layer.name)
    return {"source": str(source_path), "transferred": transferred, "skipped": skipped}

