from __future__ import annotations

import hashlib
import json
from pathlib import Path
import subprocess
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_review5_scientific_execution_identity_binding.json"


class H27Review5IdentityBindingTests(unittest.TestCase):
    def test_binding_is_exact_complete_and_dormant(self) -> None:
        value = json.loads(BINDING.read_text(encoding="utf-8"))
        self.assertEqual(value["schema_identity"], "H27_REVIEW5_SCIENTIFIC_EXECUTION_IDENTITY_BINDING_V1")
        self.assertEqual(value["implementation_commit"], "189e4e7499a6a1a719f152365bfc792f4d1fa4ac")
        self.assertEqual(value["component_count"], 8)
        self.assertEqual(len(value["components"]), 8)
        for component in value["components"].values():
            path = ROOT / component["path"]
            raw = subprocess.check_output(("git", "show", f"{value['implementation_commit']}:{component['path']}"), cwd=ROOT)
            blob = hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()
            self.assertEqual(blob, component["git_blob_sha1"])
            self.assertEqual(len(raw), component["size_bytes"])
            self.assertEqual(hashlib.sha256(raw).hexdigest(), component["sha256"])
            self.assertTrue(path.exists())
        for field in (
            "real_execution_authorized", "authority_creation_authorized",
            "claim_creation_authorized", "locked_test_authorized", "training_authorized",
        ):
            self.assertIs(value[field], False)


if __name__ == "__main__":
    unittest.main()
