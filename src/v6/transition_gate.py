"""Causal V6.3.2 feature contract for V6.0 active-to-active transitions."""

from __future__ import annotations

import math
import time
from dataclasses import dataclass

import numpy as np

from src.stream.onset_detector import AdaptiveOnsetDetector
from src.product.contracts import FEATURE_NAMES
from src.product.decoder import harmonic_match_strength, transition_feature_values
from src.v5.external_data import NoteEvent


@dataclass(frozen=True)
class TransitionCandidate:
    frame_index: int
    current_pitch: int
    candidate_pitch: int
    feature: np.ndarray
    event_end_index: int
    annotation_support_ratio: float
    label: int
    target_note_id: int
    recent_onset_note_id: int
    harmonic_suspect: int


@dataclass(frozen=True)
class TransitionDecision:
    """Decision taken at the normal two-frame V6.0 commit point."""

    frame_index: int
    current_pitch: int
    candidate_pitch: int
    score: float
    allowed: bool
    feature: np.ndarray


def progressive_stream_features(
    waveform: np.ndarray,
    sample_rate: int,
    hop_size: int,
    end_samples: np.ndarray,
) -> tuple[np.ndarray, dict[str, np.ndarray]]:
    """Run the existing causal onset detector and retain its evidence."""
    detector = AdaptiveOnsetDetector(
        sample_rate=sample_rate,
        hop_samples=hop_size,
        fft_size=512,
        calibration_s=1.0,
    )
    visible = np.full(len(end_samples), 4096, dtype=np.int32)
    values = {
        "detected_onset": np.zeros(len(end_samples), dtype=np.float32),
        "onset_confidence": np.zeros(len(end_samples), dtype=np.float32),
        "onset_age": np.ones(len(end_samples), dtype=np.float32),
        "rms_level": np.zeros(len(end_samples), dtype=np.float32),
        "rms_growth_ratio": np.zeros(len(end_samples), dtype=np.float32),
        "spectral_flux": np.zeros(len(end_samples), dtype=np.float32),
    }
    last_onset_sample: int | None = None
    for index, end_sample in enumerate(end_samples):
        start = max(0, int(end_sample) - hop_size)
        hop = np.asarray(waveform[start:int(end_sample)], dtype=np.float32)
        if len(hop) < hop_size:
            hop = np.pad(hop, (hop_size - len(hop), 0))
        result = detector.process(hop)
        values["detected_onset"][index] = float(result.is_onset)
        values["onset_confidence"][index] = float(result.confidence)
        values["rms_level"][index] = float(
            np.clip((result.rms_dbfs + 100.0) / 100.0, 0.0, 1.0)
        )
        values["rms_growth_ratio"][index] = float(np.clip(
            result.rms_growth / max(result.rms, 1e-8), 0.0, 1.0
        ))
        values["spectral_flux"][index] = float(np.tanh(result.spectral_flux))
        if result.is_onset:
            last_onset_sample = int(end_sample)
        if last_onset_sample is not None:
            age_samples = int(end_sample) - last_onset_sample
            values["onset_age"][index] = float(np.clip(
                age_samples / sample_rate / 0.5, 0.0, 1.0
            ))
            visible[index] = next(
                (window for window in (512, 1024, 2048, 4096)
                 if age_samples <= window),
                4096,
            )
    return visible, values


def infer_v60_outputs(
    model,
    waveform: np.ndarray,
    end_samples: np.ndarray,
    visible_windows: np.ndarray,
    gain: float,
    batch_size: int,
    inference_function=None,
) -> tuple[dict[str, np.ndarray], float]:
    parts: dict[str, list[np.ndarray]] = {
        "active": [], "pitch": [], "harmonic_amplitude": [],
    }
    started = time.perf_counter()
    for start in range(0, len(end_samples), batch_size):
        selected = end_samples[start:start + batch_size]
        visible = visible_windows[start:start + batch_size]
        audio = np.zeros((len(selected), 4096, 1), dtype=np.float32)
        mask = np.zeros((len(selected), 4096), dtype=np.float32)
        for row, (end_sample, window) in enumerate(zip(selected, visible)):
            available = min(int(end_sample), int(window))
            if available:
                audio[row, -available:, 0] = waveform[
                    int(end_sample) - available:int(end_sample)
                ]
                mask[row, -available:] = 1.0
        audio *= float(gain)
        np.clip(audio, -1.0, 1.0, out=audio)
        raw = (
            model({"audio": audio, "time_mask": mask}, training=False)
            if inference_function is None
            else inference_function(audio, mask)
        )
        missing = set(parts) - set(raw)
        if missing:
            raise ValueError(f"Sorties V6.0 manquantes: {sorted(missing)}")
        for name in parts:
            parts[name].append(np.asarray(raw[name], dtype=np.float32))
    outputs = {
        name: np.concatenate(values) for name, values in parts.items()
    }
    outputs["active"] = outputs["active"].reshape(-1)
    return outputs, time.perf_counter() - started


