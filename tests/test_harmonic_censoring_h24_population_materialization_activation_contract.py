import hashlib
import json
from pathlib import Path
import subprocess
import unittest

from src.polyphonic import harmonic_censoring_h24_population_materializer as materializer


ROOT = Path(__file__).resolve().parents[1]
SEAL_PATH = ROOT / "configs/harmonic_censoring_h24_population_materialization_authorization_seal.json"
ACTIVATION_PATH = ROOT / "configs/harmonic_censoring_h24_population_materialization_activation_contract.json"
EXPECTED_SEAL_SHA256 = "3d5849b89c31037bbd07be391c3a7e8e5ef53b55f65fa4c6a8be0e19bb0ef218"
REVIEWED_COMMIT = "101103e63420de3703c045142291a9f231373f77"
REVIEWED_SOURCE_BLOB = "16210df0830eb62cc32f6900af51ad3d9e4972e5"


def _load(path: Path) -> tuple[bytes, dict[str, object]]:
    raw = path.read_bytes()
    return raw, json.loads(raw)


class H24PopulationMaterializationActivationContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seal_raw, cls.seal = _load(SEAL_PATH)
        cls.activation_raw, cls.activation = _load(ACTIVATION_PATH)

    def test_seal_bytes_and_parser_bind_the_approved_materializer(self):
        self.assertNotIn(b"\r", self.seal_raw)
        digest = hashlib.sha256(self.seal_raw).hexdigest()
        self.assertEqual(digest, EXPECTED_SEAL_SHA256)
        parsed = materializer.validate_h24_population_materialization_authorization_seal(
            self.seal, raw_sha256=digest
        )
        self.assertEqual(parsed.reviewed_materializer_commit, REVIEWED_COMMIT)
        self.assertEqual(parsed.materializer_source_blob, REVIEWED_SOURCE_BLOB)
        self.assertEqual(
            parsed.materialization_contract_raw_sha256,
            materializer.H24_MATERIALIZATION_CONTRACT_RAW_SHA256,
        )

    def test_seal_changed_files_equal_the_reviewed_commit_topology(self):
        actual = subprocess.check_output(
            [
                "git", "diff-tree", "--no-commit-id", "--name-only", "-r",
                REVIEWED_COMMIT,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
        ).splitlines()
        self.assertEqual(self.seal["exact_changed_files"], sorted(actual))
        blob = subprocess.check_output(
            [
                "git", "rev-parse",
                f"{REVIEWED_COMMIT}:src/polyphonic/harmonic_censoring_h24_population_materializer.py",
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
        ).strip()
        self.assertEqual(blob, REVIEWED_SOURCE_BLOB)

    def test_activation_contract_cross_binds_the_exact_seal_and_materializer(self):
        self.assertNotIn(b"\r", self.activation_raw)
        seal_binding = self.activation["authorization_seal"]
        reviewed = self.activation["reviewed_materializer"]
        self.assertEqual(seal_binding["path"], materializer.H24_AUTHORIZATION_SEAL_RELATIVE_PATH.as_posix())
        self.assertEqual(seal_binding["raw_sha256"], EXPECTED_SEAL_SHA256)
        self.assertEqual(reviewed["commit"], REVIEWED_COMMIT)
        self.assertEqual(reviewed["source_blob"], REVIEWED_SOURCE_BLOB)
        self.assertEqual(reviewed["exact_changed_files"], self.seal["exact_changed_files"])

    def test_activation_commit_is_external_OS_bound_and_breaks_self_reference(self):
        binding = self.activation["activation_commit_contract"]
        self.assertTrue(binding["must_be_distinct_from_reviewed_materializer_commit"])
        self.assertTrue(binding["commit_sha_is_not_embedded_to_avoid_self_reference"])
        self.assertEqual(
            binding["environment_variable"],
            materializer.H24_AUTHORIZATION_COMMIT_ENV,
        )
        self.assertTrue(binding["checkout_HEAD_must_equal_environment_value"])
        self.assertTrue(binding["external_review_of_exact_activation_commit_required"])
        self.assertEqual(
            binding["activation_commit_exact_changed_files"],
            [
                ".gitattributes",
                "configs/harmonic_censoring_h24_population_materialization_activation_contract.json",
                "configs/harmonic_censoring_h24_population_materialization_authorization_seal.json",
                "readme/README.md",
                "readme/results/2026-08-10_harmonic-censoring-h24-population-materialization-activation-contract.md",
                "tests/test_harmonic_censoring_h24_population_materialization_activation_contract.py",
                "tests/test_harmonic_censoring_h24_population_materializer_dormant.py",
            ],
        )
        self.assertNotIn("activation_commit", self.activation)
        self.assertNotIn("activation_commit_sha", self.activation)

    def test_fixed_paths_and_runtime_are_exactly_the_implementation_values(self):
        paths = self.activation["fixed_paths"]
        self.assertEqual(paths["claim_marker"], materializer._FIXED_PATHS["claim_marker_path"])
        self.assertEqual(paths["staging_directory"], materializer._FIXED_PATHS["staging_directory"])
        self.assertEqual(paths["success_directory"], materializer._FIXED_PATHS["success_directory"])
        self.assertEqual(paths["terminal_record"], materializer._FIXED_PATHS["terminal_record_path"])
        self.assertTrue(paths["caller_override_forbidden"])
        self.assertEqual(self.activation["runtime_identity"], dict(materializer._RUNTIME_IDENTITY))

    def test_rights_are_one_materialization_only_and_exclude_all_science(self):
        rights = self.activation["future_one_shot_rights"]
        self.assertEqual(rights["population_id"], materializer.H24_POPULATION_ID)
        self.assertEqual(rights["maximum_materialization_attempts"], 1)
        self.assertTrue(rights["atomic_population_publication"])
        for name in (
            "P0_authorized", "P1_authorized", "P2_authorized",
            "scientific_evidence_authorized", "real_data_authorized",
            "H17_authorized", "locked_test_authorized", "training_authorized",
        ):
            self.assertFalse(rights[name], name)

    def test_contract_is_dormant_and_does_not_issue_runtime_authority(self):
        self.assertEqual(
            self.activation["status"],
            "contract_only_pending_external_review_no_runtime_authority",
        )
        dormancy = self.activation["current_dormancy"]
        self.assertFalse(dormancy["this_contract_grants_runtime_authority"])
        self.assertTrue(dormancy["authorization_seal_external_review_required"])
        self.assertTrue(dormancy["activation_commit_external_review_required"])
        for name in (
            "operational_capability_issuance_authorized_now",
            "claim_or_marker_creation_authorized_now",
            "numpy_bridge_authorized_now",
            "waveform_or_population_creation_authorized_now",
            "scientific_execution_authorized_now",
        ):
            self.assertFalse(dormancy[name], name)


if __name__ == "__main__":
    unittest.main()
