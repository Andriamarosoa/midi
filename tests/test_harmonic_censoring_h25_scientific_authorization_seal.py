import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h25_secondary_runtime_observer as observer
from src.polyphonic import harmonic_censoring_h25_scientific_capability as capability


ROOT = Path(__file__).resolve().parents[1]
SEAL = ROOT / capability.AUTHORIZATION_SEAL
OBSERVER = ROOT / "src/polyphonic/harmonic_censoring_h25_secondary_runtime_observer.py"
REVIEWED_AUTHORITY_COMMIT = "496331664023d505588a1bfcf0dd4a0c3ad01e77"


def _sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _canonical(value: object) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=False,
            allow_nan=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        + b"\n"
    )


def _git(*arguments: str) -> str:
    return subprocess.run(
        ["git", *arguments],
        cwd=ROOT,
        check=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    ).stdout.strip()


class H25ScientificAuthorizationSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.seal = json.loads(SEAL.read_text(encoding="utf-8"))
        cls.contract_raw = (ROOT / capability.CAPABILITY_CONTRACT).read_bytes()

    def test_seal_has_closed_schema_and_exact_reviewed_authority_bindings(self) -> None:
        expected_fields = {
            "schema_version", "purpose", "status", "authorized_action",
            "reviewed_authority_commit", "authority_source_blob",
            "runner_source_blob", "engine_source_blob", "recomputer_source_blob",
            "capability_contract_sha256", "population_index_sha256",
            "population_provenance_sha256", "population_receipt_sha256",
            "administrative_qualification_record_path",
            "administrative_qualification_sha256", "secondary_runtime_command",
            "secondary_runtime_timeout_seconds", "secondary_runtime_identity",
        }
        self.assertEqual(set(self.seal), expected_fields)
        self.assertEqual(self.seal["reviewed_authority_commit"], REVIEWED_AUTHORITY_COMMIT)
        expected_blobs = {
            "authority_source_blob": "src/polyphonic/harmonic_censoring_h25_scientific_capability.py",
            "runner_source_blob": "src/polyphonic/run_harmonic_censoring_h25_scientific.py",
            "engine_source_blob": "src/polyphonic/harmonic_censoring_h25_scientific_engine.py",
            "recomputer_source_blob": "src/polyphonic/harmonic_censoring_h25_recomputer.py",
        }
        for field, path in expected_blobs.items():
            self.assertEqual(
                self.seal[field],
                _git("rev-parse", f"{REVIEWED_AUTHORITY_COMMIT}:{path}"),
            )
        self.assertEqual(self.seal["capability_contract_sha256"], _sha(self.contract_raw))

    def test_seal_binds_exact_population_qualification_and_secondary_payload(self) -> None:
        contract = json.loads(self.contract_raw)
        population = contract["published_population"]
        self.assertEqual(
            self.seal["population_index_sha256"], population["index"]["raw_sha256"]
        )
        self.assertEqual(
            self.seal["population_provenance_sha256"],
            population["runtime_provenance"]["raw_sha256"],
        )
        self.assertEqual(
            self.seal["population_receipt_sha256"],
            population["receipt"]["raw_sha256"],
        )
        qualification = ROOT / self.seal["administrative_qualification_record_path"]
        self.assertEqual(_sha(qualification.read_bytes()), self.seal["administrative_qualification_sha256"])
        command = self.seal["secondary_runtime_command"]
        identity = self.seal["secondary_runtime_identity"]
        self.assertEqual(identity["command_sha256"], _sha(_canonical(command)))
        self.assertEqual(identity["observer_payload_size_bytes"], OBSERVER.stat().st_size)
        self.assertEqual(identity["observer_payload_sha256"], _sha(OBSERVER.read_bytes()))
        self.assertEqual(command[1], identity["observer_payload_path"])
        self.assertEqual(self.seal["secondary_runtime_timeout_seconds"], 120)

    def test_observer_is_dormant_before_contract_runtime_claim_numpy_or_population(self) -> None:
        self.assertFalse((ROOT / capability.ACTIVATION_RECORD).exists())
        source = OBSERVER.read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        numpy_before = sys.modules.get("numpy")
        with mock.patch.object(observer, "_validate_dormant_contract") as contract, mock.patch.object(
            observer, "_require_runtime_before_numpy"
        ) as runtime, mock.patch.object(observer, "_claim_marker") as claim, mock.patch.object(
            observer, "_load_context_after_claim"
        ) as population:
            with self.assertRaisesRegex(PermissionError, "seal and activation are absent"):
                observer.run_h25_secondary_runtime_observer(ROOT)
        contract.assert_not_called()
        runtime.assert_not_called()
        claim.assert_not_called()
        population.assert_not_called()
        self.assertIs(sys.modules.get("numpy"), numpy_before)

    def test_observer_payload_requires_true_producers_and_closed_cli(self) -> None:
        source = OBSERVER.read_text(encoding="utf-8")
        self.assertIn("_derive_recomputed_runtime_test_records(context, identity)", source)
        self.assertIn("observed_test_records=records", source)
        self.assertIn("H25_EXACT_EVIDENCE_PRODUCER_REGISTRY[test.test_id]", source)
        self.assertNotIn('"status": "PASS"', source)
        self.assertEqual(tuple(observer.__all__), ("run_h25_secondary_runtime_observer",))
        with self.assertRaisesRegex(PermissionError, "accepts no arguments"):
            observer._main([str(OBSERVER), "unexpected"])

    def test_current_tree_remains_pre_activation_and_zero_science(self) -> None:
        contract = json.loads(self.contract_raw)
        self.assertTrue(SEAL.is_file())
        self.assertFalse((ROOT / capability.ACTIVATION_RECORD).exists())
        self.assertIsNone(os.environ.get(capability.AUTHORIZATION_COMMIT_ENV))
        self.assertIsNone(os.environ.get(capability.AUTHORIZATION_SEAL_SHA256_ENV))
        self.assertFalse(contract["scope"]["scientific_capability_emitted_now"])
        self.assertFalse(contract["scope"]["scientific_claim_created_now"])
        self.assertEqual(contract["scope"]["P0_P1_P2_executed_counts"], [0, 0, 0])
        for name in (
            "claim_path", "staging_directory", "success_directory",
            "terminal_path", "forensic_terminal_path",
        ):
            self.assertFalse((ROOT / contract["one_shot_execution"][name]).exists())


if __name__ == "__main__":
    unittest.main()
