"""Independent dormant recomputer for H28 sealed records.

This module intentionally imports no H28 engine symbol and duplicates the
scientific derivation from sealed bytes.  Engine results are accepted only by
the final comparison function, after independent recomputation completes.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

from .harmonic_censoring_h28_timing_contract import (
    H28TimingContract, RECORD_ORDER, load_h28_timing_contract,
)
from .harmonic_censoring_h28_scientific_capability_dormant import (
    H28ScientificCapability, H28SealedRecordBinding,
    require_h28_scientific_capability, require_h28_sealed_record_binding,
)


_ROLES = ("current_short", "previous_short", "current_long", "previous_long")
_LENGTH = {"current_short": 4096, "previous_short": 4096,
           "current_long": 8192, "previous_long": 8192}
_BACK = {"current_short": 0, "previous_short": 256,
         "current_long": 0, "previous_long": 256}
_WAVEFORM_SAMPLES = 17152
_ROLE_MAJOR_MASK_VALUES = len(_ROLES) * _WAVEFORM_SAMPLES
_MAXIMUM_PROPOSAL_HOP_END = 16895
EXACT_RESULT_FIELDS = (
    "record_identity", "validated_payload_sha256", "role_classifications",
    "mask_counts", "outcome", "certificate_kind", "certificate_complete",
    "exclusive_ranks", "ratios_at_or_above_positive_threshold",
    "positive_partial_condition", "positive_onset_condition",
    "positive_residual_condition", "negative_partial_condition",
    "negative_onset_condition", "negative_residual_condition",
    "decision_reason", "maximum_sample_read",
)
NUMERIC_RESULT_FIELDS = (
    "current_short_total_power", "previous_short_total_power",
    "current_long_total_power", "previous_long_total_power",
    "exclusive_band_energies", "harmonic_ratios", "onset_rise",
    "active_residual_before_candidate", "augmented_residual_after_candidate",
    "residual_improvement", "persistence", "bounded_claim_lower_bounds",
    "negative_margins", "pitch_dilution_curve",
)


@dataclass(frozen=True)
class H28RecomputedResult:
    record_identity: str
    validated_payload_sha256: Mapping[str, str]
    role_classifications: Mapping[str, str]
    mask_counts: Mapping[str, int]
    current_short_total_power: float | None
    previous_short_total_power: float | None
    current_long_total_power: float | None
    previous_long_total_power: float | None
    outcome: str
    certificate_kind: str
    certificate_complete: bool
    exclusive_ranks: tuple[int, ...]
    exclusive_band_energies: tuple[float, ...] | None
    harmonic_ratios: tuple[float, ...] | None
    ratios_at_or_above_positive_threshold: int | None
    onset_rise: float | None
    active_residual_before_candidate: float | None
    augmented_residual_after_candidate: float | None
    residual_improvement: float | None
    persistence: float | None
    bounded_claim_lower_bounds: tuple[float, ...] | None
    negative_margins: tuple[float, ...] | None
    pitch_dilution_curve: tuple[tuple[int, float], ...] | None
    positive_partial_condition: bool | None
    positive_onset_condition: bool | None
    positive_residual_condition: bool | None
    negative_partial_condition: bool | None
    negative_onset_condition: bool | None
    negative_residual_condition: bool | None
    decision_reason: str | None
    maximum_sample_read: int


@dataclass(frozen=True)
class _IndependentSpectrum:
    power: Any
    frequencies: Any
    total: float


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_descriptor(value: H28SealedRecordBinding) -> None:
    if type(value) is not H28SealedRecordBinding:
        raise TypeError("H28 recomputer sealed binding type invalid.")
    if value.population_namespace != "H28_CAUSAL_TIMING_SYNTHETIC_V1" or not value.record_identity:
        raise ValueError("H28 recomputer identity binding invalid.")
    identity_path = Path(value.record_identity)
    if identity_path.is_absolute() or ".." in identity_path.parts:
        raise ValueError("H28 recomputer record identity path invalid.")
    population_root = Path(value.population_root)
    if Path(value.population_index_path) != population_root / "population_index.json":
        raise ValueError("H28 recomputer population index path mismatch.")
    if Path(value.record_directory) != population_root / identity_path:
        raise ValueError("H28 recomputer record directory mismatch.")
    for digest, label in (
        (value.population_index_sha256, "population index"),
        (value.population_index_record_sha256, "population index record"),
    ):
        if (type(digest) is not str or len(digest) != 64 or digest.lower() != digest
                or any(ch not in "0123456789abcdef" for ch in digest)):
            raise ValueError(f"H28 recomputer {label} SHA-256 invalid.")
    if type(value.candidate_pitch) is not int or not 24 <= value.candidate_pitch <= 96:
        raise ValueError("H28 recomputer candidate pitch invalid.")
    if (type(value.active_pitches) is not tuple
            or value.active_pitches != tuple(sorted(set(value.active_pitches)))
            or any(type(item) is not int or not 24 <= item <= 96 for item in value.active_pitches)):
        raise ValueError("H28 recomputer active pitch order invalid.")
    if (type(value.proposal_hop_end) is not int or type(value.resolution_hop_end) is not int
            or value.resolution_hop_end - value.proposal_hop_end != 256
            or value.proposal_hop_end < 8447
            or value.proposal_hop_end > _MAXIMUM_PROPOSAL_HOP_END):
        raise ValueError("H28 recomputer causal coordinates invalid.")
    for number, label in ((value.cents, "cents"), (value.inharmonicity, "inharmonicity")):
        if type(number) not in (int, float) or not math.isfinite(float(number)):
            raise ValueError(f"H28 recomputer {label} invalid.")
    if any(1.0 + float(value.inharmonicity) * rank * rank <= 0.0 for rank in range(1, 9)):
        raise ValueError("H28 recomputer inharmonicity invalid.")
    expected = set(value.payload_sha256)
    if expected != {"waveform.f64le", "sample-valid-mask.u8"}:
        raise ValueError("H28 recomputer payload set invalid.")
    if any(type(item) is not str or len(item) != 64 or item.lower() != item
           or any(ch not in "0123456789abcdef" for ch in item)
           for item in value.payload_sha256.values()):
        raise ValueError("H28 recomputer payload digest invalid.")


def _safe_directory(root: Path, record: Path) -> tuple[Path, Path]:
    root_abs, record_abs = root.absolute(), record.absolute()
    root_real, record_real = root_abs.resolve(strict=True), record_abs.resolve(strict=True)
    if root_abs != root_real or record_abs != record_real:
        raise ValueError("H28 recomputer rejects symlinked paths.")
    try:
        record_real.relative_to(root_real)
    except ValueError as exc:
        raise ValueError("H28 recomputer record escapes population root.") from exc
    return root_real, record_real


def _read_record(value: H28SealedRecordBinding) -> tuple[bytes, bytes]:
    _, directory = _safe_directory(Path(value.population_root), Path(value.record_directory))
    names = set(value.payload_sha256)
    if {entry.name for entry in directory.iterdir()} != names:
        raise ValueError("H28 recomputer payload topology mismatch.")
    payloads: dict[str, bytes] = {}
    for name in sorted(names):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.absolute() != path.resolve(strict=True):
            raise ValueError("H28 recomputer payload path invalid.")
        raw = path.read_bytes()
        size = _ROLE_MAJOR_MASK_VALUES if name == "sample-valid-mask.u8" else 8 * _WAVEFORM_SAMPLES
        if len(raw) != size or _digest(raw) != value.payload_sha256[name]:
            raise ValueError("H28 recomputer payload integrity mismatch.")
        payloads[name] = raw
    return payloads["waveform.f64le"], payloads["sample-valid-mask.u8"]


def _decode(np: Any, wave_raw: bytes, mask_raw: bytes) -> tuple[Any, Any]:
    wave = np.frombuffer(wave_raw, dtype="<f8")
    mask = np.frombuffer(mask_raw, dtype=np.uint8)
    if wave.shape != (_WAVEFORM_SAMPLES,) or wave.dtype != np.float64 or not bool(np.all(np.isfinite(wave))):
        raise ValueError("H28 recomputer waveform invalid.")
    if mask.shape != (_ROLE_MAJOR_MASK_VALUES,) or not bool(np.all((mask == 0) | (mask == 1))):
        raise ValueError("H28 recomputer mask invalid.")
    return wave.copy(), mask.reshape(len(_ROLES), _WAVEFORM_SAMPLES).copy()


def _extract(wave: Any, mask: Any, role: str, hop_end: int) -> tuple[Any, bool, int]:
    length = _LENGTH[role]
    end = hop_end - _BACK[role]
    start = end - length + 1
    if start < 0 or end >= wave.size:
        raise ValueError("H28 recomputer causal view unavailable.")
    support = mask[_ROLES.index(role), start:end + 1]
    return wave[start:end + 1].copy(), bool(support.all()), int(support.sum())


def _sample_state(np: Any, role: str, samples: Any, supported: bool) -> tuple[str, bool]:
    if not supported:
        return "INVALID_SUPPORT", False
    zero = not bool(np.any(samples != np.float64(0.0)))
    if zero:
        return {
            "current_short": "INVALID_CURRENT_SHORT_ANALYSIS",
            "previous_short": "VALID_EXACT_ZERO_PREVIOUS_SHORT",
            "current_long": "INVALID_CURRENT_LONG_ANALYSIS",
            "previous_long": "VALID_EXACT_ZERO_PREVIOUS_LONG",
        }[role], True
    return {
        "current_short": "VALID_CURRENT_SHORT_ANALYSIS",
        "previous_short": "VALID_PREVIOUS_SHORT_ANALYSIS",
        "current_long": "VALID_CURRENT_LONG_ANALYSIS",
        "previous_long": "VALID_PREVIOUS_LONG_ANALYSIS",
    }[role], False


def _independent_spectrum(np: Any, samples: Any) -> _IndependentSpectrum:
    length = int(samples.size)
    weighted = np.empty(length, dtype=np.float64)
    denominator = np.float64(0.0)
    for position in range(length):
        window = np.float64(0.5 - 0.5 * math.cos(2.0 * math.pi * position / float(length - 1)))
        weighted[position] = np.float64(samples[position] * window)
        denominator = np.float64(denominator + window * window)
    transformed = np.fft.rfft(weighted, n=8 * length)
    power = np.empty(transformed.size, dtype=np.float64)
    total = np.float64(0.0)
    absolute = np.float64(0.0)
    for bin_index, complex_value in enumerate(transformed):
        item = np.float64((float(complex_value.real) ** 2 + float(complex_value.imag) ** 2) / float(denominator))
        power[bin_index] = item
        if bin_index:
            total = np.float64(total + item)
            absolute = np.float64(absolute + abs(item))
    if not math.isfinite(float(total)) or not float(total) > max(1e-24, 1e-12 * float(absolute)):
        raise ArithmeticError("H28_RECOMPUTER_BELOW_FLOOR")
    frequencies = np.empty(transformed.size, dtype=np.float64)
    for bin_index in range(transformed.size):
        frequencies[bin_index] = np.float64(bin_index * 44100.0 / float(8 * length))
    return _IndependentSpectrum(power, frequencies, float(total))


def _frequency(pitch: int, rank: int, cents: float, b_value: float) -> float:
    base = 440.0 * 2.0 ** ((float(pitch) - 69.0) / 12.0)
    return rank * base * 2.0 ** (cents / 1200.0) * math.sqrt(1.0 + b_value * rank * rank)


def _weights(np: Any, frequencies: Any, target: float) -> Any:
    weights = np.zeros(frequencies.shape, dtype=np.float64)
    for bin_index in range(1, frequencies.size):
        distance = abs(1200.0 * math.log2(float(frequencies[bin_index]) / target))
        weights[bin_index] = np.float64(max(0.0, 1.0 - distance / 35.0))
    return weights


def _energy(np: Any, spectrum: _IndependentSpectrum, target: float, minimum: bool = True) -> tuple[float, Any]:
    weights = _weights(np, spectrum.frequencies, target)
    if minimum and int(np.count_nonzero(weights > 0.0)) < 3:
        raise ArithmeticError("H28_RECOMPUTER_BAND_INVALID")
    value = np.float64(0.0)
    for bin_index in range(1, weights.size):
        value = np.float64(value + spectrum.power[bin_index] * weights[bin_index])
    return float(value), weights


def _exclusive(np: Any, spectrum: _IndependentSpectrum, candidate: int,
               active: tuple[int, ...], cents: float, b_value: float) -> tuple[int, ...]:
    occupied = tuple(_weights(np, spectrum.frequencies, _frequency(pitch, rank, cents, b_value)) > 0.0
                     for pitch in active for rank in range(1, 9))
    ranks: list[int] = []
    for rank in range(1, 9):
        candidate_mask = _weights(np, spectrum.frequencies, _frequency(candidate, rank, cents, b_value)) > 0.0
        if int(np.count_nonzero(candidate_mask)) >= 3 and all(
            not bool(np.any(candidate_mask & item)) for item in occupied
        ):
            ranks.append(rank)
    return tuple(ranks)


def _independent_residual(np: Any, spectrum: _IndependentSpectrum,
                          pitches: tuple[int, ...], cents: float, b_value: float) -> float:
    if not pitches:
        return 1.0
    rows = spectrum.power.size - 1
    observation = np.empty(rows, dtype=np.float64)
    for row in range(rows):
        observation[row] = np.float64(spectrum.power[row + 1] / max(spectrum.total, 1e-24))
    basis = np.empty((rows, len(pitches)), dtype=np.float64)
    for column, pitch in enumerate(pitches):
        raw = np.zeros(spectrum.power.size, dtype=np.float64)
        for rank in range(1, 9):
            kernel = _weights(np, spectrum.frequencies, _frequency(pitch, rank, cents, b_value))
            for bin_index in range(1, raw.size):
                raw[bin_index] = np.float64(raw[bin_index] + kernel[bin_index] / float(rank * rank))
        norm_square = np.float64(0.0)
        for bin_index in range(1, raw.size):
            norm_square = np.float64(norm_square + raw[bin_index] * raw[bin_index])
        norm = math.sqrt(float(norm_square))
        if not math.isfinite(norm) or norm <= 0.0:
            raise ArithmeticError("H28_RECOMPUTER_BASIS_INVALID")
        for row in range(rows):
            basis[row, column] = np.float64(raw[row + 1] / norm)
    coefficients = np.zeros(len(pitches), dtype=np.float64)
    error = observation.copy()
    for _ in range(512):
        for column in range(len(pitches)):
            numerator = np.float64(0.0)
            denominator = np.float64(0.0)
            for row in range(rows):
                numerator = np.float64(numerator + basis[row, column] * error[row])
                denominator = np.float64(denominator + basis[row, column] * basis[row, column])
            if not float(denominator) > 0.0:
                raise ArithmeticError("H28_RECOMPUTER_NNLS_ZERO_COLUMN")
            coefficients[column] = np.float64(max(0.0, float(coefficients[column] + numerator / denominator)))
            for row in range(rows):
                fitted = np.float64(0.0)
                for inner in range(len(pitches)):
                    fitted = np.float64(fitted + basis[row, inner] * coefficients[inner])
                error[row] = np.float64(observation[row] - fitted)
    error_square = np.float64(0.0)
    observation_square = np.float64(0.0)
    for row in range(rows):
        error_square = np.float64(error_square + error[row] * error[row])
        observation_square = np.float64(observation_square + observation[row] * observation[row])
    return float(error_square) / max(float(observation_square), 1e-24)


def _early(value: H28SealedRecordBinding, classes: Mapping[str, str], counts: Mapping[str, int],
           outcome: str, reason: str, kind: str = "NONE") -> H28RecomputedResult:
    return H28RecomputedResult(
        record_identity=value.record_identity,
        validated_payload_sha256=MappingProxyType(dict(value.payload_sha256)),
        role_classifications=MappingProxyType(dict(classes)),
        mask_counts=MappingProxyType(dict(counts)),
        current_short_total_power=None,
        previous_short_total_power=None,
        current_long_total_power=None,
        previous_long_total_power=None,
        outcome=outcome,
        certificate_kind=kind,
        certificate_complete=False,
        exclusive_ranks=(),
        exclusive_band_energies=None,
        harmonic_ratios=None,
        ratios_at_or_above_positive_threshold=None,
        onset_rise=None,
        active_residual_before_candidate=None,
        augmented_residual_after_candidate=None,
        residual_improvement=None,
        persistence=None,
        bounded_claim_lower_bounds=None,
        negative_margins=None,
        pitch_dilution_curve=None,
        positive_partial_condition=None,
        positive_onset_condition=None,
        positive_residual_condition=None,
        negative_partial_condition=None,
        negative_onset_condition=None,
        negative_residual_condition=None,
        decision_reason=reason,
        maximum_sample_read=value.proposal_hop_end,
    )


def _require_record_geometry(
    contract: H28TimingContract, value: H28SealedRecordBinding,
) -> None:
    try:
        fixture_id, horizon_id = value.record_identity.split("/")
    except ValueError as exc:
        raise ValueError("H28 recomputer record identity must contain fixture and horizon.") from exc
    if value.record_identity not in RECORD_ORDER:
        raise ValueError("H28 recomputer record identity is not sealed.")
    horizon = next((item for item in contract.horizons if item.identity == horizon_id), None)
    if horizon is None or (
        value.proposal_hop_end != horizon.proposal_hop_end
        or value.resolution_hop_end != horizon.resolution_hop_end
    ):
        raise ValueError("H28 recomputer identity and causal coordinates differ.")
    if fixture_id not in {"H27-F-P01", "H27-F-N01"}:
        raise ValueError("H28 recomputer fixture identity invalid.")


def run_h28_independent_recomputer(np: Any, capability: H28ScientificCapability,
                                   repository_root: Path,
                                   invocation: H28SealedRecordBinding) -> H28RecomputedResult:
    """Recompute H28 from sealed bytes without receiving engine intermediates."""

    require_h28_scientific_capability(capability)
    require_h28_sealed_record_binding(invocation)
    contract = load_h28_timing_contract(Path(repository_root))
    _require_descriptor(invocation)
    _require_record_geometry(contract, invocation)
    wave_raw, mask_raw = _read_record(invocation)
    wave, masks = _decode(np, wave_raw, mask_raw)
    views: dict[str, Any] = {}
    classes: dict[str, str] = {}
    zeros: dict[str, bool] = {}
    counts: dict[str, int] = {}
    for role in _ROLES:
        samples, support, count = _extract(wave, masks, role, invocation.proposal_hop_end)
        views[role] = samples
        counts[role] = count
        classes[role], zeros[role] = _sample_state(np, role, samples, support)
    if invocation.candidate_pitch in invocation.active_pitches:
        raise ValueError("H28 recomputer fixed fixtures require an inactive candidate.")
    if any(item == "INVALID_SUPPORT" for item in classes.values()):
        return _early(invocation, classes, counts, "AMBIGUOUS", "invalid_or_incomplete_support")
    if zeros["current_short"] or zeros["current_long"]:
        return _early(invocation, classes, counts, "AMBIGUOUS", "invalid_current_exact_zero")
    spectra: dict[str, _IndependentSpectrum | None] = {}
    for role in _ROLES:
        if zeros[role]:
            spectra[role] = None
            continue
        try:
            spectra[role] = _independent_spectrum(np, views[role])
        except ArithmeticError as exc:
            if str(exc) != "H28_RECOMPUTER_BELOW_FLOOR":
                raise
            classes[role] = {
                "current_short": "INVALID_CURRENT_SHORT_ANALYSIS",
                "previous_short": "INVALID_PREVIOUS_SHORT_CONTEXT",
                "current_long": "INVALID_CURRENT_LONG_ANALYSIS",
                "previous_long": "INVALID_PREVIOUS_LONG_CONTEXT",
            }[role]
            return _early(invocation, classes, counts, "AMBIGUOUS", "nonzero_not_above_floor")
    short = spectra["current_short"]
    long = spectra["current_long"]
    assert short is not None and long is not None
    prior_short = 0.0 if spectra["previous_short"] is None else spectra["previous_short"].total
    prior_long = 0.0 if spectra["previous_long"] is None else spectra["previous_long"].total
    cents, b_value = float(invocation.cents), float(invocation.inharmonicity)
    ranks = _exclusive(np, short, invocation.candidate_pitch, invocation.active_pitches, cents, b_value)
    energies = tuple(
        _energy(np, short, _frequency(invocation.candidate_pitch, rank, cents, b_value))[0]
        for rank in ranks
    )
    ratios = tuple(energy / short.total for energy in energies)
    shared = _energy(np, short, _frequency(invocation.candidate_pitch, 1, cents, b_value), False)[0]
    bounds = tuple(0.8 * shared / float(rank * rank) / short.total for rank in ranks)
    margins = tuple(math.inf if ratio == 0.0 else bound / ratio for ratio, bound in zip(ratios, bounds))
    onset = max(0.0, short.total - prior_short) / max(short.total, 1e-24)
    persistence = (long.total - prior_long) / max(long.total, 1e-24)
    baseline = _independent_residual(np, short, invocation.active_pitches, cents, b_value)
    candidate_set = tuple(sorted(set(invocation.active_pitches) | {invocation.candidate_pitch}))
    candidate_residual = _independent_residual(np, short, candidate_set, cents, b_value)
    improvement = max(0.0, baseline - candidate_residual) / max(baseline, 1e-24)
    curve = tuple((pitch, max(0.0, baseline - _independent_residual(
        np, short, tuple(sorted(set(invocation.active_pitches) | {pitch})), cents, b_value
    )) / max(baseline, 1e-24)) for pitch in range(24, 97))
    ratio_count = sum(item >= 0.02 for item in ratios)
    positive_partial = ratio_count >= 2
    positive_onset = onset >= 0.05
    positive_residual = improvement >= 0.1
    bounded = tuple(index for index, item in enumerate(bounds) if math.isfinite(item) and item >= 0.02)
    negative_partial = (len(bounded) >= 2
                        and all(ratios[index] <= 0.002 for index in bounded)
                        and all(margins[index] >= 10.0 for index in bounded))
    negative_onset = onset <= 0.005
    negative_residual = improvement <= 0.001
    positive = positive_partial and positive_onset and positive_residual
    negative = negative_partial and negative_onset and negative_residual
    if positive:
        outcome, reason, kind, complete = "BIRTH_SUPPORTED", "complete_positive_certificate", "POSITIVE", True
    elif negative:
        outcome, reason, kind, complete = "NO_BIRTH", "complete_bounded_negative_certificate", "NEGATIVE", True
    else:
        outcome, reason, kind, complete = "AMBIGUOUS", "certificate_gap_or_conflict", "NONE", False
    return H28RecomputedResult(
        record_identity=invocation.record_identity,
        validated_payload_sha256=MappingProxyType(dict(invocation.payload_sha256)),
        role_classifications=MappingProxyType(dict(classes)),
        mask_counts=MappingProxyType(dict(counts)),
        current_short_total_power=short.total,
        previous_short_total_power=prior_short,
        current_long_total_power=long.total,
        previous_long_total_power=prior_long,
        outcome=outcome,
        certificate_kind=kind,
        certificate_complete=complete,
        exclusive_ranks=ranks,
        exclusive_band_energies=energies,
        harmonic_ratios=ratios,
        ratios_at_or_above_positive_threshold=ratio_count,
        onset_rise=onset,
        active_residual_before_candidate=baseline,
        augmented_residual_after_candidate=candidate_residual,
        residual_improvement=improvement,
        persistence=persistence,
        bounded_claim_lower_bounds=bounds,
        negative_margins=margins,
        pitch_dilution_curve=curve,
        positive_partial_condition=positive_partial,
        positive_onset_condition=positive_onset,
        positive_residual_condition=positive_residual,
        negative_partial_condition=negative_partial,
        negative_onset_condition=negative_onset,
        negative_residual_condition=negative_residual,
        decision_reason=reason,
        maximum_sample_read=invocation.proposal_hop_end,
    )


def compare_h28_engine_and_recomputer(engine_result: object,
                                      recomputed: H28RecomputedResult) -> None:
    """Compare only completed public results; never coerce a mismatch."""

    if type(recomputed) is not H28RecomputedResult:
        raise TypeError("H28 recomputed result type invalid.")
    for field in EXACT_RESULT_FIELDS:
        if getattr(engine_result, field, object()) != getattr(recomputed, field):
            raise RuntimeError(f"H28 engine/recomputer mismatch: {field}.")
    def close(left: object, right: object) -> bool:
        if left is None or right is None:
            return left is right
        if type(left) in (int, float) and type(right) in (int, float):
            a, b = float(left), float(right)
            if math.isinf(a) or math.isinf(b):
                return a == b == math.inf
            return math.isfinite(a) and math.isfinite(b) and abs(a - b) <= 1e-12 + 1e-10 * abs(a)
        if isinstance(left, (tuple, list)) and isinstance(right, (tuple, list)) and len(left) == len(right):
            return all(close(a, b) for a, b in zip(left, right))
        return False

    for field in NUMERIC_RESULT_FIELDS:
        if not close(getattr(engine_result, field, object()), getattr(recomputed, field)):
            raise RuntimeError(f"H28 engine/recomputer mismatch: {field}.")


__all__ = ["H28RecomputedResult", "H28SealedRecordBinding",
           "EXACT_RESULT_FIELDS", "NUMERIC_RESULT_FIELDS",
           "compare_h28_engine_and_recomputer", "run_h28_independent_recomputer"]