def transition_feature_vector(
    frame_index: int,
    current_pitch: int,
    candidate_pitch: int,
    current_since: int,
    active_probability: np.ndarray,
    pitch_probability: np.ndarray,
    harmonic_amplitude: np.ndarray,
    stream_features: dict[str, np.ndarray],
    min_pitch: int,
    max_pitch: int,
    hop_ms: float,
) -> np.ndarray:
    index = int(frame_index)
    previous = max(0, index - 1)
    return transition_feature_values(
        current_pitch=current_pitch,
        candidate_pitch=candidate_pitch,
        current_duration_frames=index - current_since,
        active_probability=float(active_probability[index]),
        pitch_probability=pitch_probability[index],
        previous_pitch_probability=pitch_probability[previous],
        harmonic_amplitude=harmonic_amplitude[index],
        stream_features={
            name: float(stream_features[name][index])
            for name in (
                "detected_onset", "onset_confidence", "onset_age", "rms_level",
                "rms_growth_ratio", "spectral_flux",
            )
        },
        min_pitch=min_pitch,
        max_pitch=max_pitch,
        hop_ms=hop_ms,
    )


def extract_transition_candidates(
    active_probability: np.ndarray,
    pitch_probability: np.ndarray,
    harmonic_amplitude: np.ndarray,
    stream_features: dict[str, np.ndarray],
    active_threshold: float,
    notes: list[NoteEvent],
    active_sets: list[tuple[int, ...]],
    frame_times: np.ndarray,
    min_pitch: int,
    max_pitch: int,
    hop_ms: float,
    required_frames: int = 2,
) -> tuple[list[TransitionCandidate], np.ndarray, np.ndarray]:
    if required_frames < 1:
        raise ValueError("required_frames doit etre positif.")
    active_probability = np.asarray(active_probability, dtype=np.float32).reshape(-1)
    pitch_probability = np.asarray(pitch_probability, dtype=np.float32)
    predicted_active = active_probability >= float(active_threshold)
    predicted_pitch = (
        np.argmax(pitch_probability, axis=1).astype(np.int32) + int(min_pitch)
    )
    count = len(active_probability)
    if not (
        pitch_probability.shape == (count, max_pitch - min_pitch + 1)
        and len(harmonic_amplitude) == count
        and len(active_sets) == count
        and len(frame_times) == count
    ):
        raise ValueError("Shapes incoherentes pour les transitions V6.3.2.")

    output_active = np.zeros(count, dtype=bool)
    output_pitch = np.full(count, -1, dtype=np.int32)
    raw_records: list[tuple[int, int, int, np.ndarray]] = []
    current = -1
    current_since = 0
    pending = -2
    pending_count = 0
    for index in range(count):
        desired = int(predicted_pitch[index]) if predicted_active[index] else -1
        if desired == current:
            pending = -2
            pending_count = 0
        else:
            if desired == pending:
                pending_count += 1
            else:
                pending = desired
                pending_count = 1
            if pending_count >= required_frames:
                previous = current
                if previous >= 0 and desired >= 0:
                    raw_records.append((
                        index,
                        previous,
                        desired,
                        transition_feature_vector(
                            index, previous, desired, current_since,
                            active_probability, pitch_probability,
                            harmonic_amplitude, stream_features,
                            min_pitch, max_pitch, hop_ms,
                        ),
                    ))
                current = desired
                current_since = index
                pending = -2
                pending_count = 0
        if current >= 0:
            output_active[index] = True
            output_pitch[index] = current

    candidates: list[TransitionCandidate] = []
    for frame_index, previous, desired, feature in raw_records:
        end_index = frame_index + 1
        while (
            end_index < count
            and output_active[end_index]
            and output_pitch[end_index] == desired
        ):
            end_index += 1
        sets = active_sets[frame_index:end_index]
        support = float(np.mean([
            desired in pitches for pitches in sets
        ])) if sets else 0.0
        label = int(support > 0.0)
        frame_time = float(frame_times[frame_index])
        active_notes = [
            note for note in notes
            if note.start_s <= frame_time < note.end_s
        ]
        matching = [note for note in active_notes if note.pitch_midi == desired]
        target_note_id = matching[0].note_id if matching else -1
        recent = [
            note for note in notes
            if (
                note.pitch_midi == desired
                and 0.0 <= frame_time - note.start_s <= 0.05
            )
        ]
        recent_note_id = max(recent, key=lambda item: item.start_s).note_id if recent else -1
        harmonic_suspect = int(
            support == 0.0
            and any(
                desired - reference in {12, 19, 24, 28, 31, 36}
                for pitches in sets for reference in pitches
            )
        )
        candidates.append(TransitionCandidate(
            frame_index=frame_index,
            current_pitch=previous,
            candidate_pitch=desired,
            feature=feature,
            event_end_index=end_index,
            annotation_support_ratio=support,
            label=label,
            target_note_id=target_note_id,
            recent_onset_note_id=recent_note_id,
            harmonic_suspect=harmonic_suspect,
        ))
    return candidates, output_active, output_pitch


