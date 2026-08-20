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
from typing import Any, Mapping


CONTRACT_RELATIVE = Path("configs/harmonic_censoring_h27_review5_scientific_execution_contract.json")
SUCCESS = "H27_REVIEW5_SCIENCE_27_OF_27_PASS_STOP_BEFORE_POST_SCIENCE"
INCONCLUSIVE = "H27_EXECUTION_INCONCLUSIVE"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git(root: Path, *args: str) -> str:
    return subprocess.check_output(("git", *args), cwd=root, text=True, encoding="utf-8").strip()


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
    if lifecycle not in {
        ("IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_REAL_EXECUTION", False, False, False),
        ("AUTHORIZED_REAL_SCIENCE_ONE_SHOT", True, True, True),
    }:
        raise ValueError("H27 Review-5 lifecycle mismatch")
    return value


def _preflight(root: Path, contract: Mapping[str, Any]) -> tuple[str, bytes]:
    if contract["real_execution_authorized"] is not True:
        raise PermissionError("H27 Review-5 real execution is not externally authorized")
    if platform.system() != "Darwin":
        raise RuntimeError("H27 Review-5 scientific execution requires macOS")
    if os.environ.get(str(contract["acknowledgement_environment"])) != contract["acknowledgement_value"]:
        raise PermissionError("H27 Review-5 acknowledgement missing")
    for key, value in contract["process_environment_exact"].items():
        if os.environ.get(str(key)) != str(value):
            raise PermissionError(f"H27 Review-5 environment mismatch: {key}")
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
    output = Path(str(contract["scientific_output_root"]))
    if output.exists():
        raise FileExistsError("H27 Review-5 one-shot output already exists; retry forbidden")
    if output.parent.is_symlink():
        raise ValueError("H27 Review-5 output parent symlink forbidden")
    output.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    return head, index_raw


def _claim(contract: Mapping[str, Any], head: str, index_raw: bytes) -> dict[str, object]:
    return {
        "schema_identity": "H27_REVIEW5_SCIENTIFIC_CLAIM_V1",
        "schema_version": 1,
        "authorization_commit": head,
        "scientific_target_commit": contract["scientific_target_commit"],
        "review4_terminal_commit": contract["review4_terminal_commit"],
        "population_index_sha256": _sha(index_raw),
        "test_ids": contract["test_ids"],
        "single_use": True,
        "retry_allowed": False,
        "locked_test_used": False,
        "training_used": False,
    }


def main() -> int:
    root = _repo_root()
    contract = _load_contract(root)
    head, index_raw = _preflight(root, contract)
    output = Path(str(contract["scientific_output_root"]))
    output.mkdir(mode=0o700)
    claim_raw, claim_sha = _atomic_publish(output / "claim.json", _claim(contract, head, index_raw))
    terminal_status = INCONCLUSIVE
    try:
        from src.polyphonic.harmonic_censoring_h27_contract import load_h27_dormant_plan
        from src.polyphonic.harmonic_censoring_h27_scientific_authority import issue_h27_scientific_capability
        from src.polyphonic.harmonic_censoring_h27_sealed_population_loader import load_h27_sealed_population_bindings
        from src.polyphonic.harmonic_censoring_h27_test_executor import (
            execute_h27_scientific_sequence, scientific_sequence_as_dict,
        )
        capability = issue_h27_scientific_capability(
            claim_raw=claim_raw, claim_sha256=claim_sha,
            population_index_sha256=str(contract["population_index_sha256"]),
            execution_authorized=True,
        )
        plan = load_h27_dormant_plan(root)
        bindings = load_h27_sealed_population_bindings(
            capability=capability, plan=plan, population_root=Path(str(contract["population_root"])),
            expected_index_sha256=str(contract["population_index_sha256"]),
        )
        import numpy as np
        result = execute_h27_scientific_sequence(
            np=np, capability=capability, repository_root=root, plan=plan, bindings=bindings,
        )
        report = scientific_sequence_as_dict(result)
        report.update({
            "schema_identity": "H27_REVIEW5_SCIENTIFIC_REPORT_V1",
            "schema_version": 1,
            "claim_sha256": claim_sha,
            "population_index_sha256": contract["population_index_sha256"],
            "locked_test_used": False,
            "training_used": False,
            "calibration_used": False,
            "checkpoint_selected": False,
        })
        report_raw, report_sha = _atomic_publish(output / "scientific_report.json", report)
        del report_raw
        terminal_status = result.terminal_status
        _atomic_publish(output / "terminal.json", {
            "schema_identity": "H27_REVIEW5_SCIENTIFIC_TERMINAL_V1",
            "schema_version": 1,
            "status": terminal_status,
            "claim_sha256": claim_sha,
            "scientific_report_sha256": report_sha,
            "locked_test_used": False,
            "training_used": False,
            "retry_allowed": False,
        })
    except BaseException as exc:
        _atomic_publish(output / "terminal.json", {
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
        raise
    print(terminal_status)
    return 0 if terminal_status == SUCCESS else 2


if __name__ == "__main__":
    raise SystemExit(main())
