#!/usr/bin/env python3
"""Internal H27 P2-007 secondary-runtime worker; never creates a claim."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import platform
import sys


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _runtime_identity(np, expected) -> None:
    executable = Path(sys.executable).resolve(strict=True)
    observed = {
        "implementation": platform.python_implementation(),
        "version": platform.python_version(),
        "platform_system": platform.system(),
        "platform_release": platform.release(),
        "platform_machine": platform.machine(),
        "resolved_executable": executable.as_posix(),
        "executable_size_bytes": executable.stat().st_size,
        "executable_sha256": _sha(executable),
        "numpy_version": np.__version__,
    }
    for key, value in observed.items():
        if expected.get(key) != value:
            raise RuntimeError(f"H27 secondary runtime mismatch: {key}")
    package = Path(np.__file__).resolve(strict=True).parent
    matches = {"numpy": [], "blas": []}
    for candidate in package.parent.rglob("*"):
        if candidate.is_symlink() or not candidate.is_file():
            continue
        size = candidate.stat().st_size
        if size not in (expected["numpy_multiarray_size_bytes"], expected["blas_library_size_bytes"]):
            continue
        digest = _sha(candidate)
        if size == expected["numpy_multiarray_size_bytes"] and digest == expected["numpy_multiarray_sha256"]:
            matches["numpy"].append(candidate)
        if size == expected["blas_library_size_bytes"] and digest == expected["blas_library_sha256"]:
            matches["blas"].append(candidate)
    if len(matches["numpy"]) != 1 or len(matches["blas"]) != 1 or "openblas" not in matches["blas"][0].name.lower():
        raise RuntimeError("H27 secondary NumPy/OpenBLAS identity mismatch")


def main() -> int:
    if os.environ.get("H27_REVIEW5_INTERNAL_SECONDARY") != "1":
        raise PermissionError("H27 secondary internal acknowledgement missing")
    from scripts.h27_review5_scientific_execute_once import _load_contract
    contract = _load_contract(ROOT)
    if contract["real_execution_authorized"] is not True:
        raise PermissionError("H27 secondary execution is not authorized")
    claim_path = Path(str(contract["scientific_output_root"])) / "claim.json"
    claim_raw = claim_path.read_bytes()
    claim_sha = hashlib.sha256(claim_raw).hexdigest()
    if claim_sha != os.environ.get("H27_REVIEW5_INTERNAL_CLAIM_SHA256"):
        raise PermissionError("H27 secondary claim SHA mismatch")
    from src.polyphonic.harmonic_censoring_h27_contract import load_h27_dormant_plan
    plan = load_h27_dormant_plan(ROOT)
    grid = plan.test_manifest["perturbation_grids"]["P2_RUNTIME_V1"]
    for key, value in grid["process_environment_exact"].items():
        if os.environ.get(str(key)) != str(value):
            raise PermissionError(f"H27 secondary environment mismatch: {key}")
    import numpy as np
    _runtime_identity(np, grid["axes"]["runtime"][1]["identity"])
    from src.polyphonic.harmonic_censoring_h27_scientific_authority import (
        issue_h27_scientific_capability, operational_h27_engine_boundary,
    )
    from src.polyphonic.harmonic_censoring_h27_sealed_population_loader import load_h27_sealed_population_bindings
    from src.polyphonic.harmonic_censoring_h27_engine import run_h27_engine
    from src.polyphonic.harmonic_censoring_h27_recomputer import (
        compare_h27_engine_and_recomputer, run_h27_independent_recomputer,
    )
    from src.polyphonic.harmonic_censoring_h27_test_executor import h27_engine_result_as_portable_dict
    capability = issue_h27_scientific_capability(
        claim_raw=claim_raw, claim_sha256=claim_sha,
        population_index_sha256=str(contract["population_index_sha256"]),
        execution_authorized=True,
    )
    bindings = load_h27_sealed_population_bindings(
        capability=capability, plan=plan, population_root=Path(str(contract["population_root"])),
        expected_index_sha256=str(contract["population_index_sha256"]),
    )
    selected = tuple(item for item in bindings if item.record_identity.startswith("p2/P2_RUNTIME_V1/")
                     and item.record_identity.endswith("runtime=secondary"))
    results = []
    with operational_h27_engine_boundary(capability):
        for binding in selected:
            engine = run_h27_engine(np, capability, ROOT, binding)
            recomputed = run_h27_independent_recomputer(np, capability, ROOT, binding)
            compare_h27_engine_and_recomputer(engine, recomputed)
            results.append(h27_engine_result_as_portable_dict(engine))
    payload = {"record_count": len(results), "results": results}
    sys.stdout.buffer.write(json.dumps(payload, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8") + b"\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
