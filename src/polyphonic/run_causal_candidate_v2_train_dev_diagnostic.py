"""Sealed CPU-only runner for the exploratory V2 train/dev diagnostic.

The module is inert on import and deliberately exposes neither a CLI nor
caller-provided paths, recordings, model weights, threshold, or placement.  A
separately reviewed Mac-worker invocation is required before it can open the
approved 30 train/dev captures.  The run stops after one descriptive A/B
report; it cannot fit, calibrate, promote, export, use live input, or open the
locked test.
"""
from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
from typing import Mapping, Sequence

import numpy as np

from .causal_candidate_fit import CAUSAL_FEATURES, ENCODED_FEATURES, FitStandardizer
from .causal_candidate_validation import (
    CausalCandidateGate,
    configure_sealed_validation_cpu_tensorflow,
)
from .decoder import CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
from .decoder_candidate_asset_evidence import load_decoder_candidate_asset_evidence
from .decoder_candidate_provenance import (
    load_decoder_candidate_manifest,
    load_decoder_candidate_partition_plan,
)
from .mine_decoder_candidates import (
    BoundedMiningProtocol,
    GUITARSET_EXPANSION_MINING_SCHEMA_VERSION,
    GUITARSET_EXPANSION_PROTOCOL_RELATIVE_PATH,
    GUITARSET_EXPANSION_PROTOCOL_SHA256,
    _require_sealed_guitarset_expansion_protocol,
    _select_bounded_items,
)


V2_DIAGNOSTIC_EXECUTE_ENV = "DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE"
V2_DIAGNOSTIC_WALL_TIMEOUT_SECONDS = 900
V2_DIAGNOSTIC_RUN_DIRECTORY_NAME = "causal_candidate_v2_train_dev_diagnostic_20260809"
V2_DIAGNOSTIC_PROTOCOL_RELATIVE_PATH = Path(
    "configs/causal_candidate_fit_v2_train_dev_diagnostic_protocol.json"
)
# Raw-byte sealing deliberately detects CRLF/LF drift as well as logical
# changes to the train/dev population.  This value is filled after the runner
# implementation updates the protocol's pending-review status.
V2_DIAGNOSTIC_PROTOCOL_SHA256 = (
    "12999e8b29984406cb94af556c2f61303de964b58222b443561b252aee4710e7"
)
FIT_ARTIFACT_DIRECTORY_NAME = "causal_candidate_fit_v1_20260809\r"
TRANSCRIPTION_CHECKPOINT_SHA256 = (
    "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
)
POLICY_A_PREREGISTRATION_DIRECTORY_NAME = (
    "decoder_candidate_policy_a_preregistration_20260809"
)
PARTITION_PLAN_FILENAME = "decoder_candidate_partition_plan_v2.json"
ASSET_EVIDENCE_FILENAME = "decoder_candidate_asset_evidence_v1.json"


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_sha(path: Path, expected: object, name: str) -> str:
    if (
        not isinstance(expected, str)
        or len(expected) != 64
        or any(character not in "0123456789abcdef" for character in expected)
    ):
        raise ValueError(f"{name} must have a sealed SHA-256 digest.")
    resolved = Path(path).resolve(strict=True)
    actual = _sha256_file(resolved)
    if actual != expected:
        raise RuntimeError(f"Fail closed: {name} SHA-256 mismatch.")
    return actual


