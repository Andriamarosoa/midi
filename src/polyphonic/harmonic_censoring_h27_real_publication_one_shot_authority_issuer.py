"""Effect-free H27 one-shot authority issuer simulation.

The public function validates the exact reviewed administrative chain, builds
only canonical in-memory bytes, and accepts only injected adapters that attest
that no destination or filesystem effect occurred.  This revision cannot
issue an artifact, authority, claim, or capability.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Callable, NamedTuple


_ROOT = Path(__file__).resolve().parents[2]
_ADMINISTRATIVE_INPUTS = (
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_implementation_contract_identity_binding.json",
        "00e36c3c6415cb7c85aac7d84f0db477714937ae", 2759,
        "76aed93a2d5bfb713b1f68c3cb27f98384956a871b8089999beccb1db044c474",
    ),
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuer_implementation_contract_identity_binding_external_seal.json",
        "26811788a5ba6c45e272905c7d3912ce3e869717", 1128,
        "b2280384fe735f493a7eaeebb6a6c0813728e9dfaa5fbfaa20d4756379794753",
    ),
)
_ISSUER_ID = "h27-execution-codex-mac-primary"
_DESTINATION = "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json"
_PREDECESSOR_COUNT = 72
_PREDECESSOR_MANIFEST_SHA256 = "8861519a15a1765c681e0684aaf4bd8ea5e42fecc5479894e51e335c8d8f3a12"
_FIELD_ORDER = (
    "schema_version", "artifact_id", "issuer_id", "invocation_nonce",
    "issued_at_utc", "destination_path", "single_use",
    "predecessor_identity_count", "predecessor_manifest_sha256",
)


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    path = (_ROOT / relative).resolve(strict=True)
    path.relative_to(_ROOT.resolve(strict=True))
    raw = path.read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 effect-free issuer administrative drift: {relative}.")
    return raw


def _sixty_four(execution_chain: list[dict[str, object]]) -> list[dict[str, object]]:
    execution_contract = json.loads((_ROOT / str(execution_chain[0]["path"])).read_bytes())
    roots = execution_contract["reviewed_and_sealed_destination_contract_chain"]
    destination_binding = json.loads((_ROOT / roots[2]["path"]).read_bytes())
    destination_contract = json.loads((_ROOT / destination_binding["reviewed_contract"]["path"]).read_bytes())
    dormant = destination_contract["reviewed_and_sealed_dormant_boundary"]
    older = json.loads((_ROOT / destination_contract["transitive_identity_source"]["path"]).read_bytes())
    authorization_roots = older["upstream_roots"]
    authorization = json.loads((_ROOT / authorization_roots[0]["path"]).read_bytes())
    publication = [
        authorization["reviewed_contract"], authorization["contract_external_seal"],
        *authorization["reviewed_and_sealed_dormant_publication_simulator"],
    ]
    upstream = json.loads((_ROOT / authorization["transitive_upstream_binding"]["path"]).read_bytes())["upstream_entries"]
    return [*roots, *dormant, *authorization_roots, *publication, *upstream]


def _verify_seventy_eight_inputs() -> None:
    for item in _ADMINISTRATIVE_INPUTS:
        _verify_exact(*item)
    binding = json.loads(_verify_exact(*_ADMINISTRATIVE_INPUTS[0]))
    contract = json.loads((_ROOT / binding["reviewed_contract"]["path"]).read_bytes())
    roots = contract["reviewed_and_sealed_issuance_artifact_contract_chain"]
    artifact_contract = json.loads((_ROOT / roots[0]["path"]).read_bytes())
    authority_roots = artifact_contract["reviewed_and_sealed_one_shot_authority_chain"]
    authority = json.loads((_ROOT / authority_roots[0]["path"]).read_bytes())
    execution_roots = authority["reviewed_and_sealed_execution_authorization_chain"]
    entries = [binding["reviewed_contract"], binding["contract_external_seal"], *roots, *authority_roots, *execution_roots, *_sixty_four(execution_roots)]
    if len(entries) != 78 or len({item["path"] for item in entries}) != 78:
        raise PermissionError("H27 effect-free issuer requires exactly 78 unique identities.")
    for item in entries:
        if type(item) is not dict or not {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(item):
            raise PermissionError("H27 effect-free issuer identity malformed.")
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])


def _strict_timestamp(value: str) -> None:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
        raise ValueError("H27 issued_at_utc must use strict RFC3339 UTC seconds.")
    datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _canonical_artifact_bytes(issuer_id: str, invocation_nonce: str, issued_at_utc: str, destination_path: str) -> bytes:
    if issuer_id != _ISSUER_ID:
        raise ValueError("H27 issuer identity mismatch.")
    if re.fullmatch(r"[0-9a-f]{64}", invocation_nonce) is None:
        raise ValueError("H27 invocation nonce must be lowercase hex64.")
    _strict_timestamp(issued_at_utc)
    if destination_path != _DESTINATION:
        raise ValueError("H27 destination path mismatch.")
    digest = hashlib.sha256((issuer_id + "\n" + invocation_nonce + "\n" + destination_path + "\n" + _PREDECESSOR_MANIFEST_SHA256).encode("utf-8")).hexdigest()
    artifact = {
        "schema_version": 1,
        "artifact_id": "h27-authority-" + digest,
        "issuer_id": issuer_id,
        "invocation_nonce": invocation_nonce,
        "issued_at_utc": issued_at_utc,
        "destination_path": destination_path,
        "single_use": True,
        "predecessor_identity_count": _PREDECESSOR_COUNT,
        "predecessor_manifest_sha256": _PREDECESSOR_MANIFEST_SHA256,
    }
    if tuple(artifact) != _FIELD_ORDER:
        raise AssertionError("H27 artifact field order drift.")
    return (json.dumps(artifact, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


class H27EffectFreeIssuerAdapters(NamedTuple):
    attest_destination_unobserved: Callable[[str], bool]
    simulate_create_exclusive: Callable[[str, bytes], tuple[bool, bool]]
    finalize_in_memory: Callable[[bytes], bytes]


@dataclass(frozen=True)
class H27EffectFreeIssuerResult:
    verified_identities: int
    canonical_bytes: bytes
    canonical_sha256: str
    destination_path: None
    issuance_artifact_exists: bool
    authority_exists: bool
    claim_exists: bool
    capability_exists: bool
    filesystem_effects: int
    science_invocations: int


def issue_h27_real_publication_one_shot_authority(
    *,
    issuer_id: str,
    invocation_nonce: str,
    issued_at_utc: str,
    destination_path: str,
    adapters: H27EffectFreeIssuerAdapters,
) -> H27EffectFreeIssuerResult:
    """Validate and simulate the issuer entirely in memory; never issue."""
    _verify_seventy_eight_inputs()
    raw = _canonical_artifact_bytes(issuer_id, invocation_nonce, issued_at_utc, destination_path)
    if adapters.attest_destination_unobserved(destination_path) is not True:
        raise PermissionError("H27 effect-free issuer cannot observe a destination.")
    if adapters.simulate_create_exclusive(destination_path, raw) != (False, False):
        raise PermissionError("H27 effect-free issuer adapter must report no create or write.")
    if adapters.finalize_in_memory(raw) != raw:
        raise PermissionError("H27 effect-free issuer finalizer changed canonical bytes.")
    return H27EffectFreeIssuerResult(78, raw, hashlib.sha256(raw).hexdigest(), None, False, False, False, False, 0, 0)


__all__ = ["H27EffectFreeIssuerAdapters", "H27EffectFreeIssuerResult", "issue_h27_real_publication_one_shot_authority"]
