#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np
import matplotlib.pyplot as plt


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--index", type=int, required=True)
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()

    data = np.load(args.npz)
    index = args.index
    if index < 0 or index >= len(data["audio"]):
        raise SystemExit("Index hors limites")

    audio = data["audio"][index]
    visible = int(data["visible_window"][index])
    visible_audio = audio[-visible:]

    print(f"Sample #{index}")
    print(f"pitch_midi      : {int(data['pitch_midi'][index])}")
    print(f"fundamental_hz  : {float(data['fundamental_hz'][index]):.3f}")
    print(f"visible_window  : {visible}")
    print(f"prediction_age  : {float(data['prediction_age_ms'][index]):.3f} ms")
    print(f"onset           : {float(data['onset'][index]):.0f}")
    print(f"attack_phase    : {float(data['attack_phase'][index]):.0f}")
    print(f"release_phase   : {float(data['release_phase'][index]):.0f}")
    print(f"active          : {float(data['active'][index]):.0f}")

    plt.figure(figsize=(10, 4))
    plt.plot(visible_audio)
    plt.title(f"Sample {index} - MIDI {int(data['pitch_midi'][index])}")
    plt.xlabel("Sample")
    plt.ylabel("Amplitude")
    plt.tight_layout()

    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        plt.savefig(args.output, dpi=150)
        print(f"Image: {args.output}")
    else:
        plt.show()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
