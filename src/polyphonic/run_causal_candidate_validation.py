"""One sealed, CPU-only invocation of the causal-candidate V1 validation A/B.

There is deliberately no CLI and no caller-controlled path, cohort, decoder,
threshold, audio-evidence, or output argument.  The shared Mac worker supplies
only its CPU acknowledgement and a separately reviewed expected Git commit.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from .causal_candidate_validation import evaluate_sealed_causal_candidate_ab


VALIDATION_EXECUTE_ENV = "DECODER_CANDIDATE_VALIDATION_EXECUTE"
VALIDATION_WALL_TIMEOUT_SECONDS = 900
VALIDATION_RUN_DIRECTORY_NAME = "causal_candidate_validation_ab_v1_20260809"
# This literal denotes the historical, immutable fit output.  Keeping the CR
# internal avoids passing it through the worker argument transport.
FIT_ARTIFACT_DIRECTORY_NAME = "causal_candidate_fit_v1_20260809\r"
TRANSCRIPTION_CHECKPOINT_SHA256 = (
    "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
)


def _require_execution_acknowledgement() -> None:
    if os.environ.get(VALIDATION_EXECUTE_ENV) != "1":
        raise RuntimeError(
            "Fail closed: set DECODER_CANDIDATE_VALIDATION_EXECUTE=1 only "
            "through the separately reviewed Mac worker invocation."
        )


def sealed_validation_paths(repository_root: Path, worker_root: Path) -> dict[str, Path]:
    """Resolve the only approved paths, including the historical CR directory."""
    repository_root = Path(repository_root).resolve(strict=True)
    worker_root = Path(worker_root).resolve(strict=True)
    if repository_root != (worker_root / "repository").resolve(strict=True):
        raise RuntimeError("Fail closed: validation must run from the worker repository.")
    fit_directory = repository_root / "tmp" / FIT_ARTIFACT_DIRECTORY_NAME
    return {
        "repository_root": repository_root,
        "run_dir": repository_root / "tmp" / VALIDATION_RUN_DIRECTORY_NAME,
        "policy_path": repository_root / "configs" / "causal_candidate_fit_v1_validation_ab_policy.json",
        "selection_path": repository_root / "configs" / "causal_candidate_fit_v1_validation_selection_12.json",
        "fit_report_path": fit_directory / "fit_report.json",
        "model_path": fit_directory / "causal_candidate_fit_v1.keras",
        "standardizer_path": fit_directory / "fit_standardizer.json",
        "manifest_path": worker_root / "data" / "processed" / "polyphonic_harmonic_presence_v1" / "manifest_train_validation.csv",
        "checkpoint_path": worker_root / "checkpoints" / f"{TRANSCRIPTION_CHECKPOINT_SHA256}.keras",
        "evaluation_config_path": repository_root / "configs" / "polyphonic_dual_stream_bass_independent_note.yaml",
        "decoder_config_path": repository_root / "configs" / "independent_note_decoder_reference.json",
    }


def run_sealed_validation() -> dict[str, object]:
    """Run the one reviewed A/B only after immutable-path preflight succeeds."""
    _require_execution_acknowledgement()
    data_root = os.environ.get("MIDI_DATA_ROOT")
    if not data_root:
        raise RuntimeError("Fail closed: MIDI_DATA_ROOT is required from the Mac worker.")
    worker_root = Path(data_root).resolve(strict=True).parent
    repository_root = Path.cwd().resolve(strict=True)
    paths = sealed_validation_paths(repository_root, worker_root)
    run_dir = paths["run_dir"]
    if run_dir.exists():
        raise FileExistsError(f"Refusing to reuse sealed validation destination: {run_dir}")
    return evaluate_sealed_causal_candidate_ab(
        **paths,
        report_suffix="causal_candidate_fit_v1_ab",
    )


def main() -> None:
    report = run_sealed_validation()
    decision = report["causal_candidate_validation"]["decision"]
    print(json.dumps({
        "status": "complete_non_authorizing",
        "report": str(
            Path.cwd() / "tmp" / VALIDATION_RUN_DIRECTORY_NAME / "reports"
            / "validation_events_1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325_causal_candidate_fit_v1_ab.json"
        ),
        "all_rules_passed": decision["all_rules_passed"],
        "locked_test_used": False,
    }, sort_keys=True))


if __name__ == "__main__":
    main()
