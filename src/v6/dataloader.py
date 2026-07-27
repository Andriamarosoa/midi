from __future__ import annotations

import math
from typing import Any

import numpy as np
import tensorflow as tf

from src.v5.cache import NPZRamCache
from src.v5.sampler import EpochSampler

from .dataset import GlobalSampleIndex


class V6Sequence(tf.keras.utils.Sequence):
    """Serve causal mono examples with masked pitch and harmonic losses."""

    def __init__(
        self,
        cache: NPZRamCache,
        sample_index: GlobalSampleIndex,
        batch_size: int,
        min_pitch: int,
        gain: float,
        seed: int,
        shuffle: bool,
        pitch_class_weights: np.ndarray | None = None,
        activity_weights: np.ndarray | None = None,
        onset_targets: bool = False,
        onset_weights: np.ndarray | None = None,
        harmonic_targets: bool = True,
        harmonic_count: int = 20,
    ) -> None:
        super().__init__()
        self.cache = cache
        self.sample_index = sample_index
        self.batch_size = int(batch_size)
        self.min_pitch = int(min_pitch)
        self.gain = float(gain)
        self.pitch_class_weights = (
            None
            if pitch_class_weights is None
            else np.asarray(pitch_class_weights, dtype=np.float32)
        )
        self.activity_weights = (
            np.ones(2, dtype=np.float32)
            if activity_weights is None
            else np.asarray(activity_weights, dtype=np.float32)
        )
        self.onset_targets = bool(onset_targets)
        self.onset_weights = (
            np.ones(2, dtype=np.float32)
            if onset_weights is None
            else np.asarray(onset_weights, dtype=np.float32)
        )
        self.harmonic_targets = bool(harmonic_targets)
        self.harmonic_count = int(harmonic_count)
        self.sampler = EpochSampler(len(sample_index), seed=seed, shuffle=shuffle)

        if self.batch_size <= 0:
            raise ValueError("batch_size doit etre positif.")
        if self.activity_weights.shape != (2,):
            raise ValueError("activity_weights doit contenir [inactif, actif].")
        if np.any(self.activity_weights <= 0.0):
            raise ValueError("Les poids active doivent etre strictement positifs.")
        if self.onset_weights.shape != (2,):
            raise ValueError("onset_weights doit contenir [non_onset, onset].")
        if np.any(self.onset_weights <= 0.0):
            raise ValueError("Les poids onset doivent etre strictement positifs.")
        if self.harmonic_count < 1:
            raise ValueError("harmonic_count doit etre positif.")

        self.order = self.sampler.indices_for_epoch()

    def __len__(self) -> int:
        return max(1, math.ceil(len(self.order) / self.batch_size))

    def __getitem__(self, batch_index: int):
        start = batch_index * self.batch_size
        end = min(start + self.batch_size, len(self.order))
        selected = self.order[start:end]
        if len(selected) == 0:
            raise IndexError(batch_index)

        refs = self.sample_index.refs[selected]
        first_file = self.cache[int(refs[0, 0])]
        input_samples = int(first_file.arrays["audio"].shape[1])
        size = len(selected)

        audio_batch = np.zeros((size, input_samples, 1), dtype=np.float32)
        mask_batch = np.zeros((size, input_samples), dtype=np.float32)
        pitch_target = np.zeros(size, dtype=np.int32)
        active_target = np.zeros((size, 1), dtype=np.float32)
        pitch_weight = np.zeros(size, dtype=np.float32)
        active_weight = np.zeros(size, dtype=np.float32)
        onset_target = np.zeros((size, 1), dtype=np.float32)
        onset_weight = np.zeros(size, dtype=np.float32)

        amplitude = np.zeros((size, self.harmonic_count), dtype=np.float32)
        offset = np.zeros((size, self.harmonic_count), dtype=np.float32)
        harmonic_valid = np.zeros((size, self.harmonic_count), dtype=np.float32)

        for row, (file_index, sample_index) in enumerate(refs):
            cached = self.cache[int(file_index)]
            arrays = cached.arrays
            index = int(sample_index)
            waveform = np.asarray(arrays["audio"][index], dtype=np.float32).copy()
            visible = int(np.clip(arrays["visible_window"][index], 1, input_samples))
            if visible < input_samples:
                waveform[:-visible] = 0.0
            waveform *= self.gain
            np.clip(waveform, -1.0, 1.0, out=waveform)

            audio_batch[row, :, 0] = waveform
            mask_batch[row, -visible:] = 1.0

            is_active = float(arrays["active"][index] > 0.5)
            active_target[row, 0] = is_active
            active_weight[row] = self.activity_weights[int(is_active)]
            if self.onset_targets:
                if "onset" not in arrays:
                    raise ValueError(f"{cached.source_id}: cible onset manquante.")
                is_onset = float(arrays["onset"][index] > 0.5)
                if is_onset > is_active:
                    raise ValueError(
                        f"{cached.source_id}: onset actif sur exemple inactif."
                    )
                onset_target[row, 0] = is_onset
                onset_weight[row] = self.onset_weights[int(is_onset)]
            if is_active:
                pitch_class = int(arrays["pitch_midi"][index]) - self.min_pitch
                pitch_target[row] = pitch_class
                pitch_weight[row] = (
                    1.0
                    if self.pitch_class_weights is None
                    else float(self.pitch_class_weights[pitch_class])
                )

            if self.harmonic_targets:
                required = {
                    "harmonic_amplitude",
                    "harmonic_offset_cents",
                    "harmonic_label_valid",
                }
                missing = required - set(arrays)
                if missing:
                    raise ValueError(
                        f"{cached.source_id}: cibles harmoniques manquantes "
                        f"{sorted(missing)}"
                    )
                amplitude_row = np.asarray(
                    arrays["harmonic_amplitude"][index], dtype=np.float32
                )
                offset_row = np.asarray(
                    arrays["harmonic_offset_cents"][index], dtype=np.float32
                )
                valid_row = np.asarray(
                    arrays["harmonic_label_valid"][index], dtype=np.float32
                )
                expected = (self.harmonic_count,)
                if (
                    amplitude_row.shape != expected
                    or offset_row.shape != expected
                    or valid_row.shape != expected
                ):
                    raise ValueError(
                        f"{cached.source_id}: shape harmonique attendue {expected}."
                    )
                amplitude[row] = amplitude_row
                offset[row] = offset_row
                harmonic_valid[row] = valid_row * is_active

        targets: dict[str, np.ndarray] = {
            "pitch": pitch_target,
            "active": active_target,
        }
        sample_weights: dict[str, np.ndarray] = {
            "pitch": pitch_weight,
            "active": active_weight,
        }

        if self.onset_targets:
            targets["onset"] = onset_target
            sample_weights["onset"] = onset_weight

        if self.harmonic_targets:
            targets["harmonic_amplitude"] = np.concatenate(
                [amplitude, harmonic_valid], axis=1
            )
            targets["harmonic_offset_cents"] = np.concatenate(
                [offset, harmonic_valid, amplitude], axis=1
            )
            sample_weights["harmonic_amplitude"] = active_target[:, 0]
            sample_weights["harmonic_offset_cents"] = active_target[:, 0]

        inputs = {"audio": audio_batch, "time_mask": mask_batch}
        return inputs, targets, sample_weights

    def on_epoch_end(self) -> None:
        self.order = self.sampler.indices_for_epoch()

    def metadata(self) -> dict[str, np.ndarray]:
        result: dict[str, list[Any]] = {
            "prediction_age_ms": [],
            "visible_window": [],
            "pitch_midi": [],
            "active": [],
            "onset": [],
            "release_phase": [],
            "player_id": [],
            "source_id": [],
            "dataset_id": [],
            "note_id": [],
            "channel": [],
        }
        for file_index, sample_index in self.sample_index.refs:
            cached = self.cache[int(file_index)]
            arrays = cached.arrays
            index = int(sample_index)
            result["prediction_age_ms"].append(float(arrays["prediction_age_ms"][index]))
            result["visible_window"].append(int(arrays["visible_window"][index]))
            result["pitch_midi"].append(int(arrays["pitch_midi"][index]))
            result["active"].append(float(arrays["active"][index]))
            result["onset"].append(
                float(arrays["onset"][index]) if "onset" in arrays else 0.0
            )
            result["release_phase"].append(
                float(arrays["release_phase"][index])
                if "release_phase" in arrays else 0.0
            )
            result["player_id"].append(cached.player_id)
            result["source_id"].append(cached.source_id)
            result["dataset_id"].append(cached.dataset_id)
            result["note_id"].append(
                int(arrays["note_id"][index]) if "note_id" in arrays else -1
            )
            result["channel"].append(
                int(arrays["channel"][index]) if "channel" in arrays else -1
            )

        return {
            "prediction_age_ms": np.asarray(result["prediction_age_ms"], dtype=np.float32),
            "visible_window": np.asarray(result["visible_window"], dtype=np.int32),
            "pitch_midi": np.asarray(result["pitch_midi"], dtype=np.int32),
            "active": np.asarray(result["active"], dtype=np.float32),
            "onset": np.asarray(result["onset"], dtype=np.float32),
            "release_phase": np.asarray(result["release_phase"], dtype=np.float32),
            "player_id": np.asarray(result["player_id"], dtype=str),
            "source_id": np.asarray(result["source_id"], dtype=str),
            "dataset_id": np.asarray(result["dataset_id"], dtype=str),
            "note_id": np.asarray(result["note_id"], dtype=np.int32),
            "channel": np.asarray(result["channel"], dtype=np.int32),
        }
