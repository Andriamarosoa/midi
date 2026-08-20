"""Fixed H27 P0/P1/P2 executor over the sealed 124-record population."""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
from typing import Any, Callable, Mapping

from .harmonic_censoring_h27_contract import H27DormantPlan, canonical_h27_record_identities
from .harmonic_censoring_h27_engine import (
    FORBIDDEN_DESCRIPTOR_FIELDS, H27EngineResult, run_h27_engine,
)
from .harmonic_censoring_h27_recomputer import (
    H27RecomputedResult, compare_h27_engine_and_recomputer,
    run_h27_independent_recomputer,
)
from .harmonic_censoring_h27_scientific_authority import (
    operational_h27_engine_boundary, require_operational_h27_binding,
    require_operational_h27_capability,
)
from .harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, H27SealedRecordBinding,
)


TEST_IDS = tuple(
    f"H27-T-{phase}-{index:03d}"
    for phase in ("P0", "P1", "P2") for index in range(1, 10)
)
KILL_STATUS = {
    "P0": "H27_PREREGISTRATION_OR_IDENTIFIABILITY_INVALID",
    "P1": "H27_CERTIFICATE_HYPOTHESIS_NOT_DEMONSTRATED",
    "P2": "H27_ROBUSTNESS_NOT_DEMONSTRATED",
}
PASS_STATUS = "H27_REVIEW5_SCIENCE_27_OF_27_PASS_STOP_BEFORE_POST_SCIENCE"
INVERSE_IDS = (
    "ZERO-INV-01", "ZERO-INV-02", "ZERO-INV-03", "ZERO-INV-04", "POS-INV",
    "NEG-INV", "COLLISION-INV", "CAUSAL-INV", "LEAKAGE-INV", "RECOMPUTE-INV",
)


@dataclass(frozen=True)
class H27TestResult:
    test_id: str
    phase: str
    status: str
    record_count: int
    record_identities: tuple[str, ...]
    detail: str


@dataclass(frozen=True)
class H27ScientificSequenceResult:
    terminal_status: str
    tests_passed: int
    tests_failed: int
    tests_not_run: int
    record_evaluations: int
    unique_records_evaluated: int
    outcome_counts: Mapping[str, int]
    test_results: tuple[H27TestResult, ...]
    record_summaries: tuple[Mapping[str, object], ...]
    locked_test_used: bool = False
    training_used: bool = False


def _fixture_expected(plan: H27DormantPlan) -> dict[str, str]:
    return {str(item["id"]): str(item["expected"]) for item in plan.fixtures}


def _fixture_id(identity: str) -> str:
    parts = identity.split("/")
    return parts[1] if parts[0] == "baseline" else parts[2]


def _summary(result: H27EngineResult) -> Mapping[str, object]:
    return {
        "record_identity": result.record_identity,
        "outcome": result.outcome,
        "certificate_kind": result.certificate_kind,
        "certificate_complete": result.certificate_complete,
        "role_classifications": dict(result.role_classifications),
        "mask_counts": dict(result.mask_counts),
        "early_resolution_reason": result.early_resolution_reason,
        "maximum_sample_read": result.maximum_sample_read,
        "validated_payload_sha256": dict(result.validated_payload_sha256),
    }


