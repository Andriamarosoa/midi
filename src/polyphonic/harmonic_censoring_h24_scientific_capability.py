"""Dormant, process-local authority for future H24 scientific execution.

The reviewed activation and seal deliberately do not exist in this commit.
Consequently the public issuer fails before it reads the published population,
imports NumPy, creates a scientific claim, or decodes a waveform.
"""
from __future__ import annotations

from dataclasses import dataclass, fields
import hashlib
import json
import os
from pathlib import Path
import platform
import subprocess
from typing import Mapping, Sequence
import weakref


H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json"
)
H24_SCIENTIFIC_CONTRACT_RAW_SHA256 = (
    "89311ecd7afdc9b26ce4e6b0c09b52da22f4cf77e57694973e27f3a0056dd95a"
)
H24_SCIENTIFIC_SEAL_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_scientific_execution_authorization_seal.json"
)
H24_SCIENTIFIC_ACTIVATION_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h24_scientific_execution_activation.json"
)
H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV = (
    "H24_SCIENTIFIC_EXECUTION_AUTHORIZATION_COMMIT"
)
H24_CAPABILITY_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/harmonic_censoring_h24_scientific_capability.py"
)
H24_RUNNER_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/run_harmonic_censoring_h24_scientific.py"
)
H24_PRODUCER_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/harmonic_censoring_h24_evidence_producers.py"
)
H24_PREDECESSOR_RUNNER_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/run_harmonic_censoring_h23_synthetic.py"
)
H24_PREDECESSOR_HARNESS_SOURCE_RELATIVE_PATH = Path(
    "src/polyphonic/harmonic_censoring_h23.py"
)
H24_PREDECESSOR_CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_pretrain_h23_contract.json"
)
H24_REVIEWED_PREDECESSOR_CONTRACT_RAW_SHA256 = (
    "719eba0aa440fc1e77ae7d204adee9e5b51517f455fad3bfed7e761d3c00a74a"
)
H24_IMPLEMENTATION_EXACT_CHANGED_FILES = (
    "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json",
    "readme/README.md",
    "readme/results/2026-08-10_harmonic-censoring-h24-scientific-execution-authorization-contract.md",
    "src/polyphonic/harmonic_censoring_h24_scientific_capability.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_dormant.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_contract.py",
)
H24_MARKER_BINDING_CORRECTION_EXACT_CHANGED_FILES = (
    ".gitattributes",
    "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json",
    "readme/README.md",
    "readme/results/2026-08-10_harmonic-censoring-h24-scientific-execution-authorization-contract.md",
    "src/polyphonic/harmonic_censoring_h24_scientific_capability.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_dormant.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_contract.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_seal.py",
)
H24_REPLACEMENT_SEAL_TOPOLOGY_CORRECTION_EXACT_CHANGED_FILES = (
    ".gitattributes",
    "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json",
    "readme/README.md",
    "readme/results/2026-08-10_harmonic-censoring-h24-scientific-execution-authorization-contract.md",
    "src/polyphonic/harmonic_censoring_h24_scientific_capability.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_activation.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_dormant.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_contract.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_seal.py",
)
H24_TERMINAL_BINDING_CORRECTION_EXACT_CHANGED_FILES = (
    "configs/harmonic_censoring_h24_scientific_execution_authorization_contract.json",
    "readme/README.md",
    "readme/results/2026-08-10_harmonic-censoring-h24-scientific-execution-authorization-contract.md",
    "src/polyphonic/harmonic_censoring_h24_scientific_capability.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_activation.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_dormant.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_contract.py",
    "tests/test_harmonic_censoring_h24_scientific_execution_authorization_seal.py",
)

_ATTESTED: dict[int, weakref.ReferenceType["AttestedH24ScientificExecutionCapability"]] = {}
_CLAIMED: dict[int, weakref.ReferenceType["AttestedH24ScientificExecutionCapability"]] = {}


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _reject_pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H24 authority JSON duplicates key {key!r}.")
        result[key] = value
    return result


def _reject_nonfinite(token: str) -> None:
    raise ValueError(f"H24 authority JSON forbids {token!r}.")


