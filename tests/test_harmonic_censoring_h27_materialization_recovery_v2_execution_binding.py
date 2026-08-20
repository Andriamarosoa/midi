from __future__ import annotations
import hashlib,json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
BINDING=ROOT/"configs/harmonic_censoring_h27_materialization_recovery_v2_execution_binding.json"

class RecoveryV2ExecutionBindingTests(unittest.TestCase):
    def test_all_nine_components_are_exact(self):
        value=json.loads(BINDING.read_bytes()); rows=value["bootstrap_components"]
        self.assertEqual(len(rows),9); self.assertEqual(len({r["destination_relative"] for r in rows}),9)
        for row in rows:
            raw=(ROOT/row["repository_path"]).read_bytes()
            blob=hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
            self.assertEqual((blob,len(raw),hashlib.sha256(raw).hexdigest()),(row["git_blob_sha1"],row["size_bytes"],row["raw_sha256"]))
    def test_scope_and_modes_are_fail_closed(self):
        value=json.loads(BINDING.read_bytes())
        self.assertEqual(value["recovery_root"],"/Users/amcarene/h27-admin-recovery-v2")
        self.assertEqual(value["runtime_entrypoint"],"/Users/amcarene/midi-worker/.venv/bin/python")
        self.assertEqual(value["bootstrap_file_mode"],"0400")
        self.assertEqual(value["directories_exact"],["activation","authority","claims","population","runner-r1","terminal"])
        self.assertTrue(value["predecessors_read_only"]["failed_preclaim_authority_absent"])
        self.assertTrue(value["one_shot_rules"]["retry_after_ack_or_claim_forbidden"])
        self.assertEqual(value["scope"],{"review4_only":True,"science":False,"p0":False,"p1":False,"p2":False,"locked_test":False,"training":False,"calibration":False})

if __name__=="__main__": unittest.main()
