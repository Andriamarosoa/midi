#!/usr/bin/env python3
"""One-shot H27 Review-4 materialization and structural data preparation."""
from __future__ import annotations

import hashlib
import importlib.metadata
import importlib.util
import json
import os
import platform
from pathlib import Path
import stat
import subprocess
import sys


ACK = "H27_REVIEW4_MATERIALIZATION_EXECUTE"
TARGET = Path("/Users/amcarene/midi-worker/repository")
REQUIRED_HEAD = "46a6bdf81a56a7a7a10524d4e55092301a452207"
ADMIN = Path("/Users/amcarene/h27-admin")
ACTIVATION = ADMIN / "activation/h27-materialization-v1.json"
AUTHORITY = ADMIN / "authority/h27-materialization-v1.json"
CLAIM = ADMIN / "claims/h27-synthetic-v1.consumed.json"
FINAL = ADMIN / "population/h27-synthetic-v1"
STAGING = ADMIN / "population/.h27-synthetic-v1.staging"
TERMINAL = ADMIN / "review4/h27-review4-terminal.json"
OPERATIONAL_MODULE = ADMIN / "review4/harmonic_censoring_h27_review4_materializer.py"
OPERATIONAL_MODULE_SHA256 = "505e45a4ae142c55121705e48db6f62658d5ad95de242fba96310d27cc4b315e"
AUTHORITY_INSTANCE_ID = "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a"
ACTIVATION_SHA256 = "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2"
SEALED_COMPONENTS = (
    ("src/polyphonic/harmonic_censoring_h27_contract.py", "0499b33a2762851d2a1fafa40b9c4976cea767e8", 12183, "34daaf2a8a2cbfc33d8ed8c8ce2a6552abb08bc30642759c8733ffda1dbb56d9"),
    ("src/polyphonic/harmonic_censoring_h27_engine.py", "d21c60e5a96cba5ba6d90dacedd49b8b1eaa5635", 24030, "a5403a675ebff4a61dfefed36f21fd529f940eb82fe466569e77e4d9ab007eb7"),
    ("src/polyphonic/harmonic_censoring_h27_materializer_dormant.py", "394f25a51f854cf629ef184694c4dcf1a45904b8", 12949, "90950664e764f6b982df3a44fd08bd534ecb190b3d7019cc49cc60b57a1c3eb7"),
    ("src/polyphonic/harmonic_censoring_h27_production_materializer_dormant.py", "d3a903acfa67daf822d50aab005b88943a8c18fa", 22223, "1d4b0b651c2c916a1a1bcd71578aa263074290c90fd381be867b77ef46cc0a25"),
    ("src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py", "79f399359e366781f9526098c98a93cca71b1b49", 32243, "02bf7e9a8e7d0e8f292adb7b00742c83c19ab56eb89e35adc5da9c1c3144ff70"),
    ("src/polyphonic/harmonic_censoring_h27_issuer_authority_claim_capability_dormant.py", "ec61eef88dce7591fd411af230568b1e1d44d62e", 18915, "d3d06f8c087845089094ff71f29d8745581d391784b9bbc40abeb57b0ba42f2f"),
    ("src/polyphonic/harmonic_censoring_h27_one_shot_execution_composition_dormant.py", "c57dbd4ccd6f9ef9b75e3698580ca14d66d74682", 7289, "6e2ccf317e071eed583b85995c11c386dfc5b306bb9a3b4c283dbf2fe0c6c9bb"),
    ("src/polyphonic/harmonic_censoring_h27_recomputer.py", "4949137f5a827e436c92b361f36f66b6f0312bcb", 22456, "4411e27fb1c2e9846f9e5688e90cb6bcc8d1d9bfd0fd12726ffd510e9f1a286a"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise PermissionError(message)


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def stable_bytes(path: Path, mode: int | None = None) -> bytes:
    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
    try:
        before = os.fstat(fd)
        named = os.stat(path, follow_symlinks=False)
        require(stat.S_ISREG(before.st_mode), f"H27 non-regular file: {path}")
        require((before.st_dev, before.st_ino) == (named.st_dev, named.st_ino), f"H27 descriptor drift: {path}")
        require(before.st_nlink == 1, f"H27 hard link forbidden: {path}")
        if mode is not None:
            require(stat.S_IMODE(before.st_mode) == mode, f"H27 mode drift: {path}")
        chunks: list[bytes] = []
        while True:
            chunk = os.read(fd, 1024 * 1024)
            if not chunk:
                break
            chunks.append(chunk)
        after = os.fstat(fd)
        for field in ("st_dev", "st_ino", "st_mode", "st_nlink", "st_size", "st_mtime_ns", "st_ctime_ns"):
            require(getattr(before, field) == getattr(after, field), f"H27 file changed while read: {path}")
        return b"".join(chunks)
    finally:
        os.close(fd)


def strict_json(raw: bytes) -> dict[str, object]:
    def pairs(items: list[tuple[str, object]]) -> dict[str, object]:
        value: dict[str, object] = {}
        for key, item in items:
            require(key not in value, "H27 duplicate JSON key")
            value[key] = item
        return value
    def constant(token: str) -> object:
        raise ValueError("H27 non-finite JSON token: " + token)
    value = json.loads(raw.decode("utf-8"), object_pairs_hook=pairs, parse_constant=constant)
    require(type(value) is dict, "H27 JSON root must be an object")
    return value


def canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=True, allow_nan=False, separators=(",", ":")) + "\n").encode("utf-8")


