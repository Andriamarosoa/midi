"""Dormant deterministic H27 generator/materializer implementation.

The numeric helpers are reviewable on toy inputs.  Every H27 fixture render and
every filesystem publication requires an unissuable capability, so importing or
testing this module cannot materialize H27_SYNTHETIC_V1.
"""
from __future__ import annotations

from dataclasses import dataclass
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h27_contract import (
    H27DormantPlan, REVIEWED_GIT_BLOBS, canonical_h27_record_identities,
)


SAMPLE_COUNT = 16640
SAMPLE_RATE_HZ = 44100
PRODUCTION_ROLE_ORDER = (
    "current_short", "previous_short", "current_long", "previous_long",
)
TOY_MAX_SAMPLE_COUNT = 4096
TOY_MAX_SAMPLE_RATE_HZ = 32000


class H27MaterializationCapability:
    """No issuer exists in the reviewed dormant H27 stack."""

    __slots__ = ()

    def __new__(cls, *args: object, **kwargs: object) -> "H27MaterializationCapability":
        del cls, args, kwargs
        raise PermissionError("H27 materialization capability has no issuer.")


@dataclass(frozen=True)
class H27DormantMaterializationPlan:
    record_identities: tuple[str, ...]
    reviewed_git_blobs: tuple[tuple[str, str], ...]
    population_namespace: str
    baseline_count: int
    p2_count: int
    total_count: int
    materialization_authorized: bool = False


def _numeric(value: object) -> float:
    if value == "2^-80":
        return math.ldexp(1.0, -80)
    if type(value) not in (int, float):
        raise ValueError("H27 numeric operand invalid.")
    result = float(value)
    if not math.isfinite(result):
        raise ValueError("H27 numeric operand must be finite.")
    return result


def _require_toy_audio_domain(*, sample_count: int, sample_rate_hz: int) -> None:
    """Reject any shape/rate that could reach the sealed H27 domain."""

    if (
        type(sample_count) is not int or not 1 <= sample_count <= TOY_MAX_SAMPLE_COUNT
        or type(sample_rate_hz) is not int or not 1 <= sample_rate_hz <= TOY_MAX_SAMPLE_RATE_HZ
    ):
        raise ValueError("H27 toy audio domain invalid.")
    if sample_count == SAMPLE_COUNT or sample_rate_hz == SAMPLE_RATE_HZ:
        raise ValueError("H27 production audio domain is forbidden to toy helpers.")


def _require_toy_mask_domain(*, sample_count: int, role_order: Sequence[str]) -> tuple[str, ...]:
    """Validate a toy mask fully before allocating its byte payload."""

    if type(sample_count) is not int or not 1 <= sample_count <= TOY_MAX_SAMPLE_COUNT:
        raise ValueError("H27 toy mask sample count invalid.")
    if isinstance(role_order, (str, bytes)) or not isinstance(role_order, Sequence):
        raise ValueError("H27 toy mask role order invalid.")
    roles = tuple(role_order)
    if not roles or any(type(role) is not str or not role for role in roles) or len(roles) != len(set(roles)):
        raise ValueError("H27 toy mask role order invalid.")
    if any(role in PRODUCTION_ROLE_ORDER for role in roles):
        raise ValueError("H27 production role names are forbidden to toy mask helpers.")
    return roles


def _f0(pitch: int) -> float:
    return 440.0 * 2.0 ** ((float(pitch) - 69.0) / 12.0)


def _envelope(source: Mapping[str, object], sample: int) -> float:
    onset = int(source["onset_sample"])
    if sample < onset:
        return 0.0
    kind = source["envelope_id"]
    if kind == "H27_ENV_ATTACK_DECAY_V1":
        return min(1.0, float(sample - onset + 1) / 64.0) * math.exp(-float(sample - onset) / 2048.0)
    if kind == "H27_ENV_EXP_DECAY_V1":
        params = source["envelope_parameters"]
        decay = _numeric(params["decay_samples"])
        if decay <= 0.0:
            raise ValueError("H27 decay must be positive.")
        return math.exp(-float(sample - onset) / decay)
    raise ValueError("H27 unknown envelope.")


