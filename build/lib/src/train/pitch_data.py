from __future__ import annotations

from typing import Dict, Tuple

import numpy as np

from src.train.global_normalizer import GlobalAudioNormalizer


def prepare_pitch_subset(
    arrays: Dict[str, np.ndarray],
    indices: np.ndarray,
    min_pitch: int,
    max_pitch: int,
    normalizer: GlobalAudioNormalizer,
) -> Tuple[Dict[str, np.ndarray], np.ndarray, Dict[str, np.ndarray]]:
    selected_pitch = arrays["pitch_midi"][indices].astype(np.int32)
    selected_active = arrays["active"][indices].astype(np.float32)

    valid = (
        (selected_active > 0.5)
        & (selected_pitch >= min_pitch)
        & (selected_pitch <= max_pitch)
    )
    valid_indices = indices[valid]
    if len(valid_indices) == 0:
        raise ValueError("No active pitch examples in this subset")

    audio = arrays["audio"][valid_indices].astype(np.float32, copy=True)
    visible = arrays["visible_window"][valid_indices].astype(np.int32)
    width = audio.shape[1]
    time_mask = np.zeros_like(audio, dtype=np.float32)

    for row_index, count_value in enumerate(visible):
        count = int(np.clip(int(count_value), 1, width))
        time_mask[row_index, -count:] = 1.0
        if count < width:
            audio[row_index, :-count] = 0.0

    audio = normalizer.apply(audio, time_mask)
    audio = audio[..., np.newaxis]

    pitch_midi = arrays["pitch_midi"][valid_indices].astype(np.int32)
    pitch_class = (pitch_midi - min_pitch).astype(np.int32)

    inputs = {"audio": audio, "time_mask": time_mask}
    metadata = {
        "indices": valid_indices.astype(np.int64),
        "pitch_midi": pitch_midi,
        "visible_window": visible,
        "prediction_age_ms": arrays["prediction_age_ms"][valid_indices].astype(np.float32),
        "note_id": arrays["note_id"][valid_indices].astype(np.int32),
    }
    return inputs, pitch_class, metadata
