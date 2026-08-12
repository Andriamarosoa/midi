"""Dormant deterministic H27 generator/materializer implementation.

The numeric helpers are reviewable on toy inputs.  Every H27 fixture render and
every filesystem publication requires an unissuable capability, so importing or
testing this module cannot materialize H27_SYNTHETIC_V1.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import math
from pathlib import Path
from typing import Any, Mapping, Sequence

from .harmonic_censoring_h27_contract import (
    H27DormantPlan, REVIEWED_GIT_BLOBS, canonical_h27_record_identities,
    deep_thaw,
)


SAMPLE_COUNT = 16640
SAMPLE_RATE_HZ = 44100


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

    if type(sample_count) is not int or sample_count <= 0 or type(sample_rate_hz) is not int or sample_rate_hz <= 0:
        raise ValueError("H27 toy shape/rate invalid.")
    result = np.zeros(sample_count, dtype=np.float64)
    sources = recipe.get("sources")
    if not isinstance(sources, Sequence) or isinstance(sources, (str, bytes)):
        raise ValueError("H27 recipe sources invalid.")
    for source in sources:
        pitch = int(source["pitch"])
        gain = _numeric(source["gain"])
        phase = _numeric(source["phase_radians"])
        cents = _numeric(source["cents"])
        inharmonicity = _numeric(source["B"])
        ranks = tuple(source["partial_ranks"])
        if ranks != tuple(sorted(set(ranks))) or any(type(rank) is not int or rank < 1 for rank in ranks):
            raise ValueError("H27 partial rank order invalid.")
        for rank in ranks:
            frequency = rank * _f0(pitch) * 2.0 ** (cents / 1200.0) * math.sqrt(1.0 + inharmonicity * rank * rank)
            amplitude = gain / float(rank)
            for sample in range(sample_count):
                component = amplitude * _envelope(source, sample) * math.sin(
                    2.0 * math.pi * frequency * float(sample) / float(sample_rate_hz) + phase
                )
                result[sample] = np.float64(result[sample] + component)
    noise = recipe.get("noise")
    if not isinstance(noise, Mapping) or noise.get("kind") != "NONE":
        raise ValueError("H27 toy renderer accepts NONE noise only; stochastic helpers are separately reviewed.")
    return result


def role_major_mask_bytes(
    *, sample_count: int, role_order: Sequence[str],
    required_intervals: Mapping[str, Sequence[int]],
    exceptions: Sequence[Mapping[str, object]] = (),
) -> bytes:
    """Canonical generic role-major mask encoder, suitable for toy tests."""

    if sample_count <= 0 or len(role_order) != len(set(role_order)):
        raise ValueError("H27 mask shape/role order invalid.")
    payload = bytearray(len(role_order) * sample_count)
    role_index = {role: index for index, role in enumerate(role_order)}
    if set(required_intervals) != set(role_order):
        raise ValueError("H27 mask intervals must cover every role exactly.")
    for role in role_order:
        bounds = required_intervals[role]
        if len(bounds) != 2:
            raise ValueError("H27 mask interval invalid.")
        start, end = int(bounds[0]), int(bounds[1])
        if not 0 <= start <= end < sample_count:
            raise ValueError("H27 mask interval out of range.")
        offset = role_index[role] * sample_count
        payload[offset + start:offset + end + 1] = b"\x01" * (end - start + 1)
    seen: set[tuple[str, int]] = set()
    for item in exceptions:
        role, sample = item.get("role"), item.get("sample_index")
        value = item.get("byte", item.get("replacement_uint8"))
        if role not in role_index or type(sample) is not int or value not in (0, 1):
            raise ValueError("H27 mask exception invalid.")
        key = (str(role), sample)
        if key in seen:
            raise ValueError("H27 duplicate mask exception.")
        seen.add(key)
        start, end = required_intervals[str(role)]
        if not int(start) <= sample <= int(end):
            raise ValueError("H27 mask exception outside required support.")
        payload[role_index[str(role)] * sample_count + sample] = int(value)
    return bytes(payload)


def render_toy_collision_pair(
    np: Any, *, sample_count: int, sample_rate_hz: int, old_pitch: int,
    collision_rank: int, old_gain: float, candidate_gain: float,
    old_onset: int, collision_onset: int, phase: float,
) -> tuple[Any, Any]:
    """Independently render a toy exact-collision pair for unit verification."""

    if collision_rank not in (2, 4, 8) or candidate_gain != old_gain / collision_rank:
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