def _object(raw: bytes, label: str) -> dict[str, object]:
    if b"\r" in raw or raw.startswith(b"\xef\xbb\xbf"):
        raise ValueError(f"H24 {label} must be UTF-8 LF without BOM.")
    value = json.loads(
        raw.decode("utf-8"),
        object_pairs_hook=_reject_pairs,
        parse_constant=_reject_nonfinite,
    )
    if type(value) is not dict:
        raise ValueError(f"H24 {label} must be an object.")
    return value


def _exact(value: Mapping[str, object], keys: Sequence[str], label: str) -> None:
    if set(value) != set(keys):
        raise ValueError(f"H24 {label} key set mismatch.")


def _hex(value: object, length: int, label: str) -> str:
    if (
        type(value) is not str
        or len(value) != length
        or any(item not in "0123456789abcdef" for item in value)
    ):
        raise ValueError(f"H24 {label} must be lowercase hex length {length}.")
    return value


def _relative(value: object, label: str) -> Path:
    if type(value) is not str or not value:
        raise ValueError(f"H24 {label} must be a relative path.")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"H24 {label} escapes the repository.")
    return path


def _mapping(value: object, label: str) -> Mapping[str, object]:
    if type(value) is not dict:
        raise ValueError(f"H24 {label} must be an object.")
    return value


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


@dataclass(frozen=True)
class H24ScientificActivation:
    raw_sha256: str
    seal_path: Path
    seal_sha256: str
    implementation_commit: str
    capability_source_blob: str
    runner_source_blob: str
    producer_source_blob: str
    predecessor_runner_source_blob: str
    predecessor_harness_source_blob: str
    predecessor_contract_sha256: str
    contract_sha256: str


@dataclass(frozen=True)
class H24ScientificSeal:
    raw_sha256: str
    implementation_commit: str
    capability_source_blob: str
    runner_source_blob: str
    producer_source_blob: str
    predecessor_runner_source_blob: str
    predecessor_harness_source_blob: str
    predecessor_contract_sha256: str
    contract_sha256: str
    exact_changed_files: tuple[str, ...]
    runtime_identity: tuple[tuple[str, str], ...]
    claim_path: Path
    staging_directory: Path
    success_directory: Path
    transcript_path: Path
    transcript_staging_path: Path
    evidence_directory: Path
    terminal_path: Path


@dataclass(frozen=True, init=False)
class AttestedH24ScientificExecutionCapability:
    repository_root: Path
    activation_commit: str
    activation_sha256: str
    seal_sha256: str
    implementation_commit: str
    capability_source_blob: str
    runner_source_blob: str
    producer_source_blob: str
    predecessor_runner_source_blob: str
    predecessor_harness_source_blob: str
    predecessor_contract_sha256: str
    contract_sha256: str
    runtime_identity: tuple[tuple[str, str], ...]
    population_marker_sha256: str
    population_terminal_sha256: str
    population_receipt_sha256: str
    population_index_sha256: str
    population_directory: Path
    ordered_fixture_ids: tuple[str, ...]
    fixture_file_bindings: tuple[tuple[str, int, str], ...]
    ordered_test_ids: tuple[str, ...]
    ordered_test_phases: tuple[str, ...]
    claim_path: Path
    staging_directory: Path
    success_directory: Path
    transcript_path: Path
    transcript_staging_path: Path
    evidence_directory: Path
    terminal_path: Path

    def __new__(cls) -> "AttestedH24ScientificExecutionCapability":
        raise TypeError(
            "AttestedH24ScientificExecutionCapability has no public constructor."
        )


def _new_capability(**values: object) -> AttestedH24ScientificExecutionCapability:
    expected = {item.name for item in fields(AttestedH24ScientificExecutionCapability)}
    if set(values) != expected:
        raise ValueError("H24 internal capability field set mismatch.")
    value = object.__new__(AttestedH24ScientificExecutionCapability)
    for name, field_value in values.items():
        object.__setattr__(value, name, field_value)
    return _register(value)


def _register(value: AttestedH24ScientificExecutionCapability) -> AttestedH24ScientificExecutionCapability:
    identity = id(value)

    def cleanup(reference: weakref.ReferenceType[AttestedH24ScientificExecutionCapability]) -> None:
        if _ATTESTED.get(identity) is reference:
            _ATTESTED.pop(identity, None)
        if _CLAIMED.get(identity) is reference:
            _CLAIMED.pop(identity, None)

    _ATTESTED[identity] = weakref.ref(value, cleanup)
    return value


