from __future__ import annotations

import hashlib
import json
import os
import re
import sys
from pathlib import Path
from typing import Optional, Sequence

from src.polyphonic.harmonic_censoring_h25_lifecycle_qualification import (
    H25_ADMIN_FAILURE,
    H25_ADMIN_FORENSIC_INCONCLUSIVE,
    H25_ADMIN_INCONCLUSIVE,
    H25_ADMIN_PRECLAIM_ABORTED,
    H25_ADMIN_SUCCESS,
    H25_REAL_OS_PROBES,
    H25AdministrativeQualificationScenario,
    H25RealOSQualificationProbe,
    recompute_h25_administrative_lifecycle_result,
    recompute_h25_real_os_lifecycle_probe_result,
    run_h25_preclaim_administrative_lifecycle_qualification,
    run_h25_real_os_lifecycle_qualification_probe,
)


EXPECTED_CONTRACT_SHA256 = (
    "a50189acc47c1999935212e8549403992a663dee316fa3e88812eca159043fd4"
)
EXECUTE_ENV = "H25_ADMIN_LIFECYCLE_QUALIFICATION_EXECUTE"
EXPECTED_COMMIT_ENV = "H25_ADMIN_LIFECYCLE_QUALIFICATION_EXPECTED_COMMIT"
OUTPUT_RELATIVE = Path("tmp/local/h25_preclaim_admin_lifecycle_qualification_20260811")
RECORD_NAME = "qualification_record.json"

ADMIN_CASES = (
    ("admin-logical", "LOGICAL_FAILURE_AT_P1", H25_ADMIN_FAILURE),
    ("admin-operational", "OPERATIONAL_ERROR_AT_P1", H25_ADMIN_INCONCLUSIVE),
    ("admin-evidence", "EVIDENCE_WRITE_FAIL", H25_ADMIN_INCONCLUSIVE),
    (
        "admin-transcript-publish",
        "TRANSCRIPT_PUBLISH_FAIL",
        H25_ADMIN_FORENSIC_INCONCLUSIVE,
    ),
    (
        "admin-terminal-publish",
        "TERMINAL_PUBLISH_FAIL",
        H25_ADMIN_FORENSIC_INCONCLUSIVE,
    ),
    (
        "admin-success-rename",
        "SUCCESS_RENAME_FAIL",
        H25_ADMIN_FORENSIC_INCONCLUSIVE,
    ),
)

EXPECTED_OS_STATUS = {
    "REAL_NOMINAL": H25_ADMIN_SUCCESS,
    "REAL_EOF_BEFORE_SURROGATE_CLAIM": H25_ADMIN_PRECLAIM_ABORTED,
    "REAL_EOF_AFTER_SURROGATE_CLAIM": H25_ADMIN_INCONCLUSIVE,
    "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM": H25_ADMIN_INCONCLUSIVE,
    "REAL_SIGINT_AFTER_SURROGATE_CLAIM": H25_ADMIN_INCONCLUSIVE,
    "REAL_TIMEOUT_PREFLIGHT": H25_ADMIN_PRECLAIM_ABORTED,
    "REAL_TIMEOUT_SURROGATE_CLAIM": H25_ADMIN_PRECLAIM_ABORTED,
    "REAL_TIMEOUT_P0": H25_ADMIN_INCONCLUSIVE,
    "REAL_TIMEOUT_P1": H25_ADMIN_INCONCLUSIVE,
    "REAL_TIMEOUT_P2": H25_ADMIN_INCONCLUSIVE,
    "REAL_TIMEOUT_SUCCESS_CLOSURE": H25_ADMIN_INCONCLUSIVE,
    "REAL_TIMEOUT_FAILURE_CLOSURE": H25_ADMIN_FORENSIC_INCONCLUSIVE,
    "REAL_TIMEOUT_INCONCLUSIVE_CLOSURE": H25_ADMIN_FORENSIC_INCONCLUSIVE,
}


def canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def parse_canonical(raw: bytes) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError("qualification JSON encoding is not canonical")
    value = json.loads(raw.decode("utf-8"))
    if type(value) is not dict or canonical(value) != raw:
        raise ValueError("qualification JSON is not canonical")
    return value


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    try:
        view = memoryview(raw)
        while view:
            written = os.write(descriptor, view)
            if written <= 0:
                raise OSError("qualification write made no progress")
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def atomic_write_new(path: Path, raw: bytes) -> None:
    part = path.with_name(path.name + ".part")
    write_new(part, raw)
    os.replace(part, path)
    directory = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(directory)
    finally:
        os.close(directory)


def git(repository: Path, *arguments: str) -> str:
    import subprocess

    return subprocess.check_output(
        ["git", *arguments], cwd=repository, text=True
    ).strip()


