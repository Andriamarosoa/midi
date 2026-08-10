"""Pure synthetic-conformant H7 ROC-AUC and leakage-group bootstrap."""
from __future__ import annotations

from dataclasses import dataclass
import json
import math
from typing import Sequence

import numpy as np

from .provisional_resolution_age1 import (
    AGE1_OBSERVATION_AVAILABLE,
    TARGET_MATCHABLE,
    Age1ScientificRow,
    count_age1_attrition,
)


BOOTSTRAP_REPLICATE_COUNT = 10_000
BOOTSTRAP_SEED = 721_629_268
MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT = 9_500
MINIMUM_VALID_AGE1_OBSERVATION_COUNT = 200
GROUP_RESAMPLING_INCONCLUSIVE = "group_resampling_inconclusive"
AGE1_SIGNAL_INSUFFICIENT = "age1_signal_insufficient_valid_observations"
AGE1_SIGNAL_SINGLE_CLASS = "age1_signal_single_class"
AGE1_SIGNAL_EXECUTION_INVALID = "age1_signal_execution_invalid"
AGE1_SIGNAL_DEMONSTRATED = "age1_persistence_signal_demonstrated"
AGE1_SIGNAL_NOT_DEMONSTRATED = "age1_persistence_signal_not_demonstrated"
AUC_UNAVAILABLE_SINGLE_CLASS = "auc_unavailable_single_class"
D1_ORIENTATION = "higher_D1_predicts_true_noteon_persistence"


class UndefinedRocAucError(ValueError):
    """Raised when a binary ROC-AUC has no positive or no negative class."""


def _metadata(value: object, name: str) -> str:
    if (
        not isinstance(value, str)
        or not value.strip()
        or value != value.strip()
    ):
        raise ValueError(f"{name} must be a non-empty string.")
    return value


@dataclass(frozen=True)
class GroupedAge1EvaluationRow:
    """Reporting/resampling metadata wrapped around one closed scientific row."""

    recording_key: str
    corpus_category: str
    leakage_group_key: str
    scientific_row: Age1ScientificRow

    def __post_init__(self) -> None:
        object.__setattr__(self, "recording_key", _metadata(self.recording_key, "recording_key"))
        object.__setattr__(self, "corpus_category", _metadata(self.corpus_category, "corpus_category"))
        object.__setattr__(self, "leakage_group_key", _metadata(self.leakage_group_key, "leakage_group_key"))
        if not isinstance(self.scientific_row, Age1ScientificRow):
            raise ValueError("scientific_row must be an Age1ScientificRow.")


def binary_roc_auc(targets: Sequence[object], scores: Sequence[object]) -> float:
    """Average-rank AUC: ties receive exactly half credit."""
    if len(targets) != len(scores) or not targets:
        raise ValueError("targets and scores must have the same non-zero length.")
    checked: list[tuple[float, int]] = []
    for target, score in zip(targets, scores):
        if type(target) is not int or target not in (0, 1):
            raise ValueError("ROC-AUC targets must be JSON-native binary integers.")
        numeric = float(score)
        if not math.isfinite(numeric):
            raise ValueError("ROC-AUC scores must be finite.")
        checked.append((numeric, target))
    positives = sum(target for _, target in checked)
    negatives = len(checked) - positives
    if positives == 0 or negatives == 0:
        raise UndefinedRocAucError(AUC_UNAVAILABLE_SINGLE_CLASS)

    ordered = sorted(checked, key=lambda item: item[0])
    positive_rank_sum = 0.0
    index = 0
    while index < len(ordered):
        stop = index + 1
        while stop < len(ordered) and ordered[stop][0] == ordered[index][0]:
            stop += 1
        # Zero-based [index, stop) corresponds to one-based ranks
        # [index + 1, stop], whose exact average is below.
        average_rank = ((index + 1) + stop) / 2.0
        positive_rank_sum += average_rank * sum(
            target for _, target in ordered[index:stop]
        )
        index = stop
    auc = (
        positive_rank_sum - positives * (positives + 1) / 2.0
    ) / (positives * negatives)
    if not math.isfinite(auc) or not 0.0 <= auc <= 1.0:
        raise RuntimeError("Fail closed: ROC-AUC calculation escaped [0, 1].")
    return float(auc)


