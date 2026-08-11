from __future__ import annotations

import dataclasses
import tempfile
import unittest
from pathlib import Path

from src.polyphonic import (
    harmonic_censoring_h26_materialization_authority_contract_seal as seal,
)


class H26MaterializationAuthorityContractSealDormantTest(unittest.TestCase):
    def setUp(self) -> None:
        self.root = Path(seal.__file__).resolve().parents[2]
        self.seal_path = (
            self.root
            / "configs"
            / "harmonic_censoring_h26_population_materialization_authority_contract_external_seal.json"
        )
        self.contract_path = (
            self.root
            / "configs"
            / "harmonic_censoring_h26_population_materialization_authority_contract.json"
        )
        self.proof_path = (
            self.root
            / "src"
            / "polyphonic"
            / "harmonic_censoring_h26_materialization_runtime_execution_proof.py"
        )

    def test_exact_seal_loads_and_is_immutable(self) -> None:
        payload = seal.load_materialization_authority_contract_external_seal()
        self.assertEqual(
            payload["corrected_materialization_authority_contract_raw_sha256"],
            seal.CORRECTED_CONTRACT_RAW_SHA256,
        )
        self.assertEqual(
            payload[
                "corrected_materialization_authority_contract_git_blob_byte_length"
            ],
            19310,
        )
        self.assertFalse(any(
            value
            for value in payload["authorization_state"].values()
            if value is not None
        ))
        with self.assertRaises(TypeError):
            payload["status"] = "changed"  # type: ignore[index]

    def test_modified_seal_schema_status_and_state_are_rejected(self) -> None:
        raw = self.seal_path.read_bytes()
        mutations = (
            raw + b" ",
            raw.replace(b'"schema_version": 1', b'"schema_version": 2', 1),
            raw.replace(
                b"DECLARATIVE_EXTERNAL_SEAL_ONLY_NO_MATERIALIZATION_AUTHORITY",
                b"DECLARATIVE_EXTERNAL_SEAL_ONLY_MATERIALIZATION_AUTHORITY",
                1,
            ),
            raw.replace(
                b'"materialization_authority_exists": false',
                b'"materialization_authority_exists": true',
                1,
            ),
        )
        with tempfile.TemporaryDirectory() as directory:
            for index, mutation in enumerate(mutations):
                with self.subTest(index=index):
                    altered = Path(directory) / f"seal-{index}.json"
                    altered.write_bytes(mutation)
                    with self.assertRaisesRegex(ValueError, "Git blob mismatch"):
                        seal.load_materialization_authority_contract_external_seal(
                            altered
                        )

    def test_false_public_seal_blob_binding_is_rejected(self) -> None:
        original = seal.EXTERNAL_SEAL_GIT_BLOB_SHA
        try:
            seal.EXTERNAL_SEAL_GIT_BLOB_SHA = "0" * 40
            with self.assertRaisesRegex(ValueError, "seal Git blob binding mismatch"):
                seal.load_materialization_authority_contract_external_seal()
        finally:
            seal.EXTERNAL_SEAL_GIT_BLOB_SHA = original

    def test_altered_contract_blob_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / "contract.json"
            altered.write_bytes(self.contract_path.read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "contract Git blob mismatch"):
                seal.load_materialization_authority_contract_external_seal(
                    corrected_contract_path=altered
                )

    def test_false_raw_sha_and_length_bindings_are_rejected(self) -> None:
        cases = (
            ("CORRECTED_CONTRACT_RAW_SHA256", "0" * 64, "raw SHA256 binding"),
            ("CORRECTED_CONTRACT_BYTE_LENGTH", 19311, "byte length binding"),
        )
        for name, replacement, message in cases:
            with self.subTest(name=name):
                original = getattr(seal, name)
                try:
                    setattr(seal, name, replacement)
                    with self.assertRaisesRegex(ValueError, message):
                        seal.load_materialization_authority_contract_external_seal()
                finally:
                    setattr(seal, name, original)

    def test_lf_and_crlf_contracts_converge_to_exact_git_bytes(self) -> None:
        lf = self.contract_path.read_bytes().replace(b"\r\n", b"\n")
        crlf = lf.replace(b"\n", b"\r\n")
        with tempfile.TemporaryDirectory() as directory:
            lf_path = Path(directory) / "contract-lf.json"
            crlf_path = Path(directory) / "contract-crlf.json"
            lf_path.write_bytes(lf)
            crlf_path.write_bytes(crlf)
            self.assertEqual(
                seal.canonical_corrected_materialization_authority_contract_bytes(
                    lf_path
                ),
                seal.canonical_corrected_materialization_authority_contract_bytes(
                    crlf_path
                ),
            )
            self.assertEqual(
                seal.canonical_corrected_materialization_authority_contract_raw_sha256(
                    crlf_path
                ),
                seal.CORRECTED_CONTRACT_RAW_SHA256,
            )

    def test_false_proof_validator_blob_is_rejected(self) -> None:
        original = seal.APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA
        try:
            seal.APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA = "0" * 40
            with self.assertRaisesRegex(
                ValueError, "proof-validator module Git blob binding mismatch"
            ):
                seal.load_materialization_authority_contract_external_seal()
        finally:
            seal.APPROVED_PROOF_VALIDATOR_MODULE_GIT_BLOB_SHA = original

    def test_altered_proof_validator_file_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            altered = Path(directory) / self.proof_path.name
            altered.write_bytes(self.proof_path.read_bytes() + b"\n")
            with self.assertRaisesRegex(
                ValueError, "proof-validator module Git blob mismatch"
            ):
                seal.load_materialization_authority_contract_external_seal(
                    proof_validator_path=altered
                )

    def test_loader_creates_no_files_and_exposes_no_operational_builder(self) -> None:
        forbidden = (
            "build_authority",
            "issue_authority",
            "create_claim",
            "create_destination",
            "observe_primary_runtime",
            "materialize",
        )
        with tempfile.TemporaryDirectory() as directory:
            before = tuple(Path(directory).iterdir())
            seal.load_materialization_authority_contract_external_seal()
            after = tuple(Path(directory).iterdir())
        self.assertEqual(before, after)
        for name in forbidden:
            self.assertFalse(hasattr(seal, name))
        source = Path(seal.__file__).read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("harmonic_censoring_h26_materializer", source)
        self.assertFalse(dataclasses.is_dataclass(seal))


if __name__ == "__main__":
    unittest.main()
