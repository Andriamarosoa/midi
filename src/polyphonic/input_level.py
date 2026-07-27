"""Causal session-level gain for the polyphonic model input only."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Mapping

import numpy as np


EPSILON = 1e-12


@dataclass(frozen=True)
class InputLevelResult:
    gain: float
    gain_db: float
    session_gain_db: float
    safety_gain_db: float
    observed_peak_dbfs: float
    observed_window_peak: float
    projected_model_peak: float
    initialized: bool


class CausalModelInputLeveler:
    """Match microphone sensitivity without normalizing every guitar tail.

    The controller observes only audible raw/capture hops.  It reduces gain
    immediately when a louder peak arrives, but can increase it by at most a
    small number of dB per second.  A decaying note therefore cannot be held at
    a constant level and mistaken for a fresh attack.  The selected scalar is
    applied uniformly to the complete causal model window by the caller; the
    audio activity gate and onset detector continue to see unlevelled audio.
    """

    def __init__(
        self,
        sample_rate: int,
        hop_samples: int,
        model_normalization_gain: float,
        *,
        input_samples: int = 4096,
        target_capture_peak_dbfs: float = -12.0,
        minimum_gain_db: float = 0.0,
        maximum_gain_db: float = 18.0,
        recovery_db_per_second: float = 1.0,
        model_headroom_peak: float = 0.98,
    ) -> None:
        if sample_rate <= 0 or hop_samples <= 0:
            raise ValueError("sample_rate and hop_samples must be positive")
        if model_normalization_gain <= 0.0:
            raise ValueError("model_normalization_gain must be positive")
        if input_samples < 1:
            raise ValueError("input_samples must be positive")
        if minimum_gain_db > maximum_gain_db:
            raise ValueError("minimum_gain_db must not exceed maximum_gain_db")
        if recovery_db_per_second <= 0.0:
            raise ValueError("recovery_db_per_second must be positive")
        if not 0.0 < model_headroom_peak < 1.0:
            raise ValueError("model_headroom_peak must be between zero and one")
        self.sample_rate = int(sample_rate)
        self.hop_samples = int(hop_samples)
        self.input_samples = int(input_samples)
        self.window_hops = int(np.ceil(
            self.input_samples / float(self.hop_samples)
        ))
        self.model_normalization_gain = float(model_normalization_gain)
        self.target_capture_peak_dbfs = float(target_capture_peak_dbfs)
        self.minimum_gain_db = float(minimum_gain_db)
        self.maximum_gain_db = float(maximum_gain_db)
        self.recovery_db_per_second = float(recovery_db_per_second)
        self.model_headroom_peak = float(model_headroom_peak)
        self.maximum_recovery_db_per_hop = (
            self.recovery_db_per_second
            * self.hop_samples
            / float(self.sample_rate)
        )
        self.session_gain_db = 0.0
        self.current_gain_db = 0.0
        self.current_safety_gain_db = float("inf")
        self.minimum_applied_gain_db: float | None = None
        self.maximum_applied_gain_db: float | None = None
        self.initialized = False
        self.audible_hops_seen = 0
        self.inactive_hops = 0
        self.hop_index = -1
        self.window_peaks: deque[tuple[int, float]] = deque()

    @classmethod
    def from_metadata(
        cls,
        sample_rate: int,
        hop_samples: int,
        model_normalization_gain: float,
        input_samples: int,
        metadata: Mapping[str, object],
    ) -> "CausalModelInputLeveler":
        config = metadata.get("automatic_model_input_level", {})
        values = config if isinstance(config, Mapping) else {}
        return cls(
            sample_rate,
            hop_samples,
            model_normalization_gain,
            input_samples=input_samples,
            target_capture_peak_dbfs=float(
                values.get("target_capture_peak_dbfs", -12.0)
            ),
            minimum_gain_db=float(
                values.get("minimum_gain_db", 0.0)
            ),
            maximum_gain_db=float(
                values.get("maximum_gain_db", 18.0)
            ),
            recovery_db_per_second=float(
                values.get("recovery_db_per_second", 1.0)
            ),
            model_headroom_peak=float(
                values.get("model_headroom_peak", 0.98)
            ),
        )

    @staticmethod
    def _dbfs(value: float) -> float:
        return float(20.0 * np.log10(max(float(value), EPSILON)))

    @property
    def gain(self) -> float:
        return float(10.0 ** (self.current_gain_db / 20.0))

    def process(self, hop: np.ndarray, *, audio_active: bool) -> InputLevelResult:
        samples = np.asarray(hop, dtype=np.float32).reshape(-1)
        if samples.shape != (self.hop_samples,):
            raise ValueError(f"Expected one audio hop of {self.hop_samples} samples.")
        peak = float(np.max(np.abs(samples), initial=0.0))
        self.hop_index += 1
        oldest = self.hop_index - self.window_hops + 1
        while self.window_peaks and self.window_peaks[0][0] < oldest:
            self.window_peaks.popleft()
        while self.window_peaks and self.window_peaks[-1][1] <= peak:
            self.window_peaks.pop()
        self.window_peaks.append((self.hop_index, peak))
        window_peak = self.window_peaks[0][1]
        peak_dbfs = self._dbfs(peak)
        if audio_active and peak > EPSILON:
            self.audible_hops_seen += 1
            self.inactive_hops = 0
            desired_gain_db = float(np.clip(
                self.target_capture_peak_dbfs - peak_dbfs,
                self.minimum_gain_db,
                self.maximum_gain_db,
            ))
            if not self.initialized:
                self.session_gain_db = desired_gain_db
                self.initialized = True
            elif desired_gain_db < self.session_gain_db:
                # Protect headroom immediately when the player strikes harder.
                self.session_gain_db = desired_gain_db
            # Never raise gain on an active tail.  Recovery is reserved for a
            # stable closed gate so it prepares the next note, not the decay.
        else:
            self.inactive_hops += 1
            if (
                self.initialized
                and self.inactive_hops >= self.window_hops
            ):
                self.session_gain_db = min(
                    self.maximum_gain_db,
                    self.session_gain_db
                    + self.maximum_recovery_db_per_hop,
                )

        if window_peak > EPSILON:
            maximum_safe_gain = (
                self.model_headroom_peak
                / (window_peak * self.model_normalization_gain)
            )
            self.current_safety_gain_db = self._dbfs(
                maximum_safe_gain
            )
        else:
            self.current_safety_gain_db = float("inf")
        self.current_gain_db = min(
            self.session_gain_db,
            self.current_safety_gain_db,
        )
        if self.initialized:
            if self.minimum_applied_gain_db is None:
                self.minimum_applied_gain_db = self.current_gain_db
                self.maximum_applied_gain_db = self.current_gain_db
            else:
                self.minimum_applied_gain_db = min(
                    self.minimum_applied_gain_db, self.current_gain_db
                )
                self.maximum_applied_gain_db = max(
                    float(self.maximum_applied_gain_db),
                    self.current_gain_db,
                )
        projected_model_peak = (
            window_peak * self.gain * self.model_normalization_gain
        )
        return InputLevelResult(
            gain=self.gain,
            gain_db=float(self.current_gain_db),
            session_gain_db=float(self.session_gain_db),
            safety_gain_db=float(self.current_safety_gain_db),
            observed_peak_dbfs=peak_dbfs,
            observed_window_peak=float(window_peak),
            projected_model_peak=float(projected_model_peak),
            initialized=bool(self.initialized),
        )

    def diagnostics(self) -> dict[str, object]:
        return {
            "enabled": True,
            "initialized": bool(self.initialized),
            "audible_hops_seen": int(self.audible_hops_seen),
            "gain": self.gain,
            "gain_db": float(self.current_gain_db),
            "session_gain_db": float(self.session_gain_db),
            "safety_gain_db": (
                None
                if not np.isfinite(self.current_safety_gain_db)
                else float(self.current_safety_gain_db)
            ),
            "minimum_applied_gain_db": (
                None
                if self.minimum_applied_gain_db is None
                else float(self.minimum_applied_gain_db)
            ),
            "maximum_applied_gain_db": (
                None
                if self.maximum_applied_gain_db is None
                else float(self.maximum_applied_gain_db)
            ),
            "target_capture_peak_dbfs": self.target_capture_peak_dbfs,
            "input_samples": self.input_samples,
            "window_hops": self.window_hops,
            "inactive_hops": self.inactive_hops,
            "minimum_gain_db": self.minimum_gain_db,
            "maximum_gain_db": self.maximum_gain_db,
            "recovery_db_per_second": self.recovery_db_per_second,
            "model_headroom_peak": self.model_headroom_peak,
            "model_normalization_gain": self.model_normalization_gain,
        }


def offline_model_input_level_gains(
    waveform: np.ndarray,
    audio_active: np.ndarray,
    sample_rate: int,
    hop_samples: int,
    model_normalization_gain: float,
    *,
    input_samples: int = 4096,
    minimum_gain_db: float = 0.0,
) -> tuple[np.ndarray, dict[str, object]]:
    """Replay the live leveler and return one causal scalar per audio hop.

    The supplied activity mask must come from the shared audio-evidence
    policy.  No note label is consulted, so this remains valid for
    validation-only decoder/input ablations.
    """
    source = np.asarray(waveform).reshape(-1)
    activity = np.asarray(audio_active, dtype=np.bool_).reshape(-1)
    if input_samples < 1:
        raise ValueError("input_samples must be positive")
    complete_frames = len(source) // hop_samples
    padded_frames = int(np.ceil(len(source) / float(hop_samples)))
    if len(activity) not in {complete_frames, padded_frames}:
        raise ValueError(
            f"audio_active has {len(activity)} rows; expected "
            f"{complete_frames} complete or {padded_frames} padded hops."
        )
    integer_scale = (
        float(max(abs(np.iinfo(source.dtype).min), 1))
        if np.issubdtype(source.dtype, np.integer)
        else 1.0
    )
    leveler = CausalModelInputLeveler(
        sample_rate,
        hop_samples,
        model_normalization_gain,
        input_samples=input_samples,
        minimum_gain_db=minimum_gain_db,
    )
    gains = np.ones(len(activity), dtype=np.float32)
    gain_db = np.zeros(len(activity), dtype=np.float32)
    baseline_projected_peak = np.zeros(len(activity), dtype=np.float32)
    projected_peak = np.zeros(len(activity), dtype=np.float32)
    for frame_index in range(len(activity)):
        start = frame_index * hop_samples
        hop = np.zeros(hop_samples, dtype=np.float32)
        part = np.asarray(
            source[start:start + hop_samples],
            dtype=np.float32,
        )
        if integer_scale != 1.0:
            part /= integer_scale
        hop[:len(part)] = part
        result = leveler.process(
            hop,
            audio_active=bool(activity[frame_index]),
        )
        gains[frame_index] = result.gain
        gain_db[frame_index] = result.gain_db
        baseline_projected_peak[frame_index] = (
            result.observed_window_peak
            * float(model_normalization_gain)
        )
        projected_peak[frame_index] = result.projected_model_peak

    def quantiles(values: np.ndarray) -> dict[str, float | None]:
        if len(values) == 0:
            return {
                "minimum": None,
                "median": None,
                "p95": None,
                "maximum": None,
            }
        return {
            "minimum": float(np.min(values)),
            "median": float(np.median(values)),
            "p95": float(np.percentile(values, 95)),
            "maximum": float(np.max(values)),
        }

    return gains, {
        "policy": "causal_session_peak_level_model_input_only",
        "label_leakage": False,
        "hops": len(activity),
        "active_hops": int(np.count_nonzero(activity)),
        "input_samples": int(input_samples),
        "window_hops": leveler.window_hops,
        "gain_db": quantiles(gain_db),
        "baseline_model_window_peak": quantiles(
            baseline_projected_peak
        ),
        "baseline_clipped_hops": int(np.count_nonzero(
            baseline_projected_peak > 1.0
        )),
        "projected_model_window_peak": quantiles(projected_peak),
        "projected_clipped_hops": int(np.count_nonzero(
            projected_peak > 1.0
        )),
        "controller": leveler.diagnostics(),
    }