def _portable_number(value: object) -> object:
    if type(value) is float and math.isinf(value):
        return "Infinity"
    if isinstance(value, Mapping):
        return {str(key): _portable_number(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_portable_number(item) for item in value]
    return value


def h27_engine_result_as_portable_dict(result: H27EngineResult) -> dict[str, object]:
    return {key: _portable_number(value) for key, value in vars(result).items()}


def _restore_number(value: object) -> object:
    if value == "Infinity":
        return math.inf
    if type(value) is list:
        return tuple(_restore_number(item) for item in value)
    if type(value) is dict:
        return {str(key): _restore_number(item) for key, item in value.items()}
    return value


def _engine_result_from_portable_dict(value: object) -> H27EngineResult:
    if type(value) is not dict:
        raise ValueError("H27 secondary result must be an object")
    restored = {str(key): _restore_number(item) for key, item in value.items()}
    return H27EngineResult(**restored)


def _secondary_runtime_records(
    plan: H27DormantPlan, repository_root: Path, expected_identities: tuple[str, ...],
) -> tuple[H27EngineResult, ...]:
    """Run the sealed secondary interpreter only when P2-007 is reached."""

    runtime_grid = plan.test_manifest["perturbation_grids"]["P2_RUNTIME_V1"]
    secondary = runtime_grid["axes"]["runtime"][1]["identity"]
    executable = Path(str(secondary["resolved_executable"]))
    if (executable.is_symlink() or not executable.is_file()
            or executable.resolve(strict=True) != executable
            or executable.stat().st_size != secondary["executable_size_bytes"]
            or hashlib.sha256(executable.read_bytes()).hexdigest() != secondary["executable_sha256"]):
        raise RuntimeError("H27 secondary executable identity mismatch")
    environment = os.environ.copy()
    for key, value in runtime_grid["process_environment_exact"].items():
        environment[str(key)] = str(value)
    claim_path = Path("/Users/amcarene/h27-admin-recovery-v2/science/review5-v1/claim.json")
    claim_raw = claim_path.read_bytes()
    environment["H27_REVIEW5_INTERNAL_SECONDARY"] = "1"
    environment["H27_REVIEW5_INTERNAL_CLAIM_SHA256"] = hashlib.sha256(claim_raw).hexdigest()
    activation_path = Path(environment["H27_REVIEW5_ACTIVATION_PATH"])
    environment["H27_REVIEW5_INTERNAL_ACTIVATION_SHA256"] = hashlib.sha256(
        activation_path.read_bytes()).hexdigest()
    helper = Path(repository_root) / "scripts/h27_review5_scientific_secondary.py"
    completed = subprocess.run(
        (str(executable), str(helper)), cwd=repository_root, env=environment,
        capture_output=True, timeout=900,
    )
    if completed.returncode != 0 or completed.stderr:
        raise RuntimeError("H27 secondary runtime execution failed")
    try:
        payload = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise RuntimeError("H27 secondary runtime output invalid") from exc
    if type(payload) is not dict or tuple(payload) != ("record_count", "results"):
        raise RuntimeError("H27 secondary runtime schema/order invalid")
    rows = tuple(_engine_result_from_portable_dict(item) for item in payload["results"])
    if payload["record_count"] != 4 or tuple(item.record_identity for item in rows) != expected_identities:
        raise RuntimeError("H27 secondary runtime identity/order mismatch")
    return rows


def _require_primary_runtime_identity(np: Any, expected: Mapping[str, object]) -> None:
    observed = {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "numpy_version": np.__version__,
    }
    for key, value in observed.items():
        if expected.get(key) != value:
            raise RuntimeError(f"H27 primary runtime mismatch: {key}")
    package = Path(np.__file__).resolve(strict=True).parent
    matches = {"numpy": [], "blas": []}
    for candidate in package.parent.rglob("*"):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        size = candidate.stat().st_size
        if size not in (expected["numpy_multiarray_size_bytes"], expected["blas_library_size_bytes"]):
            continue
        digest = hashlib.sha256(candidate.read_bytes()).hexdigest()
        if size == expected["numpy_multiarray_size_bytes"] and digest == expected["numpy_multiarray_sha256"]:
            matches["numpy"].append(candidate)
        if size == expected["blas_library_size_bytes"] and digest == expected["blas_library_sha256"]:
            matches["blas"].append(candidate)
    if len(matches["numpy"]) != 1 or len(matches["blas"]) != 1 or "openblas" not in matches["blas"][0].name.lower():
        raise RuntimeError("H27 primary NumPy/OpenBLAS identity mismatch")


def _same_semantics(left: H27EngineResult, right: H27EngineResult) -> bool:
    fields = (
        "role_classifications", "mask_counts", "outcome", "certificate_kind",
        "certificate_complete", "exclusive_partial_membership",
        "early_resolution_reason",
    )
    if any(getattr(left, name) != getattr(right, name) for name in fields):
        return False

    def close(a: object, b: object) -> bool:
        if a is None or b is None:
            return a is b
        if type(a) in (int, float) and type(b) in (int, float):
            x, y = float(a), float(b)
            if math.isinf(x) or math.isinf(y):
                return x == y == math.inf
            return math.isfinite(x) and math.isfinite(y) and abs(x-y) <= 1e-12 + 1e-10*abs(x)
        if isinstance(a, (tuple, list)) and isinstance(b, (tuple, list)) and len(a) == len(b):
            return all(close(x, y) for x, y in zip(a, b))
        return a == b

    numeric = (
        "exclusive_energy_ratios", "onset_rise", "residual_improvement",
        "persistence", "bounded_claim_lower_bounds", "negative_margins",
        "pitch_dilution_curve",
    )
    return all(close(getattr(left, name), getattr(right, name)) for name in numeric)


def _strict_result_contract(row: H27EngineResult, binding: H27SealedRecordBinding) -> bool:
    roles = ("current_short", "previous_short", "current_long", "previous_long")
    if tuple(row.role_classifications) != roles or tuple(row.mask_counts) != roles:
        return False
    if row.maximum_sample_read > binding.proposal_hop_end:
        return False
    if row.outcome == "BIRTH_SUPPORTED":
        ratios = row.exclusive_energy_ratios or ()
        return (row.certificate_kind == "POSITIVE" and row.certificate_complete is True
                and row.early_resolution_reason == "complete_positive_certificate"
                and sum(value >= 0.02 for value in ratios) >= 2
                and row.onset_rise is not None and row.onset_rise >= 0.05
                and row.residual_improvement is not None and row.residual_improvement >= 0.1)
    if row.outcome == "NO_BIRTH":
        ratios, bounds, margins = (row.exclusive_energy_ratios or (),
                                    row.bounded_claim_lower_bounds or (), row.negative_margins or ())
        bounded = tuple(i for i, value in enumerate(bounds) if math.isfinite(value) and value >= 0.02)
        return (row.certificate_kind == "NEGATIVE" and row.certificate_complete is True
                and row.early_resolution_reason == "complete_bounded_negative_certificate"
                and len(ratios) == len(bounds) == len(margins) and len(bounded) >= 2
                and all(ratios[i] <= 0.002 and margins[i] >= 10.0 for i in bounded)
                and row.onset_rise is not None and row.onset_rise <= 0.005
                and row.residual_improvement is not None and row.residual_improvement <= 0.001)
    if row.outcome == "ALREADY_ACTIVE_HISTORY":
        return (row.certificate_kind == "ACTIVE_HISTORY" and row.certificate_complete is True
                and row.early_resolution_reason == "candidate_active_before_proposal")
    if row.certificate_kind == "EQUIVALENCE":
        return (row.outcome == "AMBIGUOUS" and row.certificate_complete is True
                and row.early_resolution_reason == "observation_equivalent_latent_causes")
    return (row.outcome == "AMBIGUOUS" and row.certificate_kind == "NONE"
            and row.certificate_complete is False)


def _inverse_checks(
    plan: H27DormantPlan, rows: Mapping[str, H27EngineResult],
    bindings: Mapping[str, H27SealedRecordBinding],
) -> Mapping[str, bool]:
    """Execute every preregistered inverse as a corruption rejection."""

    positive = rows["baseline/H27-F-P02"]
    negative = rows["baseline/H27-F-N01"]
    collision = rows["baseline/H27-F-A01"]
    causal = rows["baseline/H27-F-P04"]
    p01 = rows["baseline/H27-F-P01"]
    quasi_previous = rows["baseline/H27-F-A05"]
    quasi_current = rows["baseline/H27-F-A06"]
    exact_current = rows["baseline/H27-F-A07"]
    masked = rows["baseline/H27-F-A04"]

    def rejected(row: H27EngineResult) -> bool:
        return not _strict_result_contract(row, bindings[row.record_identity])

    recomputed = H27RecomputedResult(**vars(p01))
    recompute_corruptions = (
        replace(recomputed, validated_payload_sha256={}),
        replace(recomputed, record_identity="oracle/forbidden"),
        replace(recomputed, maximum_sample_read=bindings[p01.record_identity].proposal_hop_end + 1),
        replace(recomputed, outcome="NO_BIRTH"),
        replace(recomputed, pitch_dilution_curve=((96, 0.0),)),
    )
    detected = []
    for corruption in recompute_corruptions:
        try:
            compare_h27_engine_and_recomputer(p01, corruption)
        except RuntimeError:
            detected.append(True)
        else:
            detected.append(False)
    forbidden = set(FORBIDDEN_DESCRIPTOR_FIELDS)
    binding_fields = set(type(bindings[p01.record_identity]).__slots__)
    return {
        "ZERO-INV-01": (p01.role_classifications["previous_short"] == "VALID_EXACT_ZERO_PREVIOUS_SHORT"
                        and quasi_previous.role_classifications["previous_short"] != "VALID_EXACT_ZERO_PREVIOUS_SHORT"),
        "ZERO-INV-02": masked.role_classifications["previous_short"] == "INVALID_SUPPORT",
        "ZERO-INV-03": (quasi_current.outcome == "AMBIGUOUS"
                        and quasi_current.early_resolution_reason == "nonzero_not_above_floor"),
        "ZERO-INV-04": (quasi_previous.early_resolution_reason == "nonzero_not_above_floor"
                        and exact_current.early_resolution_reason == "invalid_current_exact_zero"),
        "POS-INV": rejected(replace(positive, onset_rise=0.0)),
        "NEG-INV": rejected(replace(negative, bounded_claim_lower_bounds=None)),
        "COLLISION-INV": rejected(replace(collision, early_resolution_reason="broken_equivalence_certificate")),
        "CAUSAL-INV": rejected(replace(causal, maximum_sample_read=bindings[causal.record_identity].proposal_hop_end + 1)),
        "LEAKAGE-INV": not (forbidden & binding_fields),
        "RECOMPUTE-INV": len(detected) == 5 and all(detected),
    }


def require_inverse_checker_coverage(plan: H27DormantPlan) -> None:
    declared = tuple(plan.test_manifest["inverse_contracts"])
    if set(declared) != set(INVERSE_IDS) or len(declared) != len(INVERSE_IDS):
        raise ValueError("H27 inverse checker coverage mismatch")


def execute_h27_scientific_sequence(
    *, np: Any, capability: H27ScientificCapability, repository_root: Path,
    plan: H27DormantPlan, bindings: tuple[H27SealedRecordBinding, ...],
    on_test_completed: Callable[[H27TestResult], None] | None = None,
) -> H27ScientificSequenceResult:
    """Run exactly P0 then P1 then P2; return immediately on first failure."""

    require_operational_h27_capability(capability)
    if type(plan) is not H27DormantPlan:
        raise TypeError("exact H27DormantPlan required")
    if type(bindings) is not tuple or len(bindings) != 124:
        raise ValueError("H27 sealed binding cardinality mismatch")
    for binding in bindings:
        require_operational_h27_binding(binding)
    identities = tuple(item.record_identity for item in bindings)
    if identities != canonical_h27_record_identities(plan) or len(set(identities)) != 124:
        raise ValueError("H27 sealed binding identity/order mismatch")
    tests = plan.tests
    if tuple(str(item["id"]) for item in tests) != TEST_IDS:
        raise ValueError("H27 test order mismatch")
    require_inverse_checker_coverage(plan)

    by_identity = dict(zip(identities, bindings))
    expected = _fixture_expected(plan)
    cache: dict[str, H27EngineResult] = {}
    summaries: list[Mapping[str, object]] = []
    evaluations = 0

    def evaluate(identity: str) -> H27EngineResult:
        nonlocal evaluations
        if identity not in cache:
            binding = by_identity[identity]
            engine = run_h27_engine(np, capability, repository_root, binding)
            recomputed = run_h27_independent_recomputer(np, capability, repository_root, binding)
            compare_h27_engine_and_recomputer(engine, recomputed)
            cache[identity] = engine
            summaries.append(_summary(engine))
            evaluations += 2
        return cache[identity]

    def baseline(fixture_id: str) -> H27EngineResult:
        return evaluate(f"baseline/{fixture_id}")

    def grid_records(test: Mapping[str, object]) -> tuple[H27EngineResult, ...]:
        grid = str(test["perturbation_grid_id"])
        prefix = f"p2/{grid}/"
        selected = tuple(identity for identity in identities if identity.startswith(prefix))
        if str(test["id"]) == "H27-T-P2-007":
            runtime_grid = plan.test_manifest["perturbation_grids"]["P2_RUNTIME_V1"]
            _require_primary_runtime_identity(np, runtime_grid["axes"]["runtime"][0]["identity"])
            primary = tuple(identity for identity in selected if identity.endswith("runtime=primary"))
            secondary = tuple(identity for identity in selected if identity.endswith("runtime=secondary"))
            for identity in primary:
                evaluate(identity)
            secondary_rows = _secondary_runtime_records(plan, repository_root, secondary)
            nonlocal evaluations
            for row in secondary_rows:
                if row.record_identity in cache:
                    raise RuntimeError("H27 secondary result duplicate")
                cache[row.record_identity] = row
                summaries.append(_summary(row))
                evaluations += 2
        return tuple(cache[identity] if identity in cache else evaluate(identity) for identity in selected)

    passed: list[H27TestResult] = []
    outcome_counts: dict[str, int] = {}
    inverse_results: Mapping[str, bool] | None = None

    def check(test: Mapping[str, object]) -> tuple[bool, tuple[str, ...], str]:
        nonlocal inverse_results
        test_id, phase = str(test["id"]), str(test["phase"])
        fixture_ids = tuple(str(item) for item in test.get("fixture_ids", ()))
        if phase == "P0":
            rows = tuple(baseline(item) for item in fixture_ids)
            if test_id == "H27-T-P0-001":
                ok = len(plan.fixture_ids) == 17 and len(plan.tests) == 27 and len(identities) == 124
            elif test_id == "H27-T-P0-002":
                p01 = baseline("H27-F-P01")
                ok = (tuple(plan.test_manifest["r_zero_obligations"]) == tuple(f"R-ZERO-{i:03d}" for i in range(1,12))
                      and p01.role_classifications["previous_short"] == "VALID_EXACT_ZERO_PREVIOUS_SHORT"
                      and p01.role_classifications["previous_long"] == "VALID_EXACT_ZERO_PREVIOUS_LONG"
                      and all(row.outcome == "AMBIGUOUS" for row in rows[1:]))
            elif test_id == "H27-T-P0-003":
                ok = tuple(row.outcome for row in rows) == (
                    "BIRTH_SUPPORTED", "NO_BIRTH", "ALREADY_ACTIVE_HISTORY", "AMBIGUOUS")
            elif test_id == "H27-T-P0-004":
                ok = all(row.outcome == "BIRTH_SUPPORTED" and row.certificate_kind == "POSITIVE"
                         and row.certificate_complete for row in rows)
            elif test_id == "H27-T-P0-005":
                ok = (all(row.outcome == "NO_BIRTH" and row.certificate_kind == "NEGATIVE"
                          and row.certificate_complete for row in rows[:4])
                      and rows[4].outcome == "AMBIGUOUS")
            elif test_id == "H27-T-P0-006":
                ok = all(row.outcome == "AMBIGUOUS" and row.certificate_kind == "EQUIVALENCE"
                         and row.early_resolution_reason == "observation_equivalent_latent_causes" for row in rows)
            elif test_id == "H27-T-P0-007":
                ok = all(row.outcome == "AMBIGUOUS" for row in rows)
            elif test_id == "H27-T-P0-008":
                ok = all(row.maximum_sample_read <= by_identity[row.record_identity].proposal_hop_end for row in rows)
            else:
                ok = len(rows) == 4
            declared_for_test = tuple(str(item) for item in test.get("inverse_ids", ()))
            if declared_for_test:
                if inverse_results is None:
                    required = tuple(
                        f"baseline/{fixture}" for fixture in
                        ("H27-F-P01", "H27-F-P02", "H27-F-N01", "H27-F-P04", "H27-F-A01",
                         "H27-F-A04", "H27-F-A05", "H27-F-A06", "H27-F-A07")
                    )
                    inverse_results = _inverse_checks(
                        plan, {identity: evaluate(identity) for identity in required}, by_identity,
                    )
                ok = ok and all(inverse_results[item] for item in declared_for_test)
            return ok, tuple(row.record_identity for row in rows), str(test.get("pass_rule", ""))

        if phase == "P1":
            rows = tuple(baseline(item) for item in fixture_ids)
            strict = all(_strict_result_contract(row, by_identity[row.record_identity]) for row in rows)
            if test_id == "H27-T-P1-009":
                counts = {value: sum(row.outcome == value for row in rows) for value in (
                    "BIRTH_SUPPORTED", "NO_BIRTH", "ALREADY_ACTIVE_HISTORY", "AMBIGUOUS")}
                ok = strict and counts == {"BIRTH_SUPPORTED":4,"NO_BIRTH":4,"ALREADY_ACTIVE_HISTORY":2,"AMBIGUOUS":7}
            else:
                ok = strict and all(row.outcome == expected[item] for item, row in zip(fixture_ids, rows))
            return ok, tuple(row.record_identity for row in rows), str(test.get("pass_rule", ""))

        if test_id == "H27-T-P2-009":
            rows = tuple(evaluate(identity) for identity in identities[17:])
            ok = len(rows) == 107 and len({row.record_identity for row in rows}) == 107
            return ok, tuple(row.record_identity for row in rows), str(test.get("pass_rule", ""))
        rows = grid_records(test)
        expected_count = int(test["expected_record_count"])
        if test_id == "H27-T-P2-004":
            ok = len(rows) == expected_count and all(row.outcome == "AMBIGUOUS" for row in rows)
        else:
            ok = len(rows) == expected_count and all(
                row.outcome == expected[_fixture_id(row.record_identity)] for row in rows
            )
        if ok and test_id in {"H27-T-P2-001", "H27-T-P2-002", "H27-T-P2-006", "H27-T-P2-007"}:
            grouped: dict[str, list[H27EngineResult]] = {}
            for row in rows:
                grouped.setdefault(_fixture_id(row.record_identity), []).append(row)
            ok = all(all(_same_semantics(items[0], item) for item in items[1:]) for items in grouped.values())
        return ok, tuple(row.record_identity for row in rows), str(test.get("objective", ""))

    with operational_h27_engine_boundary(capability):
        for test in tests:
            phase = str(test["phase"])
            ok, used, detail = check(test)
            if not ok:
                failed = H27TestResult(str(test["id"]), phase, "FAIL", len(used), used, detail)
                if on_test_completed is not None:
                    on_test_completed(failed)
                all_results = tuple(passed + [failed])
                for summary in summaries:
                    outcome = str(summary["outcome"])
                    outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
                return H27ScientificSequenceResult(
                    KILL_STATUS[phase], len(passed), 1, 27-len(all_results), evaluations,
                    len(cache), dict(outcome_counts), all_results, tuple(summaries),
                )
            completed = H27TestResult(str(test["id"]), phase, "PASS", len(used), used, detail)
            if on_test_completed is not None:
                on_test_completed(completed)
            passed.append(completed)

    for summary in summaries:
        outcome = str(summary["outcome"])
        outcome_counts[outcome] = outcome_counts.get(outcome, 0) + 1
    return H27ScientificSequenceResult(
        PASS_STATUS, 27, 0, 0, evaluations, len(cache), dict(outcome_counts),
        tuple(passed), tuple(summaries),
    )


def scientific_sequence_as_dict(result: H27ScientificSequenceResult) -> dict[str, object]:
    value = asdict(result)
    value["outcome_counts"] = dict(result.outcome_counts)
    return value


__all__ = [
    "H27ScientificSequenceResult", "H27TestResult", "KILL_STATUS", "PASS_STATUS",
    "TEST_IDS", "execute_h27_scientific_sequence", "h27_engine_result_as_portable_dict",
    "require_inverse_checker_coverage", "scientific_sequence_as_dict",
]
