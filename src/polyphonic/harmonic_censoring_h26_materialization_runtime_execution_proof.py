"""Pure dormant validation of an artificial H26 runtime execution proof.

The module creates no authority, claim, evidence, receipt, runtime record,
destination, or filesystem artifact.  It only validates artificial in-memory
objects and projects the exact fields that a separately authorized future
materialization authority would have to bind.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Iterable, Mapping, Optional, Tuple

from src.polyphonic import harmonic_censoring_h26_runtime_execution_primitives as _runtime
from src.polyphonic import harmonic_censoring_h26_runtime_qualification as _qualifier


MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT = (
    "84d1a196635c6ace7f3ea5ec9b7e338f5da70300"
)
MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA = (
    "94f255c583a52d660dc57f70df80b97173791296"
)
TERMINAL_RECEIPT_VALIDATOR_COMMIT = (
    "09ef74cd537392d76eab1ed09082bf04e0214f16"
)
TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA = (
    "9721a41eca9e3f2bfa1ef8150ff39bf34ccf5fce"
)
RUNTIME_QUALIFIER_COMMIT = "25a08630d6ad99d5e3432a277b99b9603990458a"
RUNTIME_QUALIFIER_GIT_BLOB_SHA = "ef24d9ebdc4ae834b3b872175fb7e098330a68bf"
VALIDATION_STACK_CLOSURE_COMMIT = (
    "b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0"
)
VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA = (
    "f26262b28e9d00e5d5c270461dd72c04e16bbaf9"
)

_APPROVED_MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT = (
    "84d1a196635c6ace7f3ea5ec9b7e338f5da70300"
)
_APPROVED_MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA = (
    "94f255c583a52d660dc57f70df80b97173791296"
)
_APPROVED_TERMINAL_RECEIPT_VALIDATOR_COMMIT = (
    "09ef74cd537392d76eab1ed09082bf04e0214f16"
)
_APPROVED_TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA = (
    "9721a41eca9e3f2bfa1ef8150ff39bf34ccf5fce"
)
_APPROVED_RUNTIME_QUALIFIER_COMMIT = (
    "25a08630d6ad99d5e3432a277b99b9603990458a"
)
_APPROVED_RUNTIME_QUALIFIER_GIT_BLOB_SHA = (
    "ef24d9ebdc4ae834b3b872175fb7e098330a68bf"
)
_APPROVED_VALIDATION_STACK_CLOSURE_COMMIT = (
    "b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0"
)
_APPROVED_VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA = (
    "f26262b28e9d00e5d5c270461dd72c04e16bbaf9"
)
_QUALIFIED = "H26_MATERIALIZATION_RUNTIME_QUALIFIED"

_PROJECTION_FIELDS: Tuple[str, ...] = (
    "runtime_execution_authority_id",
    "runtime_execution_authority_raw_sha256",
    "runtime_execution_claim_id",
    "runtime_execution_claim_raw_sha256",
    "runtime_execution_observer_entry_evidence_id",
    "runtime_execution_observer_entry_evidence_raw_sha256",
    "runtime_execution_receipt_raw_sha256",
    "runtime_execution_terminal_status",
    "qualified_runtime_record_sha256",
)


@dataclass(frozen=True)
class H26MaterializationRuntimeExecutionProof:
    """Immutable pure projection of one fully validated artificial proof."""

    runtime_execution_authority_id: str
    runtime_execution_authority_raw_sha256: str
    runtime_execution_claim_id: str
    runtime_execution_claim_raw_sha256: str
    runtime_execution_observer_entry_evidence_id: str
    runtime_execution_observer_entry_evidence_raw_sha256: str
    runtime_execution_receipt_raw_sha256: str
    runtime_execution_terminal_status: str
    qualified_runtime_record_sha256: str


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _canonical_git_text_bytes(raw: bytes) -> bytes:
    if b"\r" in raw:
        if b"\r" in raw.replace(b"\r\n", b""):
            raise ValueError("reviewed text artifact contains a non-CRLF carriage return")
        raw = raw.replace(b"\r\n", b"\n")
    return raw


def _git_blob_sha(raw: bytes) -> str:
    canonical = _canonical_git_text_bytes(raw)
    header = f"blob {len(canonical)}\0".encode("ascii")
    return hashlib.sha1(header + canonical).hexdigest()


def _strict_json(raw: bytes) -> dict[str, Any]:
    canonical = _canonical_git_text_bytes(raw)
    try:
        text = canonical.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("materialization authority contract is not UTF-8") from exc
    if text.startswith("\ufeff"):
        raise ValueError("materialization authority contract has a forbidden BOM")

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"floating-point JSON value forbidden: {value}")

    try:
        payload = json.loads(
            text,
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except json.JSONDecodeError as exc:
        raise ValueError("invalid materialization authority contract JSON") from exc
    if not isinstance(payload, dict):
        raise ValueError("materialization authority contract must be an object")
    return payload


def _require_public_bindings() -> None:
    bindings = {
        "materialization authority contract commit": (
            MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT,
            _APPROVED_MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT,
        ),
        "materialization authority contract blob": (
            MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA,
            _APPROVED_MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        ),
        "terminal receipt validator commit": (
            TERMINAL_RECEIPT_VALIDATOR_COMMIT,
            _APPROVED_TERMINAL_RECEIPT_VALIDATOR_COMMIT,
        ),
        "terminal receipt validator blob": (
            TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA,
            _APPROVED_TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA,
        ),
        "runtime qualifier commit": (
            RUNTIME_QUALIFIER_COMMIT,
            _APPROVED_RUNTIME_QUALIFIER_COMMIT,
        ),
        "runtime qualifier blob": (
            RUNTIME_QUALIFIER_GIT_BLOB_SHA,
            _APPROVED_RUNTIME_QUALIFIER_GIT_BLOB_SHA,
        ),
        "validation closure commit": (
            VALIDATION_STACK_CLOSURE_COMMIT,
            _APPROVED_VALIDATION_STACK_CLOSURE_COMMIT,
        ),
        "validation closure report blob": (
            VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA,
            _APPROVED_VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA,
        ),
    }
    for label, (actual, expected) in bindings.items():
        if actual != expected:
            raise ValueError(f"{label} binding mismatch")


def _require_reviewed_file_blob(path: Path, expected: str, label: str) -> None:
    raw = path.resolve(strict=True).read_bytes()
    if _git_blob_sha(raw) != expected:
        raise ValueError(f"{label} Git blob mismatch")


def load_materialization_runtime_execution_proof_contract(
    path: Optional[Path] = None,
) -> Mapping[str, Any]:
    """Load and validate only the exact corrected declarative contract."""
    _require_public_bindings()
    root = _repo_root()
    contract_path = path or (
        root
        / "configs"
        / "harmonic_censoring_h26_population_materialization_authority_contract.json"
    )
    raw = contract_path.resolve(strict=True).read_bytes()
    if _git_blob_sha(raw) != MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA:
        raise ValueError("materialization authority contract Git blob mismatch")
    payload = _strict_json(raw)
    expected_top = {
        "schema_version": 1,
        "purpose": "H26_POPULATION_MATERIALIZATION_AUTHORITY_CONTRACT",
        "status": "DECLARATIVE_DORMANT_NO_ISSUER_NO_CAPABILITY_NO_EXECUTION",
    }
    for key, expected in expected_top.items():
        if type(payload.get(key)) is not type(expected) or payload.get(key) != expected:
            raise ValueError(f"materialization authority contract {key} mismatch")

    expected_stack = {
        "review_closure_commit": VALIDATION_STACK_CLOSURE_COMMIT,
        "execution_authority_contract_commit": _runtime.EXECUTION_AUTHORITY_CONTRACT_COMMIT,
        "execution_authority_contract_git_blob_sha": _runtime.EXECUTION_AUTHORITY_CONTRACT_GIT_BLOB_SHA,
        "execution_authority_contract_raw_sha256": _runtime.EXECUTION_AUTHORITY_CONTRACT_RAW_SHA256,
        "runtime_qualification_contract_commit": _runtime.RUNTIME_QUALIFICATION_CONTRACT_COMMIT,
        "runtime_qualification_contract_git_blob_sha": _runtime.RUNTIME_QUALIFICATION_CONTRACT_GIT_BLOB_SHA,
        "runtime_qualification_contract_raw_sha256": _runtime.RUNTIME_QUALIFICATION_CONTRACT_RAW_SHA256,
        "runtime_qualifier_commit": RUNTIME_QUALIFIER_COMMIT,
        "runtime_qualifier_git_blob_sha": RUNTIME_QUALIFIER_GIT_BLOB_SHA,
        "authority_claim_observer_evidence_validators_commit": "10d3ee0525790279bce299492d89cec4002ab931",
        "authority_claim_observer_evidence_validators_git_blob_sha": "1c1777ad7c4493e66674d1daf63508778874df04",
        "terminal_receipt_validator_commit": TERMINAL_RECEIPT_VALIDATOR_COMMIT,
        "terminal_receipt_validator_git_blob_sha": TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA,
        "review_closure_report_git_blob_sha": VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA,
        "stack_status": "H26_RUNTIME_EXECUTION_DORMANT_VALIDATION_STACK_REVIEWED_AND_CLOSED",
    }
    if payload.get("runtime_execution_validation_stack") != expected_stack:
        raise ValueError("runtime execution validation stack binding mismatch")

    requirements = payload.get("future_authority_requirements")
    if not isinstance(requirements, dict):
        raise ValueError("future authority requirements missing")
    fields = requirements.get("required_fields")
    if not isinstance(fields, list) or not set(_PROJECTION_FIELDS).issubset(fields):
        raise ValueError("future authority runtime proof fields mismatch")
    proof = payload.get("runtime_execution_proof_requirements")
    if not isinstance(proof, dict):
        raise ValueError("runtime execution proof requirements missing")
    expected_receipt = {
        "terminal_status": _QUALIFIED,
        "runtime_record_exists": True,
        "observer_entered": True,
        "observer_invocation_count": 1,
        "claim_consumed": True,
        "retry_allowed": False,
        "runtime_record_raw_sha256_must_equal_qualified_runtime_record_sha256": True,
        "authority_id_and_raw_sha256_must_match_bound_authority": True,
        "claim_id_and_raw_sha256_must_match_bound_consumed_claim": True,
        "observer_entry_evidence_id_and_raw_sha256_must_match_bound_evidence": True,
    }
    if proof.get("required_receipt_constraints") != expected_receipt:
        raise ValueError("runtime execution receipt constraints mismatch")
    if proof.get("qualified_runtime_record_sha256_alone_is_insufficient") is not True:
        raise ValueError("record-only proof prohibition missing")
    boundary = payload.get("authorization_boundary")
    if not isinstance(boundary, dict) or len(boundary) != 11:
        raise ValueError("authorization boundary mismatch")
    if any(value is not False for value in boundary.values()):
        raise ValueError("authorization boundary is not dormant")

    _require_reviewed_file_blob(
        Path(_runtime.__file__),
        TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA,
        "terminal receipt validator",
    )
    _require_reviewed_file_blob(
        Path(_qualifier.__file__),
        RUNTIME_QUALIFIER_GIT_BLOB_SHA,
        "runtime qualifier",
    )
    _require_reviewed_file_blob(
        root
        / "readme"
        / "results"
        / "2026-08-11_harmonic-censoring-h26-runtime-execution-validation-stack-review-closure.md",
        VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA,
        "validation closure report",
    )
    return MappingProxyType(payload)


def validate_artificial_materialization_runtime_execution_proof(
    authority: Mapping[str, Any],
    claim: Mapping[str, Any],
    evidence: Mapping[str, Any],
    receipt: Mapping[str, Any],
    authority_raw_sha256: str,
    claim_raw_sha256: str,
    observer_entry_evidence_raw_sha256: str,
    receipt_raw_sha256: str,
    runtime_record: Optional[_qualifier.H26RuntimeQualificationRecord],
) -> H26MaterializationRuntimeExecutionProof:
    """Validate one complete artificial proof and return its immutable projection."""
    load_materialization_runtime_execution_proof_contract()
    _runtime.validate_artificial_terminal_execution_receipt(
        authority,
        claim,
        evidence,
        receipt,
        authority_raw_sha256,
        claim_raw_sha256,
        observer_entry_evidence_raw_sha256,
        runtime_record,
    )
    actual_receipt_sha = _runtime.canonical_artifact_raw_sha256(receipt)
    if receipt_raw_sha256 != actual_receipt_sha:
        raise ValueError("receipt_raw_sha256 does not match canonical receipt bytes")
    if runtime_record is None or receipt.get("runtime_record_exists") is not True:
        raise ValueError("materialization runtime proof requires a runtime record")
    if receipt.get("terminal_status") != _QUALIFIED:
        raise ValueError("materialization runtime proof must be QUALIFIED")
    record_bytes = _qualifier.serialize_runtime_qualification_record(runtime_record)
    record_sha = _runtime.external_raw_sha256(record_bytes)
    if receipt.get("runtime_record_raw_sha256") != record_sha:
        raise ValueError("qualified runtime record SHA mismatch")

    return H26MaterializationRuntimeExecutionProof(
        runtime_execution_authority_id=str(authority["authority_id"]),
        runtime_execution_authority_raw_sha256=authority_raw_sha256,
        runtime_execution_claim_id=str(claim["claim_id"]),
        runtime_execution_claim_raw_sha256=claim_raw_sha256,
        runtime_execution_observer_entry_evidence_id=str(
            evidence["observer_entry_evidence_id"]
        ),
        runtime_execution_observer_entry_evidence_raw_sha256=(
            observer_entry_evidence_raw_sha256
        ),
        runtime_execution_receipt_raw_sha256=actual_receipt_sha,
        runtime_execution_terminal_status=_QUALIFIED,
        qualified_runtime_record_sha256=record_sha,
    )


__all__ = [
    "H26MaterializationRuntimeExecutionProof",
    "MATERIALIZATION_AUTHORITY_CONTRACT_COMMIT",
    "MATERIALIZATION_AUTHORITY_CONTRACT_GIT_BLOB_SHA",
    "RUNTIME_QUALIFIER_COMMIT",
    "RUNTIME_QUALIFIER_GIT_BLOB_SHA",
    "TERMINAL_RECEIPT_VALIDATOR_COMMIT",
    "TERMINAL_RECEIPT_VALIDATOR_GIT_BLOB_SHA",
    "VALIDATION_STACK_CLOSURE_COMMIT",
    "VALIDATION_STACK_CLOSURE_REPORT_GIT_BLOB_SHA",
    "load_materialization_runtime_execution_proof_contract",
    "validate_artificial_materialization_runtime_execution_proof",
]
