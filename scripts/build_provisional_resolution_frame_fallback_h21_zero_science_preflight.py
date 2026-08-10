"""Build the H21 raw-byte/runtime provenance seal without scientific parsing."""
from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import subprocess
import sys
import tempfile


EXPECTED_HEAD = "79c02c0aa07df4c17cda2bb4eac9fd9cf47f97c5"
EXPECTED_H20_BLOB = "65c64ddb031839facb26e5b9fb8b1844883449e0"
EXPECTED_H18A_BLOB = "c06459b5877526a515930561b15a5e9a08c3af31"
EXPECTED_H18A_RAW_SHA256 = "580ea2a77cd68798946c324d190082d5b960e5d1280fd93527b8ac47116fcff9"
EXPECTED_MANIFEST_SHA256 = "b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7"
EXPECTED_CHECKPOINT_SHA256 = "1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325"
EXPECTED_RECORDINGS = 146
EXPECTED_GROUPS = 51
CHUNK_SIZE = 1024 * 1024

SCIENTIFIC_BINDINGS = {
    "h17_contract_git_blob": (
        "configs/provisional_resolution_frame_fallback_risk_h17_hypothesis_contract.json",
        "f8d8e71f8d2b98955c2e19fedf2f4019ab4cca2f",
    ),
    "h17a_amendment_contract_git_blob": (
        "configs/provisional_resolution_frame_fallback_h17a_reason_taxonomy_amendment.json",
        "04385284698d3caafa8ae3e63e2e2cfe6bee1024",
    ),
    "h19a_contract_git_blob": (
        "configs/provisional_resolution_frame_fallback_h19_synthetic_conformance.json",
        "108458ac0a432d8dc71b79093f0d0e10335588cf",
    ),
    "h19a_implementation_git_blob": (
        "src/polyphonic/provisional_resolution_frame_fallback_h19.py",
        "e85622c92d040cf857a82bc3f1d20a23bd228ef3",
    ),
    "decoder_git_blob": (
        "src/polyphonic/decoder.py",
        "27026d368081fadc4fa282954428f0377020e723",
    ),
    "exact_causal_target_extractor_git_blob": (
        "src/polyphonic/provisional_resolution_age1.py",
        "22b93d2b5a6e2a3826eddc4aee0057d68fe34141",
    ),
    "canonical_group_universe_engine_git_blob": (
        "src/polyphonic/provisional_resolution_age1_metrics.py",
        "5e40574dab4a53e0ce5b2288536d337f0da66fa9",
    ),
    "grouping_implementation_git_blob": (
        "src/polyphonic/decoder_candidate_provenance.py",
        "e43187b4e8ba0775a74114faf406703dd6c3187c",
    ),
    "evaluate_events_target_source_git_blob": (
        "src/polyphonic/evaluate_events.py",
        "c63b9751e5acef49fb51b5e2a8264b00d6e60893",
    ),
    "decoder_candidate_labels_target_source_git_blob": (
        "src/polyphonic/decoder_candidate_labels.py",
        "98c3f2e87b89df599e71068ab4ae874f69172c5a",
    ),
    "causal_event_metrics_target_source_git_blob": (
        "src/polyphonic/causal_event_metrics.py",
        "42f7954b75b0994f43d7f59c62c1ff1b04c0a81d",
    ),
}


def sha256_stream(path: Path) -> tuple[int, str]:
    resolved = path.resolve(strict=True)
    if not resolved.is_file() or not os.access(resolved, os.R_OK):
        raise RuntimeError("required_asset_missing_or_unreadable")
    digest = hashlib.sha256()
    size = 0
    with resolved.open("rb") as handle:
        while True:
            chunk = handle.read(CHUNK_SIZE)
            if not chunk:
                break
            size += len(chunk)
            digest.update(chunk)
    if size != resolved.stat().st_size:
        raise RuntimeError("raw_asset_size_changed_during_hash")
    return size, digest.hexdigest()


def git_output(repo: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", "-C", str(repo), *args], text=True, encoding="utf-8"
    ).strip()


def resolve_manifest_asset(value: str, *, manifest: Path, data_root: Path) -> Path:
    normalized = value.replace("\\", "/")
    candidate = Path(normalized)
    foreign_absolute = bool(re.match(r"^[A-Za-z]:/", normalized) or normalized.startswith("/"))
    if candidate.is_absolute() and candidate.exists():
        return candidate.resolve(strict=True)
    marker = "/data/"
    marker_index = normalized.lower().find(marker)
    if foreign_absolute and marker_index >= 0:
        return (data_root / normalized[marker_index + len(marker):]).resolve(strict=True)
    if candidate.is_absolute():
        return candidate.resolve(strict=True)
    return (manifest.parent / candidate).resolve(strict=True)


