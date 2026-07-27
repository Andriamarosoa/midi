"""Compare Keras and TFLite note events on the frozen validation recordings."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import Counter
from dataclasses import asdict
from pathlib import Path
from typing import Any, Mapping

import numpy as np
import tensorflow as tf

from src.polyphonic import model as _registered_model_types  # noqa: F401
from src.polyphonic.audio_evidence import offline_audio_evidence_masks
from src.polyphonic.data import PolyphonicCorpus, PolyphonicSequence, load_manifest
from src.polyphonic.decoder import PolyphonicDecoderConfig
from src.polyphonic.evaluate_events import (
    NoteInterval,
    aggregate_dataset_note_metrics,
    decode_probabilities,
    diagnose_note_errors,
    match_notes,
    note_metrics,
    select_evaluation_recordings,
    truth_notes,
)


OUTPUT_NAMES = ("frame", "onset", "harmonic_amplitude")
MAXIMUM_EVENT_F1_DROP = 0.005
MAXIMUM_COUNT_REGRESSION_FRACTION = 0.01


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _shifted(notes: list[NoteInterval], shift: float) -> list[NoteInterval]:
    return [
        NoteInterval(note.pitch, note.start_s + shift, note.end_s + shift)
        for note in notes
    ]


def _interval_counter(notes: list[NoteInterval]) -> Counter[tuple[int, int, int]]:
    return Counter(
        (note.pitch, round(note.start_s * 1e9), round(note.end_s * 1e9))
        for note in notes
    )


def _count_regression_allowed(baseline: int, candidate: int) -> bool:
    allowance = max(
        1, int(math.ceil(MAXIMUM_COUNT_REGRESSION_FRACTION * baseline))
    )
    return candidate - baseline <= allowance


def event_policy_passes(
    keras_report: Mapping[str, Any],
    tflite_report: Mapping[str, Any],
) -> bool:
    for metric in ("onset", "onset_offset"):
        if (
            float(tflite_report[metric]["f1"])
            - float(keras_report[metric]["f1"])
            < -MAXIMUM_EVENT_F1_DROP
        ):
            return False
    keras_datasets = keras_report["dataset_metrics"]["per_dataset"]
    tflite_datasets = tflite_report["dataset_metrics"]["per_dataset"]
    if set(keras_datasets) != set(tflite_datasets):
        return False
    for dataset in keras_datasets:
        for metric in ("onset", "onset_offset"):
            if (
                float(tflite_datasets[dataset][metric]["f1"])
                - float(keras_datasets[dataset][metric]["f1"])
                < -MAXIMUM_EVENT_F1_DROP
            ):
                return False
    for metric in ("false_positive_notes", "missing_notes"):
        if not _count_regression_allowed(
            int(keras_report["onset"][metric]),
            int(tflite_report["onset"][metric]),
        ):
            return False
    if not _count_regression_allowed(
        int(keras_report["retriggers"]), int(tflite_report["retriggers"])
    ):
        return False
    if not _count_regression_allowed(
        int(keras_report["diagnostics"]["excess_fragments"]),
        int(tflite_report["diagnostics"]["excess_fragments"]),
    ):
        return False
    return True


def compare(
    run_dir: Path,
    artifact_dir: Path,
    output_path: Path,
    maximum_recordings: int = 12,
) -> dict[str, Any]:
    selection = json.loads((run_dir / "selection.json").read_text("utf-8"))
    if (
        selection.get("selected_on") != "validation_note_events"
        or selection.get("locked_test_used") is not False
    ):
        raise ValueError("Checkpoint selection is not frozen validation-only.")
    config = json.loads((run_dir / "config.json").read_text("utf-8"))
    thresholds = json.loads((run_dir / "thresholds.json").read_text("utf-8"))
    decoder_config = PolyphonicDecoderConfig(**json.loads(
        (run_dir / "decoder_config.json").read_text("utf-8")
    ))
    metadata = json.loads((artifact_dir / "metadata.json").read_text("utf-8"))
    tflite_path = artifact_dir / "guitar_midi_polyphonic.tflite"
    tflite_hash = _sha256(tflite_path)
    if tflite_hash != metadata["artifact"]["sha256"]:
        raise ValueError("TFLite SHA256 does not match metadata.")

    manifest_items = load_manifest(Path(config["dataset"]["manifest"]))
    items = select_evaluation_recordings(
        manifest_items, "validation", maximum_recordings,
    )
    if len(items) != maximum_recordings:
        raise ValueError("The requested validation recording set is incomplete.")
    baseline_path = run_dir / "reports" / "validation_events_epoch-08.json"
    baseline = json.loads(baseline_path.read_text("utf-8"))
    baseline_sources = [row["source_id"] for row in baseline["per_recording"]]
    current_sources = [item.source_id for item in items]
    if current_sources != baseline_sources:
        raise ValueError("Validation recording selection no longer matches selection.")

    model = tf.keras.models.load_model(run_dir / "selected.keras", compile=False)
    inference = tf.keras.Model(
        model.inputs,
        {name: model.get_layer(name).output for name in OUTPUT_NAMES},
    )
    interpreter = tf.lite.Interpreter(model_path=str(tflite_path), num_threads=1)
    interpreter.allocate_tensors()
    runner = interpreter.get_signature_runner("serving_default")

    runtime_rows: dict[str, list[dict[str, Any]]] = {
        "keras": [], "tflite": [],
    }
    all_reference: list[NoteInterval] = []
    all_estimated: dict[str, list[NoteInterval]] = {
        "keras": [], "tflite": [],
    }
    total_retriggers = {"keras": 0, "tflite": 0}
    exact_added = exact_removed = 0
    shift = 0.0

    for item_index, item in enumerate(items):
        corpus = PolyphonicCorpus([item])
        arrays = corpus.labels[0].arrays
        refs = np.column_stack((
            np.zeros(len(arrays["active_bits"]), dtype=np.int32),
            np.arange(len(arrays["active_bits"]), dtype=np.int32),
        ))
        sequence = PolyphonicSequence(
            corpus,
            batch_size=int(config["train"]["batch_size"]),
            input_samples=int(config["dataset"]["input_samples"]),
            normalization_gain=float(config["dataset"]["normalization_gain"]),
            seed=0,
            refs=refs,
            shuffle=False,
        )
        parts = {
            runtime: {name: [] for name in OUTPUT_NAMES}
            for runtime in ("keras", "tflite")
        }
        try:
            for batch_index in range(len(sequence)):
                inputs, _ = sequence[batch_index]
                keras_raw = inference(inputs, training=False)
                for name in OUTPUT_NAMES:
                    parts["keras"][name].append(
                        np.asarray(keras_raw[name], dtype=np.float32)
                    )
                tflite_batch = {name: [] for name in OUTPUT_NAMES}
                for row in range(len(inputs["audio"])):
                    values = runner(
                        audio=inputs["audio"][row:row + 1],
                        time_mask=inputs["time_mask"][row:row + 1],
                    )
                    for name in OUTPUT_NAMES:
                        tflite_batch[name].append(np.asarray(values[name]))
                for name in OUTPUT_NAMES:
                    parts["tflite"][name].append(
                        np.concatenate(tflite_batch[name], axis=0)
                    )
            predictions = {
                runtime: {
                    name: np.concatenate(parts[runtime][name], axis=0)
                    for name in OUTPUT_NAMES
                }
                for runtime in ("keras", "tflite")
            }
            activity_mask, onset_mask, audio_evidence = offline_audio_evidence_masks(
                corpus.audio(0), corpus.sample_rate, corpus.hop_size,
                frame_count=len(refs),
            )
            reference = truth_notes(arrays)
            estimated: dict[str, list[NoteInterval]] = {}
            retriggers: dict[str, int] = {}
            for runtime in ("keras", "tflite"):
                estimated[runtime], retriggers[runtime] = decode_probabilities(
                    predictions[runtime]["frame"],
                    predictions[runtime]["onset"],
                    predictions[runtime]["harmonic_amplitude"],
                    decoder_config,
                    corpus.sample_rate,
                    corpus.hop_size,
                    activity_mask,
                    onset_mask,
                )
        finally:
            corpus.close()

        baseline_intervals = _interval_counter(estimated["keras"])
        candidate_intervals = _interval_counter(estimated["tflite"])
        added = sum((candidate_intervals - baseline_intervals).values())
        removed = sum((baseline_intervals - candidate_intervals).values())
        exact_added += added
        exact_removed += removed
        per_runtime: dict[str, dict[str, Any]] = {}
        for runtime in ("keras", "tflite"):
            onset_matches = match_notes(reference, estimated[runtime])
            offset_matches = match_notes(
                reference, estimated[runtime], require_offset=True,
            )
            row = {
                "source_id": item.source_id,
                "dataset_id": item.dataset_id,
                "group_id": item.group_id,
                "capture_id": item.capture_id,
                "onset": note_metrics(reference, estimated[runtime], onset_matches),
                "onset_offset": note_metrics(
                    reference, estimated[runtime], offset_matches,
                ),
                "retriggers": retriggers[runtime],
                "diagnostics": diagnose_note_errors(
                    reference, estimated[runtime], onset_matches,
                ),
            }
            runtime_rows[runtime].append(row)
            per_runtime[runtime] = row
            total_retriggers[runtime] += retriggers[runtime]
            all_estimated[runtime].extend(_shifted(estimated[runtime], shift))
        all_reference.extend(_shifted(reference, shift))
        shift += (len(refs) + 1) * corpus.hop_size / corpus.sample_rate + 1.0
        print(
            f"recording {item_index + 1}/{len(items)} {item.dataset_id} "
            f"{item.source_id} added={added} removed={removed}",
            flush=True,
        )

    validation_fractions = config["train"]["validation_dataset_fractions"]
    runtime_reports: dict[str, dict[str, Any]] = {}
    for runtime in ("keras", "tflite"):
        onset_matches = match_notes(all_reference, all_estimated[runtime])
        offset_matches = match_notes(
            all_reference, all_estimated[runtime], require_offset=True,
        )
        runtime_reports[runtime] = {
            "onset": note_metrics(
                all_reference, all_estimated[runtime], onset_matches,
            ),
            "onset_offset": note_metrics(
                all_reference, all_estimated[runtime], offset_matches,
            ),
            "dataset_metrics": aggregate_dataset_note_metrics(
                runtime_rows[runtime], validation_fractions,
            ),
            "retriggers": total_retriggers[runtime],
            "diagnostics": diagnose_note_errors(
                all_reference, all_estimated[runtime], onset_matches,
            ),
        }

    keras_report = runtime_reports["keras"]
    tflite_report = runtime_reports["tflite"]
    per_dataset_delta = {
        dataset: {
            metric: {
                "f1_tflite_minus_keras": (
                    float(tflite_report["dataset_metrics"]["per_dataset"]
                          [dataset][metric]["f1"])
                    - float(keras_report["dataset_metrics"]["per_dataset"]
                            [dataset][metric]["f1"])
                )
            }
            for metric in ("onset", "onset_offset")
        }
        for dataset in keras_report["dataset_metrics"]["per_dataset"]
    }
    report = {
        "run_dir": str(run_dir),
        "artifact_dir": str(artifact_dir),
        "split": "validation",
        "locked_test_used": False,
        "thresholds_reselected": False,
        "selection_reused": str(baseline_path),
        "selected_sources": current_sources,
        "recordings": len(items),
        "tflite_sha256": tflite_hash,
        "decoder": asdict(decoder_config),
        "keras": keras_report,
        "tflite": tflite_report,
        "delta": {
            "onset_f1_tflite_minus_keras": (
                float(tflite_report["onset"]["f1"])
                - float(keras_report["onset"]["f1"])
            ),
            "onset_offset_f1_tflite_minus_keras": (
                float(tflite_report["onset_offset"]["f1"])
                - float(keras_report["onset_offset"]["f1"])
            ),
            "false_positive_notes": (
                int(tflite_report["onset"]["false_positive_notes"])
                - int(keras_report["onset"]["false_positive_notes"])
            ),
            "missing_notes": (
                int(tflite_report["onset"]["missing_notes"])
                - int(keras_report["onset"]["missing_notes"])
            ),
            "retriggers": (
                int(tflite_report["retriggers"])
                - int(keras_report["retriggers"])
            ),
            "excess_fragments": (
                int(tflite_report["diagnostics"]["excess_fragments"])
                - int(keras_report["diagnostics"]["excess_fragments"])
            ),
            "exact_intervals_added": exact_added,
            "exact_intervals_removed": exact_removed,
            "per_dataset": per_dataset_delta,
        },
        "policy": {
            "maximum_event_f1_drop_global_and_per_dataset": (
                MAXIMUM_EVENT_F1_DROP
            ),
            "maximum_false_positive_missing_retrigger_fragment_increase": (
                "max(1 note, ceil(1% of Keras baseline))"
            ),
        },
        "passed": event_policy_passes(keras_report, tflite_report),
        "per_recording": [
            {
                "source_id": item.source_id,
                "dataset_id": item.dataset_id,
                "keras": runtime_rows["keras"][index],
                "tflite": runtime_rows["tflite"][index],
            }
            for index, item in enumerate(items)
        ],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--artifact-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--maximum-recordings", type=int, default=12)
    args = parser.parse_args()
    report = compare(
        args.run_dir, args.artifact_dir, args.output, args.maximum_recordings,
    )
    print(json.dumps({
        "split": report["split"],
        "recordings": report["recordings"],
        "keras": report["keras"],
        "tflite": report["tflite"],
        "delta": report["delta"],
        "passed": report["passed"],
    }, indent=2))
    if not report["passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
