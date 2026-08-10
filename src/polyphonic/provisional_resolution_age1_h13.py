"""H13 execution seal for the fixed sealed-cohort group universe.

Import and preflight remain zero-science. The real entrypoint has no scientific
arguments and remains guarded by a separately reviewed one-shot marker.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Sequence

from . import provisional_resolution_age1_h12 as h12
from .provisional_resolution_age1_h11 import run_h11_once, sha256_file
from .provisional_resolution_age1_metrics import (
    GroupedAge1EvaluationRow,
    H7SyntheticMetricReport,
    evaluate_h7_synthetic_metrics,
)


H13_CONTRACT_RELATIVE = Path(
    "configs/provisional_resolution_age1_persistence_h13_execution_seal.json"
)
H13_PURPOSE = "provisional_resolution_age1_persistence_h13_fixed_group_universe"
H13_STATUS = "provisional_resolution_age1_persistence_h13_execution_seal_ready"
H13_VERDICT = "age1_persistence_h13_fixed_group_universe_conformance_demonstrated"


def _load_h13_contract(repository_root: Path) -> tuple[Path, dict[str, Any]]:
    path = repository_root / H13_CONTRACT_RELATIVE
    payload = json.loads(path.read_text(encoding="utf-8"))
    if (
        payload.get("purpose") != H13_PURPOSE
        or payload.get("status") != H13_STATUS
        or payload.get("verdict") != H13_VERDICT
    ):
        raise RuntimeError("H13 execution-seal contract identity mismatch.")
    return path, payload


def require_h13_source_bindings(repository_root: Path) -> dict[str, Any]:
    """Bind the corrected metric engine and final non-injectable runner."""
    _path, payload = _load_h13_contract(repository_root)
    bindings = payload.get("source_bindings")
    if not isinstance(bindings, dict):
        raise RuntimeError("H13 source bindings are missing.")
    expected = {
        "src/polyphonic/provisional_resolution_age1_metrics.py": bindings.get("corrected_metric_blob"),
        "src/polyphonic/provisional_resolution_age1_h12.py": bindings.get("corrected_h12_binding_blob"),
        "src/polyphonic/provisional_resolution_age1_h13.py": bindings.get("final_h13_runner_blob"),
    }
    for relative, expected_blob in expected.items():
        if not isinstance(expected_blob, str) or len(expected_blob) != 40:
            raise RuntimeError("H13 contract contains an invalid source blob.")
        if h12._git_blob(repository_root, f"HEAD:{relative}") != expected_blob:
            raise RuntimeError(f"H13 source binding mismatch: {relative}")
    return payload


def _sealed_metric(
    rows: Sequence[GroupedAge1EvaluationRow],
    *,
    cohort_group_universe: tuple[str, ...],
) -> H7SyntheticMetricReport:
    return evaluate_h7_synthetic_metrics(
        rows, cohort_group_universe=cohort_group_universe
    )


def run_h13_preflight(repository_root: Path, worker_root: Path) -> dict[str, object]:
    """Verify the final execution seal and 31 metadata groups, without science."""
    repository = Path(repository_root).resolve(strict=True)
    base = h12.run_h12_preflight(repository, worker_root)
    payload = require_h13_source_bindings(repository)
    paths = h12.sealed_h12_paths(repository, worker_root)
    records, _forbidden = h12._load_h8_metadata(paths.h8_cohort)
    universe = h12.h8_group_universe(records)
    sealed = payload.get("sealed_group_universe")
    if not isinstance(sealed, dict) or sealed.get("count") != 31:
        raise RuntimeError("H13 contract does not seal exactly 31 groups.")
    if sealed.get("derivation") != "sorted_unique_leakage_group_key_from_raw_h8_metadata":
        raise RuntimeError("H13 group-universe derivation mismatch.")
    if len(universe) != base.get("leakage_groups"):
        raise RuntimeError("H13 preflight group universe differs from H8 metadata.")
    return {
        **base,
        "status": "h7_real_execution_preflight_ready",
        "h13_status": H13_STATUS,
        "sealed_cohort_group_universe_count": len(universe),
        "runner_invoked": False,
    }


def run_real_h7_discovery() -> tuple[Any, Any]:
    """Final non-injectable runner; consumes only a marker bound to H13 bytes."""
    repository_root = Path(__file__).resolve().parents[2]
    data_root = os.environ.get("MIDI_DATA_ROOT")
    if not data_root:
        raise RuntimeError("H13 requires MIDI_DATA_ROOT from the Mac worker.")
    worker_root = Path(data_root).resolve(strict=True).parent
    paths = h12.sealed_h12_paths(repository_root, worker_root)
    base = h12._run_h12_preflight(
        paths, authorization_marker_must_be_absent=False
    )
    if base["status"] != "h7_real_execution_preflight_ready":
        raise RuntimeError("H13 base preflight did not reach ready status.")
    contract_path, _payload = _load_h13_contract(repository_root)
    require_h13_source_bindings(repository_root)
    records, forbidden = h12._load_h8_metadata(paths.h8_cohort)
    group_universe = h12.h8_group_universe(records)

    def metric(rows: Sequence[GroupedAge1EvaluationRow]) -> H7SyntheticMetricReport:
        return _sealed_metric(rows, cohort_group_universe=group_universe)

    return run_h11_once(
        marker_path=paths.authorization_marker,
        expected_contract_sha256=sha256_file(contract_path),
        destination=paths.result_destination,
        recordings=tuple(record.h11 for record in records),
        adapter=h12.ConcreteH7ScientificAdapter(paths, records),
        metric_callable=metric,
        forbidden_groups=forbidden,
        expected_manifest_sha256=h12.MANIFEST_SHA256,
        expected_plan_sha256=h12.PLAN_SHA256,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Sealed H13 H7 discovery runner.")
    parser.add_argument("--preflight-only", action="store_true")
    args = parser.parse_args()
    if not args.preflight_only:
        run_real_h7_discovery()
        return
    repository_root = Path(__file__).resolve().parents[2]
    data_root = os.environ.get("MIDI_DATA_ROOT")
    if not data_root:
        raise RuntimeError("H13 requires MIDI_DATA_ROOT from the Mac worker.")
    worker_root = Path(data_root).resolve(strict=True).parent
    print(json.dumps(
        run_h13_preflight(repository_root, worker_root),
        sort_keys=True,
        separators=(",", ":"),
    ))


__all__ = [
    "H13_CONTRACT_RELATIVE",
    "H13_PURPOSE",
    "H13_STATUS",
    "H13_VERDICT",
    "require_h13_source_bindings",
    "run_h13_preflight",
    "run_real_h7_discovery",
]


if __name__ == "__main__":
    main()
