#!/usr/bin/env python3
"""H27 Review-5 one-shot scientific entrypoint (dormant until contract activation)."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import uuid
from typing import Any, Mapping


CONTRACT_RELATIVE = Path("configs/harmonic_censoring_h27_review5_scientific_execution_contract.json")
SUCCESS = "H27_REVIEW5_SCIENCE_27_OF_27_PASS_STOP_BEFORE_POST_SCIENCE"
INCONCLUSIVE = "H27_EXECUTION_INCONCLUSIVE"
ACTIVATION_ENVIRONMENT = "H27_REVIEW5_ACTIVATION_PATH"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=root, text=True, encoding="utf-8").strip()


def _git_bytes(root: Path, *args: str) -> bytes:
    return subprocess.check_output(("git", *args), cwd=root)


def _git_blob_sha1(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n"


def _strict_json(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H27 {label} must be UTF-8 LF without BOM")
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value in items:
            if key in result:
                raise ValueError(f"H27 duplicate JSON key in {label}: {key}")
            result[key] = value
        return result
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs,
                       parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))
    if type(value) is not dict:
        raise ValueError(f"H27 {label} must be an object")
    return value


def _atomic_publish(path: Path, value: object) -> tuple[bytes, str]:
    raw = _canonical(value)
    temporary = path.with_name(f".{path.name}.part")
    if path.exists() or temporary.exists():
        raise FileExistsError(f"H27 output slot already exists: {path}")
    descriptor = os.open(
        temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600
    )
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temporary, path, follow_symlinks=False)
        temporary.unlink()
        if os.name == "posix":
            directory = os.open(
                path.parent, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise
    return raw, _sha(raw)


def _fsync_directory(path: Path) -> None:
    if os.name == "posix":
        descriptor = os.open(path, os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) |
                             getattr(os, "O_NOFOLLOW", 0))
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def _prepare_empty_output(path: Path) -> None:
    """Bootstrap before consumption; an exactly empty directory is retry-neutral."""

    path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    _fsync_directory(path.parent)
    if path.exists():
        if path.is_symlink() or not path.is_dir() or any(path.iterdir()):
            raise FileExistsError("H27 Review-5 consumed or non-empty output exists; retry forbidden")
        return
    path.mkdir(mode=0o700)
    _fsync_directory(path.parent)


def _load_activation(root: Path, contract: Mapping[str, Any], head: str,
                     index_raw: bytes) -> tuple[Mapping[str, object], str]:
    """Verify the distinct Review-5B activation before the irreversible claim."""

    supplied = os.environ.get(ACTIVATION_ENVIRONMENT)
    if not supplied:
        raise PermissionError("H27 Review-5 activation path missing")
    path = Path(supplied)
    if not path.is_absolute() or path.is_symlink() or path.resolve(strict=True) != path:
        raise PermissionError("H27 Review-5 activation must be an exact regular path")
    raw = path.read_bytes()
    activation_sha = _sha(raw)
    value = _strict_json(raw, "Review-5 activation")
    expected_keys = (
        "schema_identity", "schema_version", "status", "execution_id", "activation_nonce",
        "issuer", "implementation_commit", "identity_binding_commit", "external_seal_commit",
        "identity_binding_sha256", "external_seal_sha256", "population_index_sha256",
        "primary_runtime", "secondary_runtime", "single_use", "retry_allowed",
        "locked_test_authorized", "training_authorized",
    )
    if tuple(value) != expected_keys:
        raise ValueError("H27 Review-5 activation schema/order mismatch")
    fixed = {
        "schema_identity": "H27_REVIEW5_SCIENTIFIC_ACTIVATION_V1",
        "schema_version": 1,
        "status": "AUTHORIZED_REAL_SCIENCE_ONE_SHOT",
        "issuer": "h27-execution-codex-mac-primary",
        "population_index_sha256": _sha(index_raw),
        "primary_runtime": str(contract["runtime_python"]),
        "secondary_runtime": str(contract["secondary_runtime_python"]),
        "single_use": True, "retry_allowed": False,
        "locked_test_authorized": False, "training_authorized": False,
    }
    for key, expected in fixed.items():
        if value.get(key) != expected or type(value.get(key)) is not type(expected):
            raise ValueError(f"H27 Review-5 activation mismatch: {key}")
    try:
        uuid.UUID(str(value["execution_id"])); uuid.UUID(str(value["activation_nonce"]))
    except ValueError as exc:
        raise ValueError("H27 Review-5 activation identifiers invalid") from exc
    commits = tuple(str(value[key]) for key in (
        "implementation_commit", "identity_binding_commit", "external_seal_commit"))
    if any(len(item) != 40 or any(c not in "0123456789abcdef" for c in item) for item in commits):
        raise ValueError("H27 Review-5 activation commit invalid")
    if head != commits[2]:
        raise PermissionError(
            "H27 Review-5 execution HEAD must equal reviewed external seal commit"
        )
    if any(subprocess.run(("git", "merge-base", "--is-ancestor", left, right), cwd=root).returncode
           for left, right in zip(commits, commits[1:] + (head,))):
        raise PermissionError("H27 Review-5 activation commit chain invalid")
    binding_relative = "configs/harmonic_censoring_h27_review5_scientific_execution_identity_binding.json"
    seal_relative = "configs/harmonic_censoring_h27_review5_scientific_execution_external_seal.json"
    binding = root / binding_relative
    seal = root / seal_relative
    binding_raw, seal_raw = binding.read_bytes(), seal.read_bytes()
    committed_binding_raw = _git_bytes(root, "show", f"{commits[1]}:{binding_relative}")
    committed_seal_raw = _git_bytes(root, "show", f"{commits[2]}:{seal_relative}")
    if binding_raw != committed_binding_raw or seal_raw != committed_seal_raw:
        raise PermissionError("H27 Review-5 activation reviewed artifact bytes changed")
    if (_sha(binding_raw) != value["identity_binding_sha256"] or
            _sha(seal_raw) != value["external_seal_sha256"]):
        raise PermissionError("H27 Review-5 activation reviewed artifact mismatch")
    binding_value = _strict_json(binding_raw, "Review-5 identity binding")
    seal_value = _strict_json(seal_raw, "Review-5 external seal")
    sealed_binding = seal_value.get("identity_binding")
    if type(sealed_binding) is not dict:
        raise PermissionError("H27 Review-5 external seal binding identity missing")
    expected_binding_identity = {
        "path": binding_relative,
        "git_blob_sha1": _git_blob_sha1(committed_binding_raw),
        "size_bytes": len(committed_binding_raw),
        "sha256": _sha(committed_binding_raw),
    }
    if sealed_binding != expected_binding_identity:
        raise PermissionError("H27 Review-5 external seal binding identity mismatch")
    if (binding_value.get("implementation_commit") != commits[0]
            or seal_value.get("implementation_commit") != commits[0]
            or seal_value.get("identity_binding_commit") != commits[1]
            or seal_value.get("population_index_sha256") != _sha(index_raw)):
        raise PermissionError("H27 Review-5 activation transitive binding mismatch")
    seal_introduction = _git(root, "log", "-1", "--format=%H", "--", seal.relative_to(root).as_posix())
    if seal_introduction != commits[2]:
        raise PermissionError("H27 Review-5 activation external seal commit mismatch")
    return value, activation_sha


def _load_contract(root: Path) -> Mapping[str, Any]:
    value = _strict_json((root / CONTRACT_RELATIVE).read_bytes(), "Review-5 contract")
    expected_tests = [
        f"H27-T-{phase}-{index:03d}"
        for phase in ("P0", "P1", "P2") for index in range(1, 10)
    ]
    required = {
        "schema_identity": "H27_REVIEW5_SCIENTIFIC_EXECUTION_V1",
        "schema_version": 1,
        "review4_terminal_commit": "2b54bc624314a8ac56380ac826c8fe14ee09d3db",
        "scientific_target_commit": "46a6bdf81a56a7a7a10524d4e55092301a452207",
        "population_root": "/Users/amcarene/h27-admin-recovery-v2/population/h27-synthetic-v1",
        "population_index_sha256": "ae67455b07cde223b77c6d1da221cbba2252c6b67fa8c07b9d3ebfbd50f3a9f8",
        "review4_terminal_sha256": "122a87f9dfe83a342099fc7a9a7508c47b5bda5abb8fa73da42ea29adb31a636",
        "review4_terminal_path": "/Users/amcarene/h27-admin-recovery-v2/terminal/h27-materialization-recovery-v2.json",
        "scientific_output_root": "/Users/amcarene/h27-admin-recovery-v2/science/review5-v1",
        "runtime_python": "/Users/amcarene/midi-worker/.venv/bin/python",
        "secondary_runtime_python": "/Users/amcarene/midi-worker/.venv-py39/bin/python",
        "acknowledgement_environment": "H27_REVIEW5_SCIENTIFIC_EXECUTE",
        "acknowledgement_value": "1",
        "process_environment_exact": {"MIDI_FORCE_CPU":"1","OMP_NUM_THREADS":"1","OPENBLAS_NUM_THREADS":"1","MKL_NUM_THREADS":"1","NUMEXPR_NUM_THREADS":"1","VECLIB_MAXIMUM_THREADS":"1","PYTHONHASHSEED":"0","LC_ALL":"C","LANG":"C","TZ":"UTC"},
        "test_ids": expected_tests,
        "phase_counts": {"P0":9,"P1":9,"P2":9},
        "authority_maximum": 1,
        "claim_maximum": 1,
        "single_use": True,
        "retry_allowed": False,
        "stop_after_first_failed_test": True,
        "terminal_statuses": {
            "success": SUCCESS,
            "p0_failure": "H27_PREREGISTRATION_OR_IDENTIFIABILITY_INVALID",
            "p1_failure": "H27_CERTIFICATE_HYPOTHESIS_NOT_DEMONSTRATED",
            "p2_failure": "H27_ROBUSTNESS_NOT_DEMONSTRATED",
            "operational_failure_after_claim": INCONCLUSIVE,
        },
        "locked_test_authorized": False,
        "training_authorized": False,
        "calibration_authorized": False,
        "checkpoint_selection_authorized": False,
    }
    for key, expected in required.items():
        if value.get(key) != expected or type(value.get(key)) is not type(expected):
            raise ValueError(f"H27 Review-5 contract mismatch: {key}")
    lifecycle = (value.get("status"), value.get("real_execution_authorized"),
                 value.get("scientific_authority_creation_authorized"),
                 value.get("scientific_claim_creation_authorized"))
    if lifecycle != ("IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_REAL_EXECUTION", False, False, False):
        raise ValueError("H27 Review-5 lifecycle mismatch")
    return value


def _preflight(root: Path, contract: Mapping[str, Any]) -> tuple[str, bytes, Mapping[str, object], str]:
    if platform.system() != "Darwin":
        raise RuntimeError("H27 Review-5 scientific execution requires macOS")
    if Path(sys.executable).resolve(strict=True) != Path(str(contract["runtime_python"])).resolve(strict=True):
        raise PermissionError("H27 Review-5 Python runtime mismatch")
    if _git(root, "status", "--porcelain=v1"):
        raise PermissionError("H27 Review-5 requires a clean worktree")
    head = _git(root, "rev-parse", "HEAD")
    target = str(contract["scientific_target_commit"])
    if subprocess.run(("git", "merge-base", "--is-ancestor", target, head), cwd=root).returncode:
        raise PermissionError("H27 scientific target is not an ancestor of HEAD")
    bindings = contract["source_bindings"]
    if type(bindings) is not dict:
        raise ValueError("H27 source bindings invalid")
    for relative, binding in bindings.items():
        if type(relative) is not str or type(binding) is not dict:
            raise ValueError("H27 source binding schema invalid")
        raw = (root / relative).read_bytes()
        if (len(raw) != binding.get("size_bytes") or _sha(raw) != binding.get("sha256")
                or _git(root, "rev-parse", f"HEAD:{relative}") != binding.get("git_blob_sha1")):
            raise ValueError(f"H27 source binding mismatch: {relative}")
    review4_terminal = Path(str(contract["review4_terminal_path"]))
    if _sha(review4_terminal.read_bytes()) != contract["review4_terminal_sha256"]:
        raise ValueError("H27 Review-4 terminal SHA mismatch")
    population_root = Path(str(contract["population_root"]))
    if population_root.is_symlink() or population_root.absolute() != population_root.resolve(strict=True):
        raise ValueError("H27 population root must be a real directory")
    index_raw = (population_root / "population_index.json").read_bytes()
    if _sha(index_raw) != contract["population_index_sha256"]:
        raise ValueError("H27 population index SHA mismatch")
    activation, activation_sha = _load_activation(root, contract, head, index_raw)
    # The immutable dormant contract must remain false.  Only the separately
    # reviewed, byte-bound activation above authorizes this one execution.
    if os.environ.get(str(contract["acknowledgement_environment"])) != contract["acknowledgement_value"]:
        raise PermissionError("H27 Review-5 acknowledgement missing")
    for key, value in contract["process_environment_exact"].items():
        if os.environ.get(str(key)) != str(value):
            raise PermissionError(f"H27 Review-5 environment mismatch: {key}")
    output = Path(str(contract["scientific_output_root"]))
    if output.parent.is_symlink():
        raise ValueError("H27 Review-5 output parent symlink forbidden")
    _prepare_empty_output(output)
    return head, index_raw, activation, activation_sha


def _claim(contract: Mapping[str, Any], head: str, index_raw: bytes,
           activation: Mapping[str, object], activation_sha: str) -> dict[str, object]:
    return {
        "schema_identity": "H27_REVIEW5_SCIENTIFIC_CLAIM_V1",
        "schema_version": 1,
        "authorization_commit": head,
        "execution_id": activation["execution_id"],
        "activation_nonce": activation["activation_nonce"],
        "activation_sha256": activation_sha,
        "scientific_target_commit": contract["scientific_target_commit"],
        "review4_terminal_commit": contract["review4_terminal_commit"],
        "population_index_sha256": _sha(index_raw),
        "test_ids": contract["test_ids"],
        "single_use": True,
        "retry_allowed": False,
        "locked_test_used": False,
        "training_used": False,
    }


class _ReceiptPublisher:
    """Durable ordered SHA chain for the 27 preregistered test completions."""

    def __init__(self, *, output: Path, claim_sha256: str, activation_sha256: str,
                 population_index_sha256: str) -> None:
        self.output = output
        self.claim_sha256 = claim_sha256
        self.activation_sha256 = activation_sha256
        self.population_index_sha256 = population_index_sha256
        self.previous_sha256 = claim_sha256
        self.completed = 0

    def __call__(self, test_result: object) -> None:
        test_id = str(getattr(test_result, "test_id"))
        phase = str(getattr(test_result, "phase"))
        ordinal = int(test_id.rsplit("-", 1)[1]) + {"P0": 0, "P1": 9, "P2": 18}[phase]
        if ordinal != self.completed + 1:
            raise RuntimeError("H27 test receipt order is not contiguous")
        evidence = _canonical({
            "record_count": getattr(test_result, "record_count"),
            "record_identities": getattr(test_result, "record_identities"),
            "detail": getattr(test_result, "detail"),
        })
        _, digest = _atomic_publish(self.output / f"{ordinal:03d}-{test_id}.json", {
            "schema_identity": "H27_REVIEW5_TEST_RECEIPT_V1", "schema_version": 1,
            "order": ordinal, "test_id": test_id, "phase": phase,
            "status": str(getattr(test_result, "status")), "evidence_sha256": _sha(evidence),
            "population_index_sha256": self.population_index_sha256,
            "activation_sha256": self.activation_sha256, "claim_sha256": self.claim_sha256,
            "previous_receipt_sha256": self.previous_sha256,
        })
        self.previous_sha256 = digest
        self.completed = ordinal


def main() -> int:
    root = _repo_root()
    contract = _load_contract(root)
    head, index_raw, activation, activation_sha = _preflight(root, contract)
    output = Path(str(contract["scientific_output_root"]))
    claim_value = _claim(contract, head, index_raw, activation, activation_sha)
    claim_raw, claim_sha = _atomic_publish(output / "claim.json", claim_value)
    terminal_status = INCONCLUSIVE
    try:
        from src.polyphonic.harmonic_censoring_h27_contract import load_h27_dormant_plan
        from src.polyphonic.harmonic_censoring_h27_scientific_authority import (
            issue_h27_scientific_capability, verify_durable_h27_claim,
        )
        from src.polyphonic.harmonic_censoring_h27_sealed_population_loader import load_h27_sealed_population_bindings
        from src.polyphonic.harmonic_censoring_h27_test_executor import (
            execute_h27_scientific_sequence, scientific_sequence_as_dict,
        )
        proof = verify_durable_h27_claim(
            claim_path=output / "claim.json", expected_claim=claim_value,
            expected_claim_sha256=claim_sha,
            expected_activation_sha256=activation_sha,
            expected_execution_id=str(activation["execution_id"]),
            expected_activation_nonce=str(activation["activation_nonce"]),
        )
        capability = issue_h27_scientific_capability(durable_claim=proof)
        plan = load_h27_dormant_plan(root)
        bindings = load_h27_sealed_population_bindings(
            capability=capability, plan=plan, population_root=Path(str(contract["population_root"])),
            expected_index_sha256=str(contract["population_index_sha256"]),
        )
        import numpy as np
        receipt_publisher = _ReceiptPublisher(
            output=output, claim_sha256=claim_sha, activation_sha256=activation_sha,
            population_index_sha256=str(contract["population_index_sha256"]),
        )
        result = execute_h27_scientific_sequence(
            np=np, capability=capability, repository_root=root, plan=plan, bindings=bindings,
            on_test_completed=receipt_publisher,
        )
        report = scientific_sequence_as_dict(result)
        report.update({
            "schema_identity": "H27_REVIEW5_SCIENTIFIC_REPORT_V1",
            "schema_version": 1,
            "claim_sha256": claim_sha,
            "activation_sha256": activation_sha,
            "last_test_receipt_sha256": receipt_publisher.previous_sha256,
            "population_index_sha256": contract["population_index_sha256"],
            "locked_test_used": False,
            "training_used": False,
            "calibration_used": False,
            "checkpoint_selected": False,
        })
        report_raw, report_sha = _atomic_publish(output / "scientific_report.json", report)
        del report_raw
        terminal_status = result.terminal_status
        _, terminal_sha = _atomic_publish(output / "terminal.json", {
            "schema_identity": "H27_REVIEW5_SCIENTIFIC_TERMINAL_V1",
            "schema_version": 1,
            "status": terminal_status,
            "claim_sha256": claim_sha,
            "scientific_report_sha256": report_sha,
            "locked_test_used": False,
            "training_used": False,
            "retry_allowed": False,
        })
        _atomic_publish(output / "COMPLETE.json", {
            "schema_identity": "H27_REVIEW5_COMPLETION_MARKER_V1", "schema_version": 1,
            "terminal_sha256": terminal_sha, "claim_sha256": claim_sha,
            "last_test_receipt_sha256": receipt_publisher.previous_sha256,
        })
    except BaseException as exc:
        if (output / "terminal.json").exists():
            # Terminal data without its independently published marker remains
            # deliberately inconclusive and must never be overwritten.
            raise
        _, terminal_sha = _atomic_publish(output / "terminal.json", {
            "schema_identity": "H27_REVIEW5_SCIENTIFIC_TERMINAL_V1",
            "schema_version": 1,
            "status": INCONCLUSIVE,
            "claim_sha256": claim_sha,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "locked_test_used": False,
            "training_used": False,
            "retry_allowed": False,
        })
        _atomic_publish(output / "COMPLETE.json", {
            "schema_identity": "H27_REVIEW5_COMPLETION_MARKER_V1", "schema_version": 1,
            "terminal_sha256": terminal_sha, "claim_sha256": claim_sha,
            "status": INCONCLUSIVE,
        })
        raise
    print(terminal_status)
    return 0 if terminal_status == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main())
