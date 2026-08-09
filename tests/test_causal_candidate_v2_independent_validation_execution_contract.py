from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from src.polyphonic import (
    causal_candidate_v2_independent_validation_execution_contract as contract,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class IndependentV2ExecutionContractTests(unittest.TestCase):
    def _payload(self) -> dict[str, object]:
        root = Path(__file__).resolve().parents[1]
        return json.loads((
            root / contract.INDEPENDENT_V2_EXECUTION_CONTRACT_RELATIVE_PATH
        ).read_text(encoding="utf-8"))

    def test_versioned_contract_is_sealed_and_non_executable(self) -> None:
        root = Path(__file__).resolve().parents[1]
        path = root / contract.INDEPENDENT_V2_EXECUTION_CONTRACT_RELATIVE_PATH
        payload = self._payload()

        self.assertEqual(_sha256(path), contract.INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256)
        self.assertEqual(payload["status"], contract.INDEPENDENT_V2_EXECUTION_CONTRACT_STATUS)
        self.assertEqual(
            tuple(payload["authorization_scope"]["allowed_now"]),
            contract.INDEPENDENT_V2_EXECUTION_ALLOWED_NOW,
        )
        self.assertFalse(payload["locked_test_used"])
        self.assertIn("real_runner_execution", payload["authorization_scope"]["forbidden_now"])
        self.assertIn("runner_implementation", payload["authorization_scope"]["forbidden_now"])
        self.assertTrue(payload["future_runner_semantics"]["runner_is_not_part_of_this_contract"])
        self.assertFalse(payload["future_runner_semantics"]["execution_authorized_now"])
        self.assertFalse(payload["validation_consumption_policy"]["automatic_retry"])
        self.assertTrue(payload["validation_consumption_policy"]["cohort_consumed_once_any_ab_metric_is_produced_or_observed"])
        self.assertEqual(payload["required_report_for_any_future_execution"]["recording_count"], 30)
        self.assertEqual(
            payload["prerequisite_provenance"]["closed_independent_protocol_sha256"],
            contract.INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256,
        )
        self.assertEqual(
            payload["prerequisite_provenance"]["asset_evidence_sha256"],
            contract.INDEPENDENT_V2_ASSET_EVIDENCE_SHA256,
        )
        self.assertEqual(
            payload["prerequisite_provenance"]["asset_evidence_builder_protocol_sha256"],
            contract.INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256,
        )
        self.assertEqual(payload["cohort"]["recording_count"], 30)
        self.assertEqual(payload["cohort"]["independent_group_count"], 20)
        self.assertEqual(payload["cohort"]["recordings_per_dataset"]["guitarset_poly_mix"], 0)

    def test_loader_returns_only_a_factory_attested_contract(self) -> None:
        root = Path(__file__).resolve().parents[1]
        sealed = contract.load_sealed_independent_v2_execution_contract(root)
        self.assertIs(
            contract.require_sealed_independent_v2_execution_contract(sealed), sealed
        )
        self.assertFalse(dict(sealed.decision_rules)["automatic_promotion"])
        self.assertEqual(
            dict(sealed.decision_rules)["global_causal_false_noteon_relative_reduction_minimum"],
            0.01,
        )
        forged = contract.IndependentV2ExecutionContract(
            contract_sha256=contract.INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256,
            closed_independent_protocol_sha256=contract.INDEPENDENT_V2_CLOSED_PROTOCOL_SHA256,
            asset_evidence_sha256=contract.INDEPENDENT_V2_ASSET_EVIDENCE_SHA256,
            asset_evidence_builder_protocol_sha256=(
                contract.INDEPENDENT_V2_ASSET_EVIDENCE_BUILDER_PROTOCOL_SHA256
            ),
            recording_count=30,
            independent_group_count=20,
            wall_timeout_seconds=900,
            threshold=0.31,
            candidate_gate_placement="post_ranking_pre_noteon",
            decision_rules=(("automatic_promotion", False),),
        )
        with self.assertRaisesRegex(RuntimeError, "loaded from sealed bytes"):
            contract.require_sealed_independent_v2_execution_contract(forged)

    def test_non_executable_and_escape_mutations_fail_closed(self) -> None:
        payload = copy.deepcopy(self._payload())
        payload["future_runner_semantics"]["execution_authorized_now"] = True
        with self.assertRaisesRegex(ValueError, "future runner semantics"):
            contract._require_exact_execution_payload(payload)

        payload = copy.deepcopy(self._payload())
        payload["validation_consumption_policy"]["automatic_retry"] = True
        with self.assertRaisesRegex(ValueError, "consumption policy"):
            contract._require_exact_execution_payload(payload)

        payload = copy.deepcopy(self._payload())
        payload["required_report_for_any_future_execution"]["required_metrics"] = payload["required_report_for_any_future_execution"]["required_metrics"][:-1]
        with self.assertRaisesRegex(ValueError, "required report metrics"):
            contract._require_exact_execution_payload(payload)

        payload = copy.deepcopy(self._payload())
        payload["required_report_for_any_future_execution"]["provenance"] = payload["required_report_for_any_future_execution"]["provenance"][:-1]
        with self.assertRaisesRegex(ValueError, "required report provenance"):
            contract._require_exact_execution_payload(payload)

        payload = copy.deepcopy(self._payload())
        payload["prerequisite_provenance"]["asset_evidence_relative_path"] = "../escape.json"
        with self.assertRaisesRegex(ValueError, "beneath the repository root"):
            contract._require_exact_execution_payload(payload)

    def test_raw_digest_mismatch_fails_before_json_parse(self) -> None:
        root = Path(__file__).resolve().parents[1]
        with mock.patch.object(
            contract, "INDEPENDENT_V2_EXECUTION_CONTRACT_SHA256", "0" * 64
        ), mock.patch.object(contract.json, "loads") as loads:
            with self.assertRaisesRegex(RuntimeError, "SHA-256 mismatch"):
                contract.load_sealed_independent_v2_execution_contract(root)
        loads.assert_not_called()

    def test_import_has_no_tensorflow_or_cli(self) -> None:
        code = (
            "import sys; "
            "import src.polyphonic.causal_candidate_v2_independent_validation_execution_contract as module; "
            "raise SystemExit(int('tensorflow' in sys.modules or hasattr(module, 'main')))"
        )
        completed = subprocess.run(
            [sys.executable, "-c", code],
            cwd=Path(__file__).resolve().parents[1],
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)


if __name__ == "__main__":
    unittest.main()
