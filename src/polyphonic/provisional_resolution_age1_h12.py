"""Concrete, non-injectable H12 binding for the future H7 discovery.

Importing this module is zero-science: TensorFlow, the model, audio and labels
remain behind the separately authorized real entrypoint.
"""
from __future__ import annotations

from dataclasses import dataclass
import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
from typing import Any, Mapping, Sequence
from zipfile import ZipFile

from .provisional_resolution_age1 import (
    PassiveAge1SignalCollector,
    extract_exact_causal_age1_targets,
)
from .provisional_resolution_age1_h11 import (
    H11DecodedRecording,
    H11Recording,
    require_h11_cohort,
    require_raw_sha256s,
    run_h11_once,
    sha256_file,
)
from .provisional_resolution_age1_metrics import evaluate_h7_synthetic_metrics


H11_CONTRACT_RELATIVE = Path("configs/provisional_resolution_age1_persistence_h11_execution_contract.json")
H11_CONTRACT_SHA256 = "ea6032e1e2cbd3da8a9bd2facb864df6eea5740692d00f952353d399b1facf8e"
H8_COHORT_RELATIVE = Path("configs/provisional_resolution_age1_persistence_h8_selected_cohort.json")
H8_COHORT_SHA256 = "4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f"
MANIFEST_SHA256 = "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
PLAN_SHA256 = "a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4"
ASSET_EVIDENCE_SHA256 = "12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507"
CHECKPOINT_SHA256 = "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
MODEL_CONFIG_SHA256 = "245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804"
DECODER_RAW_SHA256 = "c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96"
AUDIO_POLICY_SHA256 = "45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e"
DECODER_CANONICAL_SHA256 = "7f6a93b566c2e042ec943821b5d35bdaa9151fe97711cd9463704aba20de178d"
HISTORICAL_DECODER_BLOB = "4233186147c0946372ddb2e9e3dd3343daeb26eb"
INSTRUMENTED_DECODER_BLOB = "27026d368081fadc4fa282954428f0377020e723"
H9_IMPLEMENTATION_BLOB = "22b93d2b5a6e2a3826eddc4aee0057d68fe34141"
H10_METRIC_BLOB = "5e40574dab4a53e0ce5b2288536d337f0da66fa9"
H11_ORCHESTRATOR_BLOB = "6ea9ba6637788552b5f3318b1f2dfac6fd52f71e"
H7_COMMIT = "e3e2be144282ecf0079ba22831abfb6439b16ac3"


@dataclass(frozen=True)
class SealedH8Recording:
    h11: H11Recording
    dataset_id: str
    source_id: str
    group_id: str
    capture_id: str
    audio_path_identity: str
    audio_member_identity: str
    labels_path_identity: str
    labels_member_identity: str


@dataclass(frozen=True)
class H12Paths:
    repository_root: Path
    worker_root: Path
    h11_contract: Path
    h8_cohort: Path
    manifest: Path
    partition_plan: Path
    asset_evidence: Path
    checkpoint: Path
    model_config: Path
    decoder_config: Path
    audio_policy: Path
    authorization_marker: Path
    result_destination: Path


def sealed_h12_paths(repository_root: Path, worker_root: Path) -> H12Paths:
    repo = Path(repository_root).resolve(strict=True)
    worker = Path(worker_root).resolve(strict=True)
    if repo != (worker / "repository").resolve(strict=True):
        raise RuntimeError("H12 requires the canonical Mac worker repository.")
    prereg = repo / "tmp" / "local" / "decoder_candidate_policy_a_preregistration_20260809"
    return H12Paths(
        repository_root=repo,
        worker_root=worker,
        h11_contract=repo / H11_CONTRACT_RELATIVE,
        h8_cohort=repo / H8_COHORT_RELATIVE,
        manifest=worker / "data" / "processed" / "polyphonic_harmonic_presence_v1" / "manifest_train_validation.csv",
        partition_plan=prereg / "decoder_candidate_partition_plan_v2.json",
        asset_evidence=prereg / "decoder_candidate_asset_evidence_v1.json",
        checkpoint=worker / "checkpoints" / f"{CHECKPOINT_SHA256}.keras",
        model_config=repo / "configs" / "polyphonic_dual_stream_bass_independent_note.yaml",
        decoder_config=repo / "configs" / "independent_note_decoder_reference.json",
        audio_policy=repo / "configs" / "polyphonic_audio_evidence_adaptive_temporal.json",
        authorization_marker=repo / "tmp" / "local" / "provisional_resolution_age1_h7_discovery_authorization.json",
        result_destination=repo / "tmp" / "local" / "provisional_resolution_age1_h7_discovery_result",
    )