def _eligible(rows: Sequence[GroupedAge1EvaluationRow]) -> tuple[GroupedAge1EvaluationRow, ...]:
    checked = tuple(rows)
    if not all(isinstance(row, GroupedAge1EvaluationRow) for row in checked):
        raise ValueError("rows must contain only GroupedAge1EvaluationRow values.")
    result = []
    for row in checked:
        scientific = row.scientific_row
        if scientific.age1_status != AGE1_OBSERVATION_AVAILABLE:
            continue
        if scientific.target_status != TARGET_MATCHABLE:
            continue
        if type(scientific.true_noteon) is not int or scientific.true_noteon not in (0, 1):
            raise ValueError("Eligible H7 true_noteon must be exactly 0 or 1.")
        if scientific.S1 is None or not math.isfinite(float(scientific.S1)):
            raise ValueError("Eligible H7 S1 must be finite.")
        result.append(row)
    return tuple(result)


def _row_order(row: GroupedAge1EvaluationRow) -> tuple[object, ...]:
    scientific = row.scientific_row
    return (
        row.leakage_group_key,
        row.recording_key,
        scientific.frame_index,
        scientific.pitch,
        scientific.true_noteon,
        scientific.S1,
        scientific.S0,
        scientific.D1,
    )


def canonical_group_universe(values: Sequence[str]) -> tuple[str, ...]:
    """Validate and canonicalize the sealed cohort leakage-group universe."""
    checked = tuple(_metadata(value, "cohort_group_id") for value in values)
    if not checked:
        raise ValueError("cohort_group_universe must contain at least one group.")
    if len(set(checked)) != len(checked):
        raise ValueError("cohort_group_universe must not contain duplicates.")
    return tuple(sorted(checked))


def _require_rows_in_group_universe(
    rows: Sequence[GroupedAge1EvaluationRow],
    cohort_group_universe: Sequence[str],
) -> tuple[tuple[GroupedAge1EvaluationRow, ...], tuple[str, ...]]:
    checked = tuple(rows)
    if not all(isinstance(row, GroupedAge1EvaluationRow) for row in checked):
        raise ValueError("rows must contain only GroupedAge1EvaluationRow values.")
    universe = canonical_group_universe(cohort_group_universe)
    outside = sorted({row.leakage_group_key for row in checked}.difference(universe))
    if outside:
        raise ValueError("scientific row leakage_group_key is outside cohort_group_universe.")
    return checked, universe


def expand_group_sample(
    rows: Sequence[GroupedAge1EvaluationRow],
    sampled_group_ids: Sequence[str],
    *,
    cohort_group_universe: Sequence[str] | None = None,
) -> tuple[GroupedAge1EvaluationRow, ...]:
    """Expand sampled groups with replacement while preserving multiplicity."""
    grouped: dict[str, list[GroupedAge1EvaluationRow]] = {}
    checked = tuple(rows)
    if not all(isinstance(row, GroupedAge1EvaluationRow) for row in checked):
        raise ValueError("rows must contain only GroupedAge1EvaluationRow values.")
    universe = (
        canonical_group_universe(cohort_group_universe)
        if cohort_group_universe is not None
        else tuple(sorted({row.leakage_group_key for row in checked}))
    )
    if not universe:
        raise ValueError("At least one evaluation group is required.")
    if any(row.leakage_group_key not in universe for row in checked):
        raise ValueError("scientific row leakage_group_key is outside cohort_group_universe.")
    for row in sorted(checked, key=_row_order):
        grouped.setdefault(row.leakage_group_key, []).append(row)
    expanded = []
    for raw_group in sampled_group_ids:
        group = _metadata(raw_group, "sampled_group_id")
        if group not in universe:
            raise ValueError("sampled_group_id is outside cohort_group_universe.")
        expanded.extend(grouped.get(group, ()))
    return tuple(expanded)


@dataclass(frozen=True)
class GroupBootstrapResult:
    status: str
    requested_replicates: int
    valid_replicates: int
    invalid_replicates: int
    seed: int
    rng: str
    percentile_method: str
    cohort_group_count: int
    lower_95: float | None
    upper_95: float | None


