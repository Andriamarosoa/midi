from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import numpy as np

from .manifest import ManifestItem


REQUIRED_FIELDS = {
    "audio",
    "visible_window",
    "prediction_age_ms",
    "pitch_midi",
    "active",
}

HARMONIC_LABEL_FIELDS = {
    "harmonic_present",
    "harmonic_amplitude",
    "harmonic_offset_cents",
    "harmonic_label_valid",
}


@dataclass
class CachedFile:
    source_id: str
    player_id: str
    npz_path: Path
    arrays: dict[str, np.ndarray]
    dataset_id: str = "guitarset"
    group_id: str = ""
    capture_id: str = ""

    @property
    def bytes_used(self) -> int:
        return int(sum(array.nbytes for array in self.arrays.values()))


class NPZRamCache:
    def __init__(
        self,
        items: Iterable[ManifestItem],
        validate_schema: bool = True,
    ) -> None:
        self.items = list(items)
        self.validate_schema = bool(validate_schema)
        self.files: list[CachedFile] = []
        self._source_to_index: dict[str, int] = {}

    def load(self) -> None:
        self.files.clear()
        self._source_to_index.clear()

        for item in self.items:
            with np.load(item.npz_path) as data:
                if self.validate_schema:
                    missing = REQUIRED_FIELDS - set(data.files)
                    if missing:
                        raise ValueError(
                            f"{item.npz_path}: colonnes manquantes {sorted(missing)}"
                        )

                arrays = {
                    name: np.asarray(data[name])
                    for name in data.files
                }

            if self.validate_schema and "harmonic_label_valid" in arrays:
                missing_harmonics = HARMONIC_LABEL_FIELDS - set(arrays)
                if missing_harmonics:
                    raise ValueError(
                        f"{item.npz_path}: labels harmoniques manquants "
                        f"{sorted(missing_harmonics)}"
                    )
                harmonic_shapes = {
                    arrays[name].shape for name in HARMONIC_LABEL_FIELDS
                }
                if len(harmonic_shapes) != 1:
                    raise ValueError(
                        f"{item.npz_path}: shapes harmoniques incoherentes "
                        f"{sorted(harmonic_shapes)}"
                    )
                valid = np.asarray(arrays["harmonic_label_valid"], dtype=np.float32)
                if not np.isfinite(valid).all() or np.any((valid < 0.0) | (valid > 1.0)):
                    raise ValueError(
                        f"{item.npz_path}: harmonic_label_valid doit etre fini dans [0, 1]"
                    )

            file_index = len(self.files)
            self.files.append(
                CachedFile(
                    source_id=item.source_id,
                    player_id=item.player_id,
                    npz_path=item.npz_path,
                    arrays=arrays,
                    dataset_id=item.dataset_id,
                    group_id=item.group_id,
                    capture_id=item.capture_id,
                )
            )
            self._source_to_index[item.source_id] = file_index

    def __len__(self) -> int:
        return len(self.files)

    def __getitem__(self, file_index: int) -> CachedFile:
        return self.files[file_index]

    @property
    def bytes_used(self) -> int:
        return int(sum(item.bytes_used for item in self.files))

    @property
    def gib_used(self) -> float:
        return self.bytes_used / (1024 ** 3)
