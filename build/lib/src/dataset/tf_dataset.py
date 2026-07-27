from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional, Tuple

import numpy as np


@dataclass(frozen=True)
class DatasetConfig:
    batch_size: int = 32
    seed: int = 42
    normalize_audio: bool = True
    min_pitch: int = 40
    max_pitch: int = 88
    balance_pitch: bool = True


def load_npz_arrays(path: str | Path) -> Dict[str, np.ndarray]:
    data = np.load(Path(path))
    required = {
        "audio",
        "visible_window",
        "note_id",
        "pitch_midi",
        "onset",
        "attack_phase",
        "release_phase",
        "active",
    }
    missing = sorted(required - set(data.files))
    if missing:
        raise ValueError(f"Colonnes NPZ manquantes : {missing}")
    return {key: data[key] for key in data.files}


def split_indices_by_note_id(
    arrays: Dict[str, np.ndarray],
    validation_ratio: float,
    seed: int,
) -> Tuple[np.ndarray, np.ndarray]:
    if not 0.0 < validation_ratio < 1.0:
        raise ValueError("validation_ratio doit être dans ]0, 1[")

    note_ids = arrays["note_id"].astype(np.int64)
    real_note_ids = np.unique(note_ids[note_ids >= 0])

    rng = np.random.default_rng(seed)
    shuffled = real_note_ids.copy()
    rng.shuffle(shuffled)

    validation_note_count = max(1, round(len(shuffled) * validation_ratio))
    validation_note_ids = set(shuffled[:validation_note_count].tolist())

    validation_mask = np.array(
        [(note_id in validation_note_ids) for note_id in note_ids],
        dtype=bool,
    )

    # Split negative examples separately so both partitions contain silence.
    negative_indices = np.flatnonzero(note_ids < 0)
    rng.shuffle(negative_indices)
    negative_validation_count = max(
        1,
        round(len(negative_indices) * validation_ratio),
    ) if len(negative_indices) else 0

    if negative_validation_count:
        validation_mask[negative_indices[:negative_validation_count]] = True
        validation_mask[negative_indices[negative_validation_count:]] = False

    train_indices = np.flatnonzero(~validation_mask)
    validation_indices = np.flatnonzero(validation_mask)

    if len(train_indices) == 0 or len(validation_indices) == 0:
        raise ValueError("Split vide détecté")

    return train_indices, validation_indices


def compute_pitch_class_weights(
    pitch_midi: np.ndarray,
    active: np.ndarray,
    min_pitch: int,
    max_pitch: int,
) -> np.ndarray:
    classes = max_pitch - min_pitch + 1
    valid = (
        (active > 0.5)
        & (pitch_midi >= min_pitch)
        & (pitch_midi <= max_pitch)
    )

    counts = np.bincount(
        (pitch_midi[valid] - min_pitch).astype(np.int64),
        minlength=classes,
    ).astype(np.float64)

    weights = np.zeros(classes, dtype=np.float32)
    nonzero = counts > 0

    if np.any(nonzero):
        mean_count = float(np.mean(counts[nonzero]))
        weights[nonzero] = np.sqrt(mean_count / counts[nonzero]).astype(np.float32)
        weights[nonzero] /= float(np.mean(weights[nonzero]))

    return weights


def prepare_subset(
    arrays: Dict[str, np.ndarray],
    indices: np.ndarray,
    config: DatasetConfig,
    pitch_class_weights: Optional[np.ndarray] = None,
):
    audio = arrays["audio"][indices].astype(np.float32, copy=True)
    visible_window = arrays["visible_window"][indices].astype(np.int32)

    max_window = audio.shape[1]
    time_mask = np.zeros_like(audio, dtype=np.float32)

    for row_index, visible in enumerate(visible_window):
        visible = int(np.clip(visible, 1, max_window))
        time_mask[row_index, -visible:] = 1.0

        segment = audio[row_index, -visible:]
        if config.normalize_audio:
            peak = float(np.max(np.abs(segment)))
            if peak > 1e-8:
                audio[row_index, -visible:] = segment / peak

        if visible < max_window:
            audio[row_index, :-visible] = 0.0

    audio = audio[..., np.newaxis]

    pitch_midi = arrays["pitch_midi"][indices].astype(np.int32)
    active = arrays["active"][indices].astype(np.float32)

    valid_pitch = (
        (active > 0.5)
        & (pitch_midi >= config.min_pitch)
        & (pitch_midi <= config.max_pitch)
    )

    pitch_class = np.where(
        valid_pitch,
        pitch_midi - config.min_pitch,
        0,
    ).astype(np.int32)

    pitch_weight = valid_pitch.astype(np.float32)

    if config.balance_pitch and pitch_class_weights is not None:
        pitch_weight = pitch_weight * pitch_class_weights[pitch_class]

    inputs = {
        "audio": audio,
        "time_mask": time_mask,
    }

    targets = {
        "onset": arrays["onset"][indices].astype(np.float32),
        "attack_phase": arrays["attack_phase"][indices].astype(np.float32),
        "active": active,
        "release_phase": arrays["release_phase"][indices].astype(np.float32),
        "pitch": pitch_class,
    }

    sample_weights = {
        "onset": np.ones(len(indices), dtype=np.float32),
        "attack_phase": np.ones(len(indices), dtype=np.float32),
        "active": np.ones(len(indices), dtype=np.float32),
        "release_phase": np.ones(len(indices), dtype=np.float32),
        "pitch": pitch_weight.astype(np.float32),
    }

    metadata = {
        "visible_window": visible_window,
        "pitch_midi": pitch_midi,
        "note_id": arrays["note_id"][indices].astype(np.int32),
        "active": active,
    }

    return inputs, targets, sample_weights, metadata


def make_tf_dataset(
    inputs,
    targets,
    sample_weights,
    batch_size: int,
    shuffle: bool,
    seed: int,
):
    import tensorflow as tf

    dataset = tf.data.Dataset.from_tensor_slices(
        (inputs, targets, sample_weights)
    )

    if shuffle:
        dataset = dataset.shuffle(
            buffer_size=len(inputs["audio"]),
            seed=seed,
            reshuffle_each_iteration=True,
        )

    dataset = dataset.batch(batch_size)
    dataset = dataset.prefetch(tf.data.AUTOTUNE)
    return dataset
