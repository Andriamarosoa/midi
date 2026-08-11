from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract_seal as loader

class DormantIssuanceContractSealTests(unittest.TestCase):
    @staticmethod
    def root() -> Path:
        return Path(loader.__file__).resolve().parents[2]

    def test_exact_bytes_are_accepted_immutably(self) -> None:
        result = loader.load_runtime_qualification_operational_activation_issuance_contract_external_seal()
        self.assertFalse(result["creation_authorized_now"])
        with self.assertRaises(TypeError):
            result["creation_authorized_now"] = True

    def test_seal_mutation_is_rejected_before_parsing(self) -> None:
        source = self.root() / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract_external_seal.json"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "seal.json"
            changed.write_bytes(source.read_bytes() + b" ")
            with mock.patch.object(loader, "_strict_json") as parser:
                with self.assertRaisesRegex(ValueError, "seal Git blob mismatch"):
                    loader.load_runtime_qualification_operational_activation_issuance_contract_external_seal(seal_path=changed)
            parser.assert_not_called()

    def test_exact_schema_state_self_sha_and_creation_are_required(self) -> None:
        source_path = self.root() / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract_external_seal.json"
        source = json.loads(source_path.read_text(encoding="utf-8"))
        mutations = (("seal_schema_version", True), ("status", "WRONG"), ("seal_contains_own_raw_sha256", True), ("issuance_contract_contains_own_raw_sha256", True), ("creation_authorized_now", True))
        with tempfile.TemporaryDirectory() as directory:
            for index, (field, value) in enumerate(mutations):
                payload = dict(source); payload[field] = value
                changed = Path(directory) / f"seal-{index}.json"
                changed.write_text(json.dumps(payload), encoding="utf-8")
                with mock.patch.object(loader, "_git_blob_sha", side_effect=(loader.EXTERNAL_SEAL_GIT_BLOB_SHA, loader.ISSUANCE_CONTRACT_GIT_BLOB_SHA)):
                    with self.assertRaises(ValueError):
                        loader.load_runtime_qualification_operational_activation_issuance_contract_external_seal(seal_path=changed)

    def test_contract_mutation_public_binding_and_crlf(self) -> None:
        contract = self.root() / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_contract.json"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "contract.json"
            changed.write_bytes(contract.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "contract Git blob mismatch"):
                loader.load_runtime_qualification_operational_activation_issuance_contract_external_seal(contract_path=changed)
            changed.write_bytes(contract.read_bytes().replace(b"\n", b"\r\n"))
            loader.load_runtime_qualification_operational_activation_issuance_contract_external_seal(contract_path=changed)
        original = loader.ISSUANCE_CONTRACT_RAW_SHA256
        try:
            loader.ISSUANCE_CONTRACT_RAW_SHA256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                loader.load_runtime_qualification_operational_activation_issuance_contract_external_seal()
        finally:
            loader.ISSUANCE_CONTRACT_RAW_SHA256 = original

    def test_no_operational_api_or_writes(self) -> None:
        source = Path(loader.__file__).read_text(encoding="utf-8")
        for forbidden in ("import numpy", "observe_primary_runtime", ".write_bytes(", ".mkdir(", ".rename("):
            self.assertNotIn(forbidden, source)

if __name__ == "__main__":
    unittest.main()