def file_bindings(output: Path) -> list[dict[str, object]]:
    bindings: list[dict[str, object]] = []
    for path in sorted(output.rglob("*")):
        if not path.is_file() or path.name == RECORD_NAME:
            continue
        raw = path.read_bytes()
        bindings.append(
            {
                "path": path.relative_to(output).as_posix(),
                "raw_sha256": sha(raw),
                "size_bytes": len(raw),
            }
        )
    return bindings


def verify_record(
    repository: Path,
    output: Path,
    record_path: Path,
    *,
    expected_commit: str,
) -> None:
    raw = record_path.read_bytes()
    record = parse_canonical(raw)
    expected_keys = {
        "administrative_case_count",
        "all_results_recomputed",
        "commit",
        "contract_sha256",
        "driver_sha256",
        "file_bindings",
        "H17_population_used",
        "locked_test_used",
        "model_or_checkpoint_used",
        "os_probe_count",
        "purpose",
        "real_data_used",
        "results",
        "schema_version",
        "scientific_capability_or_claim_used",
        "scientific_population_used",
        "status",
        "surrogate_claim_consumed_count",
        "surrogate_claim_not_created_count",
        "training_used",
        "worker_alive_count",
    }
    if set(record) != expected_keys:
        raise ValueError("qualification record key set mismatch")
    if (
        record["commit"] != expected_commit
        or record["contract_sha256"] != EXPECTED_CONTRACT_SHA256
        or record["os_probe_count"] != 13
        or record["administrative_case_count"] != 6
        or record["worker_alive_count"] != 0
        or record["surrogate_claim_consumed_count"] != 16
        or record["surrogate_claim_not_created_count"] != 3
        or record["status"] != "H25_ADMIN_LIFECYCLE_QUALIFICATION_PASSED"
        or record["all_results_recomputed"] is not True
    ):
        raise ValueError("qualification record summary mismatch")
    for flag in (
        "H17_population_used",
        "locked_test_used",
        "model_or_checkpoint_used",
        "real_data_used",
        "scientific_capability_or_claim_used",
        "scientific_population_used",
        "training_used",
    ):
        if record[flag] is not False:
            raise ValueError(f"qualification crossed forbidden boundary: {flag}")

    if record["file_bindings"] != file_bindings(output):
        raise ValueError("qualification file bindings changed")
    expected_actual = {
        item["path"] for item in record["file_bindings"]
    } | {RECORD_NAME}
    actual = {
        path.relative_to(output).as_posix()
        for path in output.rglob("*")
        if path.is_file()
    }
    if actual != expected_actual:
        raise ValueError("qualification output file set mismatch")

    results = record["results"]
    if type(results) is not list or len(results) != 19:
        raise ValueError("qualification result count mismatch")
    for item in results:
        if item["kind"] == "real_os":
            receipt = output / item["controller_receipt_path"]
            recomputed = recompute_h25_real_os_lifecycle_probe_result(receipt)
            if (
                recomputed["probe"] != item["probe"]
                or recomputed["result_status"] != item["status"]
                or recomputed["child_process_alive"] is not False
            ):
                raise ValueError("real-OS recomputation mismatch")
        elif item["kind"] == "administrative":
            recomputed = recompute_h25_administrative_lifecycle_result(
                output / item["root"]
            )
            if recomputed["status"] != item["status"]:
                raise ValueError("administrative recomputation mismatch")
        else:
            raise ValueError("qualification result kind is unknown")
    if git(repository, "rev-parse", "HEAD") != expected_commit:
        raise ValueError("qualification repository commit changed")
    if git(repository, "status", "--porcelain"):
        raise ValueError("qualification repository worktree changed")


