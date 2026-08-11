import os
from pathlib import Path
import tempfile
from unittest import mock
import unittest

from src.polyphonic import harmonic_censoring_h26_runtime_qualification_operational_activation as activation
from src.polyphonic import run_h26_runtime_qualification_operational_activation_issuance as runner


def candidate():
    fields, _, fixed = activation._activation_rules()
    value = dict(fixed)
    value.update(
        activation_id="placeholder",
        activation_contract_commit=activation.ACTIVATION_CONTRACT_COMMIT,
        activation_contract_raw_sha256=activation.ACTIVATION_CONTRACT_RAW_SHA256,
        administrative_root=runner.ADMINISTRATIVE_ROOT,
        issued_at=runner.ISSUED_AT,
        issuer_identity=runner.ISSUER_IDENTITY,
    )
    assert set(value) == set(fields)
    value["activation_id"] = activation.derive_runtime_qualification_operational_activation_id(value)
    return value


class OperationalEntrypointTests(unittest.TestCase):
    def test_entrypoint_contract_is_exact(self):
        value = runner._load_entrypoint_contract()
        self.assertEqual(value["administrative_root"], runner.ADMINISTRATIVE_ROOT)
        self.assertEqual(value["issuer_identity"], runner.ISSUER_IDENTITY)
        self.assertFalse(value["activation_created"])
        self.assertFalse(value["locked_test_used"])

    def test_strict_json_rejects_duplicate_float_constant_and_noncanonical_bytes(self):
        for raw in (
            b'{"a":1,"a":1}\n',
            b'{"a":1.0}\n',
            b'{"a":NaN}\n',
            b'{"a":1}\r\n',
        ):
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                runner._strict_json_object(raw)

    def test_boundary_fails_before_request_processing(self):
        with mock.patch.object(runner.os, "name", "nt"):
            with self.assertRaises(RuntimeError):
                runner.issue_h26_runtime_activation_once(b"not-json")

    def test_exact_values_and_canonical_bytes_precede_adapter(self):
        value = candidate()
        raw = activation._runtime.canonical_json_bytes(value)
        receipt = mock.Mock(
            activation_id=value["activation_id"],
            activation_raw_sha256="a" * 64,
            final_path=f"{runner.ADMINISTRATIVE_ROOT}/activation/activation.json",
            published=True,
        )
        with mock.patch.object(runner, "_require_execution_boundary", return_value="a" * 40), mock.patch.object(runner, "H26PosixIssuanceFilesystemAdapter") as adapter_type, mock.patch.object(runner, "publish_prevalidated_activation_with_adapter", return_value=receipt) as publish:
            result = runner.issue_h26_runtime_activation_once(raw)
        self.assertIs(result, receipt)
        adapter_type.assert_called_once_with(runner.ADMINISTRATIVE_ROOT)
        publish.assert_called_once()

        for field, replacement in (
            ("administrative_root", "/Users/amcarene/other"),
            ("issuer_identity", "other"),
            ("issued_at", "2026-08-12T12:00:01Z"),
        ):
            bad = candidate()
            bad[field] = replacement
            bad["activation_id"] = activation.derive_runtime_qualification_operational_activation_id(bad)
            raw_bad = activation._runtime.canonical_json_bytes(bad)
            with self.subTest(field=field), mock.patch.object(runner, "_require_execution_boundary", return_value="a" * 40), mock.patch.object(runner, "H26PosixIssuanceFilesystemAdapter") as adapter_type, self.assertRaises(ValueError):
                runner.issue_h26_runtime_activation_once(raw_bad)
            adapter_type.assert_not_called()

    @unittest.skipUnless(
        os.name == "posix" and hasattr(os, "uname") and os.uname().sysname == "Darwin",
        "Darwin-only publication primitive",
    )
    def test_real_darwin_adapter_publishes_once_without_replace(self):
        from src.polyphonic.harmonic_censoring_h26_runtime_qualification_operational_activation_issuer import (
            H26ActivationIssuanceReceipt,
            H26PosixIssuanceFilesystemAdapter,
            publish_prevalidated_activation_with_adapter,
        )
        from src.polyphonic.harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner import H26ActivationIssuancePlan

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / "activation").mkdir()
            plan = H26ActivationIssuancePlan(
                "test-id",
                "a" * 64,
                b"{}\n",
                str(root),
                str(root / "activation" / "activation.json"),
                str(root / "activation" / ".activation.json.staging"),
                "test",
                runner.ISSUED_AT,
            )
            adapter = H26PosixIssuanceFilesystemAdapter(str(root))
            receipt = publish_prevalidated_activation_with_adapter(plan, adapter)
            self.assertIsInstance(receipt, H26ActivationIssuanceReceipt)
            self.assertEqual((root / "activation" / "activation.json").read_bytes(), b"{}\n")
            with self.assertRaises(FileExistsError):
                publish_prevalidated_activation_with_adapter(plan, adapter)


if __name__ == "__main__":
    unittest.main()
