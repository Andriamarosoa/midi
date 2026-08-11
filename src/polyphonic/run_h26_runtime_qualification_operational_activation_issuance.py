"""STOP-1 entrypoint for one future H26 activation publication.

The command has no CLI arguments. It consumes caller-supplied canonical
activation bytes from stdin and can publish them only on the pre-registered
Mac root after explicit OS acknowledgement and exact clean-HEAD verification.
This module is implemented but must not be invoked before separate review.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
from typing import Any, Iterable, Tuple

from .harmonic_censoring_h26_runtime_execution_primitives import canonical_json_bytes
from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner import (
    plan_runtime_qualification_operational_activation_issuance,
)
from .harmonic_censoring_h26_runtime_qualification_operational_activation_issuer import (
    H26PosixIssuanceFilesystemAdapter,
    publish_prevalidated_activation_with_adapter,
)

ADMINISTRATIVE_ROOT = "/Users/amcarene/h26-admin"
ISSUER_IDENTITY = "h26-execution-codex-mac-primary"
ISSUED_AT = "2026-08-12T12:00:00Z"
ACKNOWLEDGEMENT_VARIABLE = "H26_RUNTIME_ACTIVATION_ISSUANCE_EXECUTE"
AUTHORIZATION_COMMIT_VARIABLE = "H26_RUNTIME_ACTIVATION_AUTHORIZATION_COMMIT"
MAXIMUM_REQUEST_BYTES = 65536
ENTRYPOINT_CONTRACT_PATH = (
    "configs/harmonic_censoring_h26_runtime_activation_operational_entrypoint_contract.json"
)
_COMMIT = re.compile(r"^[0-9a-f]{40}$")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _strict_json_object(raw: bytes) -> dict[str, Any]:
    if not raw or len(raw) > MAXIMUM_REQUEST_BYTES:
        raise ValueError("activation request byte length mismatch")
    if b"\r" in raw or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError("activation request must be canonical UTF-8 LF bytes")

    def pairs_hook(pairs: Iterable[Tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate activation request key: {key}")
            result[key] = value
        return result

    def reject_float(value: str) -> Any:
        raise ValueError(f"non-integer activation JSON value forbidden: {value}")

    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=pairs_hook,
            parse_float=reject_float,
            parse_constant=reject_float,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid activation request JSON") from exc
    if type(value) is not dict:
        raise ValueError("activation request must be a JSON object")
    return value


def _git_output(*arguments: str) -> str:
    return subprocess.check_output(
        ("git", *arguments), cwd=_repo_root(), text=True, encoding="utf-8"
    ).strip()


def _load_entrypoint_contract() -> dict[str, Any]:
    raw = (_repo_root() / ENTRYPOINT_CONTRACT_PATH).resolve(strict=True).read_bytes()
    value = _strict_json_object(raw)
    expected = {
        "schema_identity": "H26_RUNTIME_ACTIVATION_OPERATIONAL_ENTRYPOINT_CONTRACT_V1",
        "schema_version": 1,
        "status": "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_ACTIVATION_CREATED",
        "approved_parent_commit": "fcb6992cfee5ef0cb9c1e09c8e52f9600e3419a4",
        "administrative_root": ADMINISTRATIVE_ROOT,
        "issuer_identity": ISSUER_IDENTITY,
        "issued_at": ISSUED_AT,
        "acknowledgement_variable": ACKNOWLEDGEMENT_VARIABLE,
        "authorization_commit_variable": AUTHORIZATION_COMMIT_VARIABLE,
        "request_transport": "exact canonical activation bytes on stdin",
        "required_platform": "Darwin",
        "requires_clean_head_equal_authorization_commit": True,
        "publication": "create-exclusive staging fsync renameatx_np(RENAME_EXCL) directory-fsync",
        "retry_allowed": False,
        "activation_created": False,
        "runtime_observed": False,
        "materialization_executed": False,
        "p0_executed": False,
        "p1_executed": False,
        "p2_executed": False,
        "locked_test_used": False,
        "next_action": "External review of this operational entrypoint before any administrative root or activation creation",
    }
    if value != expected:
        raise ValueError("H26 operational entrypoint contract mismatch")
    return value


def _require_execution_boundary() -> str:
    _load_entrypoint_contract()
    if os.name != "posix" or not hasattr(os, "uname") or os.uname().sysname != "Darwin":
        raise RuntimeError("H26 activation issuance requires the reviewed macOS boundary")
    if os.environ.get(ACKNOWLEDGEMENT_VARIABLE) != "1":
        raise PermissionError("H26 activation issuance acknowledgement missing")
    authorization_commit = os.environ.get(AUTHORIZATION_COMMIT_VARIABLE)
    if type(authorization_commit) is not str or _COMMIT.fullmatch(authorization_commit) is None:
        raise PermissionError("H26 activation authorization commit missing")
    head = _git_output("rev-parse", "HEAD")
    if authorization_commit != head:
        raise PermissionError("H26 activation authorization commit must equal HEAD")
    if _git_output("status", "--porcelain=v1"):
        raise PermissionError("H26 activation issuance requires a clean worktree")
    return head


def issue_h26_runtime_activation_once(raw_request: bytes):
    """Publish the exact caller-supplied activation after reversible checks."""
    _require_execution_boundary()
    activation = _strict_json_object(raw_request)
    if activation.get("administrative_root") != ADMINISTRATIVE_ROOT:
        raise ValueError("pre-registered administrative_root mismatch")
    if activation.get("issuer_identity") != ISSUER_IDENTITY:
        raise ValueError("pre-registered issuer_identity mismatch")
    if activation.get("issued_at") != ISSUED_AT:
        raise ValueError("pre-registered issued_at mismatch")
    plan = plan_runtime_qualification_operational_activation_issuance(activation)
    if raw_request != plan.canonical_bytes or raw_request != canonical_json_bytes(activation):
        raise ValueError("activation request bytes are not canonical validator bytes")
    adapter = H26PosixIssuanceFilesystemAdapter(ADMINISTRATIVE_ROOT)
    return publish_prevalidated_activation_with_adapter(plan, adapter)


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("H26 activation issuance accepts no arguments")
    raw = sys.stdin.buffer.read(MAXIMUM_REQUEST_BYTES + 1)
    receipt = issue_h26_runtime_activation_once(raw)
    print(
        json.dumps(
            {
                "activation_id": receipt.activation_id,
                "activation_raw_sha256": receipt.activation_raw_sha256,
                "final_path": receipt.final_path,
                "published": receipt.published,
            },
            sort_keys=True,
            separators=(",", ":"),
        ),
        flush=True,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
