"""Independent dormant recomputer for H27 sealed records.

This module intentionally imports no H27 engine symbol and duplicates the
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

from .harmonic_censoring_h27_contract import (
    canonical_h27_record_identities, load_h27_dormant_plan,
)
from .harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, require_h27_scientific_capability,
)


_ROLES = ("current_short", "previous_short", "current_long", "previous_long")
_LENGTH = {"current_short": 4096, "previous_short": 4096,
           "current_long": 8192, "previous_long": 8192}
_BACK = {"current_short": 0, "previous_short": 256,
         "current_long": 0, "previous_long": 256}


@dataclass(frozen=True)
class H27RecomputerInvocation:
    population_root: Path
    record_directory: Path
    record_identity: str
    population_namespace: str
    payload_sha256: Mapping[str, str]
    candidate_pitch: int
    active_pitches: tuple[int, ...]
    proposal_hop_end: int
    resolution_hop_end: int
    cents: float = 0.0
    inharmonicity: float = 0.0

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload_sha256", MappingProxyType(dict(self.payload_sha256)))


@dataclass(frozen=True)
class H27RecomputedResult:
    record_identity: str
    validated_payload_sha256: Mapping[str, str]
    role_classifications: Mapping[str, str]
    mask_counts: Mapping[str, int]
    outcome: str
    certificate_kind: str
    certificate_complete: bool
    exclusive_partial_membership: tuple[int, ...]
    exclusive_energy_ratios: tuple[float, ...] | None
    onset_rise: float | None
    residual_improvement: float | None
    persistence: float | None
    bounded_claim_lower_bounds: tuple[float, ...] | None
    negative_margins: tuple[float, ...] | None
    pitch_dilution_curve: tuple[tuple[int, float], ...] | None
    early_resolution_reason: str | None
    maximum_sample_read: int


@dataclass(frozen=True)
class _IndependentSpectrum:
    power: Any
    frequencies: Any
    total: float


def _digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _require_descriptor(value: H27RecomputerInvocation) -> None:
    if type(value) is not H27RecomputerInvocation:
        raise TypeError("H27 recomputer descriptor type invalid.")
    if value.population_namespace != "H27_SYNTHETIC_V1" or not value.record_identity:
        raise ValueError("H27 recomputer identity binding invalid.")
    if type(value.candidate_pitch) is not int or not 24 <= value.candidate_pitch <= 96:
        raise ValueError("H27 recomputer candidate pitch invalid.")
    if (type(value.active_pitches) is not tuple
            or value.active_pitches != tuple(sorted(set(value.active_pitches)))
            or any(type(item) is not int or not 24 <= item <= 96 for item in value.active_pitches)):
        raise ValueError("H27 recomputer active pitch order invalid.")
    if (type(value.proposal_hop_end) is not int or type(value.resolution_hop_end) is not int
            or value.resolution_hop_end - value.proposal_hop_end != 256
            or value.proposal_hop_end < 8447 or value.proposal_hop_end >= 16640):
        raise ValueError("H27 recomputer causal coordinates invalid.")
    for number, label in ((value.cents, "cents"), (value.inharmonicity, "inharmonicity")):
        if type(number) not in (int, float) or not math.isfinite(float(number)):
            raise ValueError(f"H27 recomputer {label} invalid.")
    if any(1.0 + float(value.inharmonicity) * rank * rank <= 0.0 for rank in range(1, 9)):
        raise ValueError("H27 recomputer inharmonicity invalid.")
    expected = set(value.payload_sha256)
    if expected not in ({"waveform.f64le", "sample-valid-mask.u8"},
                        {"waveform.f64le", "sample-valid-mask.u8", "alternate-waveform.f64le"}):
        raise ValueError("H27 recomputer payload set invalid.")
    if any(type(item) is not str or len(item) != 64 or item.lower() != item
           or any(ch not in "0123456789abcdef" for ch in item)
           for item in value.payload_sha256.values()):
        raise ValueError("H27 recomputer payload digest invalid.")


def _safe_directory(root: Path, record: Path) -> tuple[Path, Path]:
    root_abs, record_abs = root.absolute(), record.absolute()
    root_real, record_real = root_abs.resolve(strict=True), record_abs.resolve(strict=True)
    if root_abs != root_real or record_abs != record_real:
        raise ValueError("H27 recomputer rejects symlinked paths.")
    try:
        record_real.relative_to(root_real)
    except ValueError as exc:
        raise ValueError("H27 recomputer record escapes population root.") from exc
    return root_real, record_real


def _read_record(value: H27RecomputerInvocation) -> tuple[bytes, bytes, bytes | None]:
    _, directory = _safe_directory(Path(value.population_root), Path(value.record_directory))
    names = set(value.payload_sha256)
    if {entry.name for entry in directory.iterdir()} != names:
        raise ValueError("H27 recomputer payload topology mismatch.")
    payloads: dict[str, bytes] = {}
    for name in sorted(names):
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.absolute() != path.resolve(strict=True):
            raise ValueError("H27 recomputer payload path invalid.")
        raw = path.read_bytes()
        size = 66560 if name == "sample-valid-mask.u8" else 133120
        if len(raw) != size or _digest(raw) != value.payload_sha256[name]:
            raise ValueError("H27 recomputer payload integrity mismatch.")
        payloads[name] = raw
    return payloads["waveform.f64le"], payloads["sample-valid-mask.u8"], payloads.get("alternate-waveform.f64le")


def _decode(np: Any, wave_raw: bytes, mask_raw: bytes) -> tuple[Any, Any]:
    wave = np.frombuffer(wave_raw, dtype="<f8")
    mask = np.frombuffer(mask_raw, dtype=np.uint8)
    if wave.shape != (16640,) or wave.dtype != np.float64 or not bool(np.all(np.isfinite(wave))):
        raise ValueError("H27 recomputer waveform invalid.")
    if mask.shape != (66560,) or not bool(np.all((mask == 0) | (mask == 1))):
        raise ValueError("H27 recomputer mask invalid.")
    return wave.copy(), mask.reshape(4, 16640).copy()


def _extract(wave: Any, mask: Any, role: str, hop_end: int) -> tuple[Any, bool, int]:
    length = _LENGTH[role]
    end = hop_end - _BACK[role]
    start = end - length + 1
    if start < 0 or end >= wave.size:
        raise ValueError("H27 recomputer causal view unavailable.")
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
        raise ArithmeticError("H27_RECOMPUTER_BELOW_FLOOR")
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
        raise ArithmeticError("H27_RECOMPUTER_BAND_INVALID")
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
            raise ArithmeticError("H27_RECOMPUTER_BASIS_INVALID")
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
                raise ArithmeticError("H27_RECOMPUTER_NNLS_ZERO_COLUMN")
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


def _early(value: H27RecomputerInvocation, classes: Mapping[str, str], counts: Mapping[str, int],
           outcome: str, reason: str, kind: str = "NONE") -> H27RecomputedResult:
    return H27RecomputedResult(value.record_identity, MappingProxyType(dict(value.payload_sha256)),
                               MappingProxyType(dict(classes)), MappingProxyType(dict(counts)),
                               outcome, kind, kind in {"EQUIVALENCE", "ACTIVE_HISTORY"}, (), None,
                               None, None, None, None, None, None, reason, value.proposal_hop_end)


def run_h27_independent_recomputer(np: Any, capability: H27ScientificCapability,
                                   repository_root: Path,
                                   invocation: H27RecomputerInvocation) -> H27RecomputedResult:
    """Recompute H27 from sealed bytes without receiving engine intermediates."""

    require_h27_scientific_capability(capability)
    plan = load_h27_dormant_plan(Path(repository_root))
    _require_descriptor(invocation)
    if invocation.record_identity not in canonical_h27_record_identities(plan):
        raise ValueError("H27 recomputer record identity is not sealed.")
    wave_raw, mask_raw, alternate_raw = _read_record(invocation)
    wave, masks = _decode(np, wave_raw, mask_raw)
    if alternate_raw is not None:
        alternate = np.frombuffer(alternate_raw, dtype="<f8")
        if alternate.shape != (16640,) or alternate.dtype != np.float64 or not bool(np.all(np.isfinite(alternate))):
            raise ValueError("H27 recomputer alternate waveform invalid.")
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
        return _early(invocation, classes, counts, "ALREADY_ACTIVE_HISTORY", "candidate_active_before_proposal", "ACTIVE_HISTORY")
    if any(item == "INVALID_SUPPORT" for item in classes.values()):
        return _early(invocation, classes, counts, "AMBIGUOUS", "invalid_or_incomplete_support")
    if zeros["current_short"] or zeros["current_long"]:
        return _early(invocation, classes, counts, "AMBIGUOUS", "invalid_current_exact_zero")
    if alternate_raw is not None:
        equivalent = wave_raw == alternate_raw and bool(np.any(wave != np.float64(0.0)))
        return _early(invocation, classes, counts, "AMBIGUOUS",
                      "observation_equivalent_latent_causes" if equivalent else "broken_equivalence_certificate",
                      "EQUIVALENCE" if equivalent else "NONE")
    spectra: dict[str, _IndependentSpectrum | None] = {}
    for role in _ROLES:
        if zeros[role]:
            spectra[role] = None
            continue
        try:
            spectra[role] = _independent_spectrum(np, views[role])
        except ArithmeticError as exc:
            if str(exc) != "H27_RECOMPUTER_BELOW_FLOOR":
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
    ratios = tuple(_energy(np, short, _frequency(invocation.candidate_pitch, rank, cents, b_value))[0] / short.total
                   for rank in ranks)
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
    positive = sum(item >= 0.02 for item in ratios) >= 2 and onset >= 0.05 and improvement >= 0.1
    bounded = tuple(index for index, item in enumerate(bounds) if math.isfinite(item) and item >= 0.02)
    negative = (len(bounded) >= 2 and all(ratios[index] <= 0.002 for index in bounded)
                and all(margins[index] >= 10.0 for index in bounded)
                and onset <= 0.005 and improvement <= 0.001)
    if positive:
        outcome, reason, kind, complete = "BIRTH_SUPPORTED", "complete_positive_certificate", "POSITIVE", True
    elif negative:
        outcome, reason, kind, complete = "NO_BIRTH", "complete_bounded_negative_certificate", "NEGATIVE", True
    else:
        outcome, reason, kind, complete = "AMBIGUOUS", "certificate_gap_or_conflict", "NONE", False
    return H27RecomputedResult(
        invocation.record_identity, MappingProxyType(dict(invocation.payload_sha256)),
        MappingProxyType(dict(classes)), MappingProxyType(dict(counts)), outcome, kind,
        complete, ranks, ratios, onset, improvement, persistence, bounds, margins, curve, reason,
        invocation.proposal_hop_end,
    )


def compare_h27_engine_and_recomputer(engine_result: object,
                                      recomputed: H27RecomputedResult) -> None:
    """Compare only completed public results; never coerce a mismatch."""

    if type(recomputed) is not H27RecomputedResult:
        raise TypeError("H27 recomputed result type invalid.")
    exact_fields = ("record_identity", "validated_payload_sha256", "role_classifications",
                    "mask_counts", "outcome", "certificate_kind", "certificate_complete",
                    "exclusive_partial_membership", "early_resolution_reason", "maximum_sample_read")
    for field in exact_fields:
        if getattr(engine_result, field, object()) != getattr(recomputed, field):
            raise RuntimeError(f"H27 engine/recomputer mismatch: {field}.")
    numeric_fields = ("exclusive_energy_ratios", "onset_rise", "residual_improvement",
                      "persistence", "bounded_claim_lower_bounds", "negative_margins",
                      "pitch_dilution_curve")

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

    for field in numeric_fields:
        if not close(getattr(engine_result, field, object()), getattr(recomputed, field)):
            raise RuntimeError(f"H27 engine/recomputer mismatch: {field}.")


__all__ = ["H27RecomputedResult", "H27RecomputerInvocation",
           "compare_h27_engine_and_recomputer", "run_h27_independent_recomputer"]
