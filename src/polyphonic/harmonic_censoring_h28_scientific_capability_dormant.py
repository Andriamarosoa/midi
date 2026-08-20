"""Unissuable nominal boundaries for dormant H28 science.

This lot intentionally contains neither a registry nor a mutable authorization
hook.  A future reviewed authority must replace these unconditional guards and
provide a sealed population-index binding in a separate commit.
"""
from __future__ import annotations


H28_SEALED_RECORD_BINDING_FIELDS = (
    "population_root", "population_index_path", "population_index_sha256",
    "population_index_record_sha256", "record_directory", "record_identity",
    "population_namespace", "payload_sha256", "candidate_pitch",
    "active_pitches", "proposal_hop_end", "resolution_hop_end", "cents",
    "inharmonicity",
)


class H28ScientificCapability:
    """Nominal type only; construction never grants H28 scientific access."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object) -> "H28ScientificCapability":
        del cls, args, kwargs
        raise PermissionError("H28 scientific capability has no issuer.")

    def __copy__(self) -> "H28ScientificCapability":
        del self
        raise TypeError("H28 scientific capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> "H28ScientificCapability":
        del self, memo
        raise TypeError("H28 scientific capability cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H28 scientific capability cannot be serialized.")


class H28SealedRecordBinding:
    """Nominal binding of one complete row from a future sealed index."""

    __slots__ = H28_SEALED_RECORD_BINDING_FIELDS + ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object) -> "H28SealedRecordBinding":
        del cls, args, kwargs
        raise PermissionError("H28 sealed record binding has no loader.")

    def __copy__(self) -> "H28SealedRecordBinding":
        del self
        raise TypeError("H28 sealed record binding cannot be copied.")

    def __deepcopy__(self, memo: object) -> "H28SealedRecordBinding":
        del self, memo
        raise TypeError("H28 sealed record binding cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H28 sealed record binding cannot be serialized.")


def require_h28_scientific_capability(value: object) -> None:
    """Fail before any payload, NumPy, filesystem, or scientific access."""

    del value
    raise PermissionError("H28 scientific capability is not issued.")


def require_h28_sealed_record_binding(value: object) -> None:
    """Fail until a future authority attests one exact population-index row."""

    del value
    raise PermissionError("H28 sealed record binding is not issued.")


__all__ = ["H28ScientificCapability", "H28SealedRecordBinding",
           "H28_SEALED_RECORD_BINDING_FIELDS"]