def _load_sealed_audio_evidence_metadata(
    path: Path,
    expected_sha256: object,
) -> tuple[Mapping[str, object], str]:
    """Read, verify, and parse the one audio policy from the same bytes.

    The V2 diagnostic may not receive an audio override.  Reading the payload
    only after (and from the same raw buffer as) its sealed digest makes the
    policy used to construct masks the policy recorded by the protocol.
    """
    if (
        not isinstance(expected_sha256, str)
        or len(expected_sha256) != 64
        or any(character not in "0123456789abcdef" for character in expected_sha256)
    ):
        raise ValueError("audio_evidence_config must have a sealed SHA-256 digest.")
    raw = Path(path).resolve(strict=True).read_bytes()
    actual = hashlib.sha256(raw).hexdigest()
    if actual != expected_sha256:
        raise RuntimeError("Fail closed: audio_evidence_config SHA-256 mismatch.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("Sealed audio evidence configuration is not valid UTF-8 JSON.") from error
    if not isinstance(payload, dict):
        raise ValueError("Sealed audio evidence configuration must be a JSON object.")
    if payload.get("onset_adapt_temporal_background") is not True:
        raise ValueError(
            "Sealed V2 audio evidence must enable onset_adapt_temporal_background."
        )
    return {"audio_evidence": payload}, actual


def _require_execution_acknowledgement() -> None:
    if os.environ.get(V2_DIAGNOSTIC_EXECUTE_ENV) != "1":
        raise RuntimeError(
            "Fail closed: set DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE=1 only "
            "through the separately reviewed Mac worker invocation."
        )


def _require_clean_worker_commit(repository_root: Path) -> str:
    """Require the worker's checked-out, clean source commit before assets."""
    repository_root = Path(repository_root).resolve(strict=True)
    status = subprocess.run(
        ["git", "-C", str(repository_root), "status", "--porcelain"],
        check=True,
        capture_output=True,
        text=True,
    )
    if status.stdout.strip():
        raise RuntimeError("Fail closed: V2 diagnostic repository worktree is not clean.")
    head = subprocess.run(
        ["git", "-C", str(repository_root), "rev-parse", "HEAD"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    recorded = os.environ.get("GUITAR_MIDI_SOURCE_COMMIT")
    if recorded is not None and recorded != head:
        raise RuntimeError(
            "Fail closed: Mac worker source commit differs from the running worktree."
        )
    return head


@dataclass(frozen=True)
class V2DiagnosticPaths:
    """The only filesystem locations accepted by the future V2 invocation."""

    repository_root: Path
    worker_root: Path
    run_dir: Path
    protocol_path: Path
    v3_policy_path: Path
    partition_plan_path: Path
    asset_evidence_path: Path
    fit_report_path: Path
    model_path: Path
    standardizer_path: Path
    manifest_path: Path
    checkpoint_path: Path
    evaluation_config_path: Path
    decoder_config_path: Path
    audio_evidence_config_path: Path


@dataclass(frozen=True)
class SealedV2DiagnosticContract:
    """Pure-Python inputs verified before TensorFlow, model, audio, or labels."""

    protocol: Mapping[str, object]
    standardizer: FitStandardizer
    artifact_sha256: Mapping[str, str]
    dev_identities: tuple[tuple[str, str, str], ...]
    audio_evidence_metadata: Mapping[str, object]


def sealed_v2_diagnostic_paths(repository_root: Path, worker_root: Path) -> V2DiagnosticPaths:
    """Resolve no caller-controlled destination or scientific input path."""
    repository_root = Path(repository_root).resolve(strict=True)
    worker_root = Path(worker_root).resolve(strict=True)
    if repository_root != (worker_root / "repository").resolve(strict=True):
        raise RuntimeError("Fail closed: V2 diagnostic must run from the worker repository.")
    fit_directory = repository_root / "tmp" / FIT_ARTIFACT_DIRECTORY_NAME
    preregistration_directory = (
        repository_root / "tmp" / "local" / POLICY_A_PREREGISTRATION_DIRECTORY_NAME
    )
    return V2DiagnosticPaths(
        repository_root=repository_root,
        worker_root=worker_root,
        run_dir=repository_root / "tmp" / V2_DIAGNOSTIC_RUN_DIRECTORY_NAME,
        protocol_path=repository_root / V2_DIAGNOSTIC_PROTOCOL_RELATIVE_PATH,
        v3_policy_path=repository_root / GUITARSET_EXPANSION_PROTOCOL_RELATIVE_PATH,
        partition_plan_path=preregistration_directory / PARTITION_PLAN_FILENAME,
        asset_evidence_path=preregistration_directory / ASSET_EVIDENCE_FILENAME,
        fit_report_path=fit_directory / "fit_report.json",
        model_path=fit_directory / "causal_candidate_fit_v1.keras",
        standardizer_path=fit_directory / "fit_standardizer.json",
        manifest_path=(
            worker_root / "data" / "processed" / "polyphonic_harmonic_presence_v1"
            / "manifest_train_validation.csv"
        ),
        checkpoint_path=worker_root / "checkpoints" / f"{TRANSCRIPTION_CHECKPOINT_SHA256}.keras",
        evaluation_config_path=(
            repository_root / "configs" / "polyphonic_dual_stream_bass_independent_note.yaml"
        ),
        decoder_config_path=(
            repository_root / "configs" / "independent_note_decoder_reference.json"
        ),
        audio_evidence_config_path=(
            repository_root / "configs" / "polyphonic_audio_evidence_adaptive_temporal.json"
        ),
    )


def _require_exact_v2_protocol(paths: V2DiagnosticPaths) -> Mapping[str, object]:
    expected = (paths.repository_root / V2_DIAGNOSTIC_PROTOCOL_RELATIVE_PATH).resolve(strict=True)
    if paths.protocol_path.resolve(strict=True) != expected:
        raise RuntimeError("Fail closed: V2 diagnostic must use the sealed protocol path.")
    _require_sha(expected, V2_DIAGNOSTIC_PROTOCOL_SHA256, "V2 diagnostic protocol")
    payload = json.loads(expected.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("V2 diagnostic protocol must contain a JSON object.")
    if payload.get("schema_version") != 1 or payload.get("locked_test_used") is not False:
        raise ValueError("V2 diagnostic protocol schema or locked-test contract is invalid.")
    if payload.get("purpose") != "causal_candidate_fit_v2_post_ranking_train_only_dev_diagnostic":
        raise ValueError("V2 diagnostic protocol purpose is invalid.")
    if payload.get("status") != "sealed_runner_implemented_pending_external_review":
        raise RuntimeError("V2 diagnostic protocol is not approved for runner execution.")
    authorization = payload.get("authorization_scope")
    if not isinstance(authorization, Mapping):
        raise ValueError("V2 diagnostic authorization scope is missing.")
    if tuple(authorization.get("allowed_now", ())) != ("external_review",):
        raise RuntimeError("V2 diagnostic authorization is not pending external review.")
    return payload


def _derive_v3_dev_identities_before_tensorflow(
    *,
    manifest_path: Path,
    persisted_plan,
    persisted_asset_evidence,
    v3_policy: BoundedMiningProtocol,
    expected_manifest_sha256: str,
) -> tuple[tuple[str, str, str], ...]:
    """Derive the V3 dev cohort from raw immutable provenance only.

    This deliberately uses ``DecoderCandidateManifestItem`` rows, not the
    TensorFlow-backed ``data.ManifestItem`` class.  Its result is compared
    later with the context's exact snapshot objects before any model is loaded.
    """
    manifest_items, manifest_sha256 = load_decoder_candidate_manifest(manifest_path)
    if manifest_sha256 != expected_manifest_sha256:
        raise RuntimeError("Fail closed: V2 manifest changed during pure preflight.")
    plan = persisted_plan.plan
    plan.require_matches_manifest_items(
        manifest_items, expected_manifest_sha256=manifest_sha256,
    )
    evidence = persisted_asset_evidence.evidence
    if (
        evidence.manifest_sha256 != manifest_sha256
        or evidence.partition_plan_sha256 != persisted_plan.sha256
    ):
        raise RuntimeError("Fail closed: V2 asset evidence is not bound to plan and manifest.")
    planned = {
        (record.dataset_id, record.source_id, record.capture_id, record.partition)
        for record in plan.records
    }
    evidenced = {
        (entry.dataset_id, entry.source_id, entry.capture_id, entry.partition)
        for entry in evidence.entries
    }
    if planned != evidenced:
        raise RuntimeError("Fail closed: V2 asset evidence does not cover the persisted plan.")
    item_by_identity = {
        (item.dataset_id, item.source_id, item.capture_id): item
        for item in manifest_items
    }
    selected: list[tuple[str, str, str]] = []
    for dataset_id in v3_policy.dataset_ids:
        records = sorted(
            (
                record for record in plan.records
                if record.partition == "dev" and record.dataset_id == dataset_id
            ),
            key=lambda record: (record.dataset_id, record.source_id, record.capture_id),
        )
        required = v3_policy.recordings_for_dataset(dataset_id)
        if len(records) < required:
            raise RuntimeError(
                "Fail closed: V3 plan has fewer dev recordings than the sealed quota."
            )
        for record in records[:required]:
            identity = (record.dataset_id, record.source_id, record.capture_id)
            item = item_by_identity.get(identity)
            if item is None or item.split != "train":
                raise PermissionError(
                    "Fail closed: V2 V3 selection includes a non-train manifest item."
                )
            selected.append(identity)
    if len(selected) != 30 or len(set(selected)) != len(selected):
        raise RuntimeError("Fail closed: V2 pure dev selection is not 30 unique recordings.")
    return tuple(selected)


def load_sealed_v2_diagnostic_contract(paths: V2DiagnosticPaths) -> SealedV2DiagnosticContract:
    """Hash all inputs and parse only contract files before TensorFlow.

    This function must remain free of TensorFlow, Keras, ``data``, audio and
    label imports.  It is deliberately usable in synthetic regression tests
    with all heavy modules absent from ``sys.modules``.
    """
    protocol = _require_exact_v2_protocol(paths)
    cohort = protocol.get("cohort")
    frozen = protocol.get("frozen_v1_artifacts")
    decoder_ab = protocol.get("decoder_ab_contract")
    if not all(isinstance(value, Mapping) for value in (cohort, frozen, decoder_ab)):
        raise ValueError("V2 diagnostic protocol is missing required sections.")
    if cohort.get("manifest_split") != "train" or cohort.get("partition") != "dev":
        raise PermissionError("V2 diagnostic must remain train/dev only.")
    if cohort.get("historical_validation_recordings_used") != 0:
        raise PermissionError("V2 diagnostic must not reuse historical validation.")
    decision_policy = protocol.get("decision_policy")
    if (
        not isinstance(decision_policy, Mapping)
        or decision_policy.get("automatic_promotion") is not False
        or decision_policy.get("threshold_or_model_selection") is not False
        or decision_policy.get("historical_validation_reuse") is not False
    ):
        raise ValueError("V2 diagnostic must remain non-promotional.")
    candidate = decoder_ab.get("candidate")
    reference = decoder_ab.get("reference")
    if not isinstance(candidate, Mapping):
        raise ValueError("V2 diagnostic candidate gate is missing.")
    if not isinstance(reference, Mapping) or reference.get("causal_candidate_gate") is not None:
        raise ValueError("V2 diagnostic reference branch must not have a candidate gate.")
    if not all(decoder_ab.get(name) is True for name in (
        "single_transcription_inference_per_recording",
        "same_transcription_predictions_reused_across_ab",
        "same_base_decoder_config",
        "same_audio_evidence_masks_reused_across_ab",
        "audio_evidence_override_forbidden",
        "independent_decoder_state_after_divergence",
    )):
        raise ValueError("V2 diagnostic A/B invariants are incomplete.")
    if candidate.get("causal_candidate_gate_placement") != CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON:
        raise ValueError("V2 diagnostic must force post-ranking/pre-NoteOn placement.")
    if candidate.get("threshold") != 0.31:
        raise ValueError("V2 diagnostic threshold changed from the frozen V1 value.")
    if candidate.get("head_and_standardizer") != "exactly_frozen_v1_artifacts":
        raise ValueError("V2 diagnostic candidate head provenance changed.")
    selection = cohort.get("selection_source")
    if not isinstance(selection, Mapping):
        raise ValueError("V2 diagnostic selection source is missing.")
    expected_counts = {
        "gaps_poly_mix": 6,
        "guitar_techs_poly_directinput": 6,
        "guitar_techs_poly_micamp": 6,
        "guitarset_poly_mix": 12,
    }
    if (
        selection.get("recording_count") != 30
        or selection.get("recordings_per_dataset") != expected_counts
        or selection.get("sealed_v3_policy_relative_path")
        != str(GUITARSET_EXPANSION_PROTOCOL_RELATIVE_PATH)
        or selection.get("sealed_v3_policy_sha256") != GUITARSET_EXPANSION_PROTOCOL_SHA256
    ):
        raise ValueError("V2 diagnostic 30-recording V3 selection contract changed.")

    # The fixed V3 raw bytes are checked before parsing the V3 policy.  This
    # avoids accepting a different per-corpus quota with the same seven
    # scientific paths.  The plan and registry are then hashed independently.
    _require_sealed_guitarset_expansion_protocol(
        paths.v3_policy_path, repository_root=paths.repository_root
    )
    v3_policy = BoundedMiningProtocol.from_path(paths.v3_policy_path)
    if v3_policy.schema_version != GUITARSET_EXPANSION_MINING_SCHEMA_VERSION:
        raise ValueError("V2 diagnostic requires the sealed V3 policy schema.")
    expected_v3_counts = tuple(
        (dataset_id, expected_counts[dataset_id])
        for dataset_id in v3_policy.dataset_ids
    )
    if v3_policy.recordings_per_dataset_partition != expected_v3_counts:
        raise ValueError("V2 diagnostic V3 canonical recording counts changed.")

    artifact_paths = {
        "model": (paths.model_path, frozen.get("model_sha256")),
        "standardizer": (paths.standardizer_path, frozen.get("standardizer_sha256")),
        "fit_report": (paths.fit_report_path, frozen.get("fit_report_sha256")),
        "manifest": (paths.manifest_path, frozen.get("manifest_sha256")),
        "partition_plan": (paths.partition_plan_path, selection.get("partition_plan_sha256")),
        "asset_evidence": (paths.asset_evidence_path, selection.get("asset_evidence_sha256")),
        "checkpoint": (paths.checkpoint_path, frozen.get("transcription_checkpoint_sha256")),
        "evaluation_config": (paths.evaluation_config_path, frozen.get("evaluation_config_sha256")),
        "reference_decoder_config": (paths.decoder_config_path, frozen.get("reference_decoder_config_sha256")),
        "audio_evidence_config": (paths.audio_evidence_config_path, frozen.get("audio_evidence_config_sha256")),
        "v3_policy": (paths.v3_policy_path, selection.get("sealed_v3_policy_sha256")),
    }
    verified: dict[str, str] = {}
    # The fit report anchors the historical V1 artifacts before any binary model
    # is considered.  Every remaining input is still hashed before TensorFlow.
    order = ("fit_report",) + tuple(name for name in artifact_paths if name != "fit_report")
    for name in order:
        path, expected_sha = artifact_paths[name]
        if name == "audio_evidence_config":
            continue
        verified[name] = _require_sha(path, expected_sha, name)
    audio_evidence_metadata, verified["audio_evidence_config"] = (
        _load_sealed_audio_evidence_metadata(
            paths.audio_evidence_config_path,
            frozen.get("audio_evidence_config_sha256"),
        )
    )

    # Parse/revalidate both persistent provenance documents and derive the
    # exact cohort before TensorFlow.  Neither loader opens an audio/label
    # asset or imports the TensorFlow-backed data module.
    persisted_plan = load_decoder_candidate_partition_plan(paths.partition_plan_path)
    persisted_asset_evidence = load_decoder_candidate_asset_evidence(
        paths.asset_evidence_path
    )
    if persisted_plan.sha256 != verified["partition_plan"]:
        raise RuntimeError("Fail closed: reloaded V2 partition plan digest changed.")
    if persisted_asset_evidence.sha256 != verified["asset_evidence"]:
        raise RuntimeError("Fail closed: reloaded V2 asset evidence digest changed.")
    dev_identities = _derive_v3_dev_identities_before_tensorflow(
        manifest_path=paths.manifest_path,
        persisted_plan=persisted_plan,
        persisted_asset_evidence=persisted_asset_evidence,
        v3_policy=v3_policy,
        expected_manifest_sha256=verified["manifest"],
    )

    fit_report = json.loads(paths.fit_report_path.read_text(encoding="utf-8"))
    standardizer_payload = json.loads(paths.standardizer_path.read_text(encoding="utf-8"))
    if not isinstance(fit_report, Mapping) or not isinstance(standardizer_payload, Mapping):
        raise ValueError("Frozen V1 fit report or standardizer is not a JSON object.")
    if fit_report.get("locked_test_used") is not False or fit_report.get("validation_used") is not False:
        raise PermissionError("Frozen V1 fit provenance is not train-only.")
    if fit_report.get("status") != "complete_non_authorizing":
        raise RuntimeError("Frozen V1 fit report is not terminal and non-authorizing.")
    if standardizer_payload.get("model_sha256") != verified["model"]:
        raise ValueError("Frozen V1 standardizer is not bound to the sealed model.")
    if tuple(standardizer_payload.get("causal_features", ())) != CAUSAL_FEATURES:
        raise ValueError("Frozen V1 standardizer causal features changed.")
    if tuple(standardizer_payload.get("encoded_features", ())) != ENCODED_FEATURES:
        raise ValueError("Frozen V1 standardizer encoded features changed.")
    standardizer = FitStandardizer(
        mean=tuple(float(value) for value in standardizer_payload.get("mean", ())),
        scale=tuple(float(value) for value in standardizer_payload.get("scale", ())),
    )
    return SealedV2DiagnosticContract(
        protocol, standardizer, verified, dev_identities, audio_evidence_metadata
    )


def _derive_v3_dev_diagnostic_items(
    context,
    v3_policy: BoundedMiningProtocol,
    v2_protocol: Mapping[str, object],
) -> tuple[object, ...]:
    """Return exactly the 30 plan-attested V3 dev items in canonical order."""
    selected = _select_bounded_items(context, v3_policy)
    dev: list[object] = []
    for item in selected:
        record = context.validated_snapshot.provenance_for_snapshot_item(item)
        if record.partition == "dev":
            dev.append(item)
    cohort = v2_protocol.get("cohort")
    if not isinstance(cohort, Mapping):
        raise ValueError("V2 diagnostic cohort is invalid.")
    source = cohort.get("selection_source")
    if not isinstance(source, Mapping):
        raise ValueError("V2 diagnostic selection source is invalid.")
    expected_counts = source.get("recordings_per_dataset")
    if not isinstance(expected_counts, Mapping):
        raise ValueError("V2 diagnostic dataset quotas are invalid.")
    identities: list[tuple[str, str, str]] = []
    counts: Counter[str] = Counter()
    for item in dev:
        if getattr(item, "split", None) != "train":
            raise PermissionError("V2 diagnostic selected a non-train item.")
        identity = (
            str(getattr(item, "dataset_id")),
            str(getattr(item, "source_id")),
            str(getattr(item, "capture_id")),
        )
        identities.append(identity)
        counts[identity[0]] += 1
    if len(identities) != 30 or len(set(identities)) != len(identities):
        raise RuntimeError("V2 diagnostic dev cohort is not exactly 30 unique recordings.")
    if dict(sorted(counts.items())) != dict(expected_counts):
        raise RuntimeError("V2 diagnostic dev cohort differs from its sealed V3 quotas.")
    return tuple(dev)


def _write_json(path: Path, payload: Mapping[str, object]) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def run_sealed_v2_train_dev_diagnostic() -> dict[str, object]:
    """Run the one reviewed V2 diagnostic only after full immutable preflight."""
    _require_execution_acknowledgement()
    data_root = os.environ.get("MIDI_DATA_ROOT")
    if not data_root:
        raise RuntimeError("Fail closed: MIDI_DATA_ROOT is required from the Mac worker.")
    worker_root = Path(data_root).resolve(strict=True).parent
    repository_root = Path.cwd().resolve(strict=True)
    paths = sealed_v2_diagnostic_paths(repository_root, worker_root)
    if paths.run_dir.exists():
        raise FileExistsError(f"Refusing to reuse V2 diagnostic destination: {paths.run_dir}")
    commit = _require_clean_worker_commit(repository_root)
    sealed = load_sealed_v2_diagnostic_contract(paths)

    # No TensorFlow has been imported through this line.  Loading the persisted
    # plan/context imports the data stack, so CPU visibility is frozen first.
    tensorflow = configure_sealed_validation_cpu_tensorflow()
    from .decoder_candidate_miner import load_decoder_candidate_mining_context
    from .evaluate_events import evaluate_events

    context = load_decoder_candidate_mining_context(
        manifest_path=paths.manifest_path,
        partition_plan_path=paths.partition_plan_path,
        asset_evidence_path=paths.asset_evidence_path,
    )
    if context.snapshot.manifest_sha256 != sealed.artifact_sha256["manifest"]:
        raise RuntimeError("Fail closed: V2 context manifest SHA differs from preflight.")
    if context.persisted_plan.sha256 != sealed.artifact_sha256["partition_plan"]:
        raise RuntimeError("Fail closed: V2 context plan SHA differs from preflight.")
    if (
        context.persisted_asset_evidence is None
        or context.persisted_asset_evidence.sha256 != sealed.artifact_sha256["asset_evidence"]
    ):
        raise RuntimeError("Fail closed: V2 context asset evidence differs from preflight.")
    v3_policy = BoundedMiningProtocol.from_path(paths.v3_policy_path)
    items = _derive_v3_dev_diagnostic_items(context, v3_policy, sealed.protocol)
    resolved_identities = tuple(
        (str(item.dataset_id), str(item.source_id), str(item.capture_id))
        for item in items
    )
    if resolved_identities != sealed.dev_identities:
        raise RuntimeError(
            "Fail closed: TensorFlow-context V2 cohort differs from pure preflight."
        )

    head = tensorflow.keras.models.load_model(paths.model_path, compile=False)

    def scorer(batch: np.ndarray) -> np.ndarray:
        values = head(np.asarray(batch, dtype=np.float32), training=False)
        return np.asarray(values.numpy(), dtype=np.float32)

    threshold = sealed.protocol["decoder_ab_contract"]["candidate"]["threshold"]  # type: ignore[index]
    if isinstance(threshold, bool) or not isinstance(threshold, (int, float)) or not math.isfinite(float(threshold)):
        raise ValueError("V2 diagnostic sealed threshold is invalid.")

    def gate_factory() -> CausalCandidateGate:
        return CausalCandidateGate(
            standardizer=sealed.standardizer,
            scorer=scorer,
            threshold=float(threshold),
        )

    report = evaluate_events(
        run_dir=paths.run_dir,
        split="train",
        maximum_recordings=len(items),
        checkpoint_path=paths.checkpoint_path,
        decoder_config_path=paths.decoder_config_path,
        report_suffix="causal_candidate_v2_train_dev_diagnostic",
        config_path=paths.evaluation_config_path,
        causal_candidate_gate_factory=gate_factory,
        causal_candidate_gate_placement=(
            CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON
        ),
        sealed_audio_evidence_metadata=sealed.audio_evidence_metadata,
        sealed_train_only_items=items,
        sealed_train_only_corpus_opener=context.open_recording,
        write_report=False,
    )
    selection_rows = [
        {
            "dataset_id": item.dataset_id,
            "source_id": item.source_id,
            "group_id": item.group_id,
            "capture_id": item.capture_id,
            "partition": context.validated_snapshot.provenance_for_snapshot_item(item).partition,
        }
        for item in items
    ]
    report["causal_candidate_v2_train_dev_diagnostic"] = {
        "status": "complete_exploratory_non_promotional",
        "git_commit": commit,
        "worker_device": "cpu",
        "locked_test_used": False,
        "historical_validation_recordings_used": 0,
        "stop_after_report": True,
        "candidate_gate_placement": CAUSAL_CANDIDATE_GATE_POST_RANKING_PRE_NOTEON,
        "threshold": float(threshold),
        "protocol_sha256": _sha256_file(paths.protocol_path),
        "artifact_sha256": dict(sealed.artifact_sha256),
        "selection": {
            "recordings": selection_rows,
            "recordings_by_dataset": dict(sorted(Counter(
                row["dataset_id"] for row in selection_rows
            ).items())),
        },
        "next_action": (
            "External review only: this train/dev V2 placement diagnostic cannot "
            "promote a model or threshold, run historical validation, fit, "
            "recalibrate, export, run live, or access the locked test."
        ),
    }
    partial = paths.run_dir.parent / f".{paths.run_dir.name}.partial-{os.getpid()}"
    if partial.exists():
        raise FileExistsError(f"Refusing to reuse V2 diagnostic partial directory: {partial}")
    try:
        report_path = partial / "reports" / (
            f"train_events_{paths.checkpoint_path.stem}_causal_candidate_v2_train_dev_diagnostic.json"
        )
        report_path.parent.mkdir(parents=True)
        _write_json(report_path, report)
        os.replace(partial, paths.run_dir)
    except Exception:
        shutil.rmtree(partial, ignore_errors=True)
        raise
    return report


def main() -> None:
    report = run_sealed_v2_train_dev_diagnostic()
    print(json.dumps({
        "status": "complete_exploratory_non_promotional",
        "run_dir": str(Path.cwd() / "tmp" / V2_DIAGNOSTIC_RUN_DIRECTORY_NAME),
        "locked_test_used": False,
        "stop_after_report": True,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
