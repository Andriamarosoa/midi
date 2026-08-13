"""Dormant synthetic simulation of future H27 activation-artifact publication.

The module contains no filesystem publication path.  Its private harness only
checks sealed bytes and exercises injected simulations; the public edge is a
native immutable barrier.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_PUBLICATION_INPUTS = (
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_contract.json", "d402672653b9e532db0ea302e5e314dfa1e5c4e3", 22288, "82b10aaed4161f189959b9ff85ed43ccabe5a1cf2b344b9ba7ec8909c1fa84f2"),
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_contract_external_seal.json", "28a2e397c50f3f7eac79a652d0c786443295f01e", 3628, "148829dfc1c9f8923a3ee0d3cd603476ae00bd10fbb191df2b166e8274f22db7"),
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_identity_binding.json", "c930376ebad5ab65689859b1534803e04e3daafe", 23269, "3798c27e2f83503907a2aefbac290e98c15d54063af48ab71e0ff7e1c97acc15"),
    ("configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_identity_binding_external_seal.json", "d0fc3359f446fde731714a3c37e45b331affd845", 3372, "e3c358aaf2bc401f54ad151b7a7638f32e7782be2946485392f8e885fc58ddb2"),
)
_BINDING_PATH = _ROOT / _PUBLICATION_INPUTS[2][0]
_FIELDS = (
    "schema_version", "activation_id", "population_namespace", "gate_module_blob",
    "gate_identity_binding_sha256", "authority_sha256", "claim_sha256",
    "invocation_nonce", "process_id", "code_identity_sha256", "materializer_blob",
    "terminal_step11_binding_sha256", "created_at_utc", "terminal",
)
_PRECONDITIONS = (
    "exact_git_head_and_clean_worktree",
    "exact_dormant_module_seal_binding_and_binding_seal_bytes",
    "exact_four_activation_artifact_and_thirty_six_dependency_bytes",
    "all_seven_public_edges_native_and_closed",
    "exact_in_memory_payload_schema_and_order",
    "created_at_utc_parseable_rfc3339_utc",
    "activation_id_unique_nonempty_and_explicitly_attested",
    "exact_terminal_step11_binding_identity",
    "authority_and_claim_current_durable_and_byte_exact",
    "invocation_nonce_process_id_and_code_identity_match",
    "exact_materializer_blob_and_native_closed_barrier",
    "both_future_connections_closed_and_unauthorized",
    "destination_absent_before_publication",
    "one_shot_right_consumed_immediately_before_first_write",
    "create_exclusive_without_overwrite_required",
    "canonical_bytes_fully_written_flushed_and_fsynced",
    "atomic_same_filesystem_visibility_without_replace",
    "published_bytes_reopened_and_rehashed",
    "parent_directory_fsync_after_visibility",
    "partial_or_failed_publication_terminal_without_retry",
    "every_check_before_any_artifact_write_or_scientific_access",
)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    raw = (_ROOT / relative).resolve(strict=True).read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 dormant publication administrative drift: {relative}.")
    return raw


def _verify_forty_eight_inputs() -> None:
    verified = {item[0] for item in _PUBLICATION_INPUTS}
    for item in _PUBLICATION_INPUTS:
        _verify_exact(*item)
    binding = json.loads(_verify_exact(*_PUBLICATION_INPUTS[2]))
    direct_keys = (
        "reviewed_dormant_activation_artifact_module",
        "dormant_activation_artifact_module_external_review_seal",
        "dormant_activation_artifact_module_identity_binding",
        "dormant_activation_artifact_module_identity_binding_external_seal",
        "reviewed_activation_artifact_contract",
        "activation_artifact_contract_external_seal",
        "activation_artifact_identity_binding",
        "activation_artifact_identity_binding_external_seal",
    )
    groups = tuple(binding[name] for name in (
        "reviewed_dormant_gate_chain", "activation_connection_chain",
        "reviewed_bridge_chain", "compatibility_chain",
    ))
    predecessors = binding.get("byte_identical_predecessor_chains")
    if any(type(group) is not dict or len(group) != 4 for group in groups):
        raise PermissionError("H27 dormant publication dependency chain malformed.")
    if type(predecessors) is not dict or len(predecessors) != 20:
        raise PermissionError("H27 dormant publication predecessor chain malformed.")
    items = [binding[name] for name in direct_keys]
    items.extend(item for group in (*groups, predecessors) for item in group.values())
    for item in items:
        if type(item) is not dict or not {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(item):
            raise PermissionError("H27 dormant publication dependency malformed.")
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
        verified.add(item["path"])
    if len(verified) != 48:
        raise PermissionError("H27 dormant publication requires exactly 48 unique sealed inputs.")


class _H27DormantPublicationTicket:
    __slots__ = ("_values", "_consume")

    def __new__(cls, *args: object, **kwargs: object) -> "_H27DormantPublicationTicket":
        del cls, args, kwargs
        raise PermissionError("H27 dormant publication ticket has no public constructor.")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise TypeError("H27 dormant publication ticket is immutable.")

    def __copy__(self) -> object:
        raise TypeError("H27 dormant publication ticket cannot be copied.")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        raise TypeError("H27 dormant publication ticket cannot be copied.")

    def __reduce__(self) -> object:
        raise TypeError("H27 dormant publication ticket cannot be serialized.")

    values = property(lambda self: self._values)


def _one_shot(ticket: _H27DormantPublicationTicket) -> object:
    received = yield
    if received is not ticket:
        raise PermissionError("H27 dormant publication requires exact ticket identity.")
    yield object()


def _make_mock_ticket(**values: object) -> _H27DormantPublicationTicket:
    ticket = object.__new__(_H27DormantPublicationTicket)
    object.__setattr__(ticket, "_values", tuple(values.get(field) for field in _FIELDS))
    consumer = _one_shot(ticket)
    next(consumer)
    object.__setattr__(ticket, "_consume", consumer.send)
    return ticket


def _hex(value: object, length: int) -> bool:
    return type(value) is str and len(value) == length and all(c in "0123456789abcdef" for c in value)


def _valid_utc(value: object) -> bool:
    if type(value) is not str or re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?Z", value) is None:
        return False
    try:
        parsed = datetime.fromisoformat(value[:-1] + "+00:00")
    except ValueError:
        return False
    return parsed.utcoffset() == timezone.utc.utcoffset(parsed)


def _canonical_payload(ticket: object) -> tuple[dict[str, object], bytes]:
    if type(ticket) is not _H27DormantPublicationTicket:
        raise PermissionError("H27 dormant publication rejects nonexact ticket types.")
    payload = dict(zip(_FIELDS, ticket.values))
    if tuple(payload) != _FIELDS or payload["schema_version"] != 1:
        raise PermissionError("H27 dormant publication payload schema invalid.")
    if type(payload["activation_id"]) is not str or not payload["activation_id"]:
        raise PermissionError("H27 dormant publication activation id invalid.")
    if payload["population_namespace"] != "H27_SYNTHETIC_V1" or type(payload["process_id"]) is not int or payload["process_id"] <= 0:
        raise PermissionError("H27 dormant publication identity invalid.")
    if not _valid_utc(payload["created_at_utc"]) or payload["terminal"] is not True:
        raise PermissionError("H27 dormant publication terminal timestamp invalid.")
    for field in ("gate_identity_binding_sha256", "authority_sha256", "claim_sha256", "code_identity_sha256", "terminal_step11_binding_sha256"):
        if not _hex(payload[field], 64):
            raise PermissionError(f"H27 dormant publication digest invalid: {field}.")
    for field in ("gate_module_blob", "materializer_blob"):
        if not _hex(payload[field], 40):
            raise PermissionError(f"H27 dormant publication blob invalid: {field}.")
    raw = (json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n").encode("utf-8")
    return payload, raw


class H27DormantPublicationAdapters(NamedTuple):
    observe_preconditions: Callable[[], dict[str, bool]]
    observe_activation_id_unique: Callable[[str], bool]
    observe_destination_absent: Callable[[], bool]
    simulate_create_exclusive: Callable[[bytes], tuple[bool, bool]]
    simulate_flush_and_file_fsync: Callable[[], tuple[bool, bool]]
    simulate_atomic_visibility_without_replace: Callable[[], bool]
    simulate_reopen_and_rehash: Callable[[bytes], bool]
    simulate_parent_directory_fsync: Callable[[], bool]
    finalize: Callable[[object, bytes], object]


@dataclass(frozen=True)
class H27DormantPublicationTrace:
    verified_inputs: int
    payload_fields: tuple[str, ...]
    canonical_payload_sha256: str
    artifact_created: bool
    artifact_written: bool
    composition_to_bridge_connected: bool
    bridge_to_materializer_connected: bool
    materializer_invocations: int
    science_invocations: int
    terminal: bool


def _exercise_dormant_publication(ticket: object, exact_ticket: object, adapters: H27DormantPublicationAdapters) -> H27DormantPublicationTrace:
    _verify_forty_eight_inputs()
    if ticket is not exact_ticket:
        raise PermissionError("H27 dormant publication requires exact ticket identity.")
    payload, raw = _canonical_payload(ticket)
    observed = adapters.observe_preconditions()
    if type(observed) is not dict or tuple(observed) != _PRECONDITIONS or any(observed[name] is not True for name in _PRECONDITIONS):
        raise PermissionError("H27 dormant publication preconditions incomplete.")
    if adapters.observe_activation_id_unique(payload["activation_id"]) is not True:
        raise PermissionError("H27 dormant publication id is not uniquely attested.")
    if adapters.observe_destination_absent() is not True:
        raise PermissionError("H27 dormant publication destination must be absent.")
    try:
        ticket._consume(ticket)
        if adapters.simulate_create_exclusive(raw) != (False, False):
            raise PermissionError("H27 dormant publication simulation must not create or write.")
        if adapters.simulate_flush_and_file_fsync() != (False, False):
            raise PermissionError("H27 dormant publication simulation must not flush or fsync.")
        if adapters.simulate_atomic_visibility_without_replace() is not False:
            raise PermissionError("H27 dormant publication simulation must not publish.")
        if adapters.simulate_reopen_and_rehash(raw) is not False:
            raise PermissionError("H27 dormant publication simulation must not reopen.")
        if adapters.simulate_parent_directory_fsync() is not False:
            raise PermissionError("H27 dormant publication simulation must not fsync a directory.")
        if adapters.finalize(ticket, raw) is not ticket:
            raise PermissionError("H27 dormant publication finalizer must return exact ticket.")
    except Exception:
        raise
    return H27DormantPublicationTrace(
        48, _FIELDS, hashlib.sha256(raw).hexdigest(), False, False, False, False, 0, 0, True
    )


simulate_h27_future_bridge_activation_artifact_publication = ().__getitem__

