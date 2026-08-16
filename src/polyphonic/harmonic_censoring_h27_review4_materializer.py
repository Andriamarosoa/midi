"""Review-4 H27 production materializer with a process-local one-shot edge.

The rendering and publication body is mechanically copied from the externally
reviewed dormant H27 production implementation.  The only intentional change
is the authority plumbing: a private issuer creates one non-copyable capability
and the public materializer consumes it atomically before calling that body.
"""
from __future__ import annotations

from dataclasses import dataclass
import errno
import hashlib
import itertools
import json
import math
import os
from pathlib import Path
import stat
from types import FunctionType
from typing import Any, Callable, Mapping, Sequence

if os.name != "nt":
    import fcntl

if "_H27_FROZEN_CONTRACT" in globals():
    H27DormantPlan = _H27_FROZEN_CONTRACT.H27DormantPlan
    canonical_h27_record_identities = _H27_FROZEN_CONTRACT.canonical_h27_record_identities
    deep_thaw = _H27_FROZEN_CONTRACT.deep_thaw
else:  # Tests only; the one-shot runner injects the frozen reviewed contract.
    from src.polyphonic.harmonic_censoring_h27_contract import (
        H27DormantPlan,
        canonical_h27_record_identities,
        deep_thaw,
    )


SAMPLE_COUNT = 16640
SAMPLE_RATE_HZ = 44100
ROLE_ORDER = ("current_short", "previous_short", "current_long", "previous_long")
POPULATION_NAMESPACE = "H27_SYNTHETIC_V1"
FINAL_DESTINATION = Path("/Users/amcarene/h27-admin/population/h27-synthetic-v1")
STAGING_DESTINATION = Path("/Users/amcarene/h27-admin/population/.h27-synthetic-v1.staging")
INDEX_FIELDS = (
    "record_identity", "record_directory", "population_namespace", "payload_sha256",
    "candidate_pitch", "active_pitches", "proposal_hop_end", "resolution_hop_end",
    "cents", "inharmonicity",
)


