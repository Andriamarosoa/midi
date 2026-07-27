#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import random
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=Path("data/dataset/stream/splits.csv"))
    parser.add_argument("--train", type=float, default=0.70)
    parser.add_argument("--validation", type=float, default=0.15)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    if args.train <= 0 or args.validation < 0 or args.train + args.validation >= 1:
        parser.error("Ratios invalides")

    with args.manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))

    random.Random(args.seed).shuffle(rows)

    total = len(rows)
    train_end = round(total * args.train)
    val_end = train_end + round(total * args.validation)

    for index, row in enumerate(rows):
        if index < train_end:
            row["split"] = "train"
        elif index < val_end:
            row["split"] = "validation"
        else:
            row["split"] = "test"

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = list(rows[0].keys()) if rows else ["source_id", "npz_path", "split"]

    with args.output.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"train      : {sum(r['split'] == 'train' for r in rows)}")
    print(f"validation : {sum(r['split'] == 'validation' for r in rows)}")
    print(f"test       : {sum(r['split'] == 'test' for r in rows)}")
    print(f"sortie     : {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
