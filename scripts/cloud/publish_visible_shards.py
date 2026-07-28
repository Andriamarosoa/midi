"""Publish real-data Kaggle shards sequentially and verify every dataset.

This is deliberately sequential: a shard becomes visible in the Kaggle GUI
before the next one starts, and a failed upload never causes duplicate work.
"""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.cloud.publish_kaggle import _kaggle


def _handle(owner: str, part: int) -> str:
    return f"{owner}/guitar-midi-polyphonic-data-part-{part:02d}"


def _run(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        arguments, cwd=ROOT, text=True, capture_output=True
    )


def _ready(handle: str) -> bool:
    result = _run([_kaggle(), "datasets", "files", handle, "--format", "json"])
    return result.returncode == 0


def _write_metadata(directory: Path, owner: str, part: int) -> None:
    (directory / "dataset-metadata.json").write_text(
        json.dumps({
            "title": f"Guitar MIDI polyphonic data part {part:02d}",
            "id": _handle(owner, part),
            "licenses": [{"name": "CC-BY-4.0"}],
        }, indent=2) + "\n",
        encoding="utf-8",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--shards-root", type=Path, required=True)
    parser.add_argument("--start-part", type=int, default=1)
    parser.add_argument("--end-part", type=int, default=16)
    parser.add_argument("--wait-for-handle")
    parser.add_argument("--interval-seconds", type=int, default=60)
    args = parser.parse_args()
    if args.start_part < 1 or args.end_part < args.start_part:
        raise ValueError("Invalid part range.")
    if args.wait_for_handle:
        while not _ready(args.wait_for_handle):
            logging.info("Waiting for visible dataset: %s", args.wait_for_handle)
            time.sleep(args.interval_seconds)
    for part in range(args.start_part, args.end_part + 1):
        handle = _handle(args.owner, part)
        if _ready(handle):
            logging.info("Already visible: %s", handle)
            continue
        directory = args.shards_root / f"part-{part:02d}"
        if not (directory / "package_report.json").is_file():
            raise FileNotFoundError(directory / "package_report.json")
        _write_metadata(directory, args.owner, part)
        logging.info("Publishing %s", handle)
        result = _run([
            _kaggle(), "datasets", "create", "-p", str(directory),
            "--dir-mode", "tar",
        ])
        if result.returncode:
            raise RuntimeError(
                f"Publication failed for {handle}:\n{result.stdout}\n{result.stderr}"
            )
        if not _ready(handle):
            raise RuntimeError(f"Published but not readable: {handle}")
        logging.info("Published and verified: %s", handle)
    return 0


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    raise SystemExit(main())
