from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .cache import NPZRamCache


@dataclass(frozen=True)
class SampleRef:
    file_index: int
    sample_index: int


class GlobalSampleIndex:
    def __init__(
        self,
        cache: NPZRamCache,
        min_pitch: int,
        max_pitch: int,
    ) -> None:
        self.cache = cache
        self.min_pitch = int(min_pitch)
        self.max_pitch = int(max_pitch)

        refs: list[tuple[int, int]] = []
        pitches: list[int] = []

        for file_index, cached_file in enumerate(cache.files):
            arrays = cached_file.arrays
            pitch = arrays["pitch_midi"].astype(np.int32)
            active = arrays["active"] > 0.5

            valid = np.flatnonzero(
                active
                & (pitch >= self.min_pitch)
                & (pitch <= self.max_pitch)
            )

            refs.extend((file_index, int(sample_index)) for sample_index in valid)
            pitches.extend(int(pitch[sample_index]) for sample_index in valid)

        if not refs:
            raise ValueError("Aucun exemple valide dans le split.")

        self.refs = np.asarray(refs, dtype=np.int32)
        self.pitch_midi = np.asarray(pitches, dtype=np.int32)

    def __len__(self) -> int:
        return int(len(self.refs))

    def class_distribution(self) -> dict[int, int]:
        values, counts = np.unique(self.pitch_midi, return_counts=True)
        return {
            int(value): int(count)
            for value, count in zip(values, counts)
        }
