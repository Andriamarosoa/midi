#!/usr/bin/env python3
"""Reconstruct a WAV from a harmonic CSV using additive synthesis.

Supports both older harmonic CSV files and CSV files enriched with attack data.

Useful columns:
    note_id, start_s, end_s, measured_hz, amplitude, relative_db

Optional attack columns:
    annotation_start_s, detected_attack_time_s, attack_offset_ms,
    attack_duration_ms, attack_peak_dbfs, attack_rms_dbfs,
    attack_spectral_flux, attack_centroid_hz, attack_confidence

Example:
    python src/process/additive.py ^
        --csv data/processed/00_BN1-129-Eb_comp_hex.csv ^
        --output data/processed/diagnostics/00_BN1-129-Eb_comp_hex_additive.wav
"""

from __future__ import annotations

import argparse
import csv
import math
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import soundfile as sf


EPSILON = 1e-12


def safe_float(row: Dict[str, str], key: str, default: float) -> float:
    value = row.get(key, "")
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return default
    return parsed if math.isfinite(parsed) else default


def db_to_linear(db: float) -> float:
    return 10.0 ** (db / 20.0)


def load_rows(csv_path: Path) -> List[Dict[str, float]]:
    required = {
        "note_id",
        "start_s",
        "end_s",
        "measured_hz",
        "amplitude",
        "relative_db",
    }

    rows: List[Dict[str, float]] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        missing = required - set(reader.fieldnames or [])
        if missing:
            raise ValueError("Colonnes CSV manquantes : {}".format(sorted(missing)))

        for line_number, raw in enumerate(reader, start=2):
            try:
                note_id = int(float(raw["note_id"]))
                start_s = float(raw["start_s"])
                end_s = float(raw["end_s"])
                frequency_hz = float(raw["measured_hz"])
            except (TypeError, ValueError, KeyError) as exc:
                raise ValueError("Ligne CSV invalide : {}".format(line_number)) from exc

            if end_s <= start_s or frequency_hz <= 0:
                continue

            rows.append(
                {
                    "note_id": note_id,
                    "start_s": start_s,
                    "end_s": end_s,
                    "frequency_hz": frequency_hz,
                    "amplitude": max(0.0, safe_float(raw, "amplitude", 0.0)),
                    "relative_db": safe_float(raw, "relative_db", -120.0),
                    "annotation_start_s": safe_float(raw, "annotation_start_s", start_s),
                    "detected_attack_time_s": safe_float(
                        raw, "detected_attack_time_s", start_s
                    ),
                    "attack_offset_ms": safe_float(raw, "attack_offset_ms", 0.0),
                    "attack_duration_ms": max(
                        0.0, safe_float(raw, "attack_duration_ms", 5.0)
                    ),
                    "attack_peak_dbfs": safe_float(raw, "attack_peak_dbfs", -12.0),
                    "attack_rms_dbfs": safe_float(raw, "attack_rms_dbfs", -24.0),
                    "attack_spectral_flux": max(
                        0.0, safe_float(raw, "attack_spectral_flux", 0.0)
                    ),
                    "attack_centroid_hz": max(
                        0.0, safe_float(raw, "attack_centroid_hz", 0.0)
                    ),
                    "attack_confidence": float(
                        np.clip(safe_float(raw, "attack_confidence", 0.0), 0.0, 1.0)
                    ),
                }
            )

    if not rows:
        raise ValueError("Aucune harmonique exploitable dans le CSV.")
    return rows


def choose_note_attack(
    note_rows: List[Dict[str, float]],
    confidence_threshold: float,
    fallback_attack_ms: float,
) -> Dict[str, float]:
    first = note_rows[0]
    confidence = float(first["attack_confidence"])

    if confidence >= confidence_threshold:
        synthesis_start_s = float(first["detected_attack_time_s"])
        attack_ms = float(first["attack_duration_ms"])
        source = 1.0
    else:
        synthesis_start_s = float(first["annotation_start_s"])
        attack_ms = fallback_attack_ms
        source = 0.0

    # Never start before zero and do not move too far away from the annotation.
    annotation_start_s = float(first["annotation_start_s"])
    synthesis_start_s = max(
        0.0,
        min(
            synthesis_start_s,
            annotation_start_s + 0.100,
        ),
    )
    synthesis_start_s = max(
        synthesis_start_s,
        annotation_start_s - 0.100,
    )

    return {
        "start_s": synthesis_start_s,
        "attack_ms": max(0.5, attack_ms),
        "confidence": confidence,
        "source_detected": source,
        "peak_dbfs": float(first["attack_peak_dbfs"]),
        "rms_dbfs": float(first["attack_rms_dbfs"]),
        "flux": float(first["attack_spectral_flux"]),
        "centroid_hz": float(first["attack_centroid_hz"]),
    }