def _git_blob(repository_root: Path, revision_path: str) -> str:
    return subprocess.check_output(
        ["git", "rev-parse", revision_path], cwd=repository_root, text=True
    ).strip()


def require_h12_source_bindings(repository_root: Path) -> None:
    expected = {
        "HEAD:src/polyphonic/decoder.py": INSTRUMENTED_DECODER_BLOB,
        "HEAD:src/polyphonic/provisional_resolution_age1.py": H9_IMPLEMENTATION_BLOB,
        "HEAD:src/polyphonic/provisional_resolution_age1_metrics.py": H10_METRIC_BLOB,
        "HEAD:src/polyphonic/provisional_resolution_age1_h11.py": H11_ORCHESTRATOR_BLOB,
        f"{H7_COMMIT}:src/polyphonic/decoder.py": HISTORICAL_DECODER_BLOB,
    }
    for revision_path, blob in expected.items():
        if _git_blob(repository_root, revision_path) != blob:
            raise RuntimeError(f"H12 source binding mismatch: {revision_path}")


def _text(value: object, name: str, *, allow_empty: bool = False) -> str:
    if not isinstance(value, str) or value != value.strip() or (not allow_empty and not value):
        raise ValueError(f"H8 {name} is not canonical text.")
    return value


def _load_h8_metadata(path: Path) -> tuple[tuple[SealedH8Recording, ...], tuple[str, ...]]:
    if sha256_file(path) != H8_COHORT_SHA256:
        raise RuntimeError("H12 H8 selected-cohort SHA-256 mismatch.")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("locked_test_used") is not False or payload.get("consumed_v2_cohort_used") is not False:
        raise RuntimeError("H12 H8 metadata is contaminated.")
    raw_records = payload.get("recordings")
    if not isinstance(raw_records, list):
        raise ValueError("H8 recordings must be a list.")
    records = []
    for raw in raw_records:
        if not isinstance(raw, dict):
            raise ValueError("H8 recording row must be an object.")
        h11 = H11Recording(
            recording_key=_text(raw.get("recording_key"), "recording_key"),
            corpus_category=_text(raw.get("corpus_category"), "corpus_category"),
            leakage_group_key=_text(raw.get("leakage_group_key"), "leakage_group_key"),
            partition=_text(raw.get("partition"), "partition"),
            audio_size_bytes=raw.get("audio_size_bytes"),
            audio_sha256=_text(raw.get("audio_sha256"), "audio_sha256"),
            labels_size_bytes=raw.get("labels_size_bytes"),
            labels_sha256=_text(raw.get("labels_sha256"), "labels_sha256"),
            source_manifest_sha256=_text(raw.get("source_manifest_sha256"), "source_manifest_sha256"),
            source_partition_plan_sha256=_text(raw.get("source_partition_plan_sha256"), "source_partition_plan_sha256"),
            audio_member_identity=_text(raw.get("audio_member_identity"), "audio_member_identity", allow_empty=True),
        )
        records.append(SealedH8Recording(
            h11=h11,
            dataset_id=_text(raw.get("dataset_id"), "dataset_id"),
            source_id=_text(raw.get("source_id"), "source_id"),
            group_id=_text(raw.get("group_id"), "group_id"),
            capture_id=_text(raw.get("capture_id"), "capture_id"),
            audio_path_identity=_text(raw.get("audio_path_identity"), "audio_path_identity"),
            audio_member_identity=h11.audio_member_identity,
            labels_path_identity=_text(raw.get("labels_path_identity"), "labels_path_identity"),
            labels_member_identity=_text(raw.get("labels_member_identity"), "labels_member_identity", allow_empty=True),
        ))
    forbidden = payload.get("forbidden_cohorts")
    if not isinstance(forbidden, dict):
        raise ValueError("H8 forbidden_cohorts must be an object.")
    groups: set[str] = set()
    for name in ("consumed_v2", "locked_test"):
        block = forbidden.get(name)
        if not isinstance(block, dict) or not isinstance(block.get("leakage_group_keys"), list):
            raise ValueError("H8 forbidden cohort group keys are missing.")
        groups.update(_text(value, "forbidden_group") for value in block["leakage_group_keys"])
    checked = require_h11_cohort(
        [record.h11 for record in records], forbidden_groups=tuple(groups),
        expected_manifest_sha256=MANIFEST_SHA256, expected_plan_sha256=PLAN_SHA256,
    )
    by_key = {record.h11.recording_key: record for record in records}
    return tuple(by_key[item.recording_key] for item in checked), tuple(sorted(groups))


