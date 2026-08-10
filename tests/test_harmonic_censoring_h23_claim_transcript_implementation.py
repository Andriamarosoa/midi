from __future__ import annotations

import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h23_execution_capability as capability
from src.polyphonic import run_harmonic_censoring_h23_synthetic as runner
from src.polyphonic.harmonic_censoring_h23 import load_h23_harness_plan


class HarmonicCensoringH23ClaimTranscriptImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.root = Path(__file__).resolve().parents[1]
        cls.plan = load_h23_harness_plan(cls.root)
        cls.transcript_contract = json.loads(
            (
                cls.root
                / capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH
            ).read_bytes()
        )

    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.repository = Path(self.temporary.name).resolve()
        executor_contract = (
            self.repository
            / capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH
        )
        executor_contract.parent.mkdir(parents=True, exist_ok=True)
        executor_contract.write_bytes(
            (
                self.root
                / capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RELATIVE_PATH
            ).read_bytes()
        )
        seal = capability.validate_h23_authorization_seal_payload(
            self._seal_payload(), raw_sha256="d" * 64
        )
        activation = capability.validate_h23_authorization_activation_payload(
            self._activation_payload(), raw_sha256="e" * 64
        )
        context = capability.H23AuthorizationContext(
            activation_commit="f" * 40,
            activation=activation,
            seal=seal,
        )
        patches = (
            mock.patch.object(capability, "_load_h23_authorization_context", return_value=context),
            mock.patch.object(capability, "load_h23_harness_plan", return_value=self.plan),
            mock.patch.object(capability, "_validate_repository_and_runtime"),
        )
        for patcher in patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        self.attested = capability.issue_h23_synthetic_execution_capability(
            self.repository
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _seal_payload(self) -> dict[str, object]:
        commit = "a" * 40
        return {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h23_synthetic_execution_authorization_seal",
            "status": "externally_approved_one_shot_synthetic_execution",
            "authorization": {
                "capability_issuance_authorized": True,
                "synthetic_execution_authorized": True,
                "scientific_execution_authorized": True,
                "P0_execution_authorized": True,
                "P1_execution_authorized": True,
                "P2_execution_authorized": True,
                "real_data_access_authorized": False,
                "training_authorized": False,
                "H17_population_used": False,
                "locked_test_used": False,
            },
            "bindings": {
                "H23_contract_raw_sha256": capability.H23_CONTRACT_SHA256,
                "capability_contract_raw_sha256": capability.H23_CAPABILITY_CONTRACT_SHA256,
                "executor_claim_transcript_contract_raw_sha256": capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256,
                "fixture_manifest_sha256": capability.H23_FIXTURE_MANIFEST_SHA256,
                "resolved_test_manifest_sha256": capability.H23_RESOLVED_TEST_MANIFEST_SHA256,
                "reviewed_execution_commit": commit,
                "exact_changed_files": [
                    capability.H23_CAPABILITY_SOURCE_RELATIVE_PATH.as_posix(),
                    capability.H23_RUNNER_SOURCE_RELATIVE_PATH.as_posix(),
                ],
                "capability_source_blob": "b" * 40,
                "runner_source_blob": "c" * 40,
            },
            "runtime_identity": {
                "implementation": "CPython",
                "python_version": "3.11.9",
                "numpy_version": "1.26.4",
                "architecture": "arm64",
                "execution_device": "CPU",
                "thread_count": 1,
            },
            "one_shot_paths": {
                "success_destination": "out/success",
                "terminal_record_destination": "out/terminal",
                "authorization_marker": "state/consumed.json",
                "transcript_path": "state/transcript.jsonl",
            },
            "external_review": {
                "verdict": "APPROVED",
                "reviewed_execution_commit": commit,
                "authorization_seal_review_required": True,
            },
        }

    def _activation_payload(self) -> dict[str, object]:
        return {
            "schema_version": 1,
            "purpose": "harmonic_censoring_h23_synthetic_execution_activation",
            "status": "externally_reviewed_seal_activation",
            "authorization_seal": {
                "path": capability.H23_AUTHORIZATION_SEAL_RELATIVE_PATH.as_posix(),
                "raw_sha256": "d" * 64,
            },
            "bindings": {
                "implementation_commit": "a" * 40,
                "capability_source_blob": "b" * 40,
                "runner_source_blob": "c" * 40,
                "executor_claim_transcript_contract_raw_sha256": capability.H23_EXECUTOR_CLAIM_TRANSCRIPT_CONTRACT_RAW_SHA256,
            },
            "external_review": {
                "verdict": "APPROVED",
                "authorization_seal_reviewed": True,
                "activation_commit_review_required": True,
            },
        }

    def _claim(self):
        with mock.patch.object(capability, "_revalidate_h23_claim_authority"):
            return capability.claim_h23_synthetic_execution_capability(self.attested)

    def _write_transcript(
        self,
        claimed: object,
        results: list[bool],
        *,
        materialize_all: bool,
        operational_inconclusive: bool = False,
    ) -> None:
        writer = runner._create_h23_transcript_writer(self.plan, claimed)
        fixture_ids: list[str] = []
        if materialize_all:
            for index, fixture in enumerate(self.plan.fixtures):
                writer.append_fixture(self._fixture_payload(index))
                fixture_ids.append(fixture.fixture_id)
        elif results:
            writer.append_fixture(self._fixture_payload())
            fixture_ids.append(self.plan.fixtures[0].fixture_id)
        for index, passed in enumerate(results):
            writer.append_test(
                self._test_payload(
                    passed,
                    test_index=index,
                    fixture_ids=fixture_ids,
                )
            )
        writer.append_terminal(
            runner._terminal_event_payload(
                self.plan,
                results,
                fixture_ids,
                operational_inconclusive=operational_inconclusive,
            )
        )
        writer.close()

    def _fixture_payload(self, fixture_index: int = 0) -> dict[str, object]:
        fixture = self.plan.fixtures[fixture_index]
        target = fixture.as_dict()["expected_target"]
        return {
            "fixture_id": fixture.fixture_id,
            "fixture_spec_sha256": fixture.spec_sha256,
            "waveform_sha256": hashlib.sha256(
                f"synthetic-float64-waveform:{fixture.fixture_id}".encode()
            ).hexdigest(),
            "target_sha256": hashlib.sha256(runner._canonical_json_line(target)).hexdigest(),
            "sample_count": 12544,
            "finite_sample_count": 12544,
            "nonfinite_sample_count": 0,
        }

    def _test_payload(
        self,
        passed: bool = False,
        *,
        test_index: int = 0,
        fixture_ids: list[str] | None = None,
    ) -> dict[str, object]:
        test = self.plan.tests[test_index]
        evidence = {
            "observed_values": {"synthetic": 1},
            "oracle_comparison": {"exact": passed},
            "pass_rule_boolean": passed,
            "inverse_expected_failure_observed": True,
            "inverse_unexpectedly_passes_primary_oracle": False,
            "nonfinite_count": 0,
            "mask_count": 0,
            "artifacts_sha256": {},
            "drawback": test.as_dict()["drawback"],
        }
        return {
            "test_id": test.test_id,
            "phase": test.phase,
            "resolved_order_index": test_index,
            "resolved_test_contract_sha256": test.resolved_sha256,
            "passed": passed,
            "fixture_ids_exercised": (
                [self.plan.fixtures[0].fixture_id]
                if fixture_ids is None
                else fixture_ids
            ),
            "evidence_schema": runner._evidence_schema_sha256(test),
            "evidence": evidence,
            "evidence_sha256": hashlib.sha256(runner._canonical_json_line(evidence)).hexdigest(),
            "inverse_check_count": 1,
            "nonfinite_count": 0,
            "mask_count": 0,
            "latency_measurements": {},
            "memory_measurements": {},
        }

    def test_claim_is_canonical_exclusive_and_irreversible(self) -> None:
        claimed = self._claim()
        raw = claimed.authorization_marker.read_bytes()
        self.assertEqual(raw, capability._canonical_json_line(json.loads(raw)))
        self.assertEqual(json.loads(raw)["claim_state"], "CLAIMED_BEFORE_FIRST_WAVEFORM")
        with self.assertRaises(FileExistsError):
            capability.claim_h23_synthetic_execution_capability(claimed)
        self.assertTrue(claimed.authorization_marker.is_file())

    def test_partial_or_corrupt_existing_marker_blocks_claim(self) -> None:
        self.attested.authorization_marker.parent.mkdir(parents=True)
        self.attested.authorization_marker.write_bytes(b"{")
        with mock.patch.object(capability, "_revalidate_h23_claim_authority"):
            with self.assertRaises(FileExistsError):
                capability.claim_h23_synthetic_execution_capability(self.attested)
        self.assertEqual(self.attested.authorization_marker.read_bytes(), b"{")

    def test_unclaimed_capability_cannot_create_transcript(self) -> None:
        with self.assertRaisesRegex(PermissionError, "not durably claimed"):
            runner._create_h23_transcript_writer(self.plan, self.attested)

    def test_hash_chain_tampering_is_rejected(self) -> None:
        claimed = self._claim()
        writer = runner._create_h23_transcript_writer(self.plan, claimed)
        writer.append_fixture(self._fixture_payload())
        writer.append_test(self._test_payload(False))
        writer.append_terminal(
            {
                "outcome_class": runner.H23_P0_KILL_STATUS,
                "executed_test_count": 1,
                "passed_test_count": 0,
                "first_failed_test_id": self.plan.tests[0].test_id,
                "not_run_test_ids": list(self.plan.test_ids[1:]),
                "materialized_fixture_ids": [self.plan.fixtures[0].fixture_id],
            }
        )
        writer.close()
        raw = claimed.transcript_path.read_bytes()
        claimed.transcript_path.write_bytes(raw.replace(b'"synthetic":1', b'"synthetic":2'))
        with self.assertRaisesRegex(ValueError, "canonical|hash chain|evidence"):
            runner._read_and_verify_h23_transcript(self.plan, claimed)

    def test_persisted_failure_is_recomputed_and_published(self) -> None:
        claimed = self._claim()
        writer = runner._create_h23_transcript_writer(self.plan, claimed)
        writer.append_fixture(self._fixture_payload())
        writer.append_test(self._test_payload(False))
        writer.append_terminal(
            {
                "outcome_class": runner.H23_P0_KILL_STATUS,
                "executed_test_count": 1,
                "passed_test_count": 0,
                "first_failed_test_id": self.plan.tests[0].test_id,
                "not_run_test_ids": list(self.plan.test_ids[1:]),
                "materialized_fixture_ids": [self.plan.fixtures[0].fixture_id],
            }
        )
        writer.close()
        with mock.patch.object(runner, "load_h23_harness_plan", return_value=self.plan):
            report = runner.finalize_and_publish_h23_terminal_record(
                self.repository, claimed
            )
        payload = json.loads(report.read_bytes())
        self.assertTrue(payload["authoritative"])
        self.assertEqual(payload["global_go_status"], runner.H23_P0_KILL_STATUS)
        self.assertEqual(payload["not_run_test_ids"], list(self.plan.test_ids[1:]))
        self.assertFalse(payload["training_authorized"])

    def test_success_requires_exact_72_passes_and_175_fixtures(self) -> None:
        claimed = self._claim()
        self._write_transcript(claimed, [True] * 72, materialize_all=True)
        with mock.patch.object(runner, "load_h23_harness_plan", return_value=self.plan):
            report = runner.finalize_and_publish_h23_terminal_record(
                self.repository, claimed
            )
        payload = json.loads(report.read_bytes())
        self.assertEqual(payload["global_go_status"], runner.H23_POSITIVE_STATUS)
        self.assertEqual(payload["executed_test_count"], 72)
        self.assertEqual(payload["materialized_fixture_count"], 175)
        self.assertFalse(payload["training_authorized"])

    def test_operational_prefix_is_inconclusive_not_scientific(self) -> None:
        claimed = self._claim()
        self._write_transcript(
            claimed,
            [True, True],
            materialize_all=True,
            operational_inconclusive=True,
        )
        with mock.patch.object(runner, "load_h23_harness_plan", return_value=self.plan):
            report = runner.finalize_and_publish_h23_terminal_record(
                self.repository, claimed
            )
        payload = json.loads(report.read_bytes())
        self.assertEqual(payload["global_go_status"], runner.H23_INCONCLUSIVE_STATUS)
        self.assertIsNone(payload["scientific_verdict"])
        self.assertFalse(self.attested.success_destination.exists())

    def test_event_after_first_failure_is_rejected(self) -> None:
        claimed = self._claim()
        writer = runner._create_h23_transcript_writer(self.plan, claimed)
        writer.append_fixture(self._fixture_payload())
        writer.append_test(
            self._test_payload(
                False,
                fixture_ids=[
                    self.plan.fixtures[0].fixture_id,
                    self.plan.fixtures[1].fixture_id,
                ],
            )
        )
        writer.append_fixture(self._fixture_payload(1))
        writer.append_terminal(
            runner._terminal_event_payload(
                self.plan,
                [False],
                [self.plan.fixtures[0].fixture_id, self.plan.fixtures[1].fixture_id],
            )
        )
        writer.close()
        with mock.patch.object(runner, "load_h23_harness_plan", return_value=self.plan):
            with self.assertRaisesRegex(ValueError, "after its first failure"):
                runner.finalize_and_publish_h23_terminal_record(
                    self.repository, claimed
                )

    def test_caller_fabricated_pass_objects_have_no_finalizer_route(self) -> None:
        signature = __import__("inspect").signature(
            runner.finalize_and_publish_h23_terminal_record
        )
        self.assertEqual(tuple(signature.parameters), ("repository_root", "capability"))
        self.assertNotIn("H23AdministrativeTestResult", signature.parameters)

    def test_first_scientific_import_and_synthesis_follow_claim(self) -> None:
        order: list[str] = []

        def claim(value: object) -> object:
            order.append("claim")
            return value

        def create(plan: object, value: object) -> object:
            del plan, value
            order.append("header")
            raise RuntimeError("stop before NumPy")

        with mock.patch.object(runner, "load_h23_harness_plan", return_value=self.plan), mock.patch.object(
            runner, "claim_h23_synthetic_execution_capability", side_effect=claim
        ), mock.patch.object(runner, "_create_h23_transcript_writer", side_effect=create), mock.patch.object(
            runner.importlib, "import_module"
        ) as import_module:
            with self.assertRaisesRegex(RuntimeError, "stop before NumPy"):
                runner.run_authorized_h23_synthetic_execution(
                    self.repository, self.attested
                )
        self.assertEqual(order, ["claim", "header"])
        import_module.assert_not_called()

    def test_partial_staging_never_becomes_destination(self) -> None:
        destination = self.repository / "out" / "atomic"
        with mock.patch.object(runner.os, "replace", side_effect=OSError("injected")):
            with self.assertRaisesRegex(OSError, "injected"):
                runner._publish_h23_terminal_record_atomically(
                    destination, {"schema_version": 1}
                )
        self.assertFalse(destination.exists())


if __name__ == "__main__":
    unittest.main()
