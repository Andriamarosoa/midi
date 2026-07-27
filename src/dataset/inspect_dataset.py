#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    args = parser.parse_args()

    data = np.load(args.npz)

    required = [
        "audio", "visible_window", "prediction_age_ms",
        "pitch_midi", "fundamental_hz", "onset", "attack_phase",
        "release_phase", "active", "harmonic_present",
        "harmonic_amplitude", "harmonic_offset_cents",
    ]

    missing = [key for key in required if key not in data.files]
    if missing:
        raise SystemExit(f"Colonnes manquantes: {missing}")

    audio = data["audio"]
    onset = data["onset"] > 0.5
    attack = data["attack_phase"] > 0.5
    release = data["release_phase"] > 0.5
    active = data["active"] > 0.5

    print("=" * 50)
    print("DATASET REPORT")
    print("=" * 50)
    print(f"Examples       : {len(audio)}")
    print(f"Audio shape    : {audio.shape}")
    print(f"Onset          : {int(onset.sum())}")
    print(f"Attack phase   : {int(attack.sum())}")
    print(f"Sustain        : {int((active & ~attack).sum())}")
    print(f"Release        : {int(release.sum())}")
    print(f"Silence        : {int((~active & ~release).sum())}")
    print("")

    print("Visible windows")
    values, counts = np.unique(data["visible_window"], return_counts=True)
    for value, count in zip(values, counts):
        print(f"  {int(value):4d}: {int(count)}")

    print("")
    print("Pitch distribution")
    pitches, pitch_counts = np.unique(data["pitch_midi"], return_counts=True)
    for pitch, count in zip(pitches, pitch_counts):
        print(f"  {int(pitch):3d}: {int(count)}")

    print("")
    invalid = 0
    invalid += int(np.isnan(audio).any())
    invalid += int(np.isinf(audio).any())
    invalid += int(np.any((onset.astype(int) + release.astype(int)) > 1))
    invalid += int(np.any((release) & (active)))
    invalid += int(np.any((onset) & (~active)))

    silent_energy = np.sqrt(np.mean(audio * audio, axis=1) + 1e-12)
    print(f"RMS median     : {float(np.median(silent_energy)):.8f}")
    print(f"RMS p95        : {float(np.percentile(silent_energy, 95)):.8f}")
    print(f"Invalid checks : {invalid}")
    print("Dataset OK" if invalid == 0 else "Dataset à vérifier")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