def require_attested_h24_scientific_capability(
    value: object,
) -> AttestedH24ScientificExecutionCapability:
    if type(value) is not AttestedH24ScientificExecutionCapability:
        raise TypeError("H24 scientific execution requires the exact capability type.")
    reference = _ATTESTED.get(id(value))
    if reference is None or reference() is not value:
        raise PermissionError("H24 scientific capability is not process-local attested.")
    return value


def require_claimed_h24_scientific_capability(
    value: object,
) -> AttestedH24ScientificExecutionCapability:
    checked = require_attested_h24_scientific_capability(value)
    reference = _CLAIMED.get(id(checked))
    if reference is None or reference() is not checked:
        raise PermissionError("H24 scientific capability has not crossed its durable claim.")
    if not checked.claim_path.exists():
        raise PermissionError("H24 scientific claim disappeared after consumption.")
    return checked


def _validate_activation(payload: Mapping[str, object], raw_sha256: str) -> H24ScientificActivation:
    _exact(payload, ("schema_version", "purpose", "status", "seal", "bindings", "external_review"), "activation")
    if payload["schema_version"] != 1 or type(payload["schema_version"]) is not int:
        raise ValueError("H24 activation schema mismatch.")
    if payload["purpose"] != "harmonic_censoring_h24_scientific_execution_activation":
        raise ValueError("H24 activation purpose mismatch.")
    if payload["status"] != "externally_reviewed_scientific_activation":
        raise PermissionError("H24 activation is not externally reviewed.")
    seal = _mapping(payload["seal"], "activation seal")
    _exact(seal, ("path", "raw_sha256"), "activation seal")
    bindings = _mapping(payload["bindings"], "activation bindings")
    _exact(bindings, ("implementation_commit", "capability_source_blob", "runner_source_blob", "producer_source_blob", "predecessor_runner_source_blob", "predecessor_harness_source_blob", "predecessor_contract_sha256", "contract_sha256"), "activation bindings")
    review = _mapping(payload["external_review"], "activation review")
    if review != {"verdict": "APPROVED", "activation_commit_review_required": True}:
        raise PermissionError("H24 activation review mismatch.")
    seal_path = _relative(seal["path"], "activation seal path")
    if seal_path != H24_SCIENTIFIC_SEAL_RELATIVE_PATH:
        raise ValueError("H24 activation seal path mismatch.")
    return H24ScientificActivation(
        _hex(raw_sha256, 64, "activation SHA"),
        seal_path,
        _hex(seal["raw_sha256"], 64, "seal SHA"),
        _hex(bindings["implementation_commit"], 40, "implementation commit"),
        _hex(bindings["capability_source_blob"], 40, "capability blob"),
        _hex(bindings["runner_source_blob"], 40, "runner blob"),
        _hex(bindings["producer_source_blob"], 40, "producer blob"),
        _hex(bindings["predecessor_runner_source_blob"], 40, "predecessor runner blob"),
        _hex(bindings["predecessor_harness_source_blob"], 40, "predecessor harness blob"),
        _hex(bindings["predecessor_contract_sha256"], 64, "predecessor contract SHA"),
        _hex(bindings["contract_sha256"], 64, "contract SHA"),
    )


