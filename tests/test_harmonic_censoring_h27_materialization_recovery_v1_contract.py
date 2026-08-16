from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"configs/harmonic_censoring_h27_materialization_recovery_v1_contract.json"


class H27MaterializationRecoveryV1ContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.raw=CONTRACT.read_bytes()
        self.value=json.loads(self.raw)

    def test_contract_is_strict_lf_json_and_dormant(self) -> None:
        self.assertNotIn(b"\r",self.raw)
        self.assertEqual(self.value["schema_version"],1)
        self.assertIs(type(self.value["schema_version"]),int)
        self.assertEqual(self.value["status"],"DORMANT_PENDING_EXTERNAL_REVIEW_NO_EXECUTION_AUTHORIZED")
        self.assertFalse(self.value["scientific_identity"]["science_authorized"])
        self.assertFalse(self.value["scientific_identity"]["locked_test_used"])

    def test_terminal_predecessor_is_consumed_and_never_reusable(self) -> None:
        prior=self.value["terminal_predecessor"]
        self.assertEqual(prior["archive_commit"],"8ff8049a3745208bc9bab1fb79f073ca12fcb073")
        self.assertTrue(prior["authority_created"])
        self.assertTrue(prior["claim_created"])
        self.assertTrue(prior["capability_consumed"])
        self.assertFalse(prior["retry_allowed"])
        self.assertFalse(prior["credentials_reusable"])
        self.assertFalse(prior["cleanup_or_repair_allowed"])

    def test_recovery_identity_and_paths_are_independent(self) -> None:
        prior=self.value["terminal_predecessor"]
        recovery=self.value["recovery_lineage"]
        self.assertNotEqual(recovery["authority_instance_id"],prior["authority_instance_id"])
        self.assertNotEqual(recovery["activation_path"],prior["activation_path"])
        self.assertNotEqual(recovery["authority_path"],prior["authority_path"])
        self.assertNotEqual(recovery["claim_path"],prior["claim_path"])
        self.assertTrue(all(path.startswith(recovery["administrative_root"]+"/") for key,path in recovery.items() if key.endswith("_path") or key=="runner_root"))
        self.assertEqual(recovery["invocations_maximum"],1)
        self.assertFalse(recovery["retry_allowed"])
        self.assertTrue(recovery["old_credentials_forbidden"])

    def test_scientific_population_and_materializer_are_unchanged(self) -> None:
        identity=self.value["scientific_identity"]
        self.assertEqual((identity["expected_total_records"],identity["expected_baseline_records"],identity["expected_p2_records"]),(124,17,107))
        self.assertEqual(identity["population_namespace"],"H27_SYNTHETIC_V1")
        self.assertTrue(identity["population_namespace_unchanged"])
        self.assertFalse(identity["taxonomy_changed"])
        self.assertFalse(identity["population_changed"])
        materializer=ROOT/"src/polyphonic/harmonic_censoring_h27_review4_materializer.py"
        raw=materializer.read_bytes()
        self.assertEqual(len(raw),identity["materializer_size_bytes"])
        self.assertEqual(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),identity["materializer_git_blob_sha1"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),identity["materializer_raw_sha256"])

    def test_loader_fix_is_exactly_bound_and_future_execution_remains_forbidden(self) -> None:
        loader=self.value["loader_correction"]
        raw=(ROOT/"scripts/h27_review4_execute_once.py").read_bytes()
        self.assertEqual(len(raw),loader["runner_size_bytes"])
        self.assertEqual(hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest(),loader["runner_git_blob_sha1"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(),loader["runner_raw_sha256"])
        self.assertEqual(loader["strict_json_label_policy"],"path.as_posix()")
        self.assertEqual(loader["real_frozen_contract_plan_cardinality_tested"],124)
        requirements=self.value["future_activation_requirements"]
        self.assertTrue(requirements["no_ssh_before_external_pass"])
        self.assertTrue(requirements["new_runner_binding_and_external_seal_required"])
        self.assertTrue(requirements["prior_authority_and_claim_must_remain_immutable"])


if __name__=="__main__":
    unittest.main()
