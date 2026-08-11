from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h24_scientific_capability as capability


ROOT = Path(__file__).resolve().parents[1]
ACTIVATION_PATH = ROOT / capability.H24_SCIENTIFIC_ACTIVATION_RELATIVE_PATH
SEAL_PATH = ROOT / capability.H24_SCIENTIFIC_SEAL_RELATIVE_PATH


class H24ScientificExecutionActivationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = ACTIVATION_PATH.read_bytes()
        cls.payload = json.loads(cls.raw)
        cls.activation = capability._validate_activation(
            cls.payload, hashlib.sha256(cls.raw).hexdigest()
        )
        cls.seal_raw = SEAL_PATH.read_bytes()
        cls.seal_payload = json.loads(cls.seal_raw)
        cls.seal = capability._validate_seal(
            cls.seal_payload, hashlib.sha256(cls.seal_raw).hexdigest()
        )

    def test_activation_is_canonical_lf_and_requires_commit_review(self) -> None:
        self.assertNotIn(b"\r", self.raw)
        self.assertTrue(self.raw.endswith(b"\n"))
        self.assertEqual(self.payload["schema_version"], 1)
        self.assertEqual(
            self.payload["external_review"],
            {"verdict": "APPROVED", "activation_commit_review_required": True},
        )

    def test_activation_binds_exact_approved_seal_bytes(self) -> None:
        self.assertEqual(
            self.activation.seal_sha256, hashlib.sha256(self.seal_raw).hexdigest()
        )
        self.assertEqual(
            self.activation.seal_sha256,
            "818e53cd510bdd5b055372ad213e1a76d83af2d74adee7d158626b3f85346c61",
        )
        self.assertEqual(
            self.activation.seal_path, capability.H24_SCIENTIFIC_SEAL_RELATIVE_PATH
        )

    def test_activation_and_seal_bindings_are_identical(self) -> None:
        fields = (
            "implementation_commit",
            "capability_source_blob",
            "runner_source_blob",
            "producer_source_blob",
            "predecessor_runner_source_blob",
            "predecessor_harness_source_blob",
            "predecessor_contract_sha256",
            "contract_sha256",
        )
        for field in fields:
            self.assertEqual(
                getattr(self.activation, field), getattr(self.seal, field), field
            )

    def test_activation_file_alone_cannot_issue_capability(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=False):
            os.environ.pop(capability.H24_SCIENTIFIC_ACTIVATION_COMMIT_ENV, None)
            with self.assertRaisesRegex(PermissionError, "no OS-bound activation"):
                capability.issue_h24_scientific_execution_capability(ROOT)


if __name__ == "__main__":
    unittest.main()
