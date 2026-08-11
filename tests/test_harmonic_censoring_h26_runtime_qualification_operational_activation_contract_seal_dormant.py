from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import (
    harmonic_censoring_h26_runtime_qualification_operational_activation_contract_seal
    as seal_loader,
)


class DormantRuntimeQualificationOperationalActivationContractSealTests(unittest.TestCase):
    @staticmethod
    def seal_path() -> Path:
        return (
            Path(seal_loader.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_runtime_qualification_operational_activation_contract_external_seal.json"
        )

    @staticmethod
    def contract_path() -> Path:
        return (
            Path(seal_loader.__file__).resolve().parents[2]
            / "configs"
            / "harmonic_censoring_h26_runtime_qualification_operational_activation_contract.json"
        )

    def test_exact_external_seal_and_contract_are_accepted(self) -> None:
        result = seal_loader.load_runtime_qualification_operational_activation_contract_external_seal()
        self.assertEqual(
            result["activation_contract_raw_sha256"],
            seal_loader.ACTIVATION_CONTRACT_RAW_SHA256,
        )
        self.assertFalse(result["creation_authorized_now"])
        with self.assertRaises(TypeError):
            result["creation_authorized_now"] = True

    def test_modified_external_seal_blob_is_rejected_before_parsing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "seal.json"
            changed.write_bytes(self.seal_path().read_bytes() + b" ")
            with mock.patch.object(seal_loader, "_strict_json") as parser:
                with self.assertRaisesRegex(ValueError, "seal Git blob mismatch"):
                    seal_loader.load_runtime_qualification_operational_activation_contract_external_seal(
                        seal_path=changed
                    )
            parser.assert_not_called()

    def test_exact_seal_schema_status_state_self_sha_and_creation_are_required(self) -> None:
        mutations = (
            ("seal_schema_identity", "WRONG"),
            ("seal_schema_version", True),
            ("status", "WRONG"),
            ("seal_contains_own_raw_sha256", True),
            ("activation_contract_contains_own_raw_sha256", True),
            ("creation_authorized_now", True),
        )
        source = json.loads(self.seal_path().read_text(encoding="utf-8"))
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (field, value) in enumerate(mutations):
                with self.subTest(field=field):
                    changed_payload = dict(source)
                    changed_payload[field] = value
                    changed = root / f"seal-{index}.json"
                    changed.write_text(json.dumps(changed_payload), encoding="utf-8")
                    with mock.patch.object(
                        seal_loader,
                        "_git_blob_sha",
                        side_effect=(
                            seal_loader.EXTERNAL_SEAL_GIT_BLOB_SHA,
                            seal_loader.ACTIVATION_CONTRACT_GIT_BLOB_SHA,
                        ),
                    ):
                        with self.assertRaises(ValueError):
                            seal_loader.load_runtime_qualification_operational_activation_contract_external_seal(
                                seal_path=changed
                            )

        changed_state = json.loads(self.seal_path().read_text(encoding="utf-8"))
        changed_state["current_state"]["observer_invocation_count"] = 1
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "seal-state.json"
            changed.write_text(json.dumps(changed_state), encoding="utf-8")
            with mock.patch.object(
                seal_loader,
                "_git_blob_sha",
                side_effect=(
                    seal_loader.EXTERNAL_SEAL_GIT_BLOB_SHA,
                    seal_loader.ACTIVATION_CONTRACT_GIT_BLOB_SHA,
                ),
            ):
                with self.assertRaisesRegex(ValueError, "seal content mismatch"):
                    seal_loader.load_runtime_qualification_operational_activation_contract_external_seal(
                        seal_path=changed
                    )

    def test_false_contract_blob_sha_and_length_bindings_are_rejected(self) -> None:
        source = json.loads(self.seal_path().read_text(encoding="utf-8"))
        mutations = (
            ("activation_contract_git_blob_sha", "0" * 40),
            ("activation_contract_raw_sha256", "0" * 64),
            ("activation_contract_git_blob_byte_length", 16049),
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for index, (field, value) in enumerate(mutations):
                with self.subTest(field=field):
                    changed_payload = dict(source)
                    changed_payload[field] = value
                    changed = root / f"seal-binding-{index}.json"
                    changed.write_text(json.dumps(changed_payload), encoding="utf-8")
                    with mock.patch.object(
                        seal_loader,
                        "_git_blob_sha",
                        side_effect=(
                            seal_loader.EXTERNAL_SEAL_GIT_BLOB_SHA,
                            seal_loader.ACTIVATION_CONTRACT_GIT_BLOB_SHA,
                        ),
                    ):
                        with self.assertRaisesRegex(ValueError, "seal content mismatch"):
                            seal_loader.load_runtime_qualification_operational_activation_contract_external_seal(
                                seal_path=changed
                            )

    def test_changed_contract_bytes_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "contract.json"
            changed.write_bytes(self.contract_path().read_bytes() + b" ")
            with self.assertRaisesRegex(ValueError, "contract Git blob mismatch"):
                seal_loader.load_runtime_qualification_operational_activation_contract_external_seal(
                    contract_path=changed
                )

    def test_crlf_checkout_converges_to_reviewed_git_bytes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "contract.json"
            changed.write_bytes(self.contract_path().read_bytes().replace(b"\n", b"\r\n"))
            result = seal_loader.load_runtime_qualification_operational_activation_contract_external_seal(
                contract_path=changed
            )
        self.assertEqual(
            result["activation_contract_git_blob_byte_length"],
            seal_loader.ACTIVATION_CONTRACT_GIT_BLOB_BYTE_LENGTH,
        )

    def test_public_binding_mutation_is_rejected(self) -> None:
        original = seal_loader.ACTIVATION_CONTRACT_RAW_SHA256
        try:
            seal_loader.ACTIVATION_CONTRACT_RAW_SHA256 = "0" * 64
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                seal_loader.load_runtime_qualification_operational_activation_contract_external_seal()
        finally:
            seal_loader.ACTIVATION_CONTRACT_RAW_SHA256 = original

    def test_loader_creates_no_files_and_exposes_no_operational_api(self) -> None:
        with mock.patch.object(Path, "mkdir") as mkdir, mock.patch.object(
            Path, "write_bytes"
        ) as write_bytes, mock.patch.object(Path, "touch") as touch, mock.patch.object(
            Path, "rename"
        ) as rename:
            seal_loader.load_runtime_qualification_operational_activation_contract_external_seal()
        mkdir.assert_not_called()
        write_bytes.assert_not_called()
        touch.assert_not_called()
        rename.assert_not_called()

        public = set(seal_loader.__all__)
        for forbidden in ("issue", "capability", "activate", "authority_path", "create"):
            self.assertFalse(any(forbidden in name.lower() for name in public))
        source = Path(seal_loader.__file__).read_text(encoding="utf-8")
        for forbidden in (
            "import numpy",
            "otool",
            "observe_primary_runtime",
            "materializer",
            ".mkdir(",
            ".write_bytes(",
            ".rename(",
        ):
            self.assertNotIn(forbidden, source)


if __name__ == "__main__":
    unittest.main()
