from __future__ import annotations

import numpy as np


class EpochSampler:
    """Deterministic one-pass sampler.

    Every example appears exactly once per epoch.
    """

    def __init__(
        self,
        sample_count: int,
        seed: int = 42,
        shuffle: bool = True,
    ) -> None:
        self.sample_count = int(sample_count)
        self.seed = int(seed)
        self.shuffle = bool(shuffle)
        self.epoch = 0

        if self.sample_count <= 0:
            raise ValueError("sample_count doit être positif.")

    def indices_for_epoch(self) -> np.ndarray:
        indices = np.arange(self.sample_count, dtype=np.int64)

        if self.shuffle:
            rng = np.random.default_rng(self.seed + self.epoch)
            rng.shuffle(indices)

        self.epoch += 1
        return indices
