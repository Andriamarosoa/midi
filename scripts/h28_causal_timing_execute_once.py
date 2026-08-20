#!/usr/bin/env python3
"""Externally activated one-shot runner for the six-record H28 timing study.

Without an exact ignored activation file and acknowledgement environment this
script stops before NumPy, claim creation, payload rendering, or science.
"""
from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
import ctypes
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import time
from types import MappingProxyType
from typing import Iterator, Mapping


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
if str(REPOSITORY_ROOT) not in sys.path:
    sys.path.insert(0, str(REPOSITORY_ROOT))
EXECUTION_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h28_one_shot_execution_contract.json"
)
EXECUTION_CONTRACT_SHA256 = (
    "286179fd68cf93b0c35ac6e8a54632772ada863a6c6041cac6738298461a9dd7"
)
ACTIVATION_FIELDS = (
    "schema_identity",
    "execution_id",
    "expected_commit",
    "execution_contract_sha256",
    "output_relative_path",
    "claim_relative_path",
    "acknowledgement_env",
    "acknowledgement_value",
    "retry_allowed",
    "locked_test_used",
)
OUTPUT_RELATIVE_PATH = Path("tmp/local/h28-causal-timing-v1")
CLAIM_RELATIVE_PATH = Path("tmp/local/h28-causal-timing-v1.claim.json")
RECORD_INDEX_FIELDS = (
    "record_identity",
    "record_directory",
    "population_namespace",
    "payload_sha256",
    "candidate_pitch",
    "active_pitches",
    "proposal_hop_end",
    "resolution_hop_end",
    "cents",
    "inharmonicity",
)


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _git_blob(raw: bytes) -> str:
    return hashlib.sha1(
        b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw
    ).hexdigest()


def _canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            allow_nan=False,
            separators=(",", ":"),
        )
        + "\n"
    ).encode("utf-8")


def _reject_constant(value: str) -> object:
    raise ValueError(f"H28 non-JSON numeric constant forbidden: {value}")


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H28 duplicate JSON key forbidden: {key}")
        result[key] = value
    return result


def _strict_json(raw: bytes, *, label: str) -> Mapping[str, object]:
    try:
        value = json.loads(
            raw.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} must be strict UTF-8 JSON") from exc
    if type(value) is not dict:
        raise ValueError(f"{label} root must be an object")
    return MappingProxyType(value)


def _relative_inside(root: Path, relative: object, *, label: str) -> Path:
    if type(relative) is not str:
        raise ValueError(f"H28 {label} must be a string")
    candidate = Path(relative)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ValueError(f"H28 {label} must be repository-relative")
    resolved = (root / candidate).absolute()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"H28 {label} escapes repository root") from exc
    return resolved


def _verify_bound_file(root: Path, item: Mapping[str, object]) -> bytes:
    path = _relative_inside(root, item.get("path"), label="bound file path")
    if path.is_symlink() or not path.is_file() or path.absolute() != path.resolve(strict=True):
        raise ValueError(f"H28 bound file path invalid: {item.get('path')}")
    raw = path.read_bytes()
    if (
        type(item.get("size_bytes")) is not int
        or len(raw) != item["size_bytes"]
        or _sha256(raw) != item.get("sha256")
        or _git_blob(raw) != item.get("git_blob")
    ):
        raise ValueError(f"H28 bound file identity changed: {item.get('path')}")
    return raw


