from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/h27_review4_recovery_v2_execute_once.py"
BASE = ROOT / "scripts/h27_review4_execute_once.py"
ACTIVATION = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v2_activation.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("h27_review4_recovery_v2_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module); return module


class H27Review4RecoveryV2RunnerTests(unittest.TestCase):
    def test_activation_and_base_are_exact(self):
        module=load_runner(); activation=ACTIVATION.read_bytes(); base=BASE.read_bytes()
        self.assertEqual(hashlib.sha256(activation).hexdigest(),module.ACTIVATION_SHA256)
        blob=hashlib.sha1(b"blob "+str(len(base)).encode()+b"\0"+base).hexdigest()
        self.assertEqual((len(base),blob,hashlib.sha256(base).hexdigest()),(module.BASE_SIZE,module.BASE_GIT_BLOB_SHA1,module.BASE_RAW_SHA256))
        value=json.loads(activation); self.assertEqual(value["administrative_root"],"/Users/amcarene/h27-admin-recovery-v2")
        self.assertFalse(value["science_authorized"]); self.assertFalse(value["locked_test_used"])

    def test_v2_binds_two_read_only_predecessors(self):
        wrapper=load_runner(); module=SimpleNamespace(); wrapper.configure(module)
        self.assertEqual(module.ADMIN.as_posix(),"/Users/amcarene/h27-admin-recovery-v2")
        self.assertEqual(module.RECOVERY_FAILED_ROOT[0].as_posix(),"/Users/amcarene/h27-admin-recovery-v1")
        self.assertEqual(len(module.RECOVERY_FAILED_ROOT[2]),9)
        self.assertTrue(all(row[4]==0o400 for row in module.RECOVERY_FAILED_ROOT[2]))
        self.assertEqual(len(module.RECOVERY_FAILED_ROOT[3]),5)
        self.assertEqual({label for label,_,_ in module.RECOVERY_PREDECESSOR},{"authority","claim"})

    def test_activation_mode_is_closed_at_both_reads(self):
        source=BASE.read_text(encoding="utf-8")
        self.assertIn("open_relative(activation_parent,ACTIVATION.name,0o400)",source)
        self.assertIn("read_fd(activation_fd,0o400)",source)
        self.assertNotIn("read_fd(activation_fd,0o600)",source)
        self.assertLess(source.index("claim_fd,claim_raw=write_new_at"),source.index("consumer=attested_consumer"))

    def test_true_frozen_plan_stays_124_without_execution(self):
        from tests.test_harmonic_censoring_h27_review4_materializer import Review4MaterializerTests
        case=Review4MaterializerTests("test_real_frozen_contract_builds_complete_124_record_plan")
        result=unittest.TestResult(); case.run(result)
        self.assertTrue(result.wasSuccessful(),result.errors+result.failures)


if __name__ == "__main__": unittest.main()