def package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def canonical_write(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent)
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def build(args: argparse.Namespace) -> dict[str, object]:
    repo = args.repo_root.resolve(strict=True)
    if git_output(repo, "rev-parse", "HEAD") != EXPECTED_HEAD:
        raise RuntimeError("h20_scientific_binding_mismatch")
    h20_path = repo / "configs/provisional_resolution_frame_fallback_h20_real_execution_contract.json"
    if git_output(repo, "hash-object", str(h20_path)) != EXPECTED_H20_BLOB:
        raise RuntimeError("h20_scientific_binding_mismatch")
    verified_bindings: dict[str, str] = {}
    for name, (relative, expected) in SCIENTIFIC_BINDINGS.items():
        actual = git_output(repo, "hash-object", relative)
        if actual != expected:
            raise RuntimeError("h20_scientific_binding_mismatch")
        verified_bindings[name] = actual

    h18a_path = repo / "configs/provisional_resolution_frame_fallback_h18_metadata_audit.json"
    if git_output(repo, "hash-object", str(h18a_path)) != EXPECTED_H18A_BLOB:
        raise RuntimeError("h20_scientific_binding_mismatch")
    _, h18a_raw_sha = sha256_stream(h18a_path)
    if h18a_raw_sha != EXPECTED_H18A_RAW_SHA256:
        raise RuntimeError("h20_scientific_binding_mismatch")
    h18a = json.loads(h18a_path.read_text(encoding="utf-8"))
    fresh = h18a.get("fresh_discovery_population")
    if not isinstance(fresh, dict):
        raise RuntimeError("h18a_identity_mismatch")
    if (
        fresh.get("recording_count") != EXPECTED_RECORDINGS
        or fresh.get("leakage_group_count") != EXPECTED_GROUPS
        or fresh.get("class") != "fresh_discovery_only_not_independent_validation"
    ):
        raise RuntimeError("h18a_identity_mismatch")
    wanted: dict[str, str] = {}
    for group in fresh.get("groups", []):
        leakage_key = group.get("leakage_group_key")
        for record in group.get("recordings", []):
            key = record.get("recording_key")
            if not isinstance(key, str) or not isinstance(leakage_key, str) or key in wanted:
                raise RuntimeError("h18a_identity_mismatch")
            wanted[key] = leakage_key
    if len(wanted) != EXPECTED_RECORDINGS or len(set(wanted.values())) != EXPECTED_GROUPS:
        raise RuntimeError("h18a_identity_mismatch")

    manifest = (repo / h18a["source_metadata"]["manifest"]["logical_path"]).resolve(strict=True)
    _, manifest_sha = sha256_stream(manifest)
    if manifest_sha != EXPECTED_MANIFEST_SHA256:
        raise RuntimeError("manifest_raw_sha256_mismatch")
    rows: dict[str, dict[str, str]] = {}
    with manifest.open("r", encoding="utf-8-sig", newline="") as handle:
        for row in csv.DictReader(handle):
            key = "|".join((row["dataset_id"], row["group_id"], row["source_id"], row["capture_id"]))
            if key in wanted:
                if key in rows:
                    raise RuntimeError("recording_mapping_ambiguous")
                rows[key] = row
    if set(rows) != set(wanted):
        raise RuntimeError("recording_not_mappable")

    data_root = args.data_root.resolve(strict=True)
    inventory = []
    raw_hash_cache: dict[Path, tuple[int, str]] = {}

    def cached_raw_hash(path: Path) -> tuple[int, str]:
        if path not in raw_hash_cache:
            raw_hash_cache[path] = sha256_stream(path)
        return raw_hash_cache[path]

    for key in sorted(wanted):
        row = rows[key]
        audio = resolve_manifest_asset(row["audio_path"], manifest=manifest, data_root=data_root)
        labels = resolve_manifest_asset(row["labels_path"], manifest=manifest, data_root=data_root)
        audio_size, audio_sha = cached_raw_hash(audio)
        label_size, label_sha = cached_raw_hash(labels)
        inventory.append({
            "recording_key": key,
            "leakage_group_key": wanted[key],
            "corpus_category": row["dataset_id"],
            "audio_member": row.get("audio_member", ""),
            "audio_logical_path": row["audio_path"],
            "audio_resolved_path": str(audio),
            "audio_size_bytes": audio_size,
            "audio_sha256": audio_sha,
            "label_logical_path": row["labels_path"],
            "label_resolved_path": str(labels),
            "label_size_bytes": label_size,
            "label_sha256": label_sha,
        })

    checkpoint = args.checkpoint.resolve(strict=True)
    checkpoint_size, checkpoint_sha = sha256_stream(checkpoint)
    if checkpoint_sha != EXPECTED_CHECKPOINT_SHA256:
        raise RuntimeError("checkpoint_raw_sha256_mismatch")
    destination = args.future_result_destination.expanduser().resolve(strict=False)
    marker = args.future_authorization_marker.expanduser().resolve(strict=False)
    claimed = Path(str(marker) + ".claimed")
    consumption_state = Path(str(marker) + ".state.json")
    if destination.exists():
        raise RuntimeError("future_result_destination_already_exists")
    if marker.exists() or claimed.exists() or consumption_state.exists():
        raise RuntimeError("future_authorization_marker_already_exists")

    audio_paths = {item["audio_resolved_path"] for item in inventory}
    label_paths = {item["label_resolved_path"] for item in inventory}
    payload = {
        "schema_version": 1,
        "purpose": "provisional_resolution_frame_fallback_h21_zero_science_preflight",
        "status": "provisional_resolution_frame_fallback_h21_zero_science_preflight_sealed",
        "bindings": {
            "h20_commit": EXPECTED_HEAD,
            "h20_contract_git_blob": EXPECTED_H20_BLOB,
            "h18a_commit": "3f9a15540d783c32486a9e0d50446efdb637ba60",
            "h18a_audit_git_blob": EXPECTED_H18A_BLOB,
            "h18a_audit_raw_sha256": EXPECTED_H18A_RAW_SHA256,
            "manifest_sha256": EXPECTED_MANIFEST_SHA256,
            **verified_bindings,
        },
        "runtime": {
            "python_executable": sys.executable,
            "python_executable_resolved": str(Path(sys.executable).resolve(strict=True)),
            "python_version": sys.version,
            "python_implementation": platform.python_implementation(),
            "os_system": platform.system(),
            "os_release": platform.release(),
            "os_version": platform.version(),
            "machine": platform.machine(),
            "numpy_distribution_version": package_version("numpy"),
            "tensorflow_distribution_version": package_version("tensorflow"),
            "keras_distribution_version": package_version("keras"),
            "future_execution_environment": {"MIDI_FORCE_CPU": "1"},
        },
        "checkpoint": {
            "resolved_path": str(checkpoint),
            "size_bytes": checkpoint_size,
            "raw_sha256": checkpoint_sha,
            "deserialized": False,
        },
        "population": {
            "recording_count": len(inventory),
            "leakage_group_count": len(set(wanted.values())),
            "leakage_group_universe": sorted(set(wanted.values())),
            "classification": "fresh_discovery_only_not_independent_validation",
            "inventory": inventory,
            "unique_audio_path_count": len(audio_paths),
            "unique_label_path_count": len(label_paths),
        },
        "future_paths": {
            "future_result_destination": str(destination),
            "destination_exists": False,
            "future_authorization_marker_path": str(marker),
            "authorization_marker_created": False,
            "claimed_marker_created": False,
            "future_consumption_state_path": str(consumption_state),
            "consumption_state_created": False,
        },
        "unresolved": {"future_runner_source_blob": None},
        "flags": {
            "zero_science_preflight": True,
            "h20_bindings_verified": True,
            "h18a_population_identity_verified": True,
            "runtime_identity_sealed": True,
            "checkpoint_raw_sha256_verified": True,
            "asset_paths_sealed": True,
            "audio_raw_sha256_sealed": True,
            "label_raw_sha256_sealed": True,
            "future_result_destination_sealed": True,
            "future_authorization_marker_path_sealed": True,
            "raw_asset_bytes_read_for_sha256": True,
            "scientific_content_interpreted": False,
            "audio_decoded": False,
            "labels_parsed": False,
            "checkpoint_deserialized": False,
            "tensorflow_imported": False,
            "model_loaded": False,
            "inference_run": False,
            "decoder_run": False,
            "real_reasons_inspected": False,
            "real_targets_extracted": False,
            "real_metrics_computed": False,
            "runner_implemented": False,
            "runner_imported": False,
            "runner_invoked": False,
            "authorization_created": False,
            "scientific_execution_authorized": False,
            "fresh_population_consumed": False,
            "locked_test_used": False,
        },
    }
    return payload


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--checkpoint", type=Path, required=True)
    parser.add_argument("--future-result-destination", type=Path, required=True)
    parser.add_argument("--future-authorization-marker", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        payload = build(args)
    except Exception as exc:
        print(json.dumps({
            "status": "provisional_resolution_frame_fallback_h21_zero_science_preflight_not_sealed",
            "reason": str(exc),
        }, sort_keys=True, separators=(",", ":")))
        raise SystemExit(1)
    canonical_write(args.output, payload)
    print(json.dumps({
        "status": payload["status"],
        "output": str(args.output.resolve()),
        "recordings": payload["population"]["recording_count"],
        "groups": payload["population"]["leakage_group_count"],
    }, sort_keys=True, separators=(",", ":")))


if __name__ == "__main__":
    main()
