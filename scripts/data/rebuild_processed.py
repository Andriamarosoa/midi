"""Rebuild the V2.2 processed datasets from the preserved raw archives."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from zipfile import ZipFile, ZipInfo

from src.polyphonic.build_gaps import build_gaps_dataset
from src.polyphonic.build_guitar_techs import build_guitar_techs_dataset
from src.polyphonic.combine_manifests import combine
from src.polyphonic.dataset_builder import build_guitarset_dataset
from src.polyphonic.validate_dataset import validate
from src.process.harmonic import (
    DEFAULT_FRAME_SIZE,
    DEFAULT_HOP_SIZE,
    DEFAULT_MAX_HARMONICS,
    DEFAULT_SEARCH_CENTS,
    analyse,
)


ROOT = Path(__file__).resolve().parents[2]
DATA = Path("data")
PROCESSED = DATA / "processed"


def _safe_target(destination: Path, member: ZipInfo) -> Path:
    target = (destination / member.filename).resolve()
    resolved_destination = destination.resolve()
    if target != resolved_destination and resolved_destination not in target.parents:
        raise ValueError(f"Archive member escapes destination: {member.filename}")
    return target


def extract_archive(archive_path: Path, destination: Path) -> int:
    """Extract an archive idempotently without allowing path traversal."""
    extracted = 0
    with ZipFile(archive_path) as archive:
        for member in archive.infolist():
            normalized = member.filename.replace("\\", "/")
            if normalized.startswith("__MACOSX/") or normalized.endswith("/.DS_Store"):
                continue
            target = _safe_target(destination, member)
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True)
                continue
            if target.is_file() and target.stat().st_size == member.file_size:
                continue
            target.parent.mkdir(parents=True, exist_ok=True)
            with archive.open(member) as source, target.open("wb") as output:
                shutil.copyfileobj(source, output, length=1024 * 1024)
            extracted += 1
    return extracted


def prepare_raw_sources() -> dict[str, int]:
    counts = {
        "guitarset_annotations": extract_archive(
            DATA / "GuitarSet" / "annotation.zip",
            DATA / "GuitarSet" / "annotation",
        ),
        "guitarset_debleeded_audio": extract_archive(
            DATA / "GuitarSet" / "audio_hex-pickup_debleeded.zip",
            DATA / "GuitarSet" / "audio_hex-pickup_debleeded",
        ),
        "guitar_techs_archives": 0,
    }
    for archive in sorted((DATA / "Guitar-TECHS").glob("P*.zip")):
        counts["guitar_techs_archives"] += extract_archive(
            archive, DATA / "Guitar-TECHS"
        )
    return counts


def _valid_harmonic_csv(path: Path) -> bool:
    if not path.is_file() or path.stat().st_size < 200:
        return False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        header = handle.readline()
        first_row = handle.readline()
    return "harmonic_number" in header and bool(first_row.strip())


def _analyse_one(paths: tuple[str, str, str]) -> tuple[str, int, int]:
    wav_value, jams_value, output_value = paths
    wav = Path(wav_value)
    jams = Path(jams_value)
    output = Path(output_value)
    temporary = output.with_suffix(".csv.tmp")
    temporary.unlink(missing_ok=True)
    try:
        notes, rows = analyse(
            wav,
            jams,
            temporary,
            DEFAULT_MAX_HARMONICS,
            DEFAULT_FRAME_SIZE,
            DEFAULT_HOP_SIZE,
            DEFAULT_SEARCH_CENTS,
        )
        temporary.replace(output)
    finally:
        temporary.unlink(missing_ok=True)
    return wav.stem, notes, rows


def build_guitarset_harmonics(workers: int) -> dict[str, int]:
    audio_root = DATA / "GuitarSet" / "audio_hex-pickup_debleeded"
    annotation_root = DATA / "GuitarSet" / "annotation"
    jobs: list[tuple[str, str, str]] = []
    reused = 0
    for wav in sorted(audio_root.glob("*_hex_cln.wav")):
        source_id = wav.stem.removesuffix("_hex_cln")
        jams = annotation_root / f"{source_id}.jams"
        output = PROCESSED / f"{wav.stem}.csv"
        if not jams.is_file():
            raise FileNotFoundError(jams)
        if _valid_harmonic_csv(output):
            reused += 1
        else:
            jobs.append((str(wav), str(jams), str(output)))
    if reused + len(jobs) != 360:
        raise ValueError(
            f"Expected 360 GuitarSet recordings, found {reused + len(jobs)}"
        )

    completed = 0
    notes = 0
    rows = 0
    if jobs:
        # NumPy/SciPy release the GIL for the FFT-heavy work. A thread pool is
        # also compatible with restricted Windows sessions where creating the
        # multiprocessing control pipe can be denied.
        with ThreadPoolExecutor(max_workers=workers) as executor:
            futures = [executor.submit(_analyse_one, job) for job in jobs]
            for future in as_completed(futures):
                source_id, note_count, row_count = future.result()
                completed += 1
                notes += note_count
                rows += row_count
                if completed == 1 or completed % 10 == 0 or completed == len(jobs):
                    print(
                        f"Harmoniques GuitarSet: {completed}/{len(jobs)} "
                        f"(dernier: {source_id})",
                        flush=True,
                    )
    return {
        "recordings": 360,
        "reused": reused,
        "generated": completed,
        "generated_notes": notes,
        "generated_rows": rows,
    }


def rebuild_datasets() -> dict[str, object]:
    guitarset = build_guitarset_dataset(
        DATA, PROCESSED / "polyphonic_v2_0"
    )
    gaps = build_gaps_dataset(
        DATA,
        PROCESSED / "polyphonic_v2_1_gaps",
        validation_recordings=30,
        seed=42,
    )
    guitar_techs = build_guitar_techs_dataset(
        DATA, PROCESSED / "polyphonic_v2_2_guitar_techs"
    )
    combined_manifest = PROCESSED / "polyphonic_v2_2_combined" / "manifest.csv"
    combined = combine(
        [
            Path(guitarset["manifest"]),
            Path(gaps["manifest"]),
            Path(guitar_techs["manifest"]),
        ],
        combined_manifest,
    )
    validation = validate(combined_manifest)
    (combined_manifest.parent / "validation_report.json").write_text(
        json.dumps(validation, indent=2), encoding="utf-8"
    )
    if not validation.get("passed", False):
        raise ValueError("Combined dataset validation failed.")
    return {
        "guitarset": guitarset["totals"],
        "gaps": gaps["totals"],
        "guitar_techs": guitar_techs["totals"],
        "combined": combined,
        "validation": validation,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--workers",
        type=int,
        default=max(1, min(4, (os.cpu_count() or 2) - 1)),
    )
    parser.add_argument("--skip-extraction", action="store_true")
    parser.add_argument("--skip-harmonics", action="store_true")
    parser.add_argument("--prepare-only", action="store_true")
    args = parser.parse_args()
    if args.workers < 1:
        parser.error("--workers must be >= 1")

    os.chdir(ROOT)
    PROCESSED.mkdir(parents=True, exist_ok=True)
    report: dict[str, object] = {"schema_version": 1}
    if not args.skip_extraction:
        report["extraction"] = prepare_raw_sources()
    if args.prepare_only:
        print(json.dumps(report, indent=2))
        return 0
    if not args.skip_harmonics:
        report["harmonics"] = build_guitarset_harmonics(args.workers)
    report["datasets"] = rebuild_datasets()
    output = PROCESSED / "rebuild_report.json"
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))
    print(f"Rapport: {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