def make_note_envelope(
    sample_count: int,
    sample_rate: int,
    attack_ms: float,
    release_ms: float,
    decay_ratio: float,
) -> np.ndarray:
    envelope = np.ones(sample_count, dtype=np.float64)

    attack_samples = min(
        sample_count,
        max(1, int(round(sample_rate * attack_ms / 1000.0))),
    )
    release_samples = min(
        sample_count,
        max(1, int(round(sample_rate * release_ms / 1000.0))),
    )

    # Smooth attack, less abrupt than a straight line.
    attack_axis = np.linspace(0.0, 1.0, attack_samples, endpoint=False)
    envelope[:attack_samples] = np.sin(attack_axis * math.pi / 2.0) ** 2

    # Gentle decay during the sustain.
    if sample_count > attack_samples:
        decay = np.linspace(1.0, max(0.05, decay_ratio), sample_count - attack_samples)
        envelope[attack_samples:] *= decay

    # Smooth release.
    release_axis = np.linspace(1.0, 0.0, release_samples, endpoint=True)
    envelope[-release_samples:] *= np.sin(release_axis * math.pi / 2.0) ** 2
    return envelope


def note_gain_from_attack(
    peak_dbfs: float,
    rms_dbfs: float,
    use_attack_level: bool,
) -> float:
    if not use_attack_level:
        return 1.0

    peak = db_to_linear(float(np.clip(peak_dbfs, -80.0, 0.0)))
    rms = db_to_linear(float(np.clip(rms_dbfs, -80.0, 0.0)))

    # Peak preserves the transient; RMS stabilizes perceived loudness.
    combined = math.sqrt(max(peak, EPSILON) * max(rms, EPSILON))
    return float(np.clip(combined * 8.0, 0.08, 2.5))


def add_attack_transient(
    audio: np.ndarray,
    start_sample: int,
    sample_rate: int,
    attack_ms: float,
    flux: float,
    centroid_hz: float,
    gain: float,
    rng: np.random.Generator,
) -> None:
    if flux <= 0.0 or gain <= 0.0:
        return

    duration_ms = float(np.clip(attack_ms * 1.5, 3.0, 35.0))
    count = int(round(sample_rate * duration_ms / 1000.0))
    if count <= 1 or start_sample >= len(audio):
        return
    count = min(count, len(audio) - start_sample)

    noise = rng.standard_normal(count)
    spectrum = np.fft.rfft(noise)
    freqs = np.fft.rfftfreq(count, 1.0 / sample_rate)

    # Approximate attack brightness from spectral centroid.
    center = float(np.clip(centroid_hz, 200.0, sample_rate * 0.45))
    width = max(300.0, center * 0.75)
    spectral_shape = np.exp(-0.5 * ((freqs - center) / width) ** 2)
    shaped = np.fft.irfft(spectrum * spectral_shape, n=count)

    peak = float(np.max(np.abs(shaped)))
    if peak > EPSILON:
        shaped /= peak

    envelope = np.exp(-np.linspace(0.0, 7.0, count))
    flux_strength = float(np.tanh(flux / 50.0))
    transient_gain = gain * flux_strength * 0.10
    audio[start_sample:start_sample + count] += shaped * envelope * transient_gain


