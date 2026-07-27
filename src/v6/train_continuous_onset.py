"""Train and evaluate the standalone V6.3 continuous causal onset detector."""

from __future__ import annotations

import argparse
import csv
import json
import platform
import subprocess
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from scipy.signal import resample_poly
from tensorflow.keras.utils import Sequence as KerasSequence

from src.v5.external_data import (
    NoteEvent,
    SourceRecording,
    causal_window,
    discover_guitarset,
    parse_recording_notes,
    read_recording_audio,
)
from src.v6.evaluate import average_precision, binary_metrics, select_f1_threshold
from src.v6.onset_continuous_dataset import (
    PHASE_NAMES,
    first_causal_frame_end,
    onset_frame_ends,
)
from src.v6.onset_continuous_model import build_continuous_onset_model


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except Exception:
        return None


def load_manifest(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ValueError(f"Manifest vide: {path}")
    required = {"source_id", "npz_path", "player_id", "split"}
    missing = required - set(rows[0])
    if missing:
        raise ValueError(f"Colonnes manifest manquantes: {sorted(missing)}")
    return rows


def load_split_arrays(
    rows: list[dict[str, str]], split: str
) -> dict[str, np.ndarray]:
    selected = [row for row in rows if row["split"] == split]
    if not selected:
        raise ValueError(f"Split absent du manifest: {split}")
    names = (
        "audio", "onset", "phase", "note_id", "pitch_midi",
        "frame_end_sample", "attack_age_ms", "harmonic_richness", "polyphony",
    )
    parts: dict[str, list[np.ndarray]] = {name: [] for name in names}
    source_ids: list[str] = []
    for row in selected:
        with np.load(Path(row["npz_path"])) as current:
            missing = set(names) - set(current.files)
            if missing:
                raise ValueError(
                    f"{row['source_id']}: arrays manquants {sorted(missing)}"
                )
            count = len(current["onset"])
            if current["audio"].shape != (count, 512):
                raise ValueError(f"{row['source_id']}: shape audio V6.3 invalide.")
            for name in names:
                parts[name].append(np.asarray(current[name]))
            source_ids.extend([row["source_id"]] * count)
    result = {name: np.concatenate(values) for name, values in parts.items()}
    result["source_id"] = np.asarray(source_ids, dtype=str)
    if not np.isfinite(result["audio"]).all():
        raise ValueError(f"Audio non fini dans le split {split}.")
    if set(np.unique(result["onset"]).tolist()) - {0.0, 1.0}:
        raise ValueError(f"Labels onset non binaires dans le split {split}.")
    return result


def compute_gain(
    audio: np.ndarray,
    percentile: float,
    target: float,
    max_gain: float,
) -> float:
    peaks = np.max(np.abs(np.asarray(audio, dtype=np.float32)), axis=1)
    reference = float(np.percentile(peaks, percentile)) if len(peaks) else 1.0
    return min(float(max_gain), float(target) / max(reference, 1e-8))


class OnsetSequence(KerasSequence):
    """RAM sequence with deterministic balanced sampling on train only."""

    def __init__(
        self,
        arrays: dict[str, np.ndarray],
        batch_size: int,
        gain: float,
        shuffle: bool,
        balance: bool,
        seed: int,
    ) -> None:
        self.arrays = arrays
        self.batch_size = int(batch_size)
        self.gain = float(gain)
        self.shuffle = bool(shuffle)
        self.balance = bool(balance)
        self.rng = np.random.default_rng(seed)
        if self.batch_size < 1:
            raise ValueError("batch_size doit etre positif.")
        self._positive = np.flatnonzero(arrays["onset"] > 0.5)
        self._negative = np.flatnonzero(arrays["onset"] <= 0.5)
        if not len(self._positive) or not len(self._negative):
            raise ValueError("Les deux classes onset sont requises.")
        self.indices = np.arange(len(arrays["onset"]), dtype=np.int64)
        self.on_epoch_end()

    def __len__(self) -> int:
        return int(np.ceil(len(self.indices) / self.batch_size))

    def __getitem__(self, batch_index: int):
        start = batch_index * self.batch_size
        selected = self.indices[start:start + self.batch_size]
        audio = np.asarray(self.arrays["audio"][selected], dtype=np.float32).copy()
        audio *= self.gain
        np.clip(audio, -1.0, 1.0, out=audio)
        targets = np.asarray(
            self.arrays["onset"][selected], dtype=np.float32
        ).reshape(-1, 1)
        phase = np.asarray(self.arrays["phase"][selected], dtype=np.int32)
        weights = np.ones(len(selected), dtype=np.float32)
        # Hard negatives matter more than easy silence, but are normalized to
        # mean one so class balance remains controlled by the sampler.
        negative = targets.reshape(-1) <= 0.5
        multipliers = np.ones(len(selected), dtype=np.float32)
        multipliers[phase == 1] = 1.35  # pre-attack
        multipliers[phase == 2] = 1.25  # decay
        multipliers[phase == 6] = 1.50  # harmonic-rich tail
        multipliers[phase == 5] = 0.75  # easy silence
        if np.any(negative):
            negative_values = multipliers[negative]
            weights[negative] = negative_values / max(
                float(np.mean(negative_values)), 1e-8
            )
        return audio[..., None], targets, weights

    def on_epoch_end(self) -> None:
        if self.balance:
            negative = self.rng.choice(
                self._negative,
                size=len(self._positive),
                replace=len(self._negative) < len(self._positive),
            )
            self.indices = np.concatenate([self._positive, negative])
        else:
            self.indices = np.arange(len(self.arrays["onset"]), dtype=np.int64)
        if self.shuffle:
            self.rng.shuffle(self.indices)


def _prepare_waveform(
    recording: SourceRecording, sample_rate: int
) -> tuple[np.ndarray, list[NoteEvent]]:
    audio, source_rate = read_recording_audio(recording)
    source_rate = int(source_rate)
    if source_rate != sample_rate:
        divisor = np.gcd(source_rate, sample_rate)
        audio = resample_poly(
            audio,
            sample_rate // divisor,
            source_rate // divisor,
            axis=0,
        ).astype(np.float32, copy=False)
    waveform = np.mean(audio, axis=1, dtype=np.float32)
    duration_s = len(waveform) / sample_rate
    notes = [
        NoteEvent(
            note.note_id,
            note.start_s,
            min(note.end_s, duration_s),
            note.pitch_midi,
            note.expression,
        )
        for note in parse_recording_notes(recording)
        if 0.0 <= note.start_s < duration_s and note.end_s > note.start_s
    ]
    return waveform, notes


def predict_continuous(
    model,
    recording: SourceRecording,
    gain: float,
    sample_rate: int,
    hop_size: int,
    window_size: int,
    positive_hops: int,
    min_pitch: int,
    max_pitch: int,
    batch_size: int,
) -> dict[str, Any]:
    waveform, notes = _prepare_waveform(recording, sample_rate)
    end_samples = np.arange(hop_size, len(waveform) + 1, hop_size, dtype=np.int64)
    probabilities: list[np.ndarray] = []
    started = time.perf_counter()
    for start in range(0, len(end_samples), batch_size):
        selected = end_samples[start:start + batch_size]
        batch = np.asarray(
            [causal_window(waveform, int(end), window_size) for end in selected],
            dtype=np.float32,
        )
        batch *= gain
        np.clip(batch, -1.0, 1.0, out=batch)
        raw = model(batch[..., None], training=False)
        probabilities.append(np.asarray(raw, dtype=np.float32).reshape(-1))
    elapsed_s = time.perf_counter() - started
    targets = np.zeros(len(end_samples), dtype=np.float32)
    positive = onset_frame_ends(
        notes,
        sample_rate,
        hop_size,
        positive_hops,
        len(waveform),
        min_pitch,
        max_pitch,
    )
    if len(end_samples):
        frame_lookup = {int(value): index for index, value in enumerate(end_samples)}
        for end_sample in positive:
            index = frame_lookup.get(int(end_sample))
            if index is not None:
                targets[index] = 1.0
    # A binary detector can emit one event for a chord attack.  Notes whose
    # first causal frame is identical are therefore one reference event,
    # while a later note_id (including the same MIDI pitch) remains a distinct
    # retrigger.
    first_frame_groups: dict[int, list[NoteEvent]] = {}
    for note in notes:
        if not min_pitch <= note.pitch_midi <= max_pitch:
            continue
        first_end = first_causal_frame_end(
            int(round(note.start_s * sample_rate)), hop_size
        )
        first_frame_groups.setdefault(first_end, []).append(note)
    reference_samples = np.asarray([
        min(int(round(note.start_s * sample_rate)) for note in grouped)
        for _, grouped in sorted(first_frame_groups.items())
    ], dtype=np.int64)
    return {
        "source_id": recording.source_id,
        "end_samples": end_samples,
        "probabilities": (
            np.concatenate(probabilities) if probabilities else
            np.empty(0, dtype=np.float32)
        ),
        "targets": targets,
        "reference_samples": reference_samples,
        "audio_duration_s": len(waveform) / sample_rate,
        "inference_s": elapsed_s,
    }


def _detected_samples(
    probabilities: np.ndarray,
    end_samples: np.ndarray,
    threshold: float,
    refractory_samples: int,
) -> np.ndarray:
    above = np.asarray(probabilities) >= float(threshold)
    rising = above & ~np.r_[False, above[:-1]]
    raw = np.asarray(end_samples, dtype=np.int64)[rising]
    if not len(raw):
        return raw
    kept = [int(raw[0])]
    for sample in raw[1:]:
        if int(sample) - kept[-1] >= refractory_samples:
            kept.append(int(sample))
    return np.asarray(kept, dtype=np.int64)


def event_counts(
    item: dict[str, Any],
    threshold: float,
    sample_rate: int,
    tolerance_ms: float = 35.0,
    refractory_ms: float = 50.0,
) -> tuple[int, int, int, list[float]]:
    detected = _detected_samples(
        item["probabilities"],
        item["end_samples"],
        threshold,
        int(round(refractory_ms / 1000.0 * sample_rate)),
    )
    references = np.asarray(item["reference_samples"], dtype=np.int64)
    tolerance = int(round(tolerance_ms / 1000.0 * sample_rate))
    used = np.zeros(len(references), dtype=bool)
    tp = 0
    latencies: list[float] = []
    for detection in detected:
        causal = np.flatnonzero(
            (~used) & (references <= detection) & (detection - references <= tolerance)
        )
        if not len(causal):
            continue
        # Match the nearest preceding reference; this preserves same-pitch
        # retriggers because identity is the annotation event, not its MIDI.
        selected = int(causal[np.argmin(detection - references[causal])])
        used[selected] = True
        tp += 1
        latencies.append((detection - int(references[selected])) / sample_rate * 1000.0)
    fp = int(len(detected) - tp)
    fn = int(len(references) - tp)
    return tp, fp, fn, latencies


def event_metrics(
    items: list[dict[str, Any]],
    threshold: float,
    sample_rate: int,
) -> dict[str, Any]:
    tp = fp = fn = 0
    latencies: list[float] = []
    duration_s = 0.0
    for item in items:
        current_tp, current_fp, current_fn, current_latencies = event_counts(
            item, threshold, sample_rate
        )
        tp += current_tp
        fp += current_fp
        fn += current_fn
        latencies.extend(current_latencies)
        duration_s += float(item["audio_duration_s"])
    precision = tp / max(tp + fp, 1)
    recall = tp / max(tp + fn, 1)
    f1 = 2.0 * precision * recall / max(precision + recall, 1e-12)
    return {
        "threshold": float(threshold),
        "tp": tp,
        "fp": fp,
        "fn": fn,
        "precision": float(precision),
        "recall": float(recall),
        "f1": float(f1),
        "false_events_per_minute": float(fp / max(duration_s / 60.0, 1e-12)),
        "latency_mean_ms": float(np.mean(latencies)) if latencies else None,
        "latency_p95_ms": float(np.percentile(latencies, 95.0)) if latencies else None,
        "recordings": len(items),
        "audio_duration_s": duration_s,
    }


def select_event_threshold(
    items: list[dict[str, Any]], sample_rate: int
) -> tuple[float, dict[str, Any]]:
    probabilities = np.concatenate([item["probabilities"] for item in items])
    targets = np.concatenate([item["targets"] for item in items])
    frame_threshold, _ = select_f1_threshold(probabilities, targets)
    quantiles = np.linspace(1.0, 99.9, 240)
    candidates = np.unique(np.r_[
        np.quantile(probabilities, quantiles / 100.0),
        frame_threshold,
        0.5,
    ])
    best: dict[str, Any] | None = None
    for threshold in candidates:
        metrics = event_metrics(items, float(threshold), sample_rate)
        key = (metrics["f1"], metrics["precision"], float(threshold))
        if best is None or key > best["_key"]:
            best = {**metrics, "_key": key}
    if best is None:
        raise ValueError("Aucun seuil onset continu candidat.")
    best.pop("_key")
    best["selection"] = "max_validation_event_f1_then_precision_then_threshold"
    return float(best["threshold"]), best


def continuous_report(
    items: list[dict[str, Any]], threshold: float, sample_rate: int
) -> dict[str, Any]:
    probabilities = np.concatenate([item["probabilities"] for item in items])
    targets = np.concatenate([item["targets"] for item in items])
    frame = binary_metrics(probabilities, targets, threshold)
    frame["average_precision"] = average_precision(probabilities, targets)
    return {
        "frame": frame,
        "event": event_metrics(items, threshold, sample_rate),
        "inference": {
            "frames": int(len(probabilities)),
            "seconds": float(sum(float(item["inference_s"]) for item in items)),
        },
    }


def phase_report(
    arrays: dict[str, np.ndarray], probabilities: np.ndarray, threshold: float
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for phase, name in enumerate(PHASE_NAMES):
        selected = np.asarray(arrays["phase"] == phase)
        if not np.any(selected):
            continue
        result[name] = binary_metrics(
            probabilities[selected], arrays["onset"][selected], threshold
        )
        result[name]["mean_probability"] = float(np.mean(probabilities[selected]))
    return result


def benchmark_batch_one(model, repeats: int = 400) -> dict[str, Any]:
    import tensorflow as tf

    sample = np.zeros((1, 512, 1), dtype=np.float32)

    @tf.function(input_signature=[tf.TensorSpec((1, 512, 1), tf.float32)])
    def compiled(value):
        return model(value, training=False)

    def measure(function) -> dict[str, float]:
        for _ in range(20):
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
        "repeats_each": int(repeats),
        "keras_eager": measure(lambda value: model(value, training=False)),
        "tf_function": measure(compiled),
    }


def _recordings_by_split(root: Path, split: str) -> list[SourceRecording]:
    return [item for item in discover_guitarset(root) if item.split == split]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config", type=Path,
        default=Path("configs/onset_v6_3_continuous.yaml"),
    )
    args = parser.parse_args()
    raw = yaml.safe_load(args.config.read_text(encoding="utf-8"))
    dataset_cfg = raw["dataset"]
    train_cfg = raw["train"]
    model_cfg = raw["model"]

    import tensorflow as tf

    seed = int(dataset_cfg.get("seed", 42))
    tf.keras.utils.set_random_seed(seed)
    manifest = Path(dataset_cfg["manifest"])
    rows = load_manifest(manifest)
    print("Chargement V6.3 en RAM...")
    arrays = {
        split: load_split_arrays(rows, split)
        for split in ("train", "validation", "test")
    }
    gain = compute_gain(
        arrays["train"]["audio"],
        float(dataset_cfg.get("normalization_percentile", 95.0)),
        float(dataset_cfg.get("normalization_target", 0.8)),
        float(dataset_cfg.get("max_gain", 16.0)),
    )
    sequences = {
        "train": OnsetSequence(
            arrays["train"], int(train_cfg["batch_size"]), gain,
            shuffle=True, balance=True, seed=seed,
        ),
        "validation": OnsetSequence(
            arrays["validation"], int(train_cfg["batch_size"]), gain,
            shuffle=False, balance=False, seed=seed,
        ),
        "test": OnsetSequence(
            arrays["test"], int(train_cfg["batch_size"]), gain,
            shuffle=False, balance=False, seed=seed,
        ),
    }
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    run_dir = Path(train_cfg.get("output_root", "runs/v6")) / (
        f"{train_cfg.get('run_name', 'onset_v6_3_continuous')}_{timestamp}"
    )
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "config.yaml").write_text(
        args.config.read_text(encoding="utf-8"), encoding="utf-8"
    )
    (run_dir / "normalization.json").write_text(
        json.dumps({"gain": gain}, indent=2), encoding="utf-8"
    )
    statistics = {
        split: {
            "examples": int(len(values["onset"])),
            "positive": int(np.sum(values["onset"] > 0.5)),
            "negative": int(np.sum(values["onset"] <= 0.5)),
            "phase_counts": {
                PHASE_NAMES[int(key)]: int(value)
                for key, value in zip(*np.unique(values["phase"], return_counts=True))
            },
        }
        for split, values in arrays.items()
    }
    (run_dir / "dataset_statistics.json").write_text(
        json.dumps(statistics, indent=2), encoding="utf-8"
    )
    (run_dir / "runtime.json").write_text(
        json.dumps({
            "python": platform.python_version(),
            "tensorflow": tf.__version__,
            "numpy": np.__version__,
            "git_commit": _git_commit(),
        }, indent=2), encoding="utf-8"
    )

    model = build_continuous_onset_model(
        window_size=int(dataset_cfg.get("window_size", 512)),
        channels=int(model_cfg.get("channels", 24)),
        dropout=float(model_cfg.get("dropout", 0.1)),
        pooling=str(model_cfg.get("pooling", "hybrid")),
    )
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
            str(run_dir / "best.keras"),
            monitor="val_auc_pr", mode="max", save_best_only=True,
        ),
        tf.keras.callbacks.ModelCheckpoint(
            str(run_dir / "last.keras"), save_best_only=False,
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor="val_auc_pr", mode="max",
            patience=int(train_cfg.get("reduce_lr_patience", 2)),
            factor=0.5,
            min_lr=float(train_cfg.get("min_learning_rate", 1e-6)),
        ),
        tf.keras.callbacks.EarlyStopping(
            monitor="val_auc_pr", mode="max",
            patience=int(train_cfg.get("early_stopping_patience", 5)),
        ),
    ]
    model.summary()
    model.fit(
        sequences["train"],
        validation_data=sequences["validation"],
        epochs=int(train_cfg["epochs"]),
        callbacks=callbacks,
        verbose=2,
    )
    best = tf.keras.models.load_model(run_dir / "best.keras", compile=False)

    # The sparse validation is diagnostic only.  The deployed threshold is
    # selected exclusively on every real continuous hop of player 04.
    extracted_validation = np.asarray(
        best.predict(sequences["validation"], verbose=0), dtype=np.float32
    ).reshape(-1)
    sparse_threshold, sparse_metrics = select_f1_threshold(
        extracted_validation,
        arrays["validation"]["onset"],
    )
    sparse_metrics["phase"] = phase_report(
        arrays["validation"], extracted_validation, sparse_threshold
    )
    (run_dir / "extracted_validation.json").write_text(
        json.dumps(sparse_metrics, indent=2), encoding="utf-8"
    )

    common = {
        "gain": gain,
        "sample_rate": int(dataset_cfg.get("sample_rate", 44_100)),
        "hop_size": int(dataset_cfg.get("hop_size", 256)),
        "window_size": int(dataset_cfg.get("window_size", 512)),
        "positive_hops": int(dataset_cfg.get("positive_hops", 2)),
        "min_pitch": int(dataset_cfg.get("min_pitch", 40)),
        "max_pitch": int(dataset_cfg.get("max_pitch", 76)),
        "batch_size": int(train_cfg.get("inference_batch_size", 1024)),
    }
    guitarset_root = Path(dataset_cfg.get("guitarset_root", "data/GuitarSet"))
    continuous_validation = [
        predict_continuous(best, recording, **common)
        for recording in _recordings_by_split(guitarset_root, "validation")
    ]
    threshold, selection = select_event_threshold(
        continuous_validation, common["sample_rate"]
    )
    validation_report = continuous_report(
        continuous_validation, threshold, common["sample_rate"]
    )
    validation_report["selection"] = selection
    (run_dir / "continuous_validation.json").write_text(
        json.dumps(validation_report, indent=2), encoding="utf-8"
    )
    (run_dir / "onset_threshold.json").write_text(
        json.dumps({
            "threshold": threshold,
            "selection_basis": "continuous_player_04_only",
            "selection": selection,
        }, indent=2), encoding="utf-8"
    )

    continuous_test = [
        predict_continuous(best, recording, **common)
        for recording in _recordings_by_split(guitarset_root, "test")
    ]
    test_report = continuous_report(
        continuous_test, threshold, common["sample_rate"]
    )
    (run_dir / "continuous_test.json").write_text(
        json.dumps(test_report, indent=2), encoding="utf-8"
    )
    latency = benchmark_batch_one(best)
    (run_dir / "latency.json").write_text(
        json.dumps(latency, indent=2), encoding="utf-8"
    )
    selected = {
        "selected_checkpoint": "best.keras",
        "selection_basis": "best_extracted_validation_auc_pr",
        "onset_threshold": threshold,
        "threshold_selection_basis": "continuous_player_04_only",
        "continuous_validation": validation_report,
        "continuous_test": test_report,
        "batch_one_latency": latency,
    }
    (run_dir / "selected_checkpoint.json").write_text(
        json.dumps(selected, indent=2), encoding="utf-8"
    )
    print(f"Run V6.3: {run_dir}")
    print(f"Seuil continu validation: {threshold:.6f}")
    print(f"Validation event F1: {validation_report['event']['f1']:.3%}")
    print(f"Test event F1: {test_report['event']['f1']:.3%}")
    print(
        "Latence batch=1 tf.function p95: "
        f"{latency['tf_function']['p95_ms']:.3f} ms"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
