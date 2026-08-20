"""Process-local H27 scientific capability, issued only after a durable claim."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import weakref
from typing import Iterator

from .harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, H27SealedRecordBinding,
)


_CAPABILITIES: dict[int, tuple[weakref.ReferenceType[H27ScientificCapability], str, str]] = {}
_BINDINGS: dict[int, tuple[weakref.ReferenceType[H27SealedRecordBinding], int]] = {}
_ISSUED_ONCE = False


def _live_capability(value: object) -> bool:
    entry = _CAPABILITIES.get(id(value))
    return entry is not None and entry[0]() is value


def issue_h27_scientific_capability(*, claim_raw: bytes, claim_sha256: str,
                                    population_index_sha256: str,
                                    execution_authorized: bool) -> H27ScientificCapability:
    """Mint one process-local capability after the caller published the claim."""

    global _ISSUED_ONCE
    if _ISSUED_ONCE:
        raise PermissionError("H27 scientific capability has already been issued in this process.")
    if execution_authorized is not True:
        raise PermissionError("H27 scientific execution is not authorized.")
    if type(claim_raw) is not bytes or not claim_raw.endswith(b"\n"):
        raise ValueError("H27 scientific claim bytes invalid.")
    if hashlib.sha256(claim_raw).hexdigest() != claim_sha256:
        raise ValueError("H27 scientific claim SHA mismatch.")
    if type(population_index_sha256) is not str or len(population_index_sha256) != 64:
        raise ValueError("H27 population index SHA invalid.")
    if (population_index_sha256.lower() != population_index_sha256
            or any(ch not in "0123456789abcdef" for ch in population_index_sha256)):
        raise ValueError("H27 population index SHA invalid.")
    capability = object.__new__(H27ScientificCapability)
    _CAPABILITIES[id(capability)] = (
        weakref.ref(capability, lambda _ref, key=id(capability): _CAPABILITIES.pop(key, None)),
        claim_sha256,
        population_index_sha256,
    )
    _ISSUED_ONCE = True
    return capability


def require_operational_h27_capability(value: object) -> None:
    if type(value) is not H27ScientificCapability or not _live_capability(value):
        raise PermissionError("H27 scientific capability is not operationally issued.")


def require_h27_capability_population_index(
    capability: H27ScientificCapability, population_index_sha256: str,
) -> None:
    require_operational_h27_capability(capability)
    entry = _CAPABILITIES[id(capability)]
    if entry[2] != population_index_sha256:
        raise PermissionError("H27 capability population index SHA mismatch.")


def register_h27_sealed_record_binding(
    capability: H27ScientificCapability, binding: H27SealedRecordBinding
) -> H27SealedRecordBinding:
    require_operational_h27_capability(capability)
    if type(binding) is not H27SealedRecordBinding:
        raise TypeError("H27 sealed record binding type invalid.")
    _BINDINGS[id(binding)] = (
        weakref.ref(binding, lambda _ref, key=id(binding): _BINDINGS.pop(key, None)),
        id(capability),
    )
    return binding


def require_operational_h27_binding(value: object) -> None:
    if type(value) is not H27SealedRecordBinding:
        raise PermissionError("H27 sealed record binding is not operationally issued.")
    entry = _BINDINGS.get(id(value))
    if entry is None or entry[0]() is not value or entry[1] not in _CAPABILITIES:
        raise PermissionError("H27 sealed record binding is not operationally issued.")


@contextmanager
def operational_h27_engine_boundary(
    capability: H27ScientificCapability,
) -> Iterator[None]:
    """Temporarily connect the already-sealed dormant engine guards."""

    require_operational_h27_capability(capability)
    from . import harmonic_censoring_h27_engine as engine
    from . import harmonic_censoring_h27_recomputer as recomputer

    old = (
        engine.require_h27_scientific_capability,
        engine.require_h27_sealed_record_binding,
        recomputer.require_h27_scientific_capability,
        recomputer.require_h27_sealed_record_binding,
    )
    engine.require_h27_scientific_capability = require_operational_h27_capability
    engine.require_h27_sealed_record_binding = require_operational_h27_binding
    recomputer.require_h27_scientific_capability = require_operational_h27_capability
    recomputer.require_h27_sealed_record_binding = require_operational_h27_binding
    try:
        yield
    finally:
        (
            engine.require_h27_scientific_capability,
            engine.require_h27_sealed_record_binding,
            recomputer.require_h27_scientific_capability,
            recomputer.require_h27_sealed_record_binding,
        ) = old


__all__ = [
    "issue_h27_scientific_capability", "operational_h27_engine_boundary",
           "register_h27_sealed_record_binding", "require_h27_capability_population_index",
           "require_operational_h27_binding",
    "require_operational_h27_capability",
]
