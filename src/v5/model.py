from __future__ import annotations

import math
from typing import Any

import tensorflow as tf


@tf.keras.utils.register_keras_serializable(package="midi_v5")
class MaskedAveragePooling1D(tf.keras.layers.Layer):
    """Average temporal features over visible causal steps only."""

    def call(self, inputs):
        features, mask = inputs
        mask = tf.cast(mask, features.dtype)
        weighted_sum = tf.reduce_sum(features * mask, axis=1)
        denominator = tf.maximum(
            tf.reduce_sum(mask, axis=1),
            tf.cast(tf.keras.backend.epsilon(), features.dtype),
        )
        return weighted_sum / denominator

    def compute_output_shape(self, input_shape):
        return input_shape[0][0], input_shape[0][2]


@tf.keras.utils.register_keras_serializable(package="midi_v5")
class ScaledTanh(tf.keras.layers.Layer):
    """Bound a regression output while preserving physical units."""

    def __init__(self, scale: float, **kwargs):
        super().__init__(**kwargs)
        self.scale = float(scale)
        if self.scale <= 0.0:
            raise ValueError("scale doit etre strictement positif.")

    def call(self, inputs):
        return tf.math.tanh(inputs) * tf.cast(self.scale, inputs.dtype)

    def get_config(self):
        return {**super().get_config(), "scale": self.scale}


