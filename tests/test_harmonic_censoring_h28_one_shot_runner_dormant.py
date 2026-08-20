from __future__ import annotations

import ast
import hashlib
from pathlib import Path
import sys
import unittest

from scripts import h28_causal_timing_execute_once as runner


ROOT = Path(__file__).resolve().parents[1]


class H28DormantOneShotRunnerTests(unittest.TestCase):
    def test_runner_binding_is_byte_exact(self):
        path = ROOT / "configs/harmonic_censoring_h28_one_shot_runner_dormant_binding.json"
        raw = path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "1fbbd623af15354c6184f002842a6b9553525e7f3736457ce2f7ee3dfee67e6f",
        )
        document = runner._strict_json(raw, label="H28 runner binding test")
        for key in ("execution_contract", "runner"):
            item = document[key]
            payload = (ROOT / item["path"]).read_bytes()
            blob = hashlib.sha1(
                b"blob " + str(len(payload)).encode("ascii") + b"\0" + payload
            ).hexdigest()
            self.assertEqual(len(payload), item["size_bytes"])
            self.assertEqual(hashlib.sha256(payload).hexdigest(), item["sha256"])
            self.assertEqual(blob, item["git_blob"])

    def test_import_is_side_effect_free_and_does_not_import_science_runtime(self):
        self.assertNotIn("numpy", sys.modules)
        self.assertNotIn("tensorflow", sys.modules)
        self.assertFalse((ROOT / runner.OUTPUT_RELATIVE_PATH).exists())
        self.assertFalse((ROOT / runner.CLAIM_RELATIVE_PATH).exists())

    def test_execution_contract_is_byte_exact_and_still_dormant(self):
        path = ROOT / runner.EXECUTION_CONTRACT_RELATIVE_PATH
        raw = path.read_bytes()
        self.assertEqual(hashlib.sha256(raw).hexdigest(), runner.EXECUTION_CONTRACT_SHA256)
        document = runner._strict_json(raw, label="H28 execution contract test")
        self.assertEqual(document["schema_identity"], "H28_ONE_SHOT_EXECUTION_CONTRACT_V1")
        self.assertEqual(
            document["status"],
            "DORMANT_RUNNER_REQUIRES_SEPARATE_EXTERNAL_ACTIVATION",
        )
        authorization = document["authorization_boundary"]
        self.assertFalse(authorization["external_activation_exists"])
        self.assertFalse(authorization["claim_exists"])
        self.assertFalse(authorization["scientific_execution_authorized"])
        self.assertFalse(authorization["locked_test_authorized"])

    def test_missing_activation_fails_before_numpy_or_claim(self):
        missing = ROOT / "tmp/local/does-not-exist-h28-activation.json"
        self.assertFalse(missing.exists())
        with self.assertRaises(FileNotFoundError):
            runner.run_once(missing)
        self.assertNotIn("numpy", sys.modules)
        self.assertFalse((ROOT / runner.CLAIM_RELATIVE_PATH).exists())

    def test_duplicate_json_key_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "duplicate JSON key"):
            runner._strict_json(b'{"x":1,"x":2}', label="test")

    def test_source_orders_preclaim_numpy_claim_and_science(self):
        source = (ROOT / "scripts/h28_causal_timing_execute_once.py").read_text(
            encoding="utf-8"
        )
        run_source = ast.get_source_segment(
            source,
            next(
                node for node in ast.parse(source).body
                if isinstance(node, ast.FunctionDef) and node.name == "run_once"
            ),
        )
        self.assertIsNotNone(run_source)
        assert run_source is not None
        self.assertLess(run_source.index("_load_preclaim("), run_source.index("import numpy as np"))
        self.assertLess(run_source.index("_write_new(claim"), run_source.index("_publish_and_measure("))
        self.assertLess(run_source.index("_publish_and_measure("), run_source.index("_rename_no_replace("))

    def test_runner_has_no_retry_or_locked_test_path(self):
        source = (ROOT / "scripts/h28_causal_timing_execute_once.py").read_text(
            encoding="utf-8"
        )
        self.assertNotIn("locked_test", source.lower().replace('"locked_test_used"', ""))
        self.assertNotIn("while True", source)
        self.assertNotIn("os.replace", source)
        self.assertIn("FAILED_AFTER_CLAIM_NO_RETRY", source)
        self.assertIn("renameatx_np", source)


if __name__ == "__main__":
    unittest.main()
