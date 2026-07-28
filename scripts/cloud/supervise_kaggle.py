"""Resume-safe supervisor for the private Kaggle GPU pipeline.

The supervisor waits for the train/validation dataset currently being
uploaded, starts a private raw-source upload in parallel with the GPU work,
runs the smoke notebook, validates its downloadable output, then starts the
full training notebook. Existing datasets, kernels and valid downloads are
never relaunched.
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Sequence

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cloud.publish_kaggle import KAGGLE_CONFIG, _kaggle
from scripts.project_summary import update_project_summary


TERMINAL_FAILURES = {
    "error",
    "cancelAcknowledged",
    "cancelled",
    "failed",
}
STATUS_PATTERN = re.compile(r'status\s+"([^"]+)"', re.IGNORECASE)


def _environment() -> dict[str, str]:
    environment = dict(os.environ)
    environment["KAGGLE_CONFIG_DIR"] = str(KAGGLE_CONFIG)
    return environment


def _command(
    arguments: Sequence[str], *, check: bool = False
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        list(arguments),
        cwd=ROOT,
        env=_environment(),
        text=True,
        capture_output=True,
    )
    if check and result.returncode:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(arguments)}\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return result


def dataset_ready(handle: str) -> bool:
    result = _command((
        _kaggle(), "datasets", "files", handle, "--format", "json"
    ))
    return result.returncode == 0


def kernel_status(handle: str) -> str | None:
    result = _command((_kaggle(), "kernels", "status", handle))
    if result.returncode:
        error = result.stdout + "\n" + result.stderr
        if "404" in error or "not found" in error.lower():
            return None
        raise RuntimeError(
            f"Cannot query Kaggle kernel {handle}: {error.strip()}"
        )
    match = STATUS_PATTERN.search(result.stdout + "\n" + result.stderr)
    if not match:
        raise RuntimeError(
            f"Unrecognized Kaggle status response for {handle}: "
            f"{result.stdout} {result.stderr}"
        )
    return match.group(1)


def _write_state(path: Path, **values: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    existing = (
        json.loads(path.read_text(encoding="utf-8"))
        if path.is_file()
        else {}
    )
    existing.update(values)
    existing["updated_at_utc"] = datetime.now(timezone.utc).isoformat()
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(existing, indent=2) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def _record_summary(
    path: Path,
    *,
    phase: str,
    status: str,
    detail: str,
    next_steps: Sequence[str],
) -> None:
    update_project_summary(
        phase=phase,
        status=status,
        detail=detail,
        next_steps=next_steps,
        summary_path=path,
    )


def wait_for_dataset(
    handle: str, *, interval_seconds: int, timeout_seconds: int
) -> None:
    deadline = time.monotonic() + timeout_seconds
    while not dataset_ready(handle):
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Dataset did not become ready: {handle}")
        logging.info("Dataset not ready yet: %s", handle)
        time.sleep(interval_seconds)
    logging.info("Dataset ready: %s", handle)


def _start_raw_upload(
    *, raw_dir: Path, handle: str, title: str, log_path: Path
) -> subprocess.Popen[str] | None:
    if dataset_ready(handle):
        logging.info("Raw dataset already exists: %s", handle)
        return None
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_handle = log_path.open("a", encoding="utf-8")
    command = [
        sys.executable,
        "scripts/cloud/publish_kaggle.py",
        "dataset",
        "--dataset-dir",
        str(raw_dir),
        "--handle",
        handle,
        "--title",
        title,
    ]
    logging.info("Starting private raw dataset upload: %s", handle)
    return subprocess.Popen(
        command,
        cwd=ROOT,
        env=_environment(),
        text=True,
        stdout=log_handle,
        stderr=subprocess.STDOUT,
    )


def _launch_kernel(
    *, owner: str, dataset_handle: str, task: str
) -> str:
    kernel = f"{owner}/guitar-midi-polyphonic-{task}"
    status = kernel_status(kernel)
    if status is not None:
        logging.info("Kernel already exists: %s (%s)", kernel, status)
        return kernel
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    staging = ROOT / "tmp/kaggle" / f"kernel-{task}-{stamp}"
    _command((
        sys.executable,
        "scripts/cloud/publish_kaggle.py",
        "kernel",
        "--owner",
        owner,
        "--dataset-handle",
        dataset_handle,
        "--task",
        task,
        "--output-dir",
        str(staging),
    ), check=True)
    logging.info("Kernel submitted: %s", kernel)
    return kernel


def _wait_for_kernel(
    handle: str, *, interval_seconds: int, timeout_seconds: int
) -> None:
    deadline = time.monotonic() + timeout_seconds
    previous: str | None = None
    while True:
        status = kernel_status(handle)
        if status != previous:
            logging.info("Kernel %s status: %s", handle, status)
            previous = status
        if status == "complete":
            return
        if status in TERMINAL_FAILURES:
            raise RuntimeError(f"Kernel {handle} ended with status {status}.")
        if time.monotonic() >= deadline:
            raise TimeoutError(f"Kernel did not finish in time: {handle}")
        time.sleep(interval_seconds)


def _valid_download(output_dir: Path, task: str) -> bool:
    manifests = list(output_dir.rglob("output_manifest.json"))
    if len(manifests) != 1:
        return False
    report = json.loads(manifests[0].read_text(encoding="utf-8"))
    archive = manifests[0].parent / report.get("archive", "")
    return (
        report.get("task") == task
        and report.get("locked_test_used") is False
        and archive.is_file()
        and archive.stat().st_size == report.get("archive_bytes")
    )


def _download_and_validate(
    *, kernel: str, task: str, output_dir: Path
) -> None:
    if _valid_download(output_dir, task):
        logging.info("Valid %s output already downloaded.", task)
        return
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(
            f"Refusing to overwrite incomplete output: {output_dir}"
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    _command((
        _kaggle(), "kernels", "output", kernel,
        "-p", str(output_dir), "-o",
    ), check=True)
    if not _valid_download(output_dir, task):
        raise RuntimeError(f"Downloaded {task} output is invalid.")
    logging.info("Downloaded and validated %s output: %s", task, output_dir)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--training-dataset", required=True)
    parser.add_argument("--raw-dataset", required=True)
    parser.add_argument("--raw-dir", type=Path, required=True)
    parser.add_argument(
        "--state", type=Path,
        default=Path("tmp/kaggle/supervisor_state.json"),
    )
    parser.add_argument(
        "--summary", type=Path, default=Path("readme/README.md")
    )
    parser.add_argument(
        "--log-file", type=Path,
        default=Path("tmp/kaggle/supervisor.stderr.log"),
    )
    parser.add_argument("--interval-seconds", type=int, default=60)
    parser.add_argument("--dataset-timeout-hours", type=float, default=6.0)
    parser.add_argument("--smoke-timeout-hours", type=float, default=1.0)
    parser.add_argument("--train-timeout-hours", type=float, default=12.0)
    args = parser.parse_args()

    log_file = args.log_file.resolve()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=(
            logging.StreamHandler(),
            logging.FileHandler(log_file, mode="a", encoding="utf-8"),
        ),
    )
    state = args.state.resolve()
    summary = args.summary.resolve()
    _write_state(state, phase="waiting_training_dataset")
    _record_summary(
        summary,
        phase="waiting_training_dataset",
        status="en cours",
        detail=(
            "upload privé du dataset train/validation Kaggle ; "
            "le superviseur attend sa finalisation"
        ),
        next_steps=(
            "Finaliser et vérifier le dataset privé train/validation.",
            "Démarrer l’upload privé des sources brutes.",
            "Exécuter le smoke test sur GPU P100.",
            "Valider le résultat avant tout train complet.",
        ),
    )
    wait_for_dataset(
        args.training_dataset,
        interval_seconds=args.interval_seconds,
        timeout_seconds=int(args.dataset_timeout_hours * 3600),
    )
    _write_state(state, phase="training_dataset_ready")
    _record_summary(
        summary,
        phase="training_dataset_ready",
        status="terminé",
        detail="dataset privé train/validation finalisé et lisible sur Kaggle",
        next_steps=(
            "Démarrer l’upload privé des sources brutes.",
            "Soumettre le smoke test GPU P100.",
        ),
    )

    raw_process = _start_raw_upload(
        raw_dir=args.raw_dir.resolve(),
        handle=args.raw_dataset,
        title="Guitar MIDI raw sources",
        log_path=ROOT / "tmp/kaggle/raw_dataset_upload.log",
    )
    _write_state(
        state,
        phase="smoke_submitting",
        raw_upload_pid=None if raw_process is None else raw_process.pid,
    )
    _record_summary(
        summary,
        phase="smoke_submitting",
        status="en cours",
        detail=(
            "upload brut lancé ou déjà présent ; soumission du smoke test P100"
        ),
        next_steps=(
            "Attendre la fin du smoke test.",
            "Télécharger et valider son paquet de résultats.",
        ),
    )

    smoke = _launch_kernel(
        owner=args.owner,
        dataset_handle=args.training_dataset,
        task="smoke",
    )
    _write_state(state, phase="smoke_running", smoke_kernel=smoke)
    _record_summary(
        summary,
        phase="smoke_running",
        status="en cours",
        detail=f"smoke test Kaggle actif : `{smoke}`",
        next_steps=(
            "Vérifier le statut Kaggle.",
            "Télécharger et valider le paquet de sortie.",
        ),
    )
    _wait_for_kernel(
        smoke,
        interval_seconds=args.interval_seconds,
        timeout_seconds=int(args.smoke_timeout_hours * 3600),
    )
    smoke_output = ROOT / "tmp/kaggle/results/smoke"
    _download_and_validate(
        kernel=smoke, task="smoke", output_dir=smoke_output
    )
    _write_state(state, phase="smoke_passed")
    _record_summary(
        summary,
        phase="smoke_passed",
        status="terminé",
        detail="smoke test P100 réussi et paquet de sortie validé localement",
        next_steps=(
            "Décider si le train inchangé doit être évité comme doublon.",
            "Sinon soumettre le train complet.",
        ),
    )

    train = _launch_kernel(
        owner=args.owner,
        dataset_handle=args.training_dataset,
        task="train",
    )
    _write_state(state, phase="train_running", train_kernel=train)
    _record_summary(
        summary,
        phase="train_running",
        status="en cours",
        detail=f"train polyphonique complet actif : `{train}`",
        next_steps=(
            "Surveiller les époques et l’early stopping.",
            "Télécharger puis valider les checkpoints et rapports.",
        ),
    )
    _wait_for_kernel(
        train,
        interval_seconds=args.interval_seconds,
        timeout_seconds=int(args.train_timeout_hours * 3600),
    )
    train_output = ROOT / "tmp/kaggle/results/train"
    _download_and_validate(
        kernel=train, task="train", output_dir=train_output
    )
    _write_state(state, phase="train_passed")
    _record_summary(
        summary,
        phase="train_passed",
        status="terminé",
        detail="train Kaggle terminé et paquet de résultats validé localement",
        next_steps=(
            "Finaliser l’upload brut s’il est encore actif.",
            "Comparer le résultat au V2.2 précédent sans ouvrir le test.",
        ),
    )

    if raw_process is not None:
        logging.info("Waiting for raw dataset upload (PID %s).", raw_process.pid)
        raw_return_code = raw_process.wait()
        if raw_return_code:
            raise RuntimeError(
                f"Raw dataset upload failed with code {raw_return_code}."
            )
    wait_for_dataset(
        args.raw_dataset,
        interval_seconds=args.interval_seconds,
        timeout_seconds=int(args.dataset_timeout_hours * 3600),
    )
    _write_state(state, phase="complete", raw_dataset_ready=True)
    _record_summary(
        summary,
        phase="complete",
        status="terminé",
        detail=(
            "datasets privés disponibles, smoke et train terminés, "
            "résultats téléchargés et validés"
        ),
        next_steps=(
            "Comparer les résultats validation-only.",
            "Documenter les limites et décider du prochain changement unique.",
        ),
    )
    logging.info("Kaggle pipeline completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
