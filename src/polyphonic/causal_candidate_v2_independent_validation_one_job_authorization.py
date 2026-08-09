"""External-review-gated authorization for one independent V2 execution.

This module is TensorFlow-free and has no CLI.  The versioned request remains
inert until a later, non-versioned external approval names the exact execution
commit.  A persistent O_EXCL marker is written before capability registration
and is intentionally never removed.
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
from typing import Mapping
import weakref


REVIEWED_RUNNER_COMMIT = "6246ea18c49a6c3c3b8e2ce1303c9a6afffac6ee"
EXECUTION_CONTRACT_SHA256 = "269efb65f225cf2522eab895cf59c351bea6bb97bc20229160f611c5e3ae63ed"
ASSET_EVIDENCE_SHA256 = "10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee"
AUTHORIZATION_REQUEST_SHA256 = "3145330a5bcd57cffb218914d3c545779ca54ce6634f716d49fae742dd922808"
AUTHORIZATION_REQUEST_RELATIVE_PATH = Path(
    "configs/causal_candidate_v2_independent_validation_one_job_authorization_request.json"
)
EXTERNAL_APPROVAL_RELATIVE_PATH = Path(
    "tmp/local/causal_candidate_v2_independent_validation_external_review_approval_20260810.json"
)
PERSISTENT_CLAIM_RELATIVE_PATH = Path(
    "tmp/local/causal_candidate_v2_independent_validation_one_job_20260810.claimed.json"
)
RUNNER_RELATIVE_PATH = Path(
    "src/polyphonic/run_causal_candidate_v2_independent_validation_execution.py"
)
JOB_ID = "causal-candidate-v2-independent-cpu-20260810"
DESTINATION = "tmp/local/causal_candidate_v2_independent_validation_execution_20260810"

AUTHORIZATION_STEP_PATHS = frozenset(
    {
        ".gitattributes",
        AUTHORIZATION_REQUEST_RELATIVE_PATH.as_posix(),
        "src/polyphonic/causal_candidate_v2_independent_validation_one_job_authorization.py",
        "tests/test_causal_candidate_v2_independent_validation_one_job_authorization.py",
        "readme/README.md",
        "readme/results/2026-08-10_causal-candidate-v2-independent-validation-one-job-authorization-request.md",
    }
)

_REQUEST_KEYS = frozenset(
    {
        "schema_version", "purpose", "status", "reviewed_runner_commit",
        "execution_contract_sha256", "asset_evidence_sha256", "device",
        "wall_timeout_seconds", "job_id", "destination", "stop_after_report",
        "locked_test_used", "single_execution_authorization", "automatic_retry",
        "automatic_promotion", "external_approval_relative_path",
        "persistent_claim_marker_relative_path",
    }
)
_APPROVAL_KEYS = frozenset(
    {
        "schema_version", "purpose", "authorization_request_sha256",
        "reviewed_runner_commit", "authorized_execution_commit",
        "approved_for_exactly_one_execution", "locked_test_used",
    }
)


def _canonical_json_bytes(payload: object) -> bytes:
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _parse_canonical_json(raw: bytes, *, label: str) -> Mapping[str, object]:
    try:
        payload = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is not valid UTF-8 JSON") from exc
    if not isinstance(payload, dict) or _canonical_json_bytes(payload) != raw:
        raise ValueError(f"{label} is not canonical JSON")
    return payload


def _require_exact_request(payload: Mapping[str, object]) -> None:
    if set(payload) != _REQUEST_KEYS:
        raise ValueError("authorization request schema is not exact")
    expected = {
        "schema_version": 1,
        "purpose": "causal_candidate_v2_independent_validation_one_job_authorization_request",
        "status": "pending_external_review",
        "reviewed_runner_commit": REVIEWED_RUNNER_COMMIT,
        "execution_contract_sha256": EXECUTION_CONTRACT_SHA256,
        "asset_evidence_sha256": ASSET_EVIDENCE_SHA256,
        "device": "cpu",
        "wall_timeout_seconds": 900,
        "job_id": JOB_ID,
        "destination": DESTINATION,
        "stop_after_report": True,
        "locked_test_used": False,
        "single_execution_authorization": True,
        "automatic_retry": False,
        "automatic_promotion": False,
        "external_approval_relative_path": EXTERNAL_APPROVAL_RELATIVE_PATH.as_posix(),
        "persistent_claim_marker_relative_path": PERSISTENT_CLAIM_RELATIVE_PATH.as_posix(),
    }
    if (
        dict(payload) != expected
        or type(payload.get("schema_version")) is not int
        or type(payload.get("wall_timeout_seconds")) is not int
        or any(
            type(payload.get(name)) is not bool
            for name in (
                "stop_after_report", "locked_test_used",
                "single_execution_authorization", "automatic_retry",
                "automatic_promotion",
            )
        )
    ):
        raise ValueError("authorization request values are not sealed")


def load_sealed_authorization_request(repository_root: Path) -> Mapping[str, object]:
    root = Path(repository_root).resolve(strict=True)
    expected_path = root / AUTHORIZATION_REQUEST_RELATIVE_PATH
    if expected_path.is_symlink() or expected_path.resolve(strict=True) != expected_path.absolute():
        raise ValueError("authorization request path is not canonical")
    path = expected_path.resolve(strict=True)
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != AUTHORIZATION_REQUEST_SHA256:
        raise ValueError("authorization request SHA-256 mismatch")
    payload = _parse_canonical_json(raw, label="authorization request")
    _require_exact_request(payload)
    return payload


def _load_external_approval(
    repository_root: Path,
    request: Mapping[str, object],
) -> tuple[Mapping[str, object], str]:
    root = Path(repository_root).resolve(strict=True)
    path = root / EXTERNAL_APPROVAL_RELATIVE_PATH
    if not path.is_file():
        raise RuntimeError("external review approval file is absent")
    if path.is_symlink() or path.resolve(strict=True) != path.absolute():
        raise ValueError("external review approval path is not canonical")
    raw = path.read_bytes()
    payload = _parse_canonical_json(raw, label="external review approval")
    if set(payload) != _APPROVAL_KEYS:
        raise ValueError("external review approval schema is not exact")
    authorized_commit = payload.get("authorized_execution_commit")
    if not isinstance(authorized_commit, str) or len(authorized_commit) != 40 or any(
        character not in "0123456789abcdef" for character in authorized_commit
    ):
        raise ValueError("authorized execution commit is not a lowercase Git SHA")
    if (
        type(payload.get("schema_version")) is not int
        or payload.get("schema_version") != 1
        or payload.get("purpose")
        != "causal_candidate_v2_independent_validation_external_review_approval"
        or payload.get("authorization_request_sha256") != AUTHORIZATION_REQUEST_SHA256
        or payload.get("reviewed_runner_commit") != REVIEWED_RUNNER_COMMIT
        or type(payload.get("approved_for_exactly_one_execution")) is not bool
        or payload.get("approved_for_exactly_one_execution") is not True
        or type(payload.get("locked_test_used")) is not bool
        or payload.get("locked_test_used") is not False
        or request.get("reviewed_runner_commit") != REVIEWED_RUNNER_COMMIT
    ):
        raise ValueError("external review approval values are not sealed")
    return payload, hashlib.sha256(raw).hexdigest()


def _git(repository_root: Path, *arguments: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repository_root), *arguments],
        check=True,
        capture_output=True,
        text=True,
    ).stdout


def _git_head(repository_root: Path) -> str:
    return _git(repository_root, "rev-parse", "HEAD").strip()


def _git_worktree_clean(repository_root: Path) -> bool:
    return not _git(repository_root, "status", "--porcelain").strip()


def _git_diff_names(repository_root: Path, head: str) -> frozenset[str]:
    return frozenset(
        line.strip().replace("\\", "/")
        for line in _git(
            repository_root, "diff", "--name-only", REVIEWED_RUNNER_COMMIT, head,
        ).splitlines()
        if line.strip()
    )


def _runner_blob_unchanged(repository_root: Path, head: str) -> bool:
    reviewed = subprocess.run(
        ["git", "-C", str(repository_root), "show", f"{REVIEWED_RUNNER_COMMIT}:{RUNNER_RELATIVE_PATH.as_posix()}"],
        check=True,
        capture_output=True,
    ).stdout
    current = subprocess.run(
        ["git", "-C", str(repository_root), "show", f"{head}:{RUNNER_RELATIVE_PATH.as_posix()}"],
        check=True,
        capture_output=True,
    ).stdout
    return reviewed == current


def _verify_git_boundary(repository_root: Path, approval: Mapping[str, object]) -> str:
    head = _git_head(repository_root)
    if approval.get("authorized_execution_commit") != head:
        raise ValueError("external approval does not authorize current HEAD")
    if not _git_worktree_clean(repository_root):
        raise RuntimeError("authorization requires a clean worktree")
    changed = _git_diff_names(repository_root, head)
    if changed != AUTHORIZATION_STEP_PATHS:
        raise RuntimeError("authorization commit contains an unexpected changed file set")
    if not _runner_blob_unchanged(repository_root, head):
        raise RuntimeError("approved independent V2 runner changed after review")
    return head


def _create_persistent_claim_marker(
    repository_root: Path,
    *,
    external_approval_sha256: str,
    authorized_execution_commit: str,
) -> Path:
    root = Path(repository_root).resolve(strict=True)
    marker = root / PERSISTENT_CLAIM_RELATIVE_PATH
    marker.parent.mkdir(parents=True, exist_ok=True)
    if marker.parent.resolve(strict=True) != marker.parent.absolute():
        raise ValueError("persistent claim marker directory is not canonical")
    payload = {
        "authorization_request_sha256": AUTHORIZATION_REQUEST_SHA256,
        "authorized_execution_commit": authorized_execution_commit,
        "claimed_at_utc": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
        "external_approval_sha256": external_approval_sha256,
        "job_id": JOB_ID,
    }
    descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(_canonical_json_bytes(payload))
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        # The marker is deliberately retained even when writing/fsync fails.
        raise
    return marker


def _tensorflow_imported() -> bool:
    return "tensorflow" in sys.modules


def execute_externally_approved_independent_v2_once(
    repository_root: Path,
) -> Mapping[str, object]:
    """Consume external approval and invoke the approved runner exactly once."""

    root = Path(repository_root).resolve(strict=True)
    request = load_sealed_authorization_request(root)
    approval, approval_sha256 = _load_external_approval(root, request)
    authorized_commit = _verify_git_boundary(root, approval)
    _create_persistent_claim_marker(
        root,
        external_approval_sha256=approval_sha256,
        authorized_execution_commit=authorized_commit,
    )

    from . import run_causal_candidate_v2_independent_validation_execution as runner

    capability = runner.IndependentV2OneJobCapability(
        runner_commit=authorized_commit,
        execution_contract_sha256=EXECUTION_CONTRACT_SHA256,
        device="cpu",
        wall_timeout_seconds=900,
        job_id=JOB_ID,
        destination=DESTINATION,
        stop_after_report=True,
        locked_test_used=False,
        single_execution_authorization=True,
    )
    runner._ONE_JOB_CAPABILITIES[id(capability)] = weakref.ref(capability)
    os.environ["MIDI_FORCE_CPU"] = "1"
    if _tensorflow_imported():
        raise RuntimeError("TensorFlow was imported before one-job runner invocation")
    return runner.run_authorized_independent_v2(root, capability)


__all__ = [
    "AUTHORIZATION_REQUEST_RELATIVE_PATH",
    "AUTHORIZATION_REQUEST_SHA256",
    "EXTERNAL_APPROVAL_RELATIVE_PATH",
    "PERSISTENT_CLAIM_RELATIVE_PATH",
    "execute_externally_approved_independent_v2_once",
    "load_sealed_authorization_request",
]
