"""Bounded, CPU-only, train-only replay for decoder candidate mining.

This module deliberately stops after serializing causal candidate labels and
their provenance counters.  It contains no fitting, calibration, threshold
search, validation-split access, export, live path, or locked-test path.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import TYPE_CHECKING, Any, Mapping, Sequence

import numpy as np
import yaml

from .audio_evidence import offline_audio_evidence_masks
from .decoder import PolyphonicDecoder, PolyphonicDecoderConfig, PolyphonicMidiEvent
from .decoder_candidate_labels import (
    CausalCandidateLabelBatch,
    DecoderCandidateMiningCounters,
    causal_reference_notes_from_label_arrays,
    label_emitted_decoder_candidates,
    require_candidate_mining_baseline_decoder_config,
)

if TYPE_CHECKING:
    # ``data`` imports TensorFlow.  These imports are deliberately type-only:
    # all immutable provenance checks and the CPU preflight must happen before
    # TensorFlow can enter ``sys.modules``.
    from .data import ManifestItem
    from .decoder_candidate_miner import DecoderCandidateMiningContext


BOUNDED_MINING_SCHEMA_VERSION = 1
BOUNDED_MINING_PURPOSE = "decoder_candidate_bounded_train_only_mining_v1"
_PARTITIONS = ("fit", "dev", "calibration")


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_json_object(path: Path, *, description: str) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{description} must be a JSON object.")
    return payload


def _read_model_config(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("model config must be a YAML object.")
    return payload


def _require_sha256(value: object, *, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
    return value


def _require_git_commit(value: object, *, name: str) -> str:
    """Validate a full lowercase Git object ID, not a SHA-256 digest."""
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        raise ValueError(f"{name} must be a lowercase 40-character Git commit SHA.")
    return value


@dataclass(frozen=True)
class BoundedMiningProtocol:
    """Immutable inputs and the intentionally small replay population."""

    manifest_sha256: str
    partition_plan_sha256: str
    asset_evidence_sha256: str
    checkpoint_sha256: str
    model_config_sha256: str
    decoder_config_sha256: str
    audio_evidence_config_sha256: str
    dataset_ids: tuple[str, ...]
    recordings_per_dataset_partition: int
    maximum_attempts_per_recording: int

    @classmethod
    def from_path(cls, path: Path) -> "BoundedMiningProtocol":
        payload = _read_json_object(path, description="bounded mining protocol")
        required = {
            "schema_version",
            "purpose",
            "locked_test_used",
            "manifest_sha256",
            "partition_plan_sha256",
            "asset_evidence_sha256",
            "checkpoint_sha256",
            "model_config_sha256",
            "decoder_config_sha256",
            "audio_evidence_config_sha256",
            "dataset_ids",
            "recordings_per_dataset_partition",
            "maximum_attempts_per_recording",
        }
        if set(payload) != required:
            raise ValueError("bounded mining protocol has unexpected or missing fields.")
        if (
            type(payload["schema_version"]) is not int
            or payload["schema_version"] != BOUNDED_MINING_SCHEMA_VERSION
        ):
            raise ValueError("unsupported bounded mining protocol schema.")
        if payload["purpose"] != BOUNDED_MINING_PURPOSE:
            raise ValueError("invalid bounded mining protocol purpose.")
        if payload["locked_test_used"] is not False:
            raise PermissionError("bounded mining protocol must keep the locked test closed.")
        datasets = payload["dataset_ids"]
        if (
            not isinstance(datasets, list)
            or not datasets
            or any(not isinstance(value, str) or not value for value in datasets)
            or datasets != sorted(set(datasets))
        ):
            raise ValueError("dataset_ids must be a non-empty sorted unique JSON list.")
        for name in (
            "recordings_per_dataset_partition",
            "maximum_attempts_per_recording",
        ):
            if type(payload[name]) is not int or payload[name] <= 0:
                raise ValueError(f"{name} must be a positive JSON-native integer.")
        return cls(
            **{
                name: _require_sha256(payload[name], name=name)
                for name in (
                    "manifest_sha256",
                    "partition_plan_sha256",
                    "asset_evidence_sha256",
                    "checkpoint_sha256",
                    "model_config_sha256",
                    "decoder_config_sha256",
                    "audio_evidence_config_sha256",
                )
            },
            dataset_ids=tuple(datasets),
            recordings_per_dataset_partition=payload["recordings_per_dataset_partition"],
            maximum_attempts_per_recording=payload["maximum_attempts_per_recording"],
        )


def _repository_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _require_expected_git_commit(expected: str, *, repository_root: Path) -> str:
    expected = _require_git_commit(expected, name="expected_git_commit")
    head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=repository_root, text=True
    ).strip()
    if head != expected:
        raise RuntimeError(
            f"Git commit mismatch: expected {expected}, got {head}."
        )
    dirty = subprocess.run(
        ["git", "diff", "--quiet"], cwd=repository_root, check=False
    ).returncode
    staged_dirty = subprocess.run(
        ["git", "diff", "--cached", "--quiet"], cwd=repository_root, check=False
    ).returncode
    untracked = subprocess.check_output(
        ["git", "ls-files", "--others", "--exclude-standard"],
        cwd=repository_root,
        text=True,
    ).strip()
    if dirty != 0 or staged_dirty != 0 or untracked:
        raise RuntimeError("Fail closed: bounded candidate mining requires a clean Git worktree.")
    return head


def _require_cpu_tensorflow() -> Any:
    """Import TensorFlow only after all non-compute provenance checks pass."""
    if os.environ.get("MIDI_FORCE_CPU") != "1":
        raise RuntimeError("Fail closed: bounded candidate mining requires MIDI_FORCE_CPU=1.")
    import tensorflow as tf

    try:
        tf.config.set_visible_devices([], "GPU")
    except RuntimeError as error:
        raise RuntimeError("TensorFlow GPU visibility was initialized before CPU preflight.") from error
    if tf.config.list_logical_devices("GPU"):
        raise RuntimeError("Fail closed: bounded candidate mining must not expose a GPU.")
    return tf


def _load_inference_model(checkpoint: Path, tensorflow: Any) -> Any:
    # Keras model construction remains behind the CPU preflight as well.
    from .keras_compat import load_polyphonic_checkpoint

    model = load_polyphonic_checkpoint(checkpoint)
    output_names = ("frame", "onset", "harmonic_amplitude")
    names = {layer.name for layer in model.layers}
    missing = set(output_names) - names
    if missing:
        raise ValueError(f"checkpoint is missing required inference outputs: {sorted(missing)}")
    return tensorflow.keras.Model(
        model.inputs,
        {name: model.get_layer(name).output for name in output_names},
    )


def _load_mining_context(
    *,
    manifest_path: Path,
    partition_plan_path: Path,
    asset_evidence_path: Path,
) -> "DecoderCandidateMiningContext":
    """Cross the dataset/TensorFlow import boundary after CPU preflight."""
    from .decoder_candidate_miner import load_decoder_candidate_mining_context

    return load_decoder_candidate_mining_context(
        manifest_path=manifest_path,
        partition_plan_path=partition_plan_path,
        asset_evidence_path=asset_evidence_path,
    )


def _resolve_model_manifest(model_config: Mapping[str, object], config_path: Path) -> Path:
    dataset = model_config.get("dataset")
    if not isinstance(dataset, Mapping) or not isinstance(dataset.get("manifest"), str):
        raise ValueError("model config must declare dataset.manifest.")
    manifest = Path(dataset["manifest"])
    if not manifest.is_absolute():
        manifest = (config_path.parent.parent / manifest).resolve()
    return manifest.resolve(strict=True)


def _select_bounded_items(
    context: "DecoderCandidateMiningContext",
    protocol: BoundedMiningProtocol,
) -> tuple["ManifestItem", ...]:
    """Choose a fixed, one-per-corpus-per-partition diagnostic population."""
    selected: list["ManifestItem"] = []
    for partition in _PARTITIONS:
        items = context.items_for_partition(partition)
        by_dataset: dict[str, list["ManifestItem"]] = {}
        for item in items:
            by_dataset.setdefault(str(item.dataset_id), []).append(item)
        if tuple(sorted(by_dataset)) != protocol.dataset_ids:
            raise RuntimeError(
                "Fail closed: bounded mining plan datasets differ from the protocol."
            )
        for dataset_id in protocol.dataset_ids:
            eligible = sorted(
                by_dataset[dataset_id],
                key=lambda item: (
                    str(item.dataset_id),
                    str(item.source_id),
                    str(item.capture_id),
                ),
            )
            if len(eligible) < protocol.recordings_per_dataset_partition:
                raise RuntimeError(
                    "Fail closed: plan has fewer recordings than the fixed bounded "
                    f"population for {partition}/{dataset_id}."
                )
            selected.extend(eligible[:protocol.recordings_per_dataset_partition])
    expected = len(_PARTITIONS) * len(protocol.dataset_ids) * protocol.recordings_per_dataset_partition
    if len(selected) != expected:
        raise AssertionError("bounded selection did not reconcile its fixed size.")
    identities = [
        (str(item.dataset_id), str(item.source_id), str(item.capture_id))
        for item in selected
    ]
    if len(set(identities)) != len(identities):
        raise RuntimeError("Fail closed: bounded mining selection repeats a recording.")
    return tuple(selected)


def _require_protocol_inputs(
    protocol: BoundedMiningProtocol,
    *,
    manifest_path: Path,
    partition_plan_path: Path,
    asset_evidence_path: Path,
    checkpoint_path: Path,
    model_config_path: Path,
    decoder_config_path: Path,
    audio_evidence_config_path: Path,
) -> tuple[dict[str, object], PolyphonicDecoderConfig, dict[str, object]]:
    paths = {
        "manifest_sha256": manifest_path,
        "partition_plan_sha256": partition_plan_path,
        "asset_evidence_sha256": asset_evidence_path,
        "checkpoint_sha256": checkpoint_path,
        "model_config_sha256": model_config_path,
        "decoder_config_sha256": decoder_config_path,
        "audio_evidence_config_sha256": audio_evidence_config_path,
    }
    for field, path in paths.items():
        resolved = path.resolve(strict=True)
        if _sha256_file(resolved) != getattr(protocol, field):
            raise RuntimeError(f"Fail closed: {field} does not match the protocol.")
    model_config = _read_model_config(model_config_path)
    decoder_payload = _read_json_object(decoder_config_path, description="decoder config")
    require_candidate_mining_baseline_decoder_config(decoder_payload)
    decoder_config = PolyphonicDecoderConfig(**decoder_payload)
    audio_evidence = _read_json_object(
        audio_evidence_config_path, description="audio evidence config"
    )
    return model_config, decoder_config, audio_evidence


def _predict_recording(
    inference_model: Any,
    context: "DecoderCandidateMiningContext",
    item: "ManifestItem",
    *,
    model_config: Mapping[str, object],
    decoder_config: PolyphonicDecoderConfig,
    audio_evidence_config: Mapping[str, object],
    maximum_attempts: int,
) -> tuple[CausalCandidateLabelBatch, list[dict[str, object]], dict[str, object]]:
    # Both imports transitively depend on ``data``/TensorFlow.  They must stay
    # after the sealed file checks and ``_require_cpu_tensorflow()``.
    from .data import PolyphonicSequence
    from .keras_compat import predict_compat

    dataset = model_config["dataset"]
    train = model_config["train"]
    if not isinstance(dataset, Mapping) or not isinstance(train, Mapping):
        raise ValueError("model config dataset/train sections must be mappings.")
    collector = context.collector_for_item(item, maximum_attempts=maximum_attempts)
    with context.open_recording(item) as corpus:
        arrays = corpus.labels[0].arrays
        frame_count = len(arrays["active_bits"])
        refs = np.column_stack((
            np.zeros(frame_count, dtype=np.int32),
            np.arange(frame_count, dtype=np.int32),
        ))
        sequence = PolyphonicSequence(
            corpus,
            batch_size=int(train["batch_size"]),
            input_samples=int(dataset["input_samples"]),
            normalization_gain=float(dataset["normalization_gain"]),
            seed=0,
            refs=refs,
            shuffle=False,
        )
        prediction = predict_compat(inference_model, sequence, verbose=0, workers=1)
        if not isinstance(prediction, Mapping):
            raise ValueError("inference model must return named frame/onset/harmonic outputs.")
        required = {"frame", "onset", "harmonic_amplitude"}
        if set(prediction) != required:
            raise ValueError("inference output names differ from the bounded mining contract.")
        outputs = {name: np.asarray(prediction[name]) for name in required}
        if any(values.shape[0] != frame_count for values in outputs.values()):
            raise ValueError("inference frame count does not match the sealed label arrays.")
        audio = corpus.audio(0)
        active, onset, audio_report = offline_audio_evidence_masks(
            audio,
            corpus.sample_rate,
            corpus.hop_size,
            frame_count=frame_count,
            metadata={"audio_evidence": dict(audio_evidence_config)},
        )
        decoder = PolyphonicDecoder(decoder_config, candidate_collector=collector)
        events: list[PolyphonicMidiEvent] = []
        for frame_index in range(frame_count):
            events.extend(decoder.step(
                outputs["frame"][frame_index],
                outputs["onset"][frame_index],
                outputs["harmonic_amplitude"][frame_index],
                audio_active=bool(active[frame_index]),
                audio_hop_index=frame_index,
                audio_onset=bool(onset[frame_index]),
                audio_onset_hop_index=(frame_index if bool(onset[frame_index]) else None),
            ))
        events.extend(decoder.panic(reason="bounded_mining_end"))
        label_batch = label_emitted_decoder_candidates(
            collector.drain(),
            causal_reference_notes_from_label_arrays(arrays),
            frame_valid=arrays["valid"],
            sample_rate=corpus.sample_rate,
            hop_size=corpus.hop_size,
            audio_frames=int(arrays["audio_frames"]),
            emitted_events=events,
            candidate_collection_error=decoder.candidate_collection_error,
        )
    label_batch.require_complete()
    rows = [label.as_json() for label in label_batch.labels]
    batch_summary = {
        field.name: getattr(label_batch, field.name)
        for field in fields(label_batch)
        if field.name != "labels"
    }
    batch_summary["dataset_id"] = item.dataset_id
    batch_summary["source_id"] = item.source_id
    batch_summary["group_id"] = item.group_id
    batch_summary["capture_id"] = item.capture_id
    batch_summary["audio_evidence"] = audio_report
    return label_batch, rows, batch_summary


def _counter_json(counters: DecoderCandidateMiningCounters) -> dict[str, object]:
    return asdict(counters)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _write_candidate_rows(path: Path, rows: Sequence[Mapping[str, object]]) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def run_bounded_train_only_mining(
    *,
    manifest_path: Path,
    partition_plan_path: Path,
    asset_evidence_path: Path,
    checkpoint_path: Path,
    model_config_path: Path,
    decoder_config_path: Path,
    audio_evidence_config_path: Path,
    protocol_path: Path,
    output_dir: Path,
    expected_git_commit: str,
    repository_root: Path | None = None,
) -> dict[str, object]:
    """Mine the fixed 12-recording train-only diagnostic population once.

    The output is a non-authorizing diagnostic candidate corpus.  A separate,
    reviewed future step would be required to fit any model from it.
    """
    root = (repository_root or _repository_root()).resolve(strict=True)
    protocol = BoundedMiningProtocol.from_path(protocol_path.resolve(strict=True))
    commit = _require_expected_git_commit(expected_git_commit, repository_root=root)
    derived_root = (root / "data" / "processed").resolve(strict=True)
    destination = output_dir.resolve(strict=False)
    try:
        destination.relative_to(derived_root)
    except ValueError as error:
        raise ValueError("bounded candidate output must be written below data/processed.") from error
    if destination.exists():
        raise FileExistsError("bounded candidate output already exists; refusing overwrite.")
    if not destination.parent.is_dir():
        raise FileNotFoundError(destination.parent)

    model_config, decoder_config, audio_evidence_config = _require_protocol_inputs(
        protocol,
        manifest_path=manifest_path,
        partition_plan_path=partition_plan_path,
        asset_evidence_path=asset_evidence_path,
        checkpoint_path=checkpoint_path,
        model_config_path=model_config_path,
        decoder_config_path=decoder_config_path,
        audio_evidence_config_path=audio_evidence_config_path,
    )
    if _resolve_model_manifest(model_config, model_config_path) != manifest_path.resolve(strict=True):
        raise RuntimeError("Fail closed: model config manifest differs from the sealed mining manifest.")

    # This is intentionally the first point at which TensorFlow may be
    # imported.  The protocol, seven sealed file digests, and the model-YAML
    # manifest binding above are all pure-Python checks.
    tensorflow = _require_cpu_tensorflow()
    context = _load_mining_context(
        manifest_path=manifest_path,
        partition_plan_path=partition_plan_path,
        asset_evidence_path=asset_evidence_path,
    )
    if context.snapshot.manifest_sha256 != protocol.manifest_sha256:
        raise RuntimeError("Fail closed: validated context manifest differs from protocol.")
    if context.persisted_plan.sha256 != protocol.partition_plan_sha256:
        raise RuntimeError("Fail closed: validated context plan differs from protocol.")
    if (
        context.persisted_asset_evidence is None
        or context.persisted_asset_evidence.sha256 != protocol.asset_evidence_sha256
    ):
        raise RuntimeError("Fail closed: validated context asset evidence differs from protocol.")
    selected = _select_bounded_items(context, protocol)

    inference_model = _load_inference_model(checkpoint_path.resolve(strict=True), tensorflow)
    batches: list[CausalCandidateLabelBatch] = []
    candidate_rows: list[dict[str, object]] = []
    recording_reports: list[dict[str, object]] = []
    for item in selected:
        batch, rows, recording_report = _predict_recording(
            inference_model,
            context,
            item,
            model_config=model_config,
            decoder_config=decoder_config,
            audio_evidence_config=audio_evidence_config,
            maximum_attempts=protocol.maximum_attempts_per_recording,
        )
        batches.append(batch)
        candidate_rows.extend(rows)
        recording_reports.append(recording_report)
    counters = DecoderCandidateMiningCounters.from_batches(batches)
    by_partition = {
        partition: _counter_json(DecoderCandidateMiningCounters.from_batches(
            batch for batch in batches if batch.partition == partition
        ))
        for partition in _PARTITIONS
    }
    partial = destination.parent / f".{destination.name}.partial-{os.getpid()}"
    if partial.exists():
        raise FileExistsError(f"refusing to reuse partial output directory: {partial}")
    try:
        partial.mkdir()
        rows_path = partial / "candidate_events.jsonl"
        _write_candidate_rows(rows_path, candidate_rows)
        report = {
            "schema_version": 1,
            "purpose": BOUNDED_MINING_PURPOSE,
            "status": "complete_non_authorizing",
            "locked_test_used": False,
            "implementation_commit": commit,
            "protocol": asdict(protocol),
            "input_paths": {
                "manifest": str(manifest_path.resolve(strict=True)),
                "partition_plan": str(partition_plan_path.resolve(strict=True)),
                "asset_evidence": str(asset_evidence_path.resolve(strict=True)),
                "checkpoint": str(checkpoint_path.resolve(strict=True)),
                "model_config": str(model_config_path.resolve(strict=True)),
                "decoder_config": str(decoder_config_path.resolve(strict=True)),
                "audio_evidence_config": str(audio_evidence_config_path.resolve(strict=True)),
            },
            "selection": {
                "policy": "first_canonical_plan_item_per_dataset_partition_v1",
                "recordings": [
                    {
                        "dataset_id": item.dataset_id,
                        "source_id": item.source_id,
                        "group_id": item.group_id,
                        "capture_id": item.capture_id,
                        "partition": context.validated_snapshot.provenance_for_snapshot_item(item).partition,
                    }
                    for item in selected
                ],
            },
            "candidate_events": {
                "path": rows_path.name,
                "sha256": _sha256_file(rows_path),
                "rows": len(candidate_rows),
            },
            "counters": _counter_json(counters),
            "counters_by_partition": by_partition,
            "recordings": recording_reports,
            "fit_authorized": False,
            "next_action": (
                "Review only: this bounded train-only mining artifact does not "
                "authorize fitting, calibration, validation, export, live use, "
                "threshold selection, or locked-test access."
            ),
        }
        _write_json(partial / "mining_report.json", report)
        os.replace(partial, destination)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run one fixed, CPU-only, train-only decoder-candidate mining diagnostic."
    )
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--partition-plan", type=Path, required=True)
    parser.add_argument("--asset-evidence", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--model-config", type=Path, required=True)
    parser.add_argument("--decoder-config", type=Path, required=True)
    parser.add_argument("--audio-evidence-config", type=Path, required=True)
    parser.add_argument("--protocol", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-git-commit", required=True)
    args = parser.parse_args()
    result = run_bounded_train_only_mining(
        manifest_path=args.manifest,
        partition_plan_path=args.partition_plan,
        asset_evidence_path=args.asset_evidence,
        checkpoint_path=args.checkpoint,
        model_config_path=args.model_config,
        decoder_config_path=args.decoder_config,
        audio_evidence_config_path=args.audio_evidence_config,
        protocol_path=args.protocol,
        output_dir=args.output_dir,
        expected_git_commit=args.expected_git_commit,
    )
    print(json.dumps({
        "status": result["status"],
        "locked_test_used": result["locked_test_used"],
        "candidate_rows": result["candidate_events"]["rows"],
        "output_dir": str(args.output_dir),
    }, sort_keys=True))


if __name__ == "__main__":
    main()
