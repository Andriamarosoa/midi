"""Dormant, effect-free constructor for the H27 authority-instance artifact.

The public entrypoint verifies the exact administrative chain and builds only
canonical in-memory bytes.  It cannot reserve an identity, observe or write a
destination, publish an artifact, or grant/consume authority.
"""
from __future__ import annotations

from dataclasses import dataclass
import datetime
import hashlib
import json
from pathlib import Path
import re


_ROOT = Path(__file__).resolve().parents[2]
_ADMINISTRATIVE_INPUTS = (
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_instance_artifact_constructor_implementation_contract_identity_binding.json",
        "b8e87b32edecc2e9ee6ef4efbaa6ffda92b01566", 3472,
        "4696c93c6aca9f3925a2acf526d38397c8be9d70a965e9e219de7b786e9d6da7",
    ),
    (
        "configs/harmonic_censoring_h27_real_publication_one_shot_authority_instance_artifact_constructor_implementation_contract_identity_binding_external_seal.json",
        "781c01c7d29ec48815df78c177747a1021753b5e", 1499,
        "bb4a5593ac9c50098af4e015716862f90a3748f89bd0d9e3a0f9b24c38c9bac7",
    ),
)
_ISSUER_ID = "h27-execution-codex-mac-primary"
_DESTINATION = "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json"
_NAMESPACE = "H27_REAL_PUBLICATION_ONE_SHOT_AUTHORITY_INSTANCE_V1"
_TOP_LEVEL_FIELDS = (
    "schema_version", "artifact_type", "authority_instance_id", "issuer_id",
    "issued_at_utc", "invocation_nonce", "canonical_destination_path",
    "sealed_chain_identity", "single_use", "consumed",
)
_SEALED_FIELDS = (
    "contract_git_blob_sha1", "contract_size_bytes", "contract_raw_sha256",
    "binding_git_blob_sha1", "binding_size_bytes", "binding_raw_sha256",
)
_SEALED_VALUES = {
    "contract_git_blob_sha1": "40757fa14d3df8b2aca2e12924faf7be329b9687",
    "contract_size_bytes": 5300,
    "contract_raw_sha256": "c23b4ceaf67dba8dc9d16ab7b279906823ae1b1259ba07aa8e8e2a2bf23210bb",
    "binding_git_blob_sha1": "41bb902d99379c0a518181e97056b4232abbc143",
    "binding_size_bytes": 3369,
    "binding_raw_sha256": "400a1010c4be36cbec585de0399137abca8b0b61f218946498d19fad23739e55",
}


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _verify_exact(relative: str, blob: str, size: int, sha256: str) -> bytes:
    path = (_ROOT / relative).resolve(strict=True)
    path.relative_to(_ROOT.resolve(strict=True))
    raw = path.read_bytes()
    if len(raw) != size or _git_blob(raw) != blob or hashlib.sha256(raw).hexdigest() != sha256:
        raise PermissionError(f"H27 effect-free constructor administrative drift: {relative}.")
    return raw


def _verified_json(item: dict[str, object]) -> dict[str, object]:
    raw = _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])
    value = json.loads(raw)
    if type(value) is not dict:
        raise PermissionError("H27 effect-free constructor expected a bound JSON object.")
    return value


def _sixty_four(execution_roots: list[dict[str, object]]) -> list[dict[str, object]]:
    execution_contract = _verified_json(execution_roots[0])
    destination_roots = execution_contract["reviewed_and_sealed_destination_contract_chain"]
    destination_binding = _verified_json(destination_roots[2])
    destination_contract = _verified_json(destination_binding["reviewed_contract"])
    dormant_roots = destination_contract["reviewed_and_sealed_dormant_boundary"]
    old_binding = _verified_json(next(x for x in dormant_roots if x["path"] == destination_contract["transitive_identity_source"]["path"]))
    activation_roots = old_binding["upstream_roots"]
    execution_binding = _verified_json(activation_roots[0])
    inherited = [execution_binding["reviewed_contract"], execution_binding["contract_external_seal"], *execution_binding["reviewed_and_sealed_dormant_publication_simulator"]]
    older = _verified_json(next(x for x in inherited if x["path"] == execution_binding["transitive_upstream_binding"]["path"]))["upstream_entries"]
    return [*destination_roots, *dormant_roots, *activation_roots, *inherited, *older]