def grouped_roc_auc_bootstrap(
    rows: Sequence[GroupedAge1EvaluationRow],
    *,
    cohort_group_universe: Sequence[str],
) -> GroupBootstrapResult:
    """Sample exactly G leakage groups with replacement for every replicate."""
    checked, group_ids = _require_rows_in_group_universe(rows, cohort_group_universe)
    eligible = _eligible(checked)
    grouped = {
        group: tuple(row for row in eligible if row.leakage_group_key == group)
        for group in group_ids
    }
    rng = np.random.Generator(np.random.PCG64(BOOTSTRAP_SEED))
    auc_values: list[float] = []
    for _ in range(BOOTSTRAP_REPLICATE_COUNT):
        sampled_indexes = rng.integers(0, len(group_ids), size=len(group_ids))
        sampled = tuple(
            row
            for index in sampled_indexes
            for row in grouped[group_ids[int(index)]]
        )
        sampled_targets = [row.scientific_row.true_noteon for row in sampled]
        if len(set(sampled_targets)) != 2:
            continue
        try:
            auc_values.append(binary_roc_auc(
                sampled_targets,
                [row.scientific_row.S1 for row in sampled],
            ))
        except UndefinedRocAucError:
            continue
    valid = len(auc_values)
    invalid = BOOTSTRAP_REPLICATE_COUNT - valid
    if valid < MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT:
        return GroupBootstrapResult(
            status=GROUP_RESAMPLING_INCONCLUSIVE,
            requested_replicates=BOOTSTRAP_REPLICATE_COUNT,
            valid_replicates=valid,
            invalid_replicates=invalid,
            seed=BOOTSTRAP_SEED,
            rng="numpy.random.Generator(numpy.random.PCG64)",
            percentile_method="numpy.percentile(method=linear)",
            cohort_group_count=len(group_ids),
            lower_95=None,
            upper_95=None,
        )
    lower, upper = np.percentile(
        np.asarray(auc_values, dtype=np.float64),
        [2.5, 97.5],
        method="linear",
    )
    if not math.isfinite(float(lower)) or not math.isfinite(float(upper)):
        raise RuntimeError("Fail closed: bootstrap percentile is non-finite.")
    return GroupBootstrapResult(
        status="complete",
        requested_replicates=BOOTSTRAP_REPLICATE_COUNT,
        valid_replicates=valid,
        invalid_replicates=invalid,
        seed=BOOTSTRAP_SEED,
        rng="numpy.random.Generator(numpy.random.PCG64)",
        percentile_method="numpy.percentile(method=linear)",
        cohort_group_count=len(group_ids),
        lower_95=float(lower),
        upper_95=float(upper),
    )


def primary_h7_verdict(global_auc: float, ci_lower: float) -> str:
    auc = float(global_auc)
    lower = float(ci_lower)
    if not all(math.isfinite(value) and 0.0 <= value <= 1.0 for value in (auc, lower)):
        raise ValueError("Primary H7 metric values must be finite in [0, 1].")
    if auc >= 0.60 and lower > 0.50:
        return AGE1_SIGNAL_DEMONSTRATED
    return AGE1_SIGNAL_NOT_DEMONSTRATED


@dataclass(frozen=True)
class CorpusAucResult:
    corpus_category: str
    status: str
    eligible_rows: int
    auc: float | None


