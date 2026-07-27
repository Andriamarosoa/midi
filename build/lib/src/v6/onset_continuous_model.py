"""Small standalone causal onset detector for V6.3."""

from __future__ import annotations


def build_continuous_onset_model(
    window_size: int = 512,
    channels: int = 24,
    dropout: float = 0.10,
    pooling: str = "hybrid",
):
    import tensorflow as tf

    if window_size < 64:
        raise ValueError("window_size doit etre >= 64.")
    if channels < 4:
        raise ValueError("channels doit etre >= 4.")
    audio = tf.keras.Input(shape=(window_size, 1), name="audio")
    x = audio
    for block, (multiplier, kernel) in enumerate(((1, 15), (2, 9), (2, 7))):
        x = tf.keras.layers.Conv1D(
            channels * multiplier,
            kernel_size=kernel,
            strides=2,
            padding="causal",
            use_bias=False,
            name=f"causal_conv_{block + 1}",
        )(x)
        x = tf.keras.layers.LayerNormalization(name=f"norm_{block + 1}")(x)
        x = tf.keras.layers.Activation("swish", name=f"activation_{block + 1}")(x)
    if pooling == "hybrid":
        average = tf.keras.layers.GlobalAveragePooling1D(name="average_pool")(x)
        maximum = tf.keras.layers.GlobalMaxPooling1D(name="max_pool")(x)
        x = tf.keras.layers.Concatenate(name="hybrid_pool")([average, maximum])
    elif pooling == "temporal_bins":
        # Preserve when the transient occurred.  Eight ordered bins distinguish
        # a fresh attack in the newest samples from the same transient sliding
        # into the older half of the 512-sample causal context.
        temporal = tf.keras.layers.AveragePooling1D(
            pool_size=8, strides=8, padding="valid", name="temporal_bin_pool"
        )(x)
        temporal = tf.keras.layers.Flatten(name="temporal_bins")(temporal)
        maximum = tf.keras.layers.GlobalMaxPooling1D(name="max_pool")(x)
        x = tf.keras.layers.Concatenate(name="temporal_pool")([
            temporal, maximum
        ])
    else:
        raise ValueError(f"Pooling onset inconnu: {pooling}")
    x = tf.keras.layers.Dense(channels * 2, activation="swish", name="dense")(x)
    x = tf.keras.layers.Dropout(dropout, name="dropout")(x)
    onset = tf.keras.layers.Dense(1, activation="sigmoid", name="onset")(x)
    return tf.keras.Model(audio, onset, name="v6_3_continuous_onset")
