"""Dormant role-aware H27 harmonic-censoring engine.

NumPy is injected only after the unissuable scientific capability is checked.
Importing this module performs no population read, FFT, NNLS, or filesystem
operation.  The implementation is self-contained and does not delegate any
scientific rule to H26/H25.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h27_contract import (
    canonical_h27_record_identities, load_h27_dormant_plan,
)
from .harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, H27SealedRecordBinding,
    H27_SEALED_RECORD_BINDING_FIELDS,
    require_h27_scientific_capability, require_h27_sealed_record_binding,
)


ROLE_ORDER = ("current_short", "previous_short", "current_long", "previous_long")
ROLE_LENGTHS = {"current_short": 4096, "previous_short": 4096,
                "current_long": 8192, "previous_long": 8192}
ROLE_OFFSETS = {"current_short": 0, "previous_short": 256,
                "current_long": 0, "previous_long": 256}
OUTCOMES = ("BIRTH_SUPPORTED", "NO_BIRTH", "AMBIGUOUS", "ALREADY_ACTIVE_HISTORY")
ROLE_CLASSIFICATIONS = (
    "VALID_CURRENT_SHORT_ANALYSIS", "VALID_EXACT_ZERO_PREVIOUS_SHORT",
    "VALID_PREVIOUS_SHORT_ANALYSIS", "VALID_CURRENT_LONG_ANALYSIS",
    "VALID_EXACT_ZERO_PREVIOUS_LONG", "VALID_PREVIOUS_LONG_ANALYSIS",
    "INVALID_CURRENT_SHORT_ANALYSIS", "INVALID_CURRENT_LONG_ANALYSIS",
    "INVALID_PREVIOUS_SHORT_CONTEXT", "INVALID_PREVIOUS_LONG_CONTEXT",
    "INVALID_SUPPORT",
)
EARLY_REASONS = (
    "candidate_active_before_proposal", "invalid_or_incomplete_support",
    "invalid_current_exact_zero", "nonzero_not_above_floor",
    "observation_equivalent_latent_causes", "broken_equivalence_certificate",
    "complete_positive_certificate", "complete_bounded_negative_certificate",
    "certificate_gap_or_conflict",
)
FORBIDDEN_DESCRIPTOR_FIELDS = frozenset({
    "future_audio", "future_labels", "fixture_id", "expected", "family",
    "category", "ground_truth_onset", "latent_label", "post_decision_state",
    "post_emission_rank", "post_emission_selection", "reference_note_id",
    "string_id", "fret", "h25_outcome", "h25_membership",
    "raw_transform_disappearance_index",
})


@dataclass(frozen=True)
class H27Spectrum:
    power: Any
    frequencies_hz: Any
    total_power: float
    view_length: int


@dataclass(frozen=True)
class H27EngineResult:
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


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _finite_float(value: object, label: str) -> float:
    if type(value) not in (int, float):
        raise ValueError(f"H27 {label} must be numeric.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError(f"H27 {label} must be finite.")
    return result


def _validate_invocation(invocation: H27SealedRecordBinding) -> None:
    if type(invocation) is not H27SealedRecordBinding:
        raise TypeError("H27 sealed record binding type invalid.")
    if invocation.population_namespace != "H27_SYNTHETIC_V1":
        raise ValueError("H27 population namespace mismatch.")
    if type(invocation.record_identity) is not str or not invocation.record_identity:
        raise ValueError("H27 record identity invalid.")
    identity_path = Path(invocation.record_identity)
    if identity_path.is_absolute() or ".." in identity_path.parts:
        raise ValueError("H27 record identity path invalid.")
    population_root = Path(invocation.population_root)
    if Path(invocation.population_index_path) != population_root / "population_index.json":
        raise ValueError("H27 sealed population index path mismatch.")
    if Path(invocation.record_directory) != population_root / identity_path:
        raise ValueError("H27 sealed record directory mismatch.")
    for digest, label in (
        (invocation.population_index_sha256, "population index"),
        (invocation.population_index_record_sha256, "population index record"),
    ):
        if (type(digest) is not str or len(digest) != 64 or digest.lower() != digest
                or any(ch not in "0123456789abcdef" for ch in digest)):
            raise ValueError(f"H27 sealed {label} SHA-256 invalid.")
    if type(invocation.candidate_pitch) is not int or not 24 <= invocation.candidate_pitch <= 96:
        raise ValueError("H27 candidate pitch invalid.")
    active = invocation.active_pitches
    if type(active) is not tuple or active != tuple(sorted(set(active))) or any(
        type(pitch) is not int or not 24 <= pitch <= 96 for pitch in active
    ):
        raise ValueError("H27 active pitches must be canonical ascending MIDI.")
    if (
        type(invocation.proposal_hop_end) is not int
        or type(invocation.resolution_hop_end) is not int
        or invocation.resolution_hop_end - invocation.proposal_hop_end != 256
        or invocation.proposal_hop_end < 8191 + 256
        or invocation.proposal_hop_end >= 16640
    ):
        raise ValueError("H27 causal coordinates invalid.")
    cents = _finite_float(invocation.cents, "cents")
    inharmonicity = _finite_float(invocation.inharmonicity, "inharmonicity")
    if any(1.0 + inharmonicity * rank * rank <= 0.0 for rank in range(1, 9)):
        raise ValueError("H27 inharmonicity invalid.")
    del cents
    keys = set(invocation.payload_sha256)
    if keys not in ({"waveform.f64le", "sample-valid-mask.u8"},
                    {"waveform.f64le", "sample-valid-mask.u8", "alternate-waveform.f64le"}):
        raise ValueError("H27 payload set invalid.")
    if any(type(value) is not str or len(value) != 64 or value.lower() != value
           or any(ch not in "0123456789abcdef" for ch in value)
           for value in invocation.payload_sha256.values()):
        raise ValueError("H27 payload SHA-256 invalid.")
    # H27SealedRecordBinding is intentionally slotted and has no __dict__.
    # Validate its closed declared schema directly instead of calling vars(),
    # which would fail before the first scientific test on every real binding.
    if FORBIDDEN_DESCRIPTOR_FIELDS & set(H27_SEALED_RECORD_BINDING_FIELDS):
        raise ValueError("H27 forbidden scientific descriptor field.")


def _contained_regular_file(root: Path, record_dir: Path, name: str) -> Path:
    root_absolute = root.absolute()
    record_absolute = record_dir.absolute()
    root_resolved = root_absolute.resolve(strict=True)
    record_resolved = record_absolute.resolve(strict=True)
    if root_absolute != root_resolved or record_absolute != record_resolved:
        raise ValueError("H27 symlinked population path forbidden.")
    try:
        record_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("H27 record path escapes population root.") from exc
    path = record_resolved / name
    if path.is_symlink() or not path.is_file() or path.absolute() != path.resolve(strict=True):
        raise ValueError("H27 payload must be a non-symlink regular file.")
    return path


def _load_payloads(invocation: H27SealedRecordBinding) -> tuple[bytes, bytes, bytes | None]:
    root = Path(invocation.population_root)
    record_dir = Path(invocation.record_directory)
    root_absolute = root.absolute()
    record_absolute = record_dir.absolute()
    root_resolved = root_absolute.resolve(strict=True)
    record_resolved = record_absolute.resolve(strict=True)
    if root_absolute != root_resolved or record_absolute != record_resolved:
        raise ValueError("H27 symlinked population path forbidden.")
    try:
        record_resolved.relative_to(root_resolved)
    except ValueError as exc:
        raise ValueError("H27 record path escapes population root.") from exc
    expected_names = set(invocation.payload_sha256)
    if {item.name for item in record_resolved.iterdir()} != expected_names:
        raise ValueError("H27 unexpected missing or extra payload.")
    loaded: dict[str, bytes] = {}
    for name in sorted(expected_names):
        raw = _contained_regular_file(root, record_dir, name).read_bytes()
        expected_size = 66560 if name == "sample-valid-mask.u8" else 133120
        if len(raw) != expected_size or _sha256(raw) != invocation.payload_sha256[name]:
            raise ValueError("H27 payload size or SHA-256 mismatch.")
        loaded[name] = raw
    return (loaded["waveform.f64le"], loaded["sample-valid-mask.u8"],
            loaded.get("alternate-waveform.f64le"))


def _decode_payloads(np: Any, waveform_raw: bytes, mask_raw: bytes) -> tuple[Any, Any]:
    waveform = np.frombuffer(waveform_raw, dtype="<f8")
    mask = np.frombuffer(mask_raw, dtype=np.uint8)
    if waveform.shape != (16640,) or waveform.dtype != np.float64 or not bool(np.all(np.isfinite(waveform))):
        raise ValueError("H27 waveform dtype shape or finiteness invalid.")
    if mask.shape != (66560,) or not bool(np.all((mask == 0) | (mask == 1))):
        raise ValueError("H27 role-major mask encoding invalid.")
    return waveform.copy(), mask.reshape(4, 16640).copy()


def _role_view(waveform: Any, masks: Any, *, role: str, hop_end: int) -> tuple[Any, bool, int]:
    index = ROLE_ORDER.index(role)
    length = ROLE_LENGTHS[role]
    end = hop_end - ROLE_OFFSETS[role]
    start = end - length + 1
    if start < 0 or end >= waveform.size:
        raise ValueError("H27 required causal view unavailable; padding forbidden.")
    role_mask = masks[index, start:end + 1]
    return waveform[start:end + 1].copy(), bool(role_mask.all()), int(role_mask.sum())


def _classify_samples(np: Any, view: Any, support: bool, role: str) -> tuple[str, bool]:
    if not support:
        return "INVALID_SUPPORT", False
    exact_zero = not bool(np.any(view != np.float64(0.0)))
    if exact_zero:
        if role == "previous_short":
            return "VALID_EXACT_ZERO_PREVIOUS_SHORT", True
        if role == "previous_long":
            return "VALID_EXACT_ZERO_PREVIOUS_LONG", True
        return ("INVALID_CURRENT_SHORT_ANALYSIS" if role == "current_short"
                else "INVALID_CURRENT_LONG_ANALYSIS"), True
    return {
        "current_short": "VALID_CURRENT_SHORT_ANALYSIS",
        "previous_short": "VALID_PREVIOUS_SHORT_ANALYSIS",
        "current_long": "VALID_CURRENT_LONG_ANALYSIS",
        "previous_long": "VALID_PREVIOUS_LONG_ANALYSIS",
    }[role], False


def _spectrum(np: Any, view: Any) -> H27Spectrum:
    length = int(view.size)
    window = np.empty(length, dtype=np.float64)
    weighted = np.empty(length, dtype=np.float64)
    window_square = np.float64(0.0)
    for index in range(length):
        w = np.float64(0.5 - 0.5 * math.cos(2.0 * math.pi * index / float(length - 1)))
        window[index] = w
        weighted[index] = np.float64(view[index] * w)
        window_square = np.float64(window_square + w * w)
    n_fft = 8 * length
    transformed = np.fft.rfft(weighted, n=n_fft)
    power = np.empty(transformed.size, dtype=np.float64)
    total = np.float64(0.0)
    absolute = np.float64(0.0)
    for index in range(transformed.size):
        value = np.float64((float(transformed[index].real) ** 2
                            + float(transformed[index].imag) ** 2) / float(window_square))
        power[index] = value
        if index > 0:
            total = np.float64(total + value)
            absolute = np.float64(absolute + abs(value))
    if not math.isfinite(float(total)) or not float(total) > max(1e-24, 1e-12 * float(absolute)):
        raise ArithmeticError("H27_NONZERO_BELOW_SPECTRAL_FLOOR")
    frequencies = np.empty(transformed.size, dtype=np.float64)
    for index in range(transformed.size):
        frequencies[index] = np.float64(index * 44100.0 / float(n_fft))
    return H27Spectrum(power, frequencies, float(total), length)


def _f0(pitch: int) -> float:
    return 440.0 * 2.0 ** ((float(pitch) - 69.0) / 12.0)


def _center(pitch: int, rank: int, cents: float, inharmonicity: float) -> float:
    return rank * _f0(pitch) * 2.0 ** (cents / 1200.0) * math.sqrt(1.0 + inharmonicity * rank * rank)


def _kernel(np: Any, frequencies: Any, target: float) -> Any:
    result = np.zeros(frequencies.shape, dtype=np.float64)
    for index in range(1, frequencies.size):
        cents = abs(1200.0 * math.log2(float(frequencies[index]) / target))
        result[index] = np.float64(max(0.0, 1.0 - cents / 35.0))
    return result


def _band(np: Any, spectrum: H27Spectrum, target: float, *, require_three: bool = True) -> tuple[float, Any]:
    kernel = _kernel(np, spectrum.frequencies_hz, target)
    if require_three and int(np.count_nonzero(kernel > 0.0)) < 3:
        raise ArithmeticError("H27_PARTIAL_BAND_INVALID")
    energy = np.float64(0.0)
    for index in range(1, kernel.size):
        energy = np.float64(energy + spectrum.power[index] * kernel[index])
    return float(energy), kernel


def _exclusive_ranks(np: Any, spectrum: H27Spectrum, candidate: int,
                     active: tuple[int, ...], cents: float, b_value: float) -> tuple[int, ...]:
    active_masks = tuple(
        _kernel(np, spectrum.frequencies_hz, _center(pitch, rank, cents, b_value)) > 0.0
        for pitch in active for rank in range(1, 9)
    )
    result: list[int] = []
    for rank in range(1, 9):
        mask = _kernel(np, spectrum.frequencies_hz, _center(candidate, rank, cents, b_value)) > 0.0
        if int(np.count_nonzero(mask)) >= 3 and all(not bool(np.any(mask & other)) for other in active_masks):
            result.append(rank)
    return tuple(result)


def _basis(np: Any, spectrum: H27Spectrum, pitches: tuple[int, ...], cents: float, b_value: float) -> Any:
    matrix = np.empty((spectrum.power.size - 1, len(pitches)), dtype=np.float64)
    for column, pitch in enumerate(pitches):
        values = np.zeros(spectrum.power.size, dtype=np.float64)
        for rank in range(1, 9):
            kernel = _kernel(np, spectrum.frequencies_hz, _center(pitch, rank, cents, b_value))
            for index in range(1, kernel.size):
                values[index] = np.float64(values[index] + kernel[index] / float(rank * rank))
        square = np.float64(0.0)
        for index in range(1, values.size):
            square = np.float64(square + values[index] * values[index])
        norm = math.sqrt(float(square))
        if not math.isfinite(norm) or norm <= 0.0:
            raise ArithmeticError("H27_HARMONIC_BASIS_INVALID")
        for index in range(1, values.size):
            matrix[index - 1, column] = np.float64(values[index] / norm)
    return matrix


def _residual(np: Any, spectrum: H27Spectrum, pitches: tuple[int, ...], cents: float, b_value: float) -> float:
    if not pitches:
        return 1.0
    y = np.empty(spectrum.power.size - 1, dtype=np.float64)
    for index in range(1, spectrum.power.size):
        y[index - 1] = np.float64(spectrum.power[index] / max(spectrum.total_power, 1e-24))
    basis = _basis(np, spectrum, pitches, cents, b_value)
    coefficients = np.zeros(basis.shape[1], dtype=np.float64)
    residual = y.copy()
    for _ in range(512):
        for column in range(basis.shape[1]):
            numerator = np.float64(0.0)
            denominator = np.float64(0.0)
            for row in range(basis.shape[0]):
                numerator = np.float64(numerator + basis[row, column] * residual[row])
                denominator = np.float64(denominator + basis[row, column] * basis[row, column])
            if not float(denominator) > 0.0:
                raise ArithmeticError("H27_NNLS_ZERO_COLUMN")
            coefficients[column] = np.float64(max(0.0, float(coefficients[column] + numerator / denominator)))
            for row in range(basis.shape[0]):
                reconstructed = np.float64(0.0)
                for inner in range(basis.shape[1]):
                    reconstructed = np.float64(reconstructed + basis[row, inner] * coefficients[inner])
                residual[row] = np.float64(y[row] - reconstructed)
    residual_square = np.float64(0.0)
    target_square = np.float64(0.0)
    for row in range(y.size):
        residual_square = np.float64(residual_square + residual[row] * residual[row])
        target_square = np.float64(target_square + y[row] * y[row])
    return float(residual_square) / max(float(target_square), 1e-24)


def _early_result(invocation: H27SealedRecordBinding, shas: Mapping[str, str],
                  classes: Mapping[str, str], counts: Mapping[str, int],
                  outcome: str, reason: str, kind: str = "NONE") -> H27EngineResult:
    return H27EngineResult(invocation.record_identity, MappingProxyType(dict(shas)),
                           MappingProxyType(dict(classes)), MappingProxyType(dict(counts)),
                           outcome, kind, kind in {"EQUIVALENCE", "ACTIVE_HISTORY"}, (), None,
                           None, None, None, None, None, None, reason,
                           invocation.proposal_hop_end)


def run_h27_engine(np: Any, capability: H27ScientificCapability,
                   repository_root: Path, invocation: H27SealedRecordBinding) -> H27EngineResult:
    """Execute H27 only after a future separately authorized capability."""

    require_h27_scientific_capability(capability)
    require_h27_sealed_record_binding(invocation)
    plan = load_h27_dormant_plan(Path(repository_root))
    _validate_invocation(invocation)
    if invocation.record_identity not in canonical_h27_record_identities(plan):
        raise ValueError("H27 record identity is not in the sealed fixed order.")
    waveform_raw, mask_raw, alternate_raw = _load_payloads(invocation)
    waveform, masks = _decode_payloads(np, waveform_raw, mask_raw)
    if alternate_raw is not None:
        alternate = np.frombuffer(alternate_raw, dtype="<f8")
        if alternate.shape != (16640,) or alternate.dtype != np.float64 or not bool(np.all(np.isfinite(alternate))):
            raise ValueError("H27 alternate waveform dtype shape or finiteness invalid.")
    views: dict[str, Any] = {}
    classes: dict[str, str] = {}
    exact_zero: dict[str, bool] = {}
    counts: dict[str, int] = {}
    for role in ROLE_ORDER:
        view, support, count = _role_view(waveform, masks, role=role, hop_end=invocation.proposal_hop_end)
        views[role] = view
        counts[role] = count
        classes[role], exact_zero[role] = _classify_samples(np, view, support, role)
    if invocation.candidate_pitch in invocation.active_pitches:
        return _early_result(invocation, invocation.payload_sha256, classes, counts,
                             "ALREADY_ACTIVE_HISTORY", "candidate_active_before_proposal", "ACTIVE_HISTORY")
    if any(value == "INVALID_SUPPORT" for value in classes.values()):
        return _early_result(invocation, invocation.payload_sha256, classes, counts,
                             "AMBIGUOUS", "invalid_or_incomplete_support")
    if exact_zero["current_short"] or exact_zero["current_long"]:
        return _early_result(invocation, invocation.payload_sha256, classes, counts,
                             "AMBIGUOUS", "invalid_current_exact_zero")
    if alternate_raw is not None:
        equivalent = waveform_raw == alternate_raw and bool(np.any(waveform != np.float64(0.0)))
        return _early_result(invocation, invocation.payload_sha256, classes, counts, "AMBIGUOUS",
                             "observation_equivalent_latent_causes" if equivalent
                             else "broken_equivalence_certificate", "EQUIVALENCE" if equivalent else "NONE")
    spectra: dict[str, H27Spectrum | None] = {}
    for role in ROLE_ORDER:
        if exact_zero[role]:
            spectra[role] = None
            continue
        try:
            spectra[role] = _spectrum(np, views[role])
        except ArithmeticError as exc:
            if str(exc) != "H27_NONZERO_BELOW_SPECTRAL_FLOOR":
                raise
            classes[role] = {
                "current_short": "INVALID_CURRENT_SHORT_ANALYSIS",
                "previous_short": "INVALID_PREVIOUS_SHORT_CONTEXT",
                "current_long": "INVALID_CURRENT_LONG_ANALYSIS",
                "previous_long": "INVALID_PREVIOUS_LONG_CONTEXT",
            }[role]
            return _early_result(invocation, invocation.payload_sha256, classes, counts,
                                 "AMBIGUOUS", "nonzero_not_above_floor")
    current_short = spectra["current_short"]
    current_long = spectra["current_long"]
    assert current_short is not None and current_long is not None
    previous_short_total = 0.0 if spectra["previous_short"] is None else spectra["previous_short"].total_power
    previous_long_total = 0.0 if spectra["previous_long"] is None else spectra["previous_long"].total_power
    cents, b_value = float(invocation.cents), float(invocation.inharmonicity)
    exclusive = _exclusive_ranks(np, current_short, invocation.candidate_pitch,
                                 invocation.active_pitches, cents, b_value)
    energies = tuple(_band(np, current_short, _center(invocation.candidate_pitch, rank, cents, b_value))[0]
                     for rank in exclusive)
    ratios = tuple(value / current_short.total_power for value in energies)
    shared = _band(np, current_short, _center(invocation.candidate_pitch, 1, cents, b_value),
                   require_three=False)[0]
    bounds = tuple(0.8 * shared / float(rank * rank) / current_short.total_power for rank in exclusive)
    margins = tuple(math.inf if ratio == 0.0 else bound / ratio
                    for ratio, bound in zip(ratios, bounds))
    onset = max(0.0, current_short.total_power - previous_short_total) / max(current_short.total_power, 1e-24)
    persistence = (current_long.total_power - previous_long_total) / max(current_long.total_power, 1e-24)
    active_residual = _residual(np, current_short, invocation.active_pitches, cents, b_value)
    augmented = tuple(sorted(set(invocation.active_pitches) | {invocation.candidate_pitch}))
    augmented_residual = _residual(np, current_short, augmented, cents, b_value)
    improvement = max(0.0, active_residual - augmented_residual) / max(active_residual, 1e-24)
    curve = tuple((pitch, max(0.0, active_residual - _residual(
        np, current_short, tuple(sorted(set(invocation.active_pitches) | {pitch})), cents, b_value
    )) / max(active_residual, 1e-24)) for pitch in range(24, 97))
    positive = sum(value >= 0.02 for value in ratios) >= 2 and onset >= 0.05 and improvement >= 0.1
    bounded = tuple(index for index, value in enumerate(bounds) if math.isfinite(value) and value >= 0.02)
    negative = (len(bounded) >= 2 and all(ratios[index] <= 0.002 for index in bounded)
                and all(margins[index] >= 10.0 for index in bounded)
                and onset <= 0.005 and improvement <= 0.001)
    if positive:
        outcome, reason, kind, complete = "BIRTH_SUPPORTED", "complete_positive_certificate", "POSITIVE", True
    elif negative:
        outcome, reason, kind, complete = "NO_BIRTH", "complete_bounded_negative_certificate", "NEGATIVE", True
    else:
        outcome, reason, kind, complete = "AMBIGUOUS", "certificate_gap_or_conflict", "NONE", False
    return H27EngineResult(
        invocation.record_identity, MappingProxyType(dict(invocation.payload_sha256)),
        MappingProxyType(dict(classes)), MappingProxyType(dict(counts)),
        outcome, kind, complete, exclusive, ratios, onset, improvement, persistence,
        bounds, margins, curve, reason, invocation.proposal_hop_end,
    )


__all__ = ["H27EngineResult", "H27SealedRecordBinding", "H27ScientificCapability",
           "run_h27_engine"]