def h8_group_universe(records: Sequence[SealedH8Recording]) -> tuple[str, ...]:
    """Return the immutable group universe encoded by sealed H8 metadata."""
    groups = tuple(sorted({record.h11.leakage_group_key for record in records}))
    if len(groups) != 31:
        raise RuntimeError("H13 real H8 group universe must contain exactly 31 groups.")
    return groups


def _asset_path(worker_root: Path, identity: str) -> Path:
    root = (worker_root / "data").resolve(strict=True)
    path = (root / identity).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as error:
        raise RuntimeError("H12 asset path escapes the worker data root.") from error
    return path


def verify_h8_asset_bytes(paths: H12Paths, records: Sequence[SealedH8Recording]) -> None:
    verified_files: dict[Path, tuple[int, str]] = {}
    archive_members: dict[Path, set[str]] = {}
    for record in records:
        audio = _asset_path(paths.worker_root, record.audio_path_identity)
        labels = _asset_path(paths.worker_root, record.labels_path_identity)
        for name, path, size, digest in (
            ("audio", audio, record.h11.audio_size_bytes, record.h11.audio_sha256),
            ("labels", labels, record.h11.labels_size_bytes, record.h11.labels_sha256),
        ):
            evidence = verified_files.get(path)
            if evidence is None:
                evidence = (path.stat().st_size, sha256_file(path))
                verified_files[path] = evidence
            if evidence != (size, digest):
                raise RuntimeError(f"H12 {name} byte evidence mismatch: {record.h11.recording_key}")
        if record.audio_member_identity:
            members = archive_members.get(audio)
            if members is None:
                with ZipFile(audio) as archive:
                    members = set(archive.namelist())
                archive_members[audio] = members
            if record.audio_member_identity not in members:
                raise RuntimeError(
                    f"H12 archive member mismatch: {record.h11.recording_key}"
                )
        if record.labels_member_identity:
            raise RuntimeError("H12 does not permit archived label members.")


def runtime_identity() -> dict[str, str]:
    return {
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "tensorflow": importlib.metadata.version("tensorflow"),
        "macos": platform.mac_ver()[0],
        "darwin": platform.release(),
        "architecture": platform.machine(),
        "device": "cpu" if os.environ.get("MIDI_FORCE_CPU") == "1" else "not_cpu_forced",
    }


def require_h12_runtime(identity: Mapping[str, str]) -> None:
    expected = {
        "python": "3.11.9", "numpy": "1.26.4", "tensorflow": "2.15.1",
        "macos": "15.5", "darwin": "24.5.0", "architecture": "arm64", "device": "cpu",
    }
    if dict(identity) != expected:
        raise RuntimeError("H12 frozen runtime identity mismatch.")


