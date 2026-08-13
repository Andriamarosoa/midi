"""Strictly dormant H27 future-bridge compatibility harness.

The private harness accepts only a mock representing the exact successful
step-11 binding.  It reattests every sealed administrative byte before any
semantic adapter and terminates before a materializer or scientific call.  The
public edge is an immutable native barrier.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_BRIDGE_CHAIN_INPUTS = (
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_contract.json", "c03e81b9532c9d3c2ef95bec3ca58e4daf3a0bca", 12630, "fa394ba1567e021aeb46f714837f52b9a63fd43cd56ff1440a962884dc274fd1"),
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_contract_external_seal.json", "c0a09c2eabe08ae6387ad3ef19d038a777295978", 3661, "952eae119585349454efe4f6585e0954c1197b5d0ce0bf0cb9000ecab8263376"),
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding.json", "5d9c1cb07d147d3ce0ad07f998c81ef3ea7950b8", 9690, "a67b3d3beca48d52fff756c959aa18ae7be752acd0a26865f2f861c9e32909e5"),
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding_external_seal.json", "686b2ea3c86ef91c13e67c3ea5af00867282751e", 3928, "29735327c4581f9f7a0b0ddd01f150a7a2fda2d50bc2dcefb8b75eed1f37d72f"),
)
_COMPATIBILITY_CONTRACT_PATH = _ROOT / _BRIDGE_CHAIN_INPUTS[0][0]


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    raw = (_ROOT / relative).resolve(strict=True).read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 dormant bridge administrative binding drift: {relative}.")
    return raw


def _verify_bridge_chain() -> None:
    for binding in _BRIDGE_CHAIN_INPUTS:
        _verify_exact(*binding)


def _verify_twenty_predecessors() -> None:
    raw = _verify_exact(*_BRIDGE_CHAIN_INPUTS[0])
    contract = json.loads(raw)
    if type(contract) is not dict or type(contract.get("sealed_predecessors")) is not dict:
        raise PermissionError("H27 dormant bridge predecessor contract is malformed.")
    predecessors = contract["sealed_predecessors"]
    if len(predecessors) != 20:
        raise PermissionError("H27 dormant bridge requires exactly twenty sealed predecessors.")
    for key, binding in predecessors.items():
        if type(key) is not str or type(binding) is not dict or set(binding) != {
            "path", "git_blob_sha1", "size_bytes", "raw_sha256"
        }:
            raise PermissionError("H27 dormant bridge predecessor binding is malformed.")
        _verify_exact(
            binding["path"], binding["git_blob_sha1"], binding["size_bytes"], binding["raw_sha256"]
        )


class _H27DormantStep11Binding:
    """Synthetic immutable binding with an object-owned terminal right."""

    __slots__ = (
        "_authority_sha256",
        "_claim_sha256",
        "_materializer_blob",
        "_invocation_nonce",
        "_process_id",
        "_code_identity_sha256",
        "_consume_bridge_right",
    )

    def __new__(cls, *args: object, **kwargs: object) -> "_H27DormantStep11Binding":
        del cls, args, kwargs
        raise PermissionError("H27 dormant step-11 binding has no public constructor.")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise TypeError("H27 dormant step-11 binding is immutable.")

    def __copy__(self) -> "_H27DormantStep11Binding":
        del self
        raise TypeError("H27 dormant step-11 binding cannot be copied.")

    def __deepcopy__(self, memo: object) -> "_H27DormantStep11Binding":
        del self, memo
        raise TypeError("H27 dormant step-11 binding cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H27 dormant step-11 binding cannot be serialized.")

    authority_sha256 = property(lambda self: self._authority_sha256)
    claim_sha256 = property(lambda self: self._claim_sha256)
    materializer_blob = property(lambda self: self._materializer_blob)
    invocation_nonce = property(lambda self: self._invocation_nonce)
    process_id = property(lambda self: self._process_id)
    code_identity_sha256 = property(lambda self: self._code_identity_sha256)


def _make_mock_step11_binding(
    authority_sha256: str,
    claim_sha256: str,
    materializer_blob: str,
    invocation_nonce: str,
    process_id: int,
    code_identity_sha256: str,
) -> _H27DormantStep11Binding:
    binding = object.__new__(_H27DormantStep11Binding)
    for name, value in (
        ("_authority_sha256", authority_sha256),
        ("_claim_sha256", claim_sha256),
        ("_materializer_blob", materializer_blob),
        ("_invocation_nonce", invocation_nonce),
        ("_process_id", process_id),
        ("_code_identity_sha256", code_identity_sha256),
    ):
        object.__setattr__(binding, name, value)
    right_consumer = _single_use_local_right(binding)
    next(right_consumer)
    object.__setattr__(binding, "_consume_bridge_right", right_consumer.send)
    return binding


class H27DormantBridgeAdapters(NamedTuple):
    verify_contract_semantics: Callable[[], None]
    verify_predecessor_semantics: Callable[[], None]
    verify_module_identities: Callable[[], None]
    observe_authority_claim: Callable[[], tuple[str, str, bool]]
    observe_runtime_binding: Callable[[], tuple[str, int, str]]
    observe_materializer: Callable[[], tuple[str, bool]]
    derive_simulated_materializer_capability: Callable[[object, _H27DormantStep11Binding], object]


@dataclass(frozen=True)
class H27DormantBridgeTrace:
    steps: tuple[str, ...]
    binding_attested: bool
    local_invocation_right_consumed: bool
    simulated_materializer_capability_derived: bool
    materializer_invocations: int
    science_invocations: int
    terminal: bool


class _SimulatedLocalInvocationRight:
    __slots__ = ()


def _single_use_local_right(exact_binding: _H27DormantStep11Binding) -> object:
    request = yield
    if request is not exact_binding:
        raise PermissionError("H27 dormant bridge requires the exact consumed binding identity.")
    yield object.__new__(_SimulatedLocalInvocationRight)


def _require_hex_sha(value: object, field: str) -> None:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PermissionError(f"H27 dormant bridge invalid {field}.")


def _require_step11_binding(binding: object) -> _H27DormantStep11Binding:
    if type(binding) is not _H27DormantStep11Binding:
        raise PermissionError("H27 dormant bridge rejects caller-built or nonexact binding types.")
    for field in (
        "authority_sha256", "claim_sha256", "invocation_nonce", "code_identity_sha256"
    ):
        _require_hex_sha(getattr(binding, field), field)
    if type(binding.materializer_blob) is not str or len(binding.materializer_blob) != 40:
        raise PermissionError("H27 dormant bridge invalid materializer blob.")
    if any(c not in "0123456789abcdef" for c in binding.materializer_blob):
        raise PermissionError("H27 dormant bridge invalid materializer blob.")
    if type(binding.process_id) is not int or binding.process_id <= 0:
        raise PermissionError("H27 dormant bridge invalid process id.")
    return binding


def _exercise_dormant_bridge(
    exact_step11_binding: _H27DormantStep11Binding,
    received_step11_binding: object,
    adapters: H27DormantBridgeAdapters,
) -> H27DormantBridgeTrace:
    """Exercise only the reviewed compatibility boundary with synthetic facts."""

    exact = _require_step11_binding(exact_step11_binding)
    if received_step11_binding is not exact:
        raise PermissionError("H27 dormant bridge requires the exact successful step-11 return.")
    completed = ["receive_exact_step11_binding"]

    _verify_bridge_chain()
    adapters.verify_contract_semantics()
    completed.append("verify_bridge_contract_chain")

    _verify_twenty_predecessors()
    adapters.verify_predecessor_semantics()
    completed.append("verify_twenty_predecessors")

    adapters.verify_module_identities()
    completed.append("verify_module_identities")

    authority_sha, claim_sha, claim_current = adapters.observe_authority_claim()
    if not claim_current or authority_sha != exact.authority_sha256 or claim_sha != exact.claim_sha256:
        raise PermissionError("H27 dormant bridge stale or mismatched authority/claim.")
    completed.append("verify_authority_claim")

    nonce, process_id, code_identity = adapters.observe_runtime_binding()
    if (
        nonce != exact.invocation_nonce
        or process_id != exact.process_id
        or code_identity != exact.code_identity_sha256
    ):
        raise PermissionError("H27 dormant bridge nonce/process/code identity mismatch.")
    completed.append("verify_nonce_process_code_identity")

    materializer_blob, barrier_closed = adapters.observe_materializer()
    if materializer_blob != exact.materializer_blob or barrier_closed is not True:
        raise PermissionError("H27 dormant bridge materializer identity or barrier mismatch.")
    completed.append("verify_materializer_identity_and_barrier")

    try:
        right = exact._consume_bridge_right(exact)
    except StopIteration as exc:
        raise PermissionError("H27 dormant bridge binding is already terminally consumed.") from exc
    completed.append("consume_simulated_local_invocation_right")

    simulated_capability = adapters.derive_simulated_materializer_capability(right, exact)
    if simulated_capability is None:
        raise PermissionError("H27 dormant bridge simulated materializer capability missing.")
    completed.append("derive_simulated_materializer_capability")

    return H27DormantBridgeTrace(
        steps=tuple(completed),
        binding_attested=True,
        local_invocation_right_consumed=True,
        simulated_materializer_capability_derived=True,
        materializer_invocations=0,
        science_invocations=0,
        terminal=True,
    )


_DORMANT_NATIVE_BARRIER = ().__getitem__
invoke_h27_future_bridge = _DORMANT_NATIVE_BARRIER


__all__ = ["invoke_h27_future_bridge"]