def build_pitch_model(config: Any, pitch_classes: int, input_samples: int = 4096):
    if pitch_classes <= 1:
        raise ValueError("pitch_classes doit être > 1.")

    channels = int(config.channels)
    tcn_blocks = int(config.tcn_blocks)
    dropout = float(config.dropout)
    dense_units = int(config.dense_units)
    pooling = str(config.pooling).lower()
    harmonic_auxiliary = bool(getattr(config, "harmonic_auxiliary", False))
    active_auxiliary = bool(getattr(config, "active_auxiliary", False))
    onset_auxiliary = bool(getattr(config, "onset_auxiliary", False))
    harmonic_count = int(getattr(config, "harmonic_count", 20))
    harmonic_offset_scale_cents = float(
        getattr(config, "harmonic_offset_scale_cents", 35.0)
    )

    if harmonic_auxiliary and harmonic_count < 1:
        raise ValueError("harmonic_count doit etre positif.")
    if harmonic_auxiliary and harmonic_offset_scale_cents <= 0.0:
        raise ValueError("harmonic_offset_scale_cents doit etre positif.")

    audio = tf.keras.Input(
        shape=(input_samples, 1),
        dtype=tf.float32,
        name="audio",
    )
    time_mask = tf.keras.Input(
        shape=(input_samples,),
        dtype=tf.float32,
        name="time_mask",
    )

    mask = tf.keras.layers.Reshape(
        (input_samples, 1),
        name="expand_time_mask",
    )(time_mask)

    x = tf.keras.layers.Multiply(
        name="apply_time_mask",
    )([audio, mask])

    x = tf.keras.layers.Conv1D(
        channels,
        kernel_size=9,
        strides=4,
        padding="causal",
        activation="swish",
        name="frontend_conv_1",
    )(x)
    x = tf.keras.layers.LayerNormalization(
        name="frontend_norm_1",
    )(x)

    pooled_mask = tf.keras.layers.MaxPooling1D(
        pool_size=4, strides=4, padding="valid", name="mask_downsample_1",
    )(mask)

    tcn_channels = channels * 2

    x = tf.keras.layers.Conv1D(
        tcn_channels,
        kernel_size=7,
        strides=4,
        padding="causal",
        activation="swish",
        name="frontend_conv_2",
    )(x)
    x = tf.keras.layers.LayerNormalization(
        name="frontend_norm_2",
    )(x)

    pooled_mask = tf.keras.layers.MaxPooling1D(
        pool_size=4, strides=4, padding="valid", name="mask_downsample_2",
    )(pooled_mask)

    for block_index in range(tcn_blocks):
        residual = x
        dilation = 2 ** block_index

        y = tf.keras.layers.Conv1D(
            tcn_channels,
            kernel_size=3,
            dilation_rate=dilation,
            padding="causal",
            activation="swish",
            name=f"tcn_{block_index}_conv_1",
        )(x)
        y = tf.keras.layers.Dropout(
            dropout,
            name=f"tcn_{block_index}_dropout",
        )(y)
        y = tf.keras.layers.Conv1D(
            tcn_channels,
            kernel_size=3,
            dilation_rate=dilation,
            padding="causal",
            name=f"tcn_{block_index}_conv_2",
        )(y)

        x = tf.keras.layers.Add(
            name=f"tcn_{block_index}_add",
        )([residual, y])
        x = tf.keras.layers.LayerNormalization(
            name=f"tcn_{block_index}_norm",
        )(x)
        x = tf.keras.layers.Activation(
            "swish",
            name=f"tcn_{block_index}_activation",
        )(x)

    frontend_steps = math.ceil(math.ceil(input_samples / 4) / 4)

    last_step = tf.keras.layers.Cropping1D(
        cropping=(0, frontend_steps - 1),
        name="last_causal_step",
    )(x)
    last_state = tf.keras.layers.Flatten(
        name="last_causal_state",
    )(last_step)
    average_state = MaskedAveragePooling1D(
        name="masked_average_state",
    )([x, pooled_mask])

    if pooling == "hybrid":
        pooled = tf.keras.layers.Concatenate(
            name="hybrid_pool",
        )([last_state, average_state])
    elif pooling == "last":
        pooled = last_state
    elif pooling == "average":
        pooled = average_state
    else:
        raise ValueError("pooling doit être hybrid, last ou average.")

    pooled = tf.keras.layers.Dense(
        dense_units,
        activation="swish",
        name="pitch_dense",
    )(pooled)
    pooled = tf.keras.layers.Dropout(
        dropout,
        name="pitch_dropout",
    )(pooled)

    pitch = tf.keras.layers.Dense(
        pitch_classes,
        activation="softmax",
        name="pitch",
    )(pooled)

    outputs: Any = pitch
    model_name = "mono_pitch_v5"
    multi_outputs: dict[str, Any] = {"pitch": pitch}
    if harmonic_auxiliary:
        harmonic_amplitude = tf.keras.layers.Dense(
            harmonic_count,
            activation="sigmoid",
            name="harmonic_amplitude",
        )(pooled)
        harmonic_offset_logits = tf.keras.layers.Dense(
            harmonic_count,
            name="harmonic_offset_logits",
        )(pooled)
        harmonic_offset_cents = ScaledTanh(
            harmonic_offset_scale_cents,
            name="harmonic_offset_cents",
        )(harmonic_offset_logits)
        multi_outputs["harmonic_amplitude"] = harmonic_amplitude
        multi_outputs["harmonic_offset_cents"] = harmonic_offset_cents
        model_name = "mono_pitch_harmonics_v5_3"

    if active_auxiliary:
        multi_outputs["active"] = tf.keras.layers.Dense(
            1,
            activation="sigmoid",
            name="active",
        )(pooled)
        model_name = "mono_pitch_harmonics_active_v6_0"

    if onset_auxiliary:
        onset_window = min(512, int(input_samples))
        onset_channels = max(8, channels // 2)
        onset_audio = tf.keras.layers.Cropping1D(
            cropping=(int(input_samples) - onset_window, 0),
            name="onset_last_512_samples",
        )(audio)
        onset_features = tf.keras.layers.Conv1D(
            onset_channels,
            kernel_size=9,
            strides=4,
            padding="causal",
            activation="swish",
            name="onset_conv_1",
        )(onset_audio)
        onset_features = tf.keras.layers.LayerNormalization(
            name="onset_norm_1",
        )(onset_features)
        onset_features = tf.keras.layers.Conv1D(
            onset_channels * 2,
            kernel_size=7,
            strides=4,
            padding="causal",
            activation="swish",
            name="onset_conv_2",
        )(onset_features)
        onset_features = tf.keras.layers.GlobalAveragePooling1D(
            name="onset_pool",
        )(onset_features)
        onset_features = tf.keras.layers.Dense(
            min(32, dense_units),
            activation="swish",
            name="onset_dense",
        )(onset_features)
        multi_outputs["onset"] = tf.keras.layers.Dense(
            1,
            activation="sigmoid",
            name="onset",
        )(onset_features)
        model_name = "mono_pitch_harmonics_active_onset_v6_2"

    if harmonic_auxiliary or active_auxiliary or onset_auxiliary:
        outputs = multi_outputs

    return tf.keras.Model(
        inputs={"audio": audio, "time_mask": time_mask},
        outputs=outputs,
        name=model_name,
    )
