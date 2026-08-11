"""Dormant loader for the corrected H26 runtime orchestration seal."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any, Mapping

CORRECTION_SEAL_GIT_BLOB_SHA = "b069f5913996c021f552eaf1d6a23ae426f4c38c"
CORRECTION_CONTRACT_GIT_BLOB_SHA = "23308c11823708b7617b8a3797d8fd9534bcb045"
CORRECTION_CONTRACT_LENGTH = 2465
CORRECTION_CONTRACT_RAW_SHA256 = (
    "3e11d664bd1a28dd5f5e3f5c815f4a173cf30c4c55a9cceb32a873814a3e72b8"
)
HISTORICAL_CONTRACT_GIT_BLOB_SHA = "a986570cea5b4dc31df40499f66f1cb6fbb8ab3c"
HISTORICAL_CONTRACT_LENGTH = 2093
HISTORICAL_CONTRACT_RAW_SHA256 = (
    "e1bd0060d6567c57ffac6e2b3b41d34eeb6790fb6dd85065f4f191bf4459afb2"
)
HISTORICAL_SEAL_GIT_BLOB_SHA = "d298ab842ff385a2717fc38fa509cd2d2e8326ee"
HISTORICAL_ORIGINAL_LOADER_GIT_BLOB_SHA = (
    "a26c07a9f303b14812581960c0bb2a63cdb97b4f"
)
HISTORICAL_DEEP_FREEZE_LOADER_GIT_BLOB_SHA = (
    "f38fe07d45ba5f0c7d802ac9c4ca19be3ce8c5bb"
)


def _canonical(raw: bytes) -> bytes:
    if b"\r" in raw.replace(b"\r\n", b""):
        raise ValueError("non-CRLF carriage return")
    return raw.replace(b"\r\n", b"\n")


def _blob(raw: bytes) -> str:
    canonical = _canonical(raw)
    return hashlib.sha1(
        f"blob {len(canonical)}\0".encode() + canonical
    ).hexdigest()


def _reject_duplicate_pairs(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _parse(raw: bytes) -> dict[str, Any]:
    value = json.loads(
        _canonical(raw).decode("utf-8"),
        object_pairs_hook=_reject_duplicate_pairs,
        parse_float=lambda value: (_ for _ in ()).throw(
            ValueError(f"float forbidden: {value}")
        ),
    )
    if type(value) is not dict:
        raise ValueError("top-level JSON object required")
    return value


def _deep_freeze_json(value: Any) -> Any:
    if isinstance(value, dict):
        return MappingProxyType(
            {key: _deep_freeze_json(item) for key, item in value.items()}
        )
    if isinstance(value, list):
        return tuple(_deep_freeze_json(item) for item in value)
    return value


def _require_binding(
    raw: bytes, *, git_blob_sha: str, byte_length: int, raw_sha256: str
) -> bytes:
    canonical = _canonical(raw)
    if (
        _blob(raw) != git_blob_sha
        or len(canonical) != byte_length
        or hashlib.sha256(canonical).hexdigest() != raw_sha256
    ):
        raise ValueError("orchestration contract binding mismatch")
    return canonical


def load_runtime_one_shot_orchestration_contract_external_seal() -> Mapping[str, Any]:
    root = Path(__file__).resolve().parents[2]
    seal_raw = (
        root
        / "configs"
        / "harmonic_censoring_h26_runtime_one_shot_orchestration_observer_entry_order_correction_external_seal.json"
    ).read_bytes()
    if _blob(seal_raw) != CORRECTION_SEAL_GIT_BLOB_SHA:
        raise ValueError("orchestration correction seal blob mismatch")
    seal = _parse(seal_raw)
    expected = {
        "seal_schema_identity": "H26_RUNTIME_ONE_SHOT_ORCHESTRATION_OBSERVER_ENTRY_ORDER_CORRECTION_EXTERNAL_SEAL_V1",
        "seal_schema_version": 1,
        "status": "DECLARATIVE_DORMANT_EXTERNAL_SEAL_NO_RUNTIME_INVOCATION",
        "correction_contract_commit": "01c3220f22974ebe8aa0cd3d49116a1d919dc26c",
        "correction_contract_git_blob_sha": CORRECTION_CONTRACT_GIT_BLOB_SHA,
        "correction_contract_git_blob_byte_length": CORRECTION_CONTRACT_LENGTH,
        "correction_contract_raw_sha256": CORRECTION_CONTRACT_RAW_SHA256,
        "historical_contract_binding": {
            "commit": "697c77c8584816740039a9a5737617c647f0d32d",
            "git_blob_sha": HISTORICAL_CONTRACT_GIT_BLOB_SHA,
            "git_blob_byte_length": HISTORICAL_CONTRACT_LENGTH,
            "raw_sha256": HISTORICAL_CONTRACT_RAW_SHA256,
        },
        "historical_external_seal_binding": {
            "commit": "1652fac8e2171955180458a325cfca75e033acc1",
            "git_blob_sha": HISTORICAL_SEAL_GIT_BLOB_SHA,
        },
        "seal_contains_own_raw_sha256": False,
        "correction_contract_contains_own_raw_sha256": False,
        "historical_contract_and_seal_remain_provenance_artifacts": True,
        "historical_external_seal_is_superseded_for_future_orchestration": True,
        "current_state": {
            "correction_contract_exists": True,
            "correction_external_seal_exists": True,
            "observer_boundary_entered": False,
            "observer_entry_evidence_exists": False,
            "observer_invoked": False,
            "runtime_record_exists": False,
            "terminal_receipt_exists": False,
            "runtime_execution_authorized": False,
            "materialization_authorized": False,
            "scientific_execution_authorized": False,
            "locked_test_used": False,
        },
        "creation_authorized_now": False,
        "next_action": "Update the dormant loader to enforce this external seal and the corrected contract",
    }
    if seal != expected:
        raise ValueError("orchestration correction seal content mismatch")

    correction_raw = (
        root
        / "configs"
        / "harmonic_censoring_h26_runtime_one_shot_orchestration_observer_entry_order_correction.json"
    ).read_bytes()
    correction = _parse(
        _require_binding(
            correction_raw,
            git_blob_sha=CORRECTION_CONTRACT_GIT_BLOB_SHA,
            byte_length=CORRECTION_CONTRACT_LENGTH,
            raw_sha256=CORRECTION_CONTRACT_RAW_SHA256,
        )
    )
    if (
        correction.get("effective_future_sequence", [])[4:8]
        != [
            "enter_observer_boundary",
            "create_observer_entry_evidence_inside_boundary",
            "validate_observer_entry_evidence",
            "invoke_observer_exactly_once",
        ]
        or correction.get("creation_authorized_now") is not False
    ):
        raise ValueError("orchestration correction contract not dormant or ordered")

    historical_raw = (
        root
        / "configs"
        / "harmonic_censoring_h26_runtime_one_shot_orchestration_dormant_contract.json"
    ).read_bytes()
    _require_binding(
        historical_raw,
        git_blob_sha=HISTORICAL_CONTRACT_GIT_BLOB_SHA,
        byte_length=HISTORICAL_CONTRACT_LENGTH,
        raw_sha256=HISTORICAL_CONTRACT_RAW_SHA256,
    )
    return _deep_freeze_json(seal)


__all__ = ["load_runtime_one_shot_orchestration_contract_external_seal"]