@dataclass(frozen=True)
class H7SyntheticMetricReport:
    status: str
    eligible_rows: int
    global_s1_auc: float | None
    descriptive_s0_auc: float | None
    descriptive_d1_auc: float | None
    d1_orientation: str
    bootstrap: GroupBootstrapResult | None
    per_corpus: tuple[CorpusAucResult, ...]
    attrition: dict[str, int]

    def canonical_json_bytes(self) -> bytes:
        payload = {
            "attrition": self.attrition,
            "bootstrap": None if self.bootstrap is None else self.bootstrap.__dict__,
            "d1_orientation": self.d1_orientation,
            "descriptive_d1_auc": self.descriptive_d1_auc,
            "descriptive_s0_auc": self.descriptive_s0_auc,
            "eligible_rows": self.eligible_rows,
            "global_s1_auc": self.global_s1_auc,
            "per_corpus": [item.__dict__ for item in self.per_corpus],
            "status": self.status,
        }
        return (json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _attrition_payload(
    rows: Sequence[GroupedAge1EvaluationRow],
    malformed_or_nonfinite_signal_cases: int,
) -> dict[str, int]:
    counts = count_age1_attrition(
        [row.scientific_row for row in rows],
        malformed_or_nonfinite_signal_cases=malformed_or_nonfinite_signal_cases,
    )
    return dict(counts.__dict__)


def evaluate_h7_synthetic_metrics(
    rows: Sequence[GroupedAge1EvaluationRow],
    *,
    cohort_group_universe: Sequence[str],
    malformed_or_nonfinite_signal_cases: int = 0,
) -> H7SyntheticMetricReport:
    """Apply the frozen H7/H8 metric gates to already-supplied synthetic rows."""
    checked, group_universe = _require_rows_in_group_universe(
        rows, cohort_group_universe
    )
    if not checked or not all(isinstance(row, GroupedAge1EvaluationRow) for row in checked):
        raise ValueError("rows must be a non-empty grouped H7 sequence.")
    eligible = _eligible(checked)
    attrition = _attrition_payload(checked, malformed_or_nonfinite_signal_cases)
    if malformed_or_nonfinite_signal_cases:
        return H7SyntheticMetricReport(
            status=AGE1_SIGNAL_EXECUTION_INVALID,
            eligible_rows=len(eligible),
            global_s1_auc=None,
            descriptive_s0_auc=None,
            descriptive_d1_auc=None,
            d1_orientation=D1_ORIENTATION,
            bootstrap=None,
            per_corpus=(),
            attrition=attrition,
        )
    if len(eligible) < MINIMUM_VALID_AGE1_OBSERVATION_COUNT:
        return H7SyntheticMetricReport(
            status=AGE1_SIGNAL_INSUFFICIENT,
            eligible_rows=len(eligible),
            global_s1_auc=None,
            descriptive_s0_auc=None,
            descriptive_d1_auc=None,
            d1_orientation=D1_ORIENTATION,
            bootstrap=None,
            per_corpus=(),
            attrition=attrition,
        )
    targets = [row.scientific_row.true_noteon for row in eligible]
    if len(set(targets)) != 2:
        return H7SyntheticMetricReport(
            status=AGE1_SIGNAL_SINGLE_CLASS,
            eligible_rows=len(eligible),
            global_s1_auc=None,
            descriptive_s0_auc=None,
            descriptive_d1_auc=None,
            d1_orientation=D1_ORIENTATION,
            bootstrap=None,
            per_corpus=(),
            attrition=attrition,
        )
    global_auc = binary_roc_auc(targets, [row.scientific_row.S1 for row in eligible])
    s0_auc = binary_roc_auc(targets, [row.scientific_row.S0 for row in eligible])
    d1_auc = binary_roc_auc(targets, [row.scientific_row.D1 for row in eligible])
    bootstrap = grouped_roc_auc_bootstrap(
        eligible, cohort_group_universe=group_universe
    )
    corpus_results = []
    for corpus in sorted({row.corpus_category for row in eligible}):
        corpus_rows = tuple(row for row in eligible if row.corpus_category == corpus)
        corpus_targets = [row.scientific_row.true_noteon for row in corpus_rows]
        if len(set(corpus_targets)) != 2:
            corpus_results.append(CorpusAucResult(
                corpus_category=corpus,
                status=AUC_UNAVAILABLE_SINGLE_CLASS,
                eligible_rows=len(corpus_rows),
                auc=None,
            ))
        else:
            corpus_results.append(CorpusAucResult(
                corpus_category=corpus,
                status="complete",
                eligible_rows=len(corpus_rows),
                auc=binary_roc_auc(
                    corpus_targets,
                    [row.scientific_row.S1 for row in corpus_rows],
                ),
            ))
    if bootstrap.status == GROUP_RESAMPLING_INCONCLUSIVE:
        status = GROUP_RESAMPLING_INCONCLUSIVE
    else:
        if bootstrap.lower_95 is None:
            raise AssertionError("Complete bootstrap must provide a lower bound.")
        status = primary_h7_verdict(global_auc, bootstrap.lower_95)
    return H7SyntheticMetricReport(
        status=status,
        eligible_rows=len(eligible),
        global_s1_auc=global_auc,
        descriptive_s0_auc=s0_auc,
        descriptive_d1_auc=d1_auc,
        d1_orientation=D1_ORIENTATION,
        bootstrap=bootstrap,
        per_corpus=tuple(corpus_results),
        attrition=attrition,
    )


__all__ = [
    "AGE1_SIGNAL_DEMONSTRATED",
    "AGE1_SIGNAL_EXECUTION_INVALID",
    "AGE1_SIGNAL_INSUFFICIENT",
    "AGE1_SIGNAL_NOT_DEMONSTRATED",
    "AGE1_SIGNAL_SINGLE_CLASS",
    "AUC_UNAVAILABLE_SINGLE_CLASS",
    "BOOTSTRAP_REPLICATE_COUNT",
    "BOOTSTRAP_SEED",
    "D1_ORIENTATION",
    "GROUP_RESAMPLING_INCONCLUSIVE",
    "GroupedAge1EvaluationRow",
    "GroupBootstrapResult",
    "H7SyntheticMetricReport",
    "MINIMUM_VALID_AGE1_OBSERVATION_COUNT",
    "MINIMUM_VALID_BOOTSTRAP_REPLICATE_COUNT",
    "UndefinedRocAucError",
    "binary_roc_auc",
    "canonical_group_universe",
    "evaluate_h7_synthetic_metrics",
    "expand_group_sample",
    "grouped_roc_auc_bootstrap",
    "primary_h7_verdict",
]
