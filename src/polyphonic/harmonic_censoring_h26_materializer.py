"""Dormant H26 deterministic synthesizer and population materializer.

No capability issuer exists in this commit.  Consequently the reviewed H26
fixture IDs cannot be rendered or published, while the implementation remains
available for structural review and small non-H26 unit inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
from copy import deepcopy
import hashlib
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h26_contract import H26DormantPlan, canonical_json_bytes


SAMPLE_COUNT = 16640
SAMPLE_RATE_HZ = 44100
_CAPABILITY_TOKEN = object()


class H26MaterializationCapability:
    """Factory-only future authority; this commit deliberately has no issuer."""

    __slots__ = ("plan", "implementation_commit", "_token")

    def __init__(
        self, plan: H26DormantPlan, implementation_commit: str,
        *, _token: object = None,
    ) -> None:
        if _token is not _CAPABILITY_TOKEN:
            raise PermissionError("H26 materialization capability has no issuer.")
        self.plan = plan
        self.implementation_commit = implementation_commit
        self._token = _token


@dataclass(frozen=True)
class H26ValidityMasks:
    sample_valid: Any
    invalid_candidate_partial_ranks: tuple[int, ...]


@dataclass(frozen=True)
class H26P2Transform:
    fixture_id: str
    test_id: str
    grid_id: str
    cell: Mapping[str, object]
    recipe: Mapping[str, object] | None
    collision_overrides: Mapping[str, object]
    target_hop_end: int
    resolution_hop_end: int
    validity_start_shift: int


def _f0(pitch: int) -> float:
    return 440.0 * 2.0 ** ((float(pitch) - 69.0) / 12.0)


def _envelope_value(source: Mapping[str, object], sample: int) -> float:
    onset = int(source["onset_sample"])
    if sample < onset:
        return 0.0
    elapsed = float(sample - onset)
    envelope = source["envelope_id"]
    if envelope == "H26_ENV_ATTACK_DECAY_V1":
        return min(1.0, (elapsed + 1.0) / 64.0) * math.exp(-elapsed / 2048.0)
    if envelope == "H26_ENV_EXP_DECAY_V1":
        tau = float(source["envelope_parameters"]["decay_samples"])
        return math.exp(-elapsed / tau)
    raise ValueError("H26 unknown envelope.")


def _accumulate_sources(
    np: Any, sources: Sequence[Mapping[str, object]], *, sample_count: int,
) -> Any:
    """Strict scalar-order synthesizer; callers must provide validated sources."""

    result = np.zeros(sample_count, dtype=np.float64)
    for source in sources:
        pitch = int(source["pitch"])
        gain = float(source["gain"])
        phase = float(source["phase_radians"])
        cents = float(source["cents"])
        inharmonicity = float(source["B"])
        for rank_raw in source["partial_ranks"]:
            rank = int(rank_raw)
            frequency = (
                rank * _f0(pitch) * 2.0 ** (cents / 1200.0)
                * math.sqrt(1.0 + inharmonicity * rank * rank)
            )
            amplitude = gain / float(rank)
            for sample in range(sample_count):
                envelope = _envelope_value(source, sample)
                component = amplitude * envelope * math.sin(
                    2.0 * math.pi * frequency * float(sample) / SAMPLE_RATE_HZ + phase
                )
                result[sample] = np.float64(result[sample] + component)
    return result


def _add_baseline_noise(np: Any, clean: Any, noise: Mapping[str, object]) -> Any:
    if noise["kind"] == "NONE":
        return clean
    if noise["kind"] not in {"WHITE_GAUSSIAN_SNR_V1", "P2_NOISE_V1"}:
        raise ValueError("H26 unsupported baseline noise kind.")
    start, end = (int(value) for value in noise["support_samples_inclusive"])
    if (start, end) != (8192, 16639) or clean.shape != (SAMPLE_COUNT,):
        raise ValueError("H26 baseline noise support drift.")
    seed = int(str(noise["seed_uint64_decimal"]), 10)
    generator = np.random.Generator(np.random.PCG64(seed))
    raw = generator.standard_normal(SAMPLE_COUNT).astype(np.float64, copy=False)
    if noise["kind"] == "P2_NOISE_V1" and noise["colour"] == "pink":
        transformed = np.fft.rfft(raw)
        transformed[0] = 0.0
        for index in range(1, transformed.size):
            transformed[index] = transformed[index] / math.sqrt(float(index))
        raw = np.fft.irfft(transformed, n=SAMPLE_COUNT).astype(np.float64, copy=False)
    elif noise["kind"] == "P2_NOISE_V1" and noise["colour"] != "white":
        raise ValueError("H26 unsupported P2 noise colour.")
    unit = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    count = end - start + 1
    mean = np.float64(0.0)
    for sample in range(start, end + 1):
        mean = np.float64(mean + raw[sample])
    mean = np.float64(mean / float(count))
    for sample in range(start, end + 1):
        unit[sample] = np.float64(raw[sample] - mean)
    noise_square = np.float64(0.0)
    clean_square = np.float64(0.0)
    for sample in range(start, end + 1):
        noise_square = np.float64(noise_square + unit[sample] * unit[sample])
        clean_square = np.float64(clean_square + clean[sample] * clean[sample])
    noise_rms = math.sqrt(float(noise_square) / float(count))
    clean_rms = math.sqrt(float(clean_square) / float(count))
    if not math.isfinite(noise_rms) or noise_rms <= 0.0 or not math.isfinite(clean_rms):
        raise ValueError("H26 baseline RMS invalid.")
    alpha = clean_rms * 10.0 ** (-float(noise["snr_db"]) / 20.0)
    result = clean.copy()
    for sample in range(start, end + 1):
        result[sample] = np.float64(result[sample] + alpha * unit[sample] / noise_rms)
    return result


def _synthesize_recipe(np: Any, recipe: Mapping[str, object], *, sample_count: int = SAMPLE_COUNT) -> Any:
    clean = _accumulate_sources(np, recipe["sources"], sample_count=sample_count)
    if sample_count != SAMPLE_COUNT and recipe["noise"]["kind"] != "NONE":
        raise ValueError("Artificial short recipes may not use H26 baseline noise.")
    return clean if sample_count != SAMPLE_COUNT else _add_baseline_noise(np, clean, recipe["noise"])


def _collision_envelope(sample: int, onset: int) -> float:
    if sample < onset:
        return 0.0
    elapsed = float(sample - onset)
    return min(1.0, (elapsed + 1.0) / 64.0) * math.exp(-elapsed / 2048.0)


def _render_collision_pair(
    np: Any, fixture: Mapping[str, object], collision: Mapping[str, object],
) -> tuple[Any, Any]:
    params = fixture["parameters"]
    old_pitch = int(params["old_pitch"])
    rank = int(params["collision_harmonic_rank"])
    old_gain = float(params["old_source_gain"])
    candidate_gain = float(params["candidate_source_gain"])
    phase = float(params["phase_radians"])
    if candidate_gain != old_gain / float(rank) or rank not in {2, 4, 8}:
        raise ValueError("H26 collision gain/rank divergence.")
    background_sources = [{
        "source_id": "common_old_background", "pitch": old_pitch,
        "gain": old_gain, "onset_sample": int(collision["old_note_on_sample"]),
        "envelope_id": "H26_ENV_EXP_DECAY_V1",
        "envelope_parameters": {"decay_samples": 8192},
        "partial_ranks": [value for value in range(1, 9) if value != rank],
        "phase_radians": float(collision["old_background_phase_radians"]),
        "cents": 0.0, "B": 0.0,
    }]
    old = _accumulate_sources(np, background_sources, sample_count=SAMPLE_COUNT)
    candidate = _accumulate_sources(np, background_sources, sample_count=SAMPLE_COUNT)
    frequency = float(rank) * _f0(old_pitch)
    onset = int(collision["collision_onset_sample"])
    for sample in range(SAMPLE_COUNT):
        envelope = _collision_envelope(sample, onset)
        old_component = (
            old_gain / float(rank) * envelope
            * math.sin(2.0 * math.pi * frequency * float(sample) / SAMPLE_RATE_HZ + phase)
        )
        old[sample] = np.float64(old[sample] + old_component)
    for sample in range(SAMPLE_COUNT):
        envelope = _collision_envelope(sample, onset)
        candidate_component = (
            candidate_gain * envelope
            * math.sin(2.0 * math.pi * frequency * float(sample) / SAMPLE_RATE_HZ + phase)
        )
        candidate[sample] = np.float64(candidate[sample] + candidate_component)
    if old.astype("<f8", copy=False).tobytes(order="C") != candidate.astype("<f8", copy=False).tobytes(order="C"):
        raise ValueError("H26 exact collision did not render byte-identically.")
    return old, candidate


def _validity_masks(np: Any, fixture: Mapping[str, object]) -> H26ValidityMasks:
    params = fixture.get("parameters")
    if type(params) is not dict:
        raise ValueError("H26 fixture parameters missing for validity masks.")
    sample_valid = np.ones(SAMPLE_COUNT, dtype=np.bool_)
    valid_start = params.get("valid_time_support_start_sample", 0)
    if type(valid_start) is not int or not 0 <= valid_start <= SAMPLE_COUNT:
        raise ValueError("H26 validity support start invalid.")
    sample_valid[:valid_start] = False
    raw_ranks = params.get("masked_candidate_partial_ranks", [])
    if type(raw_ranks) is not list or any(type(rank) is not int or not 1 <= rank <= 8 for rank in raw_ranks):
        raise ValueError("H26 masked candidate partial ranks invalid.")
    invalid_ranks = tuple(sorted(set(raw_ranks)))
    return H26ValidityMasks(sample_valid, invalid_ranks)


def build_h26_p2_transform(
    plan: H26DormantPlan, *, fixture_id: str, test_id: str,
    grid_id: str, cell: Mapping[str, object],
) -> H26P2Transform:
    """Build a declarative transform only; it never allocates audio."""

    from .harmonic_censoring_h26_engine import p2_cells

    test = next((item for item in plan.tests if item.test_id == test_id), None)
    if test is None or test.phase != "P2" or test.perturbation_grid_id != grid_id:
        raise ValueError("H26 P2 test/grid binding mismatch.")
    if fixture_id not in test.fixture_ids:
        raise ValueError("H26 P2 fixture is outside the preregistered test.")
    canonical_cells = p2_cells(plan.contract, grid_id)
    if dict(cell) not in [dict(value) for value in canonical_cells]:
        raise ValueError("H26 P2 cell is outside the sealed grid.")
    timeline = plan.specifications["global_timeline"]
    target = int(timeline["target_hop_end"])
    resolution = int(timeline["resolution_hop_end"])
    shift = 0
    recipe = None if fixture_id in plan.collision_fixture_ids else deepcopy(dict(plan.recipes[fixture_id]))
    collision_overrides: dict[str, object] = {}
    if grid_id == "P2_GAIN_V1":
        scale = float(cell["scale"])
        if recipe is not None:
            for source in recipe["sources"]:
                source["gain"] = float(source["gain"]) * scale
        collision_overrides["gain_scale"] = scale
    elif grid_id == "P2_PHASE_V1":
        phase = float(cell["phase_radians"])
        if recipe is not None:
            for source in recipe["sources"]:
                source["phase_radians"] = phase
        collision_overrides["phase_radians"] = phase
    elif grid_id == "P2_NOISE_V1":
        colour = str(cell["colour"])
        decimal = str(cell["decimal_snr_db_string"])
        seed_test_id = test_id.removeprefix("H26-T-")
        preimage = f"H26|{fixture_id}|{seed_test_id}|{colour}|{decimal}"
        seed = int.from_bytes(hashlib.sha256(preimage.encode("utf-8")).digest()[:8], "little")
        noise = {
            "kind": "P2_NOISE_V1", "colour": colour,
            "snr_db": int(cell["snr_db"]), "decimal_snr_db_string": decimal,
            "seed_preimage": preimage, "seed_uint64_decimal": str(seed),
            "support_samples_inclusive": list(
                plan.contract["p2_perturbation_grids"][grid_id]["support_samples_inclusive"]
            ),
        }
        if recipe is not None:
            recipe["noise"] = noise
        collision_overrides["noise"] = noise
    elif grid_id == "P2_CENTS_INHARMONICITY_V1":
        cents, value = float(cell["cents"]), float(cell["B"])
        if recipe is not None:
            for source in recipe["sources"]:
                source["cents"], source["B"] = cents, value
        collision_overrides.update({"cents": cents, "B": value})
    elif grid_id == "P2_HOP_SHIFT_V1":
        shift = int(cell["sample_shift"])
        if recipe is not None:
            for source in recipe["sources"]:
                source["onset_sample"] = int(source["onset_sample"]) + shift
        target += shift
        resolution += shift
        collision_overrides["sample_shift"] = shift
    elif grid_id == "P2_PERMUTATION_V1":
        if recipe is not None:
            reverse_sources = cell["active_pitch_order"] == "descending"
            noncandidate = [source for source in recipe["sources"] if source["source_id"] != "candidate"]
            candidate = [source for source in recipe["sources"] if source["source_id"] == "candidate"]
            noncandidate.sort(key=lambda source: (int(source["pitch"]), str(source["source_id"])), reverse=reverse_sources)
            recipe["sources"] = noncandidate + candidate
            reverse_partials = cell["candidate_partial_order"] == "descending"
            for source in candidate:
                source["partial_ranks"] = sorted(source["partial_ranks"], reverse=reverse_partials)
        collision_overrides["permutation"] = dict(cell)
    elif grid_id == "P2_RUNTIME_V1":
        collision_overrides["runtime_identity"] = deepcopy(dict(cell["identity"]))
    else:
        raise ValueError("H26 unsupported P2 transform grid.")
    return H26P2Transform(
        fixture_id=fixture_id, test_id=test_id, grid_id=grid_id,
        cell=deepcopy(dict(cell)), recipe=recipe,
        collision_overrides=collision_overrides,
        target_hop_end=target, resolution_hop_end=resolution,
        validity_start_shift=shift,
    )


def _require_capability(capability: H26MaterializationCapability) -> H26DormantPlan:
    if type(capability) is not H26MaterializationCapability or capability._token is not _CAPABILITY_TOKEN:
        raise PermissionError("H26 exact materialization capability required.")
    return capability.plan


def synthesize_h26_fixture(
    np: Any, capability: H26MaterializationCapability, fixture_id: str,
) -> tuple[Any, H26ValidityMasks, Any | None]:
    """Future-only reviewed synthesis boundary; impossible without an issuer."""

    plan = _require_capability(capability)
    fixture = plan.fixture(fixture_id)
    if fixture_id in plan.collision_fixture_ids:
        old, candidate = _render_collision_pair(
            np, fixture, plan.specifications["exact_nonzero_collision_contract"]
        )
        return old, _validity_masks(np, fixture), candidate
    waveform = _synthesize_recipe(np, plan.recipes[fixture_id])
    return waveform, _validity_masks(np, fixture), None


def synthesize_h26_p2_fixture(
    np: Any, capability: H26MaterializationCapability, transform: H26P2Transform,
) -> tuple[Any, H26ValidityMasks, Any | None]:
    """Future-only perturbed rendering; still unreachable without authority."""

    plan = _require_capability(capability)
    rebuilt = build_h26_p2_transform(
        plan, fixture_id=transform.fixture_id, test_id=transform.test_id,
        grid_id=transform.grid_id, cell=transform.cell,
    )
    if rebuilt != transform:
        raise ValueError("H26 P2 transform is not the canonical sealed transform.")
    fixture = deepcopy(dict(plan.fixture(transform.fixture_id)))
    params = deepcopy(dict(fixture["parameters"]))
    fixture["parameters"] = params
    masks = _validity_masks(np, fixture)
    if transform.validity_start_shift:
        shifted = np.ones(SAMPLE_COUNT, dtype=np.bool_)
        base_start = int(params.get("valid_time_support_start_sample", 0))
        shifted_start = base_start + transform.validity_start_shift
        if not 0 <= shifted_start <= SAMPLE_COUNT:
            raise ValueError("H26 shifted validity boundary requires clipping.")
        shifted[:shifted_start] = False
        masks = H26ValidityMasks(shifted, masks.invalid_candidate_partial_ranks)
    if transform.recipe is not None:
        return _synthesize_recipe(np, transform.recipe), masks, None
    collision = deepcopy(dict(plan.specifications["exact_nonzero_collision_contract"]))
    if "gain_scale" in transform.collision_overrides:
        scale = float(transform.collision_overrides["gain_scale"])
        params["old_source_gain"] = float(params["old_source_gain"]) * scale
        params["candidate_source_gain"] = float(params["candidate_source_gain"]) * scale
    if "phase_radians" in transform.collision_overrides:
        phase = float(transform.collision_overrides["phase_radians"])
        params["phase_radians"] = phase
        collision["old_background_phase_radians"] = phase
    old, candidate = _render_collision_pair(np, fixture, collision)
    noise = transform.collision_overrides.get("noise")
    if noise is not None:
        old = _add_baseline_noise(np, old, noise)
        candidate = _add_baseline_noise(np, candidate, noise)
    return old, masks, candidate


def encode_waveform(np: Any, waveform: Any) -> bytes:
    array = np.asarray(waveform)
    if array.shape != (SAMPLE_COUNT,) or array.dtype != np.float64 or not np.all(np.isfinite(array)):
        raise ValueError("H26 waveform shape/dtype/finiteness mismatch.")
    return array.astype("<f8", copy=False).tobytes(order="C")


def _write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


def materialize_h26_population(
    np: Any, capability: H26MaterializationCapability, destination: Path,
) -> None:
    """Future atomic publisher. No caller can obtain its capability today."""

    plan = _require_capability(capability)
    destination = Path(destination)
    if destination.exists():
        raise FileExistsError(destination)
    staging = destination.with_name(destination.name + ".staging")
    if staging.exists():
        raise FileExistsError(staging)
    staging.mkdir(parents=True)
    records: list[dict[str, object]] = []
    try:
        for ordinal, fixture_id in enumerate(plan.fixture_ids, start=1):
            waveform, masks, alternate = synthesize_h26_fixture(np, capability, fixture_id)
            raw = encode_waveform(np, waveform)
            name = f"{ordinal:03d}_{fixture_id}.f8le"
            _write_new(staging / name, raw)
            alternate_name = None
            if alternate is not None:
                alternate_raw = encode_waveform(np, alternate)
                alternate_name = f"{ordinal:03d}_{fixture_id}.alternate.f8le"
                _write_new(staging / alternate_name, alternate_raw)
            records.append({
                "fixture_id": fixture_id, "ordinal": ordinal, "waveform": name,
                "waveform_sha256": hashlib.sha256(raw).hexdigest(),
                "alternate_waveform": alternate_name,
                "sample_valid_count": int(np.count_nonzero(masks.sample_valid)),
                "invalid_candidate_partial_ranks": list(masks.invalid_candidate_partial_ranks),
            })
        _write_new(staging / "population_index.json", canonical_json_bytes({
            "schema_version": 1, "population_namespace": "H26_SYNTHETIC_V1",
            "materialized_by_commit": capability.implementation_commit,
            "records": records,
        }, line=True))
        os.replace(staging, destination)
    except BaseException:
        # Fail closed. Future authority must define cleanup/consumption semantics.
        raise


__all__ = [
    "H26MaterializationCapability", "H26P2Transform", "H26ValidityMasks", "SAMPLE_COUNT",
    "SAMPLE_RATE_HZ", "encode_waveform", "materialize_h26_population",
    "build_h26_p2_transform", "synthesize_h26_fixture", "synthesize_h26_p2_fixture",
]