def _eighty(issuer_binding: dict[str, object]) -> list[dict[str, object]]:
    roots = issuer_binding["upstream_roots"]
    implementation_binding = _verified_json(roots[0])
    implementation_contract = _verified_json(implementation_binding["reviewed_contract"])
    issuance_roots = implementation_contract["reviewed_and_sealed_issuance_artifact_contract_chain"]
    issuance_contract = _verified_json(issuance_roots[0])
    authority_roots = issuance_contract["reviewed_and_sealed_one_shot_authority_chain"]
    authority_contract = _verified_json(authority_roots[0])
    execution_roots = authority_contract["reviewed_and_sealed_execution_authorization_chain"]
    return [*roots, implementation_binding["reviewed_contract"], implementation_binding["contract_external_seal"], *issuance_roots, *authority_roots, *execution_roots, *_sixty_four(execution_roots)]


def _ninety_six(contract: dict[str, object]) -> list[dict[str, object]]:
    artifact_roots = contract["reviewed_and_sealed_authority_instance_artifact_chain"]
    artifact_contract = _verified_json(artifact_roots[0])
    authority_roots = artifact_contract["reviewed_and_sealed_one_shot_authority_contract_chain"]
    authority_contract = _verified_json(authority_roots[0])
    authorization_roots = authority_contract["reviewed_and_sealed_real_issuance_authorization_chain"]
    authorization_binding = _verified_json(authorization_roots[2])
    authorization_contract = _verified_json(authorization_binding["reviewed_contract"])
    issuer_roots = authorization_contract["reviewed_and_sealed_effect_free_issuer_chain"]
    issuer_binding = _verified_json(issuer_roots[2])
    return [*artifact_roots, *authority_roots, *authorization_roots, *issuer_roots, *_eighty(issuer_binding)]


def _verify_ninety_eight_inputs() -> None:
    for item in _ADMINISTRATIVE_INPUTS:
        _verify_exact(*item)
    binding = json.loads(_verify_exact(*_ADMINISTRATIVE_INPUTS[0]))
    contract = _verified_json(binding["reviewed_contract"])
    entries = [binding["reviewed_contract"], binding["contract_external_seal"], *_ninety_six(contract)]
    if len(entries) != 98 or len({item["path"] for item in entries}) != 98:
        raise PermissionError("H27 effect-free constructor requires exactly 98 unique identities.")
    for item in entries:
        if type(item) is not dict or not {"path", "git_blob_sha1", "size_bytes", "raw_sha256"} <= set(item):
            raise PermissionError("H27 effect-free constructor identity malformed.")
        _verify_exact(item["path"], item["git_blob_sha1"], item["size_bytes"], item["raw_sha256"])


def _strict_timestamp(value: str) -> None:
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value) is None:
        raise ValueError("H27 issued_at_utc must use strict RFC3339 UTC seconds.")
    datetime.datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ")