def _verify_transitive_implementation_bindings(
    root: Path,
    fixed_documents: Mapping[str, Mapping[str, object]],
) -> None:
    engine_document = fixed_documents[
        "configs/harmonic_censoring_h28_engine_recomputer_dormant_contract.json"
    ]
    bindings = engine_document.get("dormant_implementation_bindings")
    if type(bindings) is not list or len(bindings) != 6:
        raise ValueError("H28 engine implementation binding set changed")
    for raw_item in bindings:
        if type(raw_item) is not dict:
            raise ValueError("H28 engine implementation binding invalid")
        _verify_bound_file(root, raw_item)

    timing_document = fixed_documents[
        "configs/harmonic_censoring_h28_causal_timing_preregistration.json"
    ]
    timing_dependencies = timing_document.get("fixed_dependencies")
    if type(timing_dependencies) is not list or len(timing_dependencies) != 6:
        raise ValueError("H28 timing dependency binding set changed")
    for raw_item in timing_dependencies:
        if type(raw_item) is not dict:
            raise ValueError("H28 timing dependency binding invalid")
        _verify_bound_file(root, raw_item)

    materializer_document = fixed_documents[
        "configs/harmonic_censoring_h28_materializer_dormant_contract.json"
    ]
    materializer_binding = materializer_document.get("implementation_binding")
    if type(materializer_binding) is not dict:
        raise ValueError("H28 materializer implementation binding invalid")
    _verify_bound_file(root, materializer_binding)
    materializer_fixed = materializer_document.get("fixed_contracts")
    if type(materializer_fixed) is not dict or tuple(materializer_fixed) != (
        "timing_preregistration",
        "engine_recomputer",
        "h27_fixture_specification",
    ):
        raise ValueError("H28 materializer fixed binding set changed")
    for raw_item in materializer_fixed.values():
        if type(raw_item) is not dict:
            raise ValueError("H28 materializer fixed binding invalid")
        _verify_bound_file(root, raw_item)