def main() -> int:
    if os.environ.get(EXECUTE_ENV) != "1":
        raise PermissionError(
            f"qualification requires the literal acknowledgement {EXECUTE_ENV}=1"
        )
    expected_commit = os.environ.get(EXPECTED_COMMIT_ENV, "")
    if re.fullmatch(r"[0-9a-f]{40}", expected_commit) is None:
        raise PermissionError(
            f"qualification requires a full lowercase SHA in {EXPECTED_COMMIT_ENV}"
        )
    repository = Path.cwd().resolve(strict=True)
    if git(repository, "rev-parse", "HEAD") != expected_commit:
        raise PermissionError("qualification requires the exact reviewed commit")
    if git(repository, "status", "--porcelain"):
        raise PermissionError("qualification requires a clean worktree")
    contract = repository / "configs/harmonic_censoring_h25_successor_decision_contract.json"
    if sha(contract.read_bytes()) != EXPECTED_CONTRACT_SHA256:
        raise ValueError("qualification contract SHA mismatch")

    output = repository / OUTPUT_RELATIVE
    if output.exists():
        raise FileExistsError("qualification output already exists")
    output.mkdir(parents=True)
    driver_raw = Path(__file__).read_bytes()
    write_new(output / "qualification_driver.py", driver_raw)

    results: list[dict[str, object]] = []
    claim_consumed = 0
    claim_not_created = 0

    for index, probe_name in enumerate(H25_REAL_OS_PROBES):
        probe_id = f"os-{index:02d}"
        result = run_h25_real_os_lifecycle_qualification_probe(
            output,
            H25RealOSQualificationProbe(
                probe_id=probe_id,
                probe=probe_name,
                timeout_seconds=0.15,
                process_deadline_seconds=15.0,
            ),
        )
        if result.status != EXPECTED_OS_STATUS[probe_name]:
            raise ValueError(f"unexpected OS probe status: {probe_name}")
        recomputed = recompute_h25_real_os_lifecycle_probe_result(
            result.controller_receipt_path
        )
        root_recomputed = recompute_h25_administrative_lifecycle_result(result.root)
        consumed = bool(root_recomputed["surrogate_claim_consumed"])
        claim_consumed += int(consumed)
        claim_not_created += int(not consumed)
        results.append(
            {
                "child_exit_code": result.child_exit_code,
                "child_process_alive": result.child_process_alive,
                "controller_receipt_path": result.controller_receipt_path.relative_to(
                    output
                ).as_posix(),
                "kind": "real_os",
                "probe": probe_name,
                "probe_id": probe_id,
                "root": result.root.relative_to(output).as_posix(),
                "status": recomputed["result_status"],
                "surrogate_claim_consumed": consumed,
            }
        )

    for case_id, fault, expected_status in ADMIN_CASES:
        root = output / f"h25-admin-{case_id}"
        result = run_h25_preclaim_administrative_lifecycle_qualification(
            root,
            H25AdministrativeQualificationScenario(
                scenario_id=case_id,
                fault=fault,
            ),
        )
        recomputed = recompute_h25_administrative_lifecycle_result(root)
        if result.status != expected_status or recomputed["status"] != expected_status:
            raise ValueError(f"unexpected administrative status: {fault}")
        consumed = bool(recomputed["surrogate_claim_consumed"])
        if not consumed:
            raise ValueError("postclaim administrative case did not preserve its claim")
        claim_consumed += 1
        results.append(
            {
                "fault": fault,
                "kind": "administrative",
                "root": root.relative_to(output).as_posix(),
                "scenario_id": case_id,
                "status": recomputed["status"],
                "surrogate_claim_consumed": True,
            }
        )

    if (claim_consumed, claim_not_created, len(results)) != (16, 3, 19):
        raise ValueError("qualification attrition counters mismatch")
    if any(
        item.get("child_process_alive") is not False
        for item in results
        if item["kind"] == "real_os"
    ):
        raise RuntimeError("qualification retained a live worker")

    record = {
        "administrative_case_count": 6,
        "all_results_recomputed": True,
        "commit": expected_commit,
        "contract_sha256": EXPECTED_CONTRACT_SHA256,
        "driver_sha256": sha(driver_raw),
        "file_bindings": file_bindings(output),
        "H17_population_used": False,
        "locked_test_used": False,
        "model_or_checkpoint_used": False,
        "os_probe_count": 13,
        "purpose": "h25_preclaim_administrative_lifecycle_qualification_record",
        "real_data_used": False,
        "results": results,
        "schema_version": 1,
        "scientific_capability_or_claim_used": False,
        "scientific_population_used": False,
        "status": "H25_ADMIN_LIFECYCLE_QUALIFICATION_PASSED",
        "surrogate_claim_consumed_count": claim_consumed,
        "surrogate_claim_not_created_count": claim_not_created,
        "training_used": False,
        "worker_alive_count": 0,
    }
    record_path = output / RECORD_NAME
    atomic_write_new(record_path, canonical(record))
    verify_record(
        repository,
        output,
        record_path,
        expected_commit=expected_commit,
    )
    print(
        json.dumps(
            {
                "file_count": len(record["file_bindings"]) + 1,
                "output": str(output),
                "record_sha256": sha(record_path.read_bytes()),
                "status": record["status"],
                "surrogate_claim_consumed_count": claim_consumed,
                "surrogate_claim_not_created_count": claim_not_created,
                "worker_alive_count": 0,
            },
            sort_keys=True,
        )
    )
    return 0


def cli(argv: Optional[Sequence[str]] = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if arguments == ["--entrypoint-check"]:
        if os.environ.get(EXECUTE_ENV) is not None:
            raise PermissionError(
                "entrypoint check refuses an execution acknowledgement"
            )
        print(
            json.dumps(
                {
                    "entrypoint": (
                        "src.polyphonic."
                        "run_h25_preclaim_admin_lifecycle_qualification"
                    ),
                    "qualification_executed": False,
                    "status": "H25_ADMIN_QUALIFICATION_ENTRYPOINT_READY",
                },
                sort_keys=True,
            )
        )
        return 0
    if arguments:
        raise SystemExit(
            "H25 qualification entrypoint accepts no arguments; "
            "use --entrypoint-check only for the zero-execution import check."
        )
    return main()


if __name__ == "__main__":
    raise SystemExit(cli())
