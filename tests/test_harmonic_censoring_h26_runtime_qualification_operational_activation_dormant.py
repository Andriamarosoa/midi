from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path
import unittest
from unittest import mock

from src.polyphonic import (
    harmonic_censoring_h26_runtime_qualification_operational_activation
    as activation,
)
from src.polyphonic import (
    harmonic_censoring_h26_runtime_qualification_operational_activation_contract_seal
    as seal_loader,
)


class DormantRuntimeQualificationOperationalActivationTests(unittest.TestCase):
    @staticmethod
    def valid_activation() -> dict[str, object]:
        fields, _, fixed = activation._activation_rules()
        value: dict[str, object] = dict(fixed)
        value.update(
            activation_id="placeholder",
            activation_contract_commit=activation.ACTIVATION_CONTRACT_COMMIT,
            activation_contract_raw_sha256=activation.ACTIVATION_CONTRACT_RAW_SHA256,
            administrative_root="/var/tmp/h26-runtime-qualification",
            issued_at="",
            issuer_identity="",
        )
        if set(value) != set(fields):
            raise AssertionError("test fixture does not cover the exact activation keyset")
        value["activation_id"] = (
            activation.derive_runtime_qualification_operational_activation_id(value)
        )
        return value

    def test_valid_artificial_activation_is_accepted_and_immutable(self) -> None:
        value = self.valid_activation()
        result = activation.validate_artificial_runtime_qualification_operational_activation(value)
        self.assertEqual(result.activation_id, value["activation_id"])
        self.assertTrue(result.canonical_bytes.endswith(b"\n"))
        self.assertEqual(len(result.raw_sha256), 64)
        with self.assertRaises(FrozenInstanceError):
            result.raw_sha256 = "0" * 64

    def test_missing_extra_and_wrong_type_are_rejected(self) -> None:
        missing = self.valid_activation()
        missing.pop("issuer_identity")
        extra = self.valid_activation()
        extra["extra"] = "forbidden"
        wrong_type = self.valid_activation()
        wrong_type["maximum_authorities"] = True
        for value in (missing, extra, wrong_type):
            with self.subTest(keys=tuple(value)), self.assertRaises(ValueError):
                activation.validate_artificial_runtime_qualification_operational_activation(value)

    def test_wrong_fixed_value_contract_commit_and_raw_sha_are_rejected(self) -> None:
        mutations = (
            ("retry_allowed", True),
            ("activation_contract_commit", "0" * 40),
            ("activation_contract_raw_sha256", "0" * 64),
        )
        for field, changed in mutations:
            with self.subTest(field=field):
                value = self.valid_activation()
                value[field] = changed
                value["activation_id"] = (
                    activation.derive_runtime_qualification_operational_activation_id(value)
                )
                with self.assertRaises(ValueError):
                    activation.validate_artificial_runtime_qualification_operational_activation(value)

    def test_incorrect_caller_supplied_activation_id_is_rejected(self) -> None:
        value = self.valid_activation()
        value["activation_id"] = "h26-runtime-activation-v1-" + "0" * 64
        with self.assertRaisesRegex(ValueError, "activation_id derivation mismatch"):
            activation.validate_artificial_runtime_qualification_operational_activation(value)

    def test_id_bytes_and_sha_are_deterministic(self) -> None:
        first = self.valid_activation()
        second = dict(reversed(tuple(first.items())))
        self.assertEqual(
            activation.derive_runtime_qualification_operational_activation_id(first),
            activation.derive_runtime_qualification_operational_activation_id(second),
        )
        one = activation.validate_artificial_runtime_qualification_operational_activation(first)
        two = activation.validate_artificial_runtime_qualification_operational_activation(second)
        self.assertEqual(one.canonical_bytes, two.canonical_bytes)
        self.assertEqual(one.raw_sha256, two.raw_sha256)

    def test_invalid_posix_administrative_roots_are_rejected(self) -> None:
        invalid = (
            "",
            "/",
            "relative/path",
            "//host/path",
            "/trailing/",
            "/double//segment",
            "/dot/./segment",
            "/dotdot/../segment",
            "/nul\0segment",
        )
        for root in invalid:
            with self.subTest(root=root):
                value = self.valid_activation()
                value["administrative_root"] = root
                value["activation_id"] = (
                    activation.derive_runtime_qualification_operational_activation_id(value)
                )
                with self.assertRaisesRegex(ValueError, "administrative_root"):
                    activation.validate_artificial_runtime_qualification_operational_activation(value)

    def test_issued_at_and_issuer_identity_remain_contract_only_strings(self) -> None:
        value = self.valid_activation()
        value["issued_at"] = "not-yet-constrained"
        value["issuer_identity"] = "any future issuer semantics are separate"
        value["activation_id"] = (
            activation.derive_runtime_qualification_operational_activation_id(value)
        )
        activation.validate_artificial_runtime_qualification_operational_activation(value)

    def test_public_binding_mutation_is_rejected(self) -> None:
        original = activation.APPROVED_SEAL_LOADER_COMMIT
        try:
            activation.APPROVED_SEAL_LOADER_COMMIT = "0" * 40
            with self.assertRaisesRegex(ValueError, "binding mismatch"):
                activation.validate_artificial_runtime_qualification_operational_activation(
                    self.valid_activation()
                )
        finally:
            activation.APPROVED_SEAL_LOADER_COMMIT = original

    def test_approved_seal_loader_is_mandatory(self) -> None:
        value = self.valid_activation()
        with mock.patch.object(
            seal_loader,
            "load_runtime_qualification_operational_activation_contract_external_seal",
            wraps=seal_loader.load_runtime_qualification_operational_activation_contract_external_seal,
        ) as loader:
            activation.validate_artificial_runtime_qualification_operational_activation(value)
        self.assertGreaterEqual(loader.call_count, 1)

    def test_no_writer_issuer_capability_or_operational_filesystem_api(self) -> None:
        value = self.valid_activation()
        with mock.patch.object(Path, "mkdir") as mkdir, mock.patch.object(
            Path, "write_bytes"
        ) as write_bytes, mock.patch.object(Path, "touch") as touch, mock.patch.object(
            Path, "rename"
        ) as rename:
            activation.validate_artificial_runtime_qualification_operational_activation(value)
        mkdir.assert_not_called()
        write_bytes.assert_not_called()
        touch.assert_not_called()
        rename.assert_not_called()

        public = set(activation.__all__)
        for forbidden in ("issue", "capability", "create", "write", "path"):
            self.assertFalse(any(forbidden in name.lower() for name in public))
        source = Path(activation.__file__).read_text(encoding="utf-8")
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
