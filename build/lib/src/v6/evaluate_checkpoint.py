from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

from src.v5.cache import NPZRamCache
from src.v5.config import load_config
from src.v5.manifest import load_manifest, split_manifest
from src.v5.model import MaskedAveragePooling1D, ScaledTanh  # noqa: F401
from src.v5.train import predictions_by_name

from .dataloader import V6Sequence
from .dataset import GlobalSampleIndex
from .evaluate import generate_v6_reports, select_f1_threshold
from .train import concatenate_targets


def _sequence(cache: NPZRamCache, index: GlobalSampleIndex, cfg, gain: float):
    return V6Sequence(
        cache,
        index,
        cfg.train.batch_size,
        cfg.dataset.min_pitch,
        gain,
        cfg.dataset.seed,
        shuffle=False,
        activity_weights=np.ones(2, dtype=np.float32),
        onset_targets=cfg.model.onset_auxiliary,
        onset_weights=np.ones(2, dtype=np.float32),
        harmonic_targets=cfg.model.harmonic_auxiliary,
        harmonic_count=cfg.model.harmonic_count,
    )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Evaluate one V6 checkpoint with a validation-only gate threshold."
    )
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    args = parser.parse_args()

    import tensorflow as tf

    run_dir = args.run_dir.resolve()
    checkpoint = args.checkpoint
    if not checkpoint.is_absolute():
        checkpoint = run_dir / checkpoint
    checkpoint = checkpoint.resolve()
    output_dir = run_dir / "checkpoint_evaluations" / checkpoint.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    cfg = load_config(run_dir / "config.json")
    items = load_manifest(cfg.dataset.manifest)
    if cfg.dataset.include_datasets:
        requested = set(cfg.dataset.include_datasets)
        items = [item for item in items if item.dataset_id in requested]
    groups = split_manifest(
        items,
        cfg.dataset.train_players,
        cfg.dataset.validation_players,
        cfg.dataset.test_players,
    )

    caches = {
        name: NPZRamCache(groups[name], cfg.cache.validate_schema)
        for name in ("validation", "test")
    }
    for cache in caches.values():
        cache.load()
    indices = {
        name: GlobalSampleIndex(
            cache, cfg.dataset.min_pitch, cfg.dataset.max_pitch
        )
        for name, cache in caches.items()
    }
    gain = float(
        json.loads((run_dir / "normalization.json").read_text(encoding="utf-8"))[
            "gain"
        ]
    )
    sequences = {
        name: _sequence(cache, indices[name], cfg, gain)
        for name, cache in caches.items()
    }

    model = tf.keras.models.load_model(checkpoint, compile=False)
    validation_predictions = predictions_by_name(
        model,
        model.predict(
            sequences["validation"],
            workers=cfg.train.workers,
            use_multiprocessing=False,
            max_queue_size=2,
            verbose=1,
        ),
    )
    validation_targets = concatenate_targets(sequences["validation"])
    threshold, threshold_metrics = select_f1_threshold(
        validation_predictions["active"], validation_targets["active"]
    )
    (output_dir / "active_threshold.json").write_text(
        json.dumps(
            {
                "checkpoint": checkpoint.name,
                "threshold": threshold,
                "selected_on": "validation",
                "metrics": threshold_metrics,
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    onset_threshold = None
    if cfg.model.onset_auxiliary:
        onset_threshold, onset_threshold_metrics = select_f1_threshold(
            validation_predictions["onset"], validation_targets["onset"]
        )
        (output_dir / "onset_threshold.json").write_text(
            json.dumps(
                {
                    "checkpoint": checkpoint.name,
                    "threshold": onset_threshold,
                    "selected_on": "validation",
                    "metrics": onset_threshold_metrics,
                },
                indent=2,
            ),
            encoding="utf-8",
        )

    test_predictions = predictions_by_name(
        model,
        model.predict(
            sequences["test"],
            workers=cfg.train.workers,
            use_multiprocessing=False,
            max_queue_size=2,
            verbose=1,
        ),
    )
    test_targets = concatenate_targets(sequences["test"])
    metrics = generate_v6_reports(
        output_dir,
        test_predictions,
        test_targets,
        sequences["test"].metadata(),
        cfg.dataset.min_pitch,
        threshold,
        evaluated_checkpoint=checkpoint.name,
        harmonic_count=(
            cfg.model.harmonic_count if cfg.model.harmonic_auxiliary else None
        ),
        onset_threshold=onset_threshold,
    )
    result = {
        "checkpoint": checkpoint.name,
        "output_dir": str(output_dir),
        "threshold": threshold,
        "active": metrics["active"],
        "pitch_on_true_active": metrics["pitch_on_true_active"],
        "joint": metrics["joint"],
        "harmonics_on_true_active": metrics["harmonics_on_true_active"],
        "onset": metrics["onset"],
    }
    (output_dir / "result.json").write_text(
        json.dumps(result, indent=2), encoding="utf-8"
    )
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