def render_toy_recipe(
    np: Any, recipe: Mapping[str, object], *, sample_count: int, sample_rate_hz: int,
) -> Any:
    """Render a supplied toy recipe without consulting any H27 fixture ID."""

    _require_toy_audio_domain(sample_count=sample_count, sample_rate_hz=sample_rate_hz)
    sources = recipe.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise ValueError("H27 recipe sources invalid.")
    validated: list[tuple[Mapping[str, object], int, float, float, float, float, tuple[int, ...]]] = []
    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError("H27 toy source invalid.")
        pitch = int(source["pitch"])
        gain = _numeric(source["gain"])
        phase = _numeric(source["phase_radians"])
        cents = _numeric(source["cents"])
        inharmonicity = _numeric(source["B"])
        ranks = tuple(source["partial_ranks"])
        if ranks != tuple(sorted(set(ranks))) or any(type(rank) is not int or rank < 1 for rank in ranks):
            raise ValueError("H27 partial rank order invalid.")
        onset = source.get("onset_sample")
        if type(onset) is not int or not 0 <= onset < sample_count:
            raise ValueError("H27 toy source onset outside toy support.")
        if source.get("envelope_id") == "H27_ENV_ATTACK_DECAY_V1" and source.get("envelope_parameters") != {}:
            raise ValueError("H27 attack-decay toy envelope takes no parameters.")
        if source.get("envelope_id") not in ("H27_ENV_ATTACK_DECAY_V1", "H27_ENV_EXP_DECAY_V1"):
            raise ValueError("H27 unknown envelope.")
        if  any(1.0 + inharmonicity * rank * rank <= 0.0 for rank in ranks):
            raise ValueError("H27 inharmonicity makes a partial frequency invalid.")
        validated.append((source, pitch, gain, phase, cents, inharmonicity, ranks))
    noise = recipe.get("noise")
    if not isinstance(noise, Mapping) or noise.get("kind") != "NONE":
        raise ValueError("H27 toy renderer accepts NONE noise only; stochastic helpers are separately reviewed.")
    result = np.zeros(sample_count, dtype=np.float64)
    for source, pitch, gain, phase, cents, inharmonicity, ranks in validated:
        for rank in ranks:
            frequency = rank * _f0(pitch) * 2.0 ** (cents / 1200.0) * math.sqrt(1.0 + inharmonicity * rank * rank)
            amplitude = gain / float(rank)
            for sample in range(sample_count):
                component = amplitude * _envelope(source, sample) * math.sin(
                    2.0 * math.pi * frequency * float(sample) / float(sample_rate_hz) + phase
                )
                result[sample] = np.float64(result[sample] + component)
    return result


def role_major_mask_bytes(
    *, sample_count: int, role_order: Sequence[str],
    required_intervals: Mapping[str, Sequence[int]],
    exceptions: Sequence[Mapping[str, object]] = (),
) -> bytes:
    """Canonical generic role-major mask encoder, suitable for toy tests."""

    roles = _require_toy_mask_domain(sample_count=sample_count, role_order=role_order)
    if not isinstance(required_intervals, Mapping) or set(required_intervals) != set(roles):
        raise ValueError("H27 mask intervals must cover every role exactly.")
    normalized: dict[str, tuple[int, int]] = {}
    for role in roles:
        bounds = required_intervals[role]
        if isinstance(bounds, (str, bytes)) or not isinstance(bounds, Sequence) or len(bounds) != 2 or any(type(value) is not int for value in bounds):
            raise ValueError("H27 mask interval invalid.")
        start, end = bounds
        if not 0 <= start <= end < sample_count:
            raise ValueError("H27 mask interval out of range.")
        normalized[role] = (start, end)
    if isinstance(exceptions, (str, bytes)) or not isinstance(exceptions, Sequence):
        raise ValueError("H27 mask exceptions invalid.")
    validated_exceptions: list[tuple[str, int, int]] = []
    seen: set[tuple[str, int]] = set()
    for item in exceptions:
        role, sample = item.get("role"), item.get("sample_index")
        value = item["byte"] if "byte" in item else item.get("replacement_uint8")
        if type(role) is not str or role not in normalized or type(sample) is not int or type(value) is not int or value not in (0, 1):
            raise ValueError("H27 mask exception invalid.")
        key = (str(role), sample)
        if key in seen:
            raise ValueError("H27 duplicate mask exception.")
        seen.add(key)
        start, end = normalized[role]
        if not start <= sample <= end:
            raise ValueError("H27 mask exception outside required support.")
        validated_exceptions.append((role, sample, value))
    payload = bytearray(len(roles) * sample_count)
    role_index = {role: index for index, role in enumerate(roles)}
    for role in roles:
        start, end = normalized[role]
        offset = role_index[role] * sample_count
        payload[offset + start:offset + end + 1] = b"\x01" * (end - start + 1)
    for role, sample, value in validated_exceptions:
        payload[role_index[role] * sample_count + sample] = value
    return bytes(payload)


