"""Build the metadata-only H18 fresh-discovery population audit.

This helper deliberately reads only CSV/JSON/text provenance.  For candidate
assets it checks path existence; it never opens audio, labels, or checkpoints.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path


H17_COMMIT = "3a3e65ab532a4983fadae89c842b544228c3b028"
H17_CONTRACT = Path(
    "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json"
)
H8_COHORT = Path(
    "configs/provisional_resolution_age1_persistence_h8_selected_cohort.json"
)
V2_PROTOCOL = Path(
    "configs/causal_candidate_fit_v2_independent_validation_protocol.json"
)
CHECKPOINT_SHA256 = (
    "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
)
MANIFEST_SHA256 = (
    "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
)
GROUPING_BLOB = "e43187b4e8ba0775a74114faf406703dd6c3187c"
MINIMUM_GROUPS = 20


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical_identifier(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", str(value).strip()).encode(
        "ascii", "ignore"
    ).decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", normalized.lower()).strip("_")


def _leakage_group_key(row: dict[str, str]) -> str:
    dataset = _canonical_identifier(row["dataset_id"])
    if dataset.startswith("guitarset"):
        family = "guitarset"
    elif dataset.startswith("gaps"):
        family = "gaps"
    elif "guitar" in dataset and "tech" in dataset:
        family = "guitar_techs"
    else:
        family = dataset
    player = _canonical_identifier(row["player_id"])
    group = _canonical_identifier(row["group_id"])
    if family == "guitarset":
        if not player:
            raise RuntimeError("GuitarSet row has no player_id.")
        return f"guitarset:player:{player}"
    if family == "gaps":
        unavailable = {
            "", "unknown", "gaps_unknown", "unknown_player", "na", "n_a",
            "none", "null",
        }
        if player not in unavailable:
            return f"gaps:player:{player}"
        if not group:
            raise RuntimeError("GAPS row has no usable player_id or group_id.")
        return f"gaps:group:{group}"
    if not group:
        raise RuntimeError(f"{row['dataset_id']!r} row has no group_id.")
    return f"{family}:group:{group}"


def _recording_key(row: dict[str, str]) -> str:
    return "|".join(
        (row["dataset_id"], row["group_id"], row["source_id"], row["capture_id"])
    )


def _git_blob(repo: Path, path: Path) -> str:
    result = subprocess.run(
        ["git", "hash-object", path.as_posix()],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _git_blob_at(repo: Path, commit: str, path: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", f"{commit}:{path.as_posix()}"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def build(repo: Path, manifest: Path) -> dict[str, object]:
    manifest_raw = manifest.read_bytes()
    if _sha256(manifest_raw) != MANIFEST_SHA256:
        raise RuntimeError("H18 source manifest SHA-256 mismatch.")
    rows = list(csv.DictReader(manifest_raw.decode("utf-8-sig").splitlines()))
    if len(rows) != 754 or Counter(row["split"] for row in rows) != {
        "train": 572,
        "validation": 182,
    }:
        raise RuntimeError("H18 source manifest population mismatch.")

    h17_path = repo / H17_CONTRACT
    h8_path = repo / H8_COHORT
    v2_path = repo / V2_PROTOCOL
    h17_raw = h17_path.read_bytes()
    h8_raw = h8_path.read_bytes()
    v2_raw = v2_path.read_bytes()
    h8 = json.loads(h8_raw)

    h8_groups = {row["leakage_group_key"] for row in h8["recordings"]}
    v2_groups = set(
        h8["forbidden_cohorts"]["consumed_v2"]["leakage_group_keys"]
    )
    locked_groups = set(
        h8["forbidden_cohorts"]["locked_test"]["leakage_group_keys"]
    )
    fit_groups = {
        _leakage_group_key(row) for row in rows if row["split"] == "train"
    }

    candidates: list[dict[str, str]] = []
    missing: list[str] = []
    for row in rows:
        audio = Path(row["audio_path"])
        labels = Path(row["labels_path"])
        if row["audio_path"] and row["labels_path"] and audio.exists() and labels.exists():
            candidates.append(row)
        else:
            missing.append(_recording_key(row))
    if missing:
        raise RuntimeError("H18 candidate universe has missing declared assets.")

    candidate_groups = {_leakage_group_key(row) for row in candidates}
    forbidden = {
        "h8_consumed": h8_groups,
        "consumed_independent_v2": v2_groups,
        "locked_test": locked_groups,
        "checkpoint_fit": fit_groups,
    }
    fresh_groups = candidate_groups.difference(*forbidden.values())

    by_group: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in candidates:
        by_group[_leakage_group_key(row)].append(row)

    group_membership = []
    for group in sorted(candidate_groups):
        reasons = sorted(name for name, values in forbidden.items() if group in values)
        group_membership.append(
            {
                "leakage_group_key": group,
                "exclusion_reasons": reasons,
                "fresh": not reasons,
            }
        )

    fresh_detail = []
    for group in sorted(fresh_groups):
        group_rows = sorted(by_group[group], key=_recording_key)
        fresh_detail.append(
            {
                "leakage_group_key": group,
                "recording_count": len(group_rows),
                "corpus_categories": sorted({row["dataset_id"] for row in group_rows}),
                "capture_ids": sorted({row["capture_id"] for row in group_rows}),
                "shared_capture_relationship": len(group_rows) > 1,
                "recordings": [
                    {
                        "recording_key": _recording_key(row),
                        "dataset_id": row["dataset_id"],
                        "source_id": row["source_id"],
                        "group_id": row["group_id"],
                        "capture_id": row["capture_id"],
                        "split": row["split"],
                        "audio_member": row["audio_member"],
                    }
                    for row in group_rows
                ],
            }
        )

    fresh_recordings = [
        row for row in candidates if _leakage_group_key(row) in fresh_groups
    ]
    status = (
        "fresh_discovery_population_established"
        if len(fresh_groups) >= MINIMUM_GROUPS
        else "fresh_discovery_population_not_established"
    )
    return {
        "schema_version": 1,
        "purpose": "provisional_resolution_frame_fallback_h18_metadata_audit",
        "status": status,
        "h17": {
            "commit": H17_COMMIT,
            "contract_path": H17_CONTRACT.as_posix(),
            "contract_sha256": _sha256(h17_raw),
            "contract_git_blob": _git_blob(repo, H17_CONTRACT),
        },
        "grouping": {
            "function": "src.polyphonic.decoder_candidate_provenance.leakage_group_key",
            "git_blob": GROUPING_BLOB,
        },
        "source_metadata": {
            "manifest": {
                "logical_path": "data/processed/polyphonic_harmonic_presence_v1/manifest_train_validation.csv",
                "sha256": _sha256(manifest_raw),
                "size_bytes": len(manifest_raw),
                "row_count": len(rows),
            },
            "h8_cohort": {
                "path": H8_COHORT.as_posix(),
                "sha256": _sha256(h8_raw),
                "size_bytes": len(h8_raw),
            },
            "independent_v2_protocol": {
                "path": V2_PROTOCOL.as_posix(),
                "sha256": _sha256(v2_raw),
                "size_bytes": len(v2_raw),
            },
        },
        "checkpoint_fit_provenance": {
            "checkpoint_sha256": CHECKPOINT_SHA256,
            "historical_run": "polyphonic_dual_stream_bass_harmonic_presence_20260801_195145",
            "checkpoint_name": "epoch-07.keras",
            "fit_manifest_sha256": MANIFEST_SHA256,
            "fit_partition": "train",
            "fit_recording_count": 572,
            "fit_leakage_group_count": len(fit_groups),
            "fit_leakage_group_keys": sorted(fit_groups),
            "evidence": {
                "versioned_readme_path": "readme/README.md",
                "versioned_readme_git_blob": _git_blob_at(
                    repo, H17_COMMIT, Path("readme/README.md")
                ),
                "statement": "The accepted H17 parent records this exact epoch-07 checkpoint, run, full 572-row train split, and manifest SHA; the exact groups are derived from those train rows with the frozen grouping blob.",
            },
            "exact_group_provenance_established": True,
        },
        "candidate_universe": {
            "rule": "all manifest rows whose declared audio_path and labels_path both exist; existence only, no asset opened",
            "recording_count": len(candidates),
            "leakage_group_count": len(candidate_groups),
            "missing_declared_asset_recording_count": len(missing),
            "recordings_by_split": dict(sorted(Counter(row["split"] for row in candidates).items())),
            "recordings_by_corpus_category": dict(
                sorted(Counter(row["dataset_id"] for row in candidates).items())
            ),
        },
        "forbidden_group_sets": {
            name: {"count": len(values), "leakage_group_keys": sorted(values)}
            for name, values in forbidden.items()
        },
        "set_intersections": {
            "candidate_and_h8": len(candidate_groups & h8_groups),
            "candidate_and_independent_v2": len(candidate_groups & v2_groups),
            "candidate_and_locked_test": len(candidate_groups & locked_groups),
            "candidate_and_checkpoint_fit": len(candidate_groups & fit_groups),
            "h8_and_independent_v2": len(h8_groups & v2_groups),
            "h8_and_locked_test": len(h8_groups & locked_groups),
            "independent_v2_and_locked_test": len(v2_groups & locked_groups),
        },
        "candidate_group_membership": group_membership,
        "fresh_discovery_population": {
            "minimum_required_leakage_groups": MINIMUM_GROUPS,
            "minimum_met": len(fresh_groups) >= MINIMUM_GROUPS,
            "class": "fresh_discovery_only_not_independent_validation",
            "selection_rule": "all candidate groups after exact set subtraction; no sampling, balancing, duration, or outcome selection",
            "recording_count": len(fresh_recordings),
            "leakage_group_count": len(fresh_groups),
            "recordings_by_split": dict(
                sorted(Counter(row["split"] for row in fresh_recordings).items())
            ),
            "recordings_by_corpus_category": dict(
                sorted(Counter(row["dataset_id"] for row in fresh_recordings).items())
            ),
            "groups": fresh_detail,
        },
        "execution_flags": {
            "scientific_execution_authorized": False,
            "scientific_assets_opened": False,
            "model_loaded": False,
            "tensorflow_imported": False,
            "inference_run": False,
            "decoder_run": False,
            "candidate_reasons_inspected": False,
            "targets_inspected": False,
            "scientific_metrics_computed": False,
            "fresh_population_consumed": False,
            "h8_opened": False,
            "independent_v2_opened": False,
            "locked_test_opened": False,
        },
        "next_action": "external_review_before_any_h19_contract_or_scientific_execution",
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(args.repo.resolve(), args.manifest.resolve())
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
