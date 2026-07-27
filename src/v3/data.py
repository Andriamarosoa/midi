from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Tuple
import math
import numpy as np


REQUIRED = {"audio", "visible_window", "prediction_age_ms", "pitch_midi", "note_id", "active"}


def load_arrays(path: str | Path) -> Dict[str, np.ndarray]:
    data = np.load(Path(path))
    missing = sorted(REQUIRED - set(data.files))
    if missing:
        raise ValueError(f"Colonnes NPZ manquantes: {missing}")
    return {name: data[name] for name in data.files}


def active_pitch_indices(arrays: Dict[str, np.ndarray], min_pitch: int, max_pitch: int) -> np.ndarray:
    pitch = arrays["pitch_midi"]
    active = arrays["active"] > 0.5
    note_id = arrays["note_id"] >= 0
    valid = active & note_id & (pitch >= min_pitch) & (pitch <= max_pitch)
    return np.flatnonzero(valid)


def stratified_group_split(
    arrays: Dict[str, np.ndarray],
    candidate_indices: np.ndarray,
    validation_ratio: float,
    seed: int,
) -> Tuple[np.ndarray, np.ndarray, Dict[str, object]]:
    """Split by pitch then note_id.

    Every pitch in validation is guaranteed to exist in train. Pitches with one
    unique note_id remain train-only and are reported as non-evaluable.
    """
    if not 0.0 < validation_ratio < 1.0:
        raise ValueError("validation_ratio doit être dans ]0, 1[")

    rng = np.random.default_rng(seed)
    pitch = arrays["pitch_midi"].astype(np.int32)
    note_id = arrays["note_id"].astype(np.int64)

    train_groups: set[int] = set()
    val_groups: set[int] = set()
    singleton_pitches: List[int] = []

    for midi in sorted(np.unique(pitch[candidate_indices])):
        indices = candidate_indices[pitch[candidate_indices] == midi]
        groups = np.unique(note_id[indices])
        rng.shuffle(groups)
        if len(groups) < 2:
            train_groups.update(int(v) for v in groups)
            singleton_pitches.append(int(midi))
            continue

        val_count = max(1, int(round(len(groups) * validation_ratio)))
        val_count = min(val_count, len(groups) - 1)
        val_groups.update(int(v) for v in groups[:val_count])
        train_groups.update(int(v) for v in groups[val_count:])

    train_mask = np.array([int(note_id[i]) in train_groups for i in candidate_indices])
    val_mask = np.array([int(note_id[i]) in val_groups for i in candidate_indices])
    train_indices = candidate_indices[train_mask]
    val_indices = candidate_indices[val_mask]

    train_pitches = set(int(v) for v in np.unique(pitch[train_indices]))
    val_pitches = set(int(v) for v in np.unique(pitch[val_indices]))
    absent = sorted(val_pitches - train_pitches)
    if absent:
        raise RuntimeError(f"Split invalide, pitches validation absents du train: {absent}")

    report = {
        "train_examples": int(len(train_indices)),
        "validation_examples": int(len(val_indices)),
        "train_note_ids": sorted(int(v) for v in train_groups),
        "validation_note_ids": sorted(int(v) for v in val_groups),
        "singleton_train_only_pitches": singleton_pitches,
        "train_pitches": sorted(train_pitches),
        "validation_pitches": sorted(val_pitches),
    }
    return train_indices, val_indices, report


def compute_global_gain(
    arrays: Dict[str, np.ndarray],
    indices: np.ndarray,
    percentile: float,
    target: float,
    max_gain: float,
) -> float:
    values: List[np.ndarray] = []
    audio = arrays["audio"]
    visible = arrays["visible_window"].astype(np.int32)
    for index in indices:
        length = int(np.clip(visible[index], 1, audio.shape[1]))
        values.append(np.abs(audio[index, -length:]).reshape(-1))
    if not values:
        return 1.0
    concatenated = np.concatenate(values)
    reference = float(np.percentile(concatenated, percentile))
    if reference <= 1e-8:
        return 1.0
    return float(min(max_gain, target / reference))


