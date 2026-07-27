"""Re-evaluate a trained V6.3 checkpoint on complete continuous splits."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.v6.train_continuous_onset import (
    _recordings_by_split,
    benchmark_batch_one,
    continuous_report,
    predict_continuous,
    select_event_threshold,
)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--batch-size", type=int, default=1024)
    args = parser.parse_args()

    import tensorflow as tf
    import yaml

    run_dir = args.run_dir.resolve()
    config = yaml.safe_load((run_dir / "config.yaml").read_text(encoding="utf-8"))
    dataset = config["dataset"]
    selection = json.loads(
        (run_dir / "selected_checkpoint.json").read_text(encoding="utf-8")
    )
    checkpoint = run_dir / selection["selected_checkpoint"]
    gain = float(json.loads(
        (run_dir / "normalization.json").read_text(encoding="utf-8")
    )["gain"])
    model = tf.keras.models.load_model(checkpoint, compile=False)
    common = {
        "gain": gain,
        "sample_rate": int(dataset.get("sample_rate", 44_100)),
        "hop_size": int(dataset.get("hop_size", 256)),
        "window_size": int(dataset.get("window_size", 512)),
        "positive_hops": int(dataset.get("positive_hops", 2)),
        "min_pitch": int(dataset.get("min_pitch", 40)),
        "max_pitch": int(dataset.get("max_pitch", 76)),
        "batch_size": int(args.batch_size),
    }
    root = Path(dataset.get("guitarset_root", "data/GuitarSet"))
    validation_items = [
        predict_continuous(model, recording, **common)
        for recording in _recordings_by_split(root, "validation")
    ]
    threshold, threshold_selection = select_event_threshold(
        validation_items, common["sample_rate"]
    )
    validation = continuous_report(
        validation_items, threshold, common["sample_rate"]
    )
    validation["selection"] = threshold_selection
    (run_dir / "continuous_validation_corrected.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    test_items = [
        predict_continuous(model, recording, **common)
        for recording in _recordings_by_split(root, "test")
    ]
    test = continuous_report(test_items, threshold, common["sample_rate"])
    (run_dir / "continuous_test_corrected.json").write_text(
        json.dumps(test, indent=2), encoding="utf-8"
    )
    latency = benchmark_batch_one(model)
    (run_dir / "latency_corrected.json").write_text(
        json.dumps(latency, indent=2), encoding="utf-8"
    )
    corrected = {
        "selected_checkpoint": selection["selected_checkpoint"],
        "selection_basis": selection["selection_basis"],
        "onset_threshold": threshold,
        "threshold_selection_basis": "continuous_player_04_only",
        "metric_correction": (
            "one binary event per first causal onset frame; two positive label "
            "hops no longer count as two reference events"
        ),
        "continuous_validation": validation,
        "continuous_test": test,
        "batch_one_latency": latency,
    }
    (run_dir / "selected_checkpoint_corrected.json").write_text(
        json.dumps(corrected, indent=2), encoding="utf-8"
    )
    (run_dir / "METRIC_CORRECTION.md").write_text(
        "# Correction de la metrique evenementielle\n\n"
        "Les rapports `continuous_validation.json` et `continuous_test.json` "
        "comptaient par erreur les deux hops positifs d'une seule attaque comme "
        "deux evenements de reference. Ils sont conserves uniquement pour la "
        "tracabilite. Les fichiers suffixes `_corrected` comptent un evenement "
        "binaire par premiere trame causale et constituent les rapports valides.\n",
        encoding="utf-8",
    )
    print(json.dumps({
        "threshold": threshold,
        "validation_event": validation["event"],
        "test_event": test["event"],
        "latency": latency,
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