def require_h12_config_payloads(paths: H12Paths) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    import yaml
    model = yaml.safe_load(paths.model_config.read_text(encoding="utf-8"))
    decoder = json.loads(paths.decoder_config.read_text(encoding="utf-8"))
    audio = json.loads(paths.audio_policy.read_text(encoding="utf-8"))
    if not all(isinstance(value, dict) for value in (model, decoder, audio)):
        raise RuntimeError("H12 frozen config payload type mismatch.")
    canonical = json.dumps(decoder, sort_keys=True, separators=(",", ":")).encode("utf-8")
    if hashlib.sha256(canonical).hexdigest() != DECODER_CANONICAL_SHA256:
        raise RuntimeError("H12 decoder canonical SHA-256 mismatch.")
    dataset = model.get("dataset")
    train = model.get("train")
    if not isinstance(dataset, dict) or not isinstance(train, dict):
        raise RuntimeError("H12 model config dataset/train sections are missing.")
    if (
        dataset.get("input_samples") != 8192
        or float(dataset.get("normalization_gain", -1.0)) != 1.4932045250002872
        or train.get("batch_size") != 32
        or decoder.get("independent_note_threshold") is not None
        or decoder.get("midi_min") != 40
        or decoder.get("midi_max") != 76
        or audio != {"onset_adapt_temporal_background": True}
    ):
        raise RuntimeError("H12 frozen config semantic binding mismatch.")
    return model, decoder, audio


def _run_h12_preflight(
    paths: H12Paths, *, authorization_marker_must_be_absent: bool
) -> dict[str, object]:
    if sha256_file(paths.h11_contract) != H11_CONTRACT_SHA256:
        raise RuntimeError("H12 H11 contract raw SHA-256 mismatch.")
    require_h12_source_bindings(paths.repository_root)
    require_raw_sha256s(
        {
            "manifest": paths.manifest, "partition_plan": paths.partition_plan,
            "asset_evidence": paths.asset_evidence, "checkpoint": paths.checkpoint,
            "model_config": paths.model_config, "decoder_config": paths.decoder_config,
            "audio_policy": paths.audio_policy,
        },
        {
            "manifest": MANIFEST_SHA256, "partition_plan": PLAN_SHA256,
            "asset_evidence": ASSET_EVIDENCE_SHA256, "checkpoint": CHECKPOINT_SHA256,
            "model_config": MODEL_CONFIG_SHA256, "decoder_config": DECODER_RAW_SHA256,
            "audio_policy": AUDIO_POLICY_SHA256,
        },
    )
    require_h12_config_payloads(paths)
    records, forbidden = _load_h8_metadata(paths.h8_cohort)
    group_universe = h8_group_universe(records)
    verify_h8_asset_bytes(paths, records)
    identity = runtime_identity()
    require_h12_runtime(identity)
    if authorization_marker_must_be_absent:
        guarded = (paths.authorization_marker,)
    else:
        if not paths.authorization_marker.is_file():
            raise PermissionError("H12 real execution requires the separate authorization marker.")
        guarded = ()
    for path in guarded + (
        paths.authorization_marker.with_suffix(paths.authorization_marker.suffix + ".claimed"),
        paths.result_destination,
        paths.result_destination.with_suffix(paths.result_destination.suffix + ".failure.json"),
    ):
        if path.exists():
            raise FileExistsError(f"H12 preflight requires absent path: {path}")
    return {
        "status": "h7_real_execution_preflight_ready",
        "recordings": len(records),
        "leakage_groups": len(group_universe),
        "forbidden_groups": len(forbidden),
        "runtime": identity,
        "scientific_execution_authorized": False,
        "execution_marker_created": False,
        "h8_scientific_assets_opened": False,
        "h8_discovery_consumed": False,
        "real_targets_extracted": False,
        "real_signals_extracted": False,
        "real_metrics_computed": False,
    }


