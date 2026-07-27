"""Annotation-free spectral audit of a MIDI transcription and its source WAV.

This tool is intended for live captures without aligned note annotations.  It
can flag generated notes whose pitch has little spectral support and propose
durable, attack-aligned WAV pitches absent from the active MIDI.  Proposed
missing notes are hypotheses only: without aligned annotations this tool
cannot measure recall.
"""

from __future__ import annotations

import argparse
from collections import Counter
import json
import math
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import soundfile as sf
from scipy.signal import resample_poly

from src.polyphonic.audio_evidence import PolyphonicAudioEvidencePolicy
from src.polyphonic.evaluate_events import NoteInterval
from src.polyphonic.validate_product_inverse import (
    spectral_inverse_diagnostics,
)
from src.v5.external_data import parse_midi_notes


ANALYSIS_WINDOW_SAMPLES = 4096
SPECTRAL_FFT_SAMPLES = 16_384
ATTACK_WINDOW_SAMPLES = 1024
DEFAULT_HOP_SAMPLES = 256
DEFAULT_MIDI_MIN = 40
DEFAULT_MIDI_MAX = 76
POST_ATTACK_PROBE_HOPS = (2, 4, 6, 8, 10)
MINIMUM_SUPPORTED_PROBES = 3
MINIMUM_SPECTRAL_RATIO = 0.20
MINIMUM_SPECTRAL_SNR = 6.0
REVIEW_MINIMUM_SUPPORTED_PROBES = 4
REVIEW_MINIMUM_SPECTRAL_RATIO = 0.35
MIDI_OVERLAP_TOLERANCE_S = 0.050
TEMPORAL_GROUPING_S = 0.120
HARMONIC_INTERVALS = (12, 19, 24, 28, 31, 34, 36)
DEFAULT_MAXIMUM_POLYPHONY = 6
DEFAULT_ARTIFACTS = Path("artifacts/guitar_midi_polyphonic_v2_2_0")


def _maximum_polyphony(notes: list[NoteInterval]) -> int:
    points: list[tuple[float, int]] = []
    for note in notes:
        points.append((note.start_s, 1))
        points.append((note.end_s, -1))
    active = 0
    maximum = 0
    for _, delta in sorted(points, key=lambda item: (item[0], item[1])):
        active += delta
        maximum = max(maximum, active)
    return maximum


def _causal_frame(
    waveform: np.ndarray,
    end_sample: int,
    frame_samples: int,
) -> np.ndarray:
    end = min(max(int(end_sample), 0), len(waveform))
    start = max(0, end - frame_samples)
    frame = np.zeros(frame_samples, np.float64)
    values = np.asarray(waveform[start:end], np.float64)
    if len(values):
        frame[-len(values):] = values
    return frame


def _pitch_scores(
    waveform: np.ndarray,
    end_sample: int,
    sample_rate: int,
    midi_min: int,
    midi_max: int,
) -> tuple[np.ndarray, np.ndarray]:
    frame = _causal_frame(
        waveform, end_sample, ANALYSIS_WINDOW_SAMPLES,
    )
    frame -= float(np.mean(frame))
    magnitude = np.abs(np.fft.rfft(
        frame * np.hanning(ANALYSIS_WINDOW_SAMPLES),
        n=SPECTRAL_FFT_SAMPLES,
    ))
    hz_per_bin = sample_rate / float(SPECTRAL_FFT_SAMPLES)
    usable = magnitude[
        max(1, int(40.0 / hz_per_bin)):
        min(len(magnitude), int(5000.0 / hz_per_bin) + 1)
    ]
    noise = max(float(np.median(usable)) if len(usable) else 0.0, 1e-12)
    scores: list[float] = []
    for midi in range(midi_min, midi_max + 1):
        frequency = 440.0 * 2.0 ** ((midi - 69) / 12.0)
        center = int(round(frequency / hz_per_bin))
        radius = max(
            1,
            int(math.ceil(
                frequency * (2.0 ** (35.0 / 1200.0) - 1.0) / hz_per_bin
            )),
        )
        low = max(0, center - radius)
        high = min(len(magnitude), center + radius + 1)
        scores.append(
            float(np.max(magnitude[low:high])) if high > low else 0.0
        )
    values = np.asarray(scores, np.float64)
    return values, values / noise


