#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from src.dataset.tf_dataset import DatasetConfig, make_tf_dataset, summarize_npz


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--npz", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=8)
    args = parser.parse_args()

    config = DatasetConfig(
        batch_size=args.batch_size,
        shuffle=False,
    )
    summarize_npz(args.npz, config)

    dataset = make_tf_dataset(args.npz, config)
    inputs, targets, weights = next(iter(dataset))

    print("Premier batch")
    print("  audio       :", inputs["audio"].shape)
    print("  time_mask   :", inputs["time_mask"].shape)
    print("  onset       :", targets["onset"].shape)
    print("  pitch       :", targets["pitch"].shape)
    print("  pitch weight:", weights["pitch"].numpy())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
