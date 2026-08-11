from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h24_scientific_capability as capability


ROOT = Path(__file__).resolve().parents[1]
SEAL_PATH = ROOT / capability.H24_SCIENTIFIC_SEAL_RELATIVE_PATH


class H24ScientificExecutionAuthorizationSealTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = SEAL_PATH.read_bytes()
        cls.payload = json.loads(cls.raw)
        cls.seal = capability._validate_seal(
            cls.payload, hashlib.sha256(cls.raw).hexdigest()
        )

    def test_seal_is_canonical_lf_and_schema_is_closed(self) -> None:
        self.assertNotIn(b"\r", self.raw)
        self.assertTrue(self.raw.endswith(b"\n"))
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(
            self.payload["purpose"],
            "harmonic_censoring_h24_scientific_execution_authorization_seal",
        )
        self.assertEqual(
            self.payload["external_review"],
            {
                "verdict": "APPROVED",
                "implementation_reviewed": True,
                "seal_commit_review_required": True,
            },
        )

    def test_seal_binds_exact_reviewed_implementation_topology(self) -> None:
        bindings = self.payload["bindings"]
        self.assertEqual(
            bindings["implementation_commit"],
            "22bf87831838fa0c0467ae1f54be788c91d47951",
        )
        actual = tuple(
            item
            for item in subprocess.check_output(
                [
                    "git",
                    "diff-tree",
                    "--no-commit-id",
                    "--name-only",
                    "-r",
                    bindings["implementation_commit"],
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
            ).splitlines()
            if item
        )
        self.assertEqual(
            tuple(sorted(bindings["exact_changed_files"])), tuple(sorted(actual))
        )
        self.assertEqual(
            tuple(bindings["exact_changed_files"]),
            capability.H24_IMPLEMENTATION_EXACT_CHANGED_FILES,
        )

    def test_all_five_executable_blobs_and_both_contracts_are_exact(self) -> None:
        bindings = self.payload["bindings"]
        for path, field in (
            (capability.H24_CAPABILITY_SOURCE_RELATIVE_PATH, "capability_source_blob"),
            (capability.H24_RUNNER_SOURCE_RELATIVE_PATH, "runner_source_blob"),
            (capability.H24_PRODUCER_SOURCE_RELATIVE_PATH, "producer_source_blob"),
            (
                capability.H24_PREDECESSOR_RUNNER_SOURCE_RELATIVE_PATH,
                "predecessor_runner_source_blob",
            ),
            (
                capability.H24_PREDECESSOR_HARNESS_SOURCE_RELATIVE_PATH,
                "predecessor_harness_source_blob",
            ),
        ):
            actual = subprocess.check_output(
                [
                    "git",
                    "rev-parse",
                    f"{bindings['implementation_commit']}:{path.as_posix()}",
                ],
                cwd=ROOT,
                text=True,
                encoding="utf-8",
            ).strip()
            self.assertEqual(bindings[field], actual, path.as_posix())
        self.assertEqual(
            bindings["contract_sha256"],
            capability.H24_SCIENTIFIC_CONTRACT_RAW_SHA256,
        )
        self.assertEqual(
            bindings["contract_sha256"],
            hashlib.sha256(
                (ROOT / capability.H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH).read_bytes()
            ).hexdigest(),
        )
        self.assertEqual(
            bindings["predecessor_contract_sha256"],
            capability.H24_REVIEWED_PREDECESSOR_CONTRACT_RAW_SHA256,
        )

    def test_runtime_and_one_shot_topology_are_exact(self) -> None:
        self.assertEqual(
            tuple(sorted((name, str(value)) for name, value in self.payload["runtime_identity"].items())),
            self.seal.runtime_identity,
        )
        paths = {
            "claim": (ROOT / self.seal.claim_path).resolve(),
            "staging": (ROOT / self.seal.staging_directory).resolve(),
            "success": (ROOT / self.seal.success_directory).resolve(),
            "transcript": (ROOT / self.seal.transcript_path).resolve(),
            "transcript_staging": (ROOT / self.seal.transcript_staging_path).resolve(),
            "evidence": (ROOT / self.seal.evidence_directory).resolve(),
            "terminal": (ROOT / self.seal.terminal_path).resolve(),
        }
        contract = json.loads(
            (ROOT / capability.H24_SCIENTIFIC_CONTRACT_RELATIVE_PATH).read_bytes()
        )
        capability._validate_scientific_path_topology(
            ROOT, paths, contract["published_population_binding"]
        )

    def test_activation_remains_absent_and_public_issuer_remains_dormant(self) -> None:
        self.assertFalse(
            (ROOT / capability.H24_SCIENTIFIC_ACTIVATION_RELATIVE_PATH).exists()
        )
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(capability.H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV, None)
            with self.assertRaisesRegex(PermissionError, "no OS-bound activation"):
                capability.issue_h24_scientific_execution_capability(ROOT)


if __name__ == "__main__":
    unittest.main()