def _git_output(root: Path, *arguments: str) -> str:
    completed = subprocess.run(
        ["git", "-C", str(root), *arguments],
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    return completed.stdout.strip()


def _load_preclaim(
    repository_root: Path,
    activation_path: Path,
) -> tuple[Mapping[str, object], str, Mapping[str, object], str]:
    root = Path(repository_root).resolve(strict=True)
    contract_path = (root / EXECUTION_CONTRACT_RELATIVE_PATH).resolve(strict=True)
    contract_raw = contract_path.read_bytes()
    if _sha256(contract_raw) != EXECUTION_CONTRACT_SHA256:
        raise ValueError("H28 execution contract bytes changed")
    contract = _strict_json(contract_raw, label="H28 execution contract")
    if (
        contract.get("schema_identity") != "H28_ONE_SHOT_EXECUTION_CONTRACT_V1"
        or contract.get("status")
        != "DORMANT_RUNNER_REQUIRES_SEPARATE_EXTERNAL_ACTIVATION"
    ):
        raise ValueError("H28 execution contract identity/status changed")

    activation_absolute = Path(activation_path).absolute()
    activation_resolved = activation_absolute.resolve(strict=True)
    if activation_absolute != activation_resolved or activation_resolved.is_symlink():
        raise ValueError("H28 activation must be a non-symlink file")
    activation_root = (root / "tmp" / "local").absolute()
    if (
        activation_root.is_symlink()
        or not activation_root.is_dir()
        or activation_root != activation_root.resolve(strict=True)
    ):
        raise ValueError("H28 tmp/local root must be an existing non-symlink directory")
    activation_resolved.relative_to(activation_root)
    if not activation_resolved.is_file():
        raise ValueError("H28 activation must be a regular file")
    activation_raw = activation_resolved.read_bytes()
    activation = _strict_json(activation_raw, label="H28 external activation")
    if tuple(activation) != ACTIVATION_FIELDS:
        raise ValueError("H28 activation fields or order changed")
    if activation["schema_identity"] != "H28_ONE_SHOT_EXTERNAL_ACTIVATION_V1":
        raise ValueError("H28 activation identity changed")
    execution_id = activation["execution_id"]
    if type(execution_id) is not str or re.fullmatch(r"h28-[a-z0-9-]{8,64}", execution_id) is None:
        raise ValueError("H28 execution ID invalid")
    expected_commit = activation["expected_commit"]
    if type(expected_commit) is not str or re.fullmatch(r"[0-9a-f]{40}", expected_commit) is None:
        raise ValueError("H28 expected commit invalid")
    if activation["execution_contract_sha256"] != EXECUTION_CONTRACT_SHA256:
        raise ValueError("H28 activation execution-contract SHA mismatch")
    if (
        activation["output_relative_path"] != OUTPUT_RELATIVE_PATH.as_posix()
        or activation["claim_relative_path"] != CLAIM_RELATIVE_PATH.as_posix()
        or activation["acknowledgement_env"] != "H28_CAUSAL_TIMING_EXECUTE"
        or activation["acknowledgement_value"] != "1"
        or activation["retry_allowed"] is not False
        or activation["locked_test_used"] is not False
    ):
        raise ValueError("H28 activation boundary changed")
    if os.environ.get("H28_CAUSAL_TIMING_EXECUTE") != "1":
        raise PermissionError("H28 execution acknowledgement missing")

    fixed = contract.get("fixed_contracts")
    if type(fixed) is not list or len(fixed) != 3:
        raise ValueError("H28 fixed execution contract set changed")
    fixed_documents: dict[str, Mapping[str, object]] = {}
    for raw_item in fixed:
        if type(raw_item) is not dict:
            raise ValueError("H28 fixed execution contract binding invalid")
        raw = _verify_bound_file(root, raw_item)
        fixed_documents[str(raw_item["path"])] = _strict_json(
            raw, label=f"H28 fixed contract {raw_item['path']}"
        )
    _verify_transitive_implementation_bindings(root, fixed_documents)

    if _git_output(root, "rev-parse", "HEAD") != expected_commit:
        raise ValueError("H28 Git HEAD differs from activated commit")
    if _git_output(root, "status", "--porcelain=v1", "--untracked-files=all"):
        raise ValueError("H28 Git worktree must be clean")

    output = (root / OUTPUT_RELATIVE_PATH).absolute()
    claim = (root / CLAIM_RELATIVE_PATH).absolute()
    staging = output.with_name(f".{output.name}.staging-{execution_id}")
    failure = claim.with_name(claim.name + ".failure.json")
    terminal = claim.with_name(claim.name + ".terminal.json")
    for path in (output, claim, staging, failure, terminal):
        if path.exists() or path.is_symlink():
            raise FileExistsError(f"H28 one-shot destination already exists: {path}")

    runtime = contract.get("runtime")
    if type(runtime) is not dict:
        raise ValueError("H28 runtime contract invalid")
    if (
        platform.system() != runtime.get("platform_system")
        or platform.machine() != runtime.get("platform_machine")
        or platform.python_version() != runtime.get("python_version")
        or sys.implementation.name != "cpython"
    ):
        raise RuntimeError("H28 runtime identity mismatch")
    environment = runtime.get("environment_exact")
    if type(environment) is not dict or any(
        os.environ.get(key) != value for key, value in environment.items()
    ):
        raise RuntimeError("H28 exact CPU environment mismatch")
    if "tensorflow" in sys.modules:
        raise RuntimeError("H28 TensorFlow import forbidden")
    return contract, _sha256(contract_raw), activation, _sha256(activation_raw)


def _write_new(path: Path, raw: bytes, *, mode: int = 0o600) -> None:
    parent = path.parent.absolute()
    if parent.is_symlink() or not parent.is_dir() or parent != parent.resolve(strict=True):
        raise ValueError("H28 output parent must be an existing non-symlink directory")
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(str(path), flags, mode)
    try:
        view = memoryview(raw)
        offset = 0
        while offset < len(view):
            count = os.write(descriptor, view[offset:])
            if count <= 0:
                raise OSError("H28 incomplete file write")
            offset += count
        os.fsync(descriptor)
        if os.fstat(descriptor).st_size != len(raw):
            raise OSError("H28 written file size changed")
    finally:
        os.close(descriptor)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(str(path), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _rename_no_replace(source: Path, destination: Path) -> None:
    if platform.system() != "Darwin":
        raise RuntimeError("H28 atomic no-replace publication requires Darwin")
    library = ctypes.CDLL(None, use_errno=True)
    renameatx_np = library.renameatx_np
    renameatx_np.argtypes = [ctypes.c_int, ctypes.c_char_p, ctypes.c_int, ctypes.c_char_p, ctypes.c_uint]
    renameatx_np.restype = ctypes.c_int
    at_fdcwd = -2
    rename_excl = 0x00000004
    result = renameatx_np(
        at_fdcwd,
        os.fsencode(source),
        at_fdcwd,
        os.fsencode(destination),
        rename_excl,
    )
    if result != 0:
        error = ctypes.get_errno()
        raise OSError(error, os.strerror(error), str(destination))


@contextmanager
def _activated_process_local_guards() -> Iterator[tuple[object, object, set[int]]]:
    from src.polyphonic import harmonic_censoring_h28_engine as engine
    from src.polyphonic import harmonic_censoring_h28_materializer_dormant as materializer
    from src.polyphonic import harmonic_censoring_h28_recomputer as recomputer
    from src.polyphonic.harmonic_censoring_h28_scientific_capability_dormant import (
        H28ScientificCapability,
    )

    materialization_capability = object.__new__(materializer.H28MaterializationCapability)
    scientific_capability = object.__new__(H28ScientificCapability)
    binding_identities: set[int] = set()

    def require_materialization(value: object) -> None:
        if value is not materialization_capability:
            raise PermissionError("H28 materialization capability identity mismatch")

    def require_scientific(value: object) -> None:
        if value is not scientific_capability:
            raise PermissionError("H28 scientific capability identity mismatch")

    def require_binding(value: object) -> None:
        if id(value) not in binding_identities:
            raise PermissionError("H28 sealed binding identity mismatch")

    original = (
        materializer.require_h28_materialization_capability,
        engine.require_h28_scientific_capability,
        engine.require_h28_sealed_record_binding,
        recomputer.require_h28_scientific_capability,
        recomputer.require_h28_sealed_record_binding,
    )
    materializer.require_h28_materialization_capability = require_materialization
    engine.require_h28_scientific_capability = require_scientific
    engine.require_h28_sealed_record_binding = require_binding
    recomputer.require_h28_scientific_capability = require_scientific
    recomputer.require_h28_sealed_record_binding = require_binding
    try:
        yield materialization_capability, scientific_capability, binding_identities
    finally:
        (
            materializer.require_h28_materialization_capability,
            engine.require_h28_scientific_capability,
            engine.require_h28_sealed_record_binding,
            recomputer.require_h28_scientific_capability,
            recomputer.require_h28_sealed_record_binding,
        ) = original
        binding_identities.clear()


def _binding_from_index(
    population_root: Path,
    population_index_sha256: str,
    index_record: Mapping[str, object],
    binding_identities: set[int],
) -> object:
    from src.polyphonic.harmonic_censoring_h28_scientific_capability_dormant import (
        H28SealedRecordBinding,
        H28_SEALED_RECORD_BINDING_FIELDS,
    )

    record_raw = _canonical_json_bytes(dict(index_record))
    values = {
        "population_root": population_root,
        "population_index_path": population_root / "population_index.json",
        "population_index_sha256": population_index_sha256,
        "population_index_record_sha256": _sha256(record_raw),
        "record_directory": population_root / str(index_record["record_directory"]),
        "record_identity": index_record["record_identity"],
        "population_namespace": index_record["population_namespace"],
        "payload_sha256": MappingProxyType(dict(index_record["payload_sha256"])),
        "candidate_pitch": index_record["candidate_pitch"],
        "active_pitches": tuple(index_record["active_pitches"]),
        "proposal_hop_end": index_record["proposal_hop_end"],
        "resolution_hop_end": index_record["resolution_hop_end"],
        "cents": index_record["cents"],
        "inharmonicity": index_record["inharmonicity"],
    }
    if tuple(values) != H28_SEALED_RECORD_BINDING_FIELDS:
        raise RuntimeError("H28 binding field order changed")
    binding = object.__new__(H28SealedRecordBinding)
    for name, value in values.items():
        object.__setattr__(binding, name, value)
    binding_identities.add(id(binding))
    return binding


def _publish_and_measure(
    np: object,
    repository_root: Path,
    activation: Mapping[str, object],
    activation_sha256: str,
    execution_contract_sha256: str,
    claim_sha256: str,
    staging: Path,
) -> Mapping[str, object]:
    from src.polyphonic import harmonic_censoring_h28_engine as engine
    from src.polyphonic import harmonic_censoring_h28_materializer_dormant as materializer
    from src.polyphonic import harmonic_censoring_h28_recomputer as recomputer
    from src.polyphonic.harmonic_censoring_h28_diagnostics import (
        serialize_h28_reconciled_diagnostic,
    )
    from src.polyphonic.harmonic_censoring_h28_timing_contract import (
        RECORD_ORDER,
        derive_h28_terminal_verdict,
        load_h28_timing_contract,
    )

    started = time.monotonic()
    with _activated_process_local_guards() as (
        materialization_capability,
        scientific_capability,
        binding_identities,
    ):
        records = materializer.materialize_h28_records_in_memory(
            np, materialization_capability, repository_root
        )
        print("H28 heartbeat: materialized 6/6 in memory", flush=True)
        population_root = staging / "population"
        population_root.mkdir(parents=True, mode=0o700)
        index_records: list[dict[str, object]] = []
        for record in records:
            descriptor = record.descriptor
            record_directory = population_root / descriptor.record_identity
            record_directory.mkdir(parents=True, mode=0o700)
            _write_new(record_directory / "waveform.f64le", record.waveform_f64le)
            _write_new(record_directory / "sample-valid-mask.u8", record.sample_valid_mask_u8)
            index_record = {
                "record_identity": descriptor.record_identity,
                "record_directory": descriptor.record_identity,
                "population_namespace": materializer.POPULATION_NAMESPACE,
                "payload_sha256": dict(record.payload_sha256),
                "candidate_pitch": descriptor.candidate_pitch,
                "active_pitches": list(descriptor.active_pitches),
                "proposal_hop_end": descriptor.proposal_hop_end,
                "resolution_hop_end": descriptor.resolution_hop_end,
                "cents": descriptor.cents,
                "inharmonicity": descriptor.inharmonicity,
            }
            if tuple(index_record) != RECORD_INDEX_FIELDS:
                raise RuntimeError("H28 population index record fields changed")
            index_records.append(index_record)
        index_document = {
            "schema_identity": "H28_CAUSAL_TIMING_POPULATION_INDEX_V1",
            "schema_version": 1,
            "population_namespace": materializer.POPULATION_NAMESPACE,
            "record_order": list(RECORD_ORDER),
            "records": index_records,
        }
        index_raw = _canonical_json_bytes(index_document)
        index_sha = _sha256(index_raw)
        _write_new(population_root / "population_index.json", index_raw)

        timing_contract = load_h28_timing_contract(repository_root)
        diagnostics: list[dict[str, object]] = []
        outcomes: dict[str, str] = {}
        record_elapsed_seconds: dict[str, float] = {}
        for position, index_record in enumerate(index_records, start=1):
            record_started = time.monotonic()
            binding = _binding_from_index(
                population_root, index_sha, index_record, binding_identities
            )
            primary = engine.run_h28_engine(
                np, scientific_capability, repository_root, binding
            )
            independent = recomputer.run_h28_independent_recomputer(
                np, scientific_capability, repository_root, binding
            )
            row = serialize_h28_reconciled_diagnostic(
                timing_contract, primary, independent
            )
            diagnostics.append(dict(row))
            outcomes[str(row["record_identity"])] = str(row["outcome"])
            record_elapsed_seconds[str(row["record_identity"])] = (
                time.monotonic() - record_started
            )
            print(f"H28 heartbeat: reconciled {position}/6", flush=True)

    verdict = derive_h28_terminal_verdict(outcomes)
    elapsed = time.monotonic() - started
    report = {
        "schema_identity": "H28_CAUSAL_TIMING_RESULT_V1",
        "schema_version": 1,
        "status": "COMPLETE_ONE_SHOT_CONSUMED_NO_RETRY",
        "execution_id": activation["execution_id"],
        "git_commit": activation["expected_commit"],
        "execution_contract_sha256": execution_contract_sha256,
        "activation_sha256": activation_sha256,
        "claim_sha256": claim_sha256,
        "runtime": {
            "python_version": platform.python_version(),
            "numpy_version": np.__version__,
            "platform_system": platform.system(),
            "platform_machine": platform.machine(),
        },
        "population_index_sha256": index_sha,
        "record_count": len(diagnostics),
        "outcomes": outcomes,
        "record_elapsed_seconds": record_elapsed_seconds,
        "terminal_verdict": verdict,
        "elapsed_seconds": elapsed,
        "locked_test_used": False,
        "training_used": False,
        "calibration_used": False,
        "retry_allowed": False,
        "completed_at_utc": _utc_now(),
    }
    _write_new(staging / "diagnostics.json", _canonical_json_bytes(diagnostics))
    _write_new(staging / "report.json", _canonical_json_bytes(report))
    complete = {
        "schema_identity": "H28_CAUSAL_TIMING_COMPLETE_V1",
        "execution_id": activation["execution_id"],
        "report_sha256": _sha256(_canonical_json_bytes(report)),
        "diagnostics_sha256": _sha256(_canonical_json_bytes(diagnostics)),
        "population_index_sha256": index_sha,
        "terminal_verdict": verdict,
    }
    _write_new(staging / "COMPLETE.json", _canonical_json_bytes(complete), mode=0o400)
    for directory in sorted(
        (item for item in staging.rglob("*") if item.is_dir()),
        key=lambda item: len(item.parts),
        reverse=True,
    ):
        _fsync_directory(directory)
    _fsync_directory(staging)
    return MappingProxyType(report)


def run_once(activation_path: Path) -> Mapping[str, object]:
    root = REPOSITORY_ROOT.resolve(strict=True)
    contract, contract_sha, activation, activation_sha = _load_preclaim(
        root, Path(activation_path)
    )
    runtime = contract["runtime"]
    import numpy as np  # Imported only after every preclaim runtime/byte/Git check.

    if np.__version__ != runtime["numpy_version"]:
        raise RuntimeError("H28 NumPy version mismatch")
    if "tensorflow" in sys.modules:
        raise RuntimeError("H28 TensorFlow import forbidden")

    output = (root / OUTPUT_RELATIVE_PATH).absolute()
    claim = (root / CLAIM_RELATIVE_PATH).absolute()
    staging = output.with_name(f".{output.name}.staging-{activation['execution_id']}")
    failure = claim.with_name(claim.name + ".failure.json")
    terminal = claim.with_name(claim.name + ".terminal.json")
    claim_document = {
        "schema_identity": "H28_ONE_SHOT_CLAIM_V1",
        "execution_id": activation["execution_id"],
        "git_commit": activation["expected_commit"],
        "execution_contract_sha256": contract_sha,
        "activation_sha256": activation_sha,
        "claimed_at_utc": _utc_now(),
        "retry_allowed": False,
    }
    claim_raw = _canonical_json_bytes(claim_document)
    _write_new(claim, claim_raw, mode=0o400)
    _fsync_directory(claim.parent)
    claim_sha = _sha256(claim_raw)
    print("H28 heartbeat: claim created; one-shot consumed", flush=True)

    try:
        staging.mkdir(mode=0o700)
        report = _publish_and_measure(
            np,
            root,
            activation,
            activation_sha,
            contract_sha,
            claim_sha,
            staging,
        )
        _rename_no_replace(staging, output)
        _fsync_directory(output.parent)
        terminal_document = {
            "schema_identity": "H28_ONE_SHOT_TERMINAL_V1",
            "execution_id": activation["execution_id"],
            "state": "COMPLETE",
            "output_relative_path": OUTPUT_RELATIVE_PATH.as_posix(),
            "terminal_verdict": report["terminal_verdict"],
            "completed_at_utc": _utc_now(),
            "retry_allowed": False,
        }
        _write_new(terminal, _canonical_json_bytes(terminal_document), mode=0o400)
        _fsync_directory(terminal.parent)
        print(f"H28 terminal: {report['terminal_verdict']}", flush=True)
        return report
    except BaseException as exc:
        failure_document = {
            "schema_identity": "H28_ONE_SHOT_FAILURE_V1",
            "execution_id": activation["execution_id"],
            "state": "FAILED_AFTER_CLAIM_NO_RETRY",
            "error_type": type(exc).__name__,
            "error_message": str(exc),
            "failed_at_utc": _utc_now(),
            "retry_allowed": False,
        }
        try:
            _write_new(failure, _canonical_json_bytes(failure_document), mode=0o400)
            _fsync_directory(failure.parent)
        except BaseException:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    arguments = sys.argv[1:] if argv is None else argv
    if len(arguments) != 1:
        raise SystemExit("usage: h28_causal_timing_execute_once.py ACTIVATION_JSON")
    run_once(Path(arguments[0]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
