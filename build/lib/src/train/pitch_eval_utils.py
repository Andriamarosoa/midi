from __future__ import annotations

from pathlib import Path
from typing import Tuple

import numpy as np

from src.dataset.tf_dataset import load_npz_arrays
from src.train.global_normalizer import GlobalAudioNormalizer
from src.train.pitch_data import prepare_pitch_subset


def load_pitch_evaluation(
    npz_path: Path,
    model_path: Path,
    validation_indices_path: Path,
    normalization_path: Path,
    min_pitch: int,
    max_pitch: int,
):
    import tensorflow as tf

    arrays = load_npz_arrays(npz_path)
    indices = np.load(validation_indices_path)
    normalizer = GlobalAudioNormalizer.load(normalization_path)
    inputs, targets, metadata = prepare_pitch_subset(
        arrays,
        indices,
        min_pitch,
        max_pitch,
        normalizer,
    )
    model = tf.keras.models.load_model(model_path)
    probabilities = model.predict(inputs, batch_size=32, verbose=0)
    if isinstance(probabilities, dict):
        probabilities = probabilities["pitch"]
    return probabilities, targets, metadata


def topk_accuracy(probabilities: np.ndarray, targets: np.ndarray, k: int) -> float:
    topk = np.argpartition(probabilities, -k, axis=1)[:, -k:]
    return float(np.mean(np.any(topk == targets[:, None], axis=1)))
