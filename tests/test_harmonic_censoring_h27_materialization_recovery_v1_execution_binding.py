from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v1_execution_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v1_execution_external_seal.json"
COMPATIBILITY = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v1_materializer_compatibility_binding.json"
COMPATIBILITY_SEAL = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v1_materializer_compatibility_external_seal.json"


class H27RecoveryV1ExecutionBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = json.loads(BINDING.read_bytes())

    def test_every_bootstrap_component_is_byte_exact(self) -> None:
        components = self.value["bootstrap_components"]
        self.assertEqual(len(components), 9)
        self.assertEqual(len({row["destination_relative"] for row in components}), 9)
        for row in components:
            raw = (ROOT / row["repository_path"]).read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual((len(raw), blob, hashlib.sha256(raw).hexdigest()), (row["size_bytes"], row["git_blob_sha1"], row["raw_sha256"]))

    def test_paths_are_new_and_scope_stops_before_science(self) -> None:
        self.assertEqual(self.value["recovery_root"], "/Users/amcarene/h27-admin-recovery-v1")
        self.assertEqual(self.value["directories_exact"], ["activation","authority","claims","population","runner-r1","terminal"])
        self.assertEqual(self.value["runtime_entrypoint"], "/Users/amcarene/midi-worker/.venv/bin/python")
        self.assertTrue(all(not row["destination_relative"].startswith("/") and ".." not in Path(row["destination_relative"]).parts for row in self.value["bootstrap_components"]))
        self.assertTrue(self.value["predecessor_read_only"]["must_not_be_modified_deleted_or_reused"])
        self.assertEqual(self.value["scope"], {"review4_only":True,"science":False,"p0":False,"p1":False,"p2":False,"locked_test":False,"training":False,"calibration":False})

    def test_one_shot_boundary_is_fail_closed(self) -> None:
        rules = self.value["one_shot_rules"]
        self.assertTrue(rules["all_paths_and_component_bytes_verified_before_ack"])
        self.assertTrue(rules["all_destinations_absent_before_ack"])
        self.assertEqual(rules["materializer_invocations_maximum"], 1)
        self.assertTrue(rules["retry_after_ack_or_claim_forbidden"])
        self.assertTrue(rules["success_requires_terminal_and_124_reconciled_records"])

    def test_external_seal_binds_exact_execution_binding(self) -> None:
        seal = json.loads(SEAL.read_bytes())
        row = seal["execution_binding"]
        raw = BINDING.read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        self.assertEqual((len(raw), blob, hashlib.sha256(raw).hexdigest()), (row["size_bytes"], row["git_blob_sha1"], row["raw_sha256"]))
        boundary = seal["authorization_boundary"]
        self.assertTrue(boundary["external_pass_required_before_any_ssh"])
        self.assertTrue(boundary["old_activation_authority_claim_and_runner_are_immutable"])
        self.assertEqual((boundary["expected_records"], boundary["expected_baseline_records"], boundary["expected_p2_records"]), (124, 17, 107))
        self.assertEqual(set(seal["forbidden"]), {"science","P0","P1","P2","locked_test","training","calibration","old_activation_retry"})

    def test_materializer_compatibility_binding_is_byte_exact(self) -> None:
        value = json.loads(COMPATIBILITY.read_bytes())
        for key in ("recovery_contract","recovery_activation","base_runner","recovery_runner","unchanged_materializer","historical_operational_binding","historical_operational_seal"):
            row = value[key]; raw = (ROOT / row["path"]).read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual((len(raw),blob,hashlib.sha256(raw).hexdigest()),(row["size_bytes"],row["git_blob_sha1"],row["raw_sha256"]))
        invariants=value["compatibility_invariants"]
        self.assertTrue(invariants["materializer_bytes_unchanged"])
        self.assertTrue(invariants["old_claim_is_history_not_credential"])
        self.assertFalse(invariants["science_authorized"])
        seal=json.loads(COMPATIBILITY_SEAL.read_bytes()); row=seal["compatibility_binding"]
        raw=COMPATIBILITY.read_bytes(); blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        self.assertEqual((len(raw),blob,hashlib.sha256(raw).hexdigest()),(row["size_bytes"],row["git_blob_sha1"],row["raw_sha256"]))


if __name__ == "__main__":
    unittest.main()
