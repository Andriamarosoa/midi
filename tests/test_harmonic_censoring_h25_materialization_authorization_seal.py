import hashlib
import json
import subprocess
import unittest
from pathlib import Path

from src.polyphonic import harmonic_censoring_h25_materialization_authority as authority


ROOT = Path(__file__).resolve().parents[1]


class H25MaterializationAuthorizationSealTests(unittest.TestCase):
    def test_seal_is_exact_acyclic_and_bound_to_reviewed_authority(self):
        raw = (ROOT / authority.AUTHORIZATION_SEAL).read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r", raw)
        seal = authority.materializer.parse_sealed_json(raw, "materialization authorization seal")
        self.assertEqual(
            set(seal),
            {
                "schema_version",
                "purpose",
                "status",
                "authorized_action",
                "reviewed_authority_commit",
                "authority_source_blob",
                "authority_contract_sha256",
                "reviewed_materializer_commit",
                "materializer_source_blob",
                "sealed_input_raw_sha256",
            },
        )
        self.assertNotIn("activation_commit", seal)
        self.assertEqual(seal["schema_version"], 1)
        self.assertEqual(
            seal["purpose"],
            "harmonic_censoring_h25_population_materialization_authorization_seal",
        )
        self.assertEqual(seal["status"], "reviewed_H25_population_materialization_authorized_once")
        self.assertEqual(seal["authorized_action"], "AUTHORIZED_TO_MATERIALIZE_H25_SYNTHETIC_V1_ONCE")
        self.assertEqual(seal["reviewed_authority_commit"], "52337716cb80ed3e3937da7ca17575b357e77298")
        self.assertEqual(seal["authority_source_blob"], "d58351b6fd363f1d843c7c43501eb0ecf49e57df")

    def test_seal_binds_contract_materializer_and_all_five_inputs(self):
        seal = json.loads((ROOT / authority.AUTHORIZATION_SEAL).read_text(encoding="utf-8"))
        contract_raw = (ROOT / authority.AUTHORITY_CONTRACT).read_bytes()
        contract = json.loads(contract_raw.decode("utf-8"))
        self.assertEqual(seal["authority_contract_sha256"], hashlib.sha256(contract_raw).hexdigest())
        self.assertEqual(seal["reviewed_materializer_commit"], authority.REVIEWED_MATERIALIZER_COMMIT)
        self.assertEqual(seal["materializer_source_blob"], authority.REVIEWED_MATERIALIZER_BLOB)
        self.assertEqual(
            seal["sealed_input_raw_sha256"],
            {
                name: binding["raw_sha256"]
                for name, binding in contract["sealed_git_blobs"].items()
            },
        )
        reviewed_blob = subprocess.check_output(
            [
                "git",
                "rev-parse",
                f"{seal['reviewed_authority_commit']}:src/polyphonic/harmonic_censoring_h25_materialization_authority.py",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
        ).strip()
        self.assertEqual(reviewed_blob, seal["authority_source_blob"])


if __name__ == "__main__":
    unittest.main()