class H27ProductionMaterializationCapability:
    """Process-local non-copyable single-use materialization capability."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object) -> "H27ProductionMaterializationCapability":
        del cls, args, kwargs
        raise PermissionError("H27 production materialization capability has no public constructor.")

    def __copy__(self) -> "H27ProductionMaterializationCapability":
        raise PermissionError("H27 production capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> "H27ProductionMaterializationCapability":
        del memo
        raise PermissionError("H27 production capability cannot be copied.")

    def __reduce__(self) -> object:
        raise TypeError("H27 production capability cannot be serialized.")


def _require_capability(value: H27ProductionMaterializationCapability) -> None:
    del value
    raise PermissionError("H27 Review 4 direct helper invocation is permanently closed.")


@dataclass(frozen=True)
class _RecordDescriptor:
    identity: str
    fixture_id: str
    grid_id: str | None
    cell: Mapping[str, object] | None
    candidate_pitch: int
    active_pitches: tuple[int, ...]
    proposal_hop_end: int
    resolution_hop_end: int
    cents: float
    inharmonicity: float


def _canonical_json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def _numeric(value: object) -> float:
    if value == "2^-80":
        return math.ldexp(1.0, -80)
    if type(value) not in (int, float):
        raise ValueError("H27 numeric operand invalid.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("H27 numeric operand must be finite.")
    return result


def _f0(pitch: int) -> float:
    return 440.0 * 2.0 ** ((float(pitch) - 69.0) / 12.0)


def _envelope(capability: H27ProductionMaterializationCapability, source: Mapping[str, object], sample: int) -> float:
    _require_capability(capability)
    onset = int(source["onset_sample"])
    if sample < onset:
        return 0.0
    elapsed = float(sample - onset)
    if source["envelope_id"] == "H27_ENV_ATTACK_DECAY_V1":
        return min(1.0, (elapsed + 1.0) / 64.0) * math.exp(-elapsed / 2048.0)
    if source["envelope_id"] == "H27_ENV_EXP_DECAY_V1":
        decay = _numeric(source["envelope_parameters"]["decay_samples"])
        if decay <= 0.0:
            raise ValueError("H27 decay must be positive.")
        return math.exp(-elapsed / decay)
    raise ValueError("H27 envelope identity invalid.")


def _accumulate_sources(
    capability: H27ProductionMaterializationCapability, np: Any,
    sources: Sequence[Mapping[str, object]],
) -> Any:
    _require_capability(capability)
    result = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    for source in sources:
        pitch = int(source["pitch"])
        gain = _numeric(source["gain"])
        phase = _numeric(source["phase_radians"])
        cents = _numeric(source["cents"])
        b_value = _numeric(source["B"])
        ranks = tuple(source["partial_ranks"])
        if ranks != tuple(sorted(set(ranks))) or any(type(rank) is not int or rank < 1 for rank in ranks):
            raise ValueError("H27 partial rank order invalid.")
        for rank in ranks:
            radicand = 1.0 + b_value * rank * rank
            if radicand <= 0.0:
                raise ValueError("H27 partial frequency invalid.")
            frequency = float(rank) * _f0(pitch) * 2.0 ** (cents / 1200.0) * math.sqrt(radicand)
            amplitude = gain / float(rank)
            for sample in range(SAMPLE_COUNT):
                component = amplitude * _envelope(capability, source, sample) * math.sin(
                    2.0 * math.pi * frequency * float(sample) / SAMPLE_RATE_HZ + phase
                )
                result[sample] = np.float64(result[sample] + component)
    return result


def _add_noise(
    capability: H27ProductionMaterializationCapability, np: Any,
    clean: Any, noise: Mapping[str, object],
) -> Any:
    _require_capability(capability)
    if noise["kind"] == "NONE":
        return clean
    if noise["kind"] not in ("WHITE_GAUSSIAN_SNR_V1", "P2_NOISE_V1"):
        raise ValueError("H27 noise identity invalid.")
    start, end = (int(value) for value in noise["support_samples_inclusive"])
    if (start, end) != (8192, 16639):
        raise ValueError("H27 noise support drift.")
    generator = np.random.Generator(np.random.PCG64(int(str(noise["seed_uint64_decimal"]), 10)))
    raw = generator.standard_normal(SAMPLE_COUNT).astype(np.float64, copy=False)
    if noise.get("colour", "white") == "pink":
        transformed = np.fft.rfft(raw)
        transformed[0] = 0.0
        for index in range(1, transformed.size):
            transformed[index] = transformed[index] / math.sqrt(float(index))
        raw = np.fft.irfft(transformed, n=SAMPLE_COUNT).astype(np.float64, copy=False)
    elif noise.get("colour", "white") != "white":
        raise ValueError("H27 noise colour invalid.")
    count = end - start + 1
    mean = np.float64(0.0)
    for sample in range(start, end + 1):
        mean = np.float64(mean + raw[sample])
    mean = np.float64(mean / float(count))
    unit = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    clean_square = np.float64(0.0)
    noise_square = np.float64(0.0)
    for sample in range(start, end + 1):
        unit[sample] = np.float64(raw[sample] - mean)
        noise_square = np.float64(noise_square + unit[sample] * unit[sample])
        clean_square = np.float64(clean_square + clean[sample] * clean[sample])
    noise_rms = math.sqrt(float(noise_square) / float(count))
    clean_rms = math.sqrt(float(clean_square) / float(count))
    if noise_rms <= 0.0 or not math.isfinite(noise_rms) or not math.isfinite(clean_rms):
        raise ValueError("H27 noise normalization invalid.")
    alpha = clean_rms * 10.0 ** (-_numeric(noise["snr_db"]) / 20.0)
    result = clean.copy()
    for sample in range(start, end + 1):
        result[sample] = np.float64(result[sample] + alpha * unit[sample] / noise_rms)
    return result


def _render_recipe(
    capability: H27ProductionMaterializationCapability, np: Any,
    recipe: Mapping[str, object],
) -> Any:
    _require_capability(capability)
    return _add_noise(
        capability, np, _accumulate_sources(capability, np, recipe["sources"]), recipe["noise"],
    )


def _render_collision(
    capability: H27ProductionMaterializationCapability, np: Any,
    fixture: Mapping[str, object], collision: Mapping[str, object],
) -> tuple[Any, Any]:
    _require_capability(capability)
    recipe = fixture["recipe"]
    old_pitch = int(recipe["old_pitch"])
    rank = int(recipe["collision_harmonic_rank"])
    old_gain = _numeric(recipe["old_source_gain"])
    candidate_gain = _numeric(recipe["candidate_source_gain"])
    phase = _numeric(recipe["phase_radians"])
    if rank not in (2, 4, 8) or candidate_gain != old_gain / float(rank):
        raise ValueError("H27 collision equation invalid.")
    background = ({
        "pitch": old_pitch, "gain": old_gain,
        "onset_sample": int(collision["old_note_on_sample"]),
        "envelope_id": "H27_ENV_EXP_DECAY_V1", "envelope_parameters": {"decay_samples": 8192},
        "partial_ranks": [value for value in range(1, 9) if value != rank],
        "phase_radians": _numeric(collision["old_background_phase_radians"]), "cents": 0.0, "B": 0.0,
    },)
    old = _accumulate_sources(capability, np, background)
    candidate = _accumulate_sources(capability, np, background)
    frequency = float(rank) * _f0(old_pitch)
    onset = int(collision["collision_onset_sample"])
    for target, amplitude in ((old, old_gain / float(rank)), (candidate, candidate_gain)):
        for sample in range(SAMPLE_COUNT):
            elapsed = float(sample - onset)
            envelope = 0.0 if sample < onset else min(1.0, (elapsed + 1.0) / 64.0) * math.exp(-elapsed / 2048.0)
            target[sample] = np.float64(target[sample] + amplitude * envelope * math.sin(
                2.0 * math.pi * frequency * float(sample) / SAMPLE_RATE_HZ + phase
            ))
    if old.astype("<f8", copy=False).tobytes(order="C") != candidate.astype("<f8", copy=False).tobytes(order="C"):
        raise ValueError("H27 collision renders are not byte-identical.")
    return old, candidate


def _grid_cells(grid: Mapping[str, object]) -> tuple[dict[str, object], ...]:
    axes = tuple(grid["axis_names"])
    values = tuple(tuple(grid["axes"][axis]) for axis in axes)
    cells: list[dict[str, object]] = []
    for combination in itertools.product(*values):
        cell: dict[str, object] = {}
        tokens: list[str] = []
        for axis, item in zip(axes, combination):
            token = str(item["value_token"])
            tokens.append(f"{axis}={token}")
            cell[axis] = deep_thaw(item)
        cell["cell_id"] = "__".join(tokens)
        cells.append(cell)
    return tuple(cells)


def _fixture_active_pitches(fixture: Mapping[str, object], recipe: Mapping[str, object] | None) -> tuple[int, ...]:
    meta = fixture["recipe"]
    if fixture["id"] in ("H27-F-H01", "H27-F-H02"):
        return tuple(sorted({int(item["pitch"]) for item in meta["prior_transitions"] if item["kind"] == "note_on"}))
    if fixture["id"] in ("H27-F-A01", "H27-F-A02"):
        return (int(meta["old_pitch"]),)
    if "active_pitches" in meta:
        return tuple(sorted(int(value) for value in meta["active_pitches"]))
    if recipe is None:
        return ()
    return tuple(sorted({int(source["pitch"]) for source in recipe["sources"] if source.get("source_id") != "candidate"}))


def _descriptors(plan: H27DormantPlan) -> tuple[_RecordDescriptor, ...]:
    fixtures = {str(item["id"]): item for item in plan.fixtures}
    recipes = plan.specifications["baseline_waveform_recipes"]
    timeline = plan.specifications["global_timeline"]
    result: list[_RecordDescriptor] = []
    for fixture_id in plan.fixture_ids:
        fixture = fixtures[fixture_id]
        recipe = recipes.get(fixture_id)
        result.append(_RecordDescriptor(
            f"baseline/{fixture_id}", fixture_id, None, None, int(fixture["candidate_pitch"]),
            _fixture_active_pitches(fixture, recipe), int(timeline["target_hop_end"]),
            int(timeline["resolution_hop_end"]), 0.0, 0.0,
        ))
    grids = plan.test_manifest["perturbation_grids"]
    for grid_id in plan.test_manifest["cell_identity_contract"]["grid_order"]:
        grid = grids[grid_id]
        for fixture_id in grid["fixture_ids"]:
            fixture = fixtures[fixture_id]
            recipe = recipes.get(fixture_id)
            for cell in _grid_cells(grid):
                shift = 256 * int(cell["shift_hops"]["value"]) if grid_id == "P2_HOP_SHIFT_V1" else 0
                cents = float(cell["cents"]["value"]) if grid_id == "P2_CENTS_INHARMONICITY_V1" else 0.0
                b_value = float(cell["b"]["value"]) if grid_id == "P2_CENTS_INHARMONICITY_V1" else 0.0
                identity = f"p2/{grid_id}/{fixture_id}/{cell['cell_id']}"
                result.append(_RecordDescriptor(
                    identity, fixture_id, grid_id, cell, int(fixture["candidate_pitch"]),
                    _fixture_active_pitches(fixture, recipe), int(timeline["target_hop_end"]) + shift,
                    int(timeline["resolution_hop_end"]) + shift, cents, b_value,
                ))
    expected = canonical_h27_record_identities(plan)
    if tuple(item.identity for item in result) != expected or len(result) != 124:
        raise ValueError("H27 production descriptor order/cardinality drift.")
    return tuple(result)


def _transformed_recipe(plan: H27DormantPlan, descriptor: _RecordDescriptor) -> Mapping[str, object] | None:
    raw = plan.specifications["baseline_waveform_recipes"].get(descriptor.fixture_id)
    if raw is None:
        return None
    recipe = deep_thaw(raw)
    grid_id, cell = descriptor.grid_id, descriptor.cell
    if grid_id is None or cell is None:
        return recipe
    if grid_id == "P2_GAIN_V1":
        for source in recipe["sources"]:
            source["gain"] = _numeric(source["gain"]) * float(cell["scale"]["value"])
    elif grid_id == "P2_PHASE_V1":
        for source in recipe["sources"]:
            source["phase_radians"] = float(cell["phase"]["value_radians"])
    elif grid_id == "P2_NOISE_V1":
        colour, snr = str(cell["colour"]["value"]), int(cell["snr_db"]["value"])
        preimage = f"H27|{descriptor.fixture_id}|{grid_id}|{cell['cell_id']}"
        digest = hashlib.sha256(preimage.encode("utf-8")).digest()
        recipe["noise"] = {"kind":"P2_NOISE_V1", "colour":colour, "snr_db":snr,
                           "seed_preimage":preimage, "seed_uint64_decimal":str(int.from_bytes(digest[:8], "big")),
                           "support_samples_inclusive":[8192,16639]}
    elif grid_id == "P2_CENTS_INHARMONICITY_V1":
        for source in recipe["sources"]:
            source["cents"], source["B"] = descriptor.cents, descriptor.inharmonicity
    elif grid_id == "P2_HOP_SHIFT_V1":
        shift = descriptor.proposal_hop_end - 16383
        for source in recipe["sources"]:
            source["onset_sample"] = int(source["onset_sample"]) + shift
    elif grid_id in ("P2_PERMUTATION_V1", "P2_RUNTIME_V1", "P2_ZERO_CONTEXT_BOUNDARY_V1"):
        pass
    else:
        raise ValueError("H27 production grid unsupported.")
    return recipe


def _mask_bytes(
    capability: H27ProductionMaterializationCapability,
    plan: H27DormantPlan, descriptor: _RecordDescriptor,
) -> bytes:
    _require_capability(capability)
    contract = plan.specifications["sample_valid_mask_contract"]
    shift = descriptor.proposal_hop_end - 16383
    payload = bytearray(len(ROLE_ORDER) * SAMPLE_COUNT)
    for role_index, role in enumerate(ROLE_ORDER):
        start, end = (int(value) + shift for value in contract["required_intervals_inclusive"][role])
        if not 0 <= start <= end < SAMPLE_COUNT:
            raise ValueError("H27 shifted mask requires clipping.")
        offset = role_index * SAMPLE_COUNT
        payload[offset + start:offset + end + 1] = b"\x01" * (end - start + 1)
    exceptions = list(contract["baseline_exceptions"].get(descriptor.fixture_id, ()))
    if descriptor.grid_id == "P2_ZERO_CONTEXT_BOUNDARY_V1" and descriptor.cell["mutation"]["target"] == "sample-valid-mask.u8":
        exceptions.append(descriptor.cell["mutation"])
    for item in exceptions:
        role = str(item["role"])
        sample = int(item["sample_index"]) + (shift if descriptor.grid_id == "P2_HOP_SHIFT_V1" else 0)
        payload[ROLE_ORDER.index(role) * SAMPLE_COUNT + sample] = int(item.get("byte", item.get("replacement_uint8")))
    return bytes(payload)


def _render_record(
    capability: H27ProductionMaterializationCapability, np: Any,
    plan: H27DormantPlan, descriptor: _RecordDescriptor,
) -> tuple[bytes, bytes, bytes | None]:
    _require_capability(capability)
    fixture = deep_thaw(next(item for item in plan.fixtures if item["id"] == descriptor.fixture_id))
    recipe = _transformed_recipe(plan, descriptor)
    alternate = None
    if recipe is None:
        collision = deep_thaw(plan.specifications["exact_nonzero_collision_contract"])
        if descriptor.grid_id == "P2_PHASE_V1":
            phase = float(descriptor.cell["phase"]["value_radians"])
            fixture["recipe"]["phase_radians"] = phase
            collision["old_background_phase_radians"] = phase
        waveform, alternate_array = _render_collision(capability, np, fixture, collision)
        alternate = alternate_array.astype("<f8", copy=False).tobytes(order="C")
    else:
        waveform = _render_recipe(capability, np, recipe)
    if descriptor.grid_id == "P2_ZERO_CONTEXT_BOUNDARY_V1" and descriptor.cell["mutation"]["target"] == "waveform":
        waveform[int(descriptor.cell["mutation"]["sample_index"])] = np.float64(math.ldexp(1.0, -80))
    raw = waveform.astype("<f8", copy=False).tobytes(order="C")
    if len(raw) != SAMPLE_COUNT * 8 or alternate is not None and alternate != raw:
        raise ValueError("H27 waveform payload/collision mismatch.")
    return raw, _mask_bytes(capability, plan, descriptor), alternate


def _write_new(
    capability: H27ProductionMaterializationCapability, parent_fd: int, name: str, raw: bytes,
) -> None:
    _require_capability(capability)
    if "/" in name or name in ("", ".", ".."):
        raise ValueError("H27 unsafe relative file name.")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(name, flags, 0o600, dir_fd=parent_fd)
    try:
        view = memoryview(raw)
        offset = 0
        while offset < len(raw):
            count = os.write(descriptor, view[offset:])
            if count <= 0:
                raise OSError("H27 incomplete payload write.")
            offset += count
        os.fsync(descriptor)
        info = os.fstat(descriptor)
        if (not stat.S_ISREG(info.st_mode) or info.st_nlink != 1 or
                stat.S_IMODE(info.st_mode) != 0o600 or info.st_uid != os.getuid()):
            raise PermissionError("H27 payload ownership/link/mode invariant failed.")
    finally:
        os.close(descriptor)


def _fsync_directory(capability: H27ProductionMaterializationCapability, descriptor: int) -> None:
    _require_capability(capability)
    os.fsync(descriptor)


def _rename_no_replace(
    capability: H27ProductionMaterializationCapability,
    parent_fd: int, source_name: str, destination_name: str,
) -> None:
    _require_capability(capability)
    if os.uname().sysname != "Darwin":
        raise OSError(errno.ENOTSUP, "H27 no-replace publish requires reviewed Darwin runtime.")
    import ctypes
    libc = ctypes.CDLL(None, use_errno=True)
    function = libc.renameatx_np
    function.argtypes = (ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint)
    function.restype = ctypes.c_int
    if function(parent_fd, os.fsencode(source_name), parent_fd, os.fsencode(destination_name), 0x00000004) != 0:
        code = ctypes.get_errno()
        raise OSError(code, os.strerror(code), destination_name)


def _mkdir_chain(capability: H27ProductionMaterializationCapability, root_fd: int, relative: str) -> int:
    _require_capability(capability)
    current = os.dup(root_fd)
    try:
        for component in relative.split("/"):
            if component in ("", ".", ".."):
                raise ValueError("H27 unsafe record directory.")
            try:
                os.mkdir(component, 0o700, dir_fd=current)
            except FileExistsError:
                pass
            child = os.open(
                component,
                os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
                dir_fd=current,
            )
            info = os.fstat(child)
            if (not stat.S_ISDIR(info.st_mode) or stat.S_IMODE(info.st_mode) != 0o700 or
                    info.st_nlink < 2 or info.st_uid != os.getuid()):
                os.close(child)
                raise PermissionError("H27 record directory mode/type invariant failed.")
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _read_exact_file(capability: H27ProductionMaterializationCapability, parent_fd: int, name: str) -> bytes:
    _require_capability(capability)
    descriptor = os.open(name, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0), dir_fd=parent_fd)
    try:
        before = os.fstat(descriptor)
        if (not stat.S_ISREG(before.st_mode) or before.st_nlink != 1 or
                stat.S_IMODE(before.st_mode) != 0o600 or before.st_uid != os.getuid()):
            raise PermissionError("H27 payload type/link/mode invariant failed.")
        chunks = []
        while True:
            chunk = os.read(descriptor, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(descriptor)
        if (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns) != (
            after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns
        ):
            raise PermissionError("H27 payload changed during verification.")
        return b"".join(chunks)
    finally:
        os.close(descriptor)


def _open_chain_read(capability: H27ProductionMaterializationCapability, root_fd: int, relative: str) -> int:
    _require_capability(capability)
    current = os.dup(root_fd)
    try:
        for component in relative.split("/"):
            if component in ("", ".", ".."):
                raise ValueError("H27 unsafe staging directory.")
            child = os.open(component, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                            getattr(os, "O_NOFOLLOW", 0), dir_fd=current)
            os.close(current)
            current = child
        return current
    except BaseException:
        os.close(current)
        raise


def _collect_tree(capability: H27ProductionMaterializationCapability, root_fd: int, prefix: str = "") -> set[str]:
    _require_capability(capability)
    result: set[str] = set()
    for name in os.listdir(root_fd):
        information = os.stat(name, dir_fd=root_fd, follow_symlinks=False)
        if stat.S_ISLNK(information.st_mode):
            raise PermissionError("H27 staging symlink forbidden.")
        relative = prefix + name
        if stat.S_ISDIR(information.st_mode):
            if stat.S_IMODE(information.st_mode) != 0o700 or information.st_uid != os.getuid():
                raise PermissionError("H27 staging directory invariant failed.")
            child = os.open(name, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                            getattr(os, "O_NOFOLLOW", 0), dir_fd=root_fd)
            try:
                result.update(_collect_tree(capability, child, relative + "/"))
            finally:
                os.close(child)
        elif (not stat.S_ISREG(information.st_mode) or information.st_nlink != 1 or
              stat.S_IMODE(information.st_mode) != 0o600 or information.st_uid != os.getuid()):
            raise PermissionError("H27 staging file invariant failed.")
        else:
            result.add(relative)
    return result


def _verify_staging(
    capability: H27ProductionMaterializationCapability, staging_fd: int,
    plan: H27DormantPlan, records: Sequence[Mapping[str, object]], expected_index_raw: bytes,
) -> None:
    _require_capability(capability)
    observed_index_raw = _read_exact_file(capability, staging_fd, "population_index.json")
    if observed_index_raw != expected_index_raw:
        raise PermissionError("H27 staging index changed before publication.")
    index = json.loads(observed_index_raw)
    if (_canonical_json_bytes(index) != observed_index_raw or index.get("schema_version") != 1 or
            index.get("population_namespace") != POPULATION_NAMESPACE or
            index.get("record_count") != 124 or index.get("records") != list(records)):
        raise PermissionError("H27 staging index is not exact canonical content.")
    identities = tuple(str(row["record_identity"]) for row in records)
    if identities != canonical_h27_record_identities(plan) or len(set(identities)) != 124:
        raise PermissionError("H27 staging identity/order mismatch.")
    descriptors = {item.identity: item for item in _descriptors(plan)}
    recipes = plan.specifications["baseline_waveform_recipes"]
    expected_files = {"population_index.json"}
    for row in records:
        identity = str(row["record_identity"])
        descriptor = descriptors[identity]
        if (tuple(row) != INDEX_FIELDS or row["record_directory"] != identity or
                row["population_namespace"] != POPULATION_NAMESPACE):
            raise PermissionError("H27 staging row schema/directory mismatch.")
        if (row["candidate_pitch"], tuple(row["active_pitches"]), row["proposal_hop_end"],
            row["resolution_hop_end"], row["cents"], row["inharmonicity"]) != (
            descriptor.candidate_pitch, descriptor.active_pitches, descriptor.proposal_hop_end,
            descriptor.resolution_hop_end, descriptor.cents, descriptor.inharmonicity):
            raise PermissionError("H27 staging derived metadata mismatch.")
        record_fd = _open_chain_read(capability, staging_fd, identity)
        try:
            payloads = row["payload_sha256"]
            names = set(payloads)
            if names not in ({"waveform.f64le", "sample-valid-mask.u8"},
                             {"waveform.f64le", "sample-valid-mask.u8", "alternate-waveform.f64le"}):
                raise PermissionError("H27 staging payload set mismatch.")
            if ("alternate-waveform.f64le" in names) != (descriptor.fixture_id not in recipes):
                raise PermissionError("H27 staging alternate outside planned collision.")
            for name, expected_sha256 in payloads.items():
                raw = _read_exact_file(capability, record_fd, name)
                if hashlib.sha256(raw).hexdigest() != expected_sha256:
                    raise PermissionError("H27 staging payload digest mismatch.")
                if name.endswith("waveform.f64le"):
                    if len(raw) != SAMPLE_COUNT * 8:
                        raise PermissionError("H27 staging waveform size mismatch.")
                elif len(raw) != SAMPLE_COUNT * len(ROLE_ORDER) or not set(raw) <= {0, 1}:
                    raise PermissionError("H27 staging mask invariant failed.")
                expected_files.add(identity + "/" + name)
        finally:
            os.close(record_fd)
    if _collect_tree(capability, staging_fd) != expected_files:
        raise PermissionError("H27 staging tree is not exhaustive.")


def _publish(
    capability: H27ProductionMaterializationCapability, np: Any, plan: H27DormantPlan,
    population_parent_fd: int,
) -> tuple[tuple[Mapping[str, object], ...], bytes]:
    _require_capability(capability)
    staging_name = STAGING_DESTINATION.name
    final_name = FINAL_DESTINATION.name
    os.mkdir(staging_name, 0o700, dir_fd=population_parent_fd)
    staging_fd = os.open(
        staging_name,
        os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0),
        dir_fd=population_parent_fd,
    )
    records: list[dict[str, object]] = []
    try:
        for descriptor in _descriptors(plan):
            waveform, mask, alternate = _render_record(capability, np, plan, descriptor)
            payloads = {"waveform.f64le": waveform, "sample-valid-mask.u8": mask}
            if alternate is not None:
                payloads["alternate-waveform.f64le"] = alternate
            record_fd = _mkdir_chain(capability, staging_fd, descriptor.identity)
            try:
                shas: dict[str, str] = {}
                for name, raw in payloads.items():
                    expected_sha256 = hashlib.sha256(raw).hexdigest()
                    _write_new(capability, record_fd, name, raw)
                    written = _read_exact_file(capability, record_fd, name)
                    if len(written) != len(raw) or hashlib.sha256(written).hexdigest() != expected_sha256:
                        raise ValueError("H27 payload verification before index failed.")
                    shas[name] = expected_sha256
                _fsync_directory(capability, record_fd)
            finally:
                os.close(record_fd)
            row = {
                "record_identity": descriptor.identity, "record_directory": descriptor.identity,
                "population_namespace": POPULATION_NAMESPACE, "payload_sha256": shas,
                "candidate_pitch": descriptor.candidate_pitch, "active_pitches": list(descriptor.active_pitches),
                "proposal_hop_end": descriptor.proposal_hop_end, "resolution_hop_end": descriptor.resolution_hop_end,
                "cents": descriptor.cents, "inharmonicity": descriptor.inharmonicity,
            }
            if tuple(row) != INDEX_FIELDS:
                raise AssertionError("H27 index row field order drift.")
            records.append(row)
        index = {"schema_version": 1, "population_namespace": POPULATION_NAMESPACE, "record_count": 124, "records": records}
        index_raw = _canonical_json_bytes(index)
        _write_new(capability, staging_fd, "population_index.json", index_raw)
        _fsync_directory(capability, staging_fd)
        _verify_staging(capability, staging_fd, plan, records, index_raw)
        _fsync_directory(capability, staging_fd)
    finally:
        os.close(staging_fd)
    _rename_no_replace(capability, population_parent_fd, staging_name, final_name)
    _fsync_directory(capability, population_parent_fd)
    return tuple(records), index_raw


_OPERATIONAL_GRAPH_NAMES = (
    "_canonical_json_bytes", "_numeric", "_f0", "_envelope", "_accumulate_sources",
    "_add_noise", "_render_recipe", "_render_collision", "_grid_cells",
    "_fixture_active_pitches", "_descriptors", "_transformed_recipe", "_mask_bytes",
    "_render_record", "_write_new", "_fsync_directory", "_rename_no_replace",
    "_mkdir_chain", "_read_exact_file", "_open_chain_read", "_collect_tree",
    "_verify_staging", "_publish",
)


def _build_operational_entry(
    boundary: Mapping[str, object],
) -> Callable[[Callable[[Path], H27DormantPlan], Path], tuple[tuple[Mapping[str, object], ...], bytes]]:
    required = {"capability", "binding", "consume_attested", "population_parent_fd"}
    if type(boundary) is not dict or set(boundary) != required:
        raise PermissionError("H27 Review 4 injected boundary is not exact.")
    exact_capability = boundary["capability"]
    exact_binding = boundary["binding"]
    exact_consumer = boundary["consume_attested"]
    population_parent_fd = boundary["population_parent_fd"]
    if not callable(exact_consumer) or type(population_parent_fd) is not int:
        raise PermissionError("H27 Review 4 injected boundary values are invalid.")

    def exact_guard(candidate: object) -> None:
        if candidate is not exact_capability:
            raise PermissionError("H27 Review 4 private capability mismatch.")

    private_globals = dict(globals())
    private_globals["_require_capability"] = exact_guard
    for name in _OPERATIONAL_GRAPH_NAMES:
        function = globals()[name]
        private_globals[name] = FunctionType(
            function.__code__, private_globals, function.__name__, function.__defaults__, function.__closure__
        )
    private_publish = private_globals["_publish"]

    def operational_entry(
        plan_loader: Callable[[Path], H27DormantPlan], repository_root: Path,
    ) -> tuple[tuple[Mapping[str, object], ...], bytes]:
        observed = exact_consumer((exact_capability, exact_binding))
        if observed is not exact_binding:
            raise PermissionError("H27 Review 4 attested consumption mismatch.")
        import numpy as np
        plan = plan_loader(repository_root)
        return private_publish(exact_capability, np, plan, population_parent_fd)

    return operational_entry


_DORMANT_NATIVE_BARRIER = ().__getitem__
_injected_boundary = globals().pop("_H27_BOUNDARY_SESSION", None)
if _injected_boundary is None:
    materialize_h27_production_population = _DORMANT_NATIVE_BARRIER
else:
    materialize_h27_production_population = _build_operational_entry(_injected_boundary)
del _injected_boundary

# The reviewed scientific graph exists only inside the closure above.  Direct
# module access remains an immutable native barrier, even if globals are rebound.
for _name in _OPERATIONAL_GRAPH_NAMES:
    globals()[_name] = _DORMANT_NATIVE_BARRIER
_build_operational_entry = _DORMANT_NATIVE_BARRIER


__all__ = ["materialize_h27_production_population"]
