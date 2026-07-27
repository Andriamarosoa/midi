from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from .model import (  # noqa: F401 - register saved layers
    MaskedAveragePooling1D,
    ScaledTanh,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--normalization", type=Path, required=True)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()

    import tensorflow as tf

    model = tf.keras.models.load_model(args.model, compile=False)
    gain = float(json.loads(args.normalization.read_text(encoding="utf-8"))["gain"])

    with np.load(args.npz) as data:
        waveform = data["audio"][args.index].astype(np.float32, copy=True)
        visible = int(data["visible_window"][args.index])

    waveform[:-visible] = 0.0
    waveform *= gain
    np.clip(waveform, -1.0, 1.0, out=waveform)

    audio = waveform[None, :, None]
    mask = np.zeros((1, len(waveform)), dtype=np.float32)
    mask[:, -visible:] = 1.0

    raw_predictions = model.predict(
        {"audio": audio, "time_mask": mask},
        verbose=0,
    )
    if isinstance(raw_predictions, dict):
        probabilities = np.asarray(raw_predictions["pitch"])[0]
    else:
        probabilities = np.asarray(raw_predictions)[0]

    predicted_class = int(np.argmax(probabilities))
    predicted_midi = predicted_class + args.min_pitch

    print(f"predicted_midi={predicted_midi}")
    print(f"confidence={float(probabilities[predicted_class]):.6f}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