def stabilize_with_transition_gate(
    active_probability: np.ndarray,
    pitch_probability: np.ndarray,
    harmonic_amplitude: np.ndarray,
    stream_features: dict[str, np.ndarray],
    active_threshold: float,
    transition_threshold: float,
    gate_predict,
    min_pitch: int,
    max_pitch: int,
    hop_ms: float,
    required_frames: int = 2,
    minimum_retrigger_ms: float = 80.0,
) -> tuple[
    np.ndarray,
    np.ndarray,
    np.ndarray,
    np.ndarray,
    list[TransitionDecision],
]:
    """Gate stable active-to-active changes without altering other V6.0 paths.

    A rejected pitch stays blocked until the raw proposal changes. This avoids
    repeated retries that would turn a veto into an undocumented variable delay.
    """
    if required_frames < 1:
        raise ValueError("required_frames doit etre positif.")
    active_probability = np.asarray(active_probability, dtype=np.float32).reshape(-1)
    pitch_probability = np.asarray(pitch_probability, dtype=np.float32)
    harmonic_amplitude = np.asarray(harmonic_amplitude, dtype=np.float32)
    count = len(active_probability)
    required_stream = (
        "detected_onset", "onset_confidence", "onset_age", "rms_level",
        "rms_growth_ratio", "spectral_flux",
    )
    if not (
        pitch_probability.shape == (count, max_pitch - min_pitch + 1)
        and len(harmonic_amplitude) == count
        and all(len(np.asarray(stream_features[name])) == count for name in required_stream)
    ):
        raise ValueError("Shapes incoherentes pour le decodeur V6.3.2.")

    predicted_active = active_probability >= float(active_threshold)
    predicted_pitch = (
        np.argmax(pitch_probability, axis=1).astype(np.int32) + int(min_pitch)
    )
    detected_onset = np.asarray(
        stream_features["detected_onset"], dtype=np.float32
    ) >= 0.5
    output_active = np.zeros(count, dtype=bool)
    output_pitch = np.full(count, -1, dtype=np.int32)
    retrigger = np.zeros(count, dtype=bool)
    veto = np.zeros(count, dtype=bool)
    decisions: list[TransitionDecision] = []
    current = -1
    current_since = 0
    pending = -2
    pending_count = 0
    blocked = -2
    last_note_on = -10**9
    minimum_retrigger_frames = max(
        1, int(math.ceil(minimum_retrigger_ms / hop_ms))
    )

    for index in range(count):
        desired = int(predicted_pitch[index]) if predicted_active[index] else -1
        if blocked != -2 and desired != blocked:
            blocked = -2
        if desired == current:
            pending = -2
            pending_count = 0
            blocked = -2
            if (
                current >= 0
                and detected_onset[index]
                and index - last_note_on >= minimum_retrigger_frames
            ):
                retrigger[index] = True
                last_note_on = index
        elif desired == blocked:
            pending = -2
            pending_count = 0
        else:
            if desired == pending:
                pending_count += 1
            else:
                pending = desired
                pending_count = 1
            if pending_count >= required_frames:
                previous = current
                allowed = True
                if previous >= 0 and desired >= 0:
                    feature = transition_feature_vector(
                        index, previous, desired, current_since,
                        active_probability, pitch_probability,
                        harmonic_amplitude, stream_features,
                        min_pitch, max_pitch, hop_ms,
                    )
                    score_values = np.asarray(
                        gate_predict(feature[None, :]), dtype=np.float32
                    ).reshape(-1)
                    if score_values.size != 1 or not np.isfinite(score_values[0]):
                        raise ValueError("Score de transition V6.3.2 invalide.")
                    score = float(score_values[0])
                    allowed = score >= float(transition_threshold)
                    decisions.append(TransitionDecision(
                        frame_index=index,
                        current_pitch=previous,
                        candidate_pitch=desired,
                        score=score,
                        allowed=allowed,
                        feature=feature,
                    ))
                if allowed:
                    current = desired
                    current_since = index
                    blocked = -2
                    if current >= 0:
                        last_note_on = index
                else:
                    veto[index] = True
                    blocked = desired
                pending = -2
                pending_count = 0
        if current >= 0:
            output_active[index] = True
            output_pitch[index] = current
    return output_active, output_pitch, retrigger, veto, decisions


def build_transition_gate_model(feature_count: int = len(FEATURE_NAMES)):
    import tensorflow as tf

    features = tf.keras.Input(shape=(feature_count,), name="transition_features")
    x = tf.keras.layers.Dense(16, activation="swish", name="dense_1")(features)
    x = tf.keras.layers.Dense(8, activation="swish", name="dense_2")(x)
    allow = tf.keras.layers.Dense(1, activation="sigmoid", name="allow_transition")(x)
    return tf.keras.Model(features, allow, name="v6_3_2_transition_gate")
