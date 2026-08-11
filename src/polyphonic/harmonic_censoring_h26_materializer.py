"""Dormant H26 deterministic synthesizer and population materializer.

No capability issuer exists in this commit.  Consequently the reviewed H26
fixture IDs cannot be rendered or published, while the implementation remains
available for structural review and small non-H26 unit inputs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
import os
from pathlib import Path
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h26_contract import (
    H26DormantPlan, canonical_json_bytes, deep_freeze_json, deep_thaw_json,
    h26_f0_hz, h26_partial_center_hz, parse_strict_json,
)


SAMPLE_COUNT = 16640
SAMPLE_RATE_HZ = 44100
class H26MaterializationCapability:
    """Placeholder type; no instance can exist in the dormant stack."""

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object) -> "H26MaterializationCapability":
        del cls, args, kwargs
        raise PermissionError("H26 materialization capability has no issuer.")


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


@dataclass(frozen=True)
class H26BoundObservation:
    fixture_id: str
    population_root: Path
    population_index_sha256: str
    p2_test_id: str | None
    p2_grid_id: str | None
    p2_cell: Mapping[str, object] | None
    waveform_sha256: str
    waveform: Any
    sample_valid_sha256: str
    sample_valid: Any
    invalid_candidate_partial_ranks: tuple[int, ...]
    alternate_waveform_sha256: str | None
    alternate_waveform: Any | None


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
            frequency = h26_partial_center_hz(
                pitch, rank, cents=cents, inharmonicity=inharmonicity,
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
    frequency = float(rank) * h26_f0_hz(old_pitch)
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
    if not isinstance(params, Mapping):
        raise ValueError("H26 fixture parameters missing for validity masks.")
    sample_valid = np.ones(SAMPLE_COUNT, dtype=np.bool_)
    valid_start = params.get("valid_time_support_start_sample", 0)
    if type(valid_start) is not int or not 0 <= valid_start <= SAMPLE_COUNT:
        raise ValueError("H26 validity support start invalid.")
    sample_valid[:valid_start] = False
    raw_ranks = params.get("masked_candidate_partial_ranks", [])
    if type(raw_ranks) not in (list, tuple) or any(type(rank) is not int or not 1 <= rank <= 8 for rank in raw_ranks):
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
    recipe = None if fixture_id in plan.collision_fixture_ids else deep_thaw_json(plan.recipes[fixture_id])
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
        collision_overrides["permutation"] = deep_thaw_json(cell)
    elif grid_id == "P2_RUNTIME_V1":
        collision_overrides["runtime_identity"] = deep_thaw_json(cell["identity"])
    else:
        raise ValueError("H26 unsupported P2 transform grid.")
    return H26P2Transform(
        fixture_id=fixture_id, test_id=test_id, grid_id=grid_id,
        cell=deep_freeze_json(deep_thaw_json(cell)),
        recipe=None if recipe is None else deep_freeze_json(recipe),
        collision_overrides=deep_freeze_json(collision_overrides),
        target_hop_end=target, resolution_hop_end=resolution,
        validity_start_shift=shift,
    )


def _require_capability(capability: H26MaterializationCapability) -> H26DormantPlan:
    del capability
    raise PermissionError("H26 materialization remains dormant; no capability can exist.")


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
    fixture = deep_thaw_json(plan.fixture(transform.fixture_id))
    params = fixture["parameters"]
    fixture["parameters"] = params
    masks = _validity_masks_for_transform(np, plan, transform)
    if transform.recipe is not None:
        return _synthesize_recipe(np, transform.recipe), masks, None
    collision = deep_thaw_json(plan.specifications["exact_nonzero_collision_contract"])
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


def _validity_masks_for_transform(
    np: Any, plan: H26DormantPlan, transform: H26P2Transform,
) -> H26ValidityMasks:
    fixture = plan.fixture(transform.fixture_id)
    masks = _validity_masks(np, fixture)
    if not transform.validity_start_shift:
        return masks
    shifted = np.ones(SAMPLE_COUNT, dtype=np.bool_)
    params = fixture["parameters"]
    base_start = int(params.get("valid_time_support_start_sample", 0))
    shifted_start = base_start + transform.validity_start_shift
    if not 0 <= shifted_start <= SAMPLE_COUNT:
        raise ValueError("H26 shifted validity boundary requires clipping.")
    shifted[:shifted_start] = False
    return H26ValidityMasks(shifted, masks.invalid_candidate_partial_ranks)


def encode_waveform(np: Any, waveform: Any) -> bytes:
    array = np.asarray(waveform)
    if array.shape != (SAMPLE_COUNT,) or array.dtype != np.float64 or not np.all(np.isfinite(array)):
        raise ValueError("H26 waveform shape/dtype/finiteness mismatch.")
    return array.astype("<f8", copy=False).tobytes(order="C")


def _read_bound_file(root: Path, relative: object, expected_sha256: object) -> bytes:
    if type(relative) is not str or not relative or type(expected_sha256) is not str:
        raise ValueError("H26 population record path/SHA invalid.")
    path = (root / relative).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("H26 population file escapes its root.") from exc
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != expected_sha256:
        raise ValueError("H26 population file SHA mismatch.")
    return raw


def bind_h26_population_observation(
    np: Any, plan: H26DormantPlan, population_root: Path,
    *, expected_population_index_sha256: str, fixture_id: str,
    p2_transform: H26P2Transform | None = None,
) -> H26BoundObservation:
    """Future verifier for sealed bytes; it performs no synthesis or inference."""

    plan.fixture(fixture_id)
    root = Path(population_root).resolve(strict=True)
    index_path = (root / "population_index.json").resolve(strict=True)
    index_path.relative_to(root)
    index_raw = index_path.read_bytes()
    index_sha = hashlib.sha256(index_raw).hexdigest()
    if index_sha != expected_population_index_sha256:
        raise ValueError("H26 population index SHA mismatch.")
    index = parse_strict_json(index_raw, "population index")
    if index.get("schema_version") != 2 or index.get("population_namespace") != "H26_SYNTHETIC_V1":
        raise ValueError("H26 population index schema/namespace mismatch.")
    records = index.get("records")
    if type(records) is not list or len(records) != len(plan.fixture_ids):
        raise ValueError("H26 population index cardinality mismatch.")
    if any(type(item) is not dict for item in records):
        raise ValueError("H26 population record schema invalid.")
    if [record.get("fixture_id") for record in records] != list(plan.fixture_ids):
        raise ValueError("H26 population index order/identity mismatch.")
    p2_records = index.get("p2_records")
    if type(p2_records) is not list or any(type(item) is not dict for item in p2_records):
        raise ValueError("H26 P2 population records schema invalid.")
    p2_test_id = None
    p2_grid_id = None
    p2_cell = None
    expected_masks = _validity_masks(np, plan.fixture(fixture_id))
    if p2_transform is None:
        record = next(item for item in records if item["fixture_id"] == fixture_id)
    else:
        rebuilt = build_h26_p2_transform(
            plan, fixture_id=fixture_id, test_id=p2_transform.test_id,
            grid_id=p2_transform.grid_id, cell=p2_transform.cell,
        )
        if rebuilt != p2_transform:
            raise ValueError("H26 bound P2 transform is not canonical.")
        matches = [
            item for item in p2_records
            if item.get("fixture_id") == fixture_id
            and item.get("test_id") == rebuilt.test_id
            and item.get("grid_id") == rebuilt.grid_id
            and item.get("cell") == deep_thaw_json(rebuilt.cell)
        ]
        if len(matches) != 1:
            raise ValueError("H26 sealed P2 population record missing or duplicated.")
        record = matches[0]
        p2_test_id = rebuilt.test_id
        p2_grid_id = rebuilt.grid_id
        p2_cell = rebuilt.cell
        expected_masks = _validity_masks_for_transform(np, plan, rebuilt)
    waveform_raw = _read_bound_file(root, record.get("waveform"), record.get("waveform_sha256"))
    if len(waveform_raw) != SAMPLE_COUNT * 8:
        raise ValueError("H26 bound waveform byte length mismatch.")
    waveform = np.frombuffer(waveform_raw, dtype="<f8")
    if waveform.shape != (SAMPLE_COUNT,) or not np.all(np.isfinite(waveform)):
        raise ValueError("H26 bound waveform invalid.")
    mask_raw = _read_bound_file(root, record.get("sample_valid"), record.get("sample_valid_sha256"))
    if len(mask_raw) != SAMPLE_COUNT or any(value not in (0, 1) for value in mask_raw):
        raise ValueError("H26 bound sample-valid mask invalid.")
    sample_valid = np.frombuffer(mask_raw, dtype=np.uint8).astype(np.bool_)
    sample_valid.setflags(write=False)
    if mask_raw != expected_masks.sample_valid.astype(np.uint8).tobytes(order="C"):
        raise ValueError("H26 bound mask differs from sealed fixture parameters.")
    ranks = record.get("invalid_candidate_partial_ranks")
    if type(ranks) is not list or tuple(ranks) != expected_masks.invalid_candidate_partial_ranks:
        raise ValueError("H26 bound invalid-rank mask mismatch.")
    alternate = None
    alternate_sha = record.get("alternate_waveform_sha256")
    alternate_name = record.get("alternate_waveform")
    if (alternate_name is None) != (alternate_sha is None):
        raise ValueError("H26 alternate waveform path/SHA presence mismatch.")
    if alternate_name is not None:
        alternate_raw = _read_bound_file(root, alternate_name, alternate_sha)
        if len(alternate_raw) != SAMPLE_COUNT * 8:
            raise ValueError("H26 alternate waveform byte length mismatch.")
        alternate = np.frombuffer(alternate_raw, dtype="<f8")
        if not np.all(np.isfinite(alternate)):
            raise ValueError("H26 alternate waveform invalid.")
    return H26BoundObservation(
        fixture_id=fixture_id, population_root=root,
        population_index_sha256=index_sha,
        p2_test_id=p2_test_id, p2_grid_id=p2_grid_id, p2_cell=p2_cell,
        waveform_sha256=str(record["waveform_sha256"]), waveform=waveform,
        sample_valid_sha256=str(record["sample_valid_sha256"]),
        sample_valid=sample_valid,
        invalid_candidate_partial_ranks=tuple(int(rank) for rank in ranks),
        alternate_waveform_sha256=None if alternate_sha is None else str(alternate_sha),
        alternate_waveform=alternate,
    )


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
    p2_records: list[dict[str, object]] = []
    try:
        for ordinal, fixture_id in enumerate(plan.fixture_ids, start=1):
            waveform, masks, alternate = synthesize_h26_fixture(np, capability, fixture_id)
            raw = encode_waveform(np, waveform)
            name = f"{ordinal:03d}_{fixture_id}.f8le"
            _write_new(staging / name, raw)
            mask_name = f"{ordinal:03d}_{fixture_id}.sample-valid.u8"
            mask_raw = masks.sample_valid.astype(np.uint8).tobytes(order="C")
            _write_new(staging / mask_name, mask_raw)
            alternate_name = None
            alternate_sha256 = None
            if alternate is not None:
                alternate_raw = encode_waveform(np, alternate)
                alternate_name = f"{ordinal:03d}_{fixture_id}.alternate.f8le"
                _write_new(staging / alternate_name, alternate_raw)
                alternate_sha256 = hashlib.sha256(alternate_raw).hexdigest()
            records.append({
                "fixture_id": fixture_id, "ordinal": ordinal, "waveform": name,
                "waveform_sha256": hashlib.sha256(raw).hexdigest(),
                "alternate_waveform": alternate_name,
                "alternate_waveform_sha256": alternate_sha256,
                "sample_valid": mask_name,
                "sample_valid_sha256": hashlib.sha256(mask_raw).hexdigest(),
                "sample_valid_count": int(np.count_nonzero(masks.sample_valid)),
                "invalid_candidate_partial_ranks": list(masks.invalid_candidate_partial_ranks),
            })
        for test in plan.tests:
            if test.phase != "P2" or test.perturbation_grid_id is None:
                continue
            from .harmonic_censoring_h26_engine import p2_cells
            for fixture_id in test.fixture_ids:
                for cell_ordinal, cell in enumerate(
                    p2_cells(plan.contract, test.perturbation_grid_id), start=1,
                ):
                    transform = build_h26_p2_transform(
                        plan, fixture_id=fixture_id, test_id=test.test_id,
                        grid_id=test.perturbation_grid_id, cell=cell,
                    )
                    waveform, masks, alternate = synthesize_h26_p2_fixture(
                        np, capability, transform,
                    )
                    prefix = f"p2/{test.test_id}/{fixture_id}/{cell_ordinal:03d}"
                    waveform_name = prefix + ".f8le"
                    waveform_raw = encode_waveform(np, waveform)
                    _write_new(staging / waveform_name, waveform_raw)
                    mask_name = prefix + ".sample-valid.u8"
                    mask_raw = masks.sample_valid.astype(np.uint8).tobytes(order="C")
                    _write_new(staging / mask_name, mask_raw)
                    alternate_name = None
                    alternate_sha256 = None
                    if alternate is not None:
                        alternate_raw = encode_waveform(np, alternate)
                        alternate_name = prefix + ".alternate.f8le"
                        _write_new(staging / alternate_name, alternate_raw)
                        alternate_sha256 = hashlib.sha256(alternate_raw).hexdigest()
                    p2_records.append({
                        "fixture_id": fixture_id,
                        "test_id": test.test_id,
                        "grid_id": test.perturbation_grid_id,
                        "cell": deep_thaw_json(transform.cell),
                        "waveform": waveform_name,
                        "waveform_sha256": hashlib.sha256(waveform_raw).hexdigest(),
                        "alternate_waveform": alternate_name,
                        "alternate_waveform_sha256": alternate_sha256,
                        "sample_valid": mask_name,
                        "sample_valid_sha256": hashlib.sha256(mask_raw).hexdigest(),
                        "sample_valid_count": int(np.count_nonzero(masks.sample_valid)),
                        "invalid_candidate_partial_ranks": list(masks.invalid_candidate_partial_ranks),
                    })
        _write_new(staging / "population_index.json", canonical_json_bytes({
            "schema_version": 2, "population_namespace": "H26_SYNTHETIC_V1",
            "materialized_by_commit": capability.implementation_commit,
            "records": records, "p2_records": p2_records,
        }, line=True))
        os.replace(staging, destination)
    except BaseException:
        # Fail closed. Future authority must define cleanup/consumption semantics.
        raise


__all__ = [
    "H26BoundObservation", "H26MaterializationCapability", "H26P2Transform",
    "H26ValidityMasks", "SAMPLE_COUNT",
    "SAMPLE_RATE_HZ", "encode_waveform", "materialize_h26_population",
    "bind_h26_population_observation", "build_h26_p2_transform",
    "synthesize_h26_fixture", "synthesize_h26_p2_fixture",
]
