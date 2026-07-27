from __future__ import annotations

import argparse
from pathlib import Path
import numpy as np

from src.v3.config import load_config
from src.v3.data import active_pitch_indices, load_arrays


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate stratified grouped fold assignments for future multi-song CV.")
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--folds", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("runs/v3/folds.npz"))
    args = parser.parse_args()

    config = load_config(args.config)
    arrays = load_arrays(config.data.npz)
    candidates = active_pitch_indices(arrays, config.data.min_pitch, config.data.max_pitch)
    pitch = arrays["pitch_midi"].astype(np.int32)
    note_id = arrays["note_id"].astype(np.int64)
    rng = np.random.default_rng(config.data.seed)

    groups_by_fold = [set() for _ in range(args.folds)]
    for midi in sorted(np.unique(pitch[candidates])):
        groups = np.unique(note_id[candidates[pitch[candidates] == midi]])
        rng.shuffle(groups)
        for index, group in enumerate(groups):
            groups_by_fold[index % args.folds].add(int(group))

    args.output.parent.mkdir(parents=True, exist_ok=True)
    payload = {f"fold_{i}": np.array(sorted(groups), dtype=np.int64) for i, groups in enumerate(groups_by_fold)}
    np.savez(args.output, **payload)
    print(f"Folds saved: {args.output}")
    for i, groups in enumerate(groups_by_fold):
        print(f"  fold {i}: {len(groups)} note_ids")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
