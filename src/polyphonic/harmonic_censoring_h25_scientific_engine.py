"""Dormant H25 scientific engine.

This module contains the reviewed numerical kernels and evidence producers for
H25, but deliberately has no CLI, capability issuer, claim, or import-time
NumPy dependency.  The published H25 population is not opened here.  Future
execution must inject NumPy and already-attested population bytes after a
separate authority transition.
"""
from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Any, Callable, Mapping, Sequence


SCIENTIFIC_CONTRACT_PATH = Path(
    "configs/harmonic_censoring_h25_scientific_hypothesis_execution_contract.json"
)
POPULATION_MANIFEST_PATH = Path("configs/harmonic_censoring_h25_population_manifest.json")
TEST_MANIFEST_PATH = Path("configs/harmonic_censoring_h25_test_manifest.json")
FIXTURE_SPECIFICATIONS_PATH = Path("configs/harmonic_censoring_h25_fixture_specifications.json")

SCIENTIFIC_CONTRACT_SHA256 = "ae837a647792c56c02a7d96a4328f62c1ecac03d0c0a839d59488c420cfff911"
POPULATION_MANIFEST_SHA256 = "33e21457240497322351275c3a82868d0eb06beb6676d6370ea85fae6933ba5f"
TEST_MANIFEST_SHA256 = "58ce653325c785598fccd3cccffa7a77ab4944286df3baeb497bd20548544d29"
FIXTURE_SPECIFICATIONS_SHA256 = "97295c09a0dc362a9337200ede62489e254fd5e548f36e2e170f21abb3b5ef6b"

POPULATION_INDEX_SHA256 = "814d8c368ac67ce65ed20c9e90e634ceffe706db1cc5e642cc3c61ff37ab5f53"
POPULATION_PROVENANCE_SHA256 = "cadc154a84674f6e58cf412d71f73407d0c07388f3bf470fa2368a1b810825db"
POPULATION_RECEIPT_SHA256 = "dbab85910151ce25c186f478797c86604a94e6cf486dda7e0c4b7b8eeb4fddd9"

OPERATOR_NAME = "H25_SUPPORT_NORMALIZED_DILUTION_V1"
SAMPLE_RATE_HZ = 44100
HOP_SAMPLES = 256
SHORT_WINDOW_SAMPLES = 4096
LONG_WINDOW_SAMPLES = 8192
TRANSFORM_GRID = tuple(range(89))
PHYSICAL_PITCHES = tuple(range(40, 77))
LATENT_PITCHES = tuple(range(24, 77))
HARMONIC_RANKS = tuple(range(1, 21))
OBSERVATION_MAX = 128.0
RTOL = 1e-10
ATOL = 1e-12
BASELINE_ABSOLUTE_MIN = 1e-24
BASELINE_RELATIVE_MIN = 1e-12

STATES = ("INACTIVE", "PENDING_NEW", "ACTIVE")
OUTCOMES = ("BIRTH_SUPPORTED", "NO_BIRTH", "ALREADY_ACTIVE_HISTORY", "AMBIGUOUS")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json_bytes(value: object, *, line: bool = False) -> bytes:
    raw = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return raw + (b"\n" if line else b"")


def _reject_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H25 JSON duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H25 JSON forbids {token!r}.")


def _load_bound_json(repository: Path, relative: Path, expected_sha256: str) -> dict[str, object]:
    path = (repository / relative).resolve(strict=True)
    path.relative_to(repository)
    raw = path.read_bytes()
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H25 {relative} must be UTF-8 LF without BOM.")
    if _sha256(raw) != expected_sha256:
        raise ValueError(f"H25 {relative} SHA-256 mismatch.")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise ValueError(f"H25 {relative} must contain one JSON object.")
    return value


@dataclass(frozen=True)
class H25TestSpecification:
    test_id: str
    order: int
    phase: str
    objective: str
    fixture_ids: tuple[str, ...]
    oracle: str
    pass_rule: str
    kill_status: str
    inverse_check: str


@dataclass(frozen=True)
class H25DormantScientificPlan:
    repository_root: Path
    contract: Mapping[str, object]
    population_manifest: Mapping[str, object]
    test_manifest: Mapping[str, object]
    fixture_specifications: Mapping[str, object]
    fixtures: tuple[Mapping[str, object], ...]
    tests: tuple[H25TestSpecification, ...]
    population_bindings: Mapping[str, str]

    @property
    def fixture_ids(self) -> tuple[str, ...]:
        return tuple(str(item["id"]) for item in self.fixtures)

    @property
    def test_ids(self) -> tuple[str, ...]:
        return tuple(item.test_id for item in self.tests)


