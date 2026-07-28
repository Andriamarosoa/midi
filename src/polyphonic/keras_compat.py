"""Compatibility helpers shared by Keras 2 and Keras 3 runtimes."""

from __future__ import annotations

import inspect
import json
import re
import tempfile
import zipfile
from pathlib import Path
from typing import Any


def _legacy_polyphonic_spec(config: dict[str, Any]) -> dict[str, Any]:
    """Recover the current polyphonic architecture from a Keras 2 archive."""
    model_config = config.get("config", {})
    layers = {
        layer.get("name"): layer
        for layer in model_config.get("layers", [])
        if isinstance(layer, dict) and layer.get("name")
    }

    def layer_config(name: str) -> dict[str, Any]:
        try:
            return layers[name]["config"]
        except (KeyError, TypeError) as error:
            raise ValueError(
                f"Legacy checkpoint is missing required layer {name!r}."
            ) from error

    audio_shape = (
        layer_config("audio").get("batch_input_shape")
        or layer_config("audio").get("batch_shape")
    )
    if not audio_shape or len(audio_shape) != 3:
        raise ValueError("Legacy checkpoint has no supported audio input shape.")
    tcn_indices = {
        int(match.group(1))
        for name in layers
        if (match := re.fullmatch(r"tcn_(\d+)_conv_1", name))
    }
    if tcn_indices != set(range(len(tcn_indices))):
        raise ValueError("Legacy checkpoint has a non-contiguous TCN layout.")
    return {
        "pitch_classes": int(layer_config("frame")["units"]),
        "input_samples": int(audio_shape[1]),
        "channels": int(layer_config("frontend_conv_1")["filters"]),
        "tcn_blocks": len(tcn_indices),
        "dropout": float(layer_config("pitch_dropout")["rate"]),
        "dense_units": int(layer_config("pitch_dense")["units"]),
        "harmonic_count": int(
            layer_config("harmonic_amplitude")["target_shape"][-1]
        ),
        "harmonic_offset_scale_cents": float(
            layer_config("harmonic_offset_scaled")["scale"]
        ),
    }


def load_polyphonic_checkpoint(path: str | Path) -> Any:
    """Load Keras 2 or Keras 3 polyphonic checkpoints without recompiling.

    Keras 2 ``.keras`` archives identify ``Functional`` with the removed
    ``keras.src.engine.functional`` module. For those archives, rebuild the
    known causal architecture and load only ``model.weights.h5``. Native
    Keras 3 archives continue through the standard loader.
    """
    import tensorflow as tf

    checkpoint = Path(path)
    if not zipfile.is_zipfile(checkpoint):
        return tf.keras.models.load_model(checkpoint, compile=False)
    with zipfile.ZipFile(checkpoint) as archive:
        try:
            config = json.loads(archive.read("config.json"))
        except KeyError:
            return tf.keras.models.load_model(checkpoint, compile=False)
        module = str(config.get("module", ""))
        if module != "keras.src.engine.functional":
            return tf.keras.models.load_model(checkpoint, compile=False)
        if "model.weights.h5" not in archive.namelist():
            raise ValueError(
                f"Legacy checkpoint has no model.weights.h5: {checkpoint}"
            )
        spec = _legacy_polyphonic_spec(config)
        with tempfile.TemporaryDirectory(
            prefix="guitar-midi-keras2-weights-"
        ) as temporary:
            weights_path = Path(temporary) / "model.weights.h5"
            weights_path.write_bytes(archive.read("model.weights.h5"))
            from src.polyphonic.model import build_polyphonic_model

            model = build_polyphonic_model(**spec)
            model.load_weights(weights_path)
    return model


def predict_compat(
    model: Any,
    inputs: Any,
    *,
    verbose: int = 0,
    workers: int = 1,
) -> Any:
    """Call ``predict`` without legacy queue options on Keras 3."""
    kwargs: dict[str, object] = {"verbose": int(verbose)}
    if "workers" in inspect.signature(model.predict).parameters:
        kwargs["workers"] = int(workers)
    return model.predict(inputs, **kwargs)
