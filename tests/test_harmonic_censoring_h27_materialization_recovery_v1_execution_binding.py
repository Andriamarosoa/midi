from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v1_execution_binding.json"


class H27RecoveryV1ExecutionBindingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.value = json.loads(BINDING.read_bytes())

    def test_every_bootstrap_component_is_byte_exact(self) -> None:
        components = self.value["bootstrap_components"]
        self.assertEqual(len(components), 7)
        self.assertEqual(len({row["destination_relative"] for row in components}), 7)
        for row in components:
            raw = (ROOT / row["repository_path"]).read_bytes()
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
            self.assertEqual((len(raw), blob, hashlib.sha256(raw).hexdigest()), (row["size_bytes"], row["git_blob_sha1"], row["raw_sha256"]))

    def test_paths_are_new_and_scope_stops_before_science(self) -> None:
        self.assertEqual(self.value["recovery_root"], "/Users/amcarene/h27-admin-recovery-v1")
        self.assertEqual(self.value["directories_exact"], ["activation","authority","claims","population","runner-r1","terminal"])
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


if __name__ == "__main__":
    unittest.main()
