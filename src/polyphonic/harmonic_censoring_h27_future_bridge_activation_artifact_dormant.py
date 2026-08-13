"""Dormant in-memory H27 activation-artifact construction harness.

No filesystem publication or operational edge exists.  The private harness is
synthetic and the public edge is an immutable native barrier.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_ACTIVATION_ARTIFACT_INPUTS = (
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_contract.json", "f7baf8c16eb138e06e25dd647de3b516e094d732", 17525, "a84427a24adba80a730aad9fdbd53434a47d29c6a4685661f87797a7e0ec68a0"),
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_contract_external_seal.json", "0e2f5558876598de1eb7c888f358a8d8dde7e04d", 3296, "9d2de17519af8e8343f0097cbba353225bd2f36844e8d15c328e78f59a6dbd20"),
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_identity_binding.json", "b9e1e68dedcd15e59fa39ae2d499ce2c4a4c82e5", 16243, "103bfe54029c97dceb9a799f86f6cac2b9a6da5c95380f13c98025acc3c5e27c"),
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_identity_binding_external_seal.json", "72154deab7a8030dab726bfc62662f956184f4c6", 4591, "d4f13d28958c4e2d0960f5be8f13e829242e543d369ed40ce30e79805895d4a4"),
)
_ARTIFACT_BINDING_PATH = _ROOT / _ACTIVATION_ARTIFACT_INPUTS[2][0]
_FIELDS = (
    "schema_version", "activation_id", "population_namespace", "gate_module_blob",
    "gate_identity_binding_sha256", "authority_sha256", "claim_sha256",
    "invocation_nonce", "process_id", "code_identity_sha256", "materializer_blob",
    "terminal_step11_binding_sha256", "created_at_utc", "terminal",
)
_PRECONDITIONS = (
    "exact_git_head_and_clean_worktree",
    "exact_gate_module_seal_binding_and_binding_seal_bytes",
    "exact_activation_connection_bridge_compatibility_and_predecessor_bytes",
    "all_five_public_edges_native_and_closed",
    "exact_terminal_step11_binding_identity",
    "authority_and_claim_current_durable_and_byte_exact",
    "invocation_nonce_matches_authority_claim_and_binding",
    "process_id_matches_binding",
    "code_identity_sha256_matches_binding",
    "dormant_gate_owned_one_shot_right_unconsumed_before_creation",
    "exact_materializer_blob_and_native_closed_barrier",
    "both_future_connections_closed_and_unauthorized",
    "activation_destination_absent",
    "atomic_create_exclusive_publication_required",
    "second_creation_and_retry_after_consumption_forbidden",
    "every_check_before_any_artifact_write_or_scientific_access",
)
_GATE_BLOB = "d60470373ab261d585ab8f8ad40e3c94b3a03d23"
_GATE_BINDING_SHA = "a44d05b2e447f0f84167575354e7b54c0003651087d4b6660fc11d5540876504"
_MATERIALIZER_BLOB = "79f399359e366781f9526098c98a93cca71b1b49"


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    raw = (_ROOT / relative).resolve(strict=True).read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 dormant activation artifact administrative drift: {relative}.")
    return raw


def _verify_forty_inputs() -> None:
    for item in _ACTIVATION_ARTIFACT_INPUTS:
        _verify_exact(*item)
    binding = json.loads(_verify_exact(*_ACTIVATION_ARTIFACT_INPUTS[2]))
    groups = (
        binding.get("reviewed_dormant_gate_chain"),
        binding.get("activation_connection_chain"),
        binding.get("reviewed_bridge_chain"),
        binding.get("compatibility_chain"),
    )
    if any(type(group) is not dict or len(group) != 4 for group in groups):
        raise PermissionError("H27 dormant activation artifact dependency chain malformed.")
    predecessors = binding.get("byte_identical_predecessor_chains")
    if type(predecessors) is not dict or len(predecessors) != 20:
        raise PermissionError("H27 dormant activation artifact predecessor chain malformed.")
    for group in (*groups, predecessors):
        for item in group.values():
            if type(item) is not dict or not {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(item):
                raise PermissionError("H27 dormant activation artifact dependency malformed.")
            _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])


class _H27DormantActivationArtifactTicket:
    __slots__ = ("_values", "_consume")

    def __new__(cls, *args: object, **kwargs: object) -> "_H27DormantActivationArtifactTicket":
        del cls, args, kwargs
        raise PermissionError("H27 dormant activation artifact ticket has no public constructor.")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise TypeError("H27 dormant activation artifact ticket is immutable.")

    def __copy__(self) -> object:
        raise TypeError("H27 dormant activation artifact ticket cannot be copied.")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        raise TypeError("H27 dormant activation artifact ticket cannot be copied.")

    def __reduce__(self) -> object:
        raise TypeError("H27 dormant activation artifact ticket cannot be serialized.")

    values = property(lambda self: self._values)


def _one_shot(ticket: _H27DormantActivationArtifactTicket) -> object:
    received = yield
    if received is not ticket:
        raise PermissionError("H27 dormant activation artifact requires exact ticket identity.")
    yield object()


def _make_mock_ticket(**values: object) -> _H27DormantActivationArtifactTicket:
    ticket = object.__new__(_H27DormantActivationArtifactTicket)
    object.__setattr__(ticket, "_values", tuple(values.get(field) for field in _FIELDS))
    consumer = _one_shot(ticket)
    next(consumer)
    object.__setattr__(ticket, "_consume", consumer.send)
    return ticket


def _hex(value: object, length: int) -> bool:
    return type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value)


def _payload(ticket: object) -> dict[str, object]:
    if type(ticket) is not _H27DormantActivationArtifactTicket:
        raise PermissionError("H27 dormant activation artifact rejects nonexact ticket types.")
    payload = dict(zip(_FIELDS, ticket.values))
    if list(payload) != list(_FIELDS) or payload["schema_version"] != 1:
        raise PermissionError("H27 dormant activation artifact schema mismatch.")
    if type(payload["activation_id"]) is not str or not payload["activation_id"]:
        raise PermissionError("H27 dormant activation artifact id invalid.")
    if payload["population_namespace"] != "H27_SYNTHETIC_V1":
        raise PermissionError("H27 dormant activation artifact namespace mismatch.")
    if payload["gate_module_blob"] != _GATE_BLOB or payload["gate_identity_binding_sha256"] != _GATE_BINDING_SHA:
        raise PermissionError("H27 dormant activation artifact gate identity mismatch.")
    for field in ("gate_identity_binding_sha256", "authority_sha256", "claim_sha256", "invocation_nonce", "code_identity_sha256", "terminal_step11_binding_sha256"):
        if not _hex(payload[field], 64):
            raise PermissionError(f"H27 dormant activation artifact invalid {field}.")
    if payload["materializer_blob"] != _MATERIALIZER_BLOB or not _hex(payload["materializer_blob"], 40):
        raise PermissionError("H27 dormant activation artifact materializer mismatch.")
    if type(payload["process_id"]) is not int or payload["process_id"] <= 0:
        raise PermissionError("H27 dormant activation artifact process id invalid.")
    if type(payload["created_at_utc"]) is not str or not payload["created_at_utc"].endswith("Z"):
        raise PermissionError("H27 dormant activation artifact creation time invalid.")
    if payload["terminal"] is not True:
        raise PermissionError("H27 dormant activation artifact terminal state invalid.")
    return payload


class H27DormantActivationArtifactAdapters(NamedTuple):
    observe_preconditions: Callable[[], dict[str, bool]]
    observe_connections: Callable[[], tuple[bool, bool]]
    simulate_atomic_create_exclusive: Callable[[dict[str, object]], tuple[bool, bool]]
    finalize: Callable[[object, dict[str, object]], object]


@dataclass(frozen=True)
class H27DormantActivationArtifactTrace:
    payload_fields: tuple[str, ...]
    artifact_created: bool
    artifact_written: bool
    composition_to_bridge_connected: bool
    bridge_to_materializer_connected: bool
    materializer_invocations: int
    science_invocations: int
    terminal: bool


def _exercise_dormant_activation_artifact(
    exact_ticket: _H27DormantActivationArtifactTicket,
    received_ticket: object,
    adapters: H27DormantActivationArtifactAdapters,
) -> H27DormantActivationArtifactTrace:
    payload = _payload(exact_ticket)
    if received_ticket is not exact_ticket:
        raise PermissionError("H27 dormant activation artifact requires exact ticket identity.")
    _verify_forty_inputs()
    observed = adapters.observe_preconditions()
    if type(observed) is not dict or tuple(observed) != _PRECONDITIONS or any(observed[name] is not True for name in _PRECONDITIONS):
        raise PermissionError("H27 dormant activation artifact preconditions incomplete.")
    if adapters.observe_connections() != (False, False):
        raise PermissionError("H27 dormant activation artifact connections must remain closed.")
    if adapters.simulate_atomic_create_exclusive(payload) != (False, False):
        raise PermissionError("H27 dormant activation artifact simulation must not create or write.")
    try:
        right = exact_ticket._consume(exact_ticket)
    except StopIteration as exc:
        raise PermissionError("H27 dormant activation artifact ticket already terminally consumed.") from exc
    if adapters.finalize(right, payload) is not exact_ticket:
        raise PermissionError("H27 dormant activation artifact finalizer returned foreign ticket.")
    return H27DormantActivationArtifactTrace(
        payload_fields=tuple(payload), artifact_created=False, artifact_written=False,
        composition_to_bridge_connected=False, bridge_to_materializer_connected=False,
        materializer_invocations=0, science_invocations=0, terminal=True,
    )


_DORMANT_NATIVE_BARRIER = ().__getitem__
construct_h27_future_bridge_activation_artifact = _DORMANT_NATIVE_BARRIER


__all__ = ["construct_h27_future_bridge_activation_artifact"]
