"""Run the polyphonic training pipeline on Kaggle or hosted Google Colab.

The command deliberately rejects Windows and the ``main``/``master`` branch.
Stage the writable raw datasets under ``data/`` before using ``--prepare-data``.
Install the environment with::

    python -m pip install -r requirements/cloud-training.txt
    python -m pip install -e . --no-deps

Typical execution::

    python scripts/cloud/train_polyphonic.py --prepare-data

An interrupted run can be continued with ``--resume-run RUN_DIRECTORY``.
Training and checkpoint selection use train/validation only. This orchestrator
never launches the locked test evaluation.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Sequence

import yaml


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG = Path("configs/polyphonic_train.yaml")
DEFAULT_MANIFEST = Path(
    "data/processed/polyphonic_v2_2_combined/manifest.csv"
)
RAW_SOURCES = (
    Path("data/GuitarSet"),
    Path("data/GAPS"),
    Path("data/Guitar-TECHS"),
)
MINIMUM_FREE_GIB = 16.0
MINIMUM_STAGED_TRAIN_FREE_GIB = 2.0
DEFAULT_SMOKE_EXAMPLES = 8192
DEFAULT_SMOKE_VALIDATION_EXAMPLES = 2048
DEFAULT_LOG_EVERY_BATCHES = 25
DEFAULT_SMOKE_RUNTIME_MINUTES = 30.0
DEFAULT_TRAIN_RUNTIME_MINUTES = 600.0


def _run(command: Sequence[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(command, cwd=ROOT, check=True)


def _src_training_arguments(
    *,
    workers: int,
    smoke_test: bool,
    representative_smoke: bool,
    smoke_examples: int,
    smoke_validation_examples: int,
    log_every_batches: int,
    maximum_runtime_minutes: float | None,
) -> list[str]:
    """Build the bounded, observable arguments passed to the trainer."""
    if workers < 1:
        raise ValueError("workers must be positive.")
    if smoke_examples < 1 or smoke_validation_examples < 1:
        raise ValueError("Smoke example counts must be positive.")
    if log_every_batches < 1:
        raise ValueError("log_every_batches must be positive.")
    if representative_smoke and not smoke_test:
        raise ValueError("--representative-smoke requires --smoke-test.")
    runtime_minutes = (
        maximum_runtime_minutes
        if maximum_runtime_minutes is not None
        else (
            DEFAULT_SMOKE_RUNTIME_MINUTES
            if smoke_test
            else DEFAULT_TRAIN_RUNTIME_MINUTES
        )
    )
    if runtime_minutes <= 0:
        raise ValueError("maximum_runtime_minutes must be positive.")

    arguments = [
        "--workers",
        str(workers),
        "--log-every-batches",
        str(log_every_batches),
        "--maximum-runtime-minutes",
        str(float(runtime_minutes)),
    ]
    if smoke_test:
        arguments.extend([
            "--smoke-test",
            "--smoke-examples",
            str(smoke_examples),
            "--smoke-validation-examples",
            str(smoke_validation_examples),
        ])
        if representative_smoke:
            arguments.append("--representative-smoke")
    return arguments


def _git_value(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _branch() -> str:
    packaged = os.environ.get("GUITAR_MIDI_SOURCE_BRANCH")
    if packaged:
        return packaged
    return _git_value("branch", "--show-current")


def _commit() -> str:
    packaged = os.environ.get("GUITAR_MIDI_SOURCE_COMMIT")
    if packaged:
        return packaged
    return _git_value("rev-parse", "HEAD")


def validate_cloud_context(
    *,
    platform_name: str,
    branch: str,
    gpu_names: Sequence[str],
    free_gib: float,
    minimum_free_gib: float = MINIMUM_FREE_GIB,
) -> None:
    """Reject contexts that violate the cloud-training contract."""
    if platform_name == "nt":
        raise RuntimeError(
            "Training local Windows désactivé : utiliser Kaggle ou Colab."
        )
    if not branch or branch in {"main", "master"}:
        raise RuntimeError(
            "Créer une branche d'expérience avant de lancer le train."
        )
    if not gpu_names:
        raise RuntimeError(
            "Aucun GPU TensorFlow détecté dans le runtime cloud."
        )
    if free_gib < minimum_free_gib:
        raise RuntimeError(
            f"Espace libre insuffisant : {free_gib:.1f} Gio, "
            f"{minimum_free_gib:.1f} Gio requis."
        )


def _gpu_names() -> list[str]:
    import tensorflow as tf

    return [
        str(device.name)
        for device in tf.config.list_physical_devices("GPU")
    ]


def _free_gib() -> float:
    return shutil.disk_usage(ROOT).free / (1024.0 ** 3)


def _require_inputs(config_path: Path, prepare_data: bool) -> None:
    if not config_path.is_file():
        raise FileNotFoundError(config_path)
    if prepare_data:
        missing = [
            str(path) for path in RAW_SOURCES if not path.is_dir()
        ]
        if missing:
            raise FileNotFoundError(
                "Sources brutes absentes : " + ", ".join(missing)
            )
    elif not DEFAULT_MANIFEST.is_file():
        raise FileNotFoundError(
            f"{DEFAULT_MANIFEST} absent. Utiliser --prepare-data après "
            "avoir placé les sources brutes dans data/."
        )


def _latest_run(config: dict[str, Any]) -> Path:
    latest = Path(config["train"]["output_root"]) / "latest_run.txt"
    if not latest.is_file():
        raise FileNotFoundError(latest)
    run_dir = Path(latest.read_text(encoding="utf-8").strip())
    if not run_dir.is_dir():
        raise FileNotFoundError(run_dir)
    return run_dir


def _last_history_row(run_dir: Path) -> dict[str, str]:
    history = run_dir / "history.csv"
    if not history.is_file():
        return {}
    with history.open("r", encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows[-1] if rows else {}


def _write_result(
    run_dir: Path,
    artifact_dir: Path | None,
    branch: str,
    commit: str,
    started_at: str,
    post_train_completed: bool,
) -> Path:
    selection_path = run_dir / "selection.json"
    selection = (
        json.loads(selection_path.read_text(encoding="utf-8"))
        if selection_path.is_file()
        else {}
    )
    last = _last_history_row(run_dir)
    result_name = (
        f"{date.today().isoformat()}_cloud-training-{run_dir.name}.md"
    )
    result_path = ROOT / "readme" / "results" / result_name
    result_path.parent.mkdir(parents=True, exist_ok=True)
    selected = selection.get("selected_metrics", {})
    onset = selected.get("onset", {})
    weighted = (
        selected.get("dataset_metrics", {})
        .get("weighted", {})
        .get("onset", {})
    )
    lines = [
        f"# Résultat — entraînement cloud `{run_dir.name}`",
        "",
        f"> Date : {date.today().isoformat()}",
        f"> Branche : `{branch}`",
        f"> Commit : `{commit}`",
        "> Test verrouillé utilisé : non",
        "",
        "## Exécution",
        "",
        f"- Début UTC : `{started_at}`",
        f"- Run : `{run_dir.as_posix()}`",
        f"- Post-train validation-only terminé : "
        f"`{str(post_train_completed).lower()}`",
        f"- Artefacts : "
        f"`{artifact_dir.as_posix() if artifact_dir else 'non exportés'}`",
        "",
        "## Dernière époque",
        "",
        f"- `val_frame_micro_f1` : "
        f"`{last.get('val_frame_micro_f1', 'indisponible')}`",
        f"- `val_onset_micro_f1` : "
        f"`{last.get('val_onset_micro_f1', 'indisponible')}`",
        "",
        "## Sélection événementielle",
        "",
        f"- F1 onset pondéré par corpus : "
        f"`{weighted.get('f1', 'non exécuté')}`",
        f"- F1 onset global : `{onset.get('f1', 'non exécuté')}`",
        "",
        "## Limites",
        "",
        "- Le test est resté verrouillé.",
        "- La qualité live doit être validée séparément sur audio réel.",
        "- Une interruption doit être reprise avec `--resume-run`.",
        "",
    ]
    result_path.write_text("\n".join(lines), encoding="utf-8")
    return result_path


def main() -> int:
    os.environ.setdefault("PYTHONUNBUFFERED", "1")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--prepare-data", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--resume-run", type=Path)
    parser.add_argument("--initial-checkpoint", type=Path)
    parser.add_argument("--smoke-test", action="store_true")
    parser.add_argument(
        "--representative-smoke",
        action="store_true",
        help="Exercise every train/validation recording during the smoke.",
    )
    parser.add_argument(
        "--smoke-examples", type=int, default=DEFAULT_SMOKE_EXAMPLES
    )
    parser.add_argument(
        "--smoke-validation-examples",
        type=int,
        default=DEFAULT_SMOKE_VALIDATION_EXAMPLES,
    )
    parser.add_argument(
        "--log-every-batches",
        type=int,
        default=DEFAULT_LOG_EVERY_BATCHES,
    )
    parser.add_argument(
        "--maximum-runtime-minutes",
        type=float,
        help=(
            "Hard training budget. Defaults to 30 minutes for a smoke and "
            "600 minutes for a full train."
        ),
    )
    parser.add_argument(
        "--skip-post-train",
        action="store_true",
        help="Skip validation ranking, musical selection and TFLite export.",
    )
    args = parser.parse_args()

    os.chdir(ROOT)
    config_path = args.config.resolve()
    _require_inputs(config_path, args.prepare_data)
    branch = _branch()
    commit = _commit()
    gpu_names = _gpu_names()
    free_gib = _free_gib()
    validate_cloud_context(
        platform_name=os.name,
        branch=branch,
        gpu_names=gpu_names,
        free_gib=free_gib,
        minimum_free_gib=(
            MINIMUM_FREE_GIB
            if args.prepare_data
            else MINIMUM_STAGED_TRAIN_FREE_GIB
        ),
    )
    print(json.dumps({
        "branch": branch,
        "commit": commit,
        "gpus": gpu_names,
        "free_gib": round(free_gib, 2),
    }, indent=2), flush=True)

    if args.prepare_data:
        _run((
            sys.executable,
            "scripts/data/rebuild_processed.py",
            "--workers",
            str(args.workers),
        ))

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    started_at = datetime.now(timezone.utc).isoformat()
    train_command = [
        sys.executable,
        "-m",
        "src.polyphonic.train",
        "--config",
        str(config_path),
    ]
    if args.resume_run is not None:
        train_command.extend((
            "--resume-run",
            str(args.resume_run.resolve()),
        ))
    if args.initial_checkpoint is not None:
        train_command.extend((
            "--initial-checkpoint",
            str(args.initial_checkpoint.resolve()),
        ))
    train_command.extend(_src_training_arguments(
        workers=args.workers,
        smoke_test=args.smoke_test,
        representative_smoke=args.representative_smoke,
        smoke_examples=args.smoke_examples,
        smoke_validation_examples=args.smoke_validation_examples,
        log_every_batches=args.log_every_batches,
        maximum_runtime_minutes=args.maximum_runtime_minutes,
    ))
    _run(train_command)
    run_dir = (
        args.resume_run.resolve()
        if args.resume_run is not None
        else _latest_run(config)
    )

    artifact_dir: Path | None = None
    post_train_completed = False
    if not args.skip_post_train and not args.smoke_test:
        _run((
            sys.executable,
            "-m",
            "src.polyphonic.rank_checkpoints",
            "--run-dir",
            str(run_dir),
            "--maximum-examples",
            "60000",
            "--checkpoint-glob",
            "epochs/epoch-*.keras",
        ))
        _run((
            sys.executable,
            "-m",
            "src.polyphonic.select_final_checkpoint",
            "--run-dir",
            str(run_dir),
            "--maximum-recordings",
            "12",
            "--maximum-candidates",
            "8",
        ))
        artifact_dir = (
            ROOT / "artifacts" / "generated" / run_dir.name
        )
        _run((
            sys.executable,
            "-m",
            "src.polyphonic.export",
            "--run-dir",
            str(run_dir),
            "--output-dir",
            str(artifact_dir),
            "--examples",
            "96",
        ))
        post_train_completed = True

    result_path = _write_result(
        run_dir,
        artifact_dir,
        branch,
        commit,
        started_at,
        post_train_completed,
    )
    summary = {
        "run_dir": str(run_dir),
        "artifact_dir": (
            None if artifact_dir is None else str(artifact_dir)
        ),
        "result_readme": str(result_path),
        "locked_test_used": False,
    }
    (run_dir / "cloud_pipeline.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
