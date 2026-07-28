"""Build a small private Kaggle dataset containing the tracked source tree."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def _git(*arguments: str) -> str:
    result = subprocess.run(
        ("git", *arguments),
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def prepare_source_dataset(
    *, output_dir: Path, handle: str, title: str
) -> dict[str, object]:
    if handle.count("/") != 1:
        raise ValueError("Dataset handle must be OWNER/SLUG.")
    output_dir = output_dir.resolve()
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    branch = _git("branch", "--show-current")
    commit = _git("rev-parse", "HEAD")
    if not branch or branch in {"main", "master"}:
        raise ValueError("A non-main experiment branch is required.")
    archive = output_dir / "midi_source.tar.gz"
    subprocess.run(
        (
            "git",
            "archive",
            "--format=tar.gz",
            f"--output={archive}",
            commit,
        ),
        cwd=ROOT,
        check=True,
    )
    source_metadata = {
        "schema_version": 1,
        "branch": branch,
        "commit": commit,
        "archive": archive.name,
        "archive_bytes": archive.stat().st_size,
        "datasets_included": False,
        "locked_test_included": False,
    }
    (output_dir / "source_metadata.json").write_text(
        json.dumps(source_metadata, indent=2) + "\n", encoding="utf-8"
    )
    (output_dir / "dataset-metadata.json").write_text(
        json.dumps(
            {
                "title": title,
                "id": handle,
                "licenses": [{"name": "CC-BY-4.0"}],
            },
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return source_metadata


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--handle", required=True)
    parser.add_argument("--title", required=True)
    args = parser.parse_args()
    report = prepare_source_dataset(
        output_dir=args.output_dir,
        handle=args.handle,
        title=args.title,
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
