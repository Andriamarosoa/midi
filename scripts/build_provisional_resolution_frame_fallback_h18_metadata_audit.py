"""Build the metadata-only H18 fresh-discovery population audit.

This helper deliberately reads only CSV/JSON/text provenance.  For candidate
assets it checks path existence; it never opens audio, labels, or checkpoints.
"""

from __future__ import annotations

import argparse
import ast
import csv
import hashlib
import json
import re
import struct
import subprocess
import unicodedata
import zipfile
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
HISTORICAL_RUN_NAME = "polyphonic_dual_stream_bass_harmonic_presence_20260801_195145"
HISTORICAL_CONFIG_SHA256 = "a02913c5d4366c935ba9ecc073bc786a6d05c0800e73d98c6d964546f3f5185f"
HISTORICAL_RUNTIME_SHA256 = "c23ff1684b23e875e2ace5cb50cbdb8c850018c83518a3884e1f268455d045ac"
HISTORICAL_STATUS_SHA256 = "a3b7dafb184c2dc80bd6cc1bd51eac9a2b609f617ba3f90cb6a9f8cdbd587d33"
HISTORICAL_PLAN_SHA256 = "d039ac2cfba31cc9560f80ed2da7230c1d039ef9dbaea38d56574d4c0b550714"
HISTORICAL_PLAN_SIDECAR_SHA256 = "96f630a89d2c9f572afadb31ed5b54022f8a4883dd7bac3172e45f47692dca6a"
HISTORICAL_EPOCH7_TRANSACTION_SHA256 = "ff0e2c1aeadf551c2dcce200bd2617ac57c34cf0d363c0754e5517a3f89427ef"
HISTORICAL_TRAIN_COMMIT = "33251d7a64de14766f4e80b1bf0914492f84847b"


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


def _npy_order_recording_indices(archive: zipfile.ZipFile, name: str) -> set[int]:
    """Read only the integer recording-index column of an epoch-plan NPY."""

    with archive.open(name, "r") as handle:
        if handle.read(6) != b"\x93NUMPY":
            raise RuntimeError(f"{name} is not an NPY member.")
        major, minor = handle.read(2)
        if (major, minor) == (1, 0):
            header_size = struct.unpack("<H", handle.read(2))[0]
        elif major in (2, 3):
            header_size = struct.unpack("<I", handle.read(4))[0]
        else:
            raise RuntimeError(f"{name} uses an unsupported NPY version.")
        header = ast.literal_eval(handle.read(header_size).decode("latin1").strip())
        descriptor = header.get("descr")
        if descriptor not in ("<i4", "|i4", "<i8", "|i8"):
            raise RuntimeError(f"{name} recording refs are not little-endian integers.")
        if header.get("fortran_order") is not False:
            raise RuntimeError(f"{name} unexpectedly uses Fortran order.")
        shape = tuple(header.get("shape", ()))
        if len(shape) != 2 or shape[1] != 2 or shape[0] < 1:
            raise RuntimeError(f"{name} does not contain (recording, frame) refs.")
        raw = handle.read()
    item_size = 4 if descriptor in ("<i4", "|i4") else 8
    if len(raw) != shape[0] * 2 * item_size:
        raise RuntimeError(f"{name} payload length is inconsistent with its shape.")
    format_code = "<ii" if item_size == 4 else "<qq"
    return {recording for recording, _frame in struct.iter_unpack(format_code, raw)}


