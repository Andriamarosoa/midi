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
import threading


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


def _verified_json(item: dict[str, object]) -> dict[str, object]:
    raw = _verify_exact(str(item["path"]), str(item["git_blob_sha1"]), int(item["size_bytes"]), str(item["raw_sha256"]))
    value = json.loads(raw)
    if type(value) is not dict:
        raise PermissionError("H27 effect-free issuer expected a bound JSON object.")
    return value


def _sixty_four(execution_chain: list[dict[str, object]]) -> list[dict[str, object]]:
    execution_contract = _verified_json(execution_chain[0])
    roots = execution_contract["reviewed_and_sealed_destination_contract_chain"]
    for item in roots:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    destination_binding = _verified_json(roots[2])
    destination_contract = _verified_json(destination_binding["reviewed_contract"])
    dormant = destination_contract["reviewed_and_sealed_dormant_boundary"]
    for item in dormant:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    older_identity_path = destination_contract["transitive_identity_source"]["path"]
    older_identity = next(item for item in dormant if item["path"] == older_identity_path)
    older = _verified_json(older_identity)
    authorization_roots = older["upstream_roots"]
    for item in authorization_roots:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    authorization = _verified_json(authorization_roots[0])
    publication = [
        authorization["reviewed_contract"], authorization["contract_external_seal"],
        *authorization["reviewed_and_sealed_dormant_publication_simulator"],
    ]
    for item in publication:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    upstream_path = authorization["transitive_upstream_binding"]["path"]
    upstream_identity = next(item for item in publication if item["path"] == upstream_path)
    upstream_binding = _verified_json(upstream_identity)
    upstream = upstream_binding["upstream_entries"]
    for item in upstream:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    return [*roots, *dormant, *authorization_roots, *publication, *upstream]


def _verify_seventy_eight_inputs() -> None:
    for item in _ADMINISTRATIVE_INPUTS:
        _verify_exact(*item)
    binding = json.loads(_verify_exact(*_ADMINISTRATIVE_INPUTS[0]))
    contract = _verified_json(binding["reviewed_contract"])
    roots = contract["reviewed_and_sealed_issuance_artifact_contract_chain"]
    for item in roots:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    artifact_contract = _verified_json(roots[0])
    authority_roots = artifact_contract["reviewed_and_sealed_one_shot_authority_chain"]
    for item in authority_roots:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    authority = _verified_json(authority_roots[0])
    execution_roots = authority["reviewed_and_sealed_execution_authorization_chain"]
    for item in execution_roots:
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
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


@dataclass(frozen=True)
class H27EffectFreeIssuerProbe:
    destination_observed: bool
    create_attempted: bool
    write_attempted: bool
    expected_canonical_sha256: str


_USED_NONCES: set[str] = set()
_NONCE_LOCK = threading.Lock()


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
    probe: H27EffectFreeIssuerProbe,
) -> H27EffectFreeIssuerResult:
    """Validate and simulate the issuer entirely in memory; never issue."""
    _verify_seventy_eight_inputs()
    raw = _canonical_artifact_bytes(issuer_id, invocation_nonce, issued_at_utc, destination_path)
    expected_sha256 = hashlib.sha256(raw).hexdigest()
    if type(probe) is not H27EffectFreeIssuerProbe:
        raise PermissionError("H27 effect-free issuer requires the closed immutable probe type.")
    if probe.destination_observed is not False or probe.create_attempted is not False or probe.write_attempted is not False:
        raise PermissionError("H27 effect-free issuer probe must attest zero effects.")
    if probe.expected_canonical_sha256 != expected_sha256:
        raise PermissionError("H27 effect-free issuer probe canonical identity mismatch.")
    with _NONCE_LOCK:
        if invocation_nonce in _USED_NONCES:
            raise PermissionError("H27 invocation nonce was already consumed in this process.")
        _USED_NONCES.add(invocation_nonce)
    return H27EffectFreeIssuerResult(78, raw, expected_sha256, None, False, False, False, False, 0, 0)


__all__ = ["H27EffectFreeIssuerProbe", "H27EffectFreeIssuerResult", "issue_h27_real_publication_one_shot_authority"]
