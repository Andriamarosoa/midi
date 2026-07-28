"""Package the useful Kaggle outputs before the notebook workspace is cleaned.

Kaggle preserves files under ``/kaggle/working`` as notebook outputs. Keeping
the cloned repository and an extracted multi-gigabyte input there would make
result retrieval needlessly large, so this module creates one deterministic
tar archive plus a small JSON manifest outside the clone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import tarfile
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[2]


def _inside_root(path: Path, root: Path) -> Path:
    candidate = path if path.is_absolute() else root / path
    resolved = candidate.resolve()
    resolved_root = root.resolve()
    if resolved != resolved_root and resolved_root not in resolved.parents:
        raise ValueError(f"Output path escapes repository: {path}")
    if not resolved.exists():
        raise FileNotFoundError(resolved)
    return resolved


def _latest_pipeline(root: Path) -> tuple[Path, dict[str, Any]]:
    candidates = list(root.glob("runs/**/cloud_pipeline.json"))
    if not candidates:
        raise FileNotFoundError("No cloud_pipeline.json found.")
    latest = max(candidates, key=lambda path: path.stat().st_mtime_ns)
    return latest, json.loads(latest.read_text(encoding="utf-8"))


def _training_members(root: Path) -> tuple[list[tuple[Path, str]], dict[str, Any]]:
    pipeline_path, pipeline = _latest_pipeline(root)
    members: list[tuple[Path, str]] = []
    run_dir = _inside_root(Path(pipeline["run_dir"]), root)
    members.append((run_dir, f"run/{run_dir.name}"))

    artifact_value = pipeline.get("artifact_dir")
    if artifact_value:
        artifact_dir = _inside_root(Path(artifact_value), root)
        members.append((artifact_dir, f"artifacts/{artifact_dir.name}"))

    result_value = pipeline.get("result_readme")
    if result_value:
        result_path = _inside_root(Path(result_value), root)
        members.append((result_path, f"readme/results/{result_path.name}"))
    return members, {
        "pipeline": pipeline,
        "pipeline_file": str(pipeline_path.relative_to(root)),
    }


def _rebuild_members(root: Path) -> tuple[list[tuple[Path, str]], dict[str, Any]]:
    processed = _inside_root(Path("data/processed"), root)
    reports = sorted(
        str(path.relative_to(root))
        for path in processed.rglob("rebuild_report.json")
    )
    return [(processed, "data/processed")], {"rebuild_reports": reports}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def package_outputs(
    *,
    task: str,
    output_dir: Path,
    root: Path = ROOT,
) -> dict[str, Any]:
    """Create a standalone archive that can be downloaded with Kaggle CLI."""
    root = root.resolve()
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    if any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {output_dir}")

    if task == "rebuild":
        members, details = _rebuild_members(root)
    else:
        members, details = _training_members(root)

    archive_path = output_dir / f"guitar-midi-{task}-results.tar"
    with tarfile.open(archive_path, "w", format=tarfile.PAX_FORMAT) as archive:
        for source, archive_name in members:
            archive.add(source, arcname=archive_name, recursive=True)

    manifest = {
        "task": task,
        "archive": archive_path.name,
        "archive_bytes": archive_path.stat().st_size,
        "archive_sha256": _sha256(archive_path),
        "members": [
            {"source": str(source.relative_to(root)), "archive": archive_name}
            for source, archive_name in members
        ],
        "locked_test_used": False,
        **details,
    }
    manifest_path = output_dir / "output_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--task", choices=("smoke", "train", "rank", "select", "rebuild"),
        required=True,
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("/kaggle/working/guitar-midi-results"),
    )
    args = parser.parse_args()
    report = package_outputs(task=args.task, output_dir=args.output_dir)
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