def synthesize(
    rows: List[Dict[str, float]],
    sample_rate: int,
    release_ms: float,
    fallback_attack_ms: float,
    confidence_threshold: float,
    gain_source: str,
    use_attack_level: bool,
    use_attack_noise: bool,
    decay_ratio: float,
    seed: int,
) -> Dict[str, object]:
    grouped: Dict[int, List[Dict[str, float]]] = defaultdict(list)
    for row in rows:
        grouped[int(row["note_id"])].append(row)

    latest_end = max(float(row["end_s"]) for row in rows)
    total_samples = int(math.ceil((latest_end + release_ms / 1000.0) * sample_rate))
    audio = np.zeros(total_samples, dtype=np.float64)
    rng = np.random.default_rng(seed)

    detected_count = 0
    fallback_count = 0

    for note_rows in grouped.values():
        note_rows.sort(key=lambda item: item["frequency_hz"])
        attack = choose_note_attack(
            note_rows,
            confidence_threshold=confidence_threshold,
            fallback_attack_ms=fallback_attack_ms,
        )

        if attack["source_detected"] > 0:
            detected_count += 1
        else:
            fallback_count += 1

        start_s = float(attack["start_s"])
        end_s = max(float(row["end_s"]) for row in note_rows)
        start_sample = max(0, int(round(start_s * sample_rate)))
        end_sample = min(total_samples, int(round(end_s * sample_rate)))
        sample_count = end_sample - start_sample
        if sample_count <= 1:
            continue

        note_envelope = make_note_envelope(
            sample_count,
            sample_rate,
            attack_ms=float(attack["attack_ms"]),
            release_ms=release_ms,
            decay_ratio=decay_ratio,
        )

        note_gain = note_gain_from_attack(
            float(attack["peak_dbfs"]),
            float(attack["rms_dbfs"]),
            use_attack_level=use_attack_level,
        )

        t = np.arange(sample_count, dtype=np.float64) / sample_rate
        note_audio = np.zeros(sample_count, dtype=np.float64)

        for row in note_rows:
            if gain_source == "relative-db":
                harmonic_gain = db_to_linear(float(row["relative_db"]))
            else:
                harmonic_gain = float(row["amplitude"])

            if harmonic_gain <= 0.0 or not math.isfinite(harmonic_gain):
                continue

            frequency_hz = float(row["frequency_hz"])
            phase = 0.0
            oscillator = np.sin(2.0 * math.pi * frequency_hz * t + phase)
            note_audio += harmonic_gain * oscillator

        # Avoid excessive note loudness when many harmonics are present.
        harmonic_count = max(1, len(note_rows))
        note_audio /= math.sqrt(harmonic_count)
        note_audio *= note_envelope * note_gain
        audio[start_sample:end_sample] += note_audio

        if use_attack_noise:
            add_attack_transient(
                audio,
                start_sample=start_sample,
                sample_rate=sample_rate,
                attack_ms=float(attack["attack_ms"]),
                flux=float(attack["flux"]),
                centroid_hz=float(attack["centroid_hz"]),
                gain=note_gain,
                rng=rng,
            )

    return {
        "audio": audio,
        "notes": len(grouped),
        "detected_attacks": detected_count,
        "fallback_attacks": fallback_count,
    }


def normalize_audio(audio: np.ndarray, target_peak: float) -> np.ndarray:
    peak = float(np.max(np.abs(audio)))
    if peak <= EPSILON:
        return audio
    return audio * (target_peak / peak)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reconstruit un WAV par synthèse additive depuis un CSV harmonique."
    )
    parser.add_argument("--csv", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--sample-rate", type=int, default=44100)
    parser.add_argument("--release-ms", type=float, default=30.0)
    parser.add_argument("--fallback-attack-ms", type=float, default=5.0)
    parser.add_argument("--attack-confidence-threshold", type=float, default=0.60)
    parser.add_argument(
        "--gain-source",
        choices=["amplitude", "relative-db"],
        default="relative-db",
    )
    parser.add_argument(
        "--no-attack-level",
        action="store_true",
        help="N'utilise pas attack_peak_dbfs/attack_rms_dbfs pour le niveau des notes.",
    )
    parser.add_argument(
        "--no-attack-noise",
        action="store_true",
        help="N'ajoute pas le transitoire basé sur flux/centroid.",
    )
    parser.add_argument(
        "--decay-ratio",
        type=float,
        default=0.35,
        help="Niveau relatif de fin de sustain avant le release.",
    )
    parser.add_argument("--target-peak", type=float, default=0.95)
    parser.add_argument("--no-normalize", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.sample_rate <= 0:
        parser.error("--sample-rate doit être positif")
    if not 0.0 <= args.attack_confidence_threshold <= 1.0:
        parser.error("--attack-confidence-threshold doit être dans [0, 1]")
    if not 0.0 < args.decay_ratio <= 1.0:
        parser.error("--decay-ratio doit être dans ]0, 1]")
    if not 0.0 < args.target_peak <= 1.0:
        parser.error("--target-peak doit être dans ]0, 1]")

    rows = load_rows(args.csv)
    result = synthesize(
        rows=rows,
        sample_rate=args.sample_rate,
        release_ms=max(0.0, args.release_ms),
        fallback_attack_ms=max(0.5, args.fallback_attack_ms),
        confidence_threshold=args.attack_confidence_threshold,
        gain_source=args.gain_source,
        use_attack_level=not args.no_attack_level,
        use_attack_noise=not args.no_attack_noise,
        decay_ratio=args.decay_ratio,
        seed=args.seed,
    )

    audio = result["audio"]
    if not args.no_normalize:
        audio = normalize_audio(audio, args.target_peak)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    sf.write(args.output, audio.astype(np.float32), args.sample_rate)

    print("Synthèse additive terminée")
    print("  harmoniques        : {}".format(len(rows)))
    print("  notes              : {}".format(result["notes"]))
    print("  attaques détectées : {}".format(result["detected_attacks"]))
    print("  replis annotation  : {}".format(result["fallback_attacks"]))
    print("  durée              : {:.3f} s".format(len(audio) / args.sample_rate))
    print("  sortie             : {}".format(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
