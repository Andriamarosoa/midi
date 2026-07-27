from __future__ import annotations

import math
from typing import Any

import numpy as np
import tensorflow as tf

from .cache import NPZRamCache
from .dataset import GlobalSampleIndex
from .sampler import EpochSampler


class V5Sequence(tf.keras.utils.Sequence):
    def __init__(
        self,
        cache: NPZRamCache,
        sample_index: GlobalSampleIndex,
        batch_size: int,
        min_pitch: int,
        gain: float,
        seed: int,
        shuffle: bool,
        class_weights: np.ndarray | None = None,
        harmonic_targets: bool = False,
        harmonic_count: int = 20,
    ) -> None:
        super().__init__()

        self.cache = cache
        self.sample_index = sample_index
        self.batch_size = int(batch_size)
        self.min_pitch = int(min_pitch)
        self.gain = float(gain)
        self.harmonic_targets = bool(harmonic_targets)
        self.harmonic_count = int(harmonic_count)
        self.class_weights = (
            None if class_weights is None
            else np.asarray(class_weights, dtype=np.float32)
        )
        self.sampler = EpochSampler(
            sample_count=len(sample_index),
            seed=seed,
            shuffle=shuffle,
        )

        if self.batch_size <= 0:
            raise ValueError("batch_size doit être positif.")

        if self.harmonic_count < 1:
            raise ValueError("harmonic_count doit etre positif.")
        if self.harmonic_targets and self.class_weights is not None:
            raise ValueError(
                "Les class_weights pitch ne sont pas compatibles avec les "
                "cibles harmoniques multi-sorties."
            )

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

        audio_batch = np.zeros(
            (len(selected), input_samples, 1),
            dtype=np.float32,
        )
        mask_batch = np.zeros(
            (len(selected), input_samples),
            dtype=np.float32,
        )
        targets = np.zeros(len(selected), dtype=np.int32)
        harmonic_amplitude = None
        harmonic_offset_cents = None
        harmonic_valid = None
        if self.harmonic_targets:
            shape = (len(selected), self.harmonic_count)
            harmonic_amplitude = np.zeros(shape, dtype=np.float32)
            harmonic_offset_cents = np.zeros(shape, dtype=np.float32)
            harmonic_valid = np.zeros(shape, dtype=np.float32)

        for row, (file_index, sample_index) in enumerate(refs):
            cached = self.cache[int(file_index)]
            arrays = cached.arrays

            waveform = arrays["audio"][int(sample_index)].astype(
                np.float32,
                copy=True,
            )

            visible = int(arrays["visible_window"][int(sample_index)])
            visible = max(1, min(visible, input_samples))

            if visible < input_samples:
                waveform[:-visible] = 0.0

            waveform *= self.gain
            np.clip(waveform, -1.0, 1.0, out=waveform)

            audio_batch[row, :, 0] = waveform
            mask_batch[row, -visible:] = 1.0
            targets[row] = int(arrays["pitch_midi"][int(sample_index)]) - self.min_pitch

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
                    arrays["harmonic_amplitude"][int(sample_index)],
                    dtype=np.float32,
                )
                offset_row = np.asarray(
                    arrays["harmonic_offset_cents"][int(sample_index)],
                    dtype=np.float32,
                )
                valid_row = np.asarray(
                    arrays["harmonic_label_valid"][int(sample_index)],
                    dtype=np.float32,
                )
                expected_shape = (self.harmonic_count,)
                if (
                    amplitude_row.shape != expected_shape
                    or offset_row.shape != expected_shape
                    or valid_row.shape != expected_shape
                ):
                    raise ValueError(
                        f"{cached.source_id}: shape harmonique attendue "
                        f"{expected_shape}."
                    )
                harmonic_amplitude[row] = amplitude_row
                harmonic_offset_cents[row] = offset_row
                harmonic_valid[row] = valid_row

        inputs = {
            "audio": audio_batch,
            "time_mask": mask_batch,
        }
        if self.harmonic_targets:
            assert harmonic_amplitude is not None
            assert harmonic_offset_cents is not None
            assert harmonic_valid is not None
            multi_targets = {
                "pitch": targets,
                "harmonic_amplitude": np.concatenate(
                    [harmonic_amplitude, harmonic_valid], axis=1
                ),
                "harmonic_offset_cents": np.concatenate(
                    [harmonic_offset_cents, harmonic_valid, harmonic_amplitude],
                    axis=1,
                ),
            }
            return inputs, multi_targets
        if self.class_weights is None:
            return inputs, targets

        if np.any(targets < 0) or np.any(targets >= len(self.class_weights)):
            raise ValueError("Classe pitch hors de la table de pondération.")
        return inputs, targets, self.class_weights[targets]

    def on_epoch_end(self) -> None:
        self.order = self.sampler.indices_for_epoch()

    def metadata(self) -> dict[str, np.ndarray]:
        rows = self.sample_index.refs

        result: dict[str, list[Any]] = {
            "prediction_age_ms": [],
            "visible_window": [],
            "pitch_midi": [],
            "player_id": [],
            "source_id": [],
            "dataset_id": [],
            "note_id": [],
            "channel": [],
        }

        for file_index, sample_index in rows:
            cached = self.cache[int(file_index)]
            arrays = cached.arrays
            i = int(sample_index)

            result["prediction_age_ms"].append(float(arrays["prediction_age_ms"][i]))
            result["visible_window"].append(int(arrays["visible_window"][i]))
            result["pitch_midi"].append(int(arrays["pitch_midi"][i]))
            result["player_id"].append(cached.player_id)
            result["source_id"].append(cached.source_id)
            result["dataset_id"].append(cached.dataset_id)
            result["note_id"].append(int(arrays["note_id"][i]) if "note_id" in arrays else -1)
            result["channel"].append(int(arrays["channel"][i]) if "channel" in arrays else -1)

        return {
            "prediction_age_ms": np.asarray(result["prediction_age_ms"], dtype=np.float32),
            "visible_window": np.asarray(result["visible_window"], dtype=np.int32),
            "pitch_midi": np.asarray(result["pitch_midi"], dtype=np.int32),
            "player_id": np.asarray(result["player_id"], dtype=str),
            "source_id": np.asarray(result["source_id"], dtype=str),
            "dataset_id": np.asarray(result["dataset_id"], dtype=str),
            "note_id": np.asarray(result["note_id"], dtype=np.int32),
            "channel": np.asarray(result["channel"], dtype=np.int32),
        }
