"""Publish private Kaggle datasets and GPU notebooks with the official CLI.

Authentication is intentionally delegated to ``kaggle auth login``. Dataset
creation omits ``--public`` so the input remains private.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tarfile
import re
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]
NOTEBOOK = ROOT / "kaggle/polyphonic_pipeline.ipynb"
KERNEL_TEMPLATE = ROOT / "kaggle/kernel-metadata.template.json"


def _kaggle() -> str:
    candidates = [
        Path(sys.executable).with_name("kaggle.exe"),
        Path(sys.executable).with_name("kaggle"),
    ]
    executable = next(
        (str(path) for path in candidates if path.is_file()),
        shutil.which("kaggle"),
    )
    if executable is None:
        raise RuntimeError(
            "Kaggle CLI missing. Install requirements/kaggle-upload.txt "
            "with Python 3.11+."
        )
    return executable


def _run(command: list[str]) -> None:
    print("+ " + " ".join(command), flush=True)
    subprocess.run(
        command, cwd=ROOT, check=True
    )


def _read_package_report(dataset_dir: Path) -> dict[str, Any]:
    report_path = dataset_dir / "package_report.json"
    if not report_path.is_file():
        raise FileNotFoundError(report_path)
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if report.get("passed") is not True:
        raise ValueError("Kaggle package validation did not pass.")
    if (
        report.get("kind") == "polyphonic_train_validation"
        and report.get("locked_test_included") is not False
    ):
        raise ValueError("The locked test must not enter the training dataset.")
    if report.get("kind") == "polyphonic_train_validation":
        visible_shard = (
            report.get("kaggle_visible_shard") is True
            or re.fullmatch(r"part-\d{2}", dataset_dir.name) is not None
        )
        if visible_shard:
            unsafe_paths = [
                path.relative_to(dataset_dir).as_posix()
                for path in dataset_dir.rglob("*")
                if "#" in path.name
            ]
            if unsafe_paths:
                raise ValueError(
                    "Unsafe path in visible data shard: " + unsafe_paths[0]
                )
        elif report.get("archive_format") != "kaggle_chunked_tar_v1":
            raise ValueError(
                "Refusing legacy single-TAR training upload; rebuild chunked archives."
            )
        if visible_shard:
            return report
        index_name = report.get("archive_index")
        if not isinstance(index_name, str):
            raise ValueError("Chunked training package has no archive index.")
        index_path = dataset_dir / index_name
        if not index_path.is_file():
            raise FileNotFoundError(index_path)
        index = json.loads(index_path.read_text(encoding="utf-8"))
        if index.get("format") != "kaggle_chunked_tar_v1":
            raise ValueError("Unsupported chunked training archive format.")
        archives = index.get("archives")
        if not isinstance(archives, list) or not archives:
            raise ValueError("Chunked training package contains no TAR files.")
        for item in archives:
            archive_name = item.get("name")
            if not isinstance(archive_name, str) or "/" in archive_name:
                raise ValueError("Invalid chunked archive name.")
            archive_path = dataset_dir / archive_name
            if not archive_path.is_file():
                raise FileNotFoundError(archive_path)
            with tarfile.open(archive_path, "r") as archive:
                names = archive.getnames()
            if not names or any(
                "#" in name or not name.startswith("parts/")
                for name in names
            ):
                raise ValueError(
                    f"Unsafe member name in chunked archive: {archive_name}"
                )
    return report


def publish_dataset(
    *,
    dataset_dir: Path,
    handle: str,
    title: str,
    new_version: bool,
    version_notes: str,
) -> None:
    if handle.count("/") != 1:
        raise ValueError("Dataset handle must be USERNAME/SLUG.")
    dataset_dir = dataset_dir.resolve()
    _read_package_report(dataset_dir)
    metadata = {
        "title": title,
        "id": handle,
        "licenses": [{"name": "CC-BY-4.0"}],
    }
    (dataset_dir / "dataset-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    if new_version:
        _run([
            _kaggle(), "datasets", "version",
            "-p", str(dataset_dir), "-m", version_notes,
        ])
    else:
        # Kaggle datasets are private by default; --public is not used.
        _run([
            _kaggle(), "datasets", "create", "-p", str(dataset_dir),
            "--dir-mode", "tar",
        ])


def _task_notebook(
    task: str,
    *,
    source_dataset_slug: str = "",
    maximum_examples: int = 60_000,
) -> dict[str, Any]:
    if maximum_examples < 1:
        raise ValueError("maximum_examples must be positive.")
    notebook = json.loads(NOTEBOOK.read_text(encoding="utf-8"))
    task_replaced = False
    source_replaced = False
    maximum_replaced = False
    for cell in notebook["cells"]:
        if cell.get("cell_type") != "code":
            continue
        source = cell.get("source", [])
        for index, line in enumerate(source):
            if line.startswith("TASK = "):
                source[index] = (
                    f'TASK = "{task}"  # smoke, train, rank ou rebuild\n'
                )
                task_replaced = True
            elif line.startswith("SOURCE_DATASET_SLUG = "):
                source[index] = (
                    f"SOURCE_DATASET_SLUG = {json.dumps(source_dataset_slug)} "
                    "# injecté par le publisher Kaggle\n"
                )
                source_replaced = True
            elif line.startswith("MAXIMUM_EXAMPLES = "):
                source[index] = (
                    f"MAXIMUM_EXAMPLES = {int(maximum_examples)}\n"
                )
                maximum_replaced = True
    if not task_replaced:
        raise ValueError("TASK cell not found in Kaggle notebook.")
    if not source_replaced:
        raise ValueError(
            "SOURCE_DATASET_SLUG cell not found in Kaggle notebook."
        )
    if not maximum_replaced:
        raise ValueError(
            "MAXIMUM_EXAMPLES cell not found in Kaggle notebook."
        )
    return notebook


def publish_kernel(
    *,
    owner: str,
    dataset_handles: list[str],
    task: str,
    output_dir: Path,
    kernel_slug: str | None = None,
    accelerator: str = "NvidiaTeslaP100",
    maximum_examples: int = 60_000,
) -> str:
    if "/" in owner or not owner:
        raise ValueError("Owner must be a Kaggle username.")
    if not dataset_handles:
        raise ValueError("At least one dataset handle is required.")
    if any(handle.count("/") != 1 for handle in dataset_handles):
        raise ValueError("Dataset handles must be USERNAME/SLUG.")
    if len(set(dataset_handles)) != len(dataset_handles):
        raise ValueError("Dataset handles must be unique.")
    source_handles = [
        handle
        for handle in dataset_handles
        if "/guitar-midi-polyphonic-code-" in handle
    ]
    if len(source_handles) != 1:
        raise ValueError(
            "Exactly one guitar-midi-polyphonic-code source dataset "
            "must be attached."
        )
    source_dataset_slug = source_handles[0].split("/", 1)[1]
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(
            f"Kernel staging already exists: {output_dir}"
        )
    output_dir.mkdir(parents=True)
    notebook_name = f"polyphonic_{task}.ipynb"
    (output_dir / notebook_name).write_text(
        json.dumps(
            _task_notebook(
                task,
                source_dataset_slug=source_dataset_slug,
                maximum_examples=maximum_examples,
            ),
            indent=1,
            ensure_ascii=False,
        )
        + "\n",
        encoding="utf-8",
    )
    metadata = json.loads(KERNEL_TEMPLATE.read_text(encoding="utf-8"))
    slug = kernel_slug or f"guitar-midi-polyphonic-{task}"
    if "/" in slug or not slug:
        raise ValueError("Kernel slug must not be empty or contain '/'.")
    metadata.update({
        "id": f"{owner}/{slug}",
        # Kaggle derives the actual URL slug from the title. Keep both aligned
        # so status/output commands use the identifier returned here.
        "title": slug.replace("-", " "),
        "code_file": notebook_name,
        "dataset_sources": dataset_handles,
    })
    (output_dir / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    _run([
        _kaggle(), "kernels", "push",
        "-p", str(output_dir),
        "--accelerator", accelerator,
    ])
    return str(metadata["id"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    dataset = subparsers.add_parser("dataset")
    dataset.add_argument("--dataset-dir", type=Path, required=True)
    dataset.add_argument("--handle", required=True)
    dataset.add_argument("--title", required=True)
    dataset.add_argument("--new-version", action="store_true")
    dataset.add_argument(
        "--version-notes", default="Updated validated input package."
    )

    kernel = subparsers.add_parser("kernel")
    kernel.add_argument("--owner", required=True)
    kernel.add_argument(
        "--dataset-handle",
        action="append",
        dest="dataset_handles",
        required=True,
        help="Attach one private dataset. Repeat for multi-shard inputs.",
    )
    kernel.add_argument(
        "--kernel-slug",
        help="Optional unique Kaggle kernel slug; defaults to the task name.",
    )
    kernel.add_argument(
        "--task", choices=("smoke", "train", "rank", "rebuild"),
        required=True,
    )
    kernel.add_argument(
        "--output-dir", type=Path, default=Path("tmp/kaggle/kernel")
    )
    kernel.add_argument(
        "--accelerator",
        choices=("NvidiaTeslaP100", "NvidiaTeslaT4"),
        default="NvidiaTeslaP100",
        help="Kaggle GPU shape; P100 remains the default.",
    )
    kernel.add_argument(
        "--maximum-examples",
        type=int,
        default=60_000,
        help="Maximum validation examples for rank; defaults to 60000.",
    )

    args = parser.parse_args()
    if args.command == "dataset":
        publish_dataset(
            dataset_dir=args.dataset_dir,
            handle=args.handle,
            title=args.title,
            new_version=args.new_version,
            version_notes=args.version_notes,
        )
    else:
        kernel_id = publish_kernel(
            owner=args.owner,
            dataset_handles=args.dataset_handles,
            task=args.task,
            output_dir=args.output_dir,
            kernel_slug=args.kernel_slug,
            accelerator=args.accelerator,
            maximum_examples=args.maximum_examples,
        )
        print(json.dumps({"kernel": kernel_id, "task": args.task}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
