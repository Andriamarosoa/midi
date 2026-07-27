from __future__ import annotations

from pathlib import Path
from typing import Dict

import numpy as np


class StreamNPZDataset:
    """Minimal framework-agnostic loader for one streaming NPZ file."""

    def __init__(self, path: str | Path, normalize_audio: bool = False) -> None:
        self.path = Path(path)
        self.data = np.load(self.path)
        self.normalize_audio = normalize_audio

    def __len__(self) -> int:
        return len(self.data["audio"])

    def __getitem__(self, index: int) -> Dict[str, object]:
        visible = int(self.data["visible_window"][index])
        audio = self.data["audio"][index, -visible:].astype(np.float32, copy=True)

        if self.normalize_audio:
            peak = float(np.max(np.abs(audio)))
            if peak > 1e-8:
                audio /= peak

        return {
            "audio": audio,
            "visible_window": visible,
            "prediction_age_ms": float(self.data["prediction_age_ms"][index]),
            "labels": {
                "pitch_midi": int(self.data["pitch_midi"][index]),
                "fundamental_hz": float(self.data["fundamental_hz"][index]),
                "onset": float(self.data["onset"][index]),
                "attack_phase": float(self.data["attack_phase"][index]),
                "release_phase": float(self.data["release_phase"][index]),
                "active": float(self.data["active"][index]),
                "harmonic_present": self.data["harmonic_present"][index].astype(np.float32),
                "harmonic_amplitude": self.data["harmonic_amplitude"][index].astype(np.float32),
                "harmonic_offset_cents": self.data["harmonic_offset_cents"][index].astype(np.float32),
            },
        }