def run_h12_preflight(repository_root: Path, worker_root: Path) -> dict[str, object]:
    """Hash and validate metadata only; never import TensorFlow or parse science."""
    return _run_h12_preflight(
        sealed_h12_paths(repository_root, worker_root),
        authorization_marker_must_be_absent=True,
    )


class ConcreteH7ScientificAdapter:
    """The only production adapter; all scientific dependencies are internal."""

    def __init__(self, paths: H12Paths, records: Sequence[SealedH8Recording]) -> None:
        self.paths = paths
        self.records = {record.h11.recording_key: record for record in records}
        self._model = None
        self._tensorflow = None
        self._config = None
        self._decoder_config = None
        self._audio_policy = None

    def _sealed(self, recording: H11Recording) -> SealedH8Recording:
        sealed = self.records.get(recording.recording_key)
        if sealed is None or sealed.h11 != recording:
            raise RuntimeError("H12 adapter recording differs from sealed H8 metadata.")
        return sealed

    def verify_provenance(self, recording: H11Recording) -> None:
        verify_h8_asset_bytes(self.paths, (self._sealed(recording),))

    def _manifest_item(self, recording: H11Recording) -> Any:
        from .manifest_snapshot import ManifestItem
        sealed = self._sealed(recording)
        return ManifestItem(
            source_id=sealed.source_id, dataset_id=sealed.dataset_id, player_id="",
            group_id=sealed.group_id, split="train",
            audio_path=_asset_path(self.paths.worker_root, sealed.audio_path_identity),
            audio_member=sealed.audio_member_identity,
            labels_path=_asset_path(self.paths.worker_root, sealed.labels_path_identity),
            capture_id=sealed.capture_id, license_id="",
        )

    def open_recording(self, recording: H11Recording) -> Any:
        from .data import PolyphonicCorpus
        return PolyphonicCorpus((self._manifest_item(recording),))

    def _load_configuration_and_model(self) -> None:
        if self._model is not None:
            return
        if os.environ.get("MIDI_FORCE_CPU") != "1":
            raise RuntimeError("H12 real execution requires MIDI_FORCE_CPU=1.")
        import tensorflow as tf
        from .mine_decoder_candidates import _load_inference_model
        tf.config.set_visible_devices([], "GPU")
        if tf.config.list_logical_devices("GPU"):
            raise RuntimeError("H12 real execution exposed a TensorFlow GPU.")
        self._tensorflow = tf
        self._config, self._decoder_config, self._audio_policy = require_h12_config_payloads(self.paths)
        self._model = _load_inference_model(self.paths.checkpoint, tf)

    def infer_once(self, opened: Any) -> Any:
        self._load_configuration_and_model()
        import numpy as np
        from .data import PolyphonicSequence
        from .keras_compat import predict_compat
        arrays = opened.labels[0].arrays
        frame_count = len(arrays["active_bits"])
        refs = np.column_stack((np.zeros(frame_count, np.int32), np.arange(frame_count, dtype=np.int32)))
        dataset = self._config["dataset"]
        train = self._config["train"]
        sequence = PolyphonicSequence(
            opened, batch_size=int(train["batch_size"]),
            input_samples=int(dataset["input_samples"]),
            normalization_gain=float(dataset["normalization_gain"]),
            seed=0, refs=refs, shuffle=False,
        )
        prediction = predict_compat(self._model, sequence, verbose=0, workers=1)
        if not isinstance(prediction, Mapping) or set(prediction) != {"frame", "onset", "harmonic_amplitude"}:
            raise RuntimeError("H12 inference output contract mismatch.")
        result = {name: np.asarray(prediction[name]) for name in prediction}
        if any(values.shape[0] != frame_count for values in result.values()):
            raise RuntimeError("H12 inference frame count mismatch.")
        return result

    def decode_once(self, opened: Any, predictions: Any, recording: H11Recording) -> H11DecodedRecording:
        from .audio_evidence import offline_audio_evidence_masks
        from .decoder import PolyphonicDecoder, PolyphonicDecoderConfig
        self._sealed(recording)
        arrays = opened.labels[0].arrays
        frame_count = len(arrays["active_bits"])
        audio = opened.audio(0)
        active, onset, _ = offline_audio_evidence_masks(
            audio, opened.sample_rate, opened.hop_size, frame_count=frame_count,
            metadata={"audio_evidence": dict(self._audio_policy)},
        )
        collector = PassiveAge1SignalCollector()
        config = PolyphonicDecoderConfig(**dict(self._decoder_config))
        if config.independent_note_threshold is not None:
            raise RuntimeError("H12 baseline independent-note gate must be disabled.")
        decoder = PolyphonicDecoder(
            config, passive_age1_collector=collector,
            provisional_state_resolver=None, causal_candidate_gate=None,
        )
        events = []
        for frame_index in range(frame_count):
            events.extend(decoder.step(
                predictions["frame"][frame_index], predictions["onset"][frame_index],
                predictions["harmonic_amplitude"][frame_index],
                audio_active=bool(active[frame_index]), audio_hop_index=frame_index,
                audio_onset=bool(onset[frame_index]),
                audio_onset_hop_index=(frame_index if bool(onset[frame_index]) else None),
            ))
        collector.require_no_pending_age1_at_end()
        events.extend(decoder.panic(reason="h7_discovery_end"))
        return H11DecodedRecording(tuple(events), collector.records, collector.pending_count)

    def extract_targets(self, opened: Any, emitted_events: Sequence[Any]) -> Sequence[Any]:
        from .causal_event_metrics import ReferenceNote
        from .evaluate_events import truth_notes
        arrays = opened.labels[0].arrays
        references = tuple(
            ReferenceNote(note.pitch, note.start_s, note.end_s)
            for note in truth_notes(arrays)
        )
        return extract_exact_causal_age1_targets(
            emitted_events, references, frame_valid=arrays["valid"],
            sample_rate=opened.sample_rate, hop_size=opened.hop_size,
            audio_frames=int(arrays["audio_frames"]),
        )


