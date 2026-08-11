"""Dormant real H26 P0 one-shot boundary.

The checked-in lifecycle is deliberately non-executable.  A later, separately
reviewed lifecycle-only commit is required before this module can publish the
single durable claim that consumes P0.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import threading
import weakref
from typing import Any, Callable, Mapping, Sequence

from .harmonic_censoring_h26_contract import (
    FIXTURE_SPECIFICATIONS_PATH,
    FIXTURE_SPECIFICATIONS_SHA256,
    SCIENTIFIC_CONTRACT_PATH,
    SCIENTIFIC_CONTRACT_SHA256,
    TEST_MANIFEST_PATH,
    TEST_MANIFEST_SHA256,
    H26DormantPlan,
    canonical_json_bytes,
    load_h26_dormant_plan,
    parse_strict_json,
)
from .harmonic_censoring_h26_recomputer import (
    H26TranscriptRecord,
    recompute_h26_evidence_from_raw_operands,
    recompute_h26_resolution,
    validate_transcript_prefix,
)
from . import run_h26_materialization_operational as stop4

CONTRACT_PATH = Path("configs/harmonic_censoring_h26_p0_operational_entrypoint_contract.json")
ADMIN_ROOT = Path("/Users/amcarene/h26-admin")
POPULATION_ROOT = ADMIN_ROOT / "population/h26-synthetic-v1"
OUTPUT_ROOT = ADMIN_ROOT / "science/p0"
CLAIM_PATH = OUTPUT_ROOT / "claim.json"
EVIDENCE_DIRECTORY = OUTPUT_ROOT / "evidence"
TRANSCRIPT_PATH = OUTPUT_ROOT / "transcript.json"
RECEIPT_PATH = OUTPUT_ROOT / "receipt.json"
ACK = "H26_P0_EXECUTE"
AUTHORIZATION_COMMIT = "H26_P0_AUTHORIZATION_COMMIT"
STOP4_COMMIT = "4fd020c4689ded03698bb611068eccd2321ecf1e"
AUTHORITY_ID = "h26-materialization-authority-v1-1918eb0f2b74754fe79c50c994b9b038b5a27afcf80dd3ccf2d28825355a0be2"
AUTHORITY_SHA = "ed0d55afe2923e4996f19e45be5aff99e2efab2f45ee6143c28f1a8ee6f2e805"
SEAL_SHA = "f1118ccaae58bbbe90da3bcba1eab978ccd01b826f795fe163f409ae2e63bc42"
POPULATION_INDEX_SHA = "b0045797b08ef2ebbfaf7e1dda0c10f213eec3d8b3a3daaa31c8153dd842b4a7"
P0_IDS = tuple(f"H26-T-P0-{index:03d}" for index in range(1, 10))
SOURCE_BLOBS = {
    SCIENTIFIC_CONTRACT_PATH: "70d87829e5b32b8fba2ad4453d9308644d1a47e4",
    FIXTURE_SPECIFICATIONS_PATH: "c006d91f4cf61a86b169ec824b8adb95686749c9",
    TEST_MANIFEST_PATH: "a1e41dd6d7deb8599e65feef220a425e463e3b99",
    Path("src/polyphonic/harmonic_censoring_h26_engine.py"): "729a989766fc05c9e5149877b3c3b9a68e141fcd",
    Path("src/polyphonic/harmonic_censoring_h26_recomputer.py"): "2e7fc04c6e12234f39d7722ad156019511c5d63e",
    Path("src/polyphonic/harmonic_censoring_h26_materializer.py"): "2991c69db8a8816d0261c1fb6bb4e339e9408c11",
}
TERMINAL_PASS = "H26_P0_PASSED_STOP_BEFORE_P1"
TERMINAL_FAIL = "H26_P0_FAILED_KILL_STOP"
TERMINAL_INCONCLUSIVE = "H26_P0_INCONCLUSIVE_CONSUMED"

_BOUNDARIES: dict[int, weakref.ReferenceType["_H26P0Boundary"]] = {}
_ENGINE_ADAPTER_LOCK = threading.Lock()


class _H26P0Boundary:
    __slots__ = ("head", "claim_sha256", "claim_path", "population_index_sha256", "__weakref__")

    def __new__(cls) -> "_H26P0Boundary":
        raise TypeError("H26 P0 boundary has no public constructor")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _git(*args: str) -> str:
    return subprocess.check_output(
        ("git", *args), cwd=_repo_root(), text=True, encoding="utf-8"
    ).strip()


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_contract() -> Mapping[str, Any]:
    value = parse_strict_json((_repo_root() / CONTRACT_PATH).read_bytes(), str(CONTRACT_PATH))
    lifecycle = (
        value.get("status"), value.get("real_execution_authorized"), value.get("next_action")
    )
    allowed = {
        (
            "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_P0",
            False,
            "External review before P0 lifecycle activation",
        ),
        (
            "AUTHORIZED_REAL_P0_ONE_SHOT",
            True,
            "Run the single authorized H26 P0 invocation, then stop for external review",
        ),
    }
    exact = {
        "schema_identity": "H26_P0_OPERATIONAL_ENTRYPOINT_V1",
        "schema_version": 1,
        "approved_stop4_archive_commit": STOP4_COMMIT,
        "administrative_root": "/Users/amcarene/h26-admin",
        "population_root": "/Users/amcarene/h26-admin/population/h26-synthetic-v1",
        "materialization_authority_id": AUTHORITY_ID,
        "materialization_authority_raw_sha256": AUTHORITY_SHA,
        "materialization_authority_seal_raw_sha256": SEAL_SHA,
        "population_index_raw_sha256": POPULATION_INDEX_SHA,
        "runtime_artifact_sha256": {
            "authority": stop4.RUNTIME_SHAS["authority"],
            "claim": stop4.RUNTIME_SHAS["claim"],
            "observer_entry": stop4.RUNTIME_SHAS["observer-entry"],
            "runtime_record": stop4.RUNTIME_SHAS["runtime-record"],
            "receipt": stop4.RUNTIME_SHAS["receipt"],
        },
        "scientific_bindings": {
            "scientific_preregistration_git_blob_sha": SOURCE_BLOBS[SCIENTIFIC_CONTRACT_PATH],
            "scientific_preregistration_raw_sha256": SCIENTIFIC_CONTRACT_SHA256,
            "fixture_specifications_git_blob_sha": SOURCE_BLOBS[FIXTURE_SPECIFICATIONS_PATH],
            "fixture_specifications_raw_sha256": FIXTURE_SPECIFICATIONS_SHA256,
            "test_manifest_git_blob_sha": SOURCE_BLOBS[TEST_MANIFEST_PATH],
            "test_manifest_raw_sha256": TEST_MANIFEST_SHA256,
            "engine_git_blob_sha": SOURCE_BLOBS[Path("src/polyphonic/harmonic_censoring_h26_engine.py")],
            "recomputer_git_blob_sha": SOURCE_BLOBS[Path("src/polyphonic/harmonic_censoring_h26_recomputer.py")],
            "materializer_git_blob_sha": SOURCE_BLOBS[Path("src/polyphonic/harmonic_censoring_h26_materializer.py")],
        },
        "phase": "P0",
        "test_ids": list(P0_IDS),
        "scientific_runner_invocations_maximum": 1,
        "retry_allowed": False,
        "p1_authorized": False,
        "p2_authorized": False,
        "locked_test_used": False,
        "training_calibration_model_access_authorized": False,
        "acknowledgement_variable": ACK,
        "authorization_commit_variable": AUTHORIZATION_COMMIT,
        "output_root": "/Users/amcarene/h26-admin/science/p0",
        "claim_path": "/Users/amcarene/h26-admin/science/p0/claim.json",
        "evidence_directory": "/Users/amcarene/h26-admin/science/p0/evidence",
        "transcript_path": "/Users/amcarene/h26-admin/science/p0/transcript.json",
        "receipt_path": "/Users/amcarene/h26-admin/science/p0/receipt.json",
        "terminal_statuses": [TERMINAL_PASS, TERMINAL_FAIL, TERMINAL_INCONCLUSIVE],
    }
    comparable = dict(value)
    for key in ("status", "real_execution_authorized", "next_action"):
        comparable.pop(key, None)
    if lifecycle not in allowed or comparable != exact:
        raise ValueError("H26 P0 operational contract mismatch")
    return value


def _require_execution_boundary() -> str:
    contract = _load_contract()
    if contract["real_execution_authorized"] is not True:
        raise PermissionError("H26 P0 real execution is not externally authorized")
    if platform.system() != "Darwin":
        raise RuntimeError("H26 P0 requires macOS")
    if os.environ.get(ACK) != "1":
        raise PermissionError("H26 P0 acknowledgement missing")
    head = _git("rev-parse", "HEAD")
    if os.environ.get(AUTHORIZATION_COMMIT) != head:
        raise PermissionError("H26 P0 authorization commit must equal HEAD")
    if _git("status", "--porcelain=v1"):
        raise PermissionError("H26 P0 requires a clean worktree")
    runtime_contract = stop4.qualifier.load_runtime_qualification_contract()
    for key, expected in runtime_contract.process_environment_exact:
        if os.environ.get(key) != expected:
            raise PermissionError(f"H26 P0 environment mismatch: {key}")
    return head


def _regular_file(path: Path, label: str) -> Path:
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f"H26 P0 {label} must be a regular non-symlink file")
    return path


def _require_stop3_stop4() -> None:
    runtime_values = stop4._read_runtime_artifacts()
    stop4._require_live_runtime_matches_stop3(runtime_values[3])
    authority = _regular_file(stop4.AUTHORITY_DIRECTORY / f"{AUTHORITY_SHA}.json", "authority")
    seal = _regular_file(stop4.SEAL_DIRECTORY / f"{AUTHORITY_SHA}.json", "authority seal")
    if _sha(authority) != AUTHORITY_SHA:
        raise ValueError("H26 P0 authority SHA mismatch")
    authority_value = stop4.runtime.parse_canonical_json_bytes(authority.read_bytes())
    if authority_value.get("authority_id") != AUTHORITY_ID:
        raise ValueError("H26 P0 authority ID mismatch")
    if _sha(seal) != SEAL_SHA or seal.read_bytes() != stop4._seal(AUTHORITY_SHA):
        raise ValueError("H26 P0 authority seal mismatch")


def _bound_population_file(root: Path, relative: object, digest: object) -> None:
    if type(relative) is not str or type(digest) is not str:
        raise ValueError("H26 P0 population path/SHA schema mismatch")
    lexical = root / relative
    if lexical.is_symlink():
        raise ValueError("H26 P0 population symlink forbidden")
    resolved = lexical.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("H26 P0 population path escapes root") from exc
    if not resolved.is_file() or _sha(resolved) != digest:
        raise ValueError("H26 P0 population file integrity mismatch")


def _preflight_population(plan: H26DormantPlan) -> Mapping[str, Any]:
    root = POPULATION_ROOT.resolve(strict=True)
    if root != POPULATION_ROOT or POPULATION_ROOT.is_symlink() or not root.is_dir():
        raise ValueError("H26 P0 population root mismatch")
    index_path = _regular_file(root / "population_index.json", "population index")
    raw = index_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != POPULATION_INDEX_SHA:
        raise ValueError("H26 P0 population-index SHA mismatch")
    index = parse_strict_json(raw, "population index")
    records, p2_records = index.get("records"), index.get("p2_records")
    if index.get("schema_version") != 2 or index.get("population_namespace") != "H26_SYNTHETIC_V1":
        raise ValueError("H26 P0 population schema/namespace mismatch")
    if type(records) is not list or len(records) != 40:
        raise ValueError("H26 P0 baseline cardinality mismatch")
    if [item.get("fixture_id") for item in records if type(item) is dict] != list(plan.fixture_ids):
        raise ValueError("H26 P0 baseline order mismatch")
    if type(p2_records) is not list or len(p2_records) != 153:
        raise ValueError("H26 P0 P2 cardinality mismatch")
    identities: set[bytes] = set()
    for record in (*records, *p2_records):
        if type(record) is not dict:
            raise ValueError("H26 P0 population record schema mismatch")
        identity = canonical_json_bytes({
            key: record.get(key) for key in ("fixture_id", "test_id", "grid_id", "cell")
        })
        if identity in identities:
            raise ValueError("H26 P0 duplicate population identity")
        identities.add(identity)
        _bound_population_file(root, record.get("waveform"), record.get("waveform_sha256"))
        _bound_population_file(root, record.get("sample_valid"), record.get("sample_valid_sha256"))
        if record.get("alternate_waveform") is not None or record.get("alternate_waveform_sha256") is not None:
            _bound_population_file(
                root, record.get("alternate_waveform"), record.get("alternate_waveform_sha256")
            )
    return index


def _require_scientific_bindings() -> None:
    root = _repo_root()
    for relative, expected_blob in SOURCE_BLOBS.items():
        if _git("rev-parse", f"HEAD:{relative.as_posix()}") != expected_blob:
            raise ValueError(f"H26 P0 source blob mismatch: {relative}")
        if relative in {
            SCIENTIFIC_CONTRACT_PATH, FIXTURE_SPECIFICATIONS_PATH, TEST_MANIFEST_PATH
        }:
            expected_raw = {
                SCIENTIFIC_CONTRACT_PATH: SCIENTIFIC_CONTRACT_SHA256,
                FIXTURE_SPECIFICATIONS_PATH: FIXTURE_SPECIFICATIONS_SHA256,
                TEST_MANIFEST_PATH: TEST_MANIFEST_SHA256,
            }[relative]
            if _sha(root / relative) != expected_raw:
                raise ValueError(f"H26 P0 scientific raw SHA mismatch: {relative}")


def _require_output_slots_absent() -> None:
    if OUTPUT_ROOT.is_symlink():
        raise ValueError("H26 P0 output root symlink forbidden")
    if OUTPUT_ROOT.exists() and (
        not OUTPUT_ROOT.is_dir() or any(OUTPUT_ROOT.iterdir())
    ):
        raise FileExistsError("H26 P0 output root must be absent or empty")
    for path in (CLAIM_PATH, TRANSCRIPT_PATH, RECEIPT_PATH):
        if path.exists() or path.with_name("." + path.name + ".part").exists():
            raise FileExistsError(f"H26 P0 output slot exists: {path}")
    if EVIDENCE_DIRECTORY.exists():
        raise FileExistsError("H26 P0 evidence directory already exists")


def _json_safe(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if type(value) is float and not math.isfinite(value):
        return "Infinity" if value > 0 else "-Infinity"
    return value


def _publish(path: Path, value: Mapping[str, Any] | Sequence[Any]) -> tuple[bytes, str]:
    raw = canonical_json_bytes(_json_safe(value), line=True)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    stop4._publish(path, raw)
    return raw, hashlib.sha256(raw).hexdigest()


def _claim(head: str) -> Mapping[str, Any]:
    return {
        "schema_identity": "H26_P0_CLAIM_V1",
        "schema_version": 1,
        "authorization_commit": head,
        "approved_stop4_archive_commit": STOP4_COMMIT,
        "materialization_authority_id": AUTHORITY_ID,
        "materialization_authority_raw_sha256": AUTHORITY_SHA,
        "materialization_authority_seal_raw_sha256": SEAL_SHA,
        "population_index_raw_sha256": POPULATION_INDEX_SHA,
        "runtime_record_raw_sha256": stop4.RUNTIME_SHAS["runtime-record"],
        "scientific_preregistration_raw_sha256": SCIENTIFIC_CONTRACT_SHA256,
        "fixture_specifications_raw_sha256": FIXTURE_SPECIFICATIONS_SHA256,
        "test_manifest_raw_sha256": TEST_MANIFEST_SHA256,
        "engine_git_blob_sha": SOURCE_BLOBS[Path("src/polyphonic/harmonic_censoring_h26_engine.py")],
        "recomputer_git_blob_sha": SOURCE_BLOBS[Path("src/polyphonic/harmonic_censoring_h26_recomputer.py")],
        "materializer_git_blob_sha": SOURCE_BLOBS[Path("src/polyphonic/harmonic_censoring_h26_materializer.py")],
        "phase": "P0",
        "test_ids": list(P0_IDS),
        "single_use": True,
        "retry_allowed": False,
    }


def _mint_boundary(head: str, claim_sha: str) -> _H26P0Boundary:
    if _sha(_regular_file(CLAIM_PATH, "claim")) != claim_sha:
        raise PermissionError("durable H26 P0 claim mismatch")
    boundary = object.__new__(_H26P0Boundary)
    boundary.head = head
    boundary.claim_sha256 = claim_sha
    boundary.claim_path = CLAIM_PATH
    boundary.population_index_sha256 = POPULATION_INDEX_SHA
    identity = id(boundary)

    def cleanup(reference: weakref.ReferenceType[_H26P0Boundary]) -> None:
        if _BOUNDARIES.get(identity) is reference:
            _BOUNDARIES.pop(identity, None)

    _BOUNDARIES[identity] = weakref.ref(boundary, cleanup)
    return boundary


def _require_boundary(value: object) -> _H26P0Boundary:
    reference = _BOUNDARIES.get(id(value))
    if type(value) is not _H26P0Boundary or reference is None or reference() is not value:
        raise PermissionError("attested H26 P0 boundary required")
    if _git("rev-parse", "HEAD") != value.head or _git("status", "--porcelain=v1"):
        raise PermissionError("H26 P0 HEAD/worktree changed after claim")
    if _sha(_regular_file(value.claim_path, "claim")) != value.claim_sha256:
        raise PermissionError("H26 P0 claim changed after publication")
    if _sha(_regular_file(POPULATION_ROOT / "population_index.json", "population index")) != value.population_index_sha256:
        raise PermissionError("H26 P0 population index changed after claim")
    return value


class _Evaluator:
    def __init__(self, np: Any, plan: H26DormantPlan, boundary: _H26P0Boundary) -> None:
        from . import harmonic_censoring_h26_engine as engine_module
        from . import harmonic_censoring_h26_materializer as materializer_module

        self.np, self.plan, self.boundary = np, plan, boundary
        self.engine = engine_module
        self.materializer = materializer_module
        self._cache: dict[str, Any] = {}
        self._capability = object()

    def evidence(self, fixture_id: str) -> Any:
        _require_boundary(self.boundary)
        if fixture_id not in self._cache:
            observation = self.materializer.bind_h26_population_observation(
                self.np, self.plan, POPULATION_ROOT,
                expected_population_index_sha256=POPULATION_INDEX_SHA,
                fixture_id=fixture_id,
            )
            self._cache[fixture_id] = self.engine.produce_h26_fixture_evidence(
                self.np, self._capability, fixture_id=fixture_id, observation=observation
            )
        return self._cache[fixture_id]

    @staticmethod
    def _outcome(record: Any) -> str:
        return str(record.resolution["outcome"])

    def run(self, test_id: str) -> Mapping[str, Any]:
        method = getattr(self, "_" + test_id.rsplit("-", 1)[1])
        assertions = dict(method())
        return {
            "test_id": test_id,
            "assertions": assertions,
            "passed": all(value is True for value in assertions.values()),
            "fixture_evidence_sha256": {
                fixture_id: hashlib.sha256(canonical_json_bytes(_json_safe({
                    "measurement": record.measurement,
                    "resolution": record.resolution,
                    "operands": record.operands,
                }), line=True)).hexdigest()
                for fixture_id, record in sorted(self._cache.items())
            },
        }

    def _001(self) -> Mapping[str, bool]:
        return {
            "fixtures_40_unique_ordered": len(self.plan.fixture_ids) == len(set(self.plan.fixture_ids)) == 40,
            "tests_27_unique_ordered": len(self.plan.test_ids) == len(set(self.plan.test_ids)) == 27,
            "phases_9_9_9": tuple(test.phase for test in self.plan.tests) == ("P0",) * 9 + ("P1",) * 9 + ("P2",) * 9,
            "p0_ids_exact": self.plan.test_ids[:9] == P0_IDS,
        }

    def _002(self) -> Mapping[str, bool]:
        expected = {
            "H26-F-P01": "BIRTH_SUPPORTED", "H26-F-N01": "NO_BIRTH",
            "H26-F-H01": "ALREADY_ACTIVE_HISTORY", "H26-F-A01": "AMBIGUOUS",
        }
        return {fixture_id: self._outcome(self.evidence(fixture_id)) == outcome for fixture_id, outcome in expected.items()}

    def _003(self) -> Mapping[str, bool]:
        result: dict[str, bool] = {}
        for fixture_id in ("H26-F-P01", "H26-F-P04", "H26-F-P07", "H26-F-P09"):
            record = self.evidence(fixture_id)
            measurement = dict(record.measurement)
            result[fixture_id + "_complete"] = (
                self._outcome(record) == "BIRTH_SUPPORTED"
                and record.resolution["positive_certificate_complete"] is True
            )
            inverses = []
            for field, replacement in (
                ("exclusive_energy_ratios", tuple(0.0 for _ in measurement["exclusive_energy_ratios"])),
                ("onset_rise", 0.0),
                ("active_only_residual_improvement", 0.0),
            ):
                changed = dict(measurement); changed[field] = replacement
                inverses.append(recompute_h26_resolution(self.plan, fixture_id=fixture_id, measurement=changed).outcome != "BIRTH_SUPPORTED")
            result[fixture_id + "_component_removals"] = all(inverses)
        return result

    def _004(self) -> Mapping[str, bool]:
        result = {
            fixture_id + "_negative": (
                self._outcome(self.evidence(fixture_id)) == "NO_BIRTH"
                and self.evidence(fixture_id).resolution["negative_certificate_complete"] is True
            ) for fixture_id in ("H26-F-N01", "H26-F-N05", "H26-F-N08")
        }
        result["A07_below_floor_ambiguous"] = self._outcome(self.evidence("H26-F-A07")) == "AMBIGUOUS"
        base = self.evidence("H26-F-N01")
        measurement = dict(base.measurement)
        measurement["candidate_lower_bounds"] = tuple(math.nan for _ in measurement["candidate_lower_bounds"])
        try:
            inverse = recompute_h26_resolution(
                self.plan, fixture_id="H26-F-N01", measurement=measurement
            )
        except ValueError:
            result["bound_absent_not_negative"] = True
        else:
            result["bound_absent_not_negative"] = inverse.outcome != "NO_BIRTH"
        for forbidden in ("target", "caller_supplied_bound"):
            operands = dict(base.operands); operands[forbidden] = True
            try:
                recompute_h26_evidence_from_raw_operands(self.plan, fixture_id="H26-F-N01", operands=operands)
            except ValueError:
                result[forbidden + "_rejected"] = True
            else:
                result[forbidden + "_rejected"] = False
        return result

    def _005(self) -> Mapping[str, bool]:
        return {
            fixture_id: (
                self._outcome(self.evidence(fixture_id)) == "AMBIGUOUS"
                and self.evidence(fixture_id).measurement["observation_equivalent"] is True
            ) for fixture_id in tuple(f"H26-F-A{i:02d}" for i in range(1, 7))
        }

    def _006(self) -> Mapping[str, bool]:
        return {fixture_id: self._outcome(self.evidence(fixture_id)) == "AMBIGUOUS" for fixture_id in tuple(f"H26-F-A{i:02d}" for i in range(7, 13))}

    def _007(self) -> Mapping[str, bool]:
        hop = int(self.plan.contract["causal_contract"]["hop_samples"])
        result: dict[str, bool] = {}
        for fixture_id in ("H26-F-P02", "H26-F-N02", "H26-F-H02", "H26-F-A02"):
            operands = self.evidence(fixture_id).operands
            result[fixture_id] = (
                operands["resolution_hop_end"] - operands["proposal_hop_end"] == hop
                and operands["maximum_sample_read"] <= operands["proposal_hop_end"]
                and operands["state_before"] == "PENDING_NEW"
                and operands["state_after"] != "PENDING_NEW"
            )
        return result

    def _008(self) -> Mapping[str, bool]:
        forbidden = {"expected", "category", "family", "target", "ground_truth_onset"}
        result: dict[str, bool] = {}
        for fixture_id in ("H26-F-P03", "H26-F-N03", "H26-F-H03", "H26-F-A03"):
            operands = dict(self.evidence(fixture_id).operands)
            result[fixture_id + "_clean"] = not bool(forbidden & set(operands))
            for field in forbidden:
                injected = dict(operands); injected[field] = "oracle"
                try:
                    recompute_h26_evidence_from_raw_operands(self.plan, fixture_id=fixture_id, operands=injected)
                except ValueError:
                    pass
                else:
                    result[fixture_id + "_injections"] = False
                    break
            else:
                result[fixture_id + "_injections"] = True
        return result

    def _009(self) -> Mapping[str, bool]:
        fixtures = ("H26-F-P10", "H26-F-N10", "H26-F-H08", "H26-F-A12")
        result: dict[str, bool] = {}
        corruption_detected = {key: False for key in (
            "missing-required-operand", "forbidden-oracle-field-added",
            "future-read-injected", "terminal-state-corrupted",
            "pitch-dilution-order-corrupted",
        )}
        for fixture_id in fixtures:
            record = self.evidence(fixture_id)
            recomputed = recompute_h26_evidence_from_raw_operands(self.plan, fixture_id=fixture_id, operands=record.operands)
            result[fixture_id + "_recomputed"] = (
                recomputed.resolution.outcome == record.resolution["outcome"]
                and recomputed.resolution.positive_certificate_complete == record.resolution["positive_certificate_complete"]
                and recomputed.resolution.negative_certificate_complete == record.resolution["negative_certificate_complete"]
            )
            variants: dict[str, dict[str, Any]] = {}
            missing = dict(record.operands); missing.pop(next(iter(missing)))
            variants["missing-required-operand"] = missing
            forbidden = dict(record.operands); forbidden["expected"] = "oracle"
            variants["forbidden-oracle-field-added"] = forbidden
            future = dict(record.operands); future["maximum_sample_read"] = int(future["proposal_hop_end"]) + 1
            variants["future-read-injected"] = future
            terminal = dict(record.operands); terminal["state_after"] = "PENDING_NEW"
            variants["terminal-state-corrupted"] = terminal
            if "pitch_dilution_residual_triplets" in record.operands:
                order = dict(record.operands)
                order["pitch_dilution_residual_triplets"] = tuple(reversed(order["pitch_dilution_residual_triplets"]))
                variants["pitch-dilution-order-corrupted"] = order
            for name, operands in variants.items():
                try:
                    recompute_h26_evidence_from_raw_operands(self.plan, fixture_id=fixture_id, operands=operands)
                except (ValueError, KeyError):
                    corruption_detected[name] = True
        result.update({name: detected for name, detected in corruption_detected.items()})
        return result


def _engine_adapter(boundary: _H26P0Boundary, evaluator: _Evaluator) -> Callable[[object], tuple[H26DormantPlan, str]]:
    def adapter(capability: object) -> tuple[H26DormantPlan, str]:
        _require_boundary(boundary)
        if capability is not evaluator._capability:
            raise PermissionError("private H26 P0 engine capability mismatch")
        return evaluator.plan, POPULATION_INDEX_SHA
    return adapter


def _run_p0(boundary: _H26P0Boundary, plan: H26DormantPlan) -> tuple[list[H26TranscriptRecord], str]:
    _require_boundary(boundary)
    import numpy as np
    from . import harmonic_censoring_h26_engine as engine_module

    evaluator = _Evaluator(np, plan, boundary)
    records: list[H26TranscriptRecord] = []
    terminal = TERMINAL_PASS
    with _ENGINE_ADAPTER_LOCK:
        original = engine_module._require_scientific
        engine_module._require_scientific = _engine_adapter(boundary, evaluator)
        try:
            failed = False
            for index, test in enumerate(plan.tests[:9], start=1):
                if failed:
                    records.append(H26TranscriptRecord(test.test_id, test.order, test.phase, "NOT_RUN_BY_KILL_RULE", None, None))
                    continue
                result = evaluator.run(test.test_id)
                status = "PASSED" if result["passed"] is True else "FAILED"
                evidence_value = {
                    "schema_identity": "H26_P0_TEST_EVIDENCE_V1",
                    "schema_version": 1,
                    "test_id": test.test_id,
                    "order": test.order,
                    "phase": test.phase,
                    "fixture_ids": list(test.fixture_ids),
                    **result,
                    "status": status,
                }
                _, evidence_sha = _publish(EVIDENCE_DIRECTORY / f"{index:03d}_{test.test_id}.json", evidence_value)
                records.append(H26TranscriptRecord(
                    test.test_id, test.order, test.phase, status, evidence_sha,
                    test.kill_status if status == "FAILED" else None,
                ))
                if status == "FAILED":
                    failed = True
                    terminal = TERMINAL_FAIL
        finally:
            engine_module._require_scientific = original
    validate_transcript_prefix(plan, records)
    return records, terminal


def execute_h26_p0_once() -> Mapping[str, Any]:
    head = _require_execution_boundary()
    _require_stop3_stop4()
    plan = load_h26_dormant_plan(_repo_root())
    _preflight_population(plan)
    _require_scientific_bindings()
    _require_output_slots_absent()
    claim_raw, claim_sha = _publish(CLAIM_PATH, _claim(head))
    del claim_raw
    boundary = _mint_boundary(head, claim_sha)
    try:
        records, terminal = _run_p0(boundary, plan)
        transcript_value = {
            "schema_identity": "H26_P0_TRANSCRIPT_V1",
            "schema_version": 1,
            "records": [asdict(record) for record in records],
        }
        _, transcript_sha = _publish(TRANSCRIPT_PATH, transcript_value)
        receipt = {
            "schema_identity": "H26_P0_RECEIPT_V1",
            "schema_version": 1,
            "terminal_status": terminal,
            "claim_raw_sha256": claim_sha,
            "transcript_raw_sha256": transcript_sha,
            "scientific_runner_invocations": 1,
            "retry_allowed": False,
            "p1_executed": False,
            "p2_executed": False,
            "locked_test_used": False,
        }
        _publish(RECEIPT_PATH, receipt)
        return receipt
    except BaseException as exc:
        receipt = {
            "schema_identity": "H26_P0_RECEIPT_V1",
            "schema_version": 1,
            "terminal_status": TERMINAL_INCONCLUSIVE,
            "claim_raw_sha256": claim_sha,
            "transcript_raw_sha256": None,
            "scientific_runner_invocations": 1,
            "retry_allowed": False,
            "p1_executed": False,
            "p2_executed": False,
            "locked_test_used": False,
            "error_type": type(exc).__name__,
            "error_message": str(exc),
        }
        if not RECEIPT_PATH.exists():
            _publish(RECEIPT_PATH, receipt)
        raise


def main() -> int:
    if len(sys.argv) != 1:
        raise SystemExit("H26 P0 accepts no arguments")
    print(json.dumps(dict(execute_h26_p0_once()), sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
