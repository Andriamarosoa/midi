"""Dormant numerical kernels and four-outcome resolver for H26.

NumPy is injected by callers and never imported at module import time.  The
public fixture evidence boundary requires an unissuable capability; pure
kernels accept only explicit operands so they can be tested on non-H26 toy data.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import itertools
import math
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h26_contract import (
    H26DormantPlan, h26_f0_hz, h26_partial_center_hz,
)


class H26ScientificCapability:
    """Placeholder type; no instance can exist in the dormant stack."""

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object) -> "H26ScientificCapability":
        del cls, args, kwargs
        raise PermissionError("H26 scientific capability has no issuer.")


@dataclass(frozen=True)
class H26Spectrum:
    power: Any
    frequencies_hz: Any
    total_power: float
    view_length: int
    n_fft: int


@dataclass(frozen=True)
class H26NumericalPolicy:
    sample_rate_hz: int
    hop_samples: int
    short_view_samples: int
    long_view_samples: int
    fft_padding_factor: int
    partial_half_width_cents: float
    minimum_valid_bins: int
    harmonic_ranks: tuple[int, ...]
    nnls_sweeps: int
    power_floor: float
    lower_envelope_factor: float

    @classmethod
    def from_plan(cls, plan: H26DormantPlan) -> "H26NumericalPolicy":
        causal = plan.contract["causal_contract"]
        measurements = plan.contract["measurement_definitions"]
        spectrum = measurements["spectrum"]
        kernel = measurements["partial_band_kernel"]
        basis = measurements["harmonic_basis"]
        nnls = measurements["nnls_fixed_v1"]
        timbre = measurements["global_synthetic_timbre_v1"]
        expected_strings = {
            spectrum.get("zero_padding"): "n_fft=8*L",
            spectrum.get("frequency_hz"): "44100/(8*L)",
            basis.get("column_formula"): "h=1..8",
            nnls.get("algorithm"): "exactly 512 cyclic coordinate-descent sweeps",
        }
        if any(fragment not in str(value) for value, fragment in expected_strings.items()):
            raise ValueError("H26 numerical algorithm definition drift.")
        if nnls.get("no_early_stop") is not True:
            raise ValueError("H26 NNLS early-stop contract drift.")
        return cls(
            sample_rate_hz=int(causal["sample_rate_hz"]),
            hop_samples=int(causal["hop_samples"]),
            short_view_samples=int(causal["short_view_samples"]),
            long_view_samples=int(causal["long_view_samples"]),
            fft_padding_factor=8,
            partial_half_width_cents=float(kernel["half_width_cents"]),
            minimum_valid_bins=int(kernel["minimum_valid_bins"]),
            harmonic_ranks=tuple(range(1, 9)),
            nnls_sweeps=512,
            power_floor=1e-24,
            lower_envelope_factor=float(timbre["lower_envelope_factor"]),
        )


@dataclass(frozen=True)
class H26ResidualResult:
    residual: float
    coefficients: tuple[float, ...]


@dataclass(frozen=True)
class H26Measurements:
    candidate_active: bool
    support_valid: bool
    observation_equivalent: bool
    exclusive_partial_ranks: tuple[int, ...]
    exclusive_energy_ratios: tuple[float, ...]
    onset_rise: float
    active_only_residual_improvement: float
    candidate_lower_bounds: tuple[float, ...]
    negative_margin_ratios: tuple[float, ...]
    long_window_persistence: float
    maximum_sample_read: int
    pitch_dilution_curve: tuple[tuple[int, float], ...] = ()


@dataclass(frozen=True)
class H26RawOperands:
    candidate_active: bool
    support_valid: bool
    observation_equivalent: bool
    exclusive_partial_ranks: tuple[int, ...]
    exclusive_band_energies: tuple[float, ...]
    shared_band_energy: float
    current_short_total_power: float
    previous_short_total_power: float
    active_only_residual: float
    active_plus_candidate_residual: float
    current_long_total_power: float
    previous_long_total_power: float
    maximum_sample_read: int
    pitch_dilution_residual_triplets: tuple[tuple[int, float, float], ...]


@dataclass(frozen=True)
class H26Resolution:
    outcome: str
    reason: str
    positive_certificate_complete: bool
    negative_certificate_complete: bool


@dataclass(frozen=True)
class H26EvidenceRecord:
    fixture_id: str
    measurement: Mapping[str, object]
    resolution: Mapping[str, object]
    operands: Mapping[str, object]


@dataclass(frozen=True)
class H26CausalProposal:
    candidate_pitch: int
    proposal_hop_end: int
    resolution_hop_end: int
    state: str = "PENDING_NEW"


def begin_h26_causal_proposal(
    policy: H26NumericalPolicy, *, candidate_pitch: int,
    proposal_hop_end: int, resolution_hop_end: int,
) -> H26CausalProposal:
    if type(candidate_pitch) is not int or not 0 <= candidate_pitch <= 127:
        raise ValueError("H26 proposal pitch invalid.")
    if resolution_hop_end - proposal_hop_end != policy.hop_samples:
        raise ValueError("H26 resolution must occur exactly one hop after proposal.")
    return H26CausalProposal(candidate_pitch, proposal_hop_end, resolution_hop_end)


def finish_h26_causal_proposal(
    proposal: H26CausalProposal, resolution: H26Resolution,
    *, maximum_sample_read: int,
) -> str:
    if proposal.state != "PENDING_NEW":
        raise ValueError("H26 resolution requires PENDING_NEW state.")
    if maximum_sample_read > proposal.resolution_hop_end:
        raise ValueError("H26 resolution read beyond its causal boundary.")
    if resolution.outcome not in {"BIRTH_SUPPORTED", "NO_BIRTH", "AMBIGUOUS", "ALREADY_ACTIVE_HISTORY"}:
        raise ValueError("H26 resolution outcome invalid.")
    return resolution.outcome


def f0_hz(pitch: int) -> float:
    return h26_f0_hz(pitch)


def partial_center_hz(
    pitch: int, rank: int, *, cents: float, inharmonicity: float,
) -> float:
    return h26_partial_center_hz(
        pitch, rank, cents=cents, inharmonicity=inharmonicity,
    )


def nonzero_observations_are_byte_equivalent(
    np: Any, primary: Any, alternate: Any,
) -> bool:
    left = np.asarray(primary)
    right = np.asarray(alternate)
    if (
        left.dtype != np.float64 or right.dtype != np.float64
        or left.ndim != 1 or right.shape != left.shape
        or not np.all(np.isfinite(left)) or not np.all(np.isfinite(right))
    ):
        raise ValueError("H26 equivalence operands invalid.")
    return (
        left.astype("<f8", copy=False).tobytes(order="C")
        == right.astype("<f8", copy=False).tobytes(order="C")
        and bool(np.any(left != 0.0))
    )


def extract_causal_view(np: Any, waveform: Any, *, hop_end: int, length: int) -> Any:
    array = np.asarray(waveform)
    if array.ndim != 1 or array.dtype != np.float64:
        raise ValueError("H26 waveform must be one-dimensional float64.")
    start = int(hop_end) - int(length) + 1
    if type(length) is not int or length <= 0 or start < 0 or hop_end >= array.size:
        raise ValueError("H26 required causal view is unavailable; padding forbidden.")
    view = array[start : hop_end + 1]
    if view.shape != (length,) or not np.all(np.isfinite(view)):
        raise ValueError("H26 causal view invalid.")
    return view.copy()


def causal_spectrum(np: Any, view: Any, *, policy: H26NumericalPolicy) -> H26Spectrum:
    samples = np.asarray(view)
    if samples.dtype != np.float64 or samples.ndim != 1 or samples.size not in {
        policy.short_view_samples, policy.long_view_samples,
    }:
        raise ValueError("H26 spectrum view shape/dtype mismatch.")
    length = int(samples.size)
    window = np.empty(length, dtype=np.float64)
    denominator = float(length - 1)
    window_square = np.float64(0.0)
    weighted = np.empty(length, dtype=np.float64)
    for index in range(length):
        value = np.float64(0.5 - 0.5 * math.cos(2.0 * math.pi * index / denominator))
        window[index] = value
        weighted[index] = np.float64(samples[index] * value)
        window_square = np.float64(window_square + value * value)
    n_fft = policy.fft_padding_factor * length
    transformed = np.fft.rfft(weighted, n=n_fft)
    power = np.empty(transformed.size, dtype=np.float64)
    total = np.float64(0.0)
    absolute = np.float64(0.0)
    for index in range(transformed.size):
        value = np.float64(
            (float(transformed[index].real) ** 2 + float(transformed[index].imag) ** 2)
            / float(window_square)
        )
        power[index] = value
        if index > 0:
            total = np.float64(total + value)
            absolute = np.float64(absolute + abs(value))
    if not math.isfinite(float(total)) or not float(total) > max(policy.power_floor, 1e-12 * float(absolute)):
        raise ValueError("H26 spectrum total power invalid.")
    frequencies = np.empty(transformed.size, dtype=np.float64)
    for index in range(transformed.size):
        frequencies[index] = np.float64(index * float(policy.sample_rate_hz) / float(n_fft))
    return H26Spectrum(power, frequencies, float(total), length, n_fft)


def triangular_cents_kernel(
    np: Any, frequencies_hz: Any, target_hz: float, *, policy: H26NumericalPolicy,
) -> Any:
    frequencies = np.asarray(frequencies_hz)
    if frequencies.ndim != 1 or frequencies.dtype != np.float64 or target_hz <= 0.0:
        raise ValueError("H26 kernel operands invalid.")
    kernel = np.zeros(frequencies.shape, dtype=np.float64)
    for index in range(1, frequencies.size):
        cents = abs(1200.0 * math.log2(float(frequencies[index]) / float(target_hz)))
        kernel[index] = np.float64(max(0.0, 1.0 - cents / policy.partial_half_width_cents))
    return kernel


def band_energy(
    np: Any, spectrum: H26Spectrum, target_hz: float,
    *, policy: H26NumericalPolicy, require_minimum_bins: bool = True,
) -> tuple[float, Any]:
    kernel = triangular_cents_kernel(np, spectrum.frequencies_hz, target_hz, policy=policy)
    if require_minimum_bins and int(np.count_nonzero(kernel > 0.0)) < policy.minimum_valid_bins:
        raise ValueError("H26 partial band has fewer than three valid bins.")
    energy = np.float64(0.0)
    for index in range(1, kernel.size):
        energy = np.float64(energy + spectrum.power[index] * kernel[index])
    return float(energy), kernel


def exclusive_partial_ranks(
    np: Any, spectrum: H26Spectrum, *, candidate_pitch: int,
    active_pitches: Sequence[int], candidate_ranks: Sequence[int] = tuple(range(1, 9)),
    policy: H26NumericalPolicy, cents: float = 0.0, inharmonicity: float = 0.0,
) -> tuple[int, ...]:
    active_masks: list[Any] = []
    for pitch in sorted(active_pitches):
        for rank in policy.harmonic_ranks:
            center = partial_center_hz(pitch, rank, cents=cents, inharmonicity=inharmonicity)
            active_masks.append(triangular_cents_kernel(np, spectrum.frequencies_hz, center, policy=policy) > 0.0)
    exclusive: list[int] = []
    for rank in sorted(candidate_ranks):
        center = partial_center_hz(candidate_pitch, rank, cents=cents, inharmonicity=inharmonicity)
        candidate_mask = triangular_cents_kernel(np, spectrum.frequencies_hz, center, policy=policy) > 0.0
        if int(np.count_nonzero(candidate_mask)) < policy.minimum_valid_bins:
            continue
        if all(not bool(np.any(candidate_mask & active_mask)) for active_mask in active_masks):
            exclusive.append(rank)
    return tuple(exclusive)


def harmonic_basis(
    np: Any, spectrum: H26Spectrum, pitches: Sequence[int],
    *, policy: H26NumericalPolicy, cents: float = 0.0, inharmonicity: float = 0.0,
) -> Any:
    if spectrum.view_length != policy.short_view_samples:
        raise ValueError("H26 harmonic basis requires the short-view grid.")
    ordered = tuple(sorted(set(int(value) for value in pitches)))
    matrix = np.empty((spectrum.power.size - 1, len(ordered)), dtype=np.float64)
    for column, pitch in enumerate(ordered):
        values = np.zeros(spectrum.power.size, dtype=np.float64)
        for rank in policy.harmonic_ranks:
            center = partial_center_hz(pitch, rank, cents=cents, inharmonicity=inharmonicity)
            kernel = triangular_cents_kernel(np, spectrum.frequencies_hz, center, policy=policy)
            factor = 1.0 / float(rank * rank)
            for index in range(1, kernel.size):
                values[index] = np.float64(values[index] + factor * kernel[index])
        square = np.float64(0.0)
        for index in range(1, values.size):
            square = np.float64(square + values[index] * values[index])
        norm = math.sqrt(float(square))
        if not math.isfinite(norm) or norm <= 0.0:
            raise ValueError("H26 harmonic basis column invalid.")
        for index in range(1, values.size):
            matrix[index - 1, column] = np.float64(values[index] / norm)
    return matrix


def fixed_nnls_v1(
    np: Any, matrix: Any, target: Any, *, policy: H26NumericalPolicy,
) -> H26ResidualResult:
    basis = np.asarray(matrix)
    y = np.asarray(target)
    if basis.dtype != np.float64 or y.dtype != np.float64 or basis.ndim != 2 or y.shape != (basis.shape[0],):
        raise ValueError("H26 NNLS operand shape/dtype mismatch.")
    coefficients = np.zeros(basis.shape[1], dtype=np.float64)
    residual = y.copy()
    for _ in range(policy.nnls_sweeps):
        for column in range(basis.shape[1]):
            numerator = np.float64(0.0)
            denominator = np.float64(0.0)
            for row in range(basis.shape[0]):
                numerator = np.float64(numerator + basis[row, column] * residual[row])
                denominator = np.float64(denominator + basis[row, column] * basis[row, column])
            if not float(denominator) > 0.0:
                raise ValueError("H26 NNLS zero column.")
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
    value = float(residual_square) / max(float(target_square), policy.power_floor)
    return H26ResidualResult(value, tuple(float(item) for item in coefficients))


def factorization_residual(
    np: Any, spectrum: H26Spectrum, pitches: Sequence[int],
    *, policy: H26NumericalPolicy, cents: float = 0.0, inharmonicity: float = 0.0,
) -> H26ResidualResult:
    if not pitches:
        return H26ResidualResult(1.0, ())
    y = np.empty(spectrum.power.size - 1, dtype=np.float64)
    for index in range(1, spectrum.power.size):
        y[index - 1] = np.float64(spectrum.power[index] / max(spectrum.total_power, policy.power_floor))
    basis = harmonic_basis(np, spectrum, pitches, policy=policy, cents=cents, inharmonicity=inharmonicity)
    return fixed_nnls_v1(np, basis, y, policy=policy)


def pitch_dilution_pitch_order(transform_order: str) -> tuple[int, ...]:
    if transform_order == "ascending":
        return tuple(range(24, 97))
    if transform_order == "descending":
        return tuple(range(96, 23, -1))
    raise ValueError("H26 transform enumeration order invalid.")


def extract_measurements(
    np: Any, waveform: Any, *, target_hop_end: int, candidate_pitch: int,
    active_pitches: Sequence[int], candidate_active: bool,
    observation_equivalent: bool, support_valid: bool,
    policy: H26NumericalPolicy, candidate_partial_ranks: Sequence[int],
    transform_order: str, cents: float = 0.0, inharmonicity: float = 0.0,
) -> H26Measurements:
    operands = extract_raw_operands(
        np, waveform, target_hop_end=target_hop_end,
        candidate_pitch=candidate_pitch, active_pitches=active_pitches,
        candidate_active=candidate_active, observation_equivalent=observation_equivalent,
        support_valid=support_valid, policy=policy,
        candidate_partial_ranks=candidate_partial_ranks,
        cents=cents, inharmonicity=inharmonicity,
        transform_order=transform_order,
    )
    return measurements_from_raw_operands(policy, operands)


def extract_raw_operands(
    np: Any, waveform: Any, *, target_hop_end: int, candidate_pitch: int,
    active_pitches: Sequence[int], candidate_active: bool,
    observation_equivalent: bool, support_valid: bool,
    policy: H26NumericalPolicy, candidate_partial_ranks: Sequence[int],
    cents: float = 0.0, inharmonicity: float = 0.0,
    transform_order: str,
) -> H26RawOperands:
    current_short = causal_spectrum(np, extract_causal_view(np, waveform, hop_end=target_hop_end, length=policy.short_view_samples), policy=policy)
    previous_short = causal_spectrum(np, extract_causal_view(np, waveform, hop_end=target_hop_end - policy.hop_samples, length=policy.short_view_samples), policy=policy)
    current_long = causal_spectrum(np, extract_causal_view(np, waveform, hop_end=target_hop_end, length=policy.long_view_samples), policy=policy)
    previous_long = causal_spectrum(np, extract_causal_view(np, waveform, hop_end=target_hop_end - policy.hop_samples, length=policy.long_view_samples), policy=policy)
    exclusive = exclusive_partial_ranks(
        np, current_short, candidate_pitch=candidate_pitch,
        active_pitches=active_pitches, candidate_ranks=candidate_partial_ranks,
        policy=policy, cents=cents, inharmonicity=inharmonicity,
    )
    shared, _ = band_energy(
        np, current_short,
        partial_center_hz(candidate_pitch, 1, cents=cents, inharmonicity=inharmonicity),
        policy=policy,
        require_minimum_bins=False,
    )
    energies = tuple(
        band_energy(
            np, current_short,
            partial_center_hz(candidate_pitch, rank, cents=cents, inharmonicity=inharmonicity),
            policy=policy,
        )[0]
        for rank in exclusive
    )
    active = tuple(sorted(set(int(value) for value in active_pitches)))
    pitch_grid = pitch_dilution_pitch_order(transform_order)
    triplets: list[tuple[int, float, float]] = []
    for pitch in pitch_grid:
        independently_recomputed_active = factorization_residual(
            np, current_short, active, policy=policy,
            cents=cents, inharmonicity=inharmonicity,
        ).residual
        independently_recomputed_augmented = factorization_residual(
            np, current_short, tuple(sorted(set(active) | {pitch})),
            policy=policy, cents=cents, inharmonicity=inharmonicity,
        ).residual
        triplets.append((pitch, independently_recomputed_active, independently_recomputed_augmented))
    candidate_triplet = next(item for item in triplets if item[0] == candidate_pitch)
    active_residual, candidate_residual = candidate_triplet[1], candidate_triplet[2]
    return H26RawOperands(
        bool(candidate_active), bool(support_valid), bool(observation_equivalent),
        exclusive, energies, shared, current_short.total_power,
        previous_short.total_power, active_residual, candidate_residual,
        current_long.total_power, previous_long.total_power, int(target_hop_end),
        tuple(triplets),
    )


def required_support_is_valid(
    np: Any, *, sample_valid: Any, invalid_candidate_partial_ranks: Sequence[int],
    target_hop_end: int, exclusive_partial_ranks_used: Sequence[int],
    policy: H26NumericalPolicy,
) -> bool:
    """Derive validity from the persisted masks; callers cannot assert it."""

    mask = np.asarray(sample_valid)
    if mask.ndim != 1 or mask.dtype != np.bool_:
        raise ValueError("H26 sample-valid mask must be one-dimensional bool.")
    intervals = (
        (target_hop_end - policy.short_view_samples + 1, target_hop_end),
        (target_hop_end - policy.hop_samples - policy.short_view_samples + 1,
         target_hop_end - policy.hop_samples),
        (target_hop_end - policy.long_view_samples + 1, target_hop_end),
        (target_hop_end - policy.hop_samples - policy.long_view_samples + 1,
         target_hop_end - policy.hop_samples),
    )
    for start, end in intervals:
        if start < 0 or end >= mask.size or not bool(np.all(mask[start : end + 1])):
            return False
    invalid = tuple(int(rank) for rank in invalid_candidate_partial_ranks)
    if len(invalid) != len(set(invalid)) or any(rank not in policy.harmonic_ranks for rank in invalid):
        raise ValueError("H26 invalid candidate-rank mask.")
    return not bool(set(invalid) & set(int(rank) for rank in exclusive_partial_ranks_used))


def measurements_from_raw_operands(
    policy: H26NumericalPolicy, operands: H26RawOperands,
) -> H26Measurements:
    total = operands.current_short_total_power
    if not math.isfinite(total) or total <= policy.power_floor:
        raise ValueError("H26 raw current short total is invalid.")
    if len(operands.exclusive_partial_ranks) != len(operands.exclusive_band_energies):
        raise ValueError("H26 raw exclusive operand length mismatch.")
    ratios = tuple(float(energy) / total for energy in operands.exclusive_band_energies)
    bounds = tuple(
        policy.lower_envelope_factor * operands.shared_band_energy / float(rank * rank) / total
        for rank in operands.exclusive_partial_ranks
    )
    margins = tuple(
        math.inf if ratio == 0.0 else lower / ratio
        for ratio, lower in zip(ratios, bounds)
    )
    onset = max(0.0, total - operands.previous_short_total_power) / max(total, policy.power_floor)
    improvement = max(
        0.0, operands.active_only_residual - operands.active_plus_candidate_residual,
    ) / max(operands.active_only_residual, policy.power_floor)
    persistence = (
        operands.current_long_total_power - operands.previous_long_total_power
    ) / max(operands.current_long_total_power, policy.power_floor)
    if {pitch for pitch, _, _ in operands.pitch_dilution_residual_triplets} != set(range(24, 97)):
        raise ValueError("H26 pitch-dilution grid mismatch.")
    curve = tuple(sorted(
        (
            int(pitch),
            max(0.0, float(active_residual) - float(augmented_residual))
            / max(float(active_residual), policy.power_floor),
        )
        for pitch, active_residual, augmented_residual
        in operands.pitch_dilution_residual_triplets
    ))
    values = (
        *ratios, *bounds, *margins, onset, improvement, persistence,
        operands.shared_band_energy, operands.previous_short_total_power,
        operands.active_only_residual, operands.active_plus_candidate_residual,
        operands.current_long_total_power, operands.previous_long_total_power,
    )
    if any(math.isnan(float(value)) for value in values):
        raise ValueError("H26 raw operands produced NaN.")
    return H26Measurements(
        operands.candidate_active, operands.support_valid,
        operands.observation_equivalent, operands.exclusive_partial_ranks,
        ratios, onset, improvement, bounds, margins, persistence,
        operands.maximum_sample_read, curve,
    )


def resolve_h26(contract: Mapping[str, object], measurements: H26Measurements) -> H26Resolution:
    positive = contract["positive_certificate"]
    negative = contract["negative_certificate"]
    bounded_claim = contract["bounded_candidate_claim"]
    if measurements.candidate_active:
        return H26Resolution("ALREADY_ACTIVE_HISTORY", "candidate_active_before_proposal", False, False)
    if not measurements.support_valid:
        return H26Resolution("AMBIGUOUS", "invalid_or_incomplete_support", False, False)
    if measurements.observation_equivalent:
        return H26Resolution("AMBIGUOUS", "observation_equivalent_latent_causes", False, False)
    positive_count = sum(
        1 for ratio in measurements.exclusive_energy_ratios
        if ratio >= float(positive["minimum_exclusive_energy_ratio_each"])
    )
    positive_complete = (
        positive_count >= int(positive["minimum_exclusive_partial_count"])
        and measurements.onset_rise >= float(positive["minimum_short_window_onset_rise"])
        and measurements.active_only_residual_improvement >= float(positive["minimum_active_only_residual_improvement"])
    )
    bounded = [
        index for index, lower in enumerate(measurements.candidate_lower_bounds)
        if math.isfinite(lower) and lower >= float(bounded_claim["minimum_exclusive_energy_ratio"])
    ]
    negative_complete = (
        len(bounded) >= int(bounded_claim["minimum_exclusive_partial_count"])
        and all(measurements.exclusive_energy_ratios[index] <= float(negative["maximum_exclusive_energy_ratio_each"]) for index in bounded)
        and all(measurements.negative_margin_ratios[index] >= float(negative["minimum_margin_below_candidate_claim"]) for index in bounded)
        and measurements.onset_rise <= float(negative["maximum_short_window_onset_rise"])
        and measurements.active_only_residual_improvement <= float(negative["maximum_active_only_residual_improvement"])
    )
    if positive_complete:
        return H26Resolution("BIRTH_SUPPORTED", "complete_positive_certificate", True, negative_complete)
    if negative_complete:
        return H26Resolution("NO_BIRTH", "complete_bounded_negative_certificate", False, True)
    return H26Resolution("AMBIGUOUS", "certificate_gap_or_conflict", False, False)


def p2_cells(contract: Mapping[str, object], grid_id: str) -> tuple[Mapping[str, object], ...]:
    grids = contract["p2_perturbation_grids"]
    if grid_id not in grids:
        raise KeyError(grid_id)
    grid = grids[grid_id]
    if grid_id == "P2_GAIN_V1":
        return tuple({"scale": value} for value in grid["common_linear_amplitude_scales"])
    if grid_id == "P2_PHASE_V1":
        return tuple({"phase_radians": value} for value in grid["global_phase_radians"])
    if grid_id == "P2_NOISE_V1":
        return tuple(
            {"colour": colour, "snr_db": snr, "decimal_snr_db_string": decimal}
            for colour in grid["colours"]
            for snr, decimal in zip(grid["snr_db"], grid["decimal_snr_db_strings"])
        )
    if grid_id == "P2_CENTS_INHARMONICITY_V1":
        return tuple({"cents": cents, "B": value} for cents, value in itertools.product(grid["cents"], grid["B"]))
    if grid_id == "P2_HOP_SHIFT_V1":
        hop = int(contract["causal_contract"]["hop_samples"])
        return tuple({"hop_shift": value, "sample_shift": hop * value} for value in grid["hop_shifts"])
    if grid_id == "P2_PERMUTATION_V1":
        return tuple(
            {"active_pitch_order": a, "candidate_partial_order": c, "transform_order": t}
            for a, c, t in itertools.product(
                grid["active_pitch_orders"], grid["candidate_partial_orders"], grid["transform_orders"]
            )
        )
    if grid_id == "P2_RUNTIME_V1":
        return ({"runtime": "primary", "identity": grid["primary"]}, {"runtime": "secondary", "identity": grid["secondary"]})
    raise ValueError("H26 unsupported P2 grid.")


def _require_scientific(
    capability: H26ScientificCapability,
) -> tuple[H26DormantPlan, str]:
    del capability
    raise PermissionError("H26 science remains dormant; no capability can exist.")


def produce_h26_fixture_evidence(
    np: Any, capability: H26ScientificCapability, *, fixture_id: str,
    observation: object,
    p2_transform: object | None = None,
) -> H26EvidenceRecord:
    plan, expected_population_index_sha256 = _require_scientific(capability)
    from .harmonic_censoring_h26_materializer import (
        H26BoundObservation, _validity_masks, encode_waveform,
    )
    if type(observation) is not H26BoundObservation or observation.fixture_id != fixture_id:
        raise ValueError("H26 evidence requires the exact bound observation.")
    if observation.population_index_sha256 != expected_population_index_sha256:
        raise ValueError("H26 evidence population binding mismatch.")
    if hashlib.sha256(encode_waveform(np, observation.waveform)).hexdigest() != observation.waveform_sha256:
        raise ValueError("H26 bound waveform mutated after verification.")
    policy = H26NumericalPolicy.from_plan(plan)
    fixture = plan.fixture(fixture_id)
    expected_masks = _validity_masks(np, fixture)
    sample_valid = np.asarray(observation.sample_valid)
    mask_raw = sample_valid.astype(np.uint8).tobytes(order="C")
    if (
        hashlib.sha256(mask_raw).hexdigest() != observation.sample_valid_sha256
        or mask_raw != expected_masks.sample_valid.astype(np.uint8).tobytes(order="C")
        or observation.invalid_candidate_partial_ranks
        != expected_masks.invalid_candidate_partial_ranks
    ):
        raise ValueError("H26 evidence validity masks are not bound.")
    waveform = observation.waveform
    params = fixture["parameters"]
    proposal_hop_end = int(plan.specifications["global_timeline"]["target_hop_end"])
    resolution_hop_end = int(plan.specifications["global_timeline"]["resolution_hop_end"])
    cents = 0.0
    inharmonicity = 0.0
    candidate_ranks = policy.harmonic_ranks
    transform_order = "ascending"
    perturbation: Mapping[str, object] | None = None
    if p2_transform is not None:
        from .harmonic_censoring_h26_materializer import (
            H26P2Transform, build_h26_p2_transform,
        )
        if type(p2_transform) is not H26P2Transform or p2_transform.fixture_id != fixture_id:
            raise ValueError("H26 evidence P2 transform type/fixture mismatch.")
        rebuilt = build_h26_p2_transform(
            plan, fixture_id=fixture_id, test_id=p2_transform.test_id,
            grid_id=p2_transform.grid_id, cell=p2_transform.cell,
        )
        if rebuilt != p2_transform:
            raise ValueError("H26 evidence P2 transform is not canonical.")
        proposal_hop_end = p2_transform.target_hop_end
        resolution_hop_end = p2_transform.resolution_hop_end
        cents = float(p2_transform.collision_overrides.get("cents", 0.0))
        inharmonicity = float(p2_transform.collision_overrides.get("B", 0.0))
        if p2_transform.recipe is not None:
            candidate_source = next(
                (source for source in p2_transform.recipe["sources"] if source["source_id"] == "candidate"),
                None,
            )
            if candidate_source is not None:
                cents = float(candidate_source["cents"])
                inharmonicity = float(candidate_source["B"])
                candidate_ranks = tuple(int(rank) for rank in candidate_source["partial_ranks"])
        perturbation = {
            "test_id": p2_transform.test_id, "grid_id": p2_transform.grid_id,
            "cell": dict(p2_transform.cell),
        }
        if p2_transform.grid_id == "P2_PERMUTATION_V1":
            transform_order = str(p2_transform.cell["transform_order"])
    proposal = begin_h26_causal_proposal(
        policy, candidate_pitch=int(fixture["candidate_pitch"]),
        proposal_hop_end=proposal_hop_end,
        resolution_hop_end=resolution_hop_end,
    )
    observation_equivalent = False
    if observation.alternate_waveform is not None:
        alternate_raw = encode_waveform(np, observation.alternate_waveform)
        if hashlib.sha256(alternate_raw).hexdigest() != observation.alternate_waveform_sha256:
            raise ValueError("H26 alternate observation mutated after verification.")
        if not nonzero_observations_are_byte_equivalent(
            np, waveform, observation.alternate_waveform,
        ):
            raise ValueError("H26 latent observations are not nonzero byte-equivalent.")
        observation_equivalent = True
    active: tuple[int, ...]
    if "active_pitches" in params:
        active = tuple(int(value) for value in params["active_pitches"])
    elif "old_pitch" in params:
        active = (int(params["old_pitch"]),)
    else:
        active = ()
    candidate_active = False
    transitions = params["prior_transitions"] if "prior_transitions" in params else ()
    for transition in transitions:
        if not isinstance(transition, Mapping) or transition.get("pitch") != fixture["candidate_pitch"]:
            continue
        if transition.get("kind") == "note_on":
            candidate_active = True
        elif transition.get("kind") in {"note_off", "release"}:
            candidate_active = False
        else:
            raise ValueError("H26 causal-history transition kind invalid.")
    if candidate_active:
        support_valid = required_support_is_valid(
            np, sample_valid=sample_valid,
            invalid_candidate_partial_ranks=observation.invalid_candidate_partial_ranks,
            target_hop_end=resolution_hop_end, exclusive_partial_ranks_used=(), policy=policy,
        )
        measurements = H26Measurements(
            True, bool(support_valid), bool(observation_equivalent), (), (),
            0.0, 0.0, (), (), 0.0, resolution_hop_end,
        )
        resolution = resolve_h26(plan.contract, measurements)
        state_after = finish_h26_causal_proposal(
            proposal, resolution, maximum_sample_read=measurements.maximum_sample_read,
        )
        return H26EvidenceRecord(
            fixture_id=fixture_id,
            measurement={key: getattr(measurements, key) for key in measurements.__dataclass_fields__},
            resolution={key: getattr(resolution, key) for key in resolution.__dataclass_fields__},
            operands={
                "candidate_active": True, "support_valid": support_valid,
                "observation_equivalent": observation_equivalent,
                "maximum_sample_read": resolution_hop_end,
                "proposal_hop_end": proposal_hop_end,
                "resolution_hop_end": resolution_hop_end,
                "state_before": proposal.state, "state_after": state_after,
                "active_pitches": (int(fixture["candidate_pitch"]),),
                "candidate_pitch": fixture["candidate_pitch"],
                "perturbation": perturbation,
            },
        )
    time_support_valid = required_support_is_valid(
        np, sample_valid=sample_valid,
        invalid_candidate_partial_ranks=(), target_hop_end=resolution_hop_end,
        exclusive_partial_ranks_used=(), policy=policy,
    )
    if not time_support_valid or observation_equivalent:
        measurements = H26Measurements(
            False, time_support_valid, observation_equivalent, (), (),
            0.0, 0.0, (), (), 0.0, resolution_hop_end,
        )
        resolution = resolve_h26(plan.contract, measurements)
        state_after = finish_h26_causal_proposal(
            proposal, resolution, maximum_sample_read=measurements.maximum_sample_read,
        )
        return H26EvidenceRecord(
            fixture_id=fixture_id,
            measurement={key: getattr(measurements, key) for key in measurements.__dataclass_fields__},
            resolution={key: getattr(resolution, key) for key in resolution.__dataclass_fields__},
            operands={
                "candidate_active": False, "support_valid": time_support_valid,
                "observation_equivalent": observation_equivalent,
                "maximum_sample_read": resolution_hop_end,
                "proposal_hop_end": proposal_hop_end,
                "resolution_hop_end": resolution_hop_end,
                "state_before": proposal.state, "state_after": state_after,
                "active_pitches": active, "candidate_pitch": fixture["candidate_pitch"],
                "perturbation": perturbation,
            },
        )
    current_short = causal_spectrum(
        np,
        extract_causal_view(
            np, waveform, hop_end=resolution_hop_end, length=policy.short_view_samples,
        ),
        policy=policy,
    )
    exclusive = exclusive_partial_ranks(
        np, current_short, candidate_pitch=int(fixture["candidate_pitch"]),
        active_pitches=active, candidate_ranks=candidate_ranks, policy=policy,
        cents=cents, inharmonicity=inharmonicity,
        transform_order=transform_order,
    )
    support_valid = required_support_is_valid(
        np, sample_valid=sample_valid,
        invalid_candidate_partial_ranks=observation.invalid_candidate_partial_ranks,
        target_hop_end=resolution_hop_end, exclusive_partial_ranks_used=exclusive,
        policy=policy,
    )
    if not support_valid:
        measurements = H26Measurements(
            False, False, False, exclusive, (), 0.0, 0.0, (), (),
            0.0, resolution_hop_end,
        )
        resolution = resolve_h26(plan.contract, measurements)
        state_after = finish_h26_causal_proposal(
            proposal, resolution, maximum_sample_read=measurements.maximum_sample_read,
        )
        return H26EvidenceRecord(
            fixture_id=fixture_id,
            measurement={key: getattr(measurements, key) for key in measurements.__dataclass_fields__},
            resolution={key: getattr(resolution, key) for key in resolution.__dataclass_fields__},
            operands={
                "candidate_active": False, "support_valid": False,
                "observation_equivalent": False,
                "exclusive_partial_ranks": exclusive,
                "maximum_sample_read": resolution_hop_end,
                "proposal_hop_end": proposal_hop_end,
                "resolution_hop_end": resolution_hop_end,
                "state_before": proposal.state, "state_after": state_after,
                "active_pitches": active, "candidate_pitch": fixture["candidate_pitch"],
                "perturbation": perturbation,
            },
        )
    raw_operands = extract_raw_operands(
        np, waveform, target_hop_end=resolution_hop_end,
        candidate_pitch=int(fixture["candidate_pitch"]), active_pitches=active,
        candidate_active=candidate_active,
        observation_equivalent=observation_equivalent,
        support_valid=support_valid, policy=policy, candidate_partial_ranks=candidate_ranks,
        cents=cents, inharmonicity=inharmonicity,
    )
    measurements = measurements_from_raw_operands(policy, raw_operands)
    resolution = resolve_h26(plan.contract, measurements)
    state_after = finish_h26_causal_proposal(
        proposal, resolution, maximum_sample_read=measurements.maximum_sample_read,
    )
    return H26EvidenceRecord(
        fixture_id=fixture_id,
        measurement={key: getattr(measurements, key) for key in measurements.__dataclass_fields__},
        resolution={key: getattr(resolution, key) for key in resolution.__dataclass_fields__},
        operands={
            **{key: getattr(raw_operands, key) for key in raw_operands.__dataclass_fields__},
            "proposal_hop_end": proposal_hop_end,
            "resolution_hop_end": resolution_hop_end,
            "state_before": proposal.state, "state_after": state_after,
            "active_pitches": active, "candidate_pitch": fixture["candidate_pitch"],
            "perturbation": perturbation,
        },
    )


def require_h26_scientific_execution_authorized(_: object = None) -> None:
    raise PermissionError("H26 scientific execution remains unauthorized and dormant.")


__all__ = [
    "H26CausalProposal", "H26EvidenceRecord", "H26Measurements", "H26RawOperands", "H26ResidualResult", "H26Resolution",
    "H26ScientificCapability", "H26Spectrum", "H26NumericalPolicy", "band_energy",
    "begin_h26_causal_proposal", "causal_spectrum", "finish_h26_causal_proposal",
    "exclusive_partial_ranks", "extract_causal_view", "extract_measurements", "extract_raw_operands",
    "f0_hz", "factorization_residual", "fixed_nnls_v1", "harmonic_basis", "partial_center_hz",
    "nonzero_observations_are_byte_equivalent", "p2_cells",
    "pitch_dilution_pitch_order", "produce_h26_fixture_evidence",
    "require_h26_scientific_execution_authorized",
    "measurements_from_raw_operands", "required_support_is_valid", "resolve_h26", "triangular_cents_kernel",
]
