"""Dormant H25 population materializer and byte recomputer.

There is deliberately no CLI and no NumPy import at module import time.  The
only public publication function requires an identity-attested capability for
which this commit provides no issuer.  The implementation is therefore
reviewable and testable with synthetic temporary inputs, but cannot materialize
``H25_SYNTHETIC_V1`` operationally.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
from typing import Any, Callable, Mapping, Sequence


CONTRACT_RELATIVE_PATH = Path(
    "configs/harmonic_censoring_h25_population_materialization_runtime_provenance_encoding_contract.json"
)
CONTRACT_RAW_SHA256 = "a00255964eb8f10c348c4364d2b6aed641a983be52b395d7befe0f4c70472273"
POPULATION_ID = "H25_SYNTHETIC_V1"
SAMPLE_COUNT = 16640
SAMPLE_RATE = 44100
_CAPABILITY_TOKEN = object()


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def canonical_json(value: object) -> bytes:
    return json.dumps(
        value, sort_keys=True, ensure_ascii=False, allow_nan=False,
        separators=(",", ":"),
    ).encode("utf-8") + b"\n"


def _pairs(pairs: Sequence[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"H25 duplicate JSON key: {key!r}.")
        result[key] = value
    return result


def parse_sealed_json(raw: bytes, label: str) -> dict[str, object]:
    if raw.startswith(b"\xef\xbb\xbf") or b"\r" in raw:
        raise ValueError(f"H25 {label} must be UTF-8 without BOM and LF-only.")
    try:
        value = json.loads(
            raw.decode("utf-8"), object_pairs_hook=_pairs,
            parse_constant=lambda token: (_ for _ in ()).throw(
                ValueError(f"H25 forbidden JSON constant {token}.")
            ),
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"H25 invalid {label} JSON.") from exc
    if type(value) is not dict:
        raise ValueError(f"H25 {label} root must be an object.")
    return value


def _git(repository: Path, *args: str) -> str:
    return subprocess.check_output(
        ["git", *args], cwd=repository, text=True, encoding="utf-8"
    ).strip()


def _bound(repository: Path, relative: str) -> Path:
    root = repository.resolve(strict=True)
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError("H25 sealed path escapes repository.") from exc
    return path


@dataclass(frozen=True)
class H25DormantMaterializationPlan:
    repository: Path
    contract: Mapping[str, object]
    specifications: Mapping[str, object]
    population: Mapping[str, object]
    tests: Mapping[str, object]
    fixtures: tuple[Mapping[str, object], ...]


class H25MaterializationCapability:
    """Factory-only authority.  No factory exists in this commit."""

    __slots__ = ("plan", "implementation_commit", "source_blob", "_token")

    def __init__(
        self, plan: H25DormantMaterializationPlan, implementation_commit: str,
        source_blob: str, *, _token: object = None,
    ) -> None:
        if _token is not _CAPABILITY_TOKEN:
            raise PermissionError("H25 materializer capability has no authorized issuer.")
        self.plan = plan
        self.implementation_commit = implementation_commit
        self.source_blob = source_blob
        self._token = _token


def load_dormant_plan(repository_root: Path) -> H25DormantMaterializationPlan:
    """Perform the standard-library-only contract portion of preflight."""

    repository = repository_root.resolve(strict=True)
    contract_path = _bound(repository, str(CONTRACT_RELATIVE_PATH))
    contract_raw = contract_path.read_bytes()
    if _sha256(contract_raw) != CONTRACT_RAW_SHA256:
        raise ValueError("H25 materialization contract SHA mismatch.")
    contract = parse_sealed_json(contract_raw, "materialization contract")
    sealed = contract["sealed_inputs"]
    parsed: dict[str, Mapping[str, object]] = {}
    for name in ("scientific_contract", "fixture_specifications", "population_manifest", "test_manifest"):
        binding = sealed[name]
        raw = _bound(repository, binding["path"]).read_bytes()
        if len(raw) != binding.get("size_bytes", len(raw)) or _sha256(raw) != binding["raw_sha256"]:
            raise ValueError(f"H25 sealed {name} bytes mismatch.")
        parsed[name] = parse_sealed_json(raw, name)
    specifications = parsed["fixture_specifications"]
    population = parsed["population_manifest"]
    fixtures = tuple(specifications["fixtures"])
    ids = population["ordered_fixture_ids"]
    if len(fixtures) != 36 or [item["id"] for item in fixtures] != ids or len(set(ids)) != 36:
        raise ValueError("H25 fixture identity/order mismatch.")
    if specifications.get("generation_authorized") is not False or population.get("materialized") is not False:
        raise ValueError("H25 dormant source manifests changed authority state.")
    return H25DormantMaterializationPlan(
        repository, contract, specifications, population, parsed["test_manifest"], fixtures
    )


def require_reference_environment_before_numpy(plan: H25DormantMaterializationPlan) -> None:
    expected = plan.contract["reference_runtime_identity"]
    p = expected["platform"]
    py = expected["python"]
    if (
        platform.system() != p["os_system"] or platform.release() != p["os_release"]
        or platform.machine() != p["machine"] or platform.python_implementation() != py["implementation"]
        or platform.python_version() != py["version"] or Path(os.path.realpath(os.sys.executable)) != Path(py["resolved_executable"])
    ):
        raise RuntimeError("H25 reference platform/Python mismatch before NumPy.")
    for key, value in expected["process_environment_exact"].items():
        if os.environ.get(key) != value:
            raise RuntimeError(f"H25 environment mismatch for {key} before NumPy.")
    for section, path_key, size_key, sha_key in (
        ("numpy", "multiarray_extension_path", "multiarray_extension_size_bytes", "multiarray_extension_sha256"),
        ("linear_algebra_backend", "loaded_library_path", "loaded_library_size_bytes", "loaded_library_sha256"),
    ):
        binding = expected[section]
        path = Path(binding[path_key]).resolve(strict=True)
        raw = path.read_bytes()
        if len(raw) != binding[size_key] or _sha256(raw) != binding[sha_key]:
            raise RuntimeError(f"H25 pre-NumPy runtime binary mismatch for {section}.")
    dependency = subprocess.check_output(
        ["otool", "-L", expected["numpy"]["multiarray_extension_path"]],
        text=True, encoding="utf-8",
    )
    backend = expected["linear_algebra_backend"]
    if backend["multiarray_otool_dependency"] not in dependency or "Accelerate.framework" in dependency:
        raise RuntimeError("H25 OpenBLAS/no-Accelerate dependency mismatch before NumPy.")


def _require_output_paths_before_numpy(plan: H25DormantMaterializationPlan) -> None:
    encoding = plan.contract["fixture_artifact_encoding"]
    staging = Path(encoding["private_staging_sibling"])
    success = Path(encoding["reference_mac_population_root"])
    if staging.exists() or success.exists() or staging.is_symlink() or success.is_symlink():
        raise FileExistsError("H25 staging/success path must be absent before NumPy.")
    for target in (staging, success):
        current = target.parent
        while True:
            if current.is_symlink():
                raise ValueError("H25 output path has a symlink ancestor.")
            parent = current.parent
            if parent == current:
                break
            current = parent
    if staging.parent != success.parent or not success.parent.is_dir():
        raise ValueError("H25 staging and success must share one existing parent filesystem.")


def _seed(fixture_id: str) -> int:
    raw = hashlib.sha256(("H25|" + fixture_id + "|noise").encode("utf-8")).digest()
    return int.from_bytes(raw[:8], "little", signed=False)


def _envelope(np: Any, kind: str, onset: int) -> Any:
    g = np.arange(SAMPLE_COUNT, dtype=np.float64)
    out = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    active = g >= onset
    elapsed = g[active] - np.float64(onset)
    if kind == "old":
        out[active] = np.exp(-elapsed / np.float64(8192.0))
    elif kind == "new":
        out[active] = np.minimum(1.0, (elapsed + 1.0) / 64.0) * np.exp(-elapsed / 2048.0)
    elif kind == "sustained":
        out[active] = 1.0
    elif kind == "bell":
        out[active] = np.exp(-elapsed / np.float64(512.0))
    else:
        raise ValueError(f"H25 unknown envelope {kind!r}.")
    return out


def _source(np: Any, pitch: int, params: Mapping[str, object], envelope: Any, partials: Sequence[int]) -> Any:
    g = np.arange(SAMPLE_COUNT, dtype=np.float64)
    result = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    gain = np.float64(params.get("gain", 1.0))
    phase = np.float64(params.get("phase_radians", 0.0))
    cents = np.float64(params.get("cents", 0.0))
    B = np.float64(params.get("B", 0.0))
    f0 = np.float64(440.0 * math.pow(2.0, (pitch - 69.0) / 12.0))
    for harmonic in partials:
        h = np.float64(harmonic)
        frequency = h * f0 * np.exp2(cents / 1200.0) * np.sqrt(1.0 + B * h * h)
        term = gain * envelope * (1.0 / h) * np.sin(
            2.0 * np.pi * frequency * g / np.float64(SAMPLE_RATE) + phase
        )
        result = np.add(result, term, dtype=np.float64)
    return result


def _add_noise(np: Any, clean: Any, fixture_id: str, noise: Mapping[str, object]) -> Any:
    generator = np.random.Generator(np.random.PCG64(_seed(fixture_id)))
    z = generator.standard_normal(SAMPLE_COUNT).astype(np.float64, copy=False)
    if noise["colour"] == "white":
        u = z
    elif noise["colour"] == "pink":
        Z = np.fft.rfft(z)
        Z[0] = np.complex128(complex(0.0, 0.0))
        for k in range(1, len(Z)):
            Z[k] = Z[k] / np.sqrt(np.float64(k))
        u = np.fft.irfft(Z, n=SAMPLE_COUNT).astype(np.float64, copy=False)
    else:
        raise ValueError("H25 noise colour must be white or pink.")
    start = 8192
    count = 8448
    mean = np.float64(0.0)
    for g in range(start, SAMPLE_COUNT):
        mean = np.float64(mean + np.float64(u[g]))
    mean = np.float64(mean / np.float64(count))
    unit = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    square = np.float64(0.0)
    for g in range(start, SAMPLE_COUNT):
        unit[g] = np.float64(u[g] - mean)
        square = np.float64(square + np.float64(unit[g] * unit[g]))
    rms = np.sqrt(np.float64(square / np.float64(count)))
    if not np.isfinite(rms) or not rms > 0:
        raise ValueError("H25 noise RMS invalid.")
    unit[start:] = unit[start:] / rms
    clean_square = np.float64(0.0)
    for g in range(start, SAMPLE_COUNT):
        clean_square = np.float64(clean_square + np.float64(clean[g] * clean[g]))
    clean_rms = np.sqrt(np.float64(clean_square / np.float64(count)))
    if not np.isfinite(clean_rms) or not clean_rms > 0:
        raise ValueError("H25 clean RMS invalid.")
    alpha = np.float64(clean_rms * np.power(10.0, -np.float64(noise["snr_db"]) / 20.0))
    result = clean + alpha * unit
    result[:start] = np.float64(0.0)
    return result


def synthesize_fixture(np: Any, fixture: Mapping[str, object]) -> Any:
    """Synthesize one sealed-format fixture; caller authority is external."""

    family = fixture["family"]
    params = fixture["parameters"]
    result = np.zeros(SAMPLE_COUNT, dtype=np.float64)
    all_partials = tuple(range(1, 9))
    old = _envelope(np, "old", 8192)
    if family in {"IDENTIFIABLE_OVERLAP", "HARMONIC_ONLY", "OVERLAP_WITHOUT_INDEPENDENT_EVIDENCE"}:
        result += _source(np, int(params["old_pitch"]), params, old, all_partials)
    elif family in {"SHARED_PARTIAL_TWO_SOURCE", "ACTIVE_ONLY", "DECAY_NO_ATTACK"}:
        result += _source(np, int(params["old_pitch"]), params, old, all_partials)
    elif family == "NATURAL_HARMONIC":
        result += _source(np, int(params["old_pitch"]), params, old, tuple(params["partial_subset"]))
    elif family == "EXACT_COLLISION_IDENTICAL":
        result += _source(np, int(params["old_pitch"]), params, old, (int(params["collision_harmonic_rank"]),))
    elif family == "MISSING_FUNDAMENTAL":
        result += _source(np, int(params["source_pitch"]), params, old, tuple(params["partial_subset"]))
    elif family == "SYNTHETIC_OOD":
        kind = params["kind"]
        onset = int(params["onset"])
        if kind == "impulse":
            result[onset] = 1.0
        elif kind == "linear_chirp":
            m = np.arange(512, dtype=np.float64)
            w = 0.5 - 0.5 * np.cos(2.0 * np.pi * m / 511.0)
            phase = 2.0 * np.pi * (
                np.float64(params["start_hz"]) * m / SAMPLE_RATE
                + 0.5 * (np.float64(params["end_hz"]) - np.float64(params["start_hz"]))
                * m * m / (SAMPLE_RATE * 511.0)
            )
            result[onset:onset + 512] = w * np.sin(phase)
        elif kind == "inharmonic_bell":
            result += _source(np, int(params["nominal_pitch"]), params, _envelope(np, "bell", onset), all_partials)
        else:
            raise ValueError("H25 unknown OOD kind.")
    elif family != "ISOLATED_NEW":
        raise ValueError(f"H25 unknown fixture family {family!r}.")
    if family in {"IDENTIFIABLE_OVERLAP", "ISOLATED_NEW", "SHARED_PARTIAL_TWO_SOURCE"}:
        result += _source(
            np, int(fixture["candidate_pitch"]), params,
            _envelope(np, "new", int(params.get("new_onset", 16128))), all_partials,
        )
    if params.get("noise") is not None:
        result = _add_noise(np, result, fixture["id"], params["noise"])
    if result.dtype != np.dtype("float64") or result.shape != (SAMPLE_COUNT,) or not np.all(np.isfinite(result)):
        raise ValueError("H25 synthesized waveform invariant failure.")
    if result[:8192].tobytes() != bytes(8192 * 8):
        raise ValueError("H25 pre-support samples are not bit-exact positive zero.")
    return result


def encode_waveform(np: Any, waveform: Any) -> bytes:
    raw = np.asarray(waveform, dtype="<f8", order="C").tobytes(order="C")
    if len(raw) != 133120:
        raise ValueError("H25 waveform byte count mismatch.")
    return raw


def artifact_bytes(np: Any, specifications: Mapping[str, object], fixture: Mapping[str, object], ordinal: int) -> tuple[bytes, bytes, bytes]:
    waveform = encode_waveform(np, synthesize_fixture(np, fixture))
    fixture_record = {
        "schema_version": 1, "fixture_id": fixture["id"], "ordinal": ordinal,
        "population_namespace": POPULATION_ID, "source_fixture_record": fixture,
        "source_fixture_record_sha256": _sha256(canonical_json(fixture)),
    }
    target = {
        "schema_version": 1, "fixture_id": fixture["id"], "category": fixture["category"],
        "family": fixture["family"], "oracle": specifications["base_families"][fixture["family"]]["oracle"],
    }
    return waveform, canonical_json(fixture_record), canonical_json(target)


def recompute_fixture_artifacts(np: Any, plan: H25DormantMaterializationPlan) -> tuple[tuple[bytes, bytes, bytes], ...]:
    return tuple(artifact_bytes(np, plan.specifications, fixture, i) for i, fixture in enumerate(plan.fixtures))


def _write_new(path: Path, raw: bytes) -> None:
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb", closefd=False) as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
    finally:
        os.close(fd)


def _fsync_directory(path: Path) -> None:
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _artifact_names(ordinal: int, fixture_id: str) -> tuple[str, str, str]:
    stem = f"{ordinal:06d}__{fixture_id}"
    return stem + ".f64le", stem + ".fixture.json", stem + ".target.json"


def _verify_runtime_after_numpy(np: Any, plan: H25DormantMaterializationPlan) -> None:
    expected = plan.contract["reference_runtime_identity"]
    if getattr(np, "__version__", None) != expected["numpy"]["distribution_version"]:
        raise RuntimeError("H25 NumPy distribution mismatch.")
    if np.dtype("float64").itemsize != 8 or np.little_endian is not True:
        raise RuntimeError("H25 NumPy float64/little-endian runtime mismatch.")


def _build_index_row(
    ordinal: int, fixture: Mapping[str, object], names: tuple[str, str, str],
    artifacts: tuple[bytes, bytes, bytes],
) -> dict[str, object]:
    waveform_name, fixture_name, target_name = names
    waveform, fixture_raw, target_raw = artifacts
    return {
        "ordinal": ordinal,
        "fixture_id": fixture["id"],
        "category": fixture["category"],
        "family": fixture["family"],
        "waveform_path": "fixtures/" + waveform_name,
        "waveform_size_bytes": len(waveform),
        "waveform_sha256": _sha256(waveform),
        "fixture_record_path": "fixtures/" + fixture_name,
        "fixture_record_size_bytes": len(fixture_raw),
        "fixture_record_sha256": _sha256(fixture_raw),
        "target_record_path": "fixtures/" + target_name,
        "target_record_size_bytes": len(target_raw),
        "target_record_sha256": _sha256(target_raw),
    }


def verify_and_recompute_staging(
    np: Any, plan: H25DormantMaterializationPlan, staging: Path,
    rows: Sequence[Mapping[str, object]],
) -> None:
    """Reopen every staged byte and independently regenerate every fixture."""

    if len(rows) != 36:
        raise ValueError("H25 staged index row count mismatch.")
    second = recompute_fixture_artifacts(np, plan)
    for ordinal, (fixture, row, expected_artifacts) in enumerate(zip(plan.fixtures, rows, second)):
        names = _artifact_names(ordinal, fixture["id"])
        paths = tuple(staging / "fixtures" / name for name in names)
        reopened = tuple(path.read_bytes() for path in paths)
        if reopened != expected_artifacts:
            raise ValueError(f"H25 byte recomputation mismatch for {fixture['id']}.")
        rebuilt = _build_index_row(ordinal, fixture, names, expected_artifacts)
        if dict(row) != rebuilt:
            raise ValueError(f"H25 index binding mismatch for {fixture['id']}.")
    index_raw = (staging / "population_index.jsonl").read_bytes()
    if index_raw != b"".join(canonical_json(dict(row)) for row in rows):
        raise ValueError("H25 population index bytes mismatch.")


def _materialize_claimed(
    capability: H25MaterializationCapability, np: Any,
) -> Path:
    plan = capability.plan
    _verify_runtime_after_numpy(np, plan)
    encoding = plan.contract["fixture_artifact_encoding"]
    staging = Path(encoding["private_staging_sibling"])
    success = Path(encoding["reference_mac_population_root"])
    if staging.exists() or success.exists() or staging.is_symlink() or success.is_symlink():
        raise FileExistsError("H25 staging/success path must be absent.")
    staging.mkdir(mode=0o700, parents=False)
    fixtures_dir = staging / "fixtures"
    fixtures_dir.mkdir(mode=0o700)
    rows: list[dict[str, object]] = []
    try:
        index_path = staging / "population_index.jsonl"
        for ordinal, fixture in enumerate(plan.fixtures):
            artifacts = artifact_bytes(np, plan.specifications, fixture, ordinal)
            names = _artifact_names(ordinal, fixture["id"])
            for name, raw in zip(names, artifacts):
                _write_new(fixtures_dir / name, raw)
            row = _build_index_row(ordinal, fixture, names, artifacts)
            rows.append(row)
            fd = os.open(index_path, os.O_WRONLY | os.O_CREAT | os.O_APPEND, 0o600)
            try:
                os.write(fd, canonical_json(row))
                os.fsync(fd)
            finally:
                os.close(fd)
        runtime = plan.contract["reference_runtime_identity"]
        provenance = {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h25_materialization_runtime_provenance",
            "runtime_identity": runtime,
            "runtime_identity_sha256": _sha256(canonical_json(runtime)),
            "materialization_contract_sha256": CONTRACT_RAW_SHA256,
            "implementation_commit": capability.implementation_commit,
            "materializer_source_git_blob": capability.source_blob,
            "preflight_status": "PASSED_BEFORE_SCIENTIFIC_NUMPY_IMPORT",
        }
        _write_new(staging / "runtime_provenance.json", canonical_json(provenance))
        ids_raw = b"".join((fixture["id"] + "\n").encode("utf-8") for fixture in plan.fixtures)
        receipt = dict(plan.contract["population_receipt_contract"]["fixed_values"])
        receipt.update({
            "ordered_fixture_ids_sha256": _sha256(ids_raw),
            "population_index_sha256": _sha256(index_path.read_bytes()),
            "scientific_contract_sha256": plan.contract["sealed_inputs"]["scientific_contract"]["raw_sha256"],
            "fixture_specifications_sha256": plan.contract["sealed_inputs"]["fixture_specifications"]["raw_sha256"],
            "population_manifest_sha256": plan.contract["sealed_inputs"]["population_manifest"]["raw_sha256"],
            "test_manifest_sha256": plan.contract["sealed_inputs"]["test_manifest"]["raw_sha256"],
            "materialization_contract_sha256": CONTRACT_RAW_SHA256,
            "implementation_commit": capability.implementation_commit,
            "materializer_source_git_blob": capability.source_blob,
            "runtime_identity": runtime,
        })
        _write_new(staging / "population_receipt.json", canonical_json(receipt))
        verify_and_recompute_staging(np, plan, staging, rows)
        for path in (staging / "runtime_provenance.json", staging / "population_receipt.json"):
            if not path.read_bytes():
                raise ValueError("H25 empty receipt/provenance file.")
        _fsync_directory(fixtures_dir)
        _fsync_directory(staging)
        os.replace(staging, success)
        _fsync_directory(success.parent)
        return success
    except BaseException:
        # Private staging is deliberately retained for forensics and is never authoritative.
        raise


def materialize_and_publish_h25_population(
    capability: H25MaterializationCapability,
    numpy_loader: Callable[[], Any] = lambda: __import__("numpy"),
) -> Path:
    """Dormant operational boundary; unreachable without a future issuer."""

    if not isinstance(capability, H25MaterializationCapability) or capability._token is not _CAPABILITY_TOKEN:
        raise PermissionError("H25 materialization requires an attested capability.")
    plan = capability.plan
    require_reference_environment_before_numpy(plan)
    _require_output_paths_before_numpy(plan)
    repository = plan.repository
    if _git(repository, "status", "--porcelain"):
        raise RuntimeError("H25 materialization requires a clean worktree.")
    if _git(repository, "rev-parse", "HEAD") != capability.implementation_commit:
        raise RuntimeError("H25 implementation commit mismatch.")
    if _git(repository, "rev-parse", f"HEAD:src/polyphonic/harmonic_censoring_h25_population_materializer.py") != capability.source_blob:
        raise RuntimeError("H25 materializer source blob mismatch.")
    np = numpy_loader()
    return _materialize_claimed(capability, np)


__all__ = [
    "H25DormantMaterializationPlan", "H25MaterializationCapability",
    "load_dormant_plan", "require_reference_environment_before_numpy",
    "synthesize_fixture", "encode_waveform", "artifact_bytes",
    "recompute_fixture_artifacts", "verify_and_recompute_staging",
    "materialize_and_publish_h25_population",
]
