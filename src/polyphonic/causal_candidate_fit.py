"""Fail-closed preparation for the preregistered causal candidate fit V1.

This module deliberately has no command-line entry point and no function that
calls Model.fit. It implements the data contract only: sealed-artifact
preflight, exact causal feature projection, group-safe weights, threshold-free
dev metrics, calibration policy, and deterministic construction of the tiny
logistic model. A separately reviewed runner will be required before any fit
may execute.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import random
import sys
from typing import Iterable, Mapping, Sequence

from .decoder_candidate_mining import CAUSAL_FEATURES
from .decoder_reason_codes import CANDIDATE_REASON_VOCABULARY


FIT_PARTITIONS = ("fit", "dev", "calibration")
PARTITION_ORDER = {name: index for index, name in enumerate(FIT_PARTITIONS)}
FIT_SCHEMA_VERSION = 1
TARGET_FIELD = "causal_noteon_target"
FEATURE_DIMENSION = 12
V1_FIT_SEED = 47
FAMILIES = (
    "gaps_poly_mix",
    "guitar_techs_paired",
    "guitarset_poly_mix",
)
FAMILY_BY_DATASET = {
    "gaps_poly_mix": "gaps_poly_mix",
    "guitar_techs_poly_directinput": "guitar_techs_paired",
    "guitar_techs_poly_micamp": "guitar_techs_paired",
    "guitarset_poly_mix": "guitarset_poly_mix",
}
NUMERIC_FEATURES = (
    "frame_probability",
    "onset_probability",
    "candidate_score",
    "harmonic_support",
    "log1p_active_polyphony",
)
BOOLEAN_FEATURES = (
    "audio_onset_available",
    "audio_onset_recent",
)
ONE_HOT_FEATURES = tuple(
    f"candidate_reason={reason}" for reason in CANDIDATE_REASON_VOCABULARY
)
ENCODED_FEATURES = NUMERIC_FEATURES + BOOLEAN_FEATURES + ONE_HOT_FEATURES
EXPECTED_CAUSAL_FEATURES = (
    "frame_probability",
    "onset_probability",
    "candidate_score",
    "candidate_reason",
    "harmonic_support",
    "audio_onset_available",
    "audio_onset_recent",
    "active_polyphony",
)
if CAUSAL_FEATURES != EXPECTED_CAUSAL_FEATURES:
    raise RuntimeError("The sealed V1 causal feature contract changed.")

V1_EVENT_ROWS_SHA256 = (
    "fd852626f56b038837266b5336b318c8adf841c1aafbd01d36b362f7fe10150d"
)
V1_REPORT_SHA256 = (
    "e13a13be38710e7a15f9d6d222d0a7835aad204a1b7c821d8198d1ac9ccffe59"
)
V1_MINING_PROTOCOL_SHA256 = (
    "db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683"
)
V1_IMPLEMENTATION_COMMIT = "4ddc88666a1c55725c18a813c63ecd25a03bf298"
V1_MINING_PURPOSE = "decoder_candidate_guitarset_expansion_train_only_mining_v3"
V1_PARTITION_COUNTS = {
    "fit": (694, 244),
    "dev": (968, 250),
    "calibration": (793, 190),
}
V1_PROTOCOL_DIGESTS = {
    "manifest_sha256": (
        "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
    ),
    "partition_plan_sha256": (
        "a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4"
    ),
    "asset_evidence_sha256": (
        "12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507"
    ),
    "checkpoint_sha256": (
        "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
    ),
    "model_config_sha256": (
        "245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804"
    ),
    "decoder_config_sha256": (
        "c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96"
    ),
    "audio_evidence_config_sha256": (
        "45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e"
    ),
}


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _require_exact_bool(value: object, name: str) -> bool:
    if type(value) is not bool:
        raise ValueError(f"{name} must be a JSON boolean.")
    return bool(value)


def _require_non_empty_string(value: object, name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{name} must be a non-empty string.")
    return value


def _require_finite_number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a JSON number.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"{name} must be finite.")
    return result


@dataclass(frozen=True)
class CandidateFitContract:
    """All values that bind a future fit to one reviewed candidate artifact."""

    candidate_events_sha256: str
    mining_report_sha256: str
    mining_protocol_sha256: str
    implementation_commit: str
    mining_purpose: str
    partition_counts: Mapping[str, tuple[int, int]]
    required_protocol_digests: Mapping[str, str]

    def __post_init__(self) -> None:
        for name in (
            "candidate_events_sha256",
            "mining_report_sha256",
            "mining_protocol_sha256",
        ):
            value = getattr(self, name)
            if not (
                isinstance(value, str)
                and len(value) == 64
                and all(char in "0123456789abcdef" for char in value)
            ):
                raise ValueError(f"{name} must be a lowercase SHA-256 digest.")
        if not (
            isinstance(self.implementation_commit, str)
            and len(self.implementation_commit) == 40
            and all(char in "0123456789abcdef" for char in self.implementation_commit)
        ):
            raise ValueError("implementation_commit must be a lowercase Git SHA.")
        _require_non_empty_string(self.mining_purpose, "mining_purpose")
        if set(self.partition_counts) != set(FIT_PARTITIONS):
            raise ValueError("partition_counts must declare fit, dev and calibration.")
        for partition, counts in self.partition_counts.items():
            if (
                type(counts) is not tuple
                or len(counts) != 2
                or any(type(value) is not int or value < 1 for value in counts)
            ):
                raise ValueError(
                    f"partition_counts[{partition!r}] must be two positive integers."
                )
        for name, value in self.required_protocol_digests.items():
            if not (
                isinstance(name, str)
                and isinstance(value, str)
                and len(value) == 64
                and all(char in "0123456789abcdef" for char in value)
            ):
                raise ValueError("required_protocol_digests must contain SHA-256 values.")


V1_CONTRACT = CandidateFitContract(
    candidate_events_sha256=V1_EVENT_ROWS_SHA256,
    mining_report_sha256=V1_REPORT_SHA256,
    mining_protocol_sha256=V1_MINING_PROTOCOL_SHA256,
    implementation_commit=V1_IMPLEMENTATION_COMMIT,
    mining_purpose=V1_MINING_PURPOSE,
    partition_counts=V1_PARTITION_COUNTS,
    required_protocol_digests=V1_PROTOCOL_DIGESTS,
)


@dataclass(frozen=True)
class CandidateFitRow:
    """One already-labelled real NoteOn candidate eligible for future fitting."""

    event_id: str
    partition: str
    dataset_id: str
    source_id: str
    group_id: str
    capture_id: str
    leakage_group_key: str
    target: int
    frame_probability: float
    onset_probability: float
    candidate_score: float
    candidate_reason: str
    harmonic_support: float
    audio_onset_available: bool
    audio_onset_recent: bool
    active_polyphony: int

    @property
    def family(self) -> str:
        try:
            return FAMILY_BY_DATASET[self.dataset_id]
        except KeyError as error:
            raise ValueError(f"Unsupported candidate dataset: {self.dataset_id}") from error

    @classmethod
    def from_json(cls, payload: Mapping[str, object]) -> "CandidateFitRow":
        if not isinstance(payload, Mapping):
            raise ValueError("candidate row must be a JSON object.")
        if (
            type(payload.get("schema_version")) is not int
            or payload["schema_version"] != FIT_SCHEMA_VERSION
        ):
            raise ValueError("candidate row schema_version is unsupported.")
        partition = _require_non_empty_string(payload.get("partition"), "partition")
        if partition not in FIT_PARTITIONS:
            raise ValueError("candidate row must belong to a train-only partition.")
        target = payload.get(TARGET_FIELD)
        if type(target) is not int or target not in (0, 1):
            raise ValueError("causal_noteon_target must be 0 or 1.")
        if not _require_exact_bool(payload.get("gate_eligible"), "gate_eligible"):
            raise ValueError("candidate rows must be gate eligible.")
        if not _require_exact_bool(payload.get("post_gate_selected"), "post_gate_selected"):
            raise ValueError("candidate rows must be post-gate selected.")
        if not _require_exact_bool(payload.get("emitted_noteon"), "emitted_noteon"):
            raise ValueError("candidate rows must be emitted NoteOns.")
        reason = _require_non_empty_string(
            payload.get("candidate_reason"), "candidate_reason"
        )
        if reason not in CANDIDATE_REASON_VOCABULARY:
            raise ValueError("candidate_reason is outside the fixed pre-gate vocabulary.")
        values = {
            name: _require_finite_number(payload.get(name), name)
            for name in (
                "frame_probability",
                "onset_probability",
                "candidate_score",
                "harmonic_support",
            )
        }
        for name in ("frame_probability", "onset_probability", "harmonic_support"):
            if not 0.0 <= values[name] <= 1.0:
                raise ValueError(f"{name} must be in [0, 1].")
        active_polyphony = payload.get("active_polyphony")
        if type(active_polyphony) is not int or active_polyphony < 0:
            raise ValueError("active_polyphony must be a non-negative integer.")
        available = _require_exact_bool(
            payload.get("audio_onset_available"), "audio_onset_available"
        )
        recent = _require_exact_bool(
            payload.get("audio_onset_recent"), "audio_onset_recent"
        )
        if recent and not available:
            raise ValueError("audio_onset_recent requires audio_onset_available.")
        row = cls(
            event_id=_require_non_empty_string(payload.get("event_id"), "event_id"),
            partition=partition,
            dataset_id=_require_non_empty_string(payload.get("dataset_id"), "dataset_id"),
            source_id=_require_non_empty_string(payload.get("source_id"), "source_id"),
            group_id=_require_non_empty_string(payload.get("group_id"), "group_id"),
            capture_id=_require_non_empty_string(payload.get("capture_id"), "capture_id"),
            leakage_group_key=_require_non_empty_string(
                payload.get("leakage_group_key"), "leakage_group_key"
            ),
            target=target,
            frame_probability=values["frame_probability"],
            onset_probability=values["onset_probability"],
            candidate_score=values["candidate_score"],
            candidate_reason=reason,
            harmonic_support=values["harmonic_support"],
            audio_onset_available=available,
            audio_onset_recent=recent,
            active_polyphony=active_polyphony,
        )
        _ = row.family
        return row


@dataclass(frozen=True)
class CandidateFitPreflight:
    """Verified immutable rows ready for a future, separately-approved fit."""

    rows: tuple[CandidateFitRow, ...]
    candidate_events_sha256: str
    mining_report_sha256: str
    mining_protocol_sha256: str

    def rows_for_partition(self, partition: str) -> tuple[CandidateFitRow, ...]:
        if partition not in FIT_PARTITIONS:
            raise ValueError("Unknown fit partition.")
        return tuple(row for row in self.rows if row.partition == partition)


@dataclass(frozen=True)
class CandidateFitExecutionSpec:
    """Fixed optimization arguments for a future separately-reviewed runner.

    ``shuffle=False`` is intentional.  The input is canonicalized before a
    runner sees it, so no unrecorded TensorFlow shuffle seed can change the
    order of the sequential Adam updates.
    """

    seed: int = V1_FIT_SEED
    batch_size: int = 64
    learning_rate: float = 0.01
    maximum_epochs: int = 40
    patience: int = 5
    min_delta: float = 1e-4
    shuffle: bool = False

    def __post_init__(self) -> None:
        for name in ("seed", "batch_size", "maximum_epochs", "patience"):
            value = getattr(self, name)
            if type(value) is not int or value < 0:
                raise ValueError(f"{name} must be a non-negative integer.")
        if self.batch_size < 1 or self.maximum_epochs < 1 or self.patience < 1:
            raise ValueError("batch_size, maximum_epochs and patience must be positive.")
        for name in ("learning_rate", "min_delta"):
            value = getattr(self, name)
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{name} must be a finite positive number.")
            if not math.isfinite(float(value)) or float(value) <= 0.0:
                raise ValueError(f"{name} must be a finite positive number.")
        if self.shuffle is not False:
            raise ValueError("V1 fit requires shuffle=False for deterministic updates.")


V1_EXECUTION_SPEC = CandidateFitExecutionSpec()


@dataclass(frozen=True)
class FitStandardizer:
    """Fit-only parameters for the five numerical pre-gate features."""

    mean: tuple[float, ...]
    scale: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.mean) != len(NUMERIC_FEATURES) or len(self.scale) != len(NUMERIC_FEATURES):
            raise ValueError("standardizer must have one value per numerical feature.")
        if not all(math.isfinite(value) for value in self.mean):
            raise ValueError("standardizer means must be finite.")
        if not all(math.isfinite(value) and value > 0.0 for value in self.scale):
            raise ValueError("standardizer scales must be finite and positive.")

    def transform(self, row: CandidateFitRow) -> tuple[float, ...]:
        raw = _numeric_values(row)
        normalized = tuple(
            (value - mean) / scale
            for value, mean, scale in zip(raw, self.mean, self.scale)
        )
        one_hot = tuple(
            1.0 if row.candidate_reason == reason else 0.0
            for reason in CANDIDATE_REASON_VOCABULARY
        )
        vector = normalized + (
            float(row.audio_onset_available),
            float(row.audio_onset_recent),
        ) + one_hot
        if len(vector) != FEATURE_DIMENSION or not all(math.isfinite(value) for value in vector):
            raise AssertionError("candidate feature projection is invalid.")
        return vector


@dataclass(frozen=True)
class DevSignal:
    weighted_bce: float
    weighted_brier: float
    roc_auc_by_family: Mapping[str, float]
    passed: bool


@dataclass(frozen=True)
class CalibrationDecision:
    threshold: float | None
    weighted_brier: float
    rows: tuple[Mapping[str, float | bool], ...]


@dataclass(frozen=True)
class SerializationParity:
    """Exact save/reload evidence required from a future fit runner."""

    model_path: Path
    maximum_absolute_error: float

    def __post_init__(self) -> None:
        if self.model_path.suffix != ".keras":
            raise ValueError("V1 serialization parity requires a .keras path.")
        if (
            not math.isfinite(self.maximum_absolute_error)
            or self.maximum_absolute_error < 0.0
        ):
            raise ValueError("maximum_absolute_error must be finite and non-negative.")


def _numeric_values(row: CandidateFitRow) -> tuple[float, ...]:
    return (
        row.frame_probability,
        row.onset_probability,
        row.candidate_score,
        row.harmonic_support,
        math.log1p(row.active_polyphony),
    )


def canonical_candidate_order(
    rows: Iterable[CandidateFitRow],
) -> tuple[CandidateFitRow, ...]:
    result = tuple(sorted(
        rows,
        key=lambda row: (
            PARTITION_ORDER[row.partition],
            row.dataset_id,
            row.leakage_group_key,
            row.source_id,
            row.capture_id,
            row.event_id,
        ),
    ))
    ids = [row.event_id for row in result]
    if len(ids) != len(set(ids)):
        raise ValueError("candidate artifact contains duplicate event_id values.")
    return result


def fit_standardizer(rows: Sequence[CandidateFitRow]) -> FitStandardizer:
    if not rows:
        raise ValueError("fit standardization requires at least one row.")
    if any(row.partition != "fit" for row in rows):
        raise ValueError("standardizer may be fitted on fit rows only.")
    columns = tuple(zip(*(_numeric_values(row) for row in rows)))
    mean = tuple(math.fsum(column) / len(column) for column in columns)
    scale = tuple(math.sqrt(math.fsum(
        (value - average) ** 2 for value in column
    ) / len(column)) for column, average in zip(columns, mean))
    return FitStandardizer(mean=mean, scale=scale)


def transform_rows(
    rows: Sequence[CandidateFitRow],
    standardizer: FitStandardizer,
) -> tuple[tuple[float, ...], ...]:
    return tuple(standardizer.transform(row) for row in rows)


def group_balanced_weights(rows: Sequence[CandidateFitRow]) -> tuple[float, ...]:
    """Equalize family × target cells and leakage groups within each cell."""

    if not rows:
        raise ValueError("group balancing requires at least one row.")
    partition = rows[0].partition
    if partition not in FIT_PARTITIONS or any(row.partition != partition for row in rows):
        raise ValueError("weights must be calculated within exactly one partition.")
    _require_complete_family_target_cells(rows)
    groups: dict[tuple[str, int], dict[str, list[int]]] = defaultdict(
        lambda: defaultdict(list)
    )
    for index, row in enumerate(rows):
        groups[(row.family, row.target)][row.leakage_group_key].append(index)
    total = len(rows)
    weights = [0.0] * total
    for cell_groups in groups.values():
        group_count = len(cell_groups)
        for indexes in cell_groups.values():
            value = total / (6.0 * group_count * len(indexes))
            for index in indexes:
                weights[index] = value
    if not all(math.isfinite(value) and value > 0.0 for value in weights):
        raise AssertionError("invalid group-balanced weight.")
    if not math.isclose(math.fsum(weights), float(total), rel_tol=0.0, abs_tol=1e-9):
        raise AssertionError("group-balanced weights must have mean one.")
    return tuple(weights)


def weighted_binary_crossentropy(
    targets: Sequence[int],
    probabilities: Sequence[float],
    weights: Sequence[float],
) -> float:
    _validate_metric_inputs(targets, probabilities, weights)
    epsilon = 1e-7
    values = (
        -weight * (
            target * math.log(min(max(probability, epsilon), 1.0 - epsilon))
            + (1 - target) * math.log(
                1.0 - min(max(probability, epsilon), 1.0 - epsilon)
            )
        )
        for target, probability, weight in zip(targets, probabilities, weights)
    )
    return math.fsum(values) / math.fsum(weights)


def weighted_brier_score(
    targets: Sequence[int],
    probabilities: Sequence[float],
    weights: Sequence[float],
) -> float:
    _validate_metric_inputs(targets, probabilities, weights)
    return math.fsum(
        weight * (probability - target) ** 2
        for target, probability, weight in zip(targets, probabilities, weights)
    ) / math.fsum(weights)


def weighted_roc_auc(
    targets: Sequence[int],
    probabilities: Sequence[float],
    weights: Sequence[float],
) -> float:
    """Weighted AUC with exact half-credit for tied probabilities."""

    _validate_metric_inputs(targets, probabilities, weights)
    positives = math.fsum(weight for target, weight in zip(targets, weights) if target)
    negatives = math.fsum(weight for target, weight in zip(targets, weights) if not target)
    if positives <= 0.0 or negatives <= 0.0:
        raise ValueError("ROC AUC requires positive and negative examples.")
    ordered = sorted(
        zip(probabilities, targets, weights),
        key=lambda value: value[0],
    )
    negative_before = 0.0
    favourable = 0.0
    index = 0
    while index < len(ordered):
        score = ordered[index][0]
        group: list[tuple[float, int, float]] = []
        while index < len(ordered) and ordered[index][0] == score:
            group.append(ordered[index])
            index += 1
        group_positive = math.fsum(weight for _, target, weight in group if target)
        group_negative = math.fsum(weight for _, target, weight in group if not target)
        favourable += group_positive * (negative_before + 0.5 * group_negative)
        negative_before += group_negative
    return favourable / (positives * negatives)


def assess_dev_signal(
    rows: Sequence[CandidateFitRow],
    probabilities: Sequence[float],
    weights: Sequence[float] | None = None,
) -> DevSignal:
    if not rows or any(row.partition != "dev" for row in rows):
        raise ValueError("dev signal requires only dev rows.")
    _require_complete_family_target_cells(rows)
    if weights is None:
        weights = group_balanced_weights(rows)
    targets = tuple(row.target for row in rows)
    bce = weighted_binary_crossentropy(targets, probabilities, weights)
    brier = weighted_brier_score(targets, probabilities, weights)
    auc_by_family: dict[str, float] = {}
    for family in FAMILIES:
        indexes = [index for index, row in enumerate(rows) if row.family == family]
        auc_by_family[family] = weighted_roc_auc(
            [targets[index] for index in indexes],
            [probabilities[index] for index in indexes],
            [weights[index] for index in indexes],
        )
    return DevSignal(
        weighted_bce=bce,
        weighted_brier=brier,
        roc_auc_by_family=auc_by_family,
        passed=(
            brier < 0.25
            and all(value >= 0.55 for value in auc_by_family.values())
        ),
    )


def choose_calibration_threshold(
    rows: Sequence[CandidateFitRow],
    probabilities: Sequence[float],
    weights: Sequence[float] | None = None,
) -> CalibrationDecision:
    if not rows or any(row.partition != "calibration" for row in rows):
        raise ValueError("calibration requires only calibration rows.")
    _require_complete_family_target_cells(rows)
    if weights is None:
        weights = group_balanced_weights(rows)
    targets = tuple(row.target for row in rows)
    brier = weighted_brier_score(targets, probabilities, weights)
    rows_by_threshold: list[Mapping[str, float | bool]] = []
    selected: float | None = None
    for integer_threshold in range(1, 100):
        threshold = integer_threshold / 100.0
        kept = [probability >= threshold for probability in probabilities]
        positive_indexes = [index for index, target in enumerate(targets) if target]
        negative_indexes = [index for index, target in enumerate(targets) if not target]
        global_recall = (
            sum(kept[index] for index in positive_indexes) / len(positive_indexes)
        )
        family_recall = {
            family: (
                sum(
                    kept[index]
                    for index, row in enumerate(rows)
                    if row.family == family and row.target == 1
                )
                / sum(
                    row.target == 1 for row in rows if row.family == family
                )
            )
            for family in FAMILIES
        }
        negative_weight = math.fsum(weights[index] for index in negative_indexes)
        removed_weight = math.fsum(
            weights[index] for index in negative_indexes if not kept[index]
        )
        removal = removed_weight / negative_weight
        eligible = (
            brier < 0.25
            and global_recall >= 0.98
            and all(value >= 0.90 for value in family_recall.values())
            and removal >= 0.05
        )
        rows_by_threshold.append({
            "threshold": threshold,
            "global_raw_recall": global_recall,
            "gaps_raw_recall": family_recall["gaps_poly_mix"],
            "guitar_techs_raw_recall": family_recall["guitar_techs_paired"],
            "guitarset_raw_recall": family_recall["guitarset_poly_mix"],
            "group_balanced_false_noteon_removal": removal,
            "eligible": eligible,
        })
        if eligible and selected is None:
            selected = threshold
    return CalibrationDecision(
        threshold=selected,
        weighted_brier=brier,
        rows=tuple(rows_by_threshold),
    )


def preflight_sealed_candidate_artifact(
    candidate_events_path: Path,
    mining_report_path: Path,
    mining_protocol_path: Path,
    contract: CandidateFitContract = V1_CONTRACT,
) -> CandidateFitPreflight:
    """Verify reviewed V3 evidence before a future runner can see fit rows."""

    candidate_events_path = candidate_events_path.resolve(strict=True)
    mining_report_path = mining_report_path.resolve(strict=True)
    mining_protocol_path = mining_protocol_path.resolve(strict=True)
    events_bytes = candidate_events_path.read_bytes()
    report_bytes = mining_report_path.read_bytes()
    protocol_bytes = mining_protocol_path.read_bytes()
    actual_events_sha = hashlib.sha256(events_bytes).hexdigest()
    actual_report_sha = hashlib.sha256(report_bytes).hexdigest()
    actual_protocol_sha = hashlib.sha256(protocol_bytes).hexdigest()
    if actual_events_sha != contract.candidate_events_sha256:
        raise RuntimeError("candidate_events.jsonl SHA-256 mismatch.")
    if actual_report_sha != contract.mining_report_sha256:
        raise RuntimeError("mining_report.json SHA-256 mismatch.")
    if actual_protocol_sha != contract.mining_protocol_sha256:
        raise RuntimeError("mining protocol SHA-256 mismatch.")
    report = json.loads(report_bytes.decode("utf-8"))
    if not isinstance(report, Mapping):
        raise ValueError("mining report must be a JSON object.")
    if type(report.get("schema_version")) is not int or report["schema_version"] != 1:
        raise ValueError("candidate mining report schema_version is unsupported.")
    if report.get("purpose") != contract.mining_purpose:
        raise RuntimeError("candidate mining report purpose mismatch.")
    if report.get("status") != "complete_non_authorizing":
        raise RuntimeError("candidate mining report is not terminal and non-authorizing.")
    if report.get("locked_test_used") is not False or report.get("fit_authorized") is not False:
        raise RuntimeError("candidate report violates train-only authorization.")
    if report.get("implementation_commit") != contract.implementation_commit:
        raise RuntimeError("candidate report implementation commit mismatch.")
    protocol = report.get("protocol")
    if not isinstance(protocol, Mapping):
        raise ValueError("candidate report has no protocol mapping.")
    for name, expected in contract.required_protocol_digests.items():
        if protocol.get(name) != expected:
            raise RuntimeError(f"candidate report protocol mismatch: {name}.")
    parsed = [
        CandidateFitRow.from_json(json.loads(line))
        for line in events_bytes.decode("utf-8").splitlines()
        if line.strip()
    ]
    rows = canonical_candidate_order(parsed)
    counts: dict[str, tuple[int, int]] = {}
    for partition in FIT_PARTITIONS:
        subset = [row for row in rows if row.partition == partition]
        counts[partition] = (
            sum(row.target == 0 for row in subset),
            sum(row.target == 1 for row in subset),
        )
    if counts != dict(contract.partition_counts):
        raise RuntimeError(
            f"candidate partition target counts mismatch: expected "
            f"{dict(contract.partition_counts)}, got {counts}."
        )
    return CandidateFitPreflight(
        rows=rows,
        candidate_events_sha256=actual_events_sha,
        mining_report_sha256=actual_report_sha,
        mining_protocol_sha256=actual_protocol_sha,
    )


def configure_deterministic_cpu_tensorflow(seed: int = 47):
    """Import TensorFlow only for a separately-reviewed fit runner."""

    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    if os.environ.get("MIDI_FORCE_CPU") != "1":
        raise RuntimeError("Fail closed: candidate fit requires MIDI_FORCE_CPU=1.")
    # This has to precede the import for CUDA builds.  TensorFlow Metal still
    # needs the explicit visibility call below after import.
    os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
    if "tensorflow" in sys.modules:
        raise RuntimeError(
            "Fail closed: TensorFlow must be configured before it is imported."
        )
    deterministic_ops = os.environ.get("TF_DETERMINISTIC_OPS")
    if deterministic_ops not in (None, "1"):
        raise RuntimeError("Fail closed: TF_DETERMINISTIC_OPS must be 1.")
    os.environ["TF_DETERMINISTIC_OPS"] = "1"
    random.seed(seed)
    try:
        import numpy as np
        import tensorflow as tf
    except ImportError as error:
        raise RuntimeError("candidate fit requires NumPy and TensorFlow.") from error
    np.random.seed(seed)
    tf.keras.utils.set_random_seed(seed)
    try:
        tf.config.set_visible_devices([], "GPU")
    except RuntimeError as error:
        raise RuntimeError(
            "Fail closed: TensorFlow GPU visibility was initialized before CPU preflight."
        ) from error
    if tf.config.list_logical_devices("GPU"):
        raise RuntimeError("Fail closed: candidate fit must not expose a TensorFlow GPU.")
    try:
        tf.config.experimental.enable_op_determinism()
    except (AttributeError, RuntimeError):
        pass
    return tf


def build_v1_logistic_model(tf, seed: int = 47):
    """Construct but do not compile, train, save or execute the V1 head."""

    if type(seed) is not int or seed < 0:
        raise ValueError("seed must be a non-negative integer.")
    inputs = tf.keras.Input(shape=(FEATURE_DIMENSION,), name="causal_candidate_features")
    outputs = tf.keras.layers.Dense(
        1,
        activation="sigmoid",
        kernel_initializer=tf.keras.initializers.GlorotUniform(seed=seed),
        kernel_regularizer=tf.keras.regularizers.L2(1e-3),
        name="causal_candidate_logistic",
    )(inputs)
    model = tf.keras.Model(inputs=inputs, outputs=outputs, name="causal_candidate_fit_v1")
    if model.output_shape != (None, 1):
        raise AssertionError("V1 candidate model output shape changed.")
    return model


def verify_saved_model_parity(
    model,
    encoded_rows: Sequence[Sequence[float]],
    model_path: Path,
    tf,
    *,
    tolerance: float = 1e-7,
) -> SerializationParity:
    """Save once and fail closed unless reloaded predictions are identical.

    A separately-approved runner may call this only after it has chosen the
    best dev epoch.  It refuses to overwrite a previous artifact and compares
    inference directly; it neither fits the model nor selects a threshold.
    """

    if not encoded_rows:
        raise ValueError("serialization parity requires at least one feature row.")
    if (
        isinstance(tolerance, bool)
        or not isinstance(tolerance, (int, float))
        or not math.isfinite(float(tolerance))
        or float(tolerance) < 0.0
    ):
        raise ValueError("tolerance must be a finite non-negative number.")
    model_path = Path(model_path).resolve()
    if model_path.suffix != ".keras":
        raise ValueError("serialization parity output must use the .keras suffix.")
    if model_path.exists():
        raise FileExistsError(f"refusing to overwrite saved model: {model_path}")
    matrix: list[tuple[float, ...]] = []
    for row in encoded_rows:
        values = tuple(float(value) for value in row)
        if len(values) != FEATURE_DIMENSION or not all(math.isfinite(value) for value in values):
            raise ValueError("serialization parity features must be finite V1 vectors.")
        matrix.append(values)
    try:
        import numpy as np
    except ImportError as error:
        raise RuntimeError("serialization parity requires NumPy.") from error
    inputs = np.asarray(matrix, dtype=np.float32)
    before = np.asarray(model(inputs, training=False), dtype=np.float64)
    model.save(str(model_path))
    restored = tf.keras.models.load_model(str(model_path), compile=False)
    after = np.asarray(restored(inputs, training=False), dtype=np.float64)
    if before.shape != after.shape:
        raise RuntimeError("saved model prediction shape changed after reload.")
    maximum_error = float(np.max(np.abs(before - after)))
    if maximum_error > float(tolerance):
        raise RuntimeError(
            "saved model prediction mismatch after reload: "
            f"maximum_absolute_error={maximum_error}."
        )
    return SerializationParity(
        model_path=model_path,
        maximum_absolute_error=maximum_error,
    )


def _validate_metric_inputs(
    targets: Sequence[int],
    probabilities: Sequence[float],
    weights: Sequence[float],
) -> None:
    if not targets or not (len(targets) == len(probabilities) == len(weights)):
        raise ValueError("metrics require equally-sized non-empty vectors.")
    for target in targets:
        if type(target) is not int or target not in (0, 1):
            raise ValueError("metric targets must be binary integers.")
    for probability in probabilities:
        if not math.isfinite(float(probability)) or not 0.0 <= float(probability) <= 1.0:
            raise ValueError("metric probabilities must be finite values in [0, 1].")
    for weight in weights:
        if not math.isfinite(float(weight)) or float(weight) <= 0.0:
            raise ValueError("metric weights must be finite and positive.")


def _require_complete_family_target_cells(rows: Sequence[CandidateFitRow]) -> None:
    expected = {(family, target) for family in FAMILIES for target in (0, 1)}
    observed = {(row.family, row.target) for row in rows}
    if observed != expected:
        missing = sorted(expected - observed)
        extra = sorted(observed - expected)
        raise ValueError(
            f"all six family/target cells are required; missing={missing}, extra={extra}."
        )
