"""Pure provenance preflight for a future independent V2 evaluation.

This module deliberately has no CLI and cannot open audio, labels, a Keras
model, a checkpoint, or asset evidence.  It only verifies the sealed protocol,
the complete manifest metadata, and the historical selection before deriving
the exact independent validation cohort.  A separately reviewed runner will be
required before any real asset-evidence creation or CPU evaluation.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from typing import Mapping, Sequence

from .decoder_candidate_provenance import (
    DecoderCandidateManifestItem,
    candidate_train_selection,
    leakage_group_key,
    load_decoder_candidate_manifest,
)


INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH = Path(
    "configs/causal_candidate_fit_v2_independent_validation_protocol.json"
)
HISTORICAL_V1_SELECTION_RELATIVE_PATH = Path(
    "configs/causal_candidate_fit_v1_validation_selection_12.json"
)
INDEPENDENT_V2_SELECTION_NAMESPACE = "causal-v2-independent-validation-v1:47"
INDEPENDENT_V2_SELECTION_SEED = 47
INDEPENDENT_V2_GATE_PLACEMENT = "post_ranking_pre_noteon"
INDEPENDENT_V2_THRESHOLD = 0.31
INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256 = {
    "v2_execution_report_sha256": "43e28b4ebfe33f5ad0f28be1c4b61704af8cebc08012458cbd645d3027b9acf9",
    "transcription_checkpoint_sha256": "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325",
    "model_sha256": "b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e",
    "standardizer_sha256": "0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b",
    "audio_evidence_config_sha256": "45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e",
    "evaluation_config_sha256": "245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804",
    "reference_decoder_config_sha256": "c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96",
}
INDEPENDENT_V2_PROTOCOL_SHA256 = (
    "8753a88bd049de35745c6a90f9175e3ca4f9a638f127133515305b2a6a1a07a1"
)


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lower-case SHA-256 digest.")
    return value


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object.")
    return value


def _canonical_recording_key(item: DecoderCandidateManifestItem) -> str:
    return "|".join((
        item.dataset_id,
        item.group_id,
        item.source_id,
        item.capture_id,
    ))


def _stable_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _ordered_recording_keys_sha256(recording_keys: Sequence[str]) -> str:
    return _sha256_bytes(("\n".join(recording_keys) + "\n").encode("utf-8"))


@dataclass(frozen=True)
class IndependentV2ValidationCohort:
    """The metadata-only result which a future runner must reproduce exactly."""

    protocol_sha256: str
    manifest_sha256: str
    historical_selection_sha256: str
    recording_keys: tuple[str, ...]
    leakage_groups: tuple[str, ...]
    recordings_per_dataset: tuple[tuple[str, int], ...]
    independent_group_count: int

    def __post_init__(self) -> None:
        _require_sha256(self.protocol_sha256, "protocol_sha256")
        _require_sha256(self.manifest_sha256, "manifest_sha256")
        _require_sha256(self.historical_selection_sha256, "historical_selection_sha256")
        if len(self.recording_keys) != 30 or len(set(self.recording_keys)) != 30:
            raise ValueError("independent V2 cohort must contain 30 unique recordings.")
        if len(self.leakage_groups) != 20 or len(set(self.leakage_groups)) != 20:
            raise ValueError("independent V2 cohort must contain 20 unique leakage groups.")
        if dict(self.recordings_per_dataset) != {
            "gaps_poly_mix": 10,
            "guitar_techs_poly_directinput": 10,
            "guitar_techs_poly_micamp": 10,
        }:
            raise ValueError("independent V2 cohort dataset counts are invalid.")
        if self.independent_group_count != 20:
            raise ValueError("independent_group_count must be 20.")


@dataclass(frozen=True)
class IndependentV2ValidationAssetEvidenceRequirement:
    """A deterministic envelope for a future, separately authorized registry.

    It names the only identities an eventual validation asset-evidence artifact
    may cover, but deliberately contains no path, size, digest, file handle, or
    asset-reading capability.  Constructing or reading that artifact remains a
    separately reviewed operation.
    """

    protocol_sha256: str
    manifest_sha256: str
    ordered_recording_keys_sha256: str
    recording_keys: tuple[str, ...]
    asset_types: tuple[str, ...] = ("audio", "labels")

    def __post_init__(self) -> None:
        _require_sha256(self.protocol_sha256, "protocol_sha256")
        _require_sha256(self.manifest_sha256, "manifest_sha256")
        _require_sha256(
            self.ordered_recording_keys_sha256, "ordered_recording_keys_sha256"
        )
        if self.asset_types != ("audio", "labels"):
            raise ValueError("validation asset evidence must bind audio and labels only.")
        if (
            len(self.recording_keys) != 30
            or len(set(self.recording_keys)) != 30
            or self.ordered_recording_keys_sha256
            != _ordered_recording_keys_sha256(self.recording_keys)
        ):
            raise ValueError("validation asset-evidence cohort identity is invalid.")

    def as_json(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "purpose": "causal_candidate_v2_independent_validation_asset_evidence",
            "protocol_sha256": self.protocol_sha256,
            "manifest_sha256": self.manifest_sha256,
            "ordered_recording_keys_sha256": self.ordered_recording_keys_sha256,
            "recording_keys": list(self.recording_keys),
            "asset_types": list(self.asset_types),
            "builder_authorized_now": False,
            "reader_authorized_now": False,
        }


def validation_asset_evidence_requirement(
    cohort: IndependentV2ValidationCohort,
) -> IndependentV2ValidationAssetEvidenceRequirement:
    """Return the immutable identity envelope; do not build or read evidence."""
    if not isinstance(cohort, IndependentV2ValidationCohort):
        raise ValueError("cohort must be IndependentV2ValidationCohort.")
    return IndependentV2ValidationAssetEvidenceRequirement(
        protocol_sha256=cohort.protocol_sha256,
        manifest_sha256=cohort.manifest_sha256,
        ordered_recording_keys_sha256=_ordered_recording_keys_sha256(cohort.recording_keys),
        recording_keys=cohort.recording_keys,
    )


def _load_exact_json(path: Path, expected_sha256: object, name: str) -> tuple[Mapping[str, object], str]:
    expected = _require_sha256(expected_sha256, name)
    raw = Path(path).resolve(strict=True).read_bytes()
    actual = _sha256_bytes(raw)
    if actual != expected:
        raise RuntimeError(f"Fail closed: {name} SHA-256 mismatch.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"{name} is not valid UTF-8 JSON.") from error
    return _require_mapping(payload, name), actual


def _require_exact_protocol(repository_root: Path) -> tuple[Mapping[str, object], str]:
    repository_root = Path(repository_root).resolve(strict=True)
    path = (repository_root / INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH).resolve(strict=True)
    expected_path = (repository_root / INDEPENDENT_V2_PROTOCOL_RELATIVE_PATH).resolve(strict=True)
    if path != expected_path:
        raise RuntimeError("Fail closed: independent V2 protocol path is not canonical.")
    payload, digest = _load_exact_json(
        path, INDEPENDENT_V2_PROTOCOL_SHA256, "independent V2 protocol"
    )
    if payload.get("schema_version") != 1 or payload.get("locked_test_used") is not False:
        raise ValueError("independent V2 protocol schema or locked-test contract is invalid.")
    if payload.get("purpose") != "causal_candidate_fit_v2_post_ranking_independent_validation_contract":
        raise ValueError("independent V2 protocol purpose is invalid.")
    if payload.get("status") != "synthetic_runner_implemented_pending_external_review":
        raise RuntimeError("independent V2 protocol is not pending external review.")
    authorization = _require_mapping(payload.get("authorization_scope"), "authorization_scope")
    if tuple(authorization.get("allowed_now", ())) != ("external_review",):
        raise RuntimeError("independent V2 protocol is not review-only.")
    return payload, digest


def _load_historical_selection(
    repository_root: Path,
    boundary: Mapping[str, object],
) -> tuple[tuple[str, ...], str]:
    relative_path = boundary.get("historical_v1_validation_selection_path")
    if relative_path != HISTORICAL_V1_SELECTION_RELATIVE_PATH.as_posix():
        raise RuntimeError("Fail closed: historical selection path changed.")
    payload, digest = _load_exact_json(
        Path(repository_root) / HISTORICAL_V1_SELECTION_RELATIVE_PATH,
        boundary.get("historical_v1_validation_selection_sha256"),
        "historical V1 validation selection",
    )
    values = payload.get("recording_keys")
    if (
        payload.get("schema_version") != 1
        or payload.get("locked_test_used") is not False
        or not isinstance(values, list)
        or len(values) != 12
        or any(not isinstance(value, str) or not value for value in values)
        or len(set(values)) != 12
    ):
        raise ValueError("historical V1 validation selection is invalid.")
    return tuple(values), digest


def _require_frozen_intervention(protocol: Mapping[str, object]) -> None:
    frozen = _require_mapping(protocol.get("frozen_v2_intervention"), "frozen_v2_intervention")
    if (
        frozen.get("threshold") != INDEPENDENT_V2_THRESHOLD
        or frozen.get("candidate_gate_placement") != INDEPENDENT_V2_GATE_PLACEMENT
        or frozen.get("encoded_feature_count") != 12
    ):
        raise ValueError("independent V2 intervention changed from its frozen values.")
    for name, expected in INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256.items():
        if frozen.get(name) != expected:
            raise ValueError(f"independent V2 {name} changed from the sealed value.")


def _expected_recording_counts(protocol: Mapping[str, object]) -> Mapping[str, int]:
    cohort_rule = _require_mapping(protocol.get("cohort_rule"), "cohort_rule")
    expected = {
        "gaps_poly_mix": 10,
        "guitar_techs_poly_directinput": 10,
        "guitar_techs_poly_micamp": 10,
        "guitarset_poly_mix": 0,
    }
    if (
        cohort_rule.get("recording_count") != 30
        or cohort_rule.get("selection_seed") != INDEPENDENT_V2_SELECTION_SEED
        or cohort_rule.get("independent_group_count") != 20
        or cohort_rule.get("canonical_recording_key")
        != "dataset_id|group_id|source_id|capture_id"
        or cohort_rule.get("recordings_per_dataset") != expected
    ):
        raise ValueError("independent V2 cohort rule changed.")
    return expected


def _derive_expected_recording_keys(
    items: Sequence[DecoderCandidateManifestItem],
    *,
    historical_recording_keys: Sequence[str],
) -> tuple[tuple[str, ...], tuple[str, ...]]:
    """Derive the frozen cohort from full manifest metadata, never metrics.

    The complete manifest is intentionally supplied here.  Test rows are
    rejected by ``candidate_train_selection`` before the cohort is considered;
    train rows are used only to prove selected validation groups were not V1/V2
    Policy A eligible, and can never be selected.
    """
    if not items:
        raise ValueError("independent V2 manifest is empty.")
    by_key = {_canonical_recording_key(item): item for item in items}
    if len(by_key) != len(items):
        raise RuntimeError("Fail closed: manifest has duplicate canonical recording keys.")
    historical_items: list[DecoderCandidateManifestItem] = []
    for key in historical_recording_keys:
        item = by_key.get(key)
        if item is None or item.split != "validation":
            raise RuntimeError(
                "Fail closed: historical validation selection is absent from the "
                "complete validation manifest."
            )
        historical_items.append(item)
    historical_groups = {leakage_group_key(item) for item in historical_items}
    if len(historical_groups) == 0:
        raise RuntimeError("Fail closed: historical selection has no leakage groups.")

    # Reuse Policy A's exact corpus-aware leakage implementation to prove that
    # a selected validation group was not eligible for the V1/V2 fit/mining
    # population.  This is metadata-only and opens neither labels nor audio.
    policy_a = candidate_train_selection(items)
    eligible_train_groups = {
        leakage_group_key(item) for item in policy_a.eligible_train_items
    }

    eligible_validation = tuple(
        item
        for item in items
        if item.split == "validation" and leakage_group_key(item) not in historical_groups
    )
    if any(item.dataset_id == "guitarset_poly_mix" for item in eligible_validation):
        raise RuntimeError(
            "Fail closed: GuitarSet would be independent only if its historically "
            "exposed leakage group changed."
        )

    gaps_by_group: dict[str, list[DecoderCandidateManifestItem]] = defaultdict(list)
    gtech_by_group: dict[str, list[DecoderCandidateManifestItem]] = defaultdict(list)
    for item in eligible_validation:
        group = leakage_group_key(item)
        if item.dataset_id == "gaps_poly_mix":
            gaps_by_group[group].append(item)
        elif item.dataset_id in {
            "guitar_techs_poly_directinput",
            "guitar_techs_poly_micamp",
        }:
            gtech_by_group[group].append(item)
        else:
            raise RuntimeError(
                f"Fail closed: unexpected eligible validation dataset {item.dataset_id!r}."
            )

    ranked_gaps: list[tuple[str, str, DecoderCandidateManifestItem]] = []
    for group, group_items in gaps_by_group.items():
        chosen = min(
            group_items,
            key=lambda item: (
                _stable_hash(
                    f"{INDEPENDENT_V2_SELECTION_NAMESPACE}:gaps:recording:"
                    f"{_canonical_recording_key(item)}"
                ),
                _canonical_recording_key(item),
            ),
        )
        ranked_gaps.append((
            _stable_hash(f"{INDEPENDENT_V2_SELECTION_NAMESPACE}:gaps:{group}"),
            group,
            chosen,
        ))
    if len(ranked_gaps) < 10:
        raise RuntimeError("Fail closed: fewer than ten independent GAPS groups.")
    selected_gaps = tuple(row[2] for row in sorted(ranked_gaps)[:10])

    ranked_gtech: list[
        tuple[str, str, DecoderCandidateManifestItem, DecoderCandidateManifestItem]
    ] = []
    for group, group_items in gtech_by_group.items():
        direct = [
            item for item in group_items
            if item.dataset_id == "guitar_techs_poly_directinput"
        ]
        mic = [
            item for item in group_items
            if item.dataset_id == "guitar_techs_poly_micamp"
        ]
        if len(direct) != 1 or len(mic) != 1:
            raise RuntimeError(
                "Fail closed: each selected Guitar-TECHS group requires one direct "
                "and one mic/amp capture."
            )
        ranked_gtech.append((
            _stable_hash(f"{INDEPENDENT_V2_SELECTION_NAMESPACE}:guitar_techs:{group}"),
            group,
            direct[0],
            mic[0],
        ))
    if len(ranked_gtech) < 10:
        raise RuntimeError("Fail closed: fewer than ten paired Guitar-TECHS groups.")
    selected_gtech = tuple(row for row in sorted(ranked_gtech)[:10])

    selected_items = selected_gaps + tuple(
        item for _, _, direct, mic in selected_gtech for item in (direct, mic)
    )
    selected_keys = tuple(_canonical_recording_key(item) for item in selected_items)
    selected_groups = tuple(
        sorted({leakage_group_key(item) for item in selected_items})
    )
    if len(selected_keys) != 30 or len(set(selected_keys)) != 30:
        raise RuntimeError("Fail closed: independent V2 selection is not 30 unique rows.")
    if len(selected_groups) != 20:
        raise RuntimeError("Fail closed: independent V2 selection is not 20 groups.")
    if any(leakage_group_key(item) in historical_groups for item in selected_items):
        raise RuntimeError("Fail closed: independent V2 selection overlaps historical groups.")
    if set(selected_groups) & eligible_train_groups:
        raise RuntimeError("Fail closed: independent V2 selection overlaps Policy A train.")
    return selected_keys, selected_groups


def derive_independent_v2_validation_cohort(
    protocol: Mapping[str, object],
    *,
    protocol_sha256: str,
    manifest_items: Sequence[DecoderCandidateManifestItem],
    manifest_sha256: str,
    historical_recording_keys: Sequence[str],
    historical_selection_sha256: str,
) -> IndependentV2ValidationCohort:
    """Purely derive and validate the independent cohort before any asset access."""
    _require_sha256(protocol_sha256, "protocol_sha256")
    _require_sha256(manifest_sha256, "manifest_sha256")
    _require_sha256(historical_selection_sha256, "historical_selection_sha256")
    _require_frozen_intervention(protocol)
    boundary = _require_mapping(protocol.get("independence_boundary"), "independence_boundary")
    _require_sha256(boundary.get("policy_a_partition_plan_sha256"), "policy_a_partition_plan_sha256")
    if (
        boundary.get("manifest_sha256") != manifest_sha256
        or boundary.get("historical_v1_validation_selection_sha256")
        != historical_selection_sha256
        or boundary.get("exclude_historical_recording_keys") is not True
        or boundary.get("exclude_every_historical_leakage_group") is not True
        or boundary.get("require_no_overlap_with_policy_a_eligible_train_groups") is not True
        or boundary.get("forbid_manual_recording_selection") is not True
        or boundary.get("forbid_metric_or_audio_or_label_based_selection") is not True
    ):
        raise RuntimeError("Fail closed: independent V2 provenance boundary changed.")
    expected_counts = _expected_recording_counts(protocol)
    evidence_contract = _require_mapping(
        protocol.get("validation_asset_evidence_contract"),
        "validation_asset_evidence_contract",
    )
    if (
        evidence_contract.get("schema_version") != 1
        or evidence_contract.get("purpose")
        != "causal_candidate_v2_independent_validation_asset_evidence"
        or tuple(evidence_contract.get("asset_types", ())) != ("audio", "labels")
        or tuple(evidence_contract.get("must_bind", ()))
        != (
            "independent_validation_protocol_sha256",
            "manifest_sha256",
            "ordered_recording_keys_sha256",
            "recording_keys",
        )
        or evidence_contract.get("builder_authorized_now") is not False
        or evidence_contract.get("reader_authorized_now") is not False
    ):
        raise ValueError("independent V2 validation asset-evidence contract changed.")
    execution = _require_mapping(protocol.get("future_execution_contract"), "future_execution_contract")
    if (
        execution.get("independent_group_count") != 20
        or execution.get("report_recordings_and_independent_groups_separately") is not True
        or execution.get("single_cpu_job") is not True
        or execution.get("wall_timeout_seconds") != 900
        or execution.get("single_transcription_inference_per_recording") is not True
        or execution.get("same_predictions_and_audio_evidence_masks_reused_across_ab") is not True
        or execution.get("reference_has_no_causal_candidate_gate") is not True
        or execution.get("candidate_uses_only_the_frozen_v2_intervention") is not True
        or execution.get("no_model_or_threshold_selection") is not True
        or execution.get("stop_after_report") is not True
    ):
        raise ValueError("independent V2 future-execution contract changed.")
    derived_keys, groups = _derive_expected_recording_keys(
        manifest_items, historical_recording_keys=historical_recording_keys
    )
    cohort_rule = _require_mapping(protocol.get("cohort_rule"), "cohort_rule")
    configured_keys = cohort_rule.get("recording_keys")
    if not isinstance(configured_keys, list) or tuple(configured_keys) != derived_keys:
        raise RuntimeError(
            "Fail closed: independent V2 configured recording keys differ from "
            "the deterministic full-manifest derivation."
        )
    counts = Counter(key.split("|", 1)[0] for key in derived_keys)
    if dict(sorted(counts.items())) != {
        dataset: count for dataset, count in expected_counts.items() if count
    }:
        raise RuntimeError("Fail closed: independent V2 dataset counts differ from protocol.")
    decision = _require_mapping(
        protocol.get("pre_registered_interpretation_rules"),
        "pre_registered_interpretation_rules",
    )
    if (
        decision.get("all_rules_must_pass_for_positive_independent_evidence") is not True
        or decision.get("global_causal_false_noteon_relative_reduction_minimum") != 0.01
        or decision.get("per_dataset_causal_false_noteons_must_not_increase") is not True
        or decision.get("retriggers_and_excess_fragments_must_not_increase") is not True
        or decision.get("guitarset_claim_forbidden") is not True
        or decision.get("automatic_promotion") is not False
    ):
        raise ValueError("independent V2 interpretation rules changed.")
    return IndependentV2ValidationCohort(
        protocol_sha256=protocol_sha256,
        manifest_sha256=manifest_sha256,
        historical_selection_sha256=historical_selection_sha256,
        recording_keys=derived_keys,
        leakage_groups=groups,
        recordings_per_dataset=tuple(sorted(counts.items())),
        independent_group_count=len(groups),
    )


def evaluate_independent_v2_decision(
    *,
    reference: Mapping[str, object],
    candidate: Mapping[str, object],
    rules: Mapping[str, object],
) -> dict[str, object]:
    """Apply the pre-registered independent-V2 rules without choosing a model.

    This pure function accepts only an already-produced A/B report.  It never
    opens a recording or performs inference.  Missing, non-finite, incomplete,
    or GuitarSet-containing report sections fail closed rather than silently
    passing an unmeasured condition.
    """
    expected_datasets = {
        "gaps_poly_mix",
        "guitar_techs_poly_directinput",
        "guitar_techs_poly_micamp",
    }

    def mapping(value: object, name: str) -> Mapping[str, object]:
        if not isinstance(value, Mapping):
            raise ValueError(f"independent V2 report is missing {name}.")
        return value

    def number(payload: Mapping[str, object], name: str) -> float:
        value = payload.get(name)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
            raise ValueError(f"independent V2 report has missing or non-finite metric: {name}.")
        return float(value)

    def rule(name: str) -> float:
        return number(rules, name)

    ref_onset = mapping(reference.get("onset"), "reference onset")
    cand_onset = mapping(candidate.get("onset"), "candidate onset")
    ref_causal = mapping(reference.get("strictly_causal_noteon"), "reference causal metrics")
    cand_causal = mapping(candidate.get("strictly_causal_noteon"), "candidate causal metrics")
    ref_global = mapping(ref_causal.get("global"), "reference causal global")
    cand_global = mapping(cand_causal.get("global"), "candidate causal global")
    ref_datasets = mapping(reference.get("dataset_metrics"), "reference dataset metrics")
    cand_datasets = mapping(candidate.get("dataset_metrics"), "candidate dataset metrics")
    ref_per_dataset = mapping(ref_datasets.get("per_dataset"), "reference per-dataset metrics")
    cand_per_dataset = mapping(cand_datasets.get("per_dataset"), "candidate per-dataset metrics")
    ref_by_corpus = mapping(ref_causal.get("by_corpus"), "reference causal by-corpus metrics")
    cand_by_corpus = mapping(cand_causal.get("by_corpus"), "candidate causal by-corpus metrics")
    if (
        set(ref_per_dataset) != expected_datasets
        or set(cand_per_dataset) != expected_datasets
        or set(ref_by_corpus) != expected_datasets
        or set(cand_by_corpus) != expected_datasets
    ):
        raise ValueError(
            "independent V2 report must cover exactly GAPS and both Guitar-TECHS "
            "views; GuitarSet is outside this independent cohort."
        )

    ref_false_noteons = number(ref_global, "false_noteons")
    if ref_false_noteons <= 0.0:
        raise ValueError(
            "independent V2 causal false-NoteOn baseline must be positive to "
            "evaluate a relative reduction."
        )
    checks: dict[str, bool] = {
        "global_causal_false_noteon_reduction": (
            number(cand_global, "false_noteons")
            <= ref_false_noteons
            * (1.0 - rule("global_causal_false_noteon_relative_reduction_minimum"))
        ),
        "global_causal_recall_within_250ms": (
            number(cand_global, "recall_within_max_latency")
            - number(ref_global, "recall_within_max_latency")
            >= -rule("global_causal_recall_within_250ms_maximum_drop")
        ),
        "global_onset_f1": (
            number(cand_onset, "f1") - number(ref_onset, "f1")
            >= -rule("global_onset_f1_maximum_drop")
        ),
        "retriggers": number(candidate, "retriggers") <= number(reference, "retriggers"),
        "excess_fragments": (
            number(mapping(candidate.get("diagnostics"), "candidate diagnostics"), "excess_fragments")
            <= number(mapping(reference.get("diagnostics"), "reference diagnostics"), "excess_fragments")
        ),
    }
    for percentile in ("p50", "p90"):
        checks[f"causal_latency_{percentile}"] = (
            number(cand_global, f"latency_{percentile}_ms")
            - number(ref_global, f"latency_{percentile}_ms")
            <= rule("causal_latency_p50_and_p90_maximum_increase_ms")
        )
    for dataset in sorted(expected_datasets):
        ref_onset_dataset = mapping(ref_per_dataset[dataset], f"reference onset {dataset}")
        cand_onset_dataset = mapping(cand_per_dataset[dataset], f"candidate onset {dataset}")
        ref_causal_dataset = mapping(ref_by_corpus[dataset], f"reference causal {dataset}")
        cand_causal_dataset = mapping(cand_by_corpus[dataset], f"candidate causal {dataset}")
        checks[f"causal_false_noteons:{dataset}"] = (
            number(cand_causal_dataset, "false_noteons")
            <= number(ref_causal_dataset, "false_noteons")
        )
        checks[f"causal_recall_within_250ms:{dataset}"] = (
            number(cand_causal_dataset, "recall_within_max_latency")
            - number(ref_causal_dataset, "recall_within_max_latency")
            >= -rule("per_dataset_causal_recall_within_250ms_maximum_drop")
        )
        checks[f"onset_f1:{dataset}"] = (
            number(mapping(cand_onset_dataset.get("onset"), f"candidate onset values {dataset}"), "f1")
            - number(mapping(ref_onset_dataset.get("onset"), f"reference onset values {dataset}"), "f1")
            >= -rule("per_dataset_onset_f1_maximum_drop")
        )
    if rules.get("all_rules_must_pass_for_positive_independent_evidence") is not True:
        raise ValueError("independent V2 decision contract must require every rule.")
    if rules.get("per_dataset_causal_false_noteons_must_not_increase") is not True:
        raise ValueError("independent V2 decision contract must protect every corpus.")
    if rules.get("retriggers_and_excess_fragments_must_not_increase") is not True:
        raise ValueError("independent V2 decision contract must protect fragmentation.")
    if rules.get("guitarset_claim_forbidden") is not True:
        raise ValueError("independent V2 decision contract must forbid GuitarSet claims.")
    if rules.get("automatic_promotion") is not False:
        raise ValueError("independent V2 decision contract must forbid automatic promotion.")
    passed = all(checks.values())
    return {
        "all_rules_passed": passed,
        "classification": (
            "positive_independent_evidence_non_promotional"
            if passed else "non_positive_independent_evidence"
        ),
        "automatic_promotion": False,
        "checks": checks,
    }


def load_sealed_independent_v2_validation_cohort(
    repository_root: Path,
    manifest_path: Path,
) -> IndependentV2ValidationCohort:
    """Load only sealed JSON and manifest metadata; never open recording assets.

    This is intentionally the future runner's first call.  There is no
    caller-supplied recording list, asset-evidence path, model path, threshold,
    placement, or split override.
    """
    protocol, protocol_sha256 = _require_exact_protocol(repository_root)
    boundary = _require_mapping(protocol.get("independence_boundary"), "independence_boundary")
    history, history_sha256 = _load_historical_selection(repository_root, boundary)
    manifest_items, manifest_sha256 = load_decoder_candidate_manifest(manifest_path)
    return derive_independent_v2_validation_cohort(
        protocol,
        protocol_sha256=protocol_sha256,
        manifest_items=manifest_items,
        manifest_sha256=manifest_sha256,
        historical_recording_keys=history,
        historical_selection_sha256=history_sha256,
    )
