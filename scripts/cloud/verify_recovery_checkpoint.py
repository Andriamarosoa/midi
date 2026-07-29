"""Verify that the newest crash-safe training checkpoint reloads exactly.

This command is intentionally run in a fresh process after cloud training.
It validates the native Keras archive, optimizer iterations, learning rate,
immutable training signatures, and the locked-test contract.  The resulting
JSON report is included in the Kaggle output archive.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path
from typing import Any

import keras
import tensorflow as tf

# Importing the model module registers every custom Keras object needed when a
# compiled recovery archive is deserialized in this otherwise fresh process.
from src.polyphonic import model as _polyphonic_model  # noqa: F401
from src.polyphonic.recovery import (
    RecoverySignatures,
    atomic_write_json,
    load_latest_recovery_checkpoint,
)


def _state_candidates(recovery_dir: Path) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for path in sorted(recovery_dir.glob("recovery-*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            continue
        if (
            isinstance(payload, dict)
            and isinstance(payload.get("generation"), int)
            and payload.get("locked_test_used") is False
        ):
            candidates.append(payload)
    return sorted(
        candidates,
        key=lambda payload: int(payload["generation"]),
        reverse=True,
    )


def verify_recovery_roundtrip(
    run_dir: str | Path,
    *,
    output_path: str | Path | None = None,
) -> dict[str, Any]:
    """Reload and verify one run's newest intact compiled recovery state."""

    run = Path(run_dir).resolve()
    recovery_dir = run / "recovery"
    candidates = _state_candidates(recovery_dir)
    if not candidates:
        raise FileNotFoundError(
            f"No valid recovery state found below {recovery_dir}."
        )

    newest = candidates[0]
    signatures = RecoverySignatures(
        plan_sha256=str(newest["plan_sha256"]),
        config_sha256=str(newest["config_sha256"]),
        manifest_sha256=str(newest["manifest_sha256"]),
        commit=str(newest["commit"]),
    )
    snapshot = load_latest_recovery_checkpoint(
        recovery_dir,
        signatures=signatures,
    )
    if snapshot is None:
        raise FileNotFoundError(
            f"No recovery checkpoint found below {recovery_dir}."
        )
    newest_identity = (
        int(newest["generation"]),
        str(newest["slot"]),
        str(newest["model_sha256"]),
    )
    restored_identity = (
        int(snapshot.state["generation"]),
        snapshot.slot,
        str(snapshot.state["model_sha256"]),
    )
    if restored_identity != newest_identity:
        raise RuntimeError(
            "The newest recovery generation did not round-trip exactly: "
            f"expected={newest_identity}, restored={restored_identity}."
        )

    report: dict[str, Any] = {
        "schema_version": 1,
        "passed": True,
        "run_dir": str(run),
        "slot": snapshot.slot,
        "generation": int(snapshot.state["generation"]),
        "epoch": int(snapshot.state["epoch"]),
        "next_batch": int(snapshot.state["next_batch"]),
        "optimizer_iterations": int(
            snapshot.state["optimizer_iterations"]
        ),
        "learning_rate": float(snapshot.state["learning_rate"]),
        "model_sha256": str(snapshot.state["model_sha256"]),
        "signatures": signatures.as_dict(),
        "runtime": {
            "python": platform.python_version(),
            "tensorflow": str(tf.__version__),
            "keras": str(keras.__version__),
            "executable": sys.executable,
        },
        "locked_test_used": False,
    }
    destination = (
        run / "recovery_roundtrip.json"
        if output_path is None
        else Path(output_path)
    )
    atomic_write_json(destination, report)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = verify_recovery_roundtrip(
        args.run_dir,
        output_path=args.output,
    )
    print(json.dumps(report, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
