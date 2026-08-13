"""Dormant H27 real-publication implementation boundary.

The implementation validates the exact reviewed administrative chain and the
full publication protocol through injected, effect-free probes.  Its only
public edge remains a native immutable barrier, so no destination can be
opened and no artifact can be created by this revision.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Callable, NamedTuple

from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as publication


_ROOT = Path(__file__).resolve().parents[2]
_ADMINISTRATIVE_INPUTS = (
    (
        "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract_identity_binding.json",
        "4b052086a2fa9a541bd337c454492f74efec3c31", 5047,
        "69d81538c3db9e293c45d32cd619b388025dc559905b9ea09e9549c5046b64b0",
    ),
    (
        "configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_implementation_contract_identity_binding_external_seal.json",
        "1b49b2ac3774638511cc2700afa108a6bd4d0db0", 3047,
        "dca1fa4aa1ec478d51f3cfe061ae0fb0a1b8a6077c36e58cd1c9a7616c6881f2",
    ),
)
_UPSTREAM_BINDING_PATH = (
    _ROOT / "configs/harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant_identity_binding.json"
)
_REQUIREMENTS = (
    "exact_git_head_and_clean_worktree_before_any_future_execution",
    "exact_contract_and_external_seal_bytes",
    "exact_four_dormant_simulator_artifacts",
    "exact_forty_eight_transitive_upstream_artifacts",
    "all_fifty_two_identities_rehashed_before_any_future_adapter",
    "all_seven_public_edges_native_and_closed_until_separate_authorization",
    "destination_explicitly_defined_only_in_a_separately_reviewed_implementation_contract",
    "destination_absent_before_any_one_shot_consumption",
    "one_shot_consumed_immediately_before_first_real_create_exclusive_attempt",
    "create_exclusive_without_overwrite",
    "canonical_bytes_fully_written_flushed_and_fsynced",
    "atomic_same_filesystem_visibility_without_replace",
    "published_bytes_reopened_and_rehashed",
    "parent_directory_fsync_after_visibility",
    "success_or_post_consumption_failure_terminal_without_retry",
    "no_connection_authority_materializer_or_science_before_separate_authorization",
    "no_locked_test_training_or_calibration",
)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    raw = (_ROOT / relative).resolve(strict=True).read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 dormant real-publication administrative drift: {relative}.")
    return raw


def _verify_fifty_four_inputs() -> None:
    for item in _ADMINISTRATIVE_INPUTS:
        _verify_exact(*item)
    binding = json.loads(_verify_exact(*_ADMINISTRATIVE_INPUTS[0]))
    upstream = json.loads(_UPSTREAM_BINDING_PATH.read_bytes())
    roots = (binding["reviewed_contract"], binding["contract_external_seal"])
    simulator = binding["reviewed_and_sealed_dormant_publication_simulator"]
    inherited = upstream["upstream_entries"]
    if type(simulator) is not list or len(simulator) != 4:
        raise PermissionError("H27 dormant real-publication simulator binding malformed.")
    if type(inherited) is not list or len(inherited) != 48:
        raise PermissionError("H27 dormant real-publication upstream binding malformed.")
    entries = [*roots, *simulator, *inherited]
    paths: set[str] = set()
    for item in entries:
        if type(item) is not dict or not {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(item):
            raise PermissionError("H27 dormant real-publication identity malformed.")
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
        paths.add(item["path"])
    if len(entries) != 54 or len(paths) != 54:
        raise PermissionError("H27 dormant real-publication requires exactly 54 unique identities.")


class H27DormantRealPublicationAdapters(NamedTuple):
    observe_requirements: Callable[[], dict[str, bool]]
    observe_destination_absent: Callable[[], bool]
    probe_create_exclusive: Callable[[bytes], tuple[bool, bool]]
    probe_full_write_flush_and_file_fsync: Callable[[], tuple[bool, bool, bool]]
    probe_atomic_visibility_without_replace: Callable[[], bool]
    probe_reopen_and_rehash: Callable[[bytes], bool]
    probe_parent_directory_fsync: Callable[[], bool]
    finalize: Callable[[object, bytes], object]


@dataclass(frozen=True)
class H27DormantRealPublicationTrace:
    verified_identities: int
    payload_sha256: str
    destination_path: None
    artifact_created: bool
    artifact_written: bool
    composition_to_bridge_connected: bool
    bridge_to_materializer_connected: bool
    materializer_invocations: int
    science_invocations: int
    terminal: bool


def _exercise_dormant_real_publication(
    ticket: object,
    exact_ticket: object,
    adapters: H27DormantRealPublicationAdapters,
) -> H27DormantRealPublicationTrace:
    """Exercise every guard with effect-free probes; never publish."""
    _verify_fifty_four_inputs()
    if ticket is not exact_ticket:
        raise PermissionError("H27 dormant real-publication requires exact ticket identity.")
    payload, raw = publication._canonical_payload(ticket)
    observed = adapters.observe_requirements()
    if type(observed) is not dict or tuple(observed) != _REQUIREMENTS:
        raise PermissionError("H27 dormant real-publication requirements malformed.")
    if any(observed[name] is not True for name in _REQUIREMENTS):
        raise PermissionError("H27 dormant real-publication requirements incomplete.")
    if adapters.observe_destination_absent() is not True:
        raise PermissionError("H27 dormant real-publication destination must remain absent.")
    ticket._consume(ticket)
    if adapters.probe_create_exclusive(raw) != (False, False):
        raise PermissionError("H27 dormant real-publication probe must not create or write.")
    if adapters.probe_full_write_flush_and_file_fsync() != (False, False, False):
        raise PermissionError("H27 dormant real-publication probe must not write, flush, or fsync.")
    if adapters.probe_atomic_visibility_without_replace() is not False:
        raise PermissionError("H27 dormant real-publication probe must not publish.")
    if adapters.probe_reopen_and_rehash(raw) is not False:
        raise PermissionError("H27 dormant real-publication probe must not reopen an artifact.")
    if adapters.probe_parent_directory_fsync() is not False:
        raise PermissionError("H27 dormant real-publication probe must not fsync a directory.")
    if adapters.finalize(ticket, raw) is not ticket:
        raise PermissionError("H27 dormant real-publication finalizer must preserve exact ticket identity.")
    if payload["terminal"] is not True:
        raise PermissionError("H27 dormant real-publication payload must be terminal.")
    return H27DormantRealPublicationTrace(
        54, hashlib.sha256(raw).hexdigest(), None, False, False, False, False, 0, 0, True
    )


publish_h27_future_bridge_activation_artifact_real = ().__getitem__
