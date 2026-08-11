from __future__ import annotations

from dataclasses import replace
import hashlib
import json
import os
from pathlib import Path
import pickle
from types import MappingProxyType
import tempfile
from typing import Optional
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h24_scientific_capability as capability
from src.polyphonic import run_harmonic_censoring_h24_scientific as runner
from src.polyphonic.harmonic_censoring_h24 import load_h24_dormant_harness_plan
from src.polyphonic.harmonic_censoring_h24_operators import H24RecomputedOracle


ROOT = Path(__file__).resolve().parents[1]


class H24ScientificExecutionDormantTests(unittest.TestCase):
    def setUp(self) -> None:
        self.plan = load_h24_dormant_harness_plan(ROOT)
        self.temporary = tempfile.TemporaryDirectory()
        base = Path(self.temporary.name).resolve()
        self.base = base
        success = base / "success"
        self.value = capability._new_capability(
            repository_root=ROOT,
            activation_commit="1" * 40,
            activation_sha256="2" * 64,
            seal_sha256="3" * 64,
            implementation_commit="4" * 40,
            capability_source_blob="5" * 40,
            runner_source_blob="6" * 40,
            producer_source_blob="b" * 40,
            predecessor_runner_source_blob="c" * 40,
            predecessor_harness_source_blob="d" * 40,
            predecessor_contract_sha256="e" * 64,
            contract_sha256=capability.H24_SCIENTIFIC_CONTRACT_RAW_SHA256,
            runtime_identity=(("device", "1"),),
            population_marker_sha256="7" * 64,
            population_terminal_sha256="8" * 64,
            population_receipt_sha256="9" * 64,
            population_index_sha256="a" * 64,
            population_directory=ROOT / "tmp/local/harmonic_censoring_h24_synthetic_v1/population",
            ordered_fixture_ids=self.plan.fixture_ids,
            fixture_file_bindings=tuple(),
            ordered_test_ids=self.plan.test_ids,
            ordered_test_phases=tuple(item.phase for item in self.plan.tests),
            claim_path=base / "claim.json",
            staging_directory=base / "staging",
            success_directory=success,
            transcript_path=success / "scientific_transcript.jsonl",
            transcript_staging_path=base / "staging" / "scientific_transcript.jsonl.part",
            evidence_directory=success / "evidence",
            terminal_path=base / "terminal.json",
        )

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _claim(self) -> None:
        capability.claim_h24_scientific_execution(self.value)

    def _writer(self) -> runner._H24TranscriptWriter:
        self._claim()
        return runner._H24TranscriptWriter(self.plan, self.value)

    def _absolute_paths(
        self,
        *,
        claim: Optional[Path] = None,
        staging: Optional[Path] = None,
        success: Optional[Path] = None,
        terminal: Optional[Path] = None,
    ) -> dict[str, Path]:
        staging = staging or self.value.staging_directory
        success = success or self.value.success_directory
        return {
            "claim": claim or self.value.claim_path,
            "staging": staging,
            "success": success,
            "transcript": success / "scientific_transcript.jsonl",
            "transcript_staging": staging / "scientific_transcript.jsonl.part",
            "evidence": success / "evidence",
            "terminal": terminal or self.value.terminal_path,
        }

    def _population_binding(self) -> dict[str, object]:
        contract = json.loads(
            (ROOT / capability.H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH).read_bytes()
        )
        return contract["published_population_binding"]

    def test_public_issuer_is_dormant_before_population_or_numpy(self) -> None:
        self.assertEqual(
            hashlib.sha256(
                (ROOT / capability.H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH).read_bytes()
            ).hexdigest(),
            capability.H24_SCIENTIFIC_CONTRACT_RAW_SHA256,
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(capability.H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV, None)
            with self.assertRaisesRegex(PermissionError, "no OS-bound activation"):
                capability.issue_h24_scientific_execution_capability(ROOT)
        self.assertNotIn("numpy", __import__("sys").modules)

    def test_source_binding_checks_reviewed_implementation_and_activation_head(self) -> None:
        path = capability.H24_PRODUCER_SOURCE_RELATIVE_PATH
        with mock.patch.object(
            capability, "_git", side_effect=["a" * 40, "a" * 40]
        ) as git:
            capability._require_bound_source_blob_at_activation(
                ROOT, "1" * 40, "2" * 40, path, "a" * 40
            )
        self.assertEqual(
            [call.args[1:] for call in git.call_args_list],
            [
                ("rev-parse", f"{'1' * 40}:{path.as_posix()}"),
                ("rev-parse", f"{'2' * 40}:{path.as_posix()}"),
            ],
        )
        with mock.patch.object(
            capability, "_git", side_effect=["a" * 40, "b" * 40]
        ), self.assertRaisesRegex(ValueError, "activation HEAD source blob mismatch"):
            capability._require_bound_source_blob_at_activation(
                ROOT, "1" * 40, "2" * 40, path, "a" * 40
            )

    def test_predecessor_contract_anchor_is_exact_h23_scientific_sha(self) -> None:
        raw = (ROOT / capability.H24_PREDECESSOR_CONTRACT_RELATIVE_PATH).read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            capability.H24_REVIEWED_PREDECESSOR_CONTRACT_RAW_SHA256,
        )
        self.assertEqual(
            capability.H24_REVIEWED_PREDECESSOR_CONTRACT_RAW_SHA256,
            "719eba0aa440fc1e77ae7d204adee9e5b51517f455fad3bfed7e761d3c00a74a",
        )

    def test_path_topology_accepts_only_the_three_canonical_descendants(self) -> None:
        contract = json.loads(
            (ROOT / capability.H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH).read_bytes()
        )
        self.assertEqual(
            tuple(contract["contract_definition_exact_changed_files"]),
            capability.H24_TERMINAL_BINDING_CORRECTION_EXACT_CHANGED_FILES,
        )
        capability._validate_scientific_path_topology(
            ROOT,
            self._absolute_paths(),
            contract["published_population_binding"],
        )

    def test_every_scientific_top_level_output_is_forbidden_in_population_namespace(self) -> None:
        namespace = ROOT / "tmp/local/harmonic_censoring_h24_synthetic_v1"
        cases = {
            "claim": {"claim": namespace / "scientific.claim.json"},
            "staging": {"staging": namespace / "scientific.staging"},
            "success": {"success": namespace / "scientific.success"},
            "terminal": {"terminal": namespace / "scientific.terminal.json"},
            "success_ancestor": {"success": namespace.parent},
        }
        for name, overrides in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError, "immutable population control namespace"
            ):
                capability._validate_scientific_path_topology(
                    ROOT,
                    self._absolute_paths(**overrides),
                    self._population_binding(),
                )

    def test_unauthorized_one_shot_ancestor_descendant_relations_fail_closed(self) -> None:
        staging = self.base / "staging"
        success = self.base / "success"
        cases = {
            "claim_inside_staging": self._absolute_paths(
                claim=staging / "claim.json", staging=staging
            ),
            "terminal_inside_success": self._absolute_paths(
                success=success, terminal=success / "terminal.json"
            ),
            "success_inside_staging": self._absolute_paths(
                staging=staging, success=staging / "success"
            ),
            "staging_inside_success": self._absolute_paths(
                staging=success / "staging", success=success
            ),
        }
        for name, paths in cases.items():
            with self.subTest(name=name), self.assertRaisesRegex(
                ValueError, "unauthorized ancestor/descendant"
            ):
                capability._validate_scientific_path_topology(
                    ROOT,
                    paths,
                    self._population_binding(),
                )

    def test_capability_is_identity_attested_and_replace_fails(self) -> None:
        with self.assertRaisesRegex(TypeError, "no public constructor"):
            capability.AttestedH24ScientificExecutionCapability()
        self.assertIs(
            capability.require_attested_h24_scientific_capability(self.value),
            self.value,
        )
        with self.assertRaises((TypeError, PermissionError)):
            capability.require_attested_h24_scientific_capability(replace(self.value))
        with self.assertRaises((TypeError, PermissionError)):
            capability.require_attested_h24_scientific_capability(
                pickle.loads(pickle.dumps(self.value))
            )
        with self.assertRaises(TypeError):
            capability.require_attested_h24_scientific_capability(object())

    def test_claim_is_O_EXCL_and_second_claim_loses(self) -> None:
        self._claim()
        raw = self.value.claim_path.read_bytes()
        payload = json.loads(raw)
        self.assertEqual(payload["claim_state"], "CLAIMED_BEFORE_FIRST_WAVEFORM_DECODE")
        self.assertFalse(payload["locked_test_used"])
        with self.assertRaises(FileExistsError):
            capability.claim_h24_scientific_execution(self.value)

    def test_exact_producers_exist_but_public_issuer_remains_dormant(self) -> None:
        self.assertTrue(runner.H24_EVIDENCE_PRODUCER_REGISTRY_IMPLEMENTED)
        self.assertEqual(tuple(runner._H24_EVIDENCE_PRODUCER_REGISTRY), self.plan.test_ids)
        with mock.patch.object(
            runner, "issue_h24_scientific_execution_capability", wraps=capability.issue_h24_scientific_execution_capability
        ):
            with mock.patch.dict(os.environ, {}, clear=False):
                os.environ.pop(capability.H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV, None)
                with self.assertRaisesRegex(PermissionError, "no OS-bound activation"):
                    runner.main([])
        self.assertFalse(self.value.claim_path.exists())

    def test_complete_mock_registry_claims_before_numpy_or_waveform_decode(self) -> None:
        order: list[str] = []
        registry = MappingProxyType(
            {test_id: (lambda context, test: {}) for test_id in self.plan.test_ids}
        )

        def claim(value: object) -> object:
            order.append("claim")
            return value

        def writer(plan: object, value: object) -> object:
            del plan, value
            order.append("writer")
            raise RuntimeError("stop before NumPy")

        with mock.patch.object(
            runner, "_H24_EVIDENCE_PRODUCER_REGISTRY", registry
        ), mock.patch.object(
            runner, "claim_h24_scientific_execution", side_effect=claim
        ), mock.patch.object(
            runner, "_H24TranscriptWriter", side_effect=writer
        ), mock.patch.object(runner.importlib, "import_module") as import_module:
            with self.assertRaisesRegex(RuntimeError, "stop before NumPy"):
                runner.run_authorized_h24_scientific_execution(ROOT, self.value)
        self.assertEqual(order, ["claim", "writer"])
        import_module.assert_not_called()

    def test_cli_has_no_override_and_fails_at_dormant_issuer(self) -> None:
        with self.assertRaisesRegex(ValueError, "accepts no caller arguments"):
            runner.main(["--test-id", "H24-A01-GRAPH-DIRECTION"])
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(capability.H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV, None)
            with self.assertRaisesRegex(PermissionError, "no OS-bound activation"):
                runner.main([])

    def test_finalizer_has_no_caller_results_or_paths(self) -> None:
        import inspect

        self.assertEqual(
            tuple(inspect.signature(runner.finalize_and_publish_h24_scientific_terminal).parameters),
            ("repository_root", "capability"),
        )
        self.assertNotIn("_H24TranscriptWriter", runner.__all__)

    def test_success_transcript_is_72_record_hash_chain_and_terminal_is_disk_derived(self) -> None:
        writer = self._writer()
        for _ in self.plan.tests:
            writer.append_evidence({"primary": {}, "inverse": {}})
        writer.publish()
        with mock.patch.object(
            runner,
            "recompute_h24_persisted_evidence",
            side_effect=lambda plan, test_id, evidence: H24RecomputedOracle(
                test_id, True, True
            ),
        ) as recompute:
            path = runner.finalize_and_publish_h24_scientific_terminal(ROOT, self.value)
        self.assertEqual(recompute.call_count, 72)
        transcript = self.value.transcript_path.read_bytes()
        lines = transcript.splitlines(keepends=True)
        self.assertEqual(len(lines), 72)
        previous = "0" * 64
        for index, raw in enumerate(lines):
            record = json.loads(raw)
            self.assertEqual(record["sequence_index"], index)
            self.assertEqual(record["previous_record_sha256"], previous)
            previous = hashlib.sha256(raw).hexdigest()
        terminal = json.loads(path.read_bytes())
        self.assertEqual(set(terminal), runner._TERMINAL_KEYS)
        self.assertEqual(terminal["scientific_status"], runner.H24_SUCCESS_STATUS)
        self.assertEqual(terminal["passed_test_count"], 72)
        self.assertEqual(terminal["executed_evidence_record_count"], 72)
        self.assertEqual(
            terminal["ordered_test_ids_sha256"],
            "3d9c9178ece6b8f0631baf4392bc92f0aa074ed987875e0cb208ab0f90201376",
        )
        self.assertEqual(terminal["transcript_raw_sha256"], hashlib.sha256(transcript).hexdigest())
        self.assertEqual(terminal["final_record_sha256"], previous)

    def test_first_P0_failure_requires_exact_kill_suffix(self) -> None:
        writer = self._writer()
        writer.append_evidence({"primary": {}, "inverse": {}})
        writer.fill_kill_suffix()
        writer.publish()
        with mock.patch.object(
            runner,
            "recompute_h24_persisted_evidence",
            return_value=H24RecomputedOracle(self.plan.tests[0].test_id, False, True),
        ):
            terminal_path = runner.finalize_and_publish_h24_scientific_terminal(
                ROOT, self.value
            )
        terminal = json.loads(terminal_path.read_bytes())
        self.assertEqual(terminal["scientific_status"], runner.H24_P0_KILL_STATUS)
        self.assertEqual(terminal["first_failed_sequence_index"], 0)
        self.assertEqual(terminal["not_run_by_kill_rule_count"], 71)

    def test_ordinary_operational_error_is_inconclusive_and_consumed(self) -> None:
        writer = self._writer()
        writer.append_operational_error(RuntimeError("injected"))
        writer.fill_operational_suffix()
        writer.publish()
        with mock.patch.object(runner, "recompute_h24_persisted_evidence") as recompute:
            terminal_path = runner.finalize_and_publish_h24_scientific_terminal(
                ROOT, self.value
            )
        recompute.assert_not_called()
        terminal = json.loads(terminal_path.read_bytes())
        self.assertEqual(terminal["scientific_status"], runner.H24_INCONCLUSIVE_STATUS)
        self.assertEqual(terminal["operational_error_count"], 1)
        self.assertEqual(terminal["not_run_by_operational_failure_count"], 71)
        self.assertTrue(self.value.claim_path.exists())

    def test_missing_extra_or_mutated_evidence_fails_closed(self) -> None:
        writer = self._writer()
        writer.append_evidence({"primary": {}, "inverse": {}})
        writer.fill_kill_suffix()
        writer.publish()
        (self.value.evidence_directory / "extra.json").write_text("{}\n", encoding="utf-8")
        with mock.patch.object(
            runner,
            "recompute_h24_persisted_evidence",
            return_value=H24RecomputedOracle(self.plan.tests[0].test_id, False, True),
        ):
            with self.assertRaisesRegex(ValueError, "missing or extra"):
                runner.finalize_and_publish_h24_scientific_terminal(ROOT, self.value)

    def test_record_reordering_or_hash_mutation_fails_closed(self) -> None:
        writer = self._writer()
        writer.append_operational_error(RuntimeError("injected"))
        writer.fill_operational_suffix()
        writer.publish()
        lines = self.value.transcript_path.read_bytes().splitlines(keepends=True)
        self.value.transcript_path.write_bytes(lines[1] + lines[0] + b"".join(lines[2:]))
        with self.assertRaisesRegex(ValueError, "identity/order/hash chain"):
            runner.finalize_and_publish_h24_scientific_terminal(ROOT, self.value)

    def test_finalizer_error_terminal_binds_raw_transcript_without_scientific_verdict(self) -> None:
        writer = self._writer()
        writer.append_operational_error(RuntimeError("injected"))
        writer.fill_operational_suffix()
        writer.publish()
        transcript = self.value.transcript_path.read_bytes()
        terminal_path = runner._publish_h24_finalizer_error_terminal(self.value)
        terminal = json.loads(terminal_path.read_bytes())
        self.assertEqual(terminal["scientific_status"], runner.H24_INCONCLUSIVE_STATUS)
        self.assertEqual(terminal["transcript_validation_status"], "FINALIZER_ERROR")
        self.assertEqual(terminal["transcript_raw_sha256"], hashlib.sha256(transcript).hexdigest())
        self.assertIsNone(terminal["passed_test_count"])

    def test_terminal_publication_is_atomic_and_never_overwrites(self) -> None:
        payload = {key: None for key in runner._TERMINAL_KEYS}
        payload["schema_version"] = 1
        runner._atomic_terminal(self.value.terminal_path, payload)
        with self.assertRaises(FileExistsError):
            runner._atomic_terminal(self.value.terminal_path, payload)
        self.assertFalse(self.value.terminal_path.with_name("terminal.json.part").exists())


if __name__ == "__main__":
    unittest.main()
