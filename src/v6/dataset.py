from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.v5.cache import NPZRamCache


@dataclass(frozen=True)
class SampleRef:
    file_index: int
    sample_index: int


class GlobalSampleIndex:
    """Index supported active notes plus all inactive mono examples.

    Active notes outside the configured MIDI range are excluded so that the
    binary head never opens the gate for a pitch the softmax cannot emit.
    """

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
        activity: list[float] = []
        onsets: list[float] = []

        for file_index, cached_file in enumerate(cache.files):
            arrays = cached_file.arrays
            pitch = np.asarray(arrays["pitch_midi"], dtype=np.int32)
            active = np.asarray(arrays["active"], dtype=np.float32) > 0.5
            if "onset" not in arrays:
                raise ValueError(f"{cached_file.source_id}: label onset manquant.")
            onset = np.asarray(arrays["onset"], dtype=np.float32) > 0.5
            if onset.shape != active.shape:
                raise ValueError(
                    f"{cached_file.source_id}: shape onset incoherente."
                )
            if np.any(onset & ~active):
                raise ValueError(
                    f"{cached_file.source_id}: onset inactif incoherent."
                )
            supported = (pitch >= self.min_pitch) & (pitch <= self.max_pitch)
            selected = np.flatnonzero((active & supported) | ~active)

            refs.extend((file_index, int(index)) for index in selected)
            pitches.extend(int(pitch[index]) for index in selected)
            activity.extend(float(active[index]) for index in selected)
            onsets.extend(float(onset[index]) for index in selected)

        if not refs:
            raise ValueError("Aucun exemple V6 valide dans le split.")

        self.refs = np.asarray(refs, dtype=np.int32)
        self.pitch_midi = np.asarray(pitches, dtype=np.int32)
        self.active = np.asarray(activity, dtype=np.float32)
        self.onset = np.asarray(onsets, dtype=np.float32)

        if not np.any(self.active > 0.5):
            raise ValueError("Le split V6 ne contient aucun exemple actif.")
        if not np.any(self.active <= 0.5):
            raise ValueError("Le split V6 ne contient aucun exemple inactif.")

    def __len__(self) -> int:
        return int(len(self.refs))

    @property
    def positive_mask(self) -> np.ndarray:
        return self.active > 0.5

    def class_distribution(self) -> dict[int, int]:
        values, counts = np.unique(
            self.pitch_midi[self.positive_mask],
            return_counts=True,
        )
        return {
            int(value): int(count)
            for value, count in zip(values, counts)
        }

    def activity_distribution(self) -> dict[str, int]:
        positive = int(np.sum(self.positive_mask))
        return {
            "active": positive,
            "inactive": int(len(self) - positive),
        }

    def onset_distribution(self) -> dict[str, int]:
        positive = int(np.sum(self.onset > 0.5))
        return {
            "onset": positive,
            "non_onset": int(len(self) - positive),
        }