def _canonical_artifact_bytes(issuer_id: str, issued_at_utc: str, invocation_nonce: str, canonical_destination_path: str, sealed_chain_identity: dict[str, object]) -> bytes:
    if not all(type(x) is str for x in (issuer_id, issued_at_utc, invocation_nonce, canonical_destination_path)) or type(sealed_chain_identity) is not dict:
        raise TypeError("H27 constructor inputs must use exact native types.")
    if tuple(sealed_chain_identity) != _SEALED_FIELDS:
        raise ValueError("H27 sealed_chain_identity key order mismatch.")
    for key, value in sealed_chain_identity.items():
        expected_type = int if key.endswith("size_bytes") else str
        if type(value) is not expected_type:
            raise TypeError("H27 sealed_chain_identity values must use exact native types.")
    if sealed_chain_identity != _SEALED_VALUES:
        raise ValueError("H27 sealed_chain_identity value mismatch.")
    if issuer_id != _ISSUER_ID or canonical_destination_path != _DESTINATION:
        raise ValueError("H27 constructor fixed identity or destination mismatch.")
    if re.fullmatch(r"[0-9a-f]{64}", invocation_nonce) is None:
        raise ValueError("H27 invocation nonce must be lowercase hex64.")
    _strict_timestamp(issued_at_utc)
    digest_input = "\0".join((_NAMESPACE, issuer_id, issued_at_utc, invocation_nonce, canonical_destination_path, sealed_chain_identity["contract_raw_sha256"], sealed_chain_identity["binding_raw_sha256"]))
    authority_instance_id = hashlib.sha256(digest_input.encode("ascii")).hexdigest()
    artifact = {
        "schema_version": 1,
        "artifact_type": "h27_real_publication_one_shot_execution_authority_instance",
        "authority_instance_id": authority_instance_id,
        "issuer_id": issuer_id,
        "issued_at_utc": issued_at_utc,
        "invocation_nonce": invocation_nonce,
        "canonical_destination_path": canonical_destination_path,
        "sealed_chain_identity": dict(sealed_chain_identity),
        "single_use": True,
        "consumed": False,
    }
    if tuple(artifact) != _TOP_LEVEL_FIELDS or tuple(artifact["sealed_chain_identity"]) != _SEALED_FIELDS:
        raise AssertionError("H27 authority-instance artifact order drift.")
    return (json.dumps(artifact, ensure_ascii=False, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


@dataclass(frozen=True)
class H27EffectFreeConstructorProbe:
    persistent_registry_checked: bool
    identity_available: bool
    nonce_available: bool
    reservation_attempted: bool
    destination_observed: bool
    create_attempted: bool
    write_attempted: bool
    expected_canonical_sha256: str


@dataclass(frozen=True)
class H27EffectFreeConstructorResult:
    verified_identities: int
    canonical_bytes: bytes
    canonical_sha256: str
    authority_instance_id: str
    persistent_reservation_performed: bool
    destination_path: None
    authority_instance_artifact_exists: bool
    authority_instance_exists: bool
    filesystem_effects: int
    science_invocations: int


def construct_h27_real_publication_authority_instance_artifact(*, issuer_id: str, issued_at_utc: str, invocation_nonce: str, canonical_destination_path: str, sealed_chain_identity: dict[str, object], probe: H27EffectFreeConstructorProbe) -> H27EffectFreeConstructorResult:
    """Validate and simulate canonical construction entirely in memory."""
    _verify_ninety_eight_inputs()
    if not all(type(x) is str for x in (issuer_id, issued_at_utc, invocation_nonce, canonical_destination_path)) or type(sealed_chain_identity) is not dict:
        raise TypeError("H27 constructor inputs must use exact native types.")
    if type(probe) is not H27EffectFreeConstructorProbe:
        raise PermissionError("H27 constructor requires the closed immutable probe type.")
    for name in ("persistent_registry_checked", "identity_available", "nonce_available", "reservation_attempted", "destination_observed", "create_attempted", "write_attempted"):
        if type(getattr(probe, name)) is not bool:
            raise TypeError("H27 constructor probe booleans must use exact native types.")
    if type(probe.expected_canonical_sha256) is not str:
        raise TypeError("H27 constructor probe digest must be an exact native string.")
    raw = _canonical_artifact_bytes(issuer_id, issued_at_utc, invocation_nonce, canonical_destination_path, sealed_chain_identity)
    sha256 = hashlib.sha256(raw).hexdigest()
    if not (probe.persistent_registry_checked and probe.identity_available and probe.nonce_available):
        raise PermissionError("H27 constructor requires prior persistent-registry availability attestations.")
    if probe.reservation_attempted or probe.destination_observed or probe.create_attempted or probe.write_attempted:
        raise PermissionError("H27 effect-free constructor probe must attest zero effects.")
    if probe.expected_canonical_sha256 != sha256:
        raise PermissionError("H27 effect-free constructor canonical identity mismatch.")
    authority_instance_id = json.loads(raw)["authority_instance_id"]
    return H27EffectFreeConstructorResult(98, raw, sha256, authority_instance_id, False, None, False, False, 0, 0)


__all__ = ["H27EffectFreeConstructorProbe", "H27EffectFreeConstructorResult", "construct_h27_real_publication_authority_instance_artifact"]