def _historical_fit_evidence(
    repo: Path, historical_run: Path, manifest_sha256: str, train_count: int
) -> tuple[dict[str, object], set[int]]:
    if historical_run.name != HISTORICAL_RUN_NAME:
        raise RuntimeError("H18a historical run directory name mismatch.")
    paths = {
        "config": historical_run / "config.json",
        "runtime": historical_run / "runtime.json",
        "training_status": historical_run / "training_status.json",
        "epoch_plan": historical_run / "epoch_plans.npz",
        "epoch_plan_sidecar": historical_run / "epoch_plans.npz.json",
        "epoch7_transaction": historical_run / "epoch_transactions/epoch-07.json",
        "epoch7_checkpoint": historical_run / "epochs/epoch-07.keras",
    }
    expected = {
        "config": HISTORICAL_CONFIG_SHA256,
        "runtime": HISTORICAL_RUNTIME_SHA256,
        "training_status": HISTORICAL_STATUS_SHA256,
        "epoch_plan": HISTORICAL_PLAN_SHA256,
        "epoch_plan_sidecar": HISTORICAL_PLAN_SIDECAR_SHA256,
        "epoch7_transaction": HISTORICAL_EPOCH7_TRANSACTION_SHA256,
        "epoch7_checkpoint": CHECKPOINT_SHA256,
    }
    evidence_files: dict[str, object] = {}
    for name, path in paths.items():
        raw = path.read_bytes()
        digest = _sha256(raw)
        if digest != expected[name]:
            raise RuntimeError(f"H18a historical {name} SHA-256 mismatch.")
        evidence_files[name] = {
            "logical_path": str(path.relative_to(historical_run.parent.parent.parent)).replace("\\", "/"),
            "sha256": digest,
            "size_bytes": len(raw),
        }

    config = json.loads(paths["config"].read_bytes())
    runtime = json.loads(paths["runtime"].read_bytes())
    status = json.loads(paths["training_status"].read_bytes())
    sidecar = json.loads(paths["epoch_plan_sidecar"].read_bytes())
    transaction = json.loads(paths["epoch7_transaction"].read_bytes())
    signatures = transaction.get("signatures", {})
    if (
        config.get("train", {}).get("run_name")
        != "polyphonic_dual_stream_bass_harmonic_presence"
        or config.get("train", {}).get("epochs") != 8
        or runtime.get("git_commit") != HISTORICAL_TRAIN_COMMIT
        or runtime.get("smoke_test") is not False
        or status.get("status") != "complete"
        or status.get("locked_test_used") is not False
        or sidecar.get("sha256") != HISTORICAL_PLAN_SHA256
        or sidecar.get("epochs") != 8
        or sidecar.get("locked_test_used") is not False
        or signatures.get("commit") != HISTORICAL_TRAIN_COMMIT
        or signatures.get("manifest_sha256") != manifest_sha256
        or signatures.get("plan_sha256") != HISTORICAL_PLAN_SHA256
        or transaction.get("locked_test_used") is not False
        or transaction.get("policy_post", {}).get("completed_epochs") != 7
    ):
        raise RuntimeError("H18a historical run metadata chain is inconsistent.")

    per_epoch: dict[str, int] = {}
    used: set[int] = set()
    with zipfile.ZipFile(paths["epoch_plan"], "r") as archive:
        for epoch in range(7):
            indices = _npy_order_recording_indices(
                archive, f"epoch_{epoch:04d}__order.npy"
            )
            if indices != set(range(train_count)):
                raise RuntimeError(
                    f"H18a epoch {epoch + 1} does not cover every train recording."
                )
            per_epoch[str(epoch + 1)] = len(indices)
            used.update(indices)

    return {
        "historical_run_name": HISTORICAL_RUN_NAME,
        "source_files": evidence_files,
        "runtime_git_commit": HISTORICAL_TRAIN_COMMIT,
        "train_code_git_blob": _git_blob_at(
            repo, HISTORICAL_TRAIN_COMMIT, Path("src/polyphonic/train.py")
        ),
        "data_code_git_blob": _git_blob_at(
            repo, HISTORICAL_TRAIN_COMMIT, Path("src/polyphonic/data.py")
        ),
        "transaction_manifest_sha256": signatures["manifest_sha256"],
        "transaction_plan_sha256": signatures["plan_sha256"],
        "transaction_completed_epochs": 7,
        "unique_train_recordings_per_epoch_1_through_7": per_epoch,
        "union_unique_train_recording_indices": len(used),
        "missing_train_recording_indices": sorted(set(range(train_count)) - used),
        "derivation": "epoch-07 raw SHA -> epoch-07 transaction -> frozen plan SHA and manifest SHA -> recording-index column of epoch plans 1..7 -> manifest train rows in original order",
    }, used


def build(repo: Path, manifest: Path, historical_run: Path) -> dict[str, object]:
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
    train_rows = [row for row in rows if row["split"] == "train"]
    fit_evidence, fit_recording_indices = _historical_fit_evidence(
        repo, historical_run, _sha256(manifest_raw), len(train_rows)
    )
    fit_rows = [train_rows[index] for index in sorted(fit_recording_indices)]
    fit_groups = {_leakage_group_key(row) for row in fit_rows}

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
        "h18a_provenance_resolution": {
            "status": "checkpoint_fit_group_provenance_established",
            "previous_h18_review": "not_approved_checkpoint_fit_provenance_was_self_asserted",
            "resolution": "preexisting raw checkpoint, epoch-07 transaction, config, runtime, status, frozen epoch-plan archive, manifest, and frozen training code are now linked; epoch-plan recording references prove the exact fit population",
            "scientific_execution_authorized": False,
        },
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
            "historical_run": HISTORICAL_RUN_NAME,
            "checkpoint_name": "epoch-07.keras",
            "fit_manifest_sha256": MANIFEST_SHA256,
            "fit_partition": "train",
            "fit_recording_count": len(fit_rows),
            "fit_leakage_group_count": len(fit_groups),
            "fit_leakage_group_keys": sorted(fit_groups),
            "evidence": fit_evidence,
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
    parser.add_argument("--historical-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    payload = build(
        args.repo.resolve(), args.manifest.resolve(), args.historical_run.resolve()
    )
    with args.output.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(
            json.dumps(
                payload, ensure_ascii=False, separators=(",", ":"), sort_keys=True
            )
            + "\n"
        )


if __name__ == "__main__":
    main()
