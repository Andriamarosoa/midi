"""Unissuable process-local capability for dormant H27 science.

No factory or issuer is present in the reviewed H27 stack.  The engine and the
independent recomputer both require an identity registered by a future,
separately reviewed authority.  The registry is intentionally immutable and
empty here, so neither boundary can execute.
"""
from __future__ import annotations


class H27ScientificCapability:
    """Nominal type only; construction never grants H27 scientific access."""

    __slots__ = ("__weakref__",)

    def __new__(cls, *args: object, **kwargs: object) -> "H27ScientificCapability":
        del cls, args, kwargs
        raise PermissionError("H27 scientific capability has no issuer.")

    def __copy__(self) -> "H27ScientificCapability":
        del self
        raise TypeError("H27 scientific capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> "H27ScientificCapability":
        del self, memo
        raise TypeError("H27 scientific capability cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H27 scientific capability cannot be serialized.")


# A future reviewed authority must replace this module rather than mutate this
# collection.  Keeping it a tuple prevents tests or callers from registering a
# forged instance in the dormant implementation.
_ISSUED_CAPABILITY_IDENTITIES: tuple[int, ...] = ()


def require_h27_scientific_capability(value: object) -> None:
    """Fail before any payload, NumPy, filesystem, or scientific access."""

    if type(value) is not H27ScientificCapability or id(value) not in _ISSUED_CAPABILITY_IDENTITIES:
        raise PermissionError("H27 scientific capability is not issued.")


__all__ = ["H27ScientificCapability"]
