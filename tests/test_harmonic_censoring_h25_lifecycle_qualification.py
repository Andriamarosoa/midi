from __future__ import annotations

import ast
import json
import os
import tempfile
import unittest
from pathlib import Path

from src.polyphonic.harmonic_censoring_h25_lifecycle_qualification import (
    H25_ADMIN_FAILURE,
    H25_ADMIN_FAULTS,
    H25_ADMIN_FORENSIC_INCONCLUSIVE,
    H25_ADMIN_INCONCLUSIVE,
    H25_ADMIN_PRECLAIM_ABORTED,
    H25_ADMIN_SUCCESS,
    H25_REAL_OS_PROBES,
    H25AdministrativeQualificationScenario,
    H25RealOSQualificationProbe,
    recompute_h25_administrative_lifecycle_result,
    recompute_h25_real_os_lifecycle_probe_result,
    run_h25_preclaim_administrative_lifecycle_qualification,
    run_h25_real_os_lifecycle_qualification_probe,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/polyphonic/harmonic_censoring_h25_lifecycle_qualification.py"
CONTRACT = ROOT / "configs/harmonic_censoring_h25_successor_decision_contract.json"


class H25AdministrativeLifecycleQualificationTests(unittest.TestCase):
    def _run(self, fault: str, *, suffix: str = "case"):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name) / f"h25-admin-{suffix}"
        result = run_h25_preclaim_administrative_lifecycle_qualification(
            root,
            H25AdministrativeQualificationScenario(
                scenario_id=suffix,
                fault=fault,
            ),
        )
        return root, result

    def test_source_is_standard_library_only_and_has_no_scientific_imports(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        imports: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports.update(item.name.split(".")[0] for item in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imports.add(node.module.split(".")[0])
        self.assertNotIn("numpy", imports)
        self.assertNotIn("threading", imports)
        self.assertNotIn("multiprocessing", imports)
        self.assertFalse(
            any(
                isinstance(node, ast.ImportFrom)
                and node.module
                and "harmonic_censoring_h24" in node.module
                for node in ast.walk(tree)
            )
        )

    def test_contract_keeps_every_scientific_authority_false(self) -> None:
        contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
        scope = contract["scope"]
        self.assertTrue(scope["contract_only"])
        for name, value in scope.items():
            if name != "contract_only":
                self.assertFalse(value, name)
        self.assertTrue(contract["predecessor_closure"]["one_shot_consumed"])
        self.assertTrue(contract["predecessor_closure"]["retry_forbidden"])

    def test_scenario_and_namespace_are_fail_closed(self) -> None:
        with self.assertRaises(ValueError):
            H25AdministrativeQualificationScenario("Bad ID")
        with self.assertRaises(ValueError):
            H25AdministrativeQualificationScenario("ok", "UNKNOWN")
        with tempfile.TemporaryDirectory() as temporary:
            base = Path(temporary)
            scenario = H25AdministrativeQualificationScenario("valid")
            with self.assertRaises(ValueError):
                run_h25_preclaim_administrative_lifecycle_qualification(
                    Path("h25-admin-relative"), scenario
                )
            with self.assertRaises(ValueError):
                run_h25_preclaim_administrative_lifecycle_qualification(
                    base / "scientific-result", scenario
                )
            existing = base / "h25-admin-existing"
            existing.mkdir()
            with self.assertRaises(FileExistsError):
                run_h25_preclaim_administrative_lifecycle_qualification(
                    existing, scenario
                )

    def test_nominal_lifecycle_publishes_bound_evidence_and_terminal(self) -> None:
        root, result = self._run("NONE", suffix="nominal")
        self.assertEqual(result.status, H25_ADMIN_SUCCESS)
        self.assertTrue(result.surrogate_claim_consumed)
        self.assertEqual(result.event_count, 5)
        self.assertTrue(result.claim_path.is_file())
        self.assertTrue(result.success_directory.is_dir())
        self.assertFalse(result.staging_directory.exists())
        self.assertTrue(result.transcript_path.is_file())
        self.assertTrue(result.terminal_path.is_file())
        self.assertFalse(result.forensic_path.exists())
        self.assertEqual(
            sorted(path.name for path in (root / "evidence").iterdir()),
            ["P0_boundary.json", "P1_boundary.json", "P2_boundary.json"],
        )
        recomputed = recompute_h25_administrative_lifecycle_result(root)
        self.assertEqual(recomputed["status"], H25_ADMIN_SUCCESS)
        self.assertEqual(recomputed["event_count"], 5)
        claim = json.loads(result.claim_path.read_text(encoding="utf-8"))
        self.assertFalse(claim["scientific_capability_issued"])
        self.assertFalse(claim["scientific_claim_created"])
        self.assertFalse(claim["scientific_population_used"])

    def test_logical_failure_and_operational_failure_are_distinct(self) -> None:
        root_failure, logical = self._run(
            "LOGICAL_FAILURE_AT_P1", suffix="logical-failure"
        )
        self.assertEqual(logical.status, H25_ADMIN_FAILURE)
        self.assertEqual(
            recompute_h25_administrative_lifecycle_result(root_failure)["status"],
            H25_ADMIN_FAILURE,
        )

        root_error, operational = self._run(
            "OPERATIONAL_ERROR_AT_P1", suffix="operational-error"
        )
        self.assertEqual(operational.status, H25_ADMIN_INCONCLUSIVE)
        self.assertEqual(
            recompute_h25_administrative_lifecycle_result(root_error)["status"],
            H25_ADMIN_INCONCLUSIVE,
        )

    def test_preclaim_EOF_and_timeouts_do_not_consume_surrogate_claim(self) -> None:
        for index, fault in enumerate(
            (
                "EOF_BEFORE_SURROGATE_CLAIM",
                "TIMEOUT_PREFLIGHT",
                "TIMEOUT_SURROGATE_CLAIM",
            )
        ):
            with self.subTest(fault=fault):
                root, result = self._run(fault, suffix=f"preclaim-{index}")
                self.assertEqual(result.status, H25_ADMIN_PRECLAIM_ABORTED)
                self.assertFalse(result.surrogate_claim_consumed)
                self.assertFalse(result.claim_path.exists())
                self.assertEqual(
                    recompute_h25_administrative_lifecycle_result(root)["status"],
                    H25_ADMIN_PRECLAIM_ABORTED,
                )

    def test_postclaim_transport_failures_close_inconclusive(self) -> None:
        for index, fault in enumerate(
            (
                "EOF_AFTER_SURROGATE_CLAIM",
                "PARENT_SSH_DISCONNECT_AFTER_SURROGATE_CLAIM",
                "SIGINT_AFTER_SURROGATE_CLAIM",
            )
        ):
            with self.subTest(fault=fault):
                root, result = self._run(fault, suffix=f"transport-{index}")
                self.assertEqual(result.status, H25_ADMIN_INCONCLUSIVE)
                self.assertTrue(result.claim_path.exists())
                self.assertTrue(result.terminal_path.exists())
                self.assertEqual(
                    recompute_h25_administrative_lifecycle_result(root)["status"],
                    H25_ADMIN_INCONCLUSIVE,
                )

    def test_each_boundary_timeout_closes_inconclusive(self) -> None:
        for index, fault in enumerate(("TIMEOUT_P0", "TIMEOUT_P1", "TIMEOUT_P2")):
            with self.subTest(fault=fault):
                root, result = self._run(fault, suffix=f"timeout-{index}")
                self.assertEqual(result.status, H25_ADMIN_INCONCLUSIVE)
                self.assertEqual(
                    recompute_h25_administrative_lifecycle_result(root)["status"],
                    H25_ADMIN_INCONCLUSIVE,
                )

    def test_evidence_failure_closes_inconclusive_without_missing_binding(self) -> None:
        root, result = self._run("EVIDENCE_WRITE_FAIL", suffix="evidence-fail")
        self.assertEqual(result.status, H25_ADMIN_INCONCLUSIVE)
        recomputed = recompute_h25_administrative_lifecycle_result(root)
        self.assertEqual(recomputed["status"], H25_ADMIN_INCONCLUSIVE)

    def test_publication_failures_leave_forensic_receipt(self) -> None:
        for index, fault in enumerate(
            (
                "TRANSCRIPT_PUBLISH_FAIL",
                "SUCCESS_RENAME_FAIL",
                "TERMINAL_PUBLISH_FAIL",
                "TIMEOUT_FAILURE_CLOSURE",
                "TIMEOUT_INCONCLUSIVE_CLOSURE",
            )
        ):
            with self.subTest(fault=fault):
                root, result = self._run(fault, suffix=f"publish-{index}")
                self.assertEqual(result.status, H25_ADMIN_FORENSIC_INCONCLUSIVE)
                self.assertTrue(result.claim_path.exists())
                self.assertTrue(result.forensic_path.exists())
                self.assertFalse(result.terminal_path.exists())
                recomputed = recompute_h25_administrative_lifecycle_result(root)
                self.assertEqual(
                    recomputed["status"], H25_ADMIN_FORENSIC_INCONCLUSIVE
                )

    def test_timeout_during_success_closure_has_predeclared_terminal(self) -> None:
        root, result = self._run(
            "TIMEOUT_SUCCESS_CLOSURE", suffix="success-timeout"
        )
        self.assertEqual(result.status, H25_ADMIN_INCONCLUSIVE)
        self.assertEqual(
            recompute_h25_administrative_lifecycle_result(root)["status"],
            H25_ADMIN_INCONCLUSIVE,
        )

    def test_every_preregistered_fault_is_exercised_by_the_suite(self) -> None:
        covered = {
            "NONE",
            "LOGICAL_FAILURE_AT_P1",
            "OPERATIONAL_ERROR_AT_P1",
            "EOF_BEFORE_SURROGATE_CLAIM",
            "EOF_AFTER_SURROGATE_CLAIM",
            "PARENT_SSH_DISCONNECT_AFTER_SURROGATE_CLAIM",
            "SIGINT_AFTER_SURROGATE_CLAIM",
            "TIMEOUT_PREFLIGHT",
            "TIMEOUT_SURROGATE_CLAIM",
            "TIMEOUT_P0",
            "TIMEOUT_P1",
            "TIMEOUT_P2",
            "TIMEOUT_SUCCESS_CLOSURE",
            "TIMEOUT_FAILURE_CLOSURE",
            "TIMEOUT_INCONCLUSIVE_CLOSURE",
            "EVIDENCE_WRITE_FAIL",
            "TRANSCRIPT_PUBLISH_FAIL",
            "TERMINAL_PUBLISH_FAIL",
            "SUCCESS_RENAME_FAIL",
        }
        self.assertEqual(covered, set(H25_ADMIN_FAULTS))

    def test_recomputation_rejects_evidence_terminal_and_claim_tampering(self) -> None:
        root_evidence, result_evidence = self._run("NONE", suffix="tamper-evidence")
        evidence = root_evidence / "evidence/P0_boundary.json"
        evidence.write_bytes(evidence.read_bytes() + b" ")
        with self.assertRaises(ValueError):
            recompute_h25_administrative_lifecycle_result(root_evidence)

        root_terminal, result_terminal = self._run("NONE", suffix="tamper-terminal")
        terminal = result_terminal.terminal_path
        payload = json.loads(terminal.read_text(encoding="utf-8"))
        payload["event_count"] += 1
        terminal.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            recompute_h25_administrative_lifecycle_result(root_terminal)

        root_claim, result_claim = self._run("NONE", suffix="tamper-claim")
        claim = result_claim.claim_path
        payload = json.loads(claim.read_text(encoding="utf-8"))
        payload["scientific_population_used"] = True
        claim.write_text(
            json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
            encoding="utf-8",
        )
        with self.assertRaises(ValueError):
            recompute_h25_administrative_lifecycle_result(root_claim)

    def test_one_shot_paths_cannot_be_reused(self) -> None:
        root, _ = self._run("NONE", suffix="one-shot")
        with self.assertRaises(FileExistsError):
            run_h25_preclaim_administrative_lifecycle_qualification(
                root,
                H25AdministrativeQualificationScenario("one-shot"),
            )

    def test_real_OS_transport_signal_and_timeout_probes_terminate(self) -> None:
        expected = {
            "REAL_NOMINAL": H25_ADMIN_SUCCESS,
            "REAL_EOF_BEFORE_SURROGATE_CLAIM": H25_ADMIN_PRECLAIM_ABORTED,
            "REAL_EOF_AFTER_SURROGATE_CLAIM": H25_ADMIN_INCONCLUSIVE,
            "REAL_PARENT_TRANSPORT_DISCONNECT_AFTER_SURROGATE_CLAIM": H25_ADMIN_INCONCLUSIVE,
            "REAL_SIGINT_AFTER_SURROGATE_CLAIM": H25_ADMIN_INCONCLUSIVE,
            "REAL_TIMEOUT_PREFLIGHT": H25_ADMIN_PRECLAIM_ABORTED,
            "REAL_TIMEOUT_SURROGATE_CLAIM": H25_ADMIN_PRECLAIM_ABORTED,
            "REAL_TIMEOUT_P0": H25_ADMIN_INCONCLUSIVE,
            "REAL_TIMEOUT_P1": H25_ADMIN_INCONCLUSIVE,
            "REAL_TIMEOUT_P2": H25_ADMIN_INCONCLUSIVE,
            "REAL_TIMEOUT_SUCCESS_CLOSURE": H25_ADMIN_INCONCLUSIVE,
            "REAL_TIMEOUT_FAILURE_CLOSURE": H25_ADMIN_FORENSIC_INCONCLUSIVE,
            "REAL_TIMEOUT_INCONCLUSIVE_CLOSURE": H25_ADMIN_FORENSIC_INCONCLUSIVE,
        }
        self.assertEqual(set(expected), set(H25_REAL_OS_PROBES))
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            for index, probe_name in enumerate(H25_REAL_OS_PROBES):
                with self.subTest(probe=probe_name):
                    if (
                        os.name == "nt"
                        and probe_name == "REAL_SIGINT_AFTER_SURROGATE_CLAIM"
                    ):
                        # Windows console-control delivery is not reliable under
                        # the test runner PTY.  This exact probe is exercised on
                        # the reviewed macOS arm64 target.
                        continue
                    result = run_h25_real_os_lifecycle_qualification_probe(
                        parent,
                        H25RealOSQualificationProbe(
                            probe_id=f"real-{index:02d}",
                            probe=probe_name,
                            timeout_seconds=0.08,
                            process_deadline_seconds=10.0,
                        ),
                    )
                    self.assertEqual(result.status, expected[probe_name])
                    self.assertEqual(result.child_exit_code, 0)
                    self.assertFalse(result.child_process_alive)
                    receipt = recompute_h25_real_os_lifecycle_probe_result(
                        result.controller_receipt_path
                    )
                    self.assertEqual(receipt["result_status"], expected[probe_name])
                    self.assertFalse(receipt["child_process_alive"])
                    if probe_name.startswith("REAL_TIMEOUT_"):
                        self.assertGreaterEqual(result.elapsed_seconds, 0.08)

    def test_real_OS_controller_receipt_rejects_config_and_log_tampering(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            result = run_h25_real_os_lifecycle_qualification_probe(
                parent,
                H25RealOSQualificationProbe(
                    probe_id="real-tamper-config",
                    probe="REAL_NOMINAL",
                    timeout_seconds=0.05,
                ),
            )
            config = parent / "h25-admin-real-tamper-config.worker-config.json"
            config.write_bytes(config.read_bytes() + b" ")
            with self.assertRaises(ValueError):
                recompute_h25_real_os_lifecycle_probe_result(
                    result.controller_receipt_path
                )

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            result = run_h25_real_os_lifecycle_qualification_probe(
                parent,
                H25RealOSQualificationProbe(
                    probe_id="real-tamper-exit",
                    probe="REAL_NOMINAL",
                    timeout_seconds=0.05,
                ),
            )
            marker = parent / "h25-admin-real-tamper-exit.worker-exited.json"
            marker.write_bytes(marker.read_bytes() + b"tamper")
            with self.assertRaises(ValueError):
                recompute_h25_real_os_lifecycle_probe_result(
                    result.controller_receipt_path
                )

        with tempfile.TemporaryDirectory() as temporary:
            parent = Path(temporary)
            result = run_h25_real_os_lifecycle_qualification_probe(
                parent,
                H25RealOSQualificationProbe(
                    probe_id="real-tamper-log",
                    probe="REAL_NOMINAL",
                    timeout_seconds=0.05,
                ),
            )
            log = parent / "h25-admin-real-tamper-log.worker-log.json"
            log.write_bytes(log.read_bytes() + b"tamper")
            with self.assertRaises(ValueError):
                recompute_h25_real_os_lifecycle_probe_result(
                    result.controller_receipt_path
                )


if __name__ == "__main__":
    unittest.main()
