"""Dormant, fail-closed execution capability for H23 synthetic evaluation.

This module is administrative only.  It imports neither NumPy nor any project
data/model loader.  The canonical authorization activation and seal
deliberately do not exist in this commit, so
:func:`issue_h23_synthetic_execution_capability` always fails before resolving
fixtures, checking runtime packages, creating a claim marker, or allocating a
waveform.
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
from typing import Mapping, Sequence
import weakref

from .harmonic_censoring_h23 import (
    H23_CONTRACT_SHA256,
    H23HarnessPlan,
    load_h23_harness_plan,
)


H23_CAPABILITY_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h23_synthetic_execution_capability_contract.json"
)
H23_CAPABILITY_CONTRACT_SHA256 = (
    "87f9288ad25816573fd6076856320f182829cb77e4643bf887d2b1571ad819ec"
)
H23_AUTHORIZATION_SEAL_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h23_synthetic_execution_authorization_seal.json"
)
H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h23_synthetic_execution_activation.json"
)
H23_AUTHORIZATION_ACTIVATION_COMMIT_ENV = "H23_AUTHORIZATION_ACTIVATION_COMMIT"
H23_CONSUMPTION_CLAIM_IMPLEMENTED = True
H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h23_executor_claim_transcript_contract.json"
)
H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256 = (
    "8126edc0a27fe43bbb41f0d8e874c1355e01f9f1185c1a71d70048fcaea661ef"
)

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
    executor_claim_transcript_contract_raw_sha256: str
    success_destination: Path
    terminal_record_destination: Path
    authorization_marker: Path
    transcript_path: Path


@dataclass(frozen=True)
class H23AuthorizationActivation:
    """OS-bound pointer from a reviewed activation commit to a fixed seal."""

    raw_sha256: str
    authorization_seal_path: Path
    authorization_seal_sha256: str
    implementation_commit: str
    capability_source_blob: str
    runner_source_blob: str
    executor_claim_transcript_contract_raw_sha256: str


@dataclass(frozen=True)
class H23AuthorizationContext:
    activation_commit: str
    activation: H23AuthorizationActivation
    seal: H23AuthorizationSeal


def validate_h23_authorization_activation_payload(
    payload: Mapping[str, object], *, raw_sha256: str
) -> H23AuthorizationActivation:
    """Validate the future activation artifact without loading the seal."""

    _require_exact_keys(
        payload,
        (
            "schema_version",
            "purpose",
            "status",
            "authorization_seal",
            "bindings",
            "external_review",
        ),
        "authorization activation",
    )
    if type(payload["schema_version"]) is not int or payload["schema_version"] != 1:
        raise ValueError("H23 authorization activation schema version mismatch.")
    if payload["purpose"] != "harmonic_censoring_h23_synthetic_execution_activation":
        raise ValueError("H23 authorization activation purpose mismatch.")
    if payload["status"] != "externally_reviewed_seal_activation":
        raise ValueError("H23 authorization activation status mismatch.")

    seal = _require_object(payload["authorization_seal"], "activation seal")
    _require_exact_keys(seal, ("path", "raw_sha256"), "activation seal")
    seal_path = _require_relative_path(seal["path"], "activation seal path")
    if seal_path != H23_AUTHORIZATION_SEAL_RELATIVE_PATH:
        raise ValueError("H23 activation seal path is not canonical.")

    bindings = _require_object(payload["bindings"], "activation bindings")
    _require_exact_keys(
        bindings,
        (
            "implementation_commit",
            "capability_source_blob",
            "runner_source_blob",
            "executor_claim_transcript_contract_raw_sha256",
        ),
        "activation bindings",
    )
    review = _require_object(payload["external_review"], "activation external review")
    _require_exact_keys(
        review,
        ("verdict", "authorization_seal_reviewed", "activation_commit_review_required"),
        "activation external review",
    )
    if (
        review["verdict"] != "APPROVED"
        or review["authorization_seal_reviewed"] is not True
        or review["activation_commit_review_required"] is not True
    ):
        raise PermissionError("H23 activation external review is not approved.")
    return H23AuthorizationActivation(
        raw_sha256=_require_lower_hex(raw_sha256, 64, "authorization activation SHA-256"),
        authorization_seal_path=seal_path,
        authorization_seal_sha256=_require_lower_hex(
            seal["raw_sha256"], 64, "activation seal SHA-256"
        ),
        implementation_commit=_require_lower_hex(
            bindings["implementation_commit"], 40, "activation implementation commit"
        ),
        capability_source_blob=_require_lower_hex(
            bindings["capability_source_blob"], 40, "activation capability source blob"
        ),
        runner_source_blob=_require_lower_hex(
            bindings["runner_source_blob"], 40, "activation runner source blob"
        ),
        executor_claim_transcript_contract_raw_sha256=_require_lower_hex(
            bindings["executor_claim_transcript_contract_raw_sha256"],
            64,
            "activation executor claim transcript contract SHA-256",
        ),
    )


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
            "executor_claim_transcript_contract_raw_sha256",
        ),
        "bindings",
    )
    expected_hashes = {
        "H23_contract_raw_sha256": H23_CONTRACT_SHA256,
        "capability_contract_raw_sha256": H23_CAPABILITY_CONTRACT_SHA256,
        "fixture_manifest_sha256": H23_FIXTURE_MANIFEST_SHA256,
        "resolved_test_manifest_sha256": H23_RESOLVED_TEST_MANIFEST_SHA256,
        "executor_claim_transcript_contract_raw_sha256": (
            H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256
        ),
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
        (
            "success_destination",
            "terminal_record_destination",
            "authorization_marker",
            "transcript_path",
        ),
        "one_shot_paths",
    )
    success = _require_relative_path(paths["success_destination"], "success destination")
    terminal = _require_relative_path(
        paths["terminal_record_destination"], "terminal record destination"
    )
    marker = _require_relative_path(paths["authorization_marker"], "authorization marker")
    transcript = _require_relative_path(paths["transcript_path"], "transcript path")
    if len({success, terminal, marker, transcript}) != 4:
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
        executor_claim_transcript_contract_raw_sha256=_require_lower_hex(
            bindings["executor_claim_transcript_contract_raw_sha256"],
            64,
            "executor claim transcript contract SHA-256",
        ),
        success_destination=success,
        terminal_record_destination=terminal,
        authorization_marker=marker,
        transcript_path=transcript,
    )


class AttestedH23SyntheticExecutionCapability:
    """Identity-attested, process-local authority; never a public value token."""

    __slots__ = (
        "contract_sha256",
        "capability_contract_sha256",
        "executor_claim_transcript_contract_raw_sha256",
        "fixture_manifest_sha256",
        "resolved_test_manifest_sha256",
        "approved_harness_git_blob",
        "implementation_commit",
        "authorization_activation_commit",
        "authorization_activation_sha256",
        "authorization_seal_sha256",
        "capability_source_blob",
        "runner_source_blob",
        "runtime_identity",
        "repository_root",
        "success_destination",
        "terminal_record_destination",
        "authorization_marker",
        "transcript_path",
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


def _load_h23_authorization_context(repository_root: Path) -> H23AuthorizationContext:
    """Load activation and seal as one immutable authority context."""

    activation_commit_raw = os.environ.get(H23_AUTHORIZATION_ACTIVATION_COMMIT_ENV)
    if activation_commit_raw is None:
        raise PermissionError(
            "H23 execution remains dormant: no OS-bound reviewed activation commit exists."
        )
    activation_commit = _require_lower_hex(
        activation_commit_raw, 40, "authorization activation commit"
    )
    repository = Path(repository_root).resolve(strict=True)
    if _git(repository, "status", "--porcelain"):
        raise RuntimeError("H23 activation requires a clean worktree.")
    if _git(repository, "rev-parse", "HEAD") != activation_commit:
        raise ValueError("H23 checkout HEAD does not match the OS-bound activation commit.")

    activation_path = _resolve_bound_path(
        repository, H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH
    )
    activation_blob = _git(
        repository,
        "rev-parse",
        f"{activation_commit}:{H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH.as_posix()}",
    )
    if _git(repository, "hash-object", activation_path.as_posix()) != activation_blob:
        raise ValueError("H23 activation bytes differ from the reviewed activation commit.")
    activation_raw = activation_path.read_bytes()
    activation = validate_h23_authorization_activation_payload(
        _load_json_object(activation_raw), raw_sha256=_sha256(activation_raw)
    )

    path = _resolve_bound_path(repository, activation.authorization_seal_path)
    raw = path.read_bytes()
    actual = _sha256(raw)
    if actual != activation.authorization_seal_sha256:
        raise ValueError("H23 authorization seal SHA-256 mismatch.")
    seal = validate_h23_authorization_seal_payload(
        _load_json_object(raw), raw_sha256=actual
    )
    if (
        activation.implementation_commit != seal.reviewed_execution_commit
        or activation.capability_source_blob != seal.capability_source_blob
        or activation.runner_source_blob != seal.runner_source_blob
        or activation.executor_claim_transcript_contract_raw_sha256
        != seal.executor_claim_transcript_contract_raw_sha256
    ):
        raise ValueError("H23 activation and authorization seal bindings differ.")
    return H23AuthorizationContext(
        activation_commit=activation_commit,
        activation=activation,
        seal=seal,
    )


def load_h23_authorization_seal(repository_root: Path) -> H23AuthorizationSeal:
    """Load a seal pinned by a separately reviewed, OS-bound activation commit."""

    return _load_h23_authorization_context(repository_root).seal


def _validate_repository_and_runtime(
    repository: Path, seal: H23AuthorizationSeal, plan: H23HarnessPlan
) -> None:
    capability_contract = _resolve_bound_path(
        repository, H23_CAPABILITY_CONTRACT_RELATIVE_PATH
    ).read_bytes()
    if _sha256(capability_contract) != H23_CAPABILITY_CONTRACT_SHA256:
        raise ValueError("H23 capability contract SHA-256 mismatch.")
    executor_contract = _resolve_bound_path(
        repository, H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH
    ).read_bytes()
    if _sha256(executor_contract) != H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256:
        raise ValueError("H23 executor claim transcript contract SHA-256 mismatch.")
    if (
        seal.executor_claim_transcript_contract_raw_sha256
        != H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256
    ):
        raise ValueError("H23 seal executor claim transcript contract binding mismatch.")
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


def _canonical_json_line(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _write_exclusive_durable_file(path: Path, raw: bytes) -> None:
    """Create one irreversible claim file; never clean it up after O_EXCL."""

    destination = Path(path)
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        destination,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        view = memoryview(raw)
        written = 0
        while written < len(view):
            count = os.write(descriptor, view[written:])
            if count <= 0:
                raise OSError("H23 marker write made no progress.")
            written += count
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if os.name != "nt":
        directory = os.open(destination.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)


def _h23_marker_payload(
    capability: AttestedH23SyntheticExecutionCapability,
) -> dict[str, object]:
    repository = capability.repository_root
    return {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h23_synthetic_population_consumption_marker",
        "synthetic_population_consumed": True,
        "claim_state": "CLAIMED_BEFORE_FIRST_WAVEFORM",
        "authorization_activation_commit": capability.authorization_activation_commit,
        "authorization_activation_sha256": capability.authorization_activation_sha256,
        "authorization_seal_sha256": capability.authorization_seal_sha256,
        "implementation_commit": capability.implementation_commit,
        "capability_source_blob": capability.capability_source_blob,
        "runner_source_blob": capability.runner_source_blob,
        "H23_contract_raw_sha256": capability.contract_sha256,
        "capability_contract_raw_sha256": capability.capability_contract_sha256,
        "executor_claim_transcript_contract_raw_sha256": (
            capability.executor_claim_transcript_contract_raw_sha256
        ),
        "fixture_manifest_sha256": capability.fixture_manifest_sha256,
        "resolved_test_manifest_sha256": capability.resolved_test_manifest_sha256,
        "runtime_identity": dict(capability.runtime_identity),
        "fixture_count": 175,
        "test_count": 72,
        "transcript_relative_path": capability.transcript_path.relative_to(
            repository
        ).as_posix(),
        "real_data_used": False,
        "H17_population_used": False,
        "locked_test_used": False,
    }


def _revalidate_h23_claim_authority(
    capability: AttestedH23SyntheticExecutionCapability,
) -> None:
    """Confirm the issued snapshot without reading mutable environment authority."""

    repository = capability.repository_root
    expected_files = (
        (
            H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH,
            capability.authorization_activation_sha256,
        ),
        (H23_AUTHORIZATION_SEAL_RELATIVE_PATH, capability.authorization_seal_sha256),
        (
            H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH,
            capability.executor_claim_transcript_contract_raw_sha256,
        ),
    )
    for relative, expected in expected_files:
        actual = _sha256(_resolve_bound_path(repository, relative).read_bytes())
        if actual != expected:
            raise ValueError(f"H23 preclaim authority bytes changed for {relative}.")
    for relative, expected in (
        (H23_CAPABILITY_SOURCE_RELATIVE_PATH, capability.capability_source_blob),
        (H23_RUNNER_SOURCE_RELATIVE_PATH, capability.runner_source_blob),
    ):
        if _git(repository, "hash-object", relative.as_posix()) != expected:
            raise ValueError(f"H23 preclaim source bytes changed for {relative}.")
    for path in (
        capability.success_destination,
        capability.terminal_record_destination,
        capability.transcript_path,
    ):
        if path.exists():
            raise FileExistsError(f"H23 sealed one-shot path already exists: {path}")


def _build_h23_capability_authority():
    """Create the only mint/registry closure; expose no token or register helper."""

    registered_capabilities: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...]]
    ] = {}
    claimed_capabilities: dict[
        int, tuple[weakref.ReferenceType[object], tuple[object, ...], str]
    ] = {}

    def binding(
        value: AttestedH23SyntheticExecutionCapability,
    ) -> tuple[object, ...]:
        return (
            value.contract_sha256,
            value.capability_contract_sha256,
            value.executor_claim_transcript_contract_raw_sha256,
            value.fixture_manifest_sha256,
            value.resolved_test_manifest_sha256,
            value.approved_harness_git_blob,
            value.implementation_commit,
            value.authorization_activation_commit,
            value.authorization_activation_sha256,
            value.authorization_seal_sha256,
            value.capability_source_blob,
            value.runner_source_blob,
            tuple(sorted(value.runtime_identity.items())),
            value.repository_root,
            value.success_destination,
            value.terminal_record_destination,
            value.authorization_marker,
            value.transcript_path,
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
        """Issue only after a later OS-bound activation and seal pass preflight."""

        # This is intentionally first. In the present commit it fails before
        # plan resolution, package inspection, scientific path access, or claim.
        context = _load_h23_authorization_context(repository_root)
        seal = context.seal
        repository = Path(repository_root).resolve(strict=True)
        plan = load_h23_harness_plan(repository)
        _validate_repository_and_runtime(repository, seal, plan)
        success = _resolve_bound_path(repository, seal.success_destination)
        terminal = _resolve_bound_path(repository, seal.terminal_record_destination)
        marker = _resolve_bound_path(repository, seal.authorization_marker)
        transcript = _resolve_bound_path(repository, seal.transcript_path)
        for path in (success, terminal, marker, transcript):
            if path.exists():
                raise FileExistsError(f"H23 sealed one-shot path already exists: {path}")
        created = object.__new__(AttestedH23SyntheticExecutionCapability)
        values = {
            "contract_sha256": plan.contract_sha256,
            "capability_contract_sha256": H23_CAPABILITY_CONTRACT_SHA256,
            "executor_claim_transcript_contract_raw_sha256": (
                H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256
            ),
            "fixture_manifest_sha256": plan.fixture_manifest_sha256,
            "resolved_test_manifest_sha256": plan.resolved_test_manifest_sha256,
            "approved_harness_git_blob": H23_HARNESS_GIT_BLOB,
            "implementation_commit": seal.reviewed_execution_commit,
            "authorization_activation_commit": context.activation_commit,
            "authorization_activation_sha256": context.activation.raw_sha256,
            "authorization_seal_sha256": seal.raw_sha256,
            "capability_source_blob": seal.capability_source_blob,
            "runner_source_blob": seal.runner_source_blob,
            "runtime_identity": {
                "implementation": "CPython",
                "python_version": "3.11.9",
                "numpy_version": "1.26.4",
                "architecture": "arm64",
                "execution_device": "CPU",
                "thread_count": 1,
            },
            "repository_root": repository,
            "success_destination": success,
            "terminal_record_destination": terminal,
            "authorization_marker": marker,
            "transcript_path": transcript,
            "_sealed": True,
        }
        for name, value in values.items():
            object.__setattr__(created, name, value)
        identity = id(created)

        def cleanup(reference: weakref.ReferenceType[object]) -> None:
            registered = registered_capabilities.get(identity)
            if registered is not None and registered[0] is reference:
                registered_capabilities.pop(identity, None)
            claimed = claimed_capabilities.get(identity)
            if claimed is not None and claimed[0] is reference:
                claimed_capabilities.pop(identity, None)
        reference = weakref.ref(created, cleanup)
        registered_capabilities[identity] = (reference, binding(created))
        return created

    def claim(value: object) -> AttestedH23SyntheticExecutionCapability:
        checked = require(value)
        identity = id(checked)
        existing_claim = claimed_capabilities.get(identity)
        if existing_claim is not None and existing_claim[0]() is checked:
            raise FileExistsError("H23 capability was already claimed in this process.")
        if existing_claim is not None:
            claimed_capabilities.pop(identity, None)
        _revalidate_h23_claim_authority(checked)
        payload = _h23_marker_payload(checked)
        raw = _canonical_json_line(payload)
        _write_exclusive_durable_file(checked.authorization_marker, raw)
        marker_sha256 = _sha256(raw)
        reference = weakref.ref(checked)
        claimed_capabilities[identity] = (reference, binding(checked), marker_sha256)
        return checked

    def require_claimed(value: object) -> AttestedH23SyntheticExecutionCapability:
        checked = require(value)
        claimed = claimed_capabilities.get(id(checked))
        if (
            claimed is None
            or claimed[0]() is not checked
            or claimed[1] != binding(checked)
        ):
            raise PermissionError("H23 capability is not durably claimed in this process.")
        try:
            raw = checked.authorization_marker.read_bytes()
        except FileNotFoundError as exc:
            raise PermissionError("H23 claimed marker is missing.") from exc
        if _sha256(raw) != claimed[2] or raw != _canonical_json_line(_h23_marker_payload(checked)):
            raise PermissionError("H23 claimed marker bytes were modified.")
        return checked

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
    "H23AuthorizationActivation",
    "H23AuthorizationContext",
    "H23AuthorizationSeal",
    "H23_AUTHORIZATION_ACTIVATION_COMMIT_ENV",
    "H23_AUTHORIZATION_ACTIVATION_RELATIVE_PATH",
    "H23_AUTHORIZATION_SEAL_RELATIVE_PATH",
    "H23_CAPABILITY_CONTRACT_SHA256",
    "H23_CONSUMPTION_CLAIM_IMPLEMENTED",
    "H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256",
    "H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH",
    "claim_h23_synthetic_execution_capability",
    "issue_h23_synthetic_execution_capability",
    "load_h23_authorization_seal",
    "require_attested_h23_synthetic_execution_capability",
    "require_claimed_h23_synthetic_execution_capability",
    "validate_h23_authorization_seal_payload",
    "validate_h23_authorization_activation_payload",
]
