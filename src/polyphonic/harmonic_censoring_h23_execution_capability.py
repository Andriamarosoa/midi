"""Dormant, fail-closed execution capability for H23 synthetic evaluation.

This module is administrative only.  It imports neither NumPy nor any project
data/model loader.  The canonical authorization seal deliberately does not
exist in this commit, so :func:`issue_h23_synthetic_execution_capability`
always fails before resolving fixtures, checking runtime packages, creating a
claim marker, or allocating a waveform.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import threading
from typing import Mapping, Sequence
import weakref

from .harmonic_censoring_h23 import (
    H23_CONTRACT_SHA256,
    H23HarnessPlan,
    canonical_json_bytes,
    load_h23_harness_plan,
)


H23_CAPABILITY_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h23_synthetic_execution_capability_contract.json"
)
H23_CAPABILITY_CONTRACT_SHA256 = (
    "95458fc4e261d5cf7e4e9aed78bc379a9940b22c39ae7799b53c6301a3d8363f"
)
H23_AUTHORIZATION_SEAL_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h23_synthetic_execution_authorization_seal.json"
)
# A later, separately reviewed seal commit must replace this with its raw hash.
H23_AUTHORIZATION_SEAL_SHA256: str | None = None

H23_FIXTURE_MANIFEST_SHA256 = (
    "acfa37b987deb19884c9f60cf3410717b68788eb466396402aaf992b3224e19c"
)
H23_RESOLVED_TEST_MANIFEST_SHA256 = (
    "0d059d3f2540f2b08279bb8363e9036ae0f71b2bea11575bfebfce76b7fe7504"
)
H23_APPROVED_HARNESS_COMMIT = "e97674cd1d1c3a12ff113f98789105941ab17030"
H23_CONTRACT_GIT_BLOB = "864abd127ffed9daf3e5d64dddf0aedbbda8296a"
H23_HARNESS_GIT_BLOB = "548e6cc1500e682170cc7043fe694474e3bbd647"
H23_HARNESS_TEST_GIT_BLOB = "e9c03542e4c90a66895302492ce818bea5a9faca"
H23_CONTRACT_RELATIVE_PATH = Path("configs/harmonic_censoring_pretrain_h23_contract.json")
H23_HARNESS_RELATIVE_PATH = Path("src/polyphonic/harmonic_censoring_h23.py")
H23_HARNESS_TEST_RELATIVE_PATH = Path("tests/test_harmonic_censoring_h23_harness.py")
H23_CAPABILITY_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/harmonic_censoring_h23_execution_capability.py"
)
H23_RUNNER_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/run_harmonic_censoring_h23_synthetic.py"
)

def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_duplicate_pairs(
    pairs: Sequence[tuple[str, object]],
) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H23 authorization seal duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H23 authorization seal forbids numeric token {token!r}.")


def _load_json_object(raw: bytes) -> dict[str, object]:
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("H23 authorization seal must be UTF-8.") from exc
    value = json.loads(
        text,
        object_pairs_hook=_reject_duplicate_pairs,
        parse_constant=_reject_nonfinite,
    )
    if not isinstance(value, dict):
        raise ValueError("H23 authorization seal root must be an object.")
    return value


def _require_exact_keys(
    value: Mapping[str, object], expected: Sequence[str], label: str
) -> None:
    if set(value) != set(expected):
        raise ValueError(
            f"H23 {label} keys mismatch: missing={sorted(set(expected) - set(value))}, "
            f"extra={sorted(set(value) - set(expected))}."
        )


def _require_object(value: object, label: str) -> Mapping[str, object]:
    if not isinstance(value, Mapping):
        raise ValueError(f"H23 {label} must be an object.")
    return value


def _require_lower_hex(value: object, length: int, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != length
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"H23 {label} must be lowercase hexadecimal length {length}.")
    return value


def _require_relative_path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"H23 {label} must be a non-empty relative path.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"H23 {label} must stay inside the repository.")
    return path


@dataclass(frozen=True)
class H23AuthorizationSeal:
    """Parsed value record; it is not itself an execution capability."""

    raw_sha256: str
    reviewed_execution_commit: str
    exact_changed_files: tuple[str, ...]
    capability_source_blob: str
    runner_source_blob: str
    success_destination: Path
    terminal_record_destination: Path
    authorization_marker: Path


def validate_h23_authorization_seal_payload(
    payload: Mapping[str, object], *, raw_sha256: str
) -> H23AuthorizationSeal:
    """Validate the future seal schema without issuing or claiming anything."""

    _require_exact_keys(
        payload,
        (
            "schema_version",
            "purpose",
            "status",
            "authorization",
            "bindings",
            "runtime_identity",
            "one_shot_paths",
            "external_review",
        ),
        "authorization seal",
    )
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("H23 authorization seal schema version mismatch.")
    if payload["purpose"] != "harmonic_censoring_h23_synthetic_execution_authorization_seal":
        raise ValueError("H23 authorization seal purpose mismatch.")
    if payload["status"] != "externally_approved_one_shot_synthetic_execution":
        raise ValueError("H23 authorization seal status mismatch.")

    authorization = _require_object(payload["authorization"], "authorization")
    required_true = (
        "capability_issuance_authorized",
        "synthetic_execution_authorized",
        "scientific_execution_authorized",
        "P0_execution_authorized",
        "P1_execution_authorized",
        "P2_execution_authorized",
    )
    required_false = (
        "real_data_access_authorized",
        "training_authorized",
        "H17_population_used",
        "locked_test_used",
    )
    _require_exact_keys(authorization, required_true + required_false, "authorization")
    for right in required_true:
        if authorization[right] is not True:
            raise PermissionError(f"H23 seal right {right} is not authorized.")
    for prohibition in required_false:
        if authorization[prohibition] is not False:
            raise PermissionError(f"H23 seal prohibition {prohibition} is not false.")

    bindings = _require_object(payload["bindings"], "bindings")
    _require_exact_keys(
        bindings,
        (
            "H23_contract_raw_sha256",
            "capability_contract_raw_sha256",
            "fixture_manifest_sha256",
            "resolved_test_manifest_sha256",
            "reviewed_execution_commit",
            "exact_changed_files",
            "capability_source_blob",
            "runner_source_blob",
        ),
        "bindings",
    )
    expected_hashes = {
        "H23_contract_raw_sha256": H23_CONTRACT_SHA256,
        "capability_contract_raw_sha256": H23_CAPABILITY_CONTRACT_SHA256,
        "fixture_manifest_sha256": H23_FIXTURE_MANIFEST_SHA256,
        "resolved_test_manifest_sha256": H23_RESOLVED_TEST_MANIFEST_SHA256,
    }
    for name, expected in expected_hashes.items():
        if bindings[name] != expected:
            raise ValueError(f"H23 seal binding {name} mismatch.")
    commit = _require_lower_hex(bindings["reviewed_execution_commit"], 40, "commit")
    capability_blob = _require_lower_hex(
        bindings["capability_source_blob"], 40, "capability source blob"
    )
    runner_blob = _require_lower_hex(
        bindings["runner_source_blob"], 40, "runner source blob"
    )
    files = bindings["exact_changed_files"]
    if (
        not isinstance(files, list)
        or not files
        or any(not isinstance(item, str) or not item for item in files)
        or files != sorted(set(files))
    ):
        raise ValueError("H23 exact_changed_files must be a sorted unique list.")
    required_sources = {
        H23_CAPABILITY_SOURCE_RELATIVE_PATH.as_posix(),
        H23_RUNNER_SOURCE_RELATIVE_PATH.as_posix(),
    }
    if not required_sources.issubset(files):
        raise ValueError("H23 implementation changed-file set omits runner sources.")

    runtime = _require_object(payload["runtime_identity"], "runtime_identity")
    expected_runtime = {
        "implementation": "CPython",
        "python_version": "3.11.9",
        "numpy_version": "1.26.4",
        "architecture": "arm64",
        "execution_device": "CPU",
        "thread_count": 1,
    }
    if dict(runtime) != expected_runtime:
        raise ValueError("H23 authorization runtime identity mismatch.")

    paths = _require_object(payload["one_shot_paths"], "one_shot_paths")
    _require_exact_keys(
        paths,
        ("success_destination", "terminal_record_destination", "authorization_marker"),
        "one_shot_paths",
    )
    success = _require_relative_path(paths["success_destination"], "success destination")
    terminal = _require_relative_path(
        paths["terminal_record_destination"], "terminal record destination"
    )
    marker = _require_relative_path(paths["authorization_marker"], "authorization marker")
    if len({success, terminal, marker}) != 3:
        raise ValueError("H23 one-shot paths must be distinct.")

    review = _require_object(payload["external_review"], "external_review")
    _require_exact_keys(
        review,
        ("verdict", "reviewed_execution_commit", "authorization_seal_review_required"),
        "external_review",
    )
    if (
        review["verdict"] != "APPROVED"
        or review["reviewed_execution_commit"] != commit
        or review["authorization_seal_review_required"] is not True
    ):
        raise PermissionError("H23 external-review binding is not approved.")

    return H23AuthorizationSeal(
        raw_sha256=_require_lower_hex(raw_sha256, 64, "authorization seal SHA-256"),
        reviewed_execution_commit=commit,
        exact_changed_files=tuple(files),
        capability_source_blob=capability_blob,
        runner_source_blob=runner_blob,
        success_destination=success,
        terminal_record_destination=terminal,
        authorization_marker=marker,
    )


class AttestedH23SyntheticExecutionCapability:
    """Identity-attested, process-local authority; never a public value token."""

    __slots__ = (
        "contract_sha256",
        "capability_contract_sha256",
        "fixture_manifest_sha256",
        "resolved_test_manifest_sha256",
        "approved_harness_git_blob",
        "implementation_commit",
        "authorization_seal_sha256",
        "success_destination",
        "terminal_record_destination",
        "authorization_marker",
        "_sealed",
        "__weakref__",
    )

    def __init__(
        self,
        *args: object,
        **kwargs: object,
    ) -> None:
        del args, kwargs
        raise TypeError("H23 capability construction is factory-only.")

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("H23 capability is immutable.")

    def __copy__(self) -> object:
        raise TypeError("H23 capability cannot be copied.")

    def __deepcopy__(self, memo: object) -> object:
        del memo
        raise TypeError("H23 capability cannot be deep-copied.")

    def __reduce_ex__(self, protocol: int) -> object:
        del protocol
        raise TypeError("H23 capability cannot be serialized.")


def _git(repository: Path, *arguments: str) -> str:
    return subprocess.check_output(
        ["git", *arguments], cwd=repository, text=True, encoding="utf-8"
    ).strip()


def _resolve_bound_path(repository: Path, relative: Path) -> Path:
    candidate = (repository / relative).resolve()
    try:
        candidate.relative_to(repository)
    except ValueError as exc:
        raise ValueError("H23 sealed path escapes repository root.") from exc
    return candidate


def load_h23_authorization_seal(repository_root: Path) -> H23AuthorizationSeal:
    """Load the fixed future seal; fail before any other preflight while absent."""

    if H23_AUTHORIZATION_SEAL_SHA256 is None:
        raise PermissionError(
            "H23 execution remains dormant: no reviewed authorization seal SHA exists."
        )
    repository = Path(repository_root).resolve(strict=True)
    path = _resolve_bound_path(repository, H23_AUTHORIZATION_SEAL_RELATIVE_PATH)
    raw = path.read_bytes()
    actual = _sha256(raw)
    if actual != H23_AUTHORIZATION_SEAL_SHA256:
        raise ValueError("H23 authorization seal SHA-256 mismatch.")
    return validate_h23_authorization_seal_payload(
        _load_json_object(raw), raw_sha256=actual
    )


def _validate_repository_and_runtime(
    repository: Path, seal: H23AuthorizationSeal, plan: H23HarnessPlan
) -> None:
    capability_contract = _resolve_bound_path(
        repository, H23_CAPABILITY_CONTRACT_RELATIVE_PATH
    ).read_bytes()
    if _sha256(capability_contract) != H23_CAPABILITY_CONTRACT_SHA256:
        raise ValueError("H23 capability contract SHA-256 mismatch.")
    if plan.contract_sha256 != H23_CONTRACT_SHA256:
        raise ValueError("H23 plan contract SHA-256 mismatch.")
    if plan.fixture_manifest_sha256 != H23_FIXTURE_MANIFEST_SHA256:
        raise ValueError("H23 fixture manifest SHA-256 mismatch.")
    if plan.resolved_test_manifest_sha256 != H23_RESOLVED_TEST_MANIFEST_SHA256:
        raise ValueError("H23 resolved-test manifest SHA-256 mismatch.")
    if _git(repository, "status", "--porcelain"):
        raise RuntimeError("H23 execution requires a clean worktree.")
    for relative, expected in (
        (H23_CONTRACT_RELATIVE_PATH, H23_CONTRACT_GIT_BLOB),
        (H23_HARNESS_RELATIVE_PATH, H23_HARNESS_GIT_BLOB),
        (H23_HARNESS_TEST_RELATIVE_PATH, H23_HARNESS_TEST_GIT_BLOB),
    ):
        approved = _git(
            repository,
            "rev-parse",
            f"{H23_APPROVED_HARNESS_COMMIT}:{relative.as_posix()}",
        )
        current = _git(repository, "hash-object", relative.as_posix())
        if approved != expected or current != expected:
            raise ValueError(f"H23 approved harness binding drifted for {relative}.")
    if _git(repository, "cat-file", "-t", seal.reviewed_execution_commit) != "commit":
        raise ValueError("H23 reviewed execution commit does not exist.")
    changed = tuple(
        sorted(
            line
            for line in _git(
                repository,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                seal.reviewed_execution_commit,
            ).splitlines()
            if line
        )
    )
    if changed != seal.exact_changed_files:
        raise ValueError("H23 reviewed execution changed-file set mismatch.")
    for relative, expected in (
        (H23_CAPABILITY_SOURCE_RELATIVE_PATH, seal.capability_source_blob),
        (H23_RUNNER_SOURCE_RELATIVE_PATH, seal.runner_source_blob),
    ):
        actual = _git(
            repository,
            "rev-parse",
            f"{seal.reviewed_execution_commit}:{relative.as_posix()}",
        )
        if actual != expected:
            raise ValueError(f"H23 reviewed source blob mismatch for {relative}.")
        if _git(repository, "hash-object", relative.as_posix()) != expected:
            raise ValueError(f"H23 checkout source bytes drifted for {relative}.")
    if (
        platform.python_implementation() != "CPython"
        or platform.python_version() != "3.11.9"
        or platform.machine().lower() != "arm64"
        or importlib.metadata.version("numpy") != "1.26.4"
        or os.environ.get("MIDI_FORCE_CPU") != "1"
        or os.environ.get("OMP_NUM_THREADS") != "1"
        or os.environ.get("OPENBLAS_NUM_THREADS") != "1"
        or os.environ.get("MKL_NUM_THREADS") != "1"
        or os.environ.get("NUMEXPR_NUM_THREADS") != "1"
    ):
        raise RuntimeError("H23 runtime identity mismatch.")


def _build_h23_capability_authority():
    """Create the only mint/registry closure; expose no token or register helper."""

    registered_capabilities: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...]]
    ] = {}
    claimed_capabilities: dict[int, weakref.ReferenceType[object]] = {}
    claim_lock = threading.Lock()

    def binding(
        value: AttestedH23SyntheticExecutionCapability,
    ) -> tuple[object, ...]:
        return (
            value.contract_sha256,
            value.capability_contract_sha256,
            value.fixture_manifest_sha256,
            value.resolved_test_manifest_sha256,
            value.approved_harness_git_blob,
            value.implementation_commit,
            value.authorization_seal_sha256,
            value.success_destination,
            value.terminal_record_destination,
            value.authorization_marker,
        )

    def require(
        value: object,
    ) -> AttestedH23SyntheticExecutionCapability:
        if not isinstance(value, AttestedH23SyntheticExecutionCapability):
            raise TypeError("H23 execution requires its exact capability type.")
        registered = registered_capabilities.get(id(value))
        if (
            registered is None
            or registered[0]() is not value
            or registered[1] != binding(value)
        ):
            raise PermissionError("H23 execution capability is not factory-attested.")
        return value

    def issue(
        repository_root: Path,
    ) -> AttestedH23SyntheticExecutionCapability:
        """Issue only after a later fixed seal exists and all preflights pass."""

        # This is intentionally first.  In the present commit it always fails,
        # before plan resolution, package inspection, path access, or claim state.
        seal = load_h23_authorization_seal(repository_root)
        repository = Path(repository_root).resolve(strict=True)
        plan = load_h23_harness_plan(repository)
        _validate_repository_and_runtime(repository, seal, plan)
        success = _resolve_bound_path(repository, seal.success_destination)
        terminal = _resolve_bound_path(repository, seal.terminal_record_destination)
        marker = _resolve_bound_path(repository, seal.authorization_marker)
        for path in (success, terminal, marker):
            if path.exists():
                raise FileExistsError(f"H23 sealed one-shot path already exists: {path}")
        created = object.__new__(AttestedH23SyntheticExecutionCapability)
        values = {
            "contract_sha256": plan.contract_sha256,
            "capability_contract_sha256": H23_CAPABILITY_CONTRACT_SHA256,
            "fixture_manifest_sha256": plan.fixture_manifest_sha256,
            "resolved_test_manifest_sha256": plan.resolved_test_manifest_sha256,
            "approved_harness_git_blob": H23_HARNESS_GIT_BLOB,
            "implementation_commit": seal.reviewed_execution_commit,
            "authorization_seal_sha256": seal.raw_sha256,
            "success_destination": success,
            "terminal_record_destination": terminal,
            "authorization_marker": marker,
            "_sealed": True,
        }
        for name, value in values.items():
            object.__setattr__(created, name, value)
        identity = id(created)

        def cleanup(reference: weakref.ReferenceType[object]) -> None:
            registered = registered_capabilities.get(identity)
            if registered is not None and registered[0] is reference:
                registered_capabilities.pop(identity, None)
            if claimed_capabilities.get(identity) is reference:
                claimed_capabilities.pop(identity, None)

        reference = weakref.ref(created, cleanup)
        registered_capabilities[identity] = (reference, binding(created))
        return created

    def claim(
        value: object,
    ) -> AttestedH23SyntheticExecutionCapability:
        """Persist population consumption atomically before the first waveform."""

        with claim_lock:
            capability = require(value)
            claimed = claimed_capabilities.get(id(capability))
            if claimed is not None and claimed() is capability:
                raise RuntimeError("H23 capability was already claimed.")
            marker_payload = canonical_json_bytes(
                {
                    "schema_version": 1,
                    "purpose": "harmonic_censoring_h23_synthetic_population_consumption",
                    "synthetic_population_consumed": True,
                    "authorization_seal_sha256": capability.authorization_seal_sha256,
                    "implementation_commit": capability.implementation_commit,
                    "fixture_manifest_sha256": capability.fixture_manifest_sha256,
                    "resolved_test_manifest_sha256": capability.resolved_test_manifest_sha256,
                    "approved_harness_git_blob": capability.approved_harness_git_blob,
                }
            )
            capability.authorization_marker.parent.mkdir(parents=True, exist_ok=True)
            descriptor = os.open(
                capability.authorization_marker,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL,
                0o600,
            )
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(marker_payload)
                    stream.flush()
                    os.fsync(stream.fileno())
                directory_descriptor = os.open(
                    capability.authorization_marker.parent, os.O_RDONLY
                )
                try:
                    os.fsync(directory_descriptor)
                finally:
                    os.close(directory_descriptor)
            except BaseException:
                # The marker is never removed: a failed claim remains consumed.
                raise
            reference = weakref.ref(capability)
            claimed_capabilities[id(capability)] = reference
            return capability

    def require_claimed(
        value: object,
    ) -> AttestedH23SyntheticExecutionCapability:
        capability = require(value)
        reference = claimed_capabilities.get(id(capability))
        if reference is None or reference() is not capability:
            raise PermissionError("H23 capability has not crossed its one-shot claim.")
        return capability

    return issue, require, claim, require_claimed


(
    issue_h23_synthetic_execution_capability,
    require_attested_h23_synthetic_execution_capability,
    claim_h23_synthetic_execution_capability,
    require_claimed_h23_synthetic_execution_capability,
) = _build_h23_capability_authority()
del _build_h23_capability_authority


__all__ = [
    "AttestedH23SyntheticExecutionCapability",
    "H23AuthorizationSeal",
    "H23_AUTHORIZATION_SEAL_RELATIVE_PATH",
    "H23_AUTHORIZATION_SEAL_SHA256",
    "H23_CAPABILITY_CONTRACT_SHA256",
    "claim_h23_synthetic_execution_capability",
    "issue_h23_synthetic_execution_capability",
    "load_h23_authorization_seal",
    "require_attested_h23_synthetic_execution_capability",
    "require_claimed_h23_synthetic_execution_capability",
    "validate_h23_authorization_seal_payload",
]
