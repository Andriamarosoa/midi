"""Train the tiny V6.3.2 classifier on frozen V6.0 transition candidates."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import yaml

from src.v6.evaluate import average_precision, binary_metrics, select_f1_threshold
from src.v6.transition_gate import FEATURE_NAMES, build_transition_gate_model


ARRAY_NAMES = (
    "features", "label", "sample_weight", "frame_index", "frame_end_sample",
    "current_pitch", "candidate_pitch", "annotation_support_ratio",
    "target_note_id", "recent_onset_note_id", "harmonic_suspect",
    "csv_harmonic_strength",
)

OPTIONAL_ARRAY_NAMES = (
    "v6_3_2_label", "candidate_utility", "current_utility", "utility_margin",
    "candidate_support_by_horizon", "current_support_by_horizon",
)


def load_split(manifest: Path, split: str) -> dict[str, np.ndarray]:
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = [row for row in csv.DictReader(handle) if row["split"] == split]
    if not rows:
        raise ValueError(f"Split V6.3.2 absent: {split}")
    parts: dict[str, list[np.ndarray]] = {name: [] for name in ARRAY_NAMES}
    optional: set[str] | None = None
    source_ids: list[str] = []
    for row in rows:
        with np.load(Path(row["npz_path"])) as data:
            count = len(data["label"])
            current_optional = set(OPTIONAL_ARRAY_NAMES) & set(data.files)
            if optional is None:
                optional = current_optional
                parts.update({name: [] for name in optional})
            elif current_optional != optional:
                raise ValueError("Arrays optionnels incoherents entre sources.")
            for name in ARRAY_NAMES:
                parts[name].append(np.asarray(data[name]))
            for name in optional:
                parts[name].append(np.asarray(data[name]))
            source_ids.extend([row["source_id"]] * count)
    result = {name: np.concatenate(values) for name, values in parts.items()}
    result["source_id"] = np.asarray(source_ids, dtype=str)
    return result


def _metrics_by_mask(
    probabilities: np.ndarray,
    labels: np.ndarray,
    threshold: float,
    masks: dict[str, np.ndarray],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for name, mask in masks.items():
        mask = np.asarray(mask, dtype=bool)
        if not np.any(mask):
            continue
        metrics = binary_metrics(probabilities[mask], labels[mask], threshold)
        metrics["average_precision"] = average_precision(
            probabilities[mask], labels[mask]
        )
        result[name] = metrics
    return result


def grouped_metrics(
    arrays: dict[str, np.ndarray],
    probabilities: np.ndarray,
    threshold: float,
) -> dict[str, object]:
    labels = arrays["label"]
    negative = labels <= 0.5
    interval = arrays["candidate_pitch"] - arrays["current_pitch"]
    return _metrics_by_mask(probabilities, labels, threshold, {
        "all": np.ones(len(labels), dtype=bool),
        "recent_annotation_onset": arrays["recent_onset_note_id"] >= 0,
        "no_recent_annotation_onset": arrays["recent_onset_note_id"] < 0,
        "harmonic_suspect_negative": negative & (arrays["harmonic_suspect"] > 0),
        "csv_harmonic_negative": negative & (arrays["csv_harmonic_strength"] > 0),
        "upward_transition": interval > 0,
        "downward_transition": interval < 0,
    })


def write_error_csv(
    path: Path,
    arrays: dict[str, np.ndarray],
    probabilities: np.ndarray,
    threshold: float,
) -> None:
    predicted = probabilities >= threshold
    labels = arrays["label"] > 0.5
    errors = np.flatnonzero(predicted != labels)
    order = sorted(
        errors,
        key=lambda index: abs(float(probabilities[index]) - float(labels[index])),
        reverse=True,
    )
    fields = [
        "source_id", "frame_end_sample", "current_pitch", "candidate_pitch",
        "label", "probability", "error", "annotation_support_ratio",
        "target_note_id", "recent_onset_note_id", "harmonic_suspect",
        "csv_harmonic_strength", *FEATURE_NAMES,
    ]
    utility_names = [
        name for name in (
            "v6_3_2_label", "candidate_utility", "current_utility",
            "utility_margin",
        ) if name in arrays
    ]
    fields[12:12] = utility_names
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for index in order[:500]:
            row = {
                "source_id": arrays["source_id"][index],
                "frame_end_sample": int(arrays["frame_end_sample"][index]),
                "current_pitch": int(arrays["current_pitch"][index]),
                "candidate_pitch": int(arrays["candidate_pitch"][index]),
                "label": int(labels[index]),
                "probability": float(probabilities[index]),
                "error": "false_allow" if predicted[index] else "false_block",
                "annotation_support_ratio": float(
                    arrays["annotation_support_ratio"][index]
                ),
                "target_note_id": int(arrays["target_note_id"][index]),
                "recent_onset_note_id": int(arrays["recent_onset_note_id"][index]),
                "harmonic_suspect": int(arrays["harmonic_suspect"][index]),
                "csv_harmonic_strength": float(
                    arrays["csv_harmonic_strength"][index]
                ),
            }
            row.update({
                name: float(arrays["features"][index, feature_index])
                for feature_index, name in enumerate(FEATURE_NAMES)
            })
            row.update({name: float(arrays[name][index]) for name in utility_names})
            writer.writerow(row)


def benchmark(model, repeats: int = 2000) -> dict[str, object]:
    import tensorflow as tf

    sample = np.zeros((1, len(FEATURE_NAMES)), dtype=np.float32)

    @tf.function(input_signature=[
        tf.TensorSpec((1, len(FEATURE_NAMES)), tf.float32)
    ])
    def compiled(value):
        return model(value, training=False)

    def measure(function) -> dict[str, float]:
        for _ in range(30):
            np.asarray(function(sample))
        timings: list[float] = []
        for _ in range(repeats):
            started = time.perf_counter()
            np.asarray(function(sample))
            timings.append((time.perf_counter() - started) * 1000.0)
        values = np.asarray(timings, dtype=np.float64)
        return {
            "mean_ms": float(np.mean(values)),
            "p95_ms": float(np.percentile(values, 95.0)),
            "max_ms": float(np.max(values)),
        }
    return {
        "repeats_each": repeats,
        "keras_eager": measure(lambda value: model(value, training=False)),
        "tf_function": measure(compiled),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path,
        default=Path("configs/transition_gate_v6_3_2.yaml"),
    )
    args = parser.parse_args()
    config = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset_cfg = config["dataset"]
    train_cfg = config["train"]

    import tensorflow as tf

    seed = int(dataset_cfg.get("seed", 42))
    tf.keras.utils.set_random_seed(seed)
    manifest = Path(dataset_cfg["manifest"])
    arrays = {
        split: load_split(manifest, split)
        for split in ("train", "validation", "test")
    }
    train_label = arrays["train"]["label"] > 0.5
    positive = int(np.sum(train_label))
    negative = int(np.sum(~train_label))
    class_weight = np.asarray([
        len(train_label) / max(2 * negative, 1),
        len(train_label) / max(2 * positive, 1),
    ], dtype=np.float32)
    weights = arrays["train"]["sample_weight"].astype(np.float32) * np.where(
        train_label, class_weight[1], class_weight[0]
    )
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(train_cfg.get("output_root", "runs/v6")) / (
        f"{train_cfg.get('run_name', 'transition_gate_v6_3_2')}_{timestamp}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.yaml").write_text(
        args.config.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (run_dir / "runtime.json").write_text(json.dumps({
        "python": platform.python_version(),
        "tensorflow": tf.__version__,
        "numpy": np.__version__,
    }, indent=2), encoding="utf-8")
    (run_dir / "dataset_statistics.json").write_text(json.dumps({
        split: {
            "candidates": int(len(values["label"])),
            "allowed": int(np.sum(values["label"] > 0.5)),
            "rejected": int(np.sum(values["label"] <= 0.5)),
            "sources": int(len(np.unique(values["source_id"]))),
        }
        for split, values in arrays.items()
    } | {
        "feature_names": list(FEATURE_NAMES),
        "class_weight": {
            "rejected": float(class_weight[0]),
            "allowed": float(class_weight[1]),
        },
    }, indent=2), encoding="utf-8")

    model = build_transition_gate_model()
    model.compile(
        optimizer=tf.keras.optimizers.Adam(float(train_cfg["learning_rate"])),
        loss=tf.keras.losses.BinaryCrossentropy(),
        metrics=[
            tf.keras.metrics.AUC(curve="PR", name="auc_pr"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
    callbacks = [
        tf.keras.callbacks.CSVLogger(str(run_dir / "history.csv")),
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "best.keras"), monitor="val_auc_pr", mode="max",
            save_best_only=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "last.keras"), save_best_only=False,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_auc_pr", mode="max", factor=0.5,
            patience=int(train_cfg.get("reduce_lr_patience", 4)),
            min_lr=float(train_cfg.get("min_learning_rate", 1e-6)),
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc_pr", mode="max",
            patience=int(train_cfg.get("early_stopping_patience", 10)),
        ),
    ]
    model.summary()
    model.fit(
        arrays["train"]["features"],
        arrays["train"]["label"],
        sample_weight=weights,
        validation_data=(
            arrays["validation"]["features"],
            arrays["validation"]["label"],
        ),
        batch_size=int(train_cfg["batch_size"]),
        epochs=int(train_cfg["epochs"]),
        shuffle=True,
        callbacks=callbacks,
        verbose=2,
    )
    best = tf.keras.models.load_model(run_dir / "best.keras", compile=False)
    validation_probability = np.asarray(
        best.predict(arrays["validation"]["features"], batch_size=1024, verbose=0)
    ).reshape(-1)
    threshold, threshold_metrics = select_f1_threshold(
        validation_probability, arrays["validation"]["label"]
    )
    validation_metrics = grouped_metrics(
        arrays["validation"], validation_probability, threshold
    )
    test_probability = np.asarray(
        best.predict(arrays["test"]["features"], batch_size=1024, verbose=0)
    ).reshape(-1)
    test_metrics = grouped_metrics(arrays["test"], test_probability, threshold)
    latency = benchmark(best)
    (run_dir / "threshold.json").write_text(json.dumps({
        "threshold": threshold,
        "selection_basis": "all_player_04_transition_candidates_only",
        "metrics": threshold_metrics,
    }, indent=2), encoding="utf-8")
    (run_dir / "validation_metrics.json").write_text(
        json.dumps(validation_metrics, indent=2), encoding="utf-8"
    )
    (run_dir / "test_metrics.json").write_text(
        json.dumps(test_metrics, indent=2), encoding="utf-8"
    )
    (run_dir / "latency.json").write_text(
        json.dumps(latency, indent=2), encoding="utf-8"
    )
    write_error_csv(
        run_dir / "validation_errors.csv", arrays["validation"],
        validation_probability, threshold,
    )
    write_error_csv(
        run_dir / "test_errors.csv", arrays["test"], test_probability, threshold
    )
    selection = {
        "selected_checkpoint": "best.keras",
        "selection_basis": "maximum_validation_auc_pr_player_04",
        "transition_threshold": threshold,
        "threshold_selection_basis": "maximum_f1_all_player_04_candidates",
        "validation": validation_metrics,
        "test": test_metrics,
        "latency": latency,
    }
    (run_dir / "selected_checkpoint.json").write_text(
        json.dumps(selection, indent=2), encoding="utf-8"
    )
    print(f"Run V6.3.2: {run_dir}")
    print(f"Validation AP: {validation_metrics['all']['average_precision']:.3%}")
    print(f"Test AP: {test_metrics['all']['average_precision']:.3%}")
    print(f"Seuil validation: {threshold:.6f}")
    print(f"Latence gate p95: {latency['tf_function']['p95_ms']:.3f} ms")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
