from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / "configs/harmonic_censoring_h27_review5_scientific_execution_external_seal.json"


class H27Review5ExternalSealTests(unittest.TestCase):
    def test_seal_binds_exact_prior_commit_and_remains_dormant(self) -> None:
        value = json.loads(SEAL.read_text(encoding="utf-8"))
        self.assertEqual(value["schema_identity"], "H27_REVIEW5_SCIENTIFIC_EXECUTION_EXTERNAL_SEAL_V4")
        self.assertEqual(value["schema_version"], 4)
        self.assertEqual(value["implementation_commit"], "74805ea3ec870385c0ad9d0c4d7e9354a97965a2")
        self.assertEqual(value["identity_binding_commit"], "8dd545633553b3683034594e26a32941b9ff1558")
        binding = value["identity_binding"]
        raw = subprocess.check_output(
            ("git", "show", f"{value['identity_binding_commit']}:{binding['path']}"), cwd=ROOT
        )
        blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
        self.assertEqual(blob, binding["git_blob_sha1"])
        self.assertEqual(len(raw), binding["size_bytes"])
        self.assertEqual(hashlib.sha256(raw).hexdigest(), binding["sha256"])
        self.assertEqual(value["success_terminal_status"], "H27_REVIEW5_SCIENCE_27_OF_27_PASS_STOP_BEFORE_POST_SCIENCE")
        self.assertTrue(value["activation_required_before_claim"])
        self.assertTrue(value["activation_must_bind_this_seal_commit"])
        self.assertEqual(value["per_test_receipts_required"], 27)
        self.assertTrue(value["terminal_completion_marker_required"])
        for field in (
            "real_execution_authorized", "authority_creation_authorized",
            "claim_creation_authorized", "locked_test_authorized", "training_authorized",
            "retry_allowed",
        ):
            self.assertIs(value[field], False)


if __name__ == "__main__":
    unittest.main()
