from __future__ import annotations

from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import tempfile
import subprocess
import unittest
from unittest.mock import patch
import numpy as np
import uuid

from src.polyphonic.harmonic_censoring_h27_contract import (
    canonical_h27_record_identities, load_h27_dormant_plan,
)
from src.polyphonic.harmonic_censoring_h27_engine import H27EngineResult
from src.polyphonic.harmonic_censoring_h27_recomputer import H27RecomputedResult
from src.polyphonic.harmonic_censoring_h27_scientific_authority import (
    issue_h27_scientific_capability, require_operational_h27_binding,
    verify_durable_h27_claim,
)
import src.polyphonic.harmonic_censoring_h27_scientific_authority as authority
from src.polyphonic.harmonic_censoring_h27_sealed_population_loader import (
    load_h27_sealed_population_bindings,
)
import src.polyphonic.harmonic_censoring_h27_test_executor as executor
from scripts import h27_review5_scientific_execute_once as runner


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_review5_scientific_execution_contract.json"


def _raw(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8") + b"\n"


EXECUTION_ID = "11111111-1111-4111-8111-111111111111"
ACTIVATION_NONCE = "22222222-2222-4222-8222-222222222222"


def _claim_value(index_sha: str, activation_sha: str = "a" * 64) -> dict[str, object]:
    return {
        "schema_identity": "H27_REVIEW5_SCIENTIFIC_CLAIM_V1", "schema_version": 1,
        "authorization_commit": "3" * 40, "execution_id": EXECUTION_ID,
        "activation_nonce": ACTIVATION_NONCE, "activation_sha256": activation_sha,
        "scientific_target_commit": "4" * 40, "review4_terminal_commit": "5" * 40,
        "population_index_sha256": index_sha, "test_ids": list(executor.TEST_IDS),
        "single_use": True, "retry_allowed": False, "locked_test_used": False,
        "training_used": False,
    }


class H27Review5ScientificExecutionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan_source = tempfile.TemporaryDirectory()
        plan_root = Path(self.plan_source.name)
        from src.polyphonic.harmonic_censoring_h27_contract import REVIEWED_GIT_BLOBS
        for relative, blob in REVIEWED_GIT_BLOBS.items():
            destination = plan_root / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(subprocess.check_output(("git", "cat-file", "blob", blob), cwd=ROOT))
        self.plan = load_h27_dormant_plan(plan_root)
        authority._CAPABILITIES.clear()
        authority._BINDINGS.clear()
        authority._CLAIMS.clear()
        authority._ISSUED_ONCE = False
        self.index = self._index_value()
        self.index_raw = _raw(self.index)
        self.claim_source = tempfile.TemporaryDirectory()
        claim_value = _claim_value(hashlib.sha256(self.index_raw).hexdigest())
        claim = runner._canonical(claim_value)
        claim_path = Path(self.claim_source.name) / "claim.json"
        claim_path.write_bytes(claim)
        proof = verify_durable_h27_claim(
            claim_path=claim_path, expected_claim=claim_value,
            expected_claim_sha256=hashlib.sha256(claim).hexdigest(),
            expected_activation_sha256="a" * 64, expected_execution_id=EXECUTION_ID,
            expected_activation_nonce=ACTIVATION_NONCE,
        )
        self.capability = issue_h27_scientific_capability(durable_claim=proof)

    def tearDown(self) -> None:
        authority._CAPABILITIES.clear()
        authority._BINDINGS.clear()
        authority._CLAIMS.clear()
        authority._ISSUED_ONCE = False
        self.claim_source.cleanup()
        self.plan_source.cleanup()

    def _index_value(self):
        records = []
        for identity in canonical_h27_record_identities(self.plan):
            names = ["waveform.f64le", "sample-valid-mask.u8"]
            if identity == "baseline/H27-F-A01" or identity == "baseline/H27-F-A02" or "/H27-F-A01/" in identity or "/H27-F-A02/" in identity:
                names.append("alternate-waveform.f64le")
            records.append({
                "record_identity": identity,
                "record_directory": identity,
                "population_namespace": "H27_SYNTHETIC_V1",
                "payload_sha256": {name: hashlib.sha256(name.encode()).hexdigest() for name in names},
                "candidate_pitch": 40,
                "active_pitches": [],
                "proposal_hop_end": 16383,
                "resolution_hop_end": 16639,
                "cents": 0.0,
                "inharmonicity": 0.0,
            })
        return {
            "schema_version": 1,
            "population_namespace": "H27_SYNTHETIC_V1",
            "record_count": 124,
            "records": records,
        }
    def _population(self, root: Path):
        for record in self.index["records"]:
            directory = root / record["record_identity"]
            directory.mkdir(parents=True)
            for name in record["payload_sha256"]:
                (directory / name).touch()
        raw = self.index_raw
        (root / "population_index.json").write_bytes(raw)
        return raw, load_h27_sealed_population_bindings(
            capability=self.capability, plan=self.plan, population_root=root,
            expected_index_sha256=hashlib.sha256(raw).hexdigest(),
        )

    def _result(self, binding, *, corrupt: bool = False):
        identity = binding.record_identity
        fixture = identity.split("/")[1] if identity.startswith("baseline/") else identity.split("/")[2]
        expected = {str(item["id"]): str(item["expected"]) for item in self.plan.fixtures}[fixture]
        if identity.startswith("p2/P2_ZERO_CONTEXT_BOUNDARY_V1/"):
            expected = "AMBIGUOUS"
        if corrupt and fixture == "H27-F-N01":
            expected = "AMBIGUOUS"
        kind = {
            "BIRTH_SUPPORTED":"POSITIVE", "NO_BIRTH":"NEGATIVE",
            "ALREADY_ACTIVE_HISTORY":"ACTIVE_HISTORY",
        }.get(expected, "EQUIVALENCE" if fixture in {"H27-F-A01","H27-F-A02"} else "NONE")
        reason = {
            "BIRTH_SUPPORTED":"complete_positive_certificate",
            "NO_BIRTH":"complete_bounded_negative_certificate",
            "ALREADY_ACTIVE_HISTORY":"candidate_active_before_proposal",
        }.get(expected, "observation_equivalent_latent_causes" if kind == "EQUIVALENCE" else "certificate_gap_or_conflict")
        classes = {
            "current_short": "VALID_CURRENT_SHORT_ANALYSIS",
            "previous_short": "VALID_PREVIOUS_SHORT_ANALYSIS",
            "current_long": "VALID_CURRENT_LONG_ANALYSIS",
            "previous_long": "VALID_PREVIOUS_LONG_ANALYSIS",
        }
        if fixture == "H27-F-P01" and identity.startswith("baseline/"):
            classes["previous_short"] = "VALID_EXACT_ZERO_PREVIOUS_SHORT"
            classes["previous_long"] = "VALID_EXACT_ZERO_PREVIOUS_LONG"
        if fixture == "H27-F-A04":
            classes["previous_short"] = "INVALID_SUPPORT"
            classes["previous_long"] = "INVALID_SUPPORT"
            reason = "invalid_or_incomplete_support"
        elif fixture in {"H27-F-A05", "H27-F-A06"}:
            if fixture == "H27-F-A05":
                classes["previous_short"] = "INVALID_PREVIOUS_SHORT_CONTEXT"
                classes["previous_long"] = "INVALID_PREVIOUS_LONG_CONTEXT"
            else:
                classes["current_short"] = "INVALID_CURRENT_SHORT_ANALYSIS"
                classes["current_long"] = "INVALID_CURRENT_LONG_ANALYSIS"
                classes["previous_short"] = "VALID_EXACT_ZERO_PREVIOUS_SHORT"
                classes["previous_long"] = "VALID_EXACT_ZERO_PREVIOUS_LONG"
            reason = "nonzero_not_above_floor"
        elif fixture == "H27-F-A07":
            classes["current_short"] = "INVALID_CURRENT_SHORT_ANALYSIS"
            classes["current_long"] = "INVALID_CURRENT_LONG_ANALYSIS"
            classes["previous_short"] = "VALID_EXACT_ZERO_PREVIOUS_SHORT"
            classes["previous_long"] = "VALID_EXACT_ZERO_PREVIOUS_LONG"
            reason = "invalid_current_exact_zero"
        counts = {"current_short":4096, "previous_short":4096,
                  "current_long":8192, "previous_long":8192}
        if fixture == "H27-F-A04":
            counts["previous_short"] = 4095
            counts["previous_long"] = 8191
        values = dict(
            record_identity=identity, validated_payload_sha256=binding.payload_sha256,
            role_classifications=classes, mask_counts=counts,
            outcome=expected, certificate_kind=kind,
            certificate_complete=kind in {"POSITIVE","NEGATIVE","ACTIVE_HISTORY","EQUIVALENCE"},
            exclusive_partial_membership=(2,3) if expected in {"BIRTH_SUPPORTED","NO_BIRTH"} else (),
            exclusive_energy_ratios=((0.03,0.03) if expected == "BIRTH_SUPPORTED" else
                                     (0.001,0.001) if expected == "NO_BIRTH" else None),
            onset_rise=(0.1 if expected == "BIRTH_SUPPORTED" else
                        0.001 if expected == "NO_BIRTH" else None),
            residual_improvement=(0.2 if expected == "BIRTH_SUPPORTED" else
                                  0.0005 if expected == "NO_BIRTH" else None),
            persistence=0.1 if expected in {"BIRTH_SUPPORTED","NO_BIRTH"} else None,
            bounded_claim_lower_bounds=((0.01,0.01) if expected == "BIRTH_SUPPORTED" else
                                        (0.02,0.02) if expected == "NO_BIRTH" else None),
            negative_margins=((1.0,1.0) if expected == "BIRTH_SUPPORTED" else
                              (20.0,20.0) if expected == "NO_BIRTH" else None),
            pitch_dilution_curve=None, early_resolution_reason=reason,
            maximum_sample_read=binding.proposal_hop_end,
        )
        return H27EngineResult(**values)

    def test_contract_is_dormant_and_post_science_work_is_separately_forbidden(self) -> None:
        value = json.loads(CONTRACT.read_text(encoding="utf-8"))
        self.assertEqual(value["status"], "IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_REAL_EXECUTION")
        for field in (
            "real_execution_authorized", "scientific_authority_creation_authorized",
            "scientific_claim_creation_authorized", "locked_test_authorized",
            "training_authorized", "calibration_authorized", "checkpoint_selection_authorized",
        ):
            self.assertIs(value[field], False)
        post = json.loads((ROOT / "configs/harmonic_censoring_h27_post_science_model_evaluation_contract.json").read_text(encoding="utf-8"))
        self.assertTrue(all(post[field] is False for field in (
            "training_authorized", "checkpoint_generation_authorized",
            "checkpoint_selection_authorized", "locked_test_authorized",
            "final_validation_authorized", "implementation_authorized",
        )))

    def test_dormant_contract_stays_false_and_activation_is_the_runtime_authority(self) -> None:
        contract = runner._load_contract(ROOT)
        self.assertIs(contract["real_execution_authorized"], False)
        with patch.object(runner.platform, "system", return_value="Windows"):
            with self.assertRaisesRegex(RuntimeError, "requires macOS"):
                runner._preflight(ROOT, contract)

    def test_atomic_publisher_never_overwrites_an_existing_result(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "receipt.json"
            raw, digest = runner._atomic_publish(path, {"status":"complete"})
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)
            with self.assertRaises(FileExistsError):
                runner._atomic_publish(path, {"status":"replacement"})
            self.assertEqual(path.read_bytes(), raw)
            self.assertFalse((path.parent / ".receipt.json.part").exists())

    def test_durable_claim_is_reopened_and_tampering_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "claim.json"
            value = _claim_value("c" * 64)
            raw = runner._canonical(value); path.write_bytes(raw)
            changed = dict(value); changed["population_index_sha256"] = "d" * 64
            path.write_bytes(runner._canonical(changed))
            with self.assertRaisesRegex(PermissionError, "changed"):
                verify_durable_h27_claim(
                    claim_path=path, expected_claim=value,
                    expected_claim_sha256=hashlib.sha256(raw).hexdigest(),
                    expected_activation_sha256="a" * 64, expected_execution_id=EXECUTION_ID,
                    expected_activation_nonce=ACTIVATION_NONCE)

    def test_activation_binds_review_chain_population_and_both_runtimes(self) -> None:
        contract = dict(runner._load_contract(ROOT))
        head = subprocess.check_output(("git", "rev-parse", "HEAD"), cwd=ROOT, text=True).strip()
        index_raw = self.index_raw
        with tempfile.TemporaryDirectory() as temporary:
            test_root = Path(temporary).resolve(); configs = test_root / "configs"; configs.mkdir()
            commits = ("1"*40, "2"*40, "3"*40)
            binding = configs / "harmonic_censoring_h27_review5_scientific_execution_identity_binding.json"
            seal = configs / "harmonic_censoring_h27_review5_scientific_execution_external_seal.json"
            binding.write_bytes(runner._canonical({"implementation_commit": commits[0]}))
            binding_raw = binding.read_bytes()
            seal.write_bytes(runner._canonical({"implementation_commit": commits[0],
                "identity_binding_commit": commits[1],
                "identity_binding": {
                    "path": "configs/harmonic_censoring_h27_review5_scientific_execution_identity_binding.json",
                    "git_blob_sha1": runner._git_blob_sha1(binding_raw),
                    "size_bytes": len(binding_raw),
                    "sha256": hashlib.sha256(binding_raw).hexdigest(),
                },
                "population_index_sha256": hashlib.sha256(index_raw).hexdigest()}))
            committed_binding = binding.read_bytes()
            committed_seal = seal.read_bytes()
            value = {
                "schema_identity": "H27_REVIEW5_SCIENTIFIC_ACTIVATION_V1", "schema_version": 1,
                "status": "AUTHORIZED_REAL_SCIENCE_ONE_SHOT", "execution_id": str(uuid.uuid4()),
                "activation_nonce": str(uuid.uuid4()), "issuer": "h27-execution-codex-mac-primary",
                "implementation_commit": commits[0], "identity_binding_commit": commits[1],
                "external_seal_commit": commits[2],
                "identity_binding_sha256": hashlib.sha256(binding.read_bytes()).hexdigest(),
                "external_seal_sha256": hashlib.sha256(seal.read_bytes()).hexdigest(),
                "population_index_sha256": hashlib.sha256(index_raw).hexdigest(),
                "primary_runtime": contract["runtime_python"],
                "secondary_runtime": contract["secondary_runtime_python"], "single_use": True,
                "retry_allowed": False, "locked_test_authorized": False, "training_authorized": False,
            }
            path = test_root / "activation.json"
            path.write_bytes(json.dumps(value, separators=(",", ":")).encode() + b"\n")
            def committed_bytes(_root, _verb, spec):
                return committed_binding if spec.startswith(commits[1]) else committed_seal
            with patch.dict("os.environ", {runner.ACTIVATION_ENVIRONMENT: str(path)}), patch.object(
                runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ), patch.object(runner, "_git", return_value=commits[2]), patch.object(
                runner, "_git_bytes", side_effect=committed_bytes):
                observed, digest = runner._load_activation(test_root, contract, head, index_raw)
            self.assertEqual(observed["execution_id"], value["execution_id"])
            self.assertEqual(digest, hashlib.sha256(path.read_bytes()).hexdigest())
            binding.write_bytes(runner._canonical({"implementation_commit": commits[0], "drift": True}))
            with patch.dict("os.environ", {runner.ACTIVATION_ENVIRONMENT: str(path)}), patch.object(
                runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ), patch.object(runner, "_git", return_value=commits[2]), patch.object(
                runner, "_git_bytes", side_effect=committed_bytes):
                with self.assertRaisesRegex(PermissionError, "bytes changed"):
                    runner._load_activation(test_root, contract, head, index_raw)
            binding.write_bytes(committed_binding)
            value["population_index_sha256"] = "0" * 64
            path.write_bytes(json.dumps(value, separators=(",", ":")).encode() + b"\n")
            with patch.dict("os.environ", {runner.ACTIVATION_ENVIRONMENT: str(path)}), patch.object(
                runner.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)
            ), patch.object(runner, "_git", return_value=commits[2]), patch.object(
                runner, "_git_bytes", side_effect=committed_bytes):
                with self.assertRaisesRegex(ValueError, "population_index_sha256"):
                    runner._load_activation(test_root, contract, head, index_raw)

    def test_durable_claim_rejects_activation_identity_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            value = _claim_value("c" * 64)
            path = Path(temporary) / "claim.json"
            raw = runner._canonical(value); path.write_bytes(raw)
            with self.assertRaisesRegex(PermissionError, "execution_id"):
                verify_durable_h27_claim(
                    claim_path=path, expected_claim=value,
                    expected_claim_sha256=hashlib.sha256(raw).hexdigest(),
                    expected_activation_sha256="a" * 64,
                    expected_execution_id="33333333-3333-4333-8333-333333333333",
                    expected_activation_nonce=ACTIVATION_NONCE,
                )

    def test_receipts_are_exclusive_contiguous_and_sha_chained(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            publisher = runner._ReceiptPublisher(
                output=Path(temporary), claim_sha256="a"*64, activation_sha256="b"*64,
                population_index_sha256="c"*64)
            first = executor.H27TestResult("H27-T-P0-001", "P0", "PASS", 0, (), "one")
            second = executor.H27TestResult("H27-T-P0-002", "P0", "FAIL", 1, ("x",), "two")
            publisher(first); first_sha = publisher.previous_sha256; publisher(second)
            second_value = json.loads((Path(temporary) / "002-H27-T-P0-002.json").read_text())
            self.assertEqual(second_value["previous_receipt_sha256"], first_sha)
            with self.assertRaisesRegex(RuntimeError, "contiguous"):
                publisher(executor.H27TestResult("H27-T-P0-004", "P0", "PASS", 0, (), "skip"))
            with self.assertRaises(FileExistsError):
                runner._ReceiptPublisher(output=Path(temporary), claim_sha256="a"*64,
                    activation_sha256="b"*64, population_index_sha256="c"*64)(first)

    def test_process_capability_is_strictly_one_shot(self) -> None:
        with self.assertRaisesRegex(PermissionError, "already been issued"):
            issue_h27_scientific_capability(durable_claim=object())  # type: ignore[arg-type]

    def test_loader_requires_issued_capability_and_binds_exact_index_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            raw, bindings = self._population(Path(temporary))
            self.assertEqual(len(bindings), 124)
            self.assertEqual(tuple(item.record_identity for item in bindings), canonical_h27_record_identities(self.plan))
            self.assertEqual(hashlib.sha256(raw).hexdigest(), bindings[0].population_index_sha256)
            require_operational_h27_binding(bindings[-1])
            forged = object.__new__(type(self.capability))
            with self.assertRaisesRegex(PermissionError, "not operationally issued"):
                load_h27_sealed_population_bindings(
                    capability=forged, plan=self.plan, population_root=Path(temporary),
                    expected_index_sha256=hashlib.sha256(raw).hexdigest(),
                )

    def test_real_loader_engine_recomputer_path_is_operational_without_consumption(self) -> None:
        """Exercise real bytes and both implementations without the one-shot runner."""
        from src.polyphonic.harmonic_censoring_h27_engine import run_h27_engine
        from src.polyphonic.harmonic_censoring_h27_recomputer import (
            compare_h27_engine_and_recomputer, run_h27_independent_recomputer,
        )
        from src.polyphonic.harmonic_censoring_h27_scientific_authority import operational_h27_engine_boundary
        with tempfile.TemporaryDirectory() as temporary:
            population = Path(temporary) / "population"
            population.mkdir()
            records = []
            for source_record in self.index["records"]:
                identity = source_record["record_identity"]
                fixture = identity.split("/")[1] if identity.startswith("baseline/") else identity.split("/")[2]
                directory = population / identity
                directory.mkdir(parents=True)
                if identity == "baseline/H27-F-H01":
                    waveform = np.zeros(16640, dtype=np.float64)
                    payload_values = {
                        "waveform.f64le": waveform.astype("<f8").tobytes(),
                        "sample-valid-mask.u8": bytes([1]) * (4 * 16640),
                    }
                else:
                    names = ["waveform.f64le", "sample-valid-mask.u8"]
                    if fixture in {"H27-F-A01", "H27-F-A02"}:
                        names.append("alternate-waveform.f64le")
                    payload_values = {name: b"" for name in names}
                payload_sha = {}
                for name, raw in payload_values.items():
                    (directory / name).write_bytes(raw)
                    payload_sha[name] = hashlib.sha256(raw).hexdigest()
                record = dict(source_record); record["payload_sha256"] = payload_sha
                if identity == "baseline/H27-F-H01":
                    record["active_pitches"] = [40]
                records.append(record)
            index_raw = _raw({"schema_version": 1, "population_namespace": "H27_SYNTHETIC_V1",
                              "record_count": 124, "records": records})
            (population / "population_index.json").write_bytes(index_raw)
            authority._CAPABILITIES.clear(); authority._BINDINGS.clear(); authority._CLAIMS.clear()
            authority._ISSUED_ONCE = False
            claim_value = _claim_value(hashlib.sha256(index_raw).hexdigest(), "b" * 64)
            claim_path = Path(temporary) / "claim.json"
            claim_raw = runner._canonical(claim_value); claim_path.write_bytes(claim_raw)
            proof = verify_durable_h27_claim(
                claim_path=claim_path, expected_claim=claim_value,
                expected_claim_sha256=hashlib.sha256(claim_raw).hexdigest(),
                expected_activation_sha256="b" * 64, expected_execution_id=EXECUTION_ID,
                expected_activation_nonce=ACTIVATION_NONCE)
            capability = issue_h27_scientific_capability(durable_claim=proof)
            bindings = load_h27_sealed_population_bindings(
                capability=capability, plan=self.plan, population_root=population,
                expected_index_sha256=hashlib.sha256(index_raw).hexdigest())
            binding = next(item for item in bindings if item.record_identity == "baseline/H27-F-H01")
            with operational_h27_engine_boundary(capability):
                engine = run_h27_engine(np, capability, ROOT, binding)
                recomputed = run_h27_independent_recomputer(np, capability, ROOT, binding)
                compare_h27_engine_and_recomputer(engine, recomputed)
            self.assertEqual(engine.record_identity, "baseline/H27-F-H01")
            self.assertEqual(engine.outcome, "ALREADY_ACTIVE_HISTORY")

    def test_executor_runs_27_in_order_over_124_unique_records_and_stops(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, bindings = self._population(Path(temporary))
            secondary_calls = []
            def engine(_np, _capability, _root, binding):
                return self._result(binding)
            def recomputer(_np, _capability, _root, binding):
                return H27RecomputedResult(**vars(self._result(binding)))
            @contextmanager
            def boundary(_capability):
                yield
            def secondary(_plan, _root, identities):
                secondary_calls.append(identities)
                by_identity = {item.record_identity:item for item in bindings}
                return tuple(self._result(by_identity[identity]) for identity in identities)
            with patch.object(executor, "run_h27_engine", engine), patch.object(
                executor, "run_h27_independent_recomputer", recomputer
            ), patch.object(executor, "operational_h27_engine_boundary", boundary
            ), patch.object(executor, "_secondary_runtime_records", secondary
            ), patch.object(executor, "_require_primary_runtime_identity"
            ):
                result = executor.execute_h27_scientific_sequence(
                    np=np, capability=self.capability, repository_root=ROOT,
                    plan=self.plan, bindings=bindings,
                )
            self.assertEqual(result.terminal_status, executor.PASS_STATUS,
                             msg=result.test_results[-1] if result.test_results else None)
            self.assertEqual((result.tests_passed, result.tests_failed, result.tests_not_run), (27,0,0))
            self.assertEqual(result.unique_records_evaluated, 124)
            self.assertEqual(result.record_evaluations, 248)
            self.assertEqual(tuple(item.test_id for item in result.test_results), executor.TEST_IDS)
            self.assertEqual(len(secondary_calls), 1)
            self.assertEqual(len(secondary_calls[0]), 4)
            self.assertTrue(all(identity.endswith("runtime=secondary") for identity in secondary_calls[0]))
            self.assertFalse(result.locked_test_used)
            self.assertFalse(result.training_used)

    def test_every_declared_inverse_has_a_checker_and_rejects_its_corruption(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, bindings = self._population(Path(temporary))
            by_identity = {item.record_identity: item for item in bindings}
            required = (
                "H27-F-P01", "H27-F-P02", "H27-F-N01", "H27-F-P04", "H27-F-A01",
                "H27-F-A04", "H27-F-A05", "H27-F-A06", "H27-F-A07",
            )
            rows = {f"baseline/{fixture}": self._result(by_identity[f"baseline/{fixture}"])
                    for fixture in required}
            executor.require_inverse_checker_coverage(self.plan)
            observed = executor._inverse_checks(np, self.plan, rows, by_identity)
            self.assertEqual(set(observed), set(self.plan.test_manifest["inverse_contracts"]))
            self.assertTrue(all(observed.values()), msg=observed)

    def test_p1_fixture_specific_roles_reject_generic_or_swapped_classifications(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, bindings = self._population(Path(temporary))
            by_identity = {item.record_identity: item for item in bindings}
            binding = by_identity["baseline/H27-F-P01"]
            valid = self._result(binding)
            self.assertTrue(executor._p1_fixture_contract("H27-F-P01", valid, binding))
            generic = dict(valid.role_classifications)
            generic["previous_short"] = "VALID_PREVIOUS_SHORT_ANALYSIS"
            self.assertFalse(executor._p1_fixture_contract(
                "H27-F-P01", H27EngineResult(**{**vars(valid), "role_classifications": generic}), binding,
            ))

    def test_first_failure_kills_all_later_tests_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            _, bindings = self._population(Path(temporary))
            def engine(_np, _capability, _root, binding):
                return self._result(binding, corrupt=True)
            def recomputer(_np, _capability, _root, binding):
                return H27RecomputedResult(**vars(self._result(binding, corrupt=True)))
            @contextmanager
            def boundary(_capability):
                yield
            def secondary(_plan, _root, identities):
                by_identity = {item.record_identity:item for item in bindings}
                return tuple(self._result(by_identity[identity], corrupt=True) for identity in identities)
            completed = []
            with patch.object(executor, "run_h27_engine", engine), patch.object(
                executor, "run_h27_independent_recomputer", recomputer
            ), patch.object(executor, "operational_h27_engine_boundary", boundary
            ), patch.object(executor, "_secondary_runtime_records", secondary
            ), patch.object(executor, "_require_primary_runtime_identity"
            ):
                result = executor.execute_h27_scientific_sequence(
                    np=np, capability=self.capability, repository_root=ROOT,
                    plan=self.plan, bindings=bindings,
                    on_test_completed=completed.append,
                )
            self.assertEqual(result.terminal_status, executor.KILL_STATUS["P0"])
            self.assertEqual(result.tests_failed, 1)
            self.assertGreater(result.tests_not_run, 0)
            self.assertEqual(result.test_results[-1].status, "FAIL")
            self.assertEqual(tuple(item.test_id for item in completed),
                             tuple(item.test_id for item in result.test_results))
            self.assertEqual(completed[-1].status, "FAIL")


if __name__ == "__main__":
    unittest.main()
