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
    compressed_bass_branch = "bass_input_compress" in layers
    frame_layer = "frame_main_logits" if compressed_bass_branch else "frame"
    spec = {
        "pitch_classes": int(layer_config(frame_layer)["units"]),
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
        "harmonic_presence_head": "harmonic_presence" in layers,
    }
    if compressed_bass_branch:
        spec.update(
            {
                "normal_window_samples": int(audio_shape[1]) // 2,
                "compressed_bass_branch": True,
                "bass_channels": int(layer_config("bass_conv_1")["filters"]),
                "bass_dense_units": int(layer_config("bass_dense")["units"]),
                "bass_pitch_classes": int(
                    layer_config("frame_bass_logits")["units"]
                ),
            }
        )
    return spec


def _normalize_h5_paths(source: Path, destination: Path) -> bool:
    """Rewrite Windows-created Keras 2 HDF5 paths for Linux/Keras 3."""
    import h5py

    changed = False
    with h5py.File(source, "r") as input_file, h5py.File(
        destination, "w"
    ) as output_file:
        for key, value in input_file.attrs.items():
            output_file.attrs[key] = value

        def copy_item(name: str, item: Any) -> None:
            nonlocal changed
            normalized = name.replace("\\", "/")
            changed = changed or normalized != name
            if isinstance(item, h5py.Group):
                target = output_file.require_group(normalized)
            elif isinstance(item, h5py.Dataset):
                target = output_file.create_dataset(
                    normalized, data=item[()]
                )
            else:
                return
            for key, value in item.attrs.items():
                target.attrs[key] = value

        input_file.visititems(copy_item)
    return changed


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
            try:
                model.load_weights(weights_path)
            except ValueError:
                normalized_path = Path(temporary) / "normalized.weights.h5"
                if not _normalize_h5_paths(
                    weights_path, normalized_path
                ):
                    raise
                # A failed Keras load can partially assign variables. Rebuild
                # before retrying against the normalized HDF5 hierarchy.
                model = build_polyphonic_model(**spec)
                model.load_weights(normalized_path)
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