def prepare_inputs(
    arrays: Dict[str, np.ndarray],
    indices: np.ndarray,
    min_pitch: int,
    gain: float,
) -> Tuple[Dict[str, np.ndarray], np.ndarray, Dict[str, np.ndarray]]:
    audio = arrays["audio"][indices].astype(np.float32, copy=True)
    visible = arrays["visible_window"][indices].astype(np.int32)
    time_mask = np.zeros_like(audio, dtype=np.float32)
    max_window = audio.shape[1]

    for row, length in enumerate(visible):
        length = int(np.clip(length, 1, max_window))
        if length < max_window:
            audio[row, :-length] = 0.0
        time_mask[row, -length:] = 1.0

    audio *= np.float32(gain)
    np.clip(audio, -1.0, 1.0, out=audio)

    targets = (arrays["pitch_midi"][indices].astype(np.int32) - min_pitch).astype(np.int32)
    metadata = {
        "pitch_midi": arrays["pitch_midi"][indices].astype(np.int32),
        "note_id": arrays["note_id"][indices].astype(np.int32),
        "visible_window": visible,
        "prediction_age_ms": arrays["prediction_age_ms"][indices].astype(np.float32),
    }
    return {"audio": audio[..., None], "time_mask": time_mask}, targets, metadata


def make_validation_dataset(inputs: Dict[str, np.ndarray], targets: np.ndarray, batch_size: int):
    import tensorflow as tf
    ds = tf.data.Dataset.from_tensor_slices((inputs, targets))
    return ds.batch(batch_size).prefetch(tf.data.AUTOTUNE)


def make_limited_balanced_sequence(
    inputs: Dict[str, np.ndarray],
    targets: np.ndarray,
    pitch_midi: np.ndarray,
    batch_size: int,
    seed: int,
    balance_strength: float,
    max_class_multiplier: float,
    epoch_multiplier: float,
):
    """Create a Keras Sequence with soft, capped class balancing."""
    import tensorflow as tf

    class _LimitedBalancedSequence(tf.keras.utils.Sequence):
        def __init__(self) -> None:
            self.inputs = inputs
            self.targets = targets
            self.pitch_midi = pitch_midi
            self.batch_size = int(batch_size)
            self.rng = np.random.default_rng(seed)
            self.balance_strength = float(np.clip(balance_strength, 0.0, 1.0))
            self.max_class_multiplier = max(1.0, float(max_class_multiplier))
            self.epoch_multiplier = max(0.1, float(epoch_multiplier))
            self.class_indices = {
                int(midi): np.flatnonzero(pitch_midi == midi)
                for midi in np.unique(pitch_midi)
            }
            self.epoch_indices = np.empty(0, dtype=np.int64)
            self.on_epoch_end()

        def __len__(self) -> int:
            return max(1, math.ceil(len(self.epoch_indices) / self.batch_size))

        def __getitem__(self, batch_index: int):
            start = batch_index * self.batch_size
            batch = self.epoch_indices[start:start + self.batch_size]
            return {key: value[batch] for key, value in self.inputs.items()}, self.targets[batch]

        def on_epoch_end(self) -> None:
            counts = {midi: len(indices) for midi, indices in self.class_indices.items()}
            max_count = max(counts.values())
            sampled: List[np.ndarray] = []
            for midi, indices in self.class_indices.items():
                count = len(indices)
                soft_target = int(round((count ** (1.0 - self.balance_strength)) * (max_count ** self.balance_strength)))
                cap = int(math.ceil(count * self.max_class_multiplier))
                target = max(count, min(soft_target, cap))
                chosen = self.rng.choice(indices, size=target, replace=target > count)
                sampled.append(chosen)
            epoch = np.concatenate(sampled)
            desired = max(1, int(round(len(self.targets) * self.epoch_multiplier)))
            if len(epoch) > desired:
                epoch = self.rng.choice(epoch, size=desired, replace=False)
            elif len(epoch) < desired:
                epoch = self.rng.choice(epoch, size=desired, replace=True)
            self.rng.shuffle(epoch)
            self.epoch_indices = epoch.astype(np.int64)

    return _LimitedBalancedSequence()