def run_real_h7_discovery() -> tuple[Any, Any]:
    """Compatibility entrypoint delegated to the final H13 execution seal."""
    from .provisional_resolution_age1_h13 import run_real_h7_discovery as run_h13
    return run_h13()


def main() -> None:
    parser = argparse.ArgumentParser(description="Sealed H7 discovery runner.")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    repository_root = Path(__file__).resolve().parents[2]
    data_root = os.environ.get("MIDI_DATA_ROOT")
    if not data_root:
        raise RuntimeError("H12 requires MIDI_DATA_ROOT from the Mac worker.")
    worker_root = Path(data_root).resolve(strict=True).parent
    if args.preflight_only:
        print(json.dumps(
            run_h12_preflight(repository_root, worker_root),
            sort_keys=True, separators=(",", ":"),
        ))
        return
    run_real_h7_discovery()


__all__ = [
    "AUDIO_POLICY_SHA256", "CHECKPOINT_SHA256", "ConcreteH7ScientificAdapter",
    "DECODER_CANONICAL_SHA256", "DECODER_RAW_SHA256", "H10_METRIC_BLOB", "H11_CONTRACT_SHA256", "H11_ORCHESTRATOR_BLOB", "H12Paths",
    "H8_COHORT_SHA256", "H9_IMPLEMENTATION_BLOB", "HISTORICAL_DECODER_BLOB", "h8_group_universe",
    "INSTRUMENTED_DECODER_BLOB", "MANIFEST_SHA256", "MODEL_CONFIG_SHA256",
    "PLAN_SHA256", "SealedH8Recording", "require_h12_config_payloads", "require_h12_runtime",
    "require_h12_source_bindings", "run_h12_preflight", "run_real_h7_discovery",
    "runtime_identity", "sealed_h12_paths", "verify_h8_asset_bytes",
]


if __name__ == "__main__":
    main()
