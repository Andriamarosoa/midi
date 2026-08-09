"""Pure, sealed declaration of a future independent V2 execution.

This module intentionally has no CLI and does not import TensorFlow, a model,
asset evidence, manifest parsing, or the decoder.  It only validates the raw
bytes of the immutable execution *contract*.  A separately reviewed runner
and, later, a separately sealed single-job invocation are both required before
any asset, model, or scientific execution can occur.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Mapping
import weakref


INDEPENDENT_V2_EXECUTION_CONTRACT_RELATIVE_PATH = Path(
    "configs/causal_candidate_fit_v2_independent_validation_execution_contract.json"
)
INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256 = (
    "269efb65f225cf2522eab895cf59c351bea6bb97bc20229160f611c5e3ae63ed"
)
INDEPENDENT_V2_EXECUTION_CONTRACT_STATUS = (
    "independent_validation_execution_contract_pending_external_review"
)
INDEPENDENT_V2_EXECUTION_ALLOWED_NOW = ("external_review",)
INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256 = (
    "def274de1d1c738c7d4342f8f16ef2aaab99e9b2f87d6641d012d36ab6a34119"
)
INDEPENDENT_V2_ASSET_EVIDENCE_SHA256 = (
    "10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee"
)
INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256 = (
    "d63655c388991f3782a738e5bba58f0409ae79f297a3d5009dab7971349ba015"
)
INDEPENDENT_V2_MANIFEST_SHA256 = (
    "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
)
INDEPENDENT_V2_HISTORICAL_SELECTION_SHA256 = (
    "8c3cf53c7f5dcf086b70767e28499c3164aa307059652a6d0a2fc87159f9dcbc"
)
INDEPENDENT_V2_POLICY_A_PLAN_SHA256 = (
    "a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4"
)
INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256 = {
    "v2_train_dev_execution_report_sha256": (
        "43e28b4ebfe33f5ad0f28be1c4b61704af8cebc08012458cbd645d3027b9acf9"
    ),
    "transcription_checkpoint_sha256": (
        "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
    ),
    "model_sha256": "b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e",
    "standardizer_sha256": (
        "0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b"
    ),
    "audio_evidence_config_sha256": (
        "45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e"
    ),
    "evaluation_config_sha256": (
        "245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804"
    ),
    "reference_decoder_config_sha256": (
        "c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96"
    ),
}
_SEALED_EXECUTION_CONTRACTS: dict[int, weakref.ReferenceType[object]] = {}


def _sha256_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_mapping(value: object, name: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{name} must be a JSON object.")
    return value


def _require_sha256(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{name} must be a lower-case SHA-256 digest.")
    return value


def _require_relative_posix_path(value: object, name: str) -> str:
    if not isinstance(value, str) or not value or "\\" in value:
        raise ValueError(f"{name} must be a non-empty relative POSIX path.")
    path = PurePosixPath(value)
    if path.is_absolute() or ".." in path.parts or "." in path.parts:
        raise ValueError(f"{name} must remain beneath the repository root.")
    return value


def _register_identity(value: object) -> None:
    identifier = id(value)

    def cleanup(reference: weakref.ReferenceType[object]) -> None:
        if _SEALED_EXECUTION_CONTRACTS.get(identifier) is reference:
            _SEALED_EXECUTION_CONTRACTS.pop(identifier, None)

    _SEALED_EXECUTION_CONTRACTS[identifier] = weakref.ref(value, cleanup)


@dataclass(frozen=True)
class IndependentV2ExecutionContract:
    """Exact, non-executable V2 independent-evaluation declaration."""

    contract_sha256: str
    closed_independent_protocol_sha256: str
    asset_evidence_sha256: str
    asset_evidence_builder_protocol_sha256: str
    recording_count: int
    independent_group_count: int
    wall_timeout_seconds: int
    threshold: float
    candidate_gate_placement: str

    def __post_init__(self) -> None:
        _require_sha256(self.contract_sha256, "contract_sha256")
        if self.closed_independent_protocol_sha256 != INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256:
            raise ValueError("closed independent protocol SHA-256 is not frozen.")
        if self.asset_evidence_sha256 != INDEPENDENT_V2_ASSET_EVIDENCE_SHA256:
            raise ValueError("independent asset-evidence SHA-256 is not frozen.")
        if (
            self.asset_evidence_builder_protocol_sha256
            != INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256
        ):
            raise ValueError("independent asset-evidence builder SHA-256 is not frozen.")
        if self.recording_count != 30 or self.independent_group_count != 20:
            raise ValueError("independent V2 execution cohort cardinality is invalid.")
        if self.wall_timeout_seconds != 900:
            raise ValueError("independent V2 execution timeout is not frozen.")
        if self.threshold != 0.31:
            raise ValueError("independent V2 threshold is not frozen.")
        if self.candidate_gate_placement != "post_ranking_pre_noteon":
            raise ValueError("independent V2 candidate gate placement is not frozen.")


def require_sealed_independent_v2_execution_contract(
    value: object,
) -> IndependentV2ExecutionContract:
    """Return only a contract loaded from its exact canonical raw bytes."""

    if not isinstance(value, IndependentV2ExecutionContract):
        raise ValueError("value must be IndependentV2ExecutionContract.")
    reference = _SEALED_EXECUTION_CONTRACTS.get(id(value))
    if reference is None or reference() is not value:
        raise RuntimeError(
            "Fail closed: independent V2 execution contract must be loaded from sealed bytes."
        )
    return value


def _require_exact_execution_payload(payload: Mapping[str, object]) -> IndependentV2ExecutionContract:
    if type(payload.get("schema_version")) is not int or payload.get("schema_version") != 1:
        raise ValueError("independent V2 execution contract schema is invalid.")
    if (
        payload.get("purpose")
        != "causal_candidate_fit_v2_post_ranking_independent_validation_execution_contract"
        or payload.get("status") != INDEPENDENT_V2_EXECUTION_CONTRACT_STATUS
        or payload.get("locked_test_used") is not False
    ):
        raise ValueError("independent V2 execution contract identity is invalid.")
    authorization = _require_mapping(payload.get("authorization_scope"), "authorization_scope")
    if tuple(authorization.get("allowed_now", ())) != INDEPENDENT_V2_EXECUTION_ALLOWED_NOW:
        raise RuntimeError("independent V2 execution contract is not limited to external review.")
    if tuple(authorization.get("forbidden_now", ())) != (
        "independent_validation_asset_evidence_build",
        "asset_evidence_reader_or_validation",
        "asset_content_decoding",
        "model_loading",
        "runner_implementation",
        "real_runner_execution",
        "fit",
        "recalibration",
        "threshold_search",
        "historical_validation_reuse",
        "export",
        "live",
        "locked_test",
    ):
        raise ValueError("independent V2 execution contract forbidden scope changed.")

    prerequisite = _require_mapping(payload.get("prerequisite_provenance"), "prerequisite_provenance")
    if (
        prerequisite.get("closed_independent_protocol_relative_path")
        != "configs/causal_candidate_fit_v2_independent_validation_protocol.json"
        or prerequisite.get("closed_independent_protocol_sha256")
        != INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256
        or prerequisite.get("closed_independent_protocol_status")
        != "independent_validation_asset_evidence_revalidated_pending_external_review"
        or prerequisite.get("manifest_sha256") != INDEPENDENT_V2_MANIFEST_SHA256
        or prerequisite.get("historical_v1_validation_selection_sha256")
        != INDEPENDENT_V2_HISTORICAL_SELECTION_SHA256
        or prerequisite.get("policy_a_partition_plan_sha256")
        != INDEPENDENT_V2_POLICY_A_PLAN_SHA256
        or _require_relative_posix_path(
            prerequisite.get("asset_evidence_relative_path"),
            "asset_evidence_relative_path",
        )
        != "tmp/local/causal_candidate_v2_independent_validation_asset_evidence_20260810.json"
        or prerequisite.get("asset_evidence_sha256") != INDEPENDENT_V2_ASSET_EVIDENCE_SHA256
        or prerequisite.get("asset_evidence_builder_protocol_sha256")
        != INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256
        or prerequisite.get("asset_evidence_entries") != 30
        or prerequisite.get("asset_evidence_revalidated_assets") != {"audio": 30, "labels": 30}
    ):
        raise ValueError("independent V2 execution prerequisite provenance changed.")

    frozen = _require_mapping(payload.get("frozen_v2_intervention"), "frozen_v2_intervention")
    for name, expected in INDEPENDENT_V2_FROZEN_ARTIFACT_SHA256.items():
        if frozen.get(name) != expected:
            raise ValueError(f"independent V2 execution {name} changed from its frozen value.")
    if (
        frozen.get("threshold") != 0.31
        or frozen.get("encoded_feature_count") != 12
        or frozen.get("candidate_gate_placement") != "post_ranking_pre_noteon"
    ):
        raise ValueError("independent V2 execution intervention changed.")

    cohort = _require_mapping(payload.get("cohort"), "cohort")
    if cohort != {
        "manifest_split": "validation",
        "classification": "independent_validation_non_promotional",
        "recording_count": 30,
        "independent_group_count": 20,
        "recordings_per_dataset": {
            "gaps_poly_mix": 10,
            "guitar_techs_poly_directinput": 10,
            "guitar_techs_poly_micamp": 10,
            "guitarset_poly_mix": 0,
        },
        "selection_is_derived_from_full_manifest": True,
        "forbid_manual_recording_selection": True,
        "forbid_metric_audio_or_label_based_selection": True,
        "exclude_historical_recording_keys": True,
        "exclude_historical_leakage_groups": True,
        "exclude_policy_a_eligible_train_groups": True,
        "guitarset_claim_forbidden": True,
    }:
        raise ValueError("independent V2 execution cohort contract changed.")

    semantics = _require_mapping(payload.get("future_runner_semantics"), "future_runner_semantics")
    if (
        semantics.get("runner_module_to_implement")
        != "src.polyphonic.run_causal_candidate_v2_independent_validation_execution"
        or semantics.get("runner_is_not_part_of_this_contract") is not True
        or semantics.get("execution_authorized_now") is not False
        or semantics.get("single_cpu_job") is not True
        or semantics.get("wall_timeout_seconds") != 900
        or semantics.get("single_transcription_inference_per_recording") is not True
        or semantics.get("same_transcription_predictions_reused_across_ab") is not True
        or semantics.get("same_audio_evidence_masks_reused_across_ab") is not True
        or semantics.get("audio_evidence_override_forbidden") is not True
        or semantics.get("reference_has_no_causal_candidate_gate") is not True
        or semantics.get("candidate_uses_only_the_frozen_v2_intervention") is not True
        or semantics.get("candidate_gate_features_are_the_frozen_pre_ranking_v1_snapshot") is not True
        or semantics.get("candidate_gate_placement_must_equal") != "post_ranking_pre_noteon"
        or semantics.get("independent_decoder_states_after_divergence") is not True
        or semantics.get("same_hop_backfill_after_candidate_rejection") is not False
        or semantics.get("no_model_or_threshold_selection") is not True
        or semantics.get("no_automatic_retry") is not True
        or semantics.get("stop_after_report") is not True
    ):
        raise ValueError("independent V2 future runner semantics changed.")
    asset_gate = semantics.get("execution_time_asset_gate")
    if not isinstance(asset_gate, str) or "all 30 audio plus 30 label assets" not in asset_gate:
        raise ValueError("independent V2 execution-time asset gate is incomplete.")

    required_preflight = payload.get("required_before_any_future_model_loading")
    if not isinstance(required_preflight, list) or tuple(required_preflight) != (
        "implement_and_externally_review_a_new_fail_closed_runner_without_executing_it",
        "seal_a_separate_one_job_invocation_authorization_with_the_exact_reviewed_runner_commit",
        "verify_the_execution_contract_raw_bytes_before_any_manifest_or_asset_access",
        "verify_the_closed_independent_protocol_raw_bytes_and_status",
        "verify_the_historical_selection_raw_bytes",
        "derive_the_exact_thirty_recording_cohort_from_the_full_manifest_before_opening_audio_or_labels",
        "verify_all_frozen_v1_v2_artifact_hashes_before_tensorflow_or_audio_label_access",
        "rehash_the_canonical_evidence_and_all_sixty_selected_assets_inside_the_future_runner_before_opening_an_asset",
        "require_cpu_only_clean_exact_git_worktree_no_active_heavy_job_and_a_fresh_destination",
        "reject_any_test_row_historical_recording_or_historical_or_policy_a_leakage_overlap",
        "assert_post_ranking_pre_noteon_placement_before_shared_transcription_inference",
    ):
        raise ValueError("independent V2 execution preflight contract changed.")

    report = _require_mapping(payload.get("required_report_for_any_future_execution"), "required_report_for_any_future_execution")
    if (
        tuple(report.get("paired_views", ()))
        != ("reference", "candidate", "delta_candidate_minus_reference")
        or tuple(report.get("required_granularity", ()))
        != ("global", "per_dataset", "per_recording", "per_independent_leakage_group")
        or tuple(report.get("required_datasets", ()))
        != ("gaps_poly_mix", "guitar_techs_poly_directinput", "guitar_techs_poly_micamp")
        or report.get("recording_count") != 30
        or report.get("independent_group_count") != 20
        or report.get("guitarset_result_must_be_absent") is not True
        or report.get("stop_after_report") is not True
    ):
        raise ValueError("independent V2 execution report contract changed.")
    required_metrics = (
        "estimated_noteons", "matched_onset_noteons", "onset_false_positives", "onset_misses",
        "onset_precision", "onset_recall", "onset_f1", "causal_false_noteons",
        "causal_false_noteons_per_minute", "causal_recall_within_250ms", "causal_latency_p50_ms",
        "causal_latency_p90_ms", "retriggers", "excess_fragments", "midi_40_51",
        "gate_eligible_count", "gate_rejected_count"
    )
    if tuple(report.get("required_metrics", ())) != required_metrics:
        raise ValueError("independent V2 required report metrics changed.")

    consumption = _require_mapping(payload.get("validation_consumption_policy"), "validation_consumption_policy")
    if consumption != {
        "automatic_retry": False,
        "external_review_required_before_any_retry": True,
        "premetric_infrastructure_failure_only_before_scientific_observation": True,
        "premetric_infrastructure_failure_excludes": [
            "scientific_asset_open_or_decode", "transcription_or_inference",
            "any_ab_metric_production", "any_ab_metric_or_result_observation"
        ],
        "cohort_consumed_once_any_ab_metric_is_produced_or_observed": True,
        "post_observation_v2_actions_forbidden": [
            "optimization_rerun", "threshold_change", "fit", "refit", "calibration",
            "threshold_search", "model_selection", "feature_selection", "placement_change",
            "v2_modification_followed_by_cohort_rerun"
        ],
        "secondary_analysis_after_consumption": "exploratory_only_and_never_restores_independence",
    }:
        raise ValueError("independent V2 validation consumption policy changed.")
    report_policy = _require_mapping(payload.get("fail_closed_report_policy"), "fail_closed_report_policy")
    if report_policy != {
        "missing_metric_is_non_positive": True,
        "non_numeric_metric_is_non_positive": True,
        "nonfinite_metric_is_non_positive": True,
        "malformed_metric_structure_is_non_positive": True,
        "missing_required_corpus_is_non_positive": True,
        "positive_verdict": "positive_independent_evidence_non_promotional",
    }:
        raise ValueError("independent V2 fail-closed report policy changed.")

    decision = _require_mapping(payload.get("pre_registered_interpretation_rules"), "pre_registered_interpretation_rules")
    if decision != {
        "all_rules_must_pass_for_positive_independent_evidence": True,
        "global_causal_false_noteon_relative_reduction_minimum": 0.01,
        "per_dataset_causal_false_noteons_must_not_increase": True,
        "global_causal_recall_within_250ms_maximum_drop": 0.002,
        "per_dataset_causal_recall_within_250ms_maximum_drop": 0.005,
        "global_onset_f1_maximum_drop": 0.001,
        "per_dataset_onset_f1_maximum_drop": 0.002,
        "retriggers_and_excess_fragments_must_not_increase": True,
        "causal_latency_p50_and_p90_maximum_increase_ms": 5.804988662131519,
        "guitarset_claim_forbidden": True,
        "automatic_promotion": False,
    }:
        raise ValueError("independent V2 interpretation rules changed.")
    return IndependentV2ExecutionContract(
        contract_sha256=INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256,
        closed_independent_protocol_sha256=INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256,
        asset_evidence_sha256=INDEPENDENT_V2_ASSET_EVIDENCE_SHA256,
        asset_evidence_builder_protocol_sha256=(
            INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256
        ),
        recording_count=30,
        independent_group_count=20,
        wall_timeout_seconds=900,
        threshold=0.31,
        candidate_gate_placement="post_ranking_pre_noteon",
    )


def load_sealed_independent_v2_execution_contract(
    repository_root: Path,
) -> IndependentV2ExecutionContract:
    """Load the exact declarative execution contract and nothing else."""

    repository_root = Path(repository_root).resolve(strict=True)
    path = (repository_root / INDEPENDENT_V2_EXECUTION_CONTRACT_RELATIVE_PATH).resolve(
        strict=True
    )
    expected_path = (
        repository_root / INDEPENDENT_V2_EXECUTION_CONTRACT_RELATIVE_PATH
    ).resolve(strict=True)
    if path != expected_path:
        raise RuntimeError("Fail closed: independent V2 execution contract path is not canonical.")
    raw = path.read_bytes()
    if _sha256_bytes(raw) != INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256:
        raise RuntimeError("Fail closed: independent V2 execution contract SHA-256 mismatch.")
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError("independent V2 execution contract is not valid UTF-8 JSON.") from error
    contract = _require_exact_execution_payload(_require_mapping(payload, "execution contract"))
    _register_identity(contract)
    return contract


__all__ = [
    "INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256",
    "INDEPENDENT_V2_ASSET_EVIDENCE_SHA256",
    "INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256",
    "INDEPENDENT_V2_EXECUTION_ALLOWED_NOW",
    "INDEPENDENT_V2_EXECUTION_CONTRACT_RELATIVE_PATH",
    "INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256",
    "INDEPENDENT_V2_EXECUTION_CONTRACT_STATUS",
    "IndependentV2ExecutionContract",
    "load_sealed_independent_v2_execution_contract",
    "require_sealed_independent_v2_execution_contract",
]