def load_h25_dormant_scientific_plan(repository_root: Path) -> H25DormantScientificPlan:
    """Load only versioned contracts; never open the materialized population."""

    repository = Path(repository_root).resolve(strict=True)
    contract = _load_bound_json(repository, SCIENTIFIC_CONTRACT_PATH, SCIENTIFIC_CONTRACT_SHA256)
    population = _load_bound_json(repository, POPULATION_MANIFEST_PATH, POPULATION_MANIFEST_SHA256)
    test_manifest = _load_bound_json(repository, TEST_MANIFEST_PATH, TEST_MANIFEST_SHA256)
    specifications = _load_bound_json(repository, FIXTURE_SPECIFICATIONS_PATH, FIXTURE_SPECIFICATIONS_SHA256)
    fixtures_raw = specifications.get("fixtures")
    tests_raw = test_manifest.get("tests")
    if type(fixtures_raw) is not list or type(tests_raw) is not list:
        raise ValueError("H25 fixture/test arrays are missing.")
    fixtures: list[Mapping[str, object]] = []
    for item in fixtures_raw:
        if type(item) is not dict:
            raise ValueError("H25 fixture record is not an object.")
        fixtures.append(MappingProxyType(dict(item)))
    expected_fixture_ids = tuple(population.get("ordered_fixture_ids", ()))
    actual_fixture_ids = tuple(str(item["id"]) for item in fixtures)
    if actual_fixture_ids != expected_fixture_ids or len(actual_fixture_ids) != 36:
        raise ValueError("H25 fixture order/cardinality mismatch.")
    tests: list[H25TestSpecification] = []
    for ordinal, item in enumerate(tests_raw, start=1):
        if type(item) is not dict or set(item) != {
            "id", "order", "phase", "objective", "fixture_ids", "oracle",
            "pass_rule", "kill_status", "inverse_check",
        }:
            raise ValueError("H25 test record schema mismatch.")
        test = H25TestSpecification(
            test_id=str(item["id"]),
            order=int(item["order"]),
            phase=str(item["phase"]),
            objective=str(item["objective"]),
            fixture_ids=tuple(str(value) for value in item["fixture_ids"]),
            oracle=str(item["oracle"]),
            pass_rule=str(item["pass_rule"]),
            kill_status=str(item["kill_status"]),
            inverse_check=str(item["inverse_check"]),
        )
        if test.order != ordinal or test.phase != ("P0", "P1", "P2")[(ordinal - 1) // 9]:
            raise ValueError("H25 test phase/order mismatch.")
        if len(test.fixture_ids) != len(set(test.fixture_ids)) or not set(test.fixture_ids).issubset(actual_fixture_ids):
            raise ValueError("H25 test fixture references are invalid.")
        tests.append(test)
    expected_test_ids = tuple(
        f"H25-T-{phase}-{index:03d}"
        for phase in ("P0", "P1", "P2")
        for index in range(1, 10)
    )
    if tuple(item.test_id for item in tests) != expected_test_ids:
        raise ValueError("H25 test ID order mismatch.")
    return H25DormantScientificPlan(
        repository_root=repository,
        contract=MappingProxyType(contract),
        population_manifest=MappingProxyType(population),
        test_manifest=MappingProxyType(test_manifest),
        fixture_specifications=MappingProxyType(specifications),
        fixtures=tuple(fixtures),
        tests=tuple(tests),
        population_bindings=MappingProxyType({
            "population_index.jsonl": POPULATION_INDEX_SHA256,
            "runtime_provenance.json": POPULATION_PROVENANCE_SHA256,
            "population_receipt.json": POPULATION_RECEIPT_SHA256,
        }),
    )


def build_typed_harmonic_graph() -> tuple[dict[str, object], ...]:
    """Return the exact closed H1/H2..H20 relation graph."""

    edges: list[dict[str, object]] = []
    for pitch in LATENT_PITCHES:
        for harmonic in HARMONIC_RANKS:
            coordinate = float(pitch + 12.0 * math.log2(float(harmonic)))
            if coordinate <= OBSERVATION_MAX:
                edges.append({
                    "source_pitch": pitch,
                    "harmonic_rank": harmonic,
                    "observation_coordinate": coordinate,
                    "relation_type": (
                        "FUNDAMENTAL_IDENTITY" if harmonic == 1 else "PROPER_HARMONIC_ASCENT"
                    ),
                })
    return tuple(edges)


@dataclass(frozen=True)
class H25DilutionResult:
    pitches: Any
    transform_grid: Any
    harmonic_coordinates: Any
    harmonic_support: Any
    pair_support: Any
    baseline_valid: Any
    raw: Any
    normalized: Any
    geometric_null: Any
    residual: Any
    total_window_power: float


def causal_power_spectrum(np: Any, waveform: Any, *, end_sample: int, window_samples: int) -> tuple[Any, Any]:
    """Compute one strictly causal Hann-windowed power spectrum ending at end_sample."""

    if window_samples not in {SHORT_WINDOW_SAMPLES, LONG_WINDOW_SAMPLES}:
        raise ValueError("H25 window length is not sealed.")
    array = np.asarray(waveform, dtype=np.float64)
    if array.ndim != 1 or end_sample < window_samples - 1 or end_sample >= array.size:
        raise ValueError("H25 causal window is outside the waveform.")
    start = end_sample - window_samples + 1
    window = array[start : end_sample + 1]
    if not bool(np.all(np.isfinite(window))):
        raise ValueError("H25 causal window contains a nonfinite sample.")
    n = np.arange(window_samples, dtype=np.float64)
    hann = 0.5 - 0.5 * np.cos(2.0 * np.pi * n / float(window_samples))
    power = np.abs(np.fft.rfft(window * hann)) ** 2
    frequencies = np.arange(power.size, dtype=np.float64) * SAMPLE_RATE_HZ / float(window_samples)
    return power.astype(np.float64, copy=False), frequencies


def support_normalized_dilution(np: Any, power: Any, frequencies: Any, *, candidate_pitches: Sequence[int] = PHYSICAL_PITCHES) -> H25DilutionResult:
    """Vectorized H25_SUPPORT_NORMALIZED_DILUTION_V1.

    The single shared spectrum is projected onto H1..H20 once.  Transform s
    changes only which projected harmonics remain observable after an ideal
    semitone scaling.  Invalid support is represented by a mask and NaN, never
    by fabricated zero evidence.  The support-only response is normalized and
    subtracted as the geometric null.
    """

    p = np.asarray(tuple(int(value) for value in candidate_pitches), dtype=np.int64)
    if p.ndim != 1 or p.size == 0 or len(set(int(value) for value in p)) != p.size:
        raise ValueError("H25 candidate pitches must be a unique nonempty vector.")
    if bool(np.any((p < 40) | (p > 76))):
        raise ValueError("H25 candidate pitch is outside MIDI 40..76.")
    spectrum = np.asarray(power, dtype=np.float64)
    hz = np.asarray(frequencies, dtype=np.float64)
    if spectrum.ndim != 1 or hz.shape != spectrum.shape or spectrum.size < 2:
        raise ValueError("H25 spectrum/frequency shape mismatch.")
    if not bool(np.all(np.isfinite(spectrum))) or bool(np.any(spectrum < 0.0)):
        raise ValueError("H25 power spectrum is invalid.")
    if not bool(np.all(np.isfinite(hz))) or float(hz[0]) != 0.0 or not bool(np.all(np.diff(hz) > 0.0)):
        raise ValueError("H25 frequency grid is invalid.")
    harmonics = np.arange(1, 21, dtype=np.float64)
    shifts = np.arange(89, dtype=np.int64)
    coordinates = p.astype(np.float64)[:, None] + 12.0 * np.log2(harmonics[None, :])
    harmonic_hz = 440.0 * np.power(2.0, (coordinates - 69.0) / 12.0)
    positive = hz > 0.0
    cents = np.full((p.size, 20, hz.size), np.inf, dtype=np.float64)
    cents[:, :, positive] = np.abs(
        1200.0 * np.log2(hz[None, None, positive] / harmonic_hz[:, :, None])
    )
    kernels = np.maximum(0.0, 1.0 - cents / 35.0)
    kernel_mass = np.sum(kernels, axis=2)
    base_support = (coordinates <= OBSERVATION_MAX) & (harmonic_hz <= SAMPLE_RATE_HZ / 2.0) & (kernel_mass > 0.0)
    shifted_coordinates = coordinates[:, None, :] + shifts[None, :, None]
    harmonic_support = base_support[:, None, :] & (shifted_coordinates <= OBSERVATION_MAX)
    pair_support = np.any(harmonic_support, axis=2)
    harmonic_energy = np.einsum("k,phk->ph", spectrum, kernels, optimize=True)
    weights = 1.0 / harmonics
    weighted_energy = harmonic_energy * weights[None, :]
    weighted_geometry = kernel_mass * weights[None, :]
    raw_finite = np.einsum("psh,ph->ps", harmonic_support, weighted_energy, optimize=True)
    null_finite = np.einsum("psh,ph->ps", harmonic_support, weighted_geometry, optimize=True)
    total_power = float(np.sum(spectrum, dtype=np.float64))
    baseline = raw_finite[:, 0]
    baseline_valid = baseline > np.maximum(BASELINE_ABSOLUTE_MIN, BASELINE_RELATIVE_MIN * total_power)
    valid = pair_support & baseline_valid[:, None] & (null_finite[:, 0, None] > 0.0)
    raw = np.full(raw_finite.shape, np.nan, dtype=np.float64)
    normalized = np.full(raw_finite.shape, np.nan, dtype=np.float64)
    geometric_null = np.full(raw_finite.shape, np.nan, dtype=np.float64)
    raw[pair_support] = raw_finite[pair_support]
    normalized_finite = np.zeros(raw_finite.shape, dtype=np.float64)
    geometric_null_finite = np.zeros(null_finite.shape, dtype=np.float64)
    np.divide(raw_finite, baseline[:, None], out=normalized_finite, where=baseline[:, None] != 0.0)
    np.divide(
        null_finite,
        null_finite[:, 0, None],
        out=geometric_null_finite,
        where=null_finite[:, 0, None] != 0.0,
    )
    normalized[valid] = normalized_finite[valid]
    geometric_null[valid] = geometric_null_finite[valid]
    residual = normalized - geometric_null
    if bool(np.any(~np.isfinite(residual[valid]))) or bool(np.any(np.isfinite(residual[~valid]))):
        raise ValueError("H25 residual mask/nonfinite invariant failed.")
    return H25DilutionResult(
        pitches=p,
        transform_grid=shifts,
        harmonic_coordinates=coordinates,
        harmonic_support=harmonic_support,
        pair_support=pair_support,
        baseline_valid=baseline_valid,
        raw=raw,
        normalized=normalized,
        geometric_null=geometric_null,
        residual=residual,
        total_window_power=total_power,
    )


def scalar_support_normalized_dilution(np: Any, power: Any, frequencies: Any, *, candidate_pitch: int) -> Mapping[str, Any]:
    """Independent scalar reference for one candidate and all 89 shifts."""

    spectrum = np.asarray(power, dtype=np.float64)
    hz = np.asarray(frequencies, dtype=np.float64)
    energies: list[float] = []
    masses: list[float] = []
    coordinates: list[float] = []
    base_supported: list[bool] = []
    for harmonic in HARMONIC_RANKS:
        coordinate = float(candidate_pitch + 12.0 * math.log2(float(harmonic)))
        frequency = 440.0 * math.pow(2.0, (coordinate - 69.0) / 12.0)
        kernel = np.zeros(hz.shape, dtype=np.float64)
        positive = hz > 0.0
        kernel[positive] = np.maximum(
            0.0, 1.0 - np.abs(1200.0 * np.log2(hz[positive] / frequency)) / 35.0
        )
        mass = float(np.sum(kernel, dtype=np.float64))
        coordinates.append(coordinate)
        masses.append(mass / float(harmonic))
        energies.append(float(np.sum(spectrum * kernel, dtype=np.float64)) / float(harmonic))
        base_supported.append(coordinate <= OBSERVATION_MAX and frequency <= SAMPLE_RATE_HZ / 2.0 and mass > 0.0)
    raw_values: list[float] = []
    null_values: list[float] = []
    supported_values: list[bool] = []
    for shift in TRANSFORM_GRID:
        supported = [base and coordinate + shift <= OBSERVATION_MAX for base, coordinate in zip(base_supported, coordinates)]
        supported_values.append(any(supported))
        raw_values.append(sum(value for value, keep in zip(energies, supported) if keep))
        null_values.append(sum(value for value, keep in zip(masses, supported) if keep))
    total = float(np.sum(spectrum, dtype=np.float64))
    baseline_valid = raw_values[0] > max(BASELINE_ABSOLUTE_MIN, BASELINE_RELATIVE_MIN * total)
    raw: list[float] = []
    normalized: list[float] = []
    null: list[float] = []
    residual: list[float] = []
    for keep, raw_value, null_value in zip(supported_values, raw_values, null_values):
        if not keep:
            raw.append(math.nan)
            normalized.append(math.nan)
            null.append(math.nan)
            residual.append(math.nan)
        elif not baseline_valid or null_values[0] <= 0.0:
            raw.append(raw_value)
            normalized.append(math.nan)
            null.append(math.nan)
            residual.append(math.nan)
        else:
            normalized_value = raw_value / raw_values[0]
            null_value_normalized = null_value / null_values[0]
            raw.append(raw_value)
            normalized.append(normalized_value)
            null.append(null_value_normalized)
            residual.append(normalized_value - null_value_normalized)
    return MappingProxyType({
        "pair_support": tuple(supported_values),
        "baseline_valid": baseline_valid,
        "raw": tuple(raw),
        "normalized": tuple(normalized),
        "geometric_null": tuple(null),
        "residual": tuple(residual),
    })


@dataclass(frozen=True)
class H25CandidateFeatures:
    candidate_pitch: int
    short_window_onset_rise: float | None
    short_window_harmonic_novelty: float | None
    short_window_new_energy: float | None
    long_window_persistence_or_decay: float | None
    old_source_explanation_residual: float | None
    dilution_residual_change_l1: float | None
    short_valid: bool
    long_valid: bool
    maximum_sample_read: int


def _row(result: H25DilutionResult, pitch: int) -> int:
    matches = [index for index, value in enumerate(result.pitches.tolist()) if int(value) == pitch]
    if len(matches) != 1:
        raise ValueError("H25 candidate pitch row is absent or duplicated.")
    return matches[0]


def _nnls_active_set(np: Any, matrix: Any, target: Any) -> Any:
    columns = int(matrix.shape[1])
    solution = np.zeros(columns, dtype=np.float64)
    passive = np.zeros(columns, dtype=bool)
    tolerance = 10.0 * np.finfo(np.float64).eps * max(1.0, float(np.linalg.norm(matrix, 1)))
    for _ in range(5 * max(columns, 1)):
        gradient = matrix.T @ (target - matrix @ solution)
        candidates = np.flatnonzero((~passive) & (gradient > tolerance))
        if candidates.size == 0:
            break
        best = float(np.max(gradient[candidates]))
        entering = int(candidates[np.flatnonzero(gradient[candidates] == best)[0]])
        passive[entering] = True
        while True:
            trial = np.zeros(columns, dtype=np.float64)
            active = np.flatnonzero(passive)
            if active.size:
                trial[active] = np.linalg.lstsq(matrix[:, active], target, rcond=None)[0]
            if bool(np.all(trial[active] > tolerance)):
                solution = trial
                break
            violating = active[trial[active] <= tolerance]
            ratios = solution[violating] / (solution[violating] - trial[violating])
            alpha = float(np.min(ratios)) if ratios.size else 0.0
            solution += alpha * (trial - solution)
            remove = passive & (solution <= tolerance)
            passive[remove] = False
            solution[remove] = 0.0
    if not bool(np.all(np.isfinite(solution))) or bool(np.any(solution < -tolerance)):
        raise ValueError("H25 NNLS produced an invalid solution.")
    return np.maximum(solution, 0.0)


def _source_factorization_residual(np: Any, power: Any, frequencies: Any, hypotheses: Sequence[int]) -> float:
    coordinates = np.arange(40, 129, dtype=np.float64)
    coordinate_hz = 440.0 * np.power(2.0, (coordinates - 69.0) / 12.0)
    positive = frequencies > 0.0
    cents = np.full((coordinates.size, frequencies.size), np.inf, dtype=np.float64)
    cents[:, positive] = np.abs(1200.0 * np.log2(frequencies[None, positive] / coordinate_hz[:, None]))
    kernels = np.maximum(0.0, 1.0 - cents / 35.0)
    valid = (coordinate_hz <= SAMPLE_RATE_HZ / 2.0) & (np.sum(kernels, axis=1) > 0.0)
    target = np.sqrt(np.maximum(np.einsum("k,qk->q", power, kernels, optimize=True), 0.0))
    ordered = tuple(sorted(set(int(value) for value in hypotheses)))
    if any(value < 24 or value > 76 for value in ordered):
        raise ValueError("H25 old-source state is outside MIDI 24..76.")
    if not ordered:
        return float(np.sum(target[valid] ** 2, dtype=np.float64))
    columns = []
    for pitch in ordered:
        column = np.zeros(coordinates.size, dtype=np.float64)
        for harmonic in HARMONIC_RANKS:
            q = pitch + 12.0 * math.log2(float(harmonic))
            distance = np.abs(100.0 * (coordinates - q))
            column += np.maximum(0.0, 1.0 - distance / 35.0) / float(harmonic)
        norm = float(np.linalg.norm(column[valid]))
        if not norm > 0.0:
            raise ValueError("H25 source dictionary column has no support.")
        columns.append(column / norm)
    matrix = np.stack(columns, axis=1)[valid]
    amplitudes = _nnls_active_set(np, matrix, target[valid])
    return float(np.sum((target[valid] - matrix @ amplitudes) ** 2, dtype=np.float64))


def extract_causal_candidate_features(
    np: Any,
    waveform: Any,
    *,
    candidate_pitch: int,
    decision_hop_end: int,
    active_pitches: Sequence[int] = (),
) -> H25CandidateFeatures:
    """Extract only current/past evidence; the long view cannot decide onset."""

    if decision_hop_end - HOP_SAMPLES < LONG_WINDOW_SAMPLES - 1:
        raise ValueError("H25 previous long window is unavailable.")
    views: dict[str, H25DilutionResult] = {}
    spectra: dict[str, tuple[Any, Any]] = {}
    for name, length, end in (
        ("short_current", SHORT_WINDOW_SAMPLES, decision_hop_end),
        ("short_previous", SHORT_WINDOW_SAMPLES, decision_hop_end - HOP_SAMPLES),
        ("long_current", LONG_WINDOW_SAMPLES, decision_hop_end),
        ("long_previous", LONG_WINDOW_SAMPLES, decision_hop_end - HOP_SAMPLES),
    ):
        power, frequencies = causal_power_spectrum(np, waveform, end_sample=end, window_samples=length)
        spectra[name] = (power, frequencies)
        views[name] = support_normalized_dilution(np, power, frequencies, candidate_pitches=(candidate_pitch,))
    current = views["short_current"]
    previous = views["short_previous"]
    long_current = views["long_current"]
    long_previous = views["long_previous"]
    row = 0
    short_valid = bool(current.baseline_valid[row] and previous.baseline_valid[row])
    long_valid = bool(long_current.baseline_valid[row] and long_previous.baseline_valid[row])
    current_baseline = float(current.raw[row, 0]) if short_valid else math.nan
    previous_baseline = float(previous.raw[row, 0]) if short_valid else math.nan
    onset = max(0.0, current_baseline - previous_baseline) / max(current_baseline, BASELINE_ABSOLUTE_MIN) if short_valid else None
    current_residual = current.residual[row]
    previous_residual = previous.residual[row]
    common = np.isfinite(current_residual) & np.isfinite(previous_residual)
    dilution_change = float(np.sum(np.abs(current_residual[common] - previous_residual[common]))) if short_valid and bool(np.any(common)) else None
    current_power, frequencies = spectra["short_current"]
    previous_power, _ = spectra["short_previous"]
    f0 = 440.0 * math.pow(2.0, (candidate_pitch - 69.0) / 12.0)
    own_current: list[float] = []
    own_previous: list[float] = []
    for harmonic in (2, 3, 4):
        target = f0 * harmonic
        positive = frequencies > 0.0
        kernel = np.zeros(frequencies.shape, dtype=np.float64)
        kernel[positive] = np.maximum(0.0, 1.0 - np.abs(1200.0 * np.log2(frequencies[positive] / target)) / 35.0)
        own_current.append(float(np.sum(current_power * kernel, dtype=np.float64)))
        own_previous.append(float(np.sum(previous_power * kernel, dtype=np.float64)))
    own_denominator = sum(own_current)
    novelty = sum(max(0.0, left - right) for left, right in zip(own_current, own_previous)) / max(own_denominator, BASELINE_ABSOLUTE_MIN) if short_valid else None
    new_energy = max(0.0, float(np.sum(current_power)) - float(np.sum(previous_power))) / max(float(np.sum(current_power)), BASELINE_ABSOLUTE_MIN) if short_valid else None
    long_now = float(long_current.raw[row, 0]) if long_valid else math.nan
    long_before = float(long_previous.raw[row, 0]) if long_valid else math.nan
    persistence = (long_now - long_before) / max(long_now, BASELINE_ABSOLUTE_MIN) if long_valid else None
    if short_valid:
        residual_old = _source_factorization_residual(np, current_power, frequencies, active_pitches)
        residual_with_candidate = _source_factorization_residual(
            np, current_power, frequencies, tuple(active_pitches) + (candidate_pitch,)
        )
        old_explanation = max(0.0, residual_old - residual_with_candidate) / max(
            residual_old, BASELINE_ABSOLUTE_MIN
        )
    else:
        old_explanation = None
    return H25CandidateFeatures(
        candidate_pitch=candidate_pitch,
        short_window_onset_rise=onset,
        short_window_harmonic_novelty=novelty,
        short_window_new_energy=new_energy,
        long_window_persistence_or_decay=persistence,
        old_source_explanation_residual=old_explanation,
        dilution_residual_change_l1=dilution_change,
        short_valid=short_valid,
        long_valid=long_valid,
        maximum_sample_read=decision_hop_end,
    )


def resolve_one_hop_candidate(*, previous_state: str, features: H25CandidateFeatures) -> tuple[str, str]:
    """Resolve a candidate exactly once; no pending state may survive."""

    if previous_state not in STATES:
        raise ValueError("H25 candidate state is unknown.")
    if previous_state == "ACTIVE":
        return "ACTIVE", "ALREADY_ACTIVE_HISTORY"
    if previous_state != "PENDING_NEW":
        raise ValueError("H25 resolution requires a PENDING_NEW candidate.")
    if not features.short_valid or not features.long_valid:
        return "INACTIVE", "AMBIGUOUS"
    values = (
        features.short_window_onset_rise,
        features.short_window_harmonic_novelty,
        features.short_window_new_energy,
        features.old_source_explanation_residual,
        features.dilution_residual_change_l1,
    )
    if any(value is None or not math.isfinite(value) for value in values):
        return "INACTIVE", "AMBIGUOUS"
    onset, novelty, new_energy, old_residual, dilution = (float(value) for value in values)
    positive = (
        onset > ATOL
        and novelty > ATOL
        and new_energy > ATOL
        and old_residual > ATOL
        and dilution >= 0.0
    )
    absent = onset <= ATOL and novelty <= ATOL and new_energy <= ATOL
    if positive:
        return "ACTIVE", "BIRTH_SUPPORTED"
    if absent:
        return (
            ("INACTIVE", "NO_BIRTH")
            if old_residual <= ATOL
            else ("INACTIVE", "AMBIGUOUS")
        )
    return "INACTIVE", "AMBIGUOUS"


@dataclass(frozen=True)
class H25CausalReplayTrace:
    """Auditable active-state trace produced only from prior decoder events."""

    fixture_id: str
    observed_through_sample: int
    initial_active_pitches: tuple[int, ...]
    transitions: tuple[Mapping[str, object], ...]

    def active_pitches(self) -> tuple[int, ...]:
        if self.initial_active_pitches:
            raise ValueError("H25 causal replay must start with every pitch INACTIVE.")
        active: set[int] = set()
        for raw in self.transitions:
            if set(raw) != {"sample_index", "kind", "pitch"}:
                raise ValueError("H25 causal replay transition schema is invalid.")
            sample_index = raw["sample_index"]
            kind = raw["kind"]
            pitch = raw["pitch"]
            if type(sample_index) is not int or sample_index > self.observed_through_sample:
                raise ValueError("H25 causal replay transition reads the future.")
            if kind not in {"note_on", "note_off"} or type(pitch) is not int or not 24 <= pitch <= 76:
                raise ValueError("H25 causal replay transition value is invalid.")
            if kind == "note_on":
                active.add(pitch)
            else:
                active.discard(pitch)
        return tuple(sorted(active))


@dataclass(frozen=True)
class H25EvidenceProducerContext:
    np: Any
    plan: H25DormantScientificPlan
    waveforms: Mapping[str, Any]
    fixture_records: Mapping[str, Mapping[str, object]]
    causal_replay_traces: Mapping[str, H25CausalReplayTrace]
    started_ns: int
    peak_rss_bytes: int
    operational_counters: Mapping[str, int] | None = None
    observed_fixture_ids: tuple[str, ...] = ()
    observed_test_ids: tuple[str, ...] = ()
    observed_test_records: Mapping[str, Mapping[str, object]] | None = None


def _json_features(features: H25CandidateFeatures) -> dict[str, object]:
    return {
        "candidate_pitch": features.candidate_pitch,
        "short_window_onset_rise": features.short_window_onset_rise,
        "short_window_harmonic_novelty": features.short_window_harmonic_novelty,
        "short_window_new_energy": features.short_window_new_energy,
        "long_window_persistence_or_decay": features.long_window_persistence_or_decay,
        "old_source_explanation_residual": features.old_source_explanation_residual,
        "dilution_residual_change_l1": features.dilution_residual_change_l1,
        "short_valid": features.short_valid,
        "long_valid": features.long_valid,
        "maximum_sample_read": features.maximum_sample_read,
    }


def _masked_float_list(np: Any, value: Any) -> list[float | None]:
    array = np.asarray(value, dtype=np.float64)
    return [float(item) if bool(np.isfinite(item)) else None for item in array]


def _json_replay_trace(trace: H25CausalReplayTrace) -> dict[str, object]:
    return {
        "fixture_id": trace.fixture_id,
        "observed_through_sample": trace.observed_through_sample,
        "initial_active_pitches": list(trace.initial_active_pitches),
        "transitions": [dict(item) for item in trace.transitions],
        "derived_active_pitches": list(trace.active_pitches()),
    }


def _raw_operator_operands(np: Any, power: Any, frequencies: Any, pitch: int) -> dict[str, object]:
    return {
        "candidate_pitch": pitch,
        "power": [float(value) for value in np.asarray(power, dtype=np.float64).tolist()],
        "frequencies_hz": [float(value) for value in np.asarray(frequencies, dtype=np.float64).tolist()],
    }


def _fixture_measurement(context: H25EvidenceProducerContext, fixture_id: str) -> dict[str, object]:
    record = context.fixture_records[fixture_id]
    source = record["source_fixture_record"]
    candidate = source.get("candidate_pitch")
    if candidate is None:
        return {"fixture_id": fixture_id, "candidate_pitch": None, "state_trace": ["INACTIVE", "PENDING_NEW", "INACTIVE"], "outcome": "AMBIGUOUS", "features": None}
    candidate_pitch = int(candidate)
    trace = context.causal_replay_traces[fixture_id]
    if trace.fixture_id != fixture_id or trace.observed_through_sample != 16383:
        raise ValueError("H25 active-state trace is not bound to the target causal hop.")
    old_pitches = trace.active_pitches()
    if any(pitch < 24 or pitch > 76 for pitch in old_pitches):
        raise ValueError("H25 causal replay supplied an invalid active pitch.")
    initial = "ACTIVE" if candidate_pitch in old_pitches else "INACTIVE"
    if initial == "ACTIVE":
        features = extract_causal_candidate_features(context.np, context.waveforms[fixture_id], candidate_pitch=candidate_pitch, decision_hop_end=16639, active_pitches=old_pitches)
        state, outcome = resolve_one_hop_candidate(previous_state="ACTIVE", features=features)
        trace = ["ACTIVE", "ACTIVE"]
    else:
        features = extract_causal_candidate_features(context.np, context.waveforms[fixture_id], candidate_pitch=candidate_pitch, decision_hop_end=16639, active_pitches=old_pitches)
        state, outcome = resolve_one_hop_candidate(previous_state="PENDING_NEW", features=features)
        trace = ["INACTIVE", "PENDING_NEW", state]
    return {
        "fixture_id": fixture_id,
        "candidate_pitch": candidate_pitch,
        "state_trace": trace,
        "outcome": outcome,
        "features": _json_features(features),
        "causal_replay_trace": _json_replay_trace(context.causal_replay_traces[fixture_id]),
    }


def _measurement_from_inputs(
    context: H25EvidenceProducerContext,
    fixture_id: str,
    waveform: Any,
    replay_trace: H25CausalReplayTrace,
) -> dict[str, object]:
    source = context.fixture_records[fixture_id]["source_fixture_record"]
    candidate = source.get("candidate_pitch")
    if candidate is None:
        return {"fixture_id": fixture_id, "candidate_pitch": None, "features": None, "causal_replay_trace": _json_replay_trace(replay_trace)}
    pitch = int(candidate)
    active = replay_trace.active_pitches()
    features = extract_causal_candidate_features(
        context.np, waveform, candidate_pitch=pitch, decision_hop_end=16639, active_pitches=active
    )
    previous_state = "ACTIVE" if pitch in active else "PENDING_NEW"
    _, outcome = resolve_one_hop_candidate(previous_state=previous_state, features=features)
    return {
        "fixture_id": fixture_id,
        "candidate_pitch": pitch,
        "features": _json_features(features),
        "causal_replay_trace": _json_replay_trace(replay_trace),
        "derived_outcome": outcome,
    }


def _source_pitch(context: H25EvidenceProducerContext, fixture_id: str) -> int:
    source = context.fixture_records[fixture_id]["source_fixture_record"]
    parameters = source.get("parameters")
    if type(parameters) is dict and type(parameters.get("old_pitch")) is int:
        return int(parameters["old_pitch"])
    candidate = source.get("candidate_pitch")
    if type(candidate) is int:
        return candidate
    return 24


def _input_perturbation_measurements(
    context: H25EvidenceProducerContext,
    test: H25TestSpecification,
) -> dict[str, object]:
    kind_by_test = {
        "H25-T-P1-001": "remove_new_source_waveform",
        "H25-T-P1-002": "remove_newest_hop_attack",
        "H25-T-P1-003": "exclusive_partial_owner_claim",
        "H25-T-P1-004": "resolve_at_target_hop",
        "H25-T-P1-005": "force_old_harmonic_as_new_state",
        "H25-T-P1-006": "erase_old_source_state",
        "H25-T-P1-007": "inject_independent_attack",
        "H25-T-P1-008": "force_binary_attribution",
        "H25-T-P1-009": "force_nearest_midi_source",
        "H25-T-P2-003": "phase_label_only",
        "H25-T-P2-004": "undeclared_100_cent_shift",
        "H25-T-P2-005": "coordinate_128_emit_capable",
    }
    kind = kind_by_test[test.test_id]
    measurements: list[dict[str, object]] = []
    for fixture_id in test.fixture_ids:
        waveform = context.np.asarray(context.waveforms[fixture_id], dtype=context.np.float64).copy()
        replay = context.causal_replay_traces[fixture_id]
        if kind in {"remove_new_source_waveform", "remove_newest_hop_attack"}:
            waveform[16128:16640] = context.np.resize(waveform[15872:16128], 512)
        elif kind == "inject_independent_attack":
            source = context.fixture_records[fixture_id]["source_fixture_record"]
            pitch = int(source["candidate_pitch"])
            indices = context.np.arange(waveform.size - 16128, dtype=context.np.float64)
            hz = 440.0 * math.pow(2.0, (pitch - 69.0) / 12.0)
            waveform[16128:] += context.np.sin(2.0 * context.np.pi * hz * indices / SAMPLE_RATE_HZ)
        elif kind == "erase_old_source_state":
            replay = H25CausalReplayTrace(fixture_id, 16383, (), ())
        if kind in {"exclusive_partial_owner_claim", "force_binary_attribution", "force_nearest_midi_source", "phase_label_only", "undeclared_100_cent_shift", "coordinate_128_emit_capable", "resolve_at_target_hop", "force_old_harmonic_as_new_state"}:
            raw_mutations = {
                "exclusive_partial_owner_claim": {"exclusive_partial_owner_pitch": _source_pitch(context, fixture_id)},
                "force_binary_attribution": {"forced_outcome": "BIRTH_SUPPORTED"},
                "force_nearest_midi_source": {"forced_source_pitch": _source_pitch(context, fixture_id)},
                "phase_label_only": {"phase_label_radians": 1.5707963267948966},
                "undeclared_100_cent_shift": {"pitch_shift_cents": 100.0},
                "coordinate_128_emit_capable": {"emit_coordinate": 128.0},
                "resolve_at_target_hop": {"resolution_sample": 16383},
                "force_old_harmonic_as_new_state": {"state_override": "PENDING_NEW", "state_source": "fixture_label"},
            }
            measurements.append({
                "fixture_id": fixture_id,
                "perturbation_kind": kind,
                "raw_mutation": raw_mutations[kind],
            })
        else:
            item = _measurement_from_inputs(context, fixture_id, waveform, replay)
            item["perturbation_kind"] = kind
            item["waveform_changed"] = bool(not context.np.array_equal(waveform, context.waveforms[fixture_id]))
            measurements.append(item)
    return {"input_perturbations": measurements}


def _permutation_evidence(
    context: H25EvidenceProducerContext,
    fixture_ids: Sequence[str],
) -> dict[str, object]:
    candidate_transform_rows: list[dict[str, object]] = []
    for fixture_id in fixture_ids:
        source = context.fixture_records[fixture_id]["source_fixture_record"]
        candidate = source.get("candidate_pitch")
        if candidate is None:
            candidate_transform_rows.append({
                "fixture_id": fixture_id,
                "candidate_pitch": None,
                "candidate_orders": [],
                "transform_records_reversed": [],
            })
            continue
        pitch = int(candidate)
        alternate = 40 if pitch != 40 else 41
        power, hz = causal_power_spectrum(
            context.np,
            context.waveforms[fixture_id],
            end_sample=16639,
            window_samples=SHORT_WINDOW_SAMPLES,
        )
        forward_pitches = (pitch, alternate)
        reverse_pitches = tuple(reversed(forward_pitches))
        forward = support_normalized_dilution(
            context.np, power, hz, candidate_pitches=forward_pitches
        )
        reverse = support_normalized_dilution(
            context.np, power, hz, candidate_pitches=reverse_pitches
        )
        pitch_row = forward_pitches.index(pitch)
        candidate_transform_rows.append({
            "fixture_id": fixture_id,
            "candidate_pitch": pitch,
            "candidate_orders": [
                {
                    "pitches": list(forward_pitches),
                    "pair_support": forward.pair_support.tolist(),
                    "raw": [_masked_float_list(context.np, row) for row in forward.raw],
                },
                {
                    "pitches": list(reverse_pitches),
                    "pair_support": reverse.pair_support.tolist(),
                    "raw": [_masked_float_list(context.np, row) for row in reverse.raw],
                },
            ],
            "transform_records_reversed": [
                {
                    "shift": shift,
                    "support": bool(forward.pair_support[pitch_row, shift]),
                    "raw": _masked_float_list(context.np, forward.raw[pitch_row])[shift],
                }
                for shift in reversed(TRANSFORM_GRID)
            ],
        })
    graph = list(build_typed_harmonic_graph())
    return {
        "candidate_transform_rows": candidate_transform_rows,
        "graph_orders": [graph, list(reversed(graph))],
    }


def produce_h25_test_evidence(context: H25EvidenceProducerContext, test: H25TestSpecification) -> dict[str, object]:
    """Produce raw operands/measurements only; never a producer verdict."""

    if test.test_id not in context.plan.test_ids:
        raise ValueError("H25 producer received an unsealed test.")
    evidence: dict[str, object] = {
        "schema_version": 1,
        "test_id": test.test_id,
        "phase": test.phase,
        "objective": test.objective,
        "fixture_measurements": [_fixture_measurement(context, fixture_id) for fixture_id in test.fixture_ids],
    }
    if test.test_id == "H25-T-P0-001":
        graph = list(build_typed_harmonic_graph())
        evidence["typed_harmonic_graph"] = graph
        evidence["inverse_measurement"] = {"mutated_typed_harmonic_graph": graph[1:]}
    elif test.test_id in {"H25-T-P0-002", "H25-T-P0-005", "H25-T-P0-006", "H25-T-P0-008"} and test.fixture_ids:
        operator_measurements: list[dict[str, object]] = []
        for fixture_id in test.fixture_ids:
            record = context.fixture_records[fixture_id]["source_fixture_record"]
            candidate = record.get("candidate_pitch")
            if candidate is None:
                continue
            pitch = int(candidate)
            power, hz = causal_power_spectrum(context.np, context.waveforms[fixture_id], end_sample=16639, window_samples=SHORT_WINDOW_SAMPLES)
            vector = support_normalized_dilution(context.np, power, hz, candidate_pitches=(pitch,))
            operator_measurements.append({
                "fixture_id": fixture_id,
                "raw_operands": _raw_operator_operands(context.np, power, hz, pitch),
                "pair_support": vector.pair_support[0].tolist(),
                "baseline_valid": bool(vector.baseline_valid[0]),
                "raw": _masked_float_list(context.np, vector.raw[0]),
                "normalized": _masked_float_list(context.np, vector.normalized[0]),
                "geometric_null": _masked_float_list(context.np, vector.geometric_null[0]),
                "residual": _masked_float_list(context.np, vector.residual[0]),
            })
        evidence["operator_measurements"] = operator_measurements
        if test.test_id == "H25-T-P0-002":
            analytic_coordinates = []
            for item in operator_measurements:
                pitch = int(item["raw_operands"]["candidate_pitch"])
                for shift in TRANSFORM_GRID:
                    for harmonic in HARMONIC_RANKS:
                        base_hz = 440.0 * math.pow(2.0, (pitch - 69.0) / 12.0)
                        scaled_hz = base_hz * math.pow(2.0, shift / 12.0) * harmonic
                        analytic_coordinates.append({
                            "fixture_id": item["fixture_id"],
                            "candidate_pitch": pitch,
                            "harmonic_rank": harmonic,
                            "shift_semitones": shift,
                            "whole_spectrum_scaled_hz": scaled_hz,
                            "relative_remap_coordinate": pitch + shift + 12.0 * math.log2(float(harmonic)),
                        })
            evidence["analytic_scaling_operands"] = analytic_coordinates
        if test.test_id == "H25-T-P0-006":
            gain_pairs: list[dict[str, object]] = []
            for fixture_id in test.fixture_ids:
                record = context.fixture_records[fixture_id]["source_fixture_record"]
                candidate = record.get("candidate_pitch")
                if candidate is None:
                    continue
                power, hz = causal_power_spectrum(context.np, context.waveforms[fixture_id], end_sample=16639, window_samples=SHORT_WINDOW_SAMPLES)
                base = support_normalized_dilution(context.np, power, hz, candidate_pitches=(int(candidate),))
                scaled = support_normalized_dilution(context.np, power * 4.0, hz, candidate_pitches=(int(candidate),))
                gain_pairs.append({
                    "fixture_id": fixture_id,
                    "base_raw_operands": _raw_operator_operands(context.np, power, hz, int(candidate)),
                    "scaled_raw_operands": _raw_operator_operands(context.np, power * 4.0, hz, int(candidate)),
                    "base_residual": _masked_float_list(context.np, base.residual[0]),
                    "scaled_residual": _masked_float_list(context.np, scaled.residual[0]),
                })
            evidence["gain_invariance_pairs"] = gain_pairs
        if test.test_id == "H25-T-P0-002":
            inverse_operands = dict(operator_measurements[0]["raw_operands"]) if operator_measurements else {}
            if inverse_operands:
                inverse_operands["candidate_pitch"] = int(inverse_operands["candidate_pitch"]) + 1
            evidence["inverse_measurement"] = {"misaligned_candidate_raw_operands": inverse_operands}
        elif test.test_id == "H25-T-P0-005":
            first = operator_measurements[0] if operator_measurements else {}
            evidence["inverse_measurement"] = {"permuted_transform_records": [
                {
                    "shift": shift,
                    "pair_support": first.get("pair_support", [])[shift],
                    "raw": first.get("raw", [])[shift],
                    "normalized": first.get("normalized", [])[shift],
                    "geometric_null": first.get("geometric_null", [])[shift],
                    "residual": first.get("residual", [])[shift],
                }
                for shift in reversed(TRANSFORM_GRID)
            ]}
        else:
            source_measurement = next(
                (item for item in operator_measurements if any(value is None for value in item["residual"])),
                operator_measurements[0] if operator_measurements else {},
            )
            corrupted = dict(source_measurement)
            if corrupted:
                for key in ("raw", "normalized", "geometric_null", "residual"):
                    values = list(corrupted[key])
                    invalid = next((index for index, value in enumerate(values) if value is None), None)
                    if invalid is not None:
                        values[invalid] = 0.0
                    corrupted[key] = values
            evidence["inverse_measurement"] = {"zero_filled_invalid_measurement": corrupted}
    elif test.test_id == "H25-T-P0-003":
        evidence["inverse_measurement"] = {"injected_feature_name": "raw_disappearance_index"}
    elif test.test_id == "H25-T-P0-004":
        collision_explanations = []
        for fixture_id in test.fixture_ids:
            waveform = context.np.asarray(context.waveforms[fixture_id], dtype=context.np.float64)
            measurement = _fixture_measurement(context, fixture_id)
            shared = {
                "waveform_sha256": _sha256(waveform.tobytes()),
                "features": measurement.get("features"),
                "causal_state": measurement.get("causal_replay_trace"),
            }
            collision_explanations.append({
                "fixture_id": fixture_id,
                "waveform_samples_float64": [float(value) for value in waveform.tolist()],
                "latent_explanations": [
                    {"explanation_id": "OLD_HARMONIC_ONLY", **shared},
                    {"explanation_id": "PUTATIVE_NEW_FUNDAMENTAL", **shared},
                ],
            })
        evidence["collision_explanations"] = collision_explanations
        evidence["inverse_measurement"] = {"forced_attribution": "BIRTH_SUPPORTED"}
    elif test.test_id == "H25-T-P0-007":
        causal_boundaries = []
        for fixture_id in test.fixture_ids:
            source = context.fixture_records[fixture_id]["source_fixture_record"]
            candidate = source.get("candidate_pitch")
            if candidate is None:
                continue
            target_features = extract_causal_candidate_features(
                context.np,
                context.waveforms[fixture_id],
                candidate_pitch=int(candidate),
                decision_hop_end=16383,
                active_pitches=context.causal_replay_traces[fixture_id].active_pitches(),
            )
            causal_boundaries.append({
                "fixture_id": fixture_id,
                "short_current_end": 16383,
                "long_current_end": 16383,
                "short_previous_end": 16127,
                "long_previous_end": 16127,
                "maximum_sample_read": target_features.maximum_sample_read,
            })
        evidence["causal_boundaries"] = causal_boundaries
        evidence["inverse_measurement"] = {"causal_boundaries": [{**item, "short_current_end": 16384, "maximum_sample_read": 16384} for item in causal_boundaries]}
    elif test.test_id == "H25-T-P0-009":
        evidence["permutation_evidence"] = _permutation_evidence(context, test.fixture_ids)
        evidence["inverse_measurement"] = {"forced_order_invariance": "DIFFERENT"}
    elif test.test_id == "H25-T-P2-005":
        boundary_measurements = []
        for fixture_id in test.fixture_ids:
            source = context.fixture_records[fixture_id]["source_fixture_record"]
            candidate = source.get("candidate_pitch")
            if candidate is None:
                continue
            power, hz = causal_power_spectrum(
                context.np, context.waveforms[fixture_id], end_sample=16639, window_samples=SHORT_WINDOW_SAMPLES
            )
            vector = support_normalized_dilution(context.np, power, hz, candidate_pitches=(int(candidate),))
            boundary_measurements.append({
                "fixture_id": fixture_id,
                "raw_operands": _raw_operator_operands(context.np, power, hz, int(candidate)),
                "pair_support": vector.pair_support[0].tolist(),
                "baseline_valid": bool(vector.baseline_valid[0]),
                "raw": _masked_float_list(context.np, vector.raw[0]),
                "normalized": _masked_float_list(context.np, vector.normalized[0]),
                "geometric_null": _masked_float_list(context.np, vector.geometric_null[0]),
                "residual": _masked_float_list(context.np, vector.residual[0]),
            })
        evidence["boundary_operator_measurements"] = boundary_measurements
        evidence["inverse_measurement"] = _input_perturbation_measurements(context, test)
    elif test.test_id == "H25-T-P2-006":
        orders = {
            "manifest": list(test.fixture_ids),
            "reverse": list(reversed(test.fixture_ids)),
            "candidate_pitch_then_id": sorted(
                test.fixture_ids,
                key=lambda fixture_id: (
                    context.fixture_records[fixture_id]["source_fixture_record"].get("candidate_pitch") is None,
                    context.fixture_records[fixture_id]["source_fixture_record"].get("candidate_pitch") or -1,
                    fixture_id,
                ),
            ),
        }
        evidence["permutation_results"] = {
            name: [_fixture_measurement(context, fixture_id) for fixture_id in order]
            for name, order in orders.items()
        }
        evidence["permutation_evidence"] = _permutation_evidence(context, test.fixture_ids)
        evidence["inverse_measurement"] = {"filesystem_order_ids": sorted(test.fixture_ids, key=str.lower)}
    elif test.test_id in {"H25-T-P2-001", "H25-T-P2-002", "H25-T-P2-007"}:
        exact = True
        for fixture_id in test.fixture_ids:
            record = context.fixture_records[fixture_id]["source_fixture_record"]
            candidate = record.get("candidate_pitch")
            if candidate is None:
                continue
            pitch = int(candidate)
            original = context.waveforms[fixture_id]
            if test.test_id == "H25-T-P2-001":
                changed = context.np.asarray(original, dtype=context.np.float64).copy()
                changed[16384:] = changed[16384:] + context.np.linspace(0.0, 1.0, changed.size - 16384)
                left = extract_causal_candidate_features(context.np, original, candidate_pitch=pitch, decision_hop_end=16383)
                right = extract_causal_candidate_features(context.np, changed, candidate_pitch=pitch, decision_hop_end=16383)
                evidence.setdefault("future_suffix_pairs", []).append({
                    "fixture_id": fixture_id,
                    "original_features": _json_features(left),
                    "changed_future_features": _json_features(right),
                    "causal_end": 16383,
                    "changed_suffix_start": 16384,
                })
            elif test.test_id == "H25-T-P2-002":
                translations = []
                active = context.causal_replay_traces[fixture_id].active_pitches()
                for hops in (0, 1, 2, 4):
                    shifted = context.np.concatenate((
                        context.np.zeros(HOP_SAMPLES * hops),
                        context.np.asarray(original, dtype=context.np.float64),
                    ))
                    translated = extract_causal_candidate_features(
                        context.np,
                        shifted,
                        candidate_pitch=pitch,
                        decision_hop_end=16639 + HOP_SAMPLES * hops,
                        active_pitches=active,
                    )
                    translated_json = _json_features(translated)
                    translated_json["maximum_sample_read"] = 16639
                    previous_state = "ACTIVE" if pitch in active else "PENDING_NEW"
                    _, translated_outcome = resolve_one_hop_candidate(
                        previous_state=previous_state,
                        features=translated,
                    )
                    translations.append({
                        "hop_translation": hops,
                        "features": translated_json,
                        "derived_outcome": translated_outcome,
                        "resolution_delay_hops": 1,
                    })
                evidence.setdefault("hop_translation_results", []).append({
                    "fixture_id": fixture_id,
                    "translations": translations,
                })
                left = extract_causal_candidate_features(context.np, original, candidate_pitch=pitch, decision_hop_end=16639)
                right = left
            else:
                left = extract_causal_candidate_features(context.np, original, candidate_pitch=pitch, decision_hop_end=16639)
                right = extract_causal_candidate_features(context.np, original, candidate_pitch=pitch, decision_hop_end=16639)
            left_json = _json_features(left)
            right_json = _json_features(right)
            left_json["maximum_sample_read"] = 0
            right_json["maximum_sample_read"] = 0
            exact = exact and canonical_json_bytes(left_json) == canonical_json_bytes(right_json)
        if test.test_id == "H25-T-P2-007":
            if context.observed_test_records is None:
                raise ValueError("H25 current-runtime detailed test records are required for P2-007.")
            evidence["same_runtime_replay"] = {
                "first": evidence["fixture_measurements"],
                "second": [_fixture_measurement(context, fixture_id) for fixture_id in test.fixture_ids],
            }
            evidence["current_runtime_observation"] = {
                "runtime_id": "CURRENT_RUNTIME",
                "fixture_measurements": evidence["fixture_measurements"],
                "test_records": [
                    dict(context.observed_test_records[test_id])
                    for test_id in context.plan.test_ids
                ],
            }
            evidence["cross_runtime_observation"] = None
            evidence["inverse_measurement"] = {"runtime_binding_changed": True}
        else:
            evidence["invariance"] = "EXACT" if exact else "DIFFERENT"
            evidence["inverse_measurement"] = {"waveform_only_shift_hops": 1} if test.test_id == "H25-T-P2-002" else {"future_dependent": True}
    elif test.test_id == "H25-T-P2-008":
        if context.operational_counters is None:
            raise ValueError("H25 measured operational counters are required.")
        counters = dict(context.operational_counters)
        counters["elapsed_ns_since_context_start"] = time.perf_counter_ns() - context.started_ns
        counters["peak_rss_bytes"] = context.peak_rss_bytes
        evidence["operational_counters"] = counters
        evidence["inverse_measurement"] = {"operational_counters": {**counters, "model_inference_call_count": int(counters.get("model_inference_call_count", 0)) + 1}}
    elif test.test_id == "H25-T-P2-009":
        evidence["observed_id_evidence"] = {
            "fixture_ids": list(context.observed_fixture_ids),
            "test_ids": list(context.observed_test_ids),
        }
        evidence["inverse_measurement"] = {"observed_id_evidence": {
            "fixture_ids": list(context.observed_fixture_ids[:-1]),
            "test_ids": list(context.observed_test_ids),
        }}
    else:
        evidence["inverse_measurement"] = _input_perturbation_measurements(context, test)
    return evidence


def _build_producer_registry() -> Mapping[str, Callable[[H25EvidenceProducerContext, H25TestSpecification], dict[str, object]]]:
    identifiers = tuple(
        f"H25-T-{phase}-{index:03d}"
        for phase in ("P0", "P1", "P2")
        for index in range(1, 10)
    )
    return MappingProxyType({identifier: produce_h25_test_evidence for identifier in identifiers})


H25_EXACT_EVIDENCE_PRODUCER_REGISTRY = _build_producer_registry()


def require_h25_scientific_execution_authorized(_: object = None) -> None:
    raise PermissionError(
        "H25 scientific engine is dormant: no reviewed capability, seal, activation, OS binding, or claim exists."
    )


__all__ = [
    "H25DormantScientificPlan",
    "H25EvidenceProducerContext",
    "H25_EXACT_EVIDENCE_PRODUCER_REGISTRY",
    "H25DilutionResult",
    "H25CandidateFeatures",
    "H25CausalReplayTrace",
    "build_typed_harmonic_graph",
    "causal_power_spectrum",
    "extract_causal_candidate_features",
    "load_h25_dormant_scientific_plan",
    "produce_h25_test_evidence",
    "require_h25_scientific_execution_authorized",
    "resolve_one_hop_candidate",
    "scalar_support_normalized_dilution",
    "support_normalized_dilution",
]
