from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.v5.model import (  # noqa: F401 - register saved layers
    MaskedAveragePooling1D,
    ScaledTanh,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--normalization", type=Path, required=True)
    parser.add_argument("--active-threshold", type=Path, required=True)
    parser.add_argument("--min-pitch", type=int, default=40)
    parser.add_argument("--index", type=int, default=0)
    args = parser.parse_args()

    import tensorflow as tf

    model = tf.keras.models.load_model(args.model, compile=False)
    gain = float(json.loads(args.normalization.read_text(encoding="utf-8"))["gain"])
    threshold = float(
        json.loads(args.active_threshold.read_text(encoding="utf-8"))["threshold"]
    )
    with np.load(args.npz) as data:
        waveform = data["audio"][args.index].astype(np.float32, copy=True)
        visible = int(data["visible_window"][args.index])

    visible = int(np.clip(visible, 1, len(waveform)))
    waveform[:-visible] = 0.0
    waveform *= gain
    np.clip(waveform, -1.0, 1.0, out=waveform)
    mask = np.zeros((1, len(waveform)), dtype=np.float32)
    mask[:, -visible:] = 1.0
    raw = model.predict(
        {"audio": waveform[None, :, None], "time_mask": mask}, verbose=0
    )
    if not isinstance(raw, dict):
        raise ValueError("Le modele V6 doit produire un dictionnaire de sorties.")

    active_probability = float(np.asarray(raw["active"]).reshape(-1)[0])
    probabilities = np.asarray(raw["pitch"])[0]
    pitch_class = int(np.argmax(probabilities))
    active = active_probability >= threshold
    print(f"active_probability={active_probability:.6f}")
    print(f"active_threshold={threshold:.6f}")
    print(f"active={int(active)}")
    if active:
        print(f"predicted_midi={pitch_class + args.min_pitch}")
        print(f"pitch_confidence={float(probabilities[pitch_class]):.6f}")
    else:
        print("predicted_midi=none")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

