"""Verified TensorFlow Lite runtime for the portable product bundle."""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


@dataclass(frozen=True)
class PitchPrediction:
    active_probability: float
    pitch_probability: np.ndarray
    harmonic_amplitude: np.ndarray
    harmonic_offset_cents: np.ndarray
    inference_ms: float


class ProductBundle:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.metadata = json.loads(
            (self.root / "metadata.json").read_text(encoding="utf-8")
        )
        artifacts = self.metadata["artifacts"]
        self.pitch_path = self.root / artifacts["pitch_tflite"]
        self.gate_path = self.root / artifacts["transition_gate_tflite"]
        expected_hashes = {
            self.pitch_path: artifacts["pitch_sha256"],
            self.gate_path: artifacts["transition_gate_sha256"],
        }
        for path, expected in expected_hashes.items():
            if not path.is_file():
                raise FileNotFoundError(path)
            actual = file_sha256(path)
            if actual != expected:
                raise ValueError(f"SHA256 invalide pour {path.name}")


class TFLitePitchModel:
    def __init__(self, bundle: ProductBundle, threads: int | None = None) -> None:
        import tensorflow as tf

        threads = int(
            bundle.metadata.get("recommended_tflite_threads", 1)
            if threads is None else threads
        )
        if threads < 1:
            raise ValueError("threads doit etre positif.")
        self.interpreter = tf.lite.Interpreter(
            model_path=str(bundle.pitch_path), num_threads=threads
        )
        self.interpreter.allocate_tensors()
        self.runner = self.interpreter.get_signature_runner("serving_default")
        self.gain = float(bundle.metadata["normalization_gain"])
        self.audio = np.zeros((1, 4096, 1), dtype=np.float32)
        self.mask = np.zeros((1, 4096), dtype=np.float32)

    def infer(self, waveform: np.ndarray, visible_window: int) -> PitchPrediction:
        values = np.asarray(waveform, dtype=np.float32).reshape(-1)
        if values.shape != (4096,):
            raise ValueError("Une fenetre mono de 4096 echantillons est requise.")
        visible = int(np.clip(visible_window, 1, 4096))
        self.audio.fill(0.0)
        self.mask.fill(0.0)
        self.audio[0, -visible:, 0] = values[-visible:] * self.gain
        np.clip(self.audio, -1.0, 1.0, out=self.audio)
        self.mask[0, -visible:] = 1.0
        started = time.perf_counter()
        result = self.runner(audio=self.audio, time_mask=self.mask)
        elapsed_ms = (time.perf_counter() - started) * 1000.0
        return PitchPrediction(
            active_probability=float(np.asarray(result["active"]).reshape(-1)[0]),
            pitch_probability=np.asarray(result["pitch"], dtype=np.float32).reshape(-1),
            harmonic_amplitude=np.asarray(
                result["harmonic_amplitude"], dtype=np.float32
            ).reshape(-1),
            harmonic_offset_cents=np.asarray(
                result["harmonic_offset_cents"], dtype=np.float32
            ).reshape(-1),
            inference_ms=elapsed_ms,
        )


class TFLiteTransitionGate:
    def __init__(self, bundle: ProductBundle) -> None:
        import tensorflow as tf

        self.interpreter = tf.lite.Interpreter(
            model_path=str(bundle.gate_path), num_threads=1
        )
        self.interpreter.allocate_tensors()
        self.runner = self.interpreter.get_signature_runner("serving_default")

    def __call__(self, features: np.ndarray) -> np.ndarray:
        values = np.asarray(features, dtype=np.float32)
        return np.asarray(
            self.runner(features=values)["allow_transition"], dtype=np.float32
        )
