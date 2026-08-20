"""Dormant in-memory materializer for the six preregistered H28 snapshots.

The public rendering entry fails before contract, NumPy, filesystem, or
scientific access because no materialization capability issuer exists.  A
future separately reviewed authority may activate this implementation; this
commit does not create payloads or a population directory.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h28_timing_contract import (
    H27_BASELINE_PAYLOAD_SHA256,
    RECORD_ORDER,
    load_h28_timing_contract,
)


SAMPLE_COUNT = 17152
H27_PREFIX_SAMPLE_COUNT = 16640
SAMPLE_RATE_HZ = 44100
ROLE_ORDER = ("current_short", "previous_short", "current_long", "previous_long")
ROLE_LENGTHS = {
    "current_short": 4096,
    "previous_short": 4096,
    "current_long": 8192,
    "previous_long": 8192,
}
ROLE_OFFSETS = {
    "current_short": 0,
    "previous_short": 256,
    "current_long": 0,
    "previous_long": 256,
}
POPULATION_NAMESPACE = "H28_CAUSAL_TIMING_SYNTHETIC_V1"
FIXTURE_SPECIFICATION_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h27_fixture_specifications.json"
)
FIXTURE_SPECIFICATION_SIZE = 21241
FIXTURE_SPECIFICATION_SHA256 = (
    "28707e95e2d1219fa0aa678e2103a8ef5cae7e7ca24a7100f4a84479dd0ff93d"
)


class H28MaterializationCapability:
    """Nominal future capability with no issuer in the dormant lot."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object) -> "H28MaterializationCapability":
        del cls, args, kwargs
        raise PermissionError("H28 materialization capability has no issuer.")

    def __copy__(self) -> "H28MaterializationCapability":
        del self
        raise TypeError("H28 materialization capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> "H28MaterializationCapability":
        del self, memo
        raise TypeError("H28 materialization capability cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H28 materialization capability cannot be serialized.")


def require_h28_materialization_capability(value: object) -> None:
    del value
    raise PermissionError("H28 materialization capability is not issued.")


@dataclass(frozen=True)
class H28MaterializationDescriptor:
    record_identity: str
    fixture_id: str
    horizon_id: str
    candidate_pitch: int
    active_pitches: tuple[int, ...]
    proposal_hop_end: int
    resolution_hop_end: int
    cents: float
    inharmonicity: float


@dataclass(frozen=True)
class H28MaterializedRecord:
    descriptor: H28MaterializationDescriptor
    waveform_f64le: bytes
    sample_valid_mask_u8: bytes
    payload_sha256: Mapping[str, str]


def _reject_constant(value: str) -> object:
    raise ValueError(f"H28 fixture non-JSON numeric constant forbidden: {value}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H28 duplicate fixture JSON key forbidden: {key}")
        result[key] = value
    return result


def _load_fixture_specifications(repository_root: Path) -> Mapping[str, object]:
    root = Path(repository_root).resolve(strict=True)
    path = (root / FIXTURE_SPECIFICATION_RELATIVE_PATH).resolve(strict=True)
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("H28 fixture specification escapes repository root.") from exc
    if path.is_symlink() or not path.is_file():
        raise ValueError("H28 fixture specification must be a regular non-symlink file.")
    raw = path.read_bytes()
    if (
        len(raw) != FIXTURE_SPECIFICATION_SIZE
        or hashlib.sha256(raw).hexdigest() != FIXTURE_SPECIFICATION_SHA256
    ):
        raise ValueError("H28 fixture specification bytes changed.")
    try:
        document = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("H28 fixture specification must be strict UTF-8 JSON.") from exc
    if type(document) is not dict:
        raise ValueError("H28 fixture specification root must be an object.")
    return MappingProxyType(document)


def plan_h28_materialization_descriptors(
    repository_root: Path,
) -> tuple[H28MaterializationDescriptor, ...]:
    """Build the six metadata-only descriptors without rendering a sample."""

    contract = load_h28_timing_contract(Path(repository_root))
    specifications = _load_fixture_specifications(contract.repository_root)
    fixtures_raw = specifications.get("fixtures")
    recipes_raw = specifications.get("baseline_waveform_recipes")
    if type(fixtures_raw) is not list or type(recipes_raw) is not dict:
        raise ValueError("H28 fixed fixture specification structure changed.")
    fixtures = {str(item["id"]): item for item in fixtures_raw if type(item) is dict}
    recipes = recipes_raw
    expected_fixture_ids = {"H27-F-P01", "H27-F-N01"}
    if not expected_fixture_ids <= set(fixtures) or not expected_fixture_ids <= set(recipes):
        raise ValueError("H28 fixed fixtures or recipes missing.")

    descriptors: list[H28MaterializationDescriptor] = []
    for record_identity in RECORD_ORDER:
        fixture_id, horizon_id = record_identity.split("/")
        fixture = fixtures[fixture_id]
        recipe = recipes[fixture_id]
        if type(recipe) is not dict or type(recipe.get("sources")) is not list:
            raise ValueError("H28 fixed fixture recipe invalid.")
        horizon = next(item for item in contract.horizons if item.identity == horizon_id)
        active = tuple(sorted({
            int(source["pitch"])
            for source in recipe["sources"]
            if type(source) is dict and source.get("source_id") != "candidate"
        }))
        descriptors.append(H28MaterializationDescriptor(
            record_identity=record_identity,
            fixture_id=fixture_id,
            horizon_id=horizon_id,
            candidate_pitch=int(fixture["candidate_pitch"]),
            active_pitches=active,
            proposal_hop_end=horizon.proposal_hop_end,
            resolution_hop_end=horizon.resolution_hop_end,
            cents=0.0,
            inharmonicity=0.0,
        ))
    if tuple(item.record_identity for item in descriptors) != RECORD_ORDER:
        raise ValueError("H28 materialization descriptor order changed.")
    expected_semantics = (
        ("H27-F-P01", 40, ()),
        ("H27-F-N01", 52, (40,)),
    )
    for descriptor in descriptors:
        expected = next(item for item in expected_semantics if item[0] == descriptor.fixture_id)
        if (descriptor.fixture_id, descriptor.candidate_pitch, descriptor.active_pitches) != expected:
            raise ValueError("H28 fixed fixture semantics changed.")
    return tuple(descriptors)


def _numeric(value: object) -> float:
    if value == "2^-80":
        return math.ldexp(1.0, -80)
    if type(value) not in (int, float):
        raise ValueError("H28 numeric operand invalid.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("H28 numeric operand must be finite.")
    return result


def _f0(pitch: int) -> float:
    return 440.0 * 2.0 ** ((float(pitch) - 69.0) / 12.0)


def _envelope(
    capability: H28MaterializationCapability,
    source: Mapping[str, object],
    sample: int,
) -> float:
    require_h28_materialization_capability(capability)
    onset = int(source["onset_sample"])
    if sample < onset:
        return 0.0
    elapsed = float(sample - onset)
    if source["envelope_id"] == "H27_ENV_ATTACK_DECAY_V1":
        return min(1.0, (elapsed + 1.0) / 64.0) * math.exp(-elapsed / 2048.0)
    if source["envelope_id"] == "H27_ENV_EXP_DECAY_V1":
        decay = _numeric(source["envelope_parameters"]["decay_samples"])
        if decay <= 0.0:
            raise ValueError("H28 decay must be positive.")
        return math.exp(-elapsed / decay)
    raise ValueError("H28 envelope identity invalid.")


def _accumulate_sources(
    capability: H28MaterializationCapability,
    np: Any,
    sources: Sequence[Mapping[str, object]],
) -> Any:
    require_h28_materialization_capability(capability)
    result = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    for source in sources:
        pitch = int(source["pitch"])
        gain = _numeric(source["gain"])
        phase = _numeric(source["phase_radians"])
        cents = _numeric(source["cents"])
        b_value = _numeric(source["B"])
        ranks = tuple(source["partial_ranks"])
        if ranks != tuple(sorted(set(ranks))) or any(
            type(rank) is not int or rank < 1 for rank in ranks
        ):
            raise ValueError("H28 partial rank order invalid.")
        for rank in ranks:
            radicand = 1.0 + b_value * rank * rank
            if radicand <= 0.0:
                raise ValueError("H28 partial frequency invalid.")
            frequency = (
                float(rank)
                * _f0(pitch)
                * 2.0 ** (cents / 1200.0)
                * math.sqrt(radicand)
            )
            amplitude = gain / float(rank)
            for sample in range(SAMPLE_COUNT):
                component = amplitude * _envelope(capability, source, sample) * math.sin(
                    2.0 * math.pi * frequency * float(sample) / SAMPLE_RATE_HZ + phase
                )
                result[sample] = np.float64(result[sample] + component)
    return result


def _render_recipe(
    capability: H28MaterializationCapability,
    np: Any,
    recipe: Mapping[str, object],
) -> Any:
    require_h28_materialization_capability(capability)
    noise = recipe.get("noise")
    if type(noise) is not dict or noise.get("kind") != "NONE":
        raise ValueError("H28 P01/N01 recipes must remain noise-free.")
    sources = recipe.get("sources")
    if type(sources) is not list:
        raise ValueError("H28 recipe sources invalid.")
    return _accumulate_sources(capability, np, sources)


def _mask_bytes(
    capability: H28MaterializationCapability,
    proposal_hop_end: int,
    *,
    sample_count: int = SAMPLE_COUNT,
) -> bytes:
    require_h28_materialization_capability(capability)
    if sample_count not in (H27_PREFIX_SAMPLE_COUNT, SAMPLE_COUNT):
        raise ValueError("H28 mask sample count invalid.")
    payload = bytearray(len(ROLE_ORDER) * sample_count)
    for role_index, role in enumerate(ROLE_ORDER):
        end = proposal_hop_end - ROLE_OFFSETS[role]
        start = end - ROLE_LENGTHS[role] + 1
        if not 0 <= start <= end < sample_count:
            raise ValueError("H28 required mask interval unavailable.")
        offset = role_index * sample_count
        payload[offset + start:offset + end + 1] = b"\x01" * (end - start + 1)
    return bytes(payload)


def materialize_h28_records_in_memory(
    np: Any,
    capability: H28MaterializationCapability,
    repository_root: Path,
) -> tuple[H28MaterializedRecord, ...]:
    """Future activation edge; currently fails before any scientific access."""

    require_h28_materialization_capability(capability)
    descriptors = plan_h28_materialization_descriptors(Path(repository_root))
    specifications = _load_fixture_specifications(Path(repository_root))
    recipes = specifications["baseline_waveform_recipes"]
    rendered_by_fixture: dict[str, bytes] = {}
    result: list[H28MaterializedRecord] = []
    for descriptor in descriptors:
        if descriptor.fixture_id not in rendered_by_fixture:
            waveform = _render_recipe(
                capability, np, recipes[descriptor.fixture_id]
            ).astype("<f8", copy=False).tobytes(order="C")
            if len(waveform) != SAMPLE_COUNT * 8:
                raise ValueError("H28 waveform payload size invalid.")
            expected_prefix_sha = H27_BASELINE_PAYLOAD_SHA256[
                descriptor.fixture_id
            ]["waveform.f64le"]
            if hashlib.sha256(waveform[: H27_PREFIX_SAMPLE_COUNT * 8]).hexdigest() != expected_prefix_sha:
                raise ValueError("H28 waveform prefix differs from H27 baseline.")
            rendered_by_fixture[descriptor.fixture_id] = waveform
        mask = _mask_bytes(capability, descriptor.proposal_hop_end)
        if len(mask) != len(ROLE_ORDER) * SAMPLE_COUNT:
            raise ValueError("H28 mask payload size invalid.")
        if descriptor.horizon_id == "N":
            legacy_mask = _mask_bytes(
                capability,
                descriptor.proposal_hop_end,
                sample_count=H27_PREFIX_SAMPLE_COUNT,
            )
            expected_mask_sha = H27_BASELINE_PAYLOAD_SHA256[
                descriptor.fixture_id
            ]["sample-valid-mask.u8"]
            if hashlib.sha256(legacy_mask).hexdigest() != expected_mask_sha:
                raise ValueError("H28 N mask semantics differ from H27 baseline.")
        waveform = rendered_by_fixture[descriptor.fixture_id]
        digests = MappingProxyType({
            "waveform.f64le": hashlib.sha256(waveform).hexdigest(),
            "sample-valid-mask.u8": hashlib.sha256(mask).hexdigest(),
        })
        result.append(H28MaterializedRecord(
            descriptor=descriptor,
            waveform_f64le=waveform,
            sample_valid_mask_u8=mask,
            payload_sha256=digests,
        ))
    if tuple(item.descriptor.record_identity for item in result) != RECORD_ORDER:
        raise ValueError("H28 materialized record order changed.")
    return tuple(result)


__all__ = [
    "H28MaterializationCapability",
    "H28MaterializationDescriptor",
    "H28MaterializedRecord",
    "H27_PREFIX_SAMPLE_COUNT",
    "POPULATION_NAMESPACE",
    "SAMPLE_COUNT",
    "materialize_h28_records_in_memory",
    "plan_h28_materialization_descriptors",
]