def _validate_seal(payload: Mapping[str, object], raw_sha256: str) -> H24ScientificSeal:
    _exact(payload, ("schema_version", "purpose", "status", "authorization", "bindings", "runtime_identity", "one_shot_paths", "external_review"), "seal")
    if payload["schema_version"] != 1 or type(payload["schema_version"]) is not int:
        raise ValueError("H24 seal schema mismatch.")
    if payload["purpose"] != "harmonic_censoring_h24_scientific_execution_authorization_seal":
        raise ValueError("H24 seal purpose mismatch.")
    if payload["status"] != "externally_approved_one_shot_scientific_execution":
        raise PermissionError("H24 scientific seal status mismatch.")
    rights = _mapping(payload["authorization"], "seal authorization")
    true_rights = ("capability_issuance_authorized", "scientific_claim_authorized", "scientific_execution_authorized", "P0_execution_authorized", "P1_execution_authorized", "P2_execution_authorized")
    false_rights = ("population_modification_authorized", "real_data_access_authorized", "H17_population_use_authorized", "model_or_checkpoint_access_authorized", "training_authorized", "locked_test_used")
    _exact(rights, true_rights + false_rights, "seal authorization")
    if any(rights[name] is not True for name in true_rights) or any(rights[name] is not False for name in false_rights):
        raise PermissionError("H24 scientific rights are not exact.")
    bindings = _mapping(payload["bindings"], "seal bindings")
    _exact(bindings, ("implementation_commit", "capability_source_blob", "runner_source_blob", "producer_source_blob", "predecessor_runner_source_blob", "predecessor_harness_source_blob", "predecessor_contract_sha256", "contract_sha256", "exact_changed_files"), "seal bindings")
    changed = bindings["exact_changed_files"]
    if type(changed) is not list or not changed or any(type(item) is not str for item in changed):
        raise ValueError("H24 seal changed files are invalid.")
    if tuple(changed) != H24_TERMINAL_BINDING_CORRECTION_EXACT_CHANGED_FILES:
        raise ValueError("H24 seal changed files differ from reviewed implementation topology.")
    runtime = _mapping(payload["runtime_identity"], "runtime identity")
    _exact(runtime, ("machine", "python_implementation", "python_version", "numpy_version", "device", "OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "NUMEXPR_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"), "runtime identity")
    paths = _mapping(payload["one_shot_paths"], "one-shot paths")
    path_names = ("claim_path", "staging_directory", "success_directory", "transcript_path", "transcript_staging_path", "evidence_directory", "terminal_path")
    _exact(paths, path_names, "one-shot paths")
    review = _mapping(payload["external_review"], "seal review")
    if review != {"verdict": "APPROVED", "implementation_reviewed": True, "seal_commit_review_required": True}:
        raise PermissionError("H24 seal review mismatch.")
    return H24ScientificSeal(
        _hex(raw_sha256, 64, "seal SHA"),
        _hex(bindings["implementation_commit"], 40, "implementation commit"),
        _hex(bindings["capability_source_blob"], 40, "capability blob"),
        _hex(bindings["runner_source_blob"], 40, "runner blob"),
        _hex(bindings["producer_source_blob"], 40, "producer blob"),
        _hex(bindings["predecessor_runner_source_blob"], 40, "predecessor runner blob"),
        _hex(bindings["predecessor_harness_source_blob"], 40, "predecessor harness blob"),
        _hex(bindings["predecessor_contract_sha256"], 64, "predecessor contract SHA"),
        _hex(bindings["contract_sha256"], 64, "contract SHA"),
        tuple(changed),
        tuple(sorted((name, str(value)) for name, value in runtime.items())),
        *(_relative(paths[name], name) for name in path_names),
    )


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=repository, text=True, encoding="utf-8").strip()


def _require_file_blob(repository: Path, commit: str, path: Path, blob: str) -> None:
    if _git(repository, "rev-parse", f"{commit}:{path.as_posix()}") != blob:
        raise ValueError(f"H24 source blob mismatch for {path.as_posix()}.")


def _require_bound_source_blob_at_activation(
    repository: Path,
    implementation_commit: str,
    activation_commit: str,
    path: Path,
    blob: str,
) -> None:
    """Bind both the reviewed implementation and the code actually executed."""

    _require_file_blob(repository, implementation_commit, path, blob)
    if _git(repository, "rev-parse", f"{activation_commit}:{path.as_posix()}") != blob:
        raise ValueError(
            f"H24 activation HEAD source blob mismatch for {path.as_posix()}."
        )


def _runtime_identity() -> tuple[tuple[str, str], ...]:
    import importlib.metadata

    identity = {
        "machine": platform.machine(),
        "python_implementation": platform.python_implementation(),
        "python_version": platform.python_version(),
        "numpy_version": importlib.metadata.version("numpy"),
        "device": os.environ.get("MIDI_FORCE_CPU", ""),
        "OMP_NUM_THREADS": os.environ.get("OMP_NUM_THREADS", ""),
        "OPENBLAS_NUM_THREADS": os.environ.get("OPENBLAS_NUM_THREADS", ""),
        "MKL_NUM_THREADS": os.environ.get("MKL_NUM_THREADS", ""),
        "NUMEXPR_NUM_THREADS": os.environ.get("NUMEXPR_NUM_THREADS", ""),
        "VECLIB_MAXIMUM_THREADS": os.environ.get("VECLIB_MAXIMUM_THREADS", ""),
    }
    expected = {
        "machine": "arm64",
        "python_implementation": "CPython",
        "python_version": "3.11.9",
        "numpy_version": "1.26.4",
        "device": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "NUMEXPR_NUM_THREADS": "1",
        "VECLIB_MAXIMUM_THREADS": "1",
    }
    if identity != expected:
        raise PermissionError("H24 runtime is not the exact reviewed arm64 CPU one-thread runtime.")
    return tuple(sorted(identity.items()))


def _load_population_bindings(repository: Path, contract: Mapping[str, object]) -> tuple[tuple[str, ...], tuple[tuple[str, int, str], ...]]:
    population = _mapping(contract["published_population_binding"], "published population")
    success = (repository / str(population["success_directory"])).resolve(strict=True)
    index_entry = _mapping(population["index"], "population index")
    index_path = (repository / str(index_entry["path"])).resolve(strict=True)
    raw = index_path.read_bytes()
    if _sha256(raw) != index_entry["raw_sha256"]:
        raise ValueError("H24 population index SHA mismatch.")
    rows: list[dict[str, object]] = []
    for line in raw.splitlines(keepends=True):
        row = _object(line, "population index line")
        if _canonical(row) != line:
            raise ValueError("H24 population index line is not canonical.")
        rows.append(row)
    if len(rows) != 175:
        raise ValueError("H24 population index must contain 175 rows.")
    fixture_ids: list[str] = []
    files: list[tuple[str, int, str]] = []
    for row in rows:
        fixture_id = row.get("fixture_id")
        if type(fixture_id) is not str or not fixture_id:
            raise ValueError("H24 population fixture ID is invalid.")
        fixture_ids.append(fixture_id)
        for path_key, sha_key in (("specification_path", "specification_sha256"), ("target_path", "target_sha256"), ("waveform_path", "waveform_sha256")):
            relative = _relative(row.get(path_key), path_key).as_posix()
            digest = _hex(row.get(sha_key), 64, sha_key)
            file_path = (success / relative).resolve(strict=True)
            file_path.relative_to(success)
            content = file_path.read_bytes()
            size = len(content)
            if size <= 0 or _sha256(content) != digest:
                raise ValueError(f"H24 published file mismatch: {relative}.")
            if path_key == "waveform_path" and (
                row.get("waveform_byte_count") != 100352 or size != 100352
            ):
                raise ValueError("H24 waveform size mismatch.")
            files.append((relative, size, digest))
    if len(set(fixture_ids)) != 175 or len(files) != 525:
        raise ValueError("H24 population cardinality mismatch.")
    if _sha256(_canonical(fixture_ids)) != index_entry["ordered_fixture_ids_sha256"]:
        raise ValueError("H24 ordered fixture ID SHA mismatch.")
    expected_files = {relative for relative, _, _ in files}
    expected_files.update({"population_index.jsonl", "population_receipt.json"})
    actual_files = {
        item.relative_to(success).as_posix()
        for item in success.rglob("*")
        if item.is_file()
    }
    if actual_files != expected_files or len(actual_files) != 527:
        raise ValueError("H24 population has missing or extra published files.")
    return tuple(fixture_ids), tuple(files)


def _is_same_or_descendant(path: Path, ancestor: Path) -> bool:
    try:
        path.relative_to(ancestor)
    except ValueError:
        return False
    return True


def _validate_scientific_path_topology(
    repository: Path,
    absolute_paths: Mapping[str, Path],
    population: Mapping[str, object],
) -> None:
    """Reject every one-shot topology except the three intentional descendants."""

    expected_names = {
        "claim",
        "staging",
        "success",
        "transcript",
        "transcript_staging",
        "evidence",
        "terminal",
    }
    if set(absolute_paths) != expected_names:
        raise ValueError("H24 one-shot path key set mismatch.")
    if len(set(absolute_paths.values())) != len(absolute_paths):
        raise ValueError("H24 one-shot paths must be distinct.")
    if absolute_paths["transcript"] != absolute_paths["success"] / "scientific_transcript.jsonl":
        raise ValueError("H24 final transcript path is not canonical.")
    if absolute_paths["transcript_staging"] != absolute_paths["staging"] / "scientific_transcript.jsonl.part":
        raise ValueError("H24 staging transcript path is not canonical.")
    if absolute_paths["evidence"] != absolute_paths["success"] / "evidence":
        raise ValueError("H24 evidence directory is not canonical.")

    population_success = (repository / str(population["success_directory"])).resolve()
    population_staging = (repository / str(population["staging_directory"])).resolve()
    population_marker = (
        repository / str(_mapping(population["claim_marker"], "population marker")["path"])
    ).resolve()
    population_terminal = (
        repository / str(_mapping(population["terminal"], "population terminal")["path"])
    ).resolve()
    population_namespace = population_success.parent
    if not (
        population_staging.parent == population_namespace
        and population_marker.parent == population_namespace
        and population_terminal.parent == population_namespace
    ):
        raise ValueError("H24 population control namespace is inconsistent.")
    for name in ("claim", "staging", "success", "terminal"):
        if _is_same_or_descendant(
            absolute_paths[name], population_namespace
        ) or _is_same_or_descendant(population_namespace, absolute_paths[name]):
            raise ValueError(
                f"H24 {name} path overlaps the immutable population control namespace."
            )

    allowed_descendants = {
        ("success", "transcript"),
        ("success", "evidence"),
        ("staging", "transcript_staging"),
    }
    names = tuple(sorted(absolute_paths))
    for ancestor_name in names:
        for descendant_name in names:
            if ancestor_name == descendant_name:
                continue
            if _is_same_or_descendant(
                absolute_paths[descendant_name], absolute_paths[ancestor_name]
            ) and (ancestor_name, descendant_name) not in allowed_descendants:
                raise ValueError(
                    "H24 one-shot paths have an unauthorized ancestor/descendant "
                    f"relation: {ancestor_name}->{descendant_name}."
                )


def issue_h24_scientific_execution_capability(repository_root: Path) -> AttestedH24ScientificExecutionCapability:
    """Issue only from a future exact reviewed activation; currently dormant."""

    repository = Path(repository_root).resolve(strict=True)
    contract_raw = (repository / H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH).read_bytes()
    if _sha256(contract_raw) != H24_SCIENTIFIC_CONTRACT_RAW_SHA256:
        raise ValueError("H24 scientific contract SHA mismatch.")
    contract = _object(contract_raw, "scientific contract")
    activation_commit = os.environ.get(H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV)
    if not activation_commit:
        raise PermissionError("H24 scientific execution remains dormant: no OS-bound activation commit.")
    activation_commit = _hex(activation_commit, 40, "OS activation commit")
    if _git(repository, "rev-parse", "HEAD") != activation_commit:
        raise PermissionError("H24 checkout HEAD differs from OS-bound activation commit.")
    if _git(repository, "status", "--porcelain"):
        raise PermissionError("H24 scientific execution requires a clean worktree.")
    activation_path = (repository / H24_SCIENTIFIC_ACTIVATION_RELATIVE_PATH).resolve(strict=True)
    activation_raw = activation_path.read_bytes()
    committed_activation = subprocess.check_output(
        ["git", "show", f"{activation_commit}:{H24_SCIENTIFIC_ACTIVATION_RELATIVE_PATH.as_posix()}"],
        cwd=repository,
    )
    if activation_raw != committed_activation:
        raise ValueError("H24 activation bytes differ from the OS-bound commit.")
    activation = _validate_activation(_object(activation_raw, "activation"), _sha256(activation_raw))
    seal_raw = (repository / activation.seal_path).read_bytes()
    if _sha256(seal_raw) != activation.seal_sha256:
        raise ValueError("H24 seal SHA differs from activation.")
    seal = _validate_seal(_object(seal_raw, "seal"), _sha256(seal_raw))
    if (seal.implementation_commit, seal.capability_source_blob, seal.runner_source_blob, seal.producer_source_blob, seal.predecessor_runner_source_blob, seal.predecessor_harness_source_blob, seal.predecessor_contract_sha256, seal.contract_sha256) != (activation.implementation_commit, activation.capability_source_blob, activation.runner_source_blob, activation.producer_source_blob, activation.predecessor_runner_source_blob, activation.predecessor_harness_source_blob, activation.predecessor_contract_sha256, activation.contract_sha256):
        raise ValueError("H24 seal and activation bindings differ.")
    if seal.contract_sha256 != H24_SCIENTIFIC_CONTRACT_RAW_SHA256:
        raise ValueError("H24 seal does not bind the reviewed contract.")
    for path, blob in (
        (H24_CAPABILITY_SOURCE_RELATIVE_PATH, seal.capability_source_blob),
        (H24_RUNNER_SOURCE_RELATIVE_PATH, seal.runner_source_blob),
        (H24_PRODUCER_SOURCE_RELATIVE_PATH, seal.producer_source_blob),
        (H24_PREDECESSOR_RUNNER_SOURCE_RELATIVE_PATH, seal.predecessor_runner_source_blob),
        (H24_PREDECESSOR_HARNESS_SOURCE_RELATIVE_PATH, seal.predecessor_harness_source_blob),
    ):
        _require_bound_source_blob_at_activation(
            repository,
            seal.implementation_commit,
            activation_commit,
            path,
            blob,
        )
    if seal.predecessor_contract_sha256 != H24_REVIEWED_PREDECESSOR_CONTRACT_RAW_SHA256:
        raise ValueError("H24 predecessor contract is not anchored to reviewed H23.")
    predecessor_contract_raw = (repository / H24_PREDECESSOR_CONTRACT_RELATIVE_PATH).read_bytes()
    if _sha256(predecessor_contract_raw) != seal.predecessor_contract_sha256:
        raise ValueError("H24 predecessor scientific contract SHA mismatch.")
    committed_predecessor_contract = subprocess.check_output(
        [
            "git",
            "show",
            f"{activation_commit}:{H24_PREDECESSOR_CONTRACT_RELATIVE_PATH.as_posix()}",
        ],
        cwd=repository,
    )
    if _sha256(committed_predecessor_contract) != H24_REVIEWED_PREDECESSOR_CONTRACT_RAW_SHA256:
        raise ValueError("H24 activation HEAD predecessor contract SHA mismatch.")
    changed_files = tuple(
        sorted(
            item
            for item in _git(
                repository,
                "diff-tree",
                "--no-commit-id",
                "--name-only",
                "-r",
                seal.implementation_commit,
            ).splitlines()
            if item
        )
    )
    if changed_files != tuple(sorted(seal.exact_changed_files)):
        raise ValueError("H24 implementation commit topology differs from the seal.")
    if seal.runtime_identity != _runtime_identity():
        raise PermissionError("H24 runtime identity differs from the seal.")
    absolute_paths = {
        name: (repository / path).resolve()
        for name, path in (
            ("claim", seal.claim_path),
            ("staging", seal.staging_directory),
            ("success", seal.success_directory),
            ("transcript", seal.transcript_path),
            ("transcript_staging", seal.transcript_staging_path),
            ("evidence", seal.evidence_directory),
            ("terminal", seal.terminal_path),
        )
    }
    for name, path in absolute_paths.items():
        try:
            path.relative_to(repository)
        except ValueError as exc:
            raise ValueError(f"H24 {name} path escapes repository.") from exc
    population = _mapping(contract["published_population_binding"], "population")
    _validate_scientific_path_topology(repository, absolute_paths, population)
    for path in (seal.claim_path, seal.staging_directory, seal.success_directory, seal.transcript_path, seal.transcript_staging_path, seal.evidence_directory, seal.terminal_path):
        if (repository / path).exists():
            raise FileExistsError(f"H24 scientific one-shot path already exists: {path}.")
    for label, entry_name in (
        ("population marker", "claim_marker"),
        ("population terminal", "terminal"),
        ("population receipt", "receipt"),
        ("population index", "index"),
    ):
        entry = _mapping(population[entry_name], label)
        bound_path = (repository / str(entry["path"])).resolve(strict=True)
        if _sha256(bound_path.read_bytes()) != entry["raw_sha256"]:
            raise ValueError(f"H24 {label} SHA mismatch.")
    if (repository / str(population["staging_directory"])).exists():
        raise ValueError("H24 population staging directory must remain absent.")
    if not (repository / str(population["success_directory"])).is_dir():
        raise ValueError("H24 population success directory is absent.")
    fixture_ids, files = _load_population_bindings(repository, contract)
    from .harmonic_censoring_h24 import load_h24_dormant_harness_plan

    plan = load_h24_dormant_harness_plan(repository)
    if plan.fixture_ids != fixture_ids or len(plan.test_ids) != 72:
        raise ValueError("H24 sealed plan differs from published population.")
    return _new_capability(
        repository_root=repository,
        activation_commit=activation_commit,
        activation_sha256=activation.raw_sha256,
        seal_sha256=seal.raw_sha256,
        implementation_commit=seal.implementation_commit,
        capability_source_blob=seal.capability_source_blob,
        runner_source_blob=seal.runner_source_blob,
        producer_source_blob=seal.producer_source_blob,
        predecessor_runner_source_blob=seal.predecessor_runner_source_blob,
        predecessor_harness_source_blob=seal.predecessor_harness_source_blob,
        predecessor_contract_sha256=seal.predecessor_contract_sha256,
        contract_sha256=seal.contract_sha256,
        runtime_identity=seal.runtime_identity,
        population_marker_sha256=str(_mapping(population["claim_marker"], "marker")["raw_sha256"]),
        population_terminal_sha256=str(_mapping(population["terminal"], "population terminal")["raw_sha256"]),
        population_receipt_sha256=str(_mapping(population["receipt"], "receipt")["raw_sha256"]),
        population_index_sha256=str(_mapping(population["index"], "index")["raw_sha256"]),
        population_directory=repository / str(population["success_directory"]),
        ordered_fixture_ids=fixture_ids,
        fixture_file_bindings=files,
        ordered_test_ids=plan.test_ids,
        ordered_test_phases=tuple(item.phase for item in plan.tests),
        claim_path=repository / seal.claim_path,
        staging_directory=repository / seal.staging_directory,
        success_directory=repository / seal.success_directory,
        transcript_path=repository / seal.transcript_path,
        transcript_staging_path=repository / seal.transcript_staging_path,
        evidence_directory=repository / seal.evidence_directory,
        terminal_path=repository / seal.terminal_path,
    )


def claim_h24_scientific_execution(value: object) -> AttestedH24ScientificExecutionCapability:
    checked = require_attested_h24_scientific_capability(value)
    marker = {
        "schema_version": 1,
        "purpose": "harmonic_censoring_h24_scientific_execution_claim",
        "claim_state": "CLAIMED_BEFORE_FIRST_WAVEFORM_DECODE",
        "activation_commit": checked.activation_commit,
        "activation_sha256": checked.activation_sha256,
        "seal_sha256": checked.seal_sha256,
        "implementation_commit": checked.implementation_commit,
        "capability_source_blob": checked.capability_source_blob,
        "runner_source_blob": checked.runner_source_blob,
        "producer_source_blob": checked.producer_source_blob,
        "predecessor_runner_source_blob": checked.predecessor_runner_source_blob,
        "predecessor_harness_source_blob": checked.predecessor_harness_source_blob,
        "predecessor_contract_sha256": checked.predecessor_contract_sha256,
        "contract_sha256": checked.contract_sha256,
        "population_index_sha256": checked.population_index_sha256,
        "ordered_test_ids": list(checked.ordered_test_ids),
        "real_data_used": False,
        "H17_population_used": False,
        "locked_test_used": False,
        "training_authorized": False,
    }
    raw = _canonical(marker)
    checked.claim_path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(
        checked.claim_path,
        os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0),
        0o600,
    )
    try:
        remaining = memoryview(raw)
        while remaining:
            written = os.write(descriptor, remaining)
            if written <= 0:
                raise OSError("H24 scientific claim write made no progress.")
            remaining = remaining[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    if os.name != "nt":
        parent = os.open(checked.claim_path.parent, os.O_RDONLY)
        try:
            os.fsync(parent)
        finally:
            os.close(parent)
    if checked.claim_path.read_bytes() != raw:
        raise ValueError("H24 scientific claim bytes changed after durable write.")
    if os.name != "nt" and (checked.claim_path.stat().st_mode & 0o777) != 0o600:
        raise PermissionError("H24 scientific claim mode is not 0600.")
    _CLAIMED[id(checked)] = weakref.ref(checked)
    return checked


__all__ = [
    "AttestedH24ScientificExecutionCapability",
    "H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV",
    "H24_SCIENTIFIC_CONTRACT_RAW_SHA256",
    "claim_h24_scientific_execution",
    "issue_h24_scientific_execution_capability",
    "require_attested_h24_scientific_capability",
    "require_claimed_h24_scientific_capability",
]