def git(*args: str, allowed: tuple[int, ...] = (0,)) -> bytes:
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    result = subprocess.run(
        ["git", "--no-optional-locks", "--no-replace-objects", "-c", "core.hooksPath=/dev/null", "-C", str(TARGET), *args],
        check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env,
    )
    require(result.returncode in allowed, "H27 Git preflight failed: " + repr(args))
    return result.stdout


def write_new(path: Path, raw: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        view = memoryview(raw)
        offset = 0
        while offset < len(raw):
            count = os.write(fd, view[offset:])
            require(count > 0, "H27 incomplete durable write")
            offset += count
        os.fsync(fd)
    finally:
        os.close(fd)
    parent = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(parent)
    finally:
        os.close(parent)
    require(stable_bytes(path, 0o600) == raw, f"H27 durable bytes mismatch: {path}")


def verify_runtime_and_environment() -> None:
    activation_contract = strict_json(git("cat-file", "blob", REQUIRED_HEAD + ":configs/harmonic_censoring_h27_materialization_activation_contract.json"))
    expected = activation_contract["runtime_exact"]
    observed = {
        "implementation": platform.python_implementation(), "version": platform.python_version(),
        "platform_system": platform.system(), "platform_release": platform.release(),
        "platform_machine": platform.machine(), "resolved_executable": Path(sys.executable).resolve(strict=True).as_posix(),
        "executable_size_bytes": Path(sys.executable).resolve(strict=True).stat().st_size,
        "executable_sha256": digest(Path(sys.executable).resolve(strict=True).read_bytes()),
    }
    require(all(observed[key] == expected[key] for key in observed), "H27 exact runtime mismatch")
    environment = activation_contract["process_environment_exact"]
    require(all(os.environ.get(key) == value for key, value in environment.items()), "H27 exact process environment mismatch")
    distribution = importlib.metadata.distribution("numpy")
    require(distribution.version == expected["numpy_version"], "H27 NumPy version mismatch")
    matches: dict[str, list[Path]] = {"numpy": [], "blas": []}
    for relative in distribution.files or ():
        candidate = Path(distribution.locate_file(relative)).resolve(strict=True)
        if not candidate.is_file():
            continue
        if candidate.stat().st_size == expected["numpy_multiarray_size_bytes"] and digest(candidate.read_bytes()) == expected["numpy_multiarray_sha256"]:
            matches["numpy"].append(candidate)
        if candidate.stat().st_size == expected["blas_library_size_bytes"] and digest(candidate.read_bytes()) == expected["blas_library_sha256"]:
            matches["blas"].append(candidate)
    require(len(matches["numpy"]) == len(matches["blas"]) == 1, "H27 NumPy/OpenBLAS binary identity mismatch")
    require("openblas" in matches["blas"][0].name.lower(), "H27 BLAS provider mismatch")


def preflight() -> tuple[dict[str, object], object, object]:
    require(sys.platform == "darwin" and len(sys.argv) == 1, "H27 exact Darwin zero-argument runner required")
    require(os.environ.get(ACK) == "I_UNDERSTAND_H27_REVIEW4_IS_ONE_SHOT", "H27 Review 4 ACK missing")
    require(git("rev-parse", "HEAD").decode().strip() == REQUIRED_HEAD, "H27 target HEAD mismatch")
    require(git("symbolic-ref", "-q", "HEAD", allowed=(0, 1)) == b"", "H27 target must be detached")
    require(git("status", "--porcelain=v1", "--untracked-files=all") == b"", "H27 target worktree dirty")
    require(not (TARGET / ".git/index.lock").exists(), "H27 target index.lock exists")
    for relative, blob, size, sha256 in SEALED_COMPONENTS:
        raw_component = git("cat-file", "blob", REQUIRED_HEAD + ":" + relative)
        require((git("rev-parse", REQUIRED_HEAD + ":" + relative).decode().strip(), len(raw_component), digest(raw_component)) == (blob, size, sha256), "H27 sealed component drift: " + relative)
    raw = stable_bytes(ACTIVATION, 0o600)
    require(digest(raw) == ACTIVATION_SHA256, "H27 authority-instance digest mismatch")
    activation = strict_json(raw)
    require(activation.get("authority_instance_id") == AUTHORITY_INSTANCE_ID, "H27 authority-instance id mismatch")
    require(activation.get("single_use") is True and activation.get("consumed") is False, "H27 authority-instance state mismatch")
    require(activation.get("issuer_id") == "h27-execution-codex-mac-primary", "H27 issuer mismatch")
    require(not any(path.exists() for path in (AUTHORITY, CLAIM, FINAL, STAGING, TERMINAL)), "H27 one-shot destination preexists")
    module_raw = stable_bytes(OPERATIONAL_MODULE, 0o400)
    require(digest(module_raw) == OPERATIONAL_MODULE_SHA256, "H27 operational materializer identity mismatch")
    sys.path.insert(0, str(TARGET))
    from src.polyphonic.harmonic_censoring_h27_contract import load_h27_dormant_plan
    verify_runtime_and_environment()
    plan = load_h27_dormant_plan(TARGET)
    require(len(plan.fixture_ids) == 17, "H27 baseline plan count mismatch")
    spec = importlib.util.spec_from_file_location("h27_review4_materializer", OPERATIONAL_MODULE)
    require(spec is not None and spec.loader is not None, "H27 operational materializer loader unavailable")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return activation, plan, module


def consume_and_run(activation: dict[str, object], plan: object, module: object) -> dict[str, object]:
    authority_value = {
        "schema_version": 1,
        "authority_type": "h27_review4_materialization_authority",
        "authority_instance_id": AUTHORITY_INSTANCE_ID,
        "activation_sha256": ACTIVATION_SHA256,
        "issuer_identity": activation["issuer_id"],
        "invocation_nonce": activation["invocation_nonce"],
        "population_namespace": "H27_SYNTHETIC_V1",
        "expected_record_count": 124,
        "materializer_sha256": OPERATIONAL_MODULE_SHA256,
        "single_use": True,
    }
    authority_raw = canonical(authority_value)
    write_new(AUTHORITY, authority_raw)
    claim_value = {
        "schema_version": 1,
        "claim_type": "h27_review4_materialization_consumed",
        "authority_instance_id": AUTHORITY_INSTANCE_ID,
        "authority_sha256": digest(authority_raw),
        "activation_sha256": ACTIVATION_SHA256,
        "invocation_nonce": activation["invocation_nonce"],
        "materializer_sha256": OPERATIONAL_MODULE_SHA256,
        "population_namespace": "H27_SYNTHETIC_V1",
        "retry_allowed": False,
        "consumed": True,
    }
    write_new(CLAIM, canonical(claim_value))
    capability = module._issue_review4_capability()
    import numpy as np
    module.materialize_h27_production_population(np, capability, plan)
    index_raw = stable_bytes(FINAL / "population_index.json", 0o600)
    index = strict_json(index_raw)
    records = index.get("records")
    require(index.get("population_namespace") == "H27_SYNTHETIC_V1" and index.get("record_count") == 124, "H27 index header mismatch")
    require(type(records) is list and len(records) == 124, "H27 index cardinality mismatch")
    identities = [row["record_identity"] for row in records]
    require(len(set(identities)) == 124, "H27 duplicate record identity")
    baseline = sum(str(value).startswith("baseline/") for value in identities)
    p2 = sum(str(value).startswith("p2/") for value in identities)
    require((baseline, p2) == (17, 107), "H27 phase counts mismatch")
    for row in records:
        root = FINAL / str(row["record_directory"])
        for name, expected in row["payload_sha256"].items():
            raw = stable_bytes(root / name, 0o600)
            require(digest(raw) == expected, "H27 final payload digest mismatch")
    return {
        "status": "H27_REVIEW4_TERMINAL_SUCCESS",
        "control_plane_verified": True,
        "constructor_gate_replayed": False,
        "publisher_replayed": False,
        "authority_instance_id": AUTHORITY_INSTANCE_ID,
        "materializer_authority_consumed": True,
        "materializer_invoked_once": True,
        "p0_complete": True,
        "p1_complete": True,
        "p2_complete": True,
        "population_namespace": "H27_SYNTHETIC_V1",
        "total_records": 124,
        "unique_records": 124,
        "baseline_records": baseline,
        "p2_records": p2,
        "population_index_sha256": digest(index_raw),
        "data_preparation_complete": True,
        "global_reconciliation_pass": True,
        "science_executed": False,
        "locked_test_opened": False,
        "training_executed": False,
        "review4_closed": True,
    }


def main() -> int:
    activation, plan, module = preflight()
    terminal_value = consume_and_run(activation, plan, module)
    write_new(TERMINAL, canonical(terminal_value))
    print(json.dumps(terminal_value, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
