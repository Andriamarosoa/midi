from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ModelConfig:
    input_samples: int = 4096
    min_pitch: int = 40
    max_pitch: int = 88
    channels: int = 32
    tcn_blocks: int = 4
    dropout: float = 0.10

    @property
    def pitch_classes(self) -> int:
        return self.max_pitch - self.min_pitch + 1


def build_model(config: ModelConfig):
    import tensorflow as tf

    audio = tf.keras.Input(
        shape=(config.input_samples, 1),
        name="audio",
        dtype=tf.float32,
    )
    time_mask = tf.keras.Input(
        shape=(config.input_samples,),
        name="time_mask",
        dtype=tf.float32,
    )

    x = audio * tf.expand_dims(time_mask, axis=-1)

    x = tf.keras.layers.Conv1D(
        config.channels,
        kernel_size=9,
        strides=4,
        padding="causal",
        activation="swish",
        name="frontend_conv_1",
    )(x)
    x = tf.keras.layers.LayerNormalization(name="frontend_norm_1")(x)

    x = tf.keras.layers.Conv1D(
        config.channels * 2,
        kernel_size=7,
        strides=4,
        padding="causal",
        activation="swish",
        name="frontend_conv_2",
    )(x)
    x = tf.keras.layers.LayerNormalization(name="frontend_norm_2")(x)

    channels = config.channels * 2

    for block in range(config.tcn_blocks):
        residual = x
        dilation = 2 ** block

        y = tf.keras.layers.Conv1D(
            channels,
            kernel_size=3,
            dilation_rate=dilation,
            padding="causal",
            activation="swish",
            name=f"tcn_{block}_conv_1",
        )(x)
        y = tf.keras.layers.Dropout(
            config.dropout,
            name=f"tcn_{block}_dropout",
        )(y)
        y = tf.keras.layers.Conv1D(
            channels,
            kernel_size=3,
            dilation_rate=dilation,
            padding="causal",
            activation=None,
            name=f"tcn_{block}_conv_2",
        )(y)

        x = tf.keras.layers.Add(name=f"tcn_{block}_add")([residual, y])
        x = tf.keras.layers.LayerNormalization(
            name=f"tcn_{block}_norm"
        )(x)
        x = tf.keras.layers.Activation(
            "swish",
            name=f"tcn_{block}_activation",
        )(x)

    x = tf.keras.layers.GlobalAveragePooling1D(name="global_pool")(x)
    x = tf.keras.layers.Dense(128, activation="swish", name="shared_dense")(x)
    x = tf.keras.layers.Dropout(config.dropout, name="shared_dropout")(x)

    outputs = {
        "onset": tf.keras.layers.Dense(1, activation="sigmoid", name="onset")(x),
        "attack_phase": tf.keras.layers.Dense(
            1, activation="sigmoid", name="attack_phase"
        )(x),
        "active": tf.keras.layers.Dense(1, activation="sigmoid", name="active")(x),
        "release_phase": tf.keras.layers.Dense(
            1, activation="sigmoid", name="release_phase"
        )(x),
        "pitch": tf.keras.layers.Dense(
            config.pitch_classes,
            activation="softmax",
            name="pitch",
        )(x),
    }

    return tf.keras.Model(
        inputs={"audio": audio, "time_mask": time_mask},
        outputs=outputs,
        name="mono_stream_cnn_tcn_v1_fixed",
    )
