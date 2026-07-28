"""Prepare a Kaggle kernel that selects from an existing rank kernel output.

The ranked checkpoints remain inside Kaggle: the selection kernel attaches the
private rank kernel as a kernel source instead of uploading the models again.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from scripts.cloud.publish_kaggle import (
    KERNEL_TEMPLATE,
    _task_notebook,
)


SELECTION_CELL = """\
if str(workspace) not in sys.path:
    sys.path.insert(0, str(workspace))
os.chdir(workspace)

from scripts.cloud.kaggle_entrypoint import (
    find_checkpoint_run,
    find_training_shard_manifests,
    stage_training_shards,
    validate_training_manifest,
)
from scripts.cloud.package_kaggle_outputs import package_outputs

rank_archives = sorted(input_root.rglob("guitar-midi-rank-results.tar"))
if len(rank_archives) != 1:
    raise RuntimeError(f"Expected one rank archive, got {rank_archives}")
rank_root = pathlib.Path("/kaggle/working/ranked-validation")
rank_root.mkdir(parents=True, exist_ok=False)
with tarfile.open(rank_archives[0], "r") as archive:
    destination = rank_root.resolve()
    for member in archive.getmembers():
        target = (rank_root / member.name).resolve()
        if target != destination and destination not in target.parents:
            raise RuntimeError(f"Rank archive escapes workspace: {member.name}")
    archive.extractall(rank_root)

shard_manifests = find_training_shard_manifests(input_root)
manifest = stage_training_shards(shard_manifests)
validation = validate_training_manifest(manifest)
source_run = find_checkpoint_run(rank_root)
run_dir = workspace / "runs/polyphonic" / source_run.name
run_dir.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source_run, run_dir)
subprocess.run([
    sys.executable,
    "-m",
    "src.polyphonic.select_final_checkpoint",
    "--run-dir",
    str(run_dir),
    "--maximum-recordings",
    str(MAXIMUM_RECORDINGS),
    "--maximum-candidates",
    str(MAXIMUM_CANDIDATES),
], cwd=workspace, check=True)

pipeline = {
    "task": "select",
    "run_dir": str(run_dir),
    "artifact_dir": None,
    "result_readme": None,
    "locked_test_used": False,
}
(run_dir / "cloud_pipeline.json").write_text(
    json.dumps(pipeline, indent=2) + "\\n", encoding="utf-8"
)
output_dir = pathlib.Path("/kaggle/working/guitar-midi-results")
result = package_outputs(
    task="select", output_dir=output_dir, root=workspace
)
print(json.dumps({
    "task": "select",
    "run_dir": str(run_dir),
    "validation": validation,
    "selection": json.loads(
        (run_dir / "selection.json").read_text(encoding="utf-8")
    ),
    "output": result,
}, indent=2))
"""


def prepare_selection_kernel(
    *,
    output_dir: Path,
    owner: str,
    kernel_slug: str,
    source_dataset: str,
    data_datasets: list[str],
    rank_kernel: str,
) -> str:
    """Write one private, GPU-enabled validation-only selection kernel."""
    if output_dir.exists():
        raise FileExistsError(output_dir)
    if not data_datasets:
        raise ValueError("At least one training/validation shard is required.")
    notebook = _task_notebook(
        "select",
        source_dataset_slug=source_dataset.split("/", 1)[1],
        maximum_recordings=12,
        maximum_candidates=8,
    )
    execution_cells = [
        cell
        for cell in notebook["cells"]
        if cell.get("cell_type") == "code"
        and any(
            line.startswith("command = [")
            for line in cell.get("source", [])
        )
    ]
    if len(execution_cells) != 1:
        raise ValueError("Expected one pipeline execution cell.")
    execution_cells[0]["source"] = SELECTION_CELL.splitlines(keepends=True)

    output_dir.mkdir(parents=True)
    notebook_name = "polyphonic_select.ipynb"
    (output_dir / notebook_name).write_text(
        json.dumps(notebook, indent=1, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    metadata = json.loads(KERNEL_TEMPLATE.read_text(encoding="utf-8"))
    metadata.update({
        "id": f"{owner}/{kernel_slug}",
        "title": kernel_slug.replace("-", " "),
        "code_file": notebook_name,
        "dataset_sources": [*data_datasets, source_dataset],
        "kernel_sources": [rank_kernel],
    })
    (output_dir / "kernel-metadata.json").write_text(
        json.dumps(metadata, indent=2) + "\n", encoding="utf-8"
    )
    return str(metadata["id"])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--kernel-slug", required=True)
    parser.add_argument("--source-dataset", required=True)
    parser.add_argument("--data-dataset", action="append", required=True)
    parser.add_argument("--rank-kernel", required=True)
    args = parser.parse_args()
    kernel = prepare_selection_kernel(
        output_dir=args.output_dir,
        owner=args.owner,
        kernel_slug=args.kernel_slug,
        source_dataset=args.source_dataset,
        data_datasets=args.data_dataset,
        rank_kernel=args.rank_kernel,
    )
    print(json.dumps({"kernel": kernel, "task": "select"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
