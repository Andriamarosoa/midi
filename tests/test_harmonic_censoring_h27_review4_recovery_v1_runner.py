from __future__ import annotations

import hashlib
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import unittest


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/h27_review4_recovery_v1_execute_once.py"
ACTIVATION = ROOT / "configs/harmonic_censoring_h27_materialization_recovery_v1_activation.json"


def load_runner():
    spec = importlib.util.spec_from_file_location("h27_review4_recovery_v1_test", RUNNER)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class H27Review4RecoveryV1RunnerTests(unittest.TestCase):
    def test_activation_is_exact_independent_single_use_artifact(self) -> None:
        raw = ACTIVATION.read_bytes()
        value = json.loads(raw)
        self.assertNotIn(b"\r", raw)
        self.assertEqual(value["artifact_type"], "h27_review4_materialization_recovery_v1_activation")
        self.assertEqual(value["activation_id"], "101ef27d0bd246816696623a24608433d50850bfcaf5d4f02a2affb85d59ee5b")
        self.assertEqual(value["authority_instance_id"], "f1e8fb1a5c9fab6a75608a19a73916791bab406334d8a1c7162cbe3d8c5035e2")
        self.assertEqual(value["issuer_id"], "h27-recovery-execution-codex-mac-primary")
        self.assertTrue(value["single_use"])
        self.assertFalse(value["consumed"])
        self.assertFalse(value["science_authorized"])
        self.assertFalse(value["locked_test_used"])

    def test_wrapper_binds_only_disjoint_recovery_paths(self) -> None:
        runner = load_runner()
        module = SimpleNamespace()
        runner.configure(module)
        self.assertEqual(module.ADMIN.as_posix(), "/Users/amcarene/h27-admin-recovery-v1")
        self.assertEqual(module.OPERATIONAL_PARENT_NAME, "runner-r1")
        self.assertEqual(module.TERMINAL_PARENT_NAME, "terminal")
        self.assertTrue(module.ACTIVATION.as_posix().startswith(module.ADMIN.as_posix() + "/"))
        self.assertTrue(module.AUTHORITY.as_posix().startswith(module.ADMIN.as_posix() + "/"))
        self.assertTrue(module.CLAIM.as_posix().startswith(module.ADMIN.as_posix() + "/"))
        self.assertNotEqual(module.AUTHORITY_INSTANCE_ID, "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a")
        self.assertEqual({label for label, _, _ in module.RECOVERY_PREDECESSOR}, {"authority", "claim"})
        self.assertTrue(all(path.as_posix().startswith("/Users/amcarene/h27-admin/") for _, path, _ in module.RECOVERY_PREDECESSOR))

    def test_wrapper_verifies_base_bytes_before_import(self) -> None:
        source = RUNNER.read_text(encoding="utf-8")
        self.assertLess(source.index("raw = BASE.read_bytes()"), source.index("spec_from_file_location"))
        raw = (ROOT / "scripts/h27_review4_execute_once.py").read_bytes()
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode() + b"\0" + raw).hexdigest()
        runner = load_runner()
        self.assertNotEqual((len(raw), blob, hashlib.sha256(raw).hexdigest()), (runner.BASE_SIZE, runner.BASE_GIT_BLOB_SHA1, runner.BASE_RAW_SHA256))

    def test_base_runner_attests_predecessor_before_new_claim(self) -> None:
        source = (ROOT / "scripts/h27_review4_execute_once.py").read_text(encoding="utf-8")
        self.assertLess(source.index("predecessor={\"consumed\":attest_recovery_predecessor()"), source.index("def consume_and_run"))
        self.assertLess(source.index("claim_fd,claim_raw=write_new_at"), source.index("materialize_h27_production_population"))
        self.assertIn('"predecessor_consumed_attestation":predecessor', source)
        self.assertIn('"predecessor_consumed_attested":RECOVERY_PREDECESSOR is not None', source)

    def test_activation_mode_is_0400_before_and_after_claim(self) -> None:
        source = (ROOT / "scripts/h27_review4_execute_once.py").read_text(encoding="utf-8")
        self.assertIn("open_relative(activation_parent,ACTIVATION.name,0o400)", source)
        self.assertIn("read_fd(activation_fd,0o400)", source)
        self.assertNotIn("read_fd(activation_fd,0o600)", source)
        self.assertLess(source.index("claim_fd,claim_raw=write_new_at"), source.rindex("read_fd(activation_fd,0o400)"))


if __name__ == "__main__":
    unittest.main()
