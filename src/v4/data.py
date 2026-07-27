from __future__ import annotations
from collections import OrderedDict
from pathlib import Path
from typing import Sequence
import math, numpy as np
from .manifest import ManifestItem

import tensorflow as tf
REQUIRED={'audio','visible_window','pitch_midi','active','prediction_age_ms'}

class NPZCache:
    def __init__(self,max_files:int=4): self.max_files=max(1,int(max_files)); self._cache=OrderedDict()
    def get(self,path:Path):
        key=str(path)
        if key in self._cache:
            value=self._cache.pop(key); self._cache[key]=value; return value
        with np.load(path) as data:
            missing=REQUIRED-set(data.files)
            if missing: raise ValueError(f"{path}: colonnes manquantes {sorted(missing)}")
            value={name:data[name] for name in data.files}
        self._cache[key]=value
        while len(self._cache)>self.max_files: self._cache.popitem(last=False)
        return value

def active_indices(data,min_pitch,max_pitch):
    pitch=data['pitch_midi']; active=data['active']>0.5
    return np.flatnonzero(active & (pitch>=min_pitch)&(pitch<=max_pitch))

def compute_global_gain(items,min_pitch,max_pitch,percentile,target,max_gain,sample_per_file=512,seed=42):
    rng=np.random.default_rng(seed); peaks=[]
    for item in items:
        with np.load(item.npz_path) as d:
            ids=active_indices(d,min_pitch,max_pitch)
            if len(ids)>sample_per_file: ids=rng.choice(ids,size=sample_per_file,replace=False)
            if len(ids): peaks.extend(np.max(np.abs(d['audio'][ids]),axis=1).tolist())
    reference=float(np.percentile(np.asarray(peaks),percentile)) if peaks else 1.0
    return min(float(max_gain),float(target)/max(reference,1e-8))

class MultiNPZSequence(tf.keras.utils.Sequence):
    def __init__(
        self,
        entries,
        batch_size: int,
        min_pitch: int,
        max_pitch: int,
        gain: float,
        seed: int = 42,
        shuffle: bool = True,
        cache_size: int = 4,
        steps_per_epoch: int | None = None,
    ) -> None:
        super().__init__()

        self.entries = list(entries)
        self.batch_size = int(batch_size)
        self.min_pitch = int(min_pitch)
        self.max_pitch = int(max_pitch)
        self.gain = float(gain)
        self.seed = int(seed)
        self.shuffle = bool(shuffle)
        self.cache_size = int(cache_size)
        self.steps_per_epoch = steps_per_epoch

        if not self.entries:
            raise ValueError("MultiNPZSequence ne contient aucun fichier.")

        if self.batch_size <= 0:
            raise ValueError("batch_size doit être positif.")

        self.rng = np.random.default_rng(self.seed)
        self.cache: dict[Path, dict[str, np.ndarray]] = {}
        self.cache_order: list[Path] = []

        self.samples: list[tuple[int, int]] = []

        for entry_index, entry in enumerate(self.entries):
            npz_path = Path(entry.npz_path)

            with np.load(npz_path) as data:
                pitch = data["pitch_midi"]
                active = data["active"]

                valid_indices = np.flatnonzero(
                    (active > 0.5)
                    & (pitch >= self.min_pitch)
                    & (pitch <= self.max_pitch)
                )

            self.samples.extend(
                (entry_index, int(sample_index))
                for sample_index in valid_indices
            )

        if not self.samples:
            raise ValueError(
                "Aucun exemple de pitch actif trouvé dans les fichiers NPZ."
            )

        self.indexes = np.arange(len(self.samples), dtype=np.int64)
        self.on_epoch_end()

    def __len__(self) -> int:
        if self.steps_per_epoch is not None:
            return int(self.steps_per_epoch)

        return max(
            1,
            int(np.ceil(len(self.indexes) / self.batch_size)),
        )

    def _load_npz(self, path: Path) -> dict[str, np.ndarray]:
        path = Path(path)

        if path in self.cache:
            return self.cache[path]

        with np.load(path) as data:
            arrays = {
                key: data[key]
                for key in data.files
            }

        self.cache[path] = arrays
        self.cache_order.append(path)

        while len(self.cache_order) > self.cache_size:
            oldest = self.cache_order.pop(0)
            self.cache.pop(oldest, None)

        return arrays

    def __getitem__(self, batch_index: int):
        start = batch_index * self.batch_size

        if self.steps_per_epoch is not None:
            selected_positions = self.rng.integers(
                low=0,
                high=len(self.indexes),
                size=self.batch_size,
            )
            selected_indexes = self.indexes[selected_positions]
        else:
            end = min(start + self.batch_size, len(self.indexes))
            selected_indexes = self.indexes[start:end]

        if len(selected_indexes) == 0:
            raise IndexError(batch_index)

        first_entry_index, first_sample_index = self.samples[
            int(selected_indexes[0])
        ]
        first_entry = self.entries[first_entry_index]
        first_arrays = self._load_npz(Path(first_entry.npz_path))

        input_samples = int(first_arrays["audio"].shape[1])
        batch_length = len(selected_indexes)

        audio_batch = np.zeros(
            (batch_length, input_samples, 1),
            dtype=np.float32,
        )
        mask_batch = np.zeros(
            (batch_length, input_samples),
            dtype=np.float32,
        )
        target_batch = np.zeros(
            batch_length,
            dtype=np.int32,
        )

        for row, global_index in enumerate(selected_indexes):
            entry_index, sample_index = self.samples[int(global_index)]
            entry = self.entries[entry_index]
            arrays = self._load_npz(Path(entry.npz_path))

            waveform = arrays["audio"][sample_index].astype(
                np.float32,
                copy=True,
            )

            visible = int(arrays["visible_window"][sample_index])
            visible = max(1, min(visible, input_samples))

            if visible < input_samples:
                waveform[:-visible] = 0.0

            waveform *= self.gain
            np.clip(waveform, -1.0, 1.0, out=waveform)

            audio_batch[row, :, 0] = waveform
            mask_batch[row, -visible:] = 1.0

            midi = int(arrays["pitch_midi"][sample_index])
            target_batch[row] = midi - self.min_pitch

        inputs = {
            "audio": audio_batch,
            "time_mask": mask_batch,
        }

        return inputs, target_batch

    def on_epoch_end(self) -> None:
        if self.shuffle:
            self.rng.shuffle(self.indexes)

def materialize_sequence(sequence:MultiNPZSequence):
    inputs_audio=[]; inputs_mask=[]; targets=[]
    for index in range(len(sequence)):
        x,y=sequence[index]; inputs_audio.append(x['audio']); inputs_mask.append(x['time_mask']); targets.append(y)
    return {'audio':np.concatenate(inputs_audio),'time_mask':np.concatenate(inputs_mask)},np.concatenate(targets)
