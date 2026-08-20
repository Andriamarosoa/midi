"""Process-local H27 capability issued from verified durable claim evidence."""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import stat
import weakref
from typing import Iterator, Mapping

from .harmonic_censoring_h27_scientific_capability_dormant import (
    H27ScientificCapability, H27SealedRecordBinding,
)


class H27VerifiedDurableClaim:
    """Unforgeable process-local proof that exact claim bytes were reopened."""

    __slots__ = ("__weakref__",)

    def __new__(cls):
        raise PermissionError("H27 durable claim proof is factory-only.")


_CLAIMS: dict[int, tuple[weakref.ReferenceType[H27VerifiedDurableClaim], str, str, str]] = {}
_CAPABILITIES: dict[int, tuple[weakref.ReferenceType[H27ScientificCapability], str, str, str]] = {}
_BINDINGS: dict[int, tuple[weakref.ReferenceType[H27SealedRecordBinding], int]] = {}
_ISSUED_ONCE = False


def _live_capability(value: object) -> bool:
    entry = _CAPABILITIES.get(id(value))
    return entry is not None and entry[0]() is value


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8") + b"\n"


def _read_regular_nofollow(path: Path) -> bytes:
    descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0))
    try:
        info = os.fstat(descriptor)
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise PermissionError("H27 durable claim must be one regular non-linked file.")
        with os.fdopen(descriptor, "rb", closefd=False) as stream:
            return stream.read()
    finally:
        os.close(descriptor)


def verify_durable_h27_claim(
    *, claim_path: Path, expected_claim: Mapping[str, object], expected_claim_sha256: str,
    authority_sha256: str,
) -> H27VerifiedDurableClaim:
    """Reopen the O_EXCL-published claim and attest its canonical exact bytes."""

    expected_raw = _canonical(dict(expected_claim))
    observed_raw = _read_regular_nofollow(claim_path)
    observed_sha = hashlib.sha256(observed_raw).hexdigest()
    if observed_raw != expected_raw or observed_sha != expected_claim_sha256:
        raise PermissionError("H27 durable claim bytes changed after publication.")
    for digest in (authority_sha256, str(expected_claim.get("population_index_sha256", ""))):
        if len(digest) != 64 or digest.lower() != digest or any(c not in "0123456789abcdef" for c in digest):
            raise ValueError("H27 durable claim authority digest invalid.")
    proof = object.__new__(H27VerifiedDurableClaim)
    _CLAIMS[id(proof)] = (
        weakref.ref(proof, lambda _ref, key=id(proof): _CLAIMS.pop(key, None)),
        observed_sha, str(expected_claim["population_index_sha256"]), authority_sha256,
    )
    return proof


def issue_h27_scientific_capability(*, durable_claim: H27VerifiedDurableClaim) -> H27ScientificCapability:
    """Mint one capability only from a live verified durable-claim proof."""

    global _ISSUED_ONCE
    if _ISSUED_ONCE:
        raise PermissionError("H27 scientific capability has already been issued in this process.")
    entry = _CLAIMS.get(id(durable_claim))
    if type(durable_claim) is not H27VerifiedDurableClaim or entry is None or entry[0]() is not durable_claim:
        raise PermissionError("H27 durable claim proof is not operationally verified.")
    capability = object.__new__(H27ScientificCapability)
    _CAPABILITIES[id(capability)] = (
        weakref.ref(capability, lambda _ref, key=id(capability): _CAPABILITIES.pop(key, None)),
        entry[1], entry[2], entry[3],
    )
    _CLAIMS.pop(id(durable_claim), None)
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
    "H27VerifiedDurableClaim", "issue_h27_scientific_capability", "operational_h27_engine_boundary",
           "register_h27_sealed_record_binding", "require_h27_capability_population_index",
           "require_operational_h27_binding",
    "require_operational_h27_capability", "verify_durable_h27_claim",
]
