"""Strictly dormant H27 operational activation/connection gate.

The private harness reattests the complete reviewed administrative chain and
exercises only synthetic fail-closed observations.  It cannot create an
activation, connect either edge, invoke the materializer, or execute science.
The public edge is an immutable native barrier.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_ACTIVATION_CONNECTION_INPUTS = (
    ("configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_contract.json", "d084467fa316f308e78a1235280c4d0dae3c8324", 13281, "7565b0faccd5aa40855196cf15f8468bdd85a081292f301811fa14964ddba403"),
    ("configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_contract_external_seal.json", "a76af4832bdf8a73a3eca448c9c8970e706d35a7", 4090, "7d8b693389b92593c25730d654013f5722a80f0fcc8641b4966c6557fd8f2196"),
    ("configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_identity_binding.json", "cf7e0eb546970e1535eb1f5116f7587d691d1724", 12720, "d43a2bdce4bc221bb44ca23897819e0cd247ed2ed488185cf87bc745738a005a"),
    ("configs/harmonic_censoring_h27_future_bridge_operational_activation_connection_identity_binding_external_seal.json", "0ff52a2aad439828555b321de39d1b27fbe7330d", 5155, "2b9834e446747a174b5b44d61cb0d0011c5f84e5d86395f6a113525d65404d19"),
)
_BRIDGE_INPUTS = (
    ("src/polyphonic/harmonic_censoring_h27_future_bridge_dormant.py", "6cc65097b636ed35eeedf5675457c4f599cb811d", 10443, "23e33bc4f81610c84fe0cb7bcc174d9176b531cae5559ad0b904edf257b97777"),
    ("configs/harmonic_censoring_h27_future_bridge_dormant_external_review_seal.json", "e6eae1e6a91bd959c8ddcbc810f8c0cc7707e3b6", 2829, "7d281ab1ce55bfb9bb3a75b725697754343b98a8c52e9e4a7d805f6ad921dd42"),
    ("configs/harmonic_censoring_h27_future_bridge_dormant_identity_binding.json", "57426a89a4c05093c7bf2dc5867383d4620aa1a6", 11020, "285123266ffec33605d997ff5e80ccf7feca81d13b96fc6f3bea543f9e700466"),
    ("configs/harmonic_censoring_h27_future_bridge_dormant_identity_binding_external_seal.json", "6e77dccebc771a37e41a24a2edf82b62dbc6039d", 2994, "e155a3bc8afd8b6f6dc64042c65bbb3bd377ae2d549eddb6fdde2b44a8b5da2a"),
)
_COMPATIBILITY_INPUTS = (
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_contract.json", "c03e81b9532c9d3c2ef95bec3ca58e4daf3a0bca", 12630, "fa394ba1567e021aeb46f714837f52b9a63fd43cd56ff1440a962884dc274fd1"),
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_contract_external_seal.json", "c0a09c2eabe08ae6387ad3ef19d038a777295978", 3661, "952eae119585349454efe4f6585e0954c1197b5d0ce0bf0cb9000ecab8263376"),
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding.json", "5d9c1cb07d147d3ce0ad07f998c81ef3ea7950b8", 9690, "a67b3d3beca48d52fff756c959aa18ae7be752acd0a26865f2f861c9e32909e5"),
    ("configs/harmonic_censoring_h27_future_bridge_compatibility_identity_binding_external_seal.json", "686b2ea3c86ef91c13e67c3ea5af00867282751e", 3928, "29735327c4581f9f7a0b0ddd01f150a7a2fda2d50bc2dcefb8b75eed1f37d72f"),
)
_ACTIVATION_CONNECTION_BINDING_PATH = _ROOT / _ACTIVATION_CONNECTION_INPUTS[2][0]
_MATERIALIZER_BLOB = "79f399359e366781f9526098c98a93cca71b1b49"


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    raw = (_ROOT / relative).resolve(strict=True).read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 dormant activation/connection administrative drift: {relative}.")
    return raw


def _verify_exact_group(group: tuple[tuple[str, str, int, str], ...]) -> None:
    for binding in group:
        _verify_exact(*binding)


def _verify_twenty_predecessors() -> None:
    raw = _verify_exact(*_ACTIVATION_CONNECTION_INPUTS[2])
    binding = json.loads(raw)
    if type(binding) is not dict or type(binding.get("byte_identical_predecessor_chains")) is not dict:
        raise PermissionError("H27 dormant activation/connection binding is malformed.")
    predecessors = binding["byte_identical_predecessor_chains"]
    if len(predecessors) != 20:
        raise PermissionError("H27 dormant activation/connection requires twenty predecessors.")
    for key, predecessor in predecessors.items():
        if type(key) is not str or type(predecessor) is not dict or set(predecessor) != {
            "path", "git_blob_sha1", "size_bytes", "raw_sha256"
        }:
            raise PermissionError("H27 dormant activation/connection predecessor is malformed.")
        _verify_exact(
            predecessor["path"],
            predecessor["git_blob_sha1"],
            predecessor["size_bytes"],
            predecessor["raw_sha256"],
        )


class _H27DormantActivationConnectionTicket:
    """Synthetic immutable request with an object-owned terminal right."""

    __slots__ = (
        "_step11_binding",
        "_authority_sha256",
        "_claim_sha256",
        "_invocation_nonce",
        "_process_id",
        "_code_identity_sha256",
        "_consume_gate_right",
    )

    def __new__(cls, *args: object, **kwargs: object) -> "_H27DormantActivationConnectionTicket":
        del cls, args, kwargs
        raise PermissionError("H27 dormant activation/connection ticket has no public constructor.")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise TypeError("H27 dormant activation/connection ticket is immutable.")

    def __copy__(self) -> "_H27DormantActivationConnectionTicket":
        del self
        raise TypeError("H27 dormant activation/connection ticket cannot be copied.")

    def __deepcopy__(self, memo: object) -> "_H27DormantActivationConnectionTicket":
        del self, memo
        raise TypeError("H27 dormant activation/connection ticket cannot be copied.")

    def __reduce__(self) -> object:
        del self
        raise TypeError("H27 dormant activation/connection ticket cannot be serialized.")

    step11_binding = property(lambda self: self._step11_binding)
    authority_sha256 = property(lambda self: self._authority_sha256)
    claim_sha256 = property(lambda self: self._claim_sha256)
    invocation_nonce = property(lambda self: self._invocation_nonce)
    process_id = property(lambda self: self._process_id)
    code_identity_sha256 = property(lambda self: self._code_identity_sha256)


class _SyntheticGateRight:
    __slots__ = ()


def _single_use_gate_right(exact_ticket: _H27DormantActivationConnectionTicket) -> object:
    request = yield
    if request is not exact_ticket:
        raise PermissionError("H27 dormant activation/connection requires exact ticket identity.")
    yield object.__new__(_SyntheticGateRight)


def _make_mock_activation_connection_ticket(
    step11_binding: object,
    authority_sha256: str,
    claim_sha256: str,
    invocation_nonce: str,
    process_id: int,
    code_identity_sha256: str,
) -> _H27DormantActivationConnectionTicket:
    ticket = object.__new__(_H27DormantActivationConnectionTicket)
    for name, value in (
        ("_step11_binding", step11_binding),
        ("_authority_sha256", authority_sha256),
        ("_claim_sha256", claim_sha256),
        ("_invocation_nonce", invocation_nonce),
        ("_process_id", process_id),
        ("_code_identity_sha256", code_identity_sha256),
    ):
        object.__setattr__(ticket, name, value)
    right = _single_use_gate_right(ticket)
    next(right)
    object.__setattr__(ticket, "_consume_gate_right", right.send)
    return ticket


def _require_hex_sha(value: object, field: str) -> None:
    if type(value) is not str or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise PermissionError(f"H27 dormant activation/connection invalid {field}.")


def _require_ticket(ticket: object) -> _H27DormantActivationConnectionTicket:
    if type(ticket) is not _H27DormantActivationConnectionTicket:
        raise PermissionError("H27 dormant activation/connection rejects nonexact ticket types.")
    if ticket.step11_binding is None:
        raise PermissionError("H27 dormant activation/connection missing step-11 binding identity.")
    for field in ("authority_sha256", "claim_sha256", "invocation_nonce", "code_identity_sha256"):
        _require_hex_sha(getattr(ticket, field), field)
    if type(ticket.process_id) is not int or ticket.process_id <= 0:
        raise PermissionError("H27 dormant activation/connection invalid process id.")
    return ticket


class H27DormantActivationConnectionAdapters(NamedTuple):
    verify_git_and_code_identities: Callable[[], None]
    observe_step11_binding: Callable[[], tuple[object, bool]]
    observe_authority_claim: Callable[[], tuple[str, str, bool]]
    observe_runtime_binding: Callable[[], tuple[str, int, str]]
    observe_bridge_terminal_state: Callable[[], bool]
    observe_materializer: Callable[[], tuple[str, bool]]
    observe_composition_to_bridge: Callable[[], tuple[bool, bool]]
    observe_bridge_to_materializer: Callable[[], tuple[bool, bool]]
    finalize_synthetic_gate: Callable[[object], object]


@dataclass(frozen=True)
class H27DormantActivationConnectionTrace:
    steps: tuple[str, ...]
    activation_created: bool
    composition_to_bridge_connected: bool
    bridge_to_materializer_connected: bool
    materializer_invocations: int
    science_invocations: int
    terminal: bool


def _exercise_dormant_activation_connection(
    exact_ticket: _H27DormantActivationConnectionTicket,
    received_ticket: object,
    adapters: H27DormantActivationConnectionAdapters,
) -> H27DormantActivationConnectionTrace:
    """Exercise synthetic checks only and terminate with both edges closed."""

    exact = _require_ticket(exact_ticket)
    if received_ticket is not exact:
        raise PermissionError("H27 dormant activation/connection requires exact ticket identity.")
    completed = ["receive_exact_activation_connection_ticket"]

    _verify_exact_group(_ACTIVATION_CONNECTION_INPUTS)
    _verify_exact_group(_BRIDGE_INPUTS)
    _verify_exact_group(_COMPATIBILITY_INPUTS)
    _verify_twenty_predecessors()
    completed.append("verify_thirty_two_sealed_administrative_inputs")

    adapters.verify_git_and_code_identities()
    completed.append("verify_git_and_code_identities")

    step11_binding, terminally_consumed = adapters.observe_step11_binding()
    if step11_binding is not exact.step11_binding or terminally_consumed is not True:
        raise PermissionError("H27 dormant activation/connection step-11 identity or terminal state mismatch.")
    completed.append("verify_exact_terminal_step11_binding")

    authority_sha, claim_sha, claim_current = adapters.observe_authority_claim()
    if not claim_current or authority_sha != exact.authority_sha256 or claim_sha != exact.claim_sha256:
        raise PermissionError("H27 dormant activation/connection authority or claim mismatch.")
    completed.append("verify_authority_claim")

    nonce, process_id, code_identity = adapters.observe_runtime_binding()
    if nonce != exact.invocation_nonce or process_id != exact.process_id or code_identity != exact.code_identity_sha256:
        raise PermissionError("H27 dormant activation/connection nonce, process, or code identity mismatch.")
    completed.append("verify_nonce_process_code_identity")

    if adapters.observe_bridge_terminal_state() is not True:
        raise PermissionError("H27 dormant activation/connection bridge is not terminal.")
    completed.append("verify_bridge_terminal_state")

    materializer_blob, barrier_closed = adapters.observe_materializer()
    if materializer_blob != _MATERIALIZER_BLOB or barrier_closed is not True:
        raise PermissionError("H27 dormant activation/connection materializer identity or barrier mismatch.")
    completed.append("verify_materializer_identity_and_barrier")

    composition_connected, composition_authorized = adapters.observe_composition_to_bridge()
    if composition_connected is not False or composition_authorized is not False:
        raise PermissionError("H27 dormant activation/connection composition-to-bridge edge must remain closed.")
    completed.append("verify_composition_to_bridge_closed")

    materializer_connected, materializer_authorized = adapters.observe_bridge_to_materializer()
    if materializer_connected is not False or materializer_authorized is not False:
        raise PermissionError("H27 dormant activation/connection bridge-to-materializer edge must remain closed.")
    completed.append("verify_bridge_to_materializer_closed")

    try:
        right = exact._consume_gate_right(exact)
    except StopIteration as exc:
        raise PermissionError("H27 dormant activation/connection ticket is already terminally consumed.") from exc
    completed.append("consume_synthetic_gate_right")

    finalized = adapters.finalize_synthetic_gate(right)
    if finalized is not exact:
        raise PermissionError("H27 dormant activation/connection finalizer returned a foreign ticket.")
    completed.append("finalize_synthetic_gate_without_activation")

    return H27DormantActivationConnectionTrace(
        steps=tuple(completed),
        activation_created=False,
        composition_to_bridge_connected=False,
        bridge_to_materializer_connected=False,
        materializer_invocations=0,
        science_invocations=0,
        terminal=True,
    )


_DORMANT_NATIVE_BARRIER = ().__getitem__
activate_and_connect_h27_future_bridge = _DORMANT_NATIVE_BARRIER


__all__ = ["activate_and_connect_h27_future_bridge"]