def render_toy_collision_pair(
    np: Any, *, sample_count: int, sample_rate_hz: int, old_pitch: int,
    collision_rank: int, old_gain: float, candidate_gain: float,
    old_onset: int, collision_onset: int, phase: float,
) -> tuple[Any, Any]:
    """Independently render a toy exact-collision pair for unit verification."""

    _require_toy_audio_domain(sample_count=sample_count, sample_rate_hz=sample_rate_hz)
    if type(old_pitch) is not int or type(collision_rank) is not int or collision_rank not in (2, 4, 8):
        raise ValueError("H27 collision amplitude/rank equation invalid.")
    if type(old_onset) is not int or type(collision_onset) is not int or not 0 <= old_onset < sample_count or not 0 <= collision_onset < sample_count:
        raise ValueError("H27 toy collision onset outside toy support.")
    old_gain = _numeric(old_gain)
    candidate_gain = _numeric(candidate_gain)
    phase = _numeric(phase)
    if candidate_gain != old_gain / collision_rank:
        raise ValueError("H27 collision amplitude/rank equation invalid.")
    canonical = float(collision_rank) * _f0(old_pitch)

    def render(candidate: bool) -> Any:
        out = np.zeros(sample_count, dtype=np.float64)
        for rank in range(1, 9):
            if rank == collision_rank:
                continue
            frequency = float(rank) * _f0(old_pitch)
            amplitude = old_gain / float(rank)
            for sample in range(sample_count):
                env = 0.0 if sample < old_onset else math.exp(-float(sample - old_onset) / 8192.0)
                out[sample] = np.float64(out[sample] + amplitude * env * math.sin(2*math.pi*frequency*sample/sample_rate_hz))
        amplitude = candidate_gain if candidate else old_gain / float(collision_rank)
        for sample in range(sample_count):
            env = 0.0 if sample < collision_onset else min(1.0, float(sample-collision_onset+1)/64.0)*math.exp(-float(sample-collision_onset)/2048.0)
            out[sample] = np.float64(out[sample] + amplitude * env * math.sin(2*math.pi*canonical*sample/sample_rate_hz + phase))
        return out

    return render(False), render(True)


def inspect_h27_materialization_plan(plan: H27DormantPlan) -> H27DormantMaterializationPlan:
    identities = canonical_h27_record_identities(plan)
    if len(identities) != 124 or len(set(identities)) != 124:
        raise ValueError("H27 dormant population identity reconciliation failed.")
    return H27DormantMaterializationPlan(
        record_identities=identities,
        reviewed_git_blobs=tuple((str(path).replace("\\", "/"), digest) for path, digest in REVIEWED_GIT_BLOBS.items()),
        population_namespace="H27_SYNTHETIC_V1",
        baseline_count=17, p2_count=107, total_count=124,
    )


def _require_capability(_: H27MaterializationCapability) -> None:
    raise PermissionError("H27 materialization remains dormant; no capability can exist.")


def synthesize_h27_fixture(
    np: Any, capability: H27MaterializationCapability, plan: H27DormantPlan,
    fixture_id: str,
) -> tuple[Any, bytes, Any | None]:
    """Unreachable reviewed fixture boundary; capability check is first."""

    _require_capability(capability)
    del np, plan, fixture_id
    raise AssertionError("unreachable")


def materialize_h27_population(
    np: Any, capability: H27MaterializationCapability, plan: H27DormantPlan,
    destination: Path,
) -> None:
    """Unreachable publisher; fails before inspecting the destination."""

    _require_capability(capability)
    del np, plan, destination
    raise AssertionError("unreachable")


__all__ = ["H27DormantMaterializationPlan", "H27MaterializationCapability",
           "inspect_h27_materialization_plan", "materialize_h27_population",
           "render_toy_collision_pair", "render_toy_recipe", "role_major_mask_bytes",
           "synthesize_h27_fixture"]