def _robust_threshold(values: np.ndarray, floor: float) -> float:
    finite = np.asarray(values[np.isfinite(values)], np.float64)
    if not len(finite):
        return float(floor)
    median = float(np.median(finite))
    mad = float(np.median(np.abs(finite - median)))
    return max(
        float(floor),
        median + 4.0 * 1.4826 * mad,
        float(np.percentile(finite, 90)),
    )


def _fallback_attack_hops(
    waveform: np.ndarray,
    sample_rate: int,
    hop_samples: int,
) -> tuple[list[int], np.ndarray]:
    frame_count = int(math.ceil(len(waveform) / float(hop_samples)))
    if frame_count == 0:
        return [], np.zeros(0, np.float64)
    rms = np.zeros(frame_count, np.float64)
    flux = np.zeros(frame_count, np.float64)
    previous_spectrum = np.zeros(ATTACK_WINDOW_SAMPLES // 2 + 1, np.float64)
    attack_window = np.hanning(ATTACK_WINDOW_SAMPLES)
    for index in range(frame_count):
        start = index * hop_samples
        hop = np.asarray(
            waveform[start:min(start + hop_samples, len(waveform))],
            np.float64,
        )
        rms[index] = (
            float(np.sqrt(np.mean(hop * hop))) if len(hop) else 0.0
        )
        frame = _causal_frame(
            waveform, (index + 1) * hop_samples, ATTACK_WINDOW_SAMPLES,
        )
        spectrum = np.abs(np.fft.rfft(frame * attack_window))
        total = float(np.sum(spectrum))
        if total > 0.0:
            spectrum /= total
        flux[index] = float(np.sum(np.maximum(
            spectrum - previous_spectrum, 0.0,
        )))
        previous_spectrum = spectrum

    baseline = np.zeros(frame_count, np.float64)
    for index in range(frame_count):
        start = max(0, index - 8)
        baseline[index] = float(np.median(rms[start:index])) if index else 0.0
    rise = np.maximum(rms - baseline, 0.0)
    rise_threshold = _robust_threshold(rise, 1e-5)
    flux_threshold = _robust_threshold(flux, 0.025)
    rms_floor = max(
        1e-5,
        3.0 * float(np.percentile(rms, 10)) if len(rms) else 0.0,
    )
    strengths = np.maximum(
        rise / rise_threshold,
        flux / flux_threshold,
    )
    rising_or_stable = rms >= 0.90 * baseline
    triggered = np.flatnonzero(
        (rms >= rms_floor)
        & (
            (rise >= rise_threshold)
            | ((flux >= flux_threshold) & rising_or_stable)
        )
    )

    # Keep the strongest trigger in each short transient cluster.  A second
    # temporal grouping later combines repeated detections of the same pitch.
    attacks: list[int] = []
    for raw_index in triggered:
        index = int(raw_index)
        if attacks and index - attacks[-1] <= 3:
            if strengths[index] > strengths[attacks[-1]]:
                attacks[-1] = index
            continue
        attacks.append(index)
    return attacks, strengths


def _product_attack_hops(
    waveform: np.ndarray,
    sample_rate: int,
    hop_samples: int,
    metadata: Mapping[str, object],
) -> tuple[list[int], np.ndarray, dict[str, object]]:
    """Replay the exact causal onset policy used by WAV and live products."""
    policy = PolyphonicAudioEvidencePolicy.from_metadata(
        sample_rate,
        hop_samples,
        metadata,
        calibration_s=1.0,
    )
    priming_hops = policy.prime_silence()
    frame_count = int(math.ceil(len(waveform) / float(hop_samples)))
    strengths = np.zeros(frame_count, np.float64)
    attacks: list[int] = []
    for frame_index in range(frame_count):
        start = frame_index * hop_samples
        hop = np.zeros(hop_samples, np.float32)
        part = np.asarray(
            waveform[start:start + hop_samples], np.float32,
        )
        hop[:len(part)] = part
        evidence = policy.process(hop)
        strengths[frame_index] = float(evidence.onset.confidence)
        if evidence.onset.is_onset:
            attacks.append(frame_index)
    diagnostics = policy.diagnostics()
    diagnostics.update({
        "policy": (
            "product_polyphonic_audio_evidence_from_bundle_metadata"
        ),
        "silent_priming_hops": priming_hops,
        "real_audio_hops": frame_count,
        "onset_hops": len(attacks),
        "label_leakage": False,
    })
    return attacks, strengths, diagnostics


def _midi_pitch_overlaps(
    notes: list[NoteInterval],
    pitch: int,
    start_s: float,
    end_s: float,
) -> bool:
    return any(
        note.pitch == pitch
        and note.end_s >= start_s - MIDI_OVERLAP_TOLERANCE_S
        and note.start_s <= end_s + MIDI_OVERLAP_TOLERANCE_S
        for note in notes
    )


def _active_midi_pitches(
    notes: list[NoteInterval],
    time_s: float,
) -> list[int]:
    return sorted({
        int(note.pitch)
        for note in notes
        if note.end_s >= time_s - MIDI_OVERLAP_TOLERANCE_S
        and note.start_s <= time_s + MIDI_OVERLAP_TOLERANCE_S
    })


def _review_score(
    spectral_ratio: float,
    supported_probes: int,
    spectral_snr_median: float,
    attack_strength: float,
) -> tuple[float, dict[str, float]]:
    stability = supported_probes / float(len(POST_ATTACK_PROBE_HOPS))
    ratio_component = float(np.clip(spectral_ratio, 0.0, 1.0))
    snr_component = float(np.clip(
        spectral_snr_median / (2.0 * MINIMUM_SPECTRAL_SNR),
        0.0,
        1.0,
    ))
    attack_component = float(np.clip(attack_strength, 0.0, 1.0))
    components = {
        "stability": stability,
        "spectral_ratio": ratio_component,
        "spectral_snr": snr_component,
        "attack_confidence": attack_component,
    }
    score = (
        0.40 * stability
        + 0.35 * ratio_component
        + 0.15 * snr_component
        + 0.10 * attack_component
    )
    return float(score), components


def _probable_harmonic(
    pitch: int,
    candidate_ratio: float,
    ratios: np.ndarray,
    supported_probes: np.ndarray,
    notes: list[NoteInterval],
    start_s: float,
    end_s: float,
    midi_min: int,
) -> tuple[bool, int | None]:
    for interval in HARMONIC_INTERVALS:
        lower = pitch - interval
        lower_index = lower - midi_min
        if lower_index < 0 or lower_index >= len(ratios):
            continue
        lower_supported = int(supported_probes[lower_index])
        lower_ratio = float(ratios[lower_index])
        lower_in_midi = _midi_pitch_overlaps(
            notes, lower, start_s, end_s,
        )
        lower_is_candidate = (
            lower_supported >= MINIMUM_SUPPORTED_PROBES
            and lower_ratio >= max(0.12, 0.45 * candidate_ratio)
        )
        if (
            (lower_in_midi or lower_is_candidate)
            and lower_supported >= 2
            and lower_ratio >= max(0.10, 0.30 * candidate_ratio)
        ):
            return True, lower
    return False, None


def _group_candidates(
    candidates: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    grouped: list[dict[str, Any]] = []
    for candidate in sorted(
        candidates, key=lambda row: (int(row["pitch"]), float(row["onset_s"])),
    ):
        previous = next(
            (
                row for row in reversed(grouped)
                if int(row["pitch"]) == int(candidate["pitch"])
            ),
            None,
        )
        if (
            previous is not None
            and float(candidate["onset_s"]) - float(previous["last_detection_s"])
            <= TEMPORAL_GROUPING_S
        ):
            previous["last_detection_s"] = float(candidate["onset_s"])
            previous["grouped_detections"] = (
                int(previous["grouped_detections"]) + 1
            )
            previous["spectral_support_ratio"] = max(
                float(previous["spectral_support_ratio"]),
                float(candidate["spectral_support_ratio"]),
            )
            previous["supported_probes"] = max(
                int(previous["supported_probes"]),
                int(candidate["supported_probes"]),
            )
            previous["attack_strength"] = max(
                float(previous["attack_strength"]),
                float(candidate["attack_strength"]),
            )
            previous["last_probe_s"] = max(
                float(previous["last_probe_s"]),
                float(candidate["last_probe_s"]),
            )
            if (
                float(candidate["review_score"])
                > float(previous["review_score"])
            ):
                previous["review_score"] = float(candidate["review_score"])
                previous["review_score_components"] = dict(
                    candidate["review_score_components"]
                )
            previous["stability_ratio"] = max(
                float(previous["stability_ratio"]),
                float(candidate["stability_ratio"]),
            )
            previous["raw_candidate_ids"].extend(
                str(value) for value in candidate["raw_candidate_ids"]
            )
            previous["raw_candidate_ids"] = sorted(set(
                previous["raw_candidate_ids"]
            ))
            continue
        grouped.append({
            **candidate,
            "last_detection_s": float(candidate["onset_s"]),
            "grouped_detections": 1,
        })
    for row in grouped:
        row["support_duration_ms"] = 1000.0 * (
            float(row.pop("last_probe_s")) - float(row["onset_s"])
        )
        row.pop("last_detection_s", None)
    return sorted(grouped, key=lambda row: (
        float(row["onset_s"]), int(row["pitch"])
    ))


def find_likely_missing_candidates(
    waveform: np.ndarray,
    sample_rate: int,
    notes: list[NoteInterval],
    hop_samples: int | None = None,
    midi_min: int | None = None,
    midi_max: int | None = None,
    maximum_polyphony: int | None = None,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, Any]:
    """Propose attack-aligned durable WAV pitches absent from active MIDI.

    This is deliberately an offline diagnostic.  It confirms candidates over
    post-attack frames and must not be interpreted as annotation-derived
    recall or as ground truth.
    """
    mono = np.asarray(waveform, np.float32).reshape(-1)
    if metadata is not None:
        metadata_sample_rate = int(metadata["sample_rate"])
        if int(sample_rate) != metadata_sample_rate:
            raise ValueError(
                "Product attack replay requires audio resampled to metadata "
                f"sample_rate={metadata_sample_rate}, got {sample_rate}."
            )
        resolved_hop = int(metadata["hop_samples"])
        if hop_samples is not None and int(hop_samples) != resolved_hop:
            raise ValueError(
                "Explicit hop_samples does not match bundle metadata."
            )
        resolved_midi_min = int(metadata.get(
            "min_pitch", DEFAULT_MIDI_MIN,
        ))
        resolved_midi_max = int(metadata.get(
            "max_pitch", DEFAULT_MIDI_MAX,
        ))
        resolved_maximum_polyphony = int(metadata.get(
            "maximum_polyphony", DEFAULT_MAXIMUM_POLYPHONY,
        ))
        if midi_min is not None and int(midi_min) != resolved_midi_min:
            raise ValueError("Explicit midi_min does not match bundle metadata.")
        if midi_max is not None and int(midi_max) != resolved_midi_max:
            raise ValueError("Explicit midi_max does not match bundle metadata.")
        if (
            maximum_polyphony is not None
            and int(maximum_polyphony) != resolved_maximum_polyphony
        ):
            raise ValueError(
                "Explicit maximum_polyphony does not match bundle metadata."
            )
        attacks, attack_strengths, attack_diagnostics = _product_attack_hops(
            mono,
            metadata_sample_rate,
            resolved_hop,
            metadata,
        )
        attack_source = (
            "product_polyphonic_audio_evidence_from_bundle_metadata"
        )
    else:
        resolved_hop = int(hop_samples or DEFAULT_HOP_SAMPLES)
        resolved_midi_min = int(
            DEFAULT_MIDI_MIN if midi_min is None else midi_min
        )
        resolved_midi_max = int(
            DEFAULT_MIDI_MAX if midi_max is None else midi_max
        )
        resolved_maximum_polyphony = int(
            DEFAULT_MAXIMUM_POLYPHONY
            if maximum_polyphony is None
            else maximum_polyphony
        )
        attacks, attack_strengths = _fallback_attack_hops(
            mono, int(sample_rate), resolved_hop,
        )
        attack_source = "synthetic_test_fallback_adaptive_rms_flux"
        attack_diagnostics = {
            "policy": attack_source,
            "onset_hops": len(attacks),
            "label_leakage": False,
            "purpose": (
                "Deterministic fallback for isolated synthetic tests or "
                "callers without product metadata."
            ),
        }
    hop_samples = resolved_hop
    midi_min = resolved_midi_min
    midi_max = resolved_midi_max
    maximum_polyphony = resolved_maximum_polyphony
    if maximum_polyphony < 1:
        raise ValueError("maximum_polyphony must be positive.")
    raw_evidence: list[dict[str, Any]] = []
    review_detections: list[dict[str, Any]] = []
    pitch_count = midi_max - midi_min + 1

    for attack_hop in attacks:
        probe_rows: list[np.ndarray] = []
        snr_rows: list[np.ndarray] = []
        for offset in POST_ATTACK_PROBE_HOPS:
            end_sample = min(
                len(mono), (attack_hop + 1 + offset) * hop_samples,
            )
            scores, snr = _pitch_scores(
                mono, end_sample, sample_rate, midi_min, midi_max,
            )
            denominator = max(float(np.max(scores)), 1e-12)
            probe_rows.append(scores / denominator)
            snr_rows.append(snr)
        ratios_by_probe = np.stack(probe_rows)
        snr_by_probe = np.stack(snr_rows)
        supported = (
            (ratios_by_probe >= MINIMUM_SPECTRAL_RATIO)
            & (snr_by_probe >= MINIMUM_SPECTRAL_SNR)
        )
        supported_probes = np.sum(supported, axis=0)
        ratios = np.median(ratios_by_probe, axis=0)
        stable_ratios = np.percentile(ratios_by_probe, 20, axis=0)
        median_snr = np.median(snr_by_probe, axis=0)

        eligible = [
            index for index in range(pitch_count)
            if int(supported_probes[index]) >= MINIMUM_SUPPORTED_PROBES
        ]
        # Suppress adjacent-bin leakage: retain the strongest pitch within
        # each +/- one-semitone cluster before checking MIDI coverage.
        selected: list[int] = []
        for index in sorted(
            eligible,
            key=lambda value: (
                float(ratios[value]), int(supported_probes[value])
            ),
            reverse=True,
        ):
            if any(abs(index - other) <= 1 for other in selected):
                continue
            selected.append(index)

        onset_s = (attack_hop + 1) * hop_samples / float(sample_rate)
        last_probe_s = min(
            len(mono) / float(sample_rate),
            (
                attack_hop + 1 + max(POST_ATTACK_PROBE_HOPS)
            ) * hop_samples / float(sample_rate),
        )
        active_midi_pitches = _active_midi_pitches(notes, onset_s)
        available_review_slots = max(
            0, maximum_polyphony - len(active_midi_pitches)
        )
        selected_set = set(selected)
        records_by_index: dict[int, dict[str, Any]] = {}
        attack_strength = float(attack_strengths[attack_hop])
        for index in sorted(eligible):
            pitch = midi_min + index
            review_score, score_components = _review_score(
                float(ratios[index]),
                int(supported_probes[index]),
                float(median_snr[index]),
                attack_strength,
            )
            record: dict[str, Any] = {
                "candidate_id": f"hop-{attack_hop}-midi-{pitch}",
                "attack_hop": attack_hop,
                "onset_s": onset_s,
                "last_probe_s": last_probe_s,
                "pitch": pitch,
                "spectral_support_ratio": float(ratios[index]),
                "stable_spectral_ratio_p20": float(
                    stable_ratios[index]
                ),
                "spectral_snr_median": float(median_snr[index]),
                "supported_probes": int(supported_probes[index]),
                "total_probes": len(POST_ATTACK_PROBE_HOPS),
                "stability_ratio": (
                    int(supported_probes[index])
                    / float(len(POST_ATTACK_PROBE_HOPS))
                ),
                "attack_strength": attack_strength,
                "review_score": review_score,
                "review_score_components": score_components,
                "active_midi_pitches": active_midi_pitches,
                "active_midi_polyphony": len(active_midi_pitches),
                "maximum_polyphony": maximum_polyphony,
                "available_review_slots": available_review_slots,
                "adjacent_peak_selected": index in selected_set,
                "probable_fundamental_pitch": None,
                "review_eligible_before_budget": False,
                "selected_for_review": False,
                "review_rank_at_attack": None,
                "disposition": (
                    "pending"
                    if index in selected_set
                    else "adjacent_pitch_suppressed"
                ),
            }
            raw_evidence.append(record)
            records_by_index[index] = record

        review_pool: list[dict[str, Any]] = []
        for index in selected:
            record = records_by_index[index]
            pitch = int(record["pitch"])
            if pitch in active_midi_pitches:
                record["disposition"] = "covered_by_active_midi"
                continue
            is_harmonic, lower_pitch = _probable_harmonic(
                pitch,
                float(ratios[index]),
                ratios,
                supported_probes,
                notes,
                onset_s,
                last_probe_s,
                midi_min,
            )
            if is_harmonic:
                record["disposition"] = "probable_harmonic"
                record["probable_fundamental_pitch"] = lower_pitch
                continue
            stable_for_review = (
                int(record["supported_probes"])
                >= REVIEW_MINIMUM_SUPPORTED_PROBES
                and float(record["spectral_support_ratio"])
                >= REVIEW_MINIMUM_SPECTRAL_RATIO
            )
            if not stable_for_review:
                record["disposition"] = (
                    "secondary_insufficient_review_stability"
                )
                continue
            record["review_eligible_before_budget"] = True
            review_pool.append(record)

        review_pool.sort(
            key=lambda row: (
                float(row["review_score"]),
                float(row["stable_spectral_ratio_p20"]),
                -int(row["pitch"]),
            ),
            reverse=True,
        )
        for rank, record in enumerate(review_pool, start=1):
            record["review_rank_at_attack"] = rank
            if rank > available_review_slots:
                record["disposition"] = "polyphony_budget_exceeded"
                continue
            record["disposition"] = "review_selected"
            record["selected_for_review"] = True
            review_detections.append({
                "pitch": int(record["pitch"]),
                "onset_s": float(record["onset_s"]),
                "last_probe_s": float(record["last_probe_s"]),
                "spectral_support_ratio": float(
                    record["spectral_support_ratio"]
                ),
                "stable_spectral_ratio_p20": float(
                    record["stable_spectral_ratio_p20"]
                ),
                "spectral_snr_median": float(
                    record["spectral_snr_median"]
                ),
                "supported_probes": int(record["supported_probes"]),
                "stability_ratio": float(record["stability_ratio"]),
                "attack_strength": float(record["attack_strength"]),
                "review_score": float(record["review_score"]),
                "review_score_components": dict(
                    record["review_score_components"]
                ),
                "active_midi_pitches": list(
                    record["active_midi_pitches"]
                ),
                "available_review_slots": int(
                    record["available_review_slots"]
                ),
                "raw_candidate_ids": [str(record["candidate_id"])],
            })

    grouped = _group_candidates(review_detections)
    disposition_counts = Counter(
        str(row["disposition"]) for row in raw_evidence
    )
    harmonic_examples = [
        {
            "candidate_id": row["candidate_id"],
            "pitch": row["pitch"],
            "onset_s": row["onset_s"],
            "probable_fundamental_pitch": (
                row["probable_fundamental_pitch"]
            ),
            "spectral_support_ratio": row["spectral_support_ratio"],
            "review_score": row["review_score"],
        }
        for row in raw_evidence
        if row["disposition"] == "probable_harmonic"
    ][:20]
    review_eligible_before_budget = (
        disposition_counts["review_selected"]
        + disposition_counts["polyphony_budget_exceeded"]
    )
    counts_by_level = {
        "attacks": len(attacks),
        "raw_spectral_pitch_detections": len(raw_evidence),
        "adjacent_pitch_suppressed": disposition_counts[
            "adjacent_pitch_suppressed"
        ],
        "peak_detections_after_adjacent_suppression": (
            len(raw_evidence)
            - disposition_counts["adjacent_pitch_suppressed"]
        ),
        "covered_by_active_midi": disposition_counts[
            "covered_by_active_midi"
        ],
        "probable_harmonic": disposition_counts["probable_harmonic"],
        "secondary_insufficient_review_stability": disposition_counts[
            "secondary_insufficient_review_stability"
        ],
        "review_eligible_before_polyphony_budget": (
            review_eligible_before_budget
        ),
        "review_rejected_by_polyphony_budget": disposition_counts[
            "polyphony_budget_exceeded"
        ],
        "review_selected_detections": disposition_counts[
            "review_selected"
        ],
        "review_grouped_candidates": len(grouped),
    }
    return {
        "count": len(grouped),
        "count_semantics": (
            "Temporally grouped robust review candidates after MIDI, "
            "harmonic, stability, and maximum-polyphony controls."
        ),
        "examples": grouped[:20],
        "review_candidates": grouped,
        "raw_candidates": raw_evidence,
        "raw_candidate_examples": raw_evidence[:20],
        "counts_by_level": counts_by_level,
        "disposition_counts": dict(sorted(disposition_counts.items())),
        "attack_source": attack_source,
        "attack_count": len(attacks),
        "attack_diagnostics": attack_diagnostics,
        "sample_rate": int(sample_rate),
        "hop_samples": hop_samples,
        "maximum_polyphony": maximum_polyphony,
        "raw_candidate_detections": len(raw_evidence),
        "covered_by_active_midi": disposition_counts[
            "covered_by_active_midi"
        ],
        "probable_harmonics_filtered": disposition_counts[
            "probable_harmonic"
        ],
        "probable_harmonic_examples": harmonic_examples,
        "policy": {
            "kind": (
                "offline_attack_aligned_durable_spectral_candidate_search"
            ),
            "attack_detection": attack_source,
            "midi_range": [midi_min, midi_max],
            "analysis_window_samples": ANALYSIS_WINDOW_SAMPLES,
            "zero_padded_spectral_fft_samples": SPECTRAL_FFT_SAMPLES,
            "hop_samples": hop_samples,
            "post_attack_probe_hops": list(POST_ATTACK_PROBE_HOPS),
            "minimum_supported_probes": MINIMUM_SUPPORTED_PROBES,
            "minimum_spectral_ratio": MINIMUM_SPECTRAL_RATIO,
            "minimum_spectral_snr": MINIMUM_SPECTRAL_SNR,
            "review_minimum_supported_probes": (
                REVIEW_MINIMUM_SUPPORTED_PROBES
            ),
            "review_minimum_spectral_ratio": (
                REVIEW_MINIMUM_SPECTRAL_RATIO
            ),
            "review_score": (
                "0.40*probe_stability + 0.35*median_spectral_ratio + "
                "0.15*clipped_median_snr/(2*minimum_snr) + "
                "0.10*attack_confidence"
            ),
            "review_score_usage": (
                "Ranking within one attack only; it is not thresholded to "
                "reach a target candidate count."
            ),
            "review_stability_rationale": (
                "The review tier requires support in at least 4 of 5 fixed "
                "post-attack probes and a median ratio >= 0.35; the looser "
                "3-of-5 tier remains fully available as raw evidence."
            ),
            "maximum_polyphony": maximum_polyphony,
            "polyphony_budget": (
                "maximum_polyphony minus distinct MIDI pitches active within "
                "the overlap tolerance at each product attack"
            ),
            "threshold_origin": (
                "Structural two-tier policy validated by synthetic tests; "
                "not selected on the audited recording."
            ),
            "midi_overlap_tolerance_ms": (
                1000.0 * MIDI_OVERLAP_TOLERANCE_S
            ),
            "temporal_grouping_ms": 1000.0 * TEMPORAL_GROUPING_S,
            "probable_harmonic_intervals_semitones": list(
                HARMONIC_INTERVALS
            ),
        },
        "interpretation": (
            "Only review_candidates are the compact review queue. "
            "raw_candidates preserve every durable spectral pitch and its "
            "disposition for audit; they are not all likely missing notes. "
            "Neither level is ground truth or a recall measurement."
        ),
        "ground_truth_claimed": False,
        "recall_claimed": False,
        "limitations": [
            (
                "The product onset detector can miss weak attacks; candidates "
                "are searched only at the attacks it emits."
            ),
            (
                "Post-attack spectral durability uses offline confirmation "
                "and is not a proposed live decoder delay."
            ),
            (
                "Resonance, tuning, true octave voicings, noise, and spectral "
                "leakage can create false candidates or filtered real notes."
            ),
            (
                "MIDI overlap uses a 50 ms tolerance and cannot prove that an "
                "event was intentionally played."
            ),
            (
                "The maximum-polyphony budget can hide a real missing note if "
                "the MIDI contains a stale or otherwise false active note."
            ),
            (
                "Attack parity assumes the WAV already represents the same "
                "capture-gain domain supplied to the product; an unknown live "
                "gain cannot be reconstructed from MIDI."
            ),
        ],
        "latency_impact": (
            "Offline diagnostic only; zero added live algorithmic latency."
        ),
    }


def _resample_audio(
    waveform: np.ndarray,
    source_rate: int,
    target_rate: int,
) -> np.ndarray:
    mono = np.asarray(waveform, np.float32).reshape(-1)
    if int(source_rate) == int(target_rate):
        return mono
    divisor = math.gcd(int(source_rate), int(target_rate))
    return resample_poly(
        mono,
        int(target_rate) // divisor,
        int(source_rate) // divisor,
    ).astype(np.float32)


def diagnose(
    wav_path: Path,
    midi_path: Path,
    artifacts: Path = DEFAULT_ARTIFACTS,
) -> dict[str, Any]:
    metadata_path = artifacts / "metadata.json"
    metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    product_sample_rate = int(metadata["sample_rate"])
    product_hop_samples = int(metadata["hop_samples"])
    waveform, source_sample_rate = sf.read(
        wav_path,
        dtype="float32",
        always_2d=True,
    )
    source_mono = np.mean(waveform, axis=1, dtype=np.float32)
    mono = _resample_audio(
        source_mono,
        int(source_sample_rate),
        product_sample_rate,
    )
    notes = [
        NoteInterval(note.pitch_midi, note.start_s, note.end_s)
        for note in parse_midi_notes(midi_path)
    ]
    spectral, ratios, _ = spectral_inverse_diagnostics(
        mono,
        product_sample_rate,
        product_hop_samples,
        [],
        notes,
        [],
    )
    durations_ms = np.asarray(
        [1000.0 * (note.end_s - note.start_s) for note in notes],
        np.float64,
    )
    pitch_counts = Counter(note.pitch for note in notes)
    duration_s = len(mono) / float(product_sample_rate)
    ratio_values = np.asarray(ratios, np.float64)
    likely_missing = find_likely_missing_candidates(
        mono,
        product_sample_rate,
        notes,
        metadata=metadata,
    )
    return {
        "purpose": (
            "Annotation-free generated-MIDI to source-WAV support audit plus "
            "source-WAV to likely-missing-MIDI candidate search."
        ),
        "inputs": {
            "wav": str(wav_path),
            "midi": str(midi_path),
            "artifacts": str(artifacts),
            "metadata": str(metadata_path),
        },
        "contract": {
            "source_sample_rate": int(source_sample_rate),
            "sample_rate": product_sample_rate,
            "hop_samples": product_hop_samples,
            "resampled_to_product_rate": bool(
                int(source_sample_rate) != product_sample_rate
            ),
            "duration_s": duration_s,
            "attack_source": likely_missing["attack_source"],
            "attack_count": likely_missing["attack_count"],
            "aligned_annotations_available": False,
            "locked_test_used": False,
        },
        "midi": {
            "notes": len(notes),
            "notes_per_minute": (
                60.0 * len(notes) / duration_s if duration_s else 0.0
            ),
            "unique_pitches": len(pitch_counts),
            "pitch_counts": {
                str(pitch): count
                for pitch, count in sorted(pitch_counts.items())
            },
            "maximum_polyphony": _maximum_polyphony(notes),
            "duration_ms": {
                "median": (
                    float(np.median(durations_ms))
                    if len(durations_ms) else 0.0
                ),
                "p10": (
                    float(np.percentile(durations_ms, 10))
                    if len(durations_ms) else 0.0
                ),
                "shorter_than_50_ms": int(np.count_nonzero(
                    durations_ms < 50.0
                )),
            },
        },
        "spectral_inverse": spectral,
        "likely_missing_notes": likely_missing,
        "decision_support": {
            "spectrally_supported_ratio_ge_0_25": int(np.count_nonzero(
                ratio_values >= 0.25
            )),
            "weak_ratio_0_10_to_0_25": int(np.count_nonzero(
                (ratio_values >= 0.10) & (ratio_values < 0.25)
            )),
            "unsupported_ratio_lt_0_10": int(np.count_nonzero(
                ratio_values < 0.10
            )),
            "review_candidate_count": likely_missing["count"],
            "raw_spectral_candidate_count": (
                likely_missing["raw_candidate_detections"]
            ),
            "candidate_counts_by_level": (
                likely_missing["counts_by_level"]
            ),
            "probable_harmonics_filtered": (
                likely_missing["probable_harmonics_filtered"]
            ),
            "raw_candidates_are_not_all_likely_missing": True,
            "candidates_are_hypotheses_not_ground_truth": True,
            "recall_is_not_claimed_without_aligned_annotations": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--wav", type=Path, required=True)
    parser.add_argument("--midi", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--artifacts",
        type=Path,
        default=DEFAULT_ARTIFACTS,
        help="Bundle produit contenant metadata.json.",
    )
    args = parser.parse_args()
    report = diagnose(args.wav, args.midi, args.artifacts)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "output": str(args.output),
        "notes": report["midi"]["notes"],
        "notes_per_minute": report["midi"]["notes_per_minute"],
        **report["decision_support"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
