"""Dormant, side-effect-free contract helpers for H28.

Importing this module does not read population payloads, run NumPy, execute an
FFT, materialize a record, or authorize a scientific run.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
import re
from types import MappingProxyType
from typing import Mapping


CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h28_causal_timing_preregistration.json"
)
SCHEMA_IDENTITY = "H28_CAUSAL_CERTIFICATE_TIMING_PREREGISTRATION_V1"
HORIZON_IDS = ("N", "N_PLUS_1", "N_PLUS_2")
FIXTURE_IDS = ("H27-F-P01", "H27-F-N01")
RECORD_ORDER = tuple(
    f"{fixture_id}/{horizon_id}"
    for horizon_id in HORIZON_IDS
    for fixture_id in FIXTURE_IDS
)
ALLOWED_OUTCOMES = ("BIRTH_SUPPORTED", "NO_BIRTH", "AMBIGUOUS")
DEPENDENCY_BINDINGS = (
    ("configs/harmonic_censoring_h27_fixture_specifications.json", "9aea04053a13a3f5cf81b461a58977c377600f5b", 21241, "28707e95e2d1219fa0aa678e2103a8ef5cae7e7ca24a7100f4a84479dd0ff93d"),
    ("configs/harmonic_censoring_h27_scientific_preregistration_contract.json", "869c70f7c643d8387645377a8cf5166b8728914d", 10354, "93d081a2f1ab17396cde97f974f6f338ecb41dc5c98ed40a72289200215efe29"),
    ("configs/harmonic_censoring_h27_engine_recomputer_contract.json", "684f0594d563d40ebc51502aa0f0b987cbe44b01", 18415, "de28cef12aff887045ac244f8aa9085bdd1dab20e9587314e94a96eff546dc78"),
    ("src/polyphonic/harmonic_censoring_h27_engine.py", "ec7e775d0397a4415ca21df18c7b49528aa29387", 24316, "eb28f19d383215408516163a2f6e53f164ab1cbc7dcdbd6977954a58d49e507a"),
    ("src/polyphonic/harmonic_censoring_h27_recomputer.py", "4949137f5a827e436c92b361f36f66b6f0312bcb", 22456, "4411e27fb1c2e9846f9e5688e90cb6bcc8d1d9bfd0fd12726ffd510e9f1a286a"),
    ("src/polyphonic/harmonic_censoring_h27_review4_materializer.py", "8cdafbd6a08ea893daa2d6f41cb62166bf9162cd", 34416, "db8ab8073affa01b148da581ee4f21da99e3a2eefcc95a9c1205d907eec756bd"),
)
H27_BASELINE_PAYLOAD_SHA256 = {
    "H27-F-P01": {
        "waveform.f64le": "173183bf0a8017e8d24591cbbdd4c8055838546775917a5534c894527fa70a7e",
        "sample-valid-mask.u8": "c38ec8da6c365d305710ffee001885a5a3ee99dffe73f6acc4ebd5f2461e3205",
    },
    "H27-F-N01": {
        "waveform.f64le": "657fb5dd2a0bac49b6d4a56911d861bcc194cc04f95de6c93d2731e3da0e0ebb",
        "sample-valid-mask.u8": "c38ec8da6c365d305710ffee001885a5a3ee99dffe73f6acc4ebd5f2461e3205",
    },
}
REQUIRED_DIAGNOSTIC_FIELDS = (
    "record_identity",
    "fixture_id",
    "horizon_id",
    "proposal_hop_end",
    "maximum_sample_read",
    "role_classifications",
    "mask_counts",
    "current_short_total_power",
    "previous_short_total_power",
    "current_long_total_power",
    "previous_long_total_power",
    "exclusive_ranks",
    "exclusive_band_energies",
    "harmonic_ratios",
    "ratios_at_or_above_positive_threshold",
    "onset_rise",
    "active_residual_before_candidate",
    "augmented_residual_after_candidate",
    "residual_improvement",
    "persistence",
    "bounded_claim_lower_bounds",
    "negative_margins",
    "positive_partial_condition",
    "positive_onset_condition",
    "positive_residual_condition",
    "negative_partial_condition",
    "negative_onset_condition",
    "negative_residual_condition",
    "outcome",
    "certificate_kind",
    "certificate_complete",
    "decision_reason",
    "waveform_sha256",
    "mask_sha256",
)


@dataclass(frozen=True)
class H28Horizon:
    identity: str
    order: int
    proposal_hop_end: int
    resolution_hop_end: int
    causal_samples_after_onset: int
    causal_milliseconds: float


@dataclass(frozen=True)
class H28TimingContract:
    repository_root: Path
    raw_sha256: str
    horizons: tuple[H28Horizon, ...]
    diagnostic_fields: tuple[str, ...]
    document: Mapping[str, object]


def _reject_constant(value: str) -> object:
    raise ValueError(f"H28 non-JSON numeric constant forbidden: {value}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H28 duplicate JSON key forbidden: {key}")
        result[key] = value
    return result


def _strict_json(raw: bytes, *, label: str) -> object:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError(f"{label} must be UTF-8") from exc
    try:
        return json.loads(
            text,
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be strict JSON") from exc


def _mapping(value: object, *, label: str) -> Mapping[str, object]:
    if type(value) is not dict:
        raise ValueError(f"{label} must be an object")
    return value


def _exact_int(value: object, *, label: str) -> int:
    if type(value) is not int:
        raise ValueError(f"{label} must be an integer")
    return value


def _finite_float(value: object, *, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"{label} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _require_dependency(root: Path, value: object) -> None:
    item = _mapping(value, label="H28 fixed dependency")
    relative = Path(str(item.get("path", "")))
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("H28 dependency path must be repository-relative")
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("H28 dependency escapes repository root") from exc
    raw = path.read_bytes()
    if len(raw) != _exact_int(item.get("size_bytes"), label="H28 dependency size"):
        raise ValueError(f"H28 dependency size changed: {relative.as_posix()}")
    expected = str(item.get("sha256", ""))
    if hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError(f"H28 dependency bytes changed: {relative.as_posix()}")


def load_h28_timing_contract(repository_root: Path) -> H28TimingContract:
    """Load and fail-closed validate the dormant H28 preregistration."""

    root = Path(repository_root).resolve(strict=True)
    path = (root / CONTRACT_RELATIVE_PATH).resolve(strict=True)
    raw = path.read_bytes()
    document = _mapping(_strict_json(raw, label="H28 preregistration"), label="H28 preregistration")
    if (
        document.get("schema_identity") != SCHEMA_IDENTITY
        or type(document.get("schema_version")) is not int
        or document.get("schema_version") != 1
    ):
        raise ValueError("H28 schema identity/version changed")
    if document.get("status") != "PREREGISTERED_DORMANT_NO_SCIENTIFIC_EXECUTION":
        raise ValueError("H28 preregistration is not dormant")
    if document.get("design_base_commit") != "a441a43c80bf831b59c70f35d17dba2bff6901c0":
        raise ValueError("H28 design base changed")

    dependencies = document.get("fixed_dependencies")
    if type(dependencies) is not list or len(dependencies) != 6:
        raise ValueError("H28 fixed dependency set changed")
    observed_dependencies = tuple(
        (
            str(_mapping(item, label="H28 fixed dependency").get("path")),
            str(item.get("git_blob")),
            item.get("size_bytes"),
            str(item.get("sha256")),
        )
        for item in dependencies
    )
    if observed_dependencies != DEPENDENCY_BINDINGS:
        raise ValueError("H28 fixed dependency identity changed")
    for dependency in dependencies:
        _require_dependency(root, dependency)

    population = _mapping(document.get("population"), label="H28 population")
    if (
        population.get("fixture_ids_in_order") != list(FIXTURE_IDS)
        or population.get("record_count") != 6
        or population.get("candidate_onset_sample") != 16128
        or population.get("extended_stream_last_sample") != 17151
        or population.get("maximum_future_samples_read") != 0
        or population.get("locked_test_forbidden") is not True
        or population.get("h27_baseline_payload_sha256") != H27_BASELINE_PAYLOAD_SHA256
    ):
        raise ValueError("H28 population contract changed")

    raw_horizons = document.get("horizons")
    if type(raw_horizons) is not list or len(raw_horizons) != 3:
        raise ValueError("H28 horizon count changed")
    horizons = tuple(
        H28Horizon(
            identity=str(_mapping(item, label="H28 horizon").get("id")),
            order=_exact_int(item.get("order"), label="H28 horizon order"),
            proposal_hop_end=_exact_int(item.get("proposal_hop_end"), label="H28 proposal end"),
            resolution_hop_end=_exact_int(item.get("resolution_hop_end"), label="H28 resolution end"),
            causal_samples_after_onset=_exact_int(
                item.get("causal_samples_after_onset"), label="H28 causal samples"
            ),
            causal_milliseconds=_finite_float(
                item.get("causal_milliseconds"), label="H28 causal milliseconds"
            ),
        )
        for item in raw_horizons
    )
    expected_horizon_scalars = (
        ("N", 1, 16383, 16639, 256),
        ("N_PLUS_1", 2, 16639, 16895, 512),
        ("N_PLUS_2", 3, 16895, 17151, 768),
    )
    if tuple(
        (item.identity, item.order, item.proposal_hop_end, item.resolution_hop_end,
         item.causal_samples_after_onset)
        for item in horizons
    ) != expected_horizon_scalars:
        raise ValueError("H28 horizon geometry changed")
    for item in horizons:
        expected_ms = item.causal_samples_after_onset / 44100.0 * 1000.0
        if item.causal_milliseconds != expected_ms:
            raise ValueError("H28 causal milliseconds changed")

    science = _mapping(document.get("unchanged_science"), label="H28 unchanged science")
    required_science = {
        "window": "Hann",
        "fft_zero_padding_multiplier": 8,
        "partial_band_half_width_cents": 35.0,
        "nnls_iterations": 512,
        "positive_minimum_exclusive_energy_ratio": 0.02,
        "positive_minimum_onset_rise": 0.05,
        "positive_minimum_residual_improvement": 0.1,
        "negative_maximum_exclusive_energy_ratio": 0.002,
        "negative_maximum_onset_rise": 0.005,
        "negative_maximum_residual_improvement": 0.001,
        "negative_minimum_margin": 10.0,
        "minimum_exclusive_partial_count": 2,
        "minimum_valid_bin_count_per_partial": 3,
        "h27_engine_formulas_are_normative_reference": True,
        "h27_engine_direct_runtime_reuse_forbidden": True,
        "h28_geometry_only_engine_adapter_required": True,
    }
    for key, expected in required_science.items():
        if science.get(key) != expected:
            raise ValueError(f"H28 inherited science changed: {key}")
    if science.get("permitted_engine_geometry_changes") != [
        "waveform sample count 16640 to 17152",
        "role-major mask plane length 16640 to 17152",
        "proposal horizon upper bound extended through 16895",
        "complete diagnostic serialization",
    ]:
        raise ValueError("H28 permitted engine geometry changes changed")

    evaluation = _mapping(document.get("evaluation_contract"), label="H28 evaluation")
    if evaluation.get("record_order") != list(RECORD_ORDER):
        raise ValueError("H28 record order changed")
    if (
        evaluation.get("independent_snapshot_per_fixture_and_horizon") is not True
        or evaluation.get("decoder_state_carry_between_horizons_forbidden") is not True
        or evaluation.get("h27_engine_and_recomputer_are_reference_only") is not True
        or evaluation.get("direct_h27_engine_invocation_for_h28_forbidden") is not True
        or evaluation.get("independent_h28_engine_and_h28_recomputer_required") is not True
        or evaluation.get("n01_birth_at_any_horizon_is_safety_failure") is not True
    ):
        raise ValueError("H28 evaluation boundary changed")

    diagnostic_fields = document.get("required_diagnostic_fields")
    if diagnostic_fields != list(REQUIRED_DIAGNOSTIC_FIELDS):
        raise ValueError("H28 diagnostic schema changed")

    authorization = _mapping(document.get("authorization_boundary"), label="H28 authorization")
    for forbidden in (
        "population_materialization_authorized",
        "scientific_execution_authorized",
        "mac_execution_authorized",
        "training_authorized",
        "calibration_authorized",
        "checkpoint_selection_authorized",
        "locked_test_authorized",
    ):
        if authorization.get(forbidden) is not False:
            raise ValueError(f"H28 forbidden authorization changed: {forbidden}")
    if authorization.get("requires_external_review_before_materialization") is not True:
        raise ValueError("H28 external review gate changed")

    return H28TimingContract(
        repository_root=root,
        raw_sha256=hashlib.sha256(raw).hexdigest(),
        horizons=horizons,
        diagnostic_fields=REQUIRED_DIAGNOSTIC_FIELDS,
        document=MappingProxyType(dict(document)),
    )


def derive_h28_terminal_verdict(outcomes: Mapping[str, str]) -> str:
    """Apply the preregistered verdict order to six already-computed outcomes."""

    if tuple(outcomes) != RECORD_ORDER:
        raise ValueError("H28 outcomes must use the exact sealed record order")
    if any(value not in ALLOWED_OUTCOMES for value in outcomes.values()):
        raise ValueError("H28 outcome outside the timing-study state space")
    if any(outcomes[f"H27-F-N01/{horizon}"] == "BIRTH_SUPPORTED" for horizon in HORIZON_IDS):
        return "H28_NEGATIVE_CONTROL_BECAME_BIRTH_SUPPORTED"
    for horizon in HORIZON_IDS:
        if outcomes[f"H27-F-P01/{horizon}"] == "BIRTH_SUPPORTED":
            return f"H28_P01_FIRST_SUPPORTED_AT_{horizon}"
    return "H28_TIMING_INSUFFICIENT_THROUGH_N_PLUS_2"


def _numeric_sequence(value: object, *, label: str, allow_infinity: bool = False) -> tuple[float, ...]:
    if type(value) is not list:
        raise ValueError(f"{label} must be an array")
    result: list[float] = []
    for item in value:
        if allow_infinity and item == "Infinity":
            result.append(math.inf)
        else:
            result.append(_finite_float(item, label=label))
    return tuple(result)


def validate_h28_diagnostic_record(
    contract: H28TimingContract, value: object,
) -> Mapping[str, object]:
    """Validate one future serialized row without reading or computing a spectrum."""

    row = _mapping(value, label="H28 diagnostic record")
    if tuple(row) != REQUIRED_DIAGNOSTIC_FIELDS:
        raise ValueError("H28 diagnostic fields or order changed")
    if type(row["fixture_id"]) is not str or type(row["horizon_id"]) is not str:
        raise ValueError("H28 diagnostic fixture/horizon must be strings")
    fixture_id, horizon_id = row["fixture_id"], row["horizon_id"]
    if fixture_id not in FIXTURE_IDS or horizon_id not in HORIZON_IDS:
        raise ValueError("H28 diagnostic fixture/horizon invalid")
    if row["record_identity"] != f"{fixture_id}/{horizon_id}":
        raise ValueError("H28 diagnostic record identity invalid")
    horizon = next(item for item in contract.horizons if item.identity == horizon_id)
    if row["proposal_hop_end"] != horizon.proposal_hop_end:
        raise ValueError("H28 diagnostic proposal horizon changed")
    maximum_read = _exact_int(row["maximum_sample_read"], label="H28 maximum sample read")
    if maximum_read != horizon.proposal_hop_end:
        raise ValueError("H28 diagnostic maximum read must equal the causal horizon")

    roles = ("current_short", "previous_short", "current_long", "previous_long")
    role_classifications = _mapping(row["role_classifications"], label="H28 role classifications")
    mask_counts = _mapping(row["mask_counts"], label="H28 mask counts")
    if tuple(role_classifications) != roles or tuple(mask_counts) != roles:
        raise ValueError("H28 role mapping changed")
    if any(type(value) is not int for value in mask_counts.values()):
        raise ValueError("H28 diagnostic support counts must be integers")
    if tuple(mask_counts.values()) != (4096, 4096, 8192, 8192):
        raise ValueError("H28 diagnostic support is incomplete")
    expected_roles = {
        "current_short": "VALID_CURRENT_SHORT_ANALYSIS",
        "previous_short": (
            "VALID_EXACT_ZERO_PREVIOUS_SHORT"
            if fixture_id == "H27-F-P01" and horizon_id == "N"
            else "VALID_PREVIOUS_SHORT_ANALYSIS"
        ),
        "current_long": "VALID_CURRENT_LONG_ANALYSIS",
        "previous_long": (
            "VALID_EXACT_ZERO_PREVIOUS_LONG"
            if fixture_id == "H27-F-P01" and horizon_id == "N"
            else "VALID_PREVIOUS_LONG_ANALYSIS"
        ),
    }
    if dict(role_classifications) != expected_roles:
        raise ValueError("H28 role classification is inconsistent with fixture/horizon")

    for field in (
        "current_short_total_power",
        "previous_short_total_power",
        "current_long_total_power",
        "previous_long_total_power",
        "onset_rise",
        "active_residual_before_candidate",
        "augmented_residual_after_candidate",
        "residual_improvement",
        "persistence",
    ):
        number = _finite_float(row[field], label=f"H28 {field}")
        if field != "persistence" and number < 0.0:
            raise ValueError(f"H28 {field} must be nonnegative")

    ranks_raw = row["exclusive_ranks"]
    if type(ranks_raw) is not list:
        raise ValueError("H28 exclusive ranks must be an array")
    ranks = tuple(ranks_raw)
    if ranks != tuple(sorted(set(ranks))) or any(type(item) is not int or not 1 <= item <= 8 for item in ranks):
        raise ValueError("H28 exclusive ranks invalid")
    energies = _numeric_sequence(row["exclusive_band_energies"], label="H28 exclusive energies")
    ratios = _numeric_sequence(row["harmonic_ratios"], label="H28 harmonic ratios")
    bounds = _numeric_sequence(row["bounded_claim_lower_bounds"], label="H28 lower bounds")
    margins = _numeric_sequence(row["negative_margins"], label="H28 negative margins", allow_infinity=True)
    if not len(ranks) == len(energies) == len(ratios) == len(bounds) == len(margins):
        raise ValueError("H28 exclusive diagnostic lengths differ")
    if any(number < 0.0 for values in (energies, ratios, bounds, margins) for number in values):
        raise ValueError("H28 exclusive diagnostics must be nonnegative")

    ratio_count = sum(number >= 0.02 for number in ratios)
    if (
        type(row["ratios_at_or_above_positive_threshold"]) is not int
        or row["ratios_at_or_above_positive_threshold"] != ratio_count
    ):
        raise ValueError("H28 positive ratio count inconsistent")
    positive_partial = ratio_count >= 2
    positive_onset = float(row["onset_rise"]) >= 0.05
    positive_residual = float(row["residual_improvement"]) >= 0.1
    bounded = tuple(index for index, number in enumerate(bounds) if number >= 0.02)
    negative_partial = (
        len(bounded) >= 2
        and all(ratios[index] <= 0.002 and margins[index] >= 10.0 for index in bounded)
    )
    negative_onset = float(row["onset_rise"]) <= 0.005
    negative_residual = float(row["residual_improvement"]) <= 0.001
    derived_conditions = {
        "positive_partial_condition": positive_partial,
        "positive_onset_condition": positive_onset,
        "positive_residual_condition": positive_residual,
        "negative_partial_condition": negative_partial,
        "negative_onset_condition": negative_onset,
        "negative_residual_condition": negative_residual,
    }
    for field, expected in derived_conditions.items():
        if type(row[field]) is not bool or row[field] is not expected:
            raise ValueError(f"H28 derived condition inconsistent: {field}")

    if positive_partial and positive_onset and positive_residual:
        expected_decision = ("BIRTH_SUPPORTED", "POSITIVE", True, "complete_positive_certificate")
    elif negative_partial and negative_onset and negative_residual:
        expected_decision = ("NO_BIRTH", "NEGATIVE", True, "complete_bounded_negative_certificate")
    else:
        expected_decision = ("AMBIGUOUS", "NONE", False, "certificate_gap_or_conflict")
    if type(row["certificate_complete"]) is not bool:
        raise ValueError("H28 certificate_complete must be boolean")
    observed_decision = (
        row["outcome"], row["certificate_kind"], row["certificate_complete"], row["decision_reason"]
    )
    if observed_decision != expected_decision:
        raise ValueError("H28 serialized decision is inconsistent with diagnostics")
    for field in ("waveform_sha256", "mask_sha256"):
        if type(row[field]) is not str or re.fullmatch(r"[0-9a-f]{64}", row[field]) is None:
            raise ValueError(f"H28 {field} invalid")
    return MappingProxyType(dict(row))


__all__ = [
    "ALLOWED_OUTCOMES",
    "CONTRACT_RELATIVE_PATH",
    "FIXTURE_IDS",
    "HORIZON_IDS",
    "H28Horizon",
    "H28TimingContract",
    "RECORD_ORDER",
    "REQUIRED_DIAGNOSTIC_FIELDS",
    "derive_h28_terminal_verdict",
    "load_h28_timing_contract",
    "validate_h28_diagnostic_record",
]
