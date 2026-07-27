from __future__ import annotations

from typing import Any
import math


def _get_config_value(config: Any, name: str, default: Any) -> Any:
    """Read a model option from a dataclass, namespace or dictionary."""
    if isinstance(config, dict):
        return config.get(name, default)
    return getattr(config, name, default)


def build_pitch_model(config: Any, pitch_classes: int):
    """Build the serializable causal CNN + TCN pitch model.

    This implementation intentionally avoids Python Lambda layers so that
    models saved as ``.keras`` can be loaded with the default safe mode.

    Expected optional config fields:
        input_samples: int = 4096
        channels: int = 32
        tcn_blocks: int = 4
        dropout: float = 0.10
        dense_units: int = 128
        pooling: str = "hybrid"

    Supported pooling modes:
        "hybrid"  -> last causal state + global average state
        "last"    -> last causal state only
        "average" -> global average state only
    """
    if pitch_classes <= 1:
        raise ValueError("pitch_classes must be greater than 1")

    import tensorflow as tf

    input_samples = int(
        _get_config_value(config, "input_samples", 4096)
    )
    frontend_channels = int(
        _get_config_value(config, "channels", 32)
    )
    tcn_blocks = int(
        _get_config_value(config, "tcn_blocks", 4)
    )
    dropout = float(
        _get_config_value(config, "dropout", 0.10)
    )
    dense_units = int(
        _get_config_value(config, "dense_units", 128)
    )
    pooling = str(
        _get_config_value(config, "pooling", "hybrid")
    ).strip().lower()

    if input_samples <= 0:
        raise ValueError("input_samples must be > 0")
    if frontend_channels <= 0:
        raise ValueError("channels must be > 0")
    if tcn_blocks <= 0:
        raise ValueError("tcn_blocks must be > 0")
    if not 0.0 <= dropout < 1.0:
        raise ValueError("dropout must be in [0, 1)")
    if dense_units <= 0:
        raise ValueError("dense_units must be > 0")
    if pooling not in {"hybrid", "last", "average"}:
        raise ValueError(
            "pooling must be one of: hybrid, last, average"
        )

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

    # Avoid TFOpLambda/Python Lambda for mask expansion.
    expanded_mask = tf.keras.layers.Reshape(
        target_shape=(input_samples, 1),
        name="expand_time_mask",
    )(time_mask)

    x = tf.keras.layers.Multiply(
        name="apply_time_mask",
    )([audio, expanded_mask])

    # Causal waveform frontend.
    x = tf.keras.layers.Conv1D(
        filters=frontend_channels,
        kernel_size=9,
        strides=4,
        padding="causal",
        activation="swish",
        name="frontend_conv_1",
    )(x)

    x = tf.keras.layers.LayerNormalization(
        name="frontend_norm_1",
    )(x)

    tcn_channels = frontend_channels * 2

    x = tf.keras.layers.Conv1D(
        filters=tcn_channels,
        kernel_size=7,
        strides=4,
        padding="causal",
        activation="swish",
        name="frontend_conv_2",
    )(x)

    x = tf.keras.layers.LayerNormalization(
        name="frontend_norm_2",
    )(x)

    # Residual causal TCN.
    for block_index in range(tcn_blocks):
        dilation_rate = 2 ** block_index
        residual = x

        y = tf.keras.layers.Conv1D(
            filters=tcn_channels,
            kernel_size=3,
            dilation_rate=dilation_rate,
            padding="causal",
            activation="swish",
            name=f"tcn_{block_index}_conv_1",
        )(x)

        y = tf.keras.layers.Dropout(
            rate=dropout,
            name=f"tcn_{block_index}_dropout",
        )(y)

        y = tf.keras.layers.Conv1D(
            filters=tcn_channels,
            kernel_size=3,
            dilation_rate=dilation_rate,
            padding="causal",
            activation=None,
            name=f"tcn_{block_index}_conv_2",
        )(y)

        x = tf.keras.layers.Add(
            name=f"tcn_{block_index}_add",
        )([residual, y])

        x = tf.keras.layers.LayerNormalization(
            name=f"tcn_{block_index}_norm",
        )(x)

        x = tf.keras.layers.Activation(
            activation="swish",
            name=f"tcn_{block_index}_activation",
        )(x)

    # Cropping1D is fully serializable and replaces:
    # Lambda(lambda value: value[:, -1, :])
    # Each frontend convolution uses stride 4 with causal/same-length rules.
    # Keras therefore produces ceil(input_length / stride) at each stage.
    frontend_steps = math.ceil(math.ceil(input_samples / 4) / 4)

    last_sequence_step = tf.keras.layers.Cropping1D(
        cropping=(0, frontend_steps - 1),
        name="last_causal_step",
    )(x)

    last_state = tf.keras.layers.Flatten(
        name="last_causal_state",
    )(last_sequence_step)

    average_state = tf.keras.layers.GlobalAveragePooling1D(
        name="global_average_state",
    )(x)

    if pooling == "hybrid":
        pooled = tf.keras.layers.Concatenate(
            name="hybrid_pool",
        )([last_state, average_state])
    elif pooling == "last":
        pooled = last_state
    else:
        pooled = average_state

    pooled = tf.keras.layers.Dense(
        units=dense_units,
        activation="swish",
        name="pitch_dense",
    )(pooled)

    pooled = tf.keras.layers.Dropout(
        rate=dropout,
        name="pitch_dropout",
    )(pooled)

    pitch = tf.keras.layers.Dense(
        units=int(pitch_classes),
        activation="softmax",
        name="pitch",
    )(pooled)

    return tf.keras.Model(
        inputs={
            "audio": audio,
            "time_mask": time_mask,
        },
        outputs=pitch,
        name="mono_pitch_v3",
    )