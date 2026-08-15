from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/h27_review4_constructor_execution_gate_once.py"


def load_module():
    spec = importlib.util.spec_from_file_location("h27_review4_constructor_execution_gate_once_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestH27Review4ConstructorExecutionGate(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_import_is_inert_and_contract_is_exact(self) -> None:
        self.assertEqual(self.module.ACK, "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE")
        self.assertEqual(self.module.REQUIRED_HEAD, "46a6bdf81a56a7a7a10524d4e55092301a452207")
        self.assertEqual(self.module.CLOSED_BUNDLE_DIGEST, "879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe")
        self.assertEqual(self.module.AUTHORITY_ID, "45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e")
        self.assertEqual((self.module.CONSTRUCTOR_BLOB, self.module.CONSTRUCTOR_SIZE, self.module.CONSTRUCTOR_SHA256), (
            "0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62", 12599,
            "0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807",
        ))

    def test_platform_ack_and_zero_arguments_fail_closed(self) -> None:
        with mock.patch.object(self.module.sys, "platform", "darwin"), mock.patch.object(self.module.sys, "argv", ["runner"]), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PermissionError):
                self.module.require_platform_ack_and_zero_arguments()
        with mock.patch.object(self.module.sys, "platform", "darwin"), mock.patch.object(self.module.sys, "argv", ["runner", "extra"]), mock.patch.dict(os.environ, {self.module.ACK: "1"}, clear=True):
            with self.assertRaises(PermissionError):
                self.module.require_platform_ack_and_zero_arguments()

    def test_canonical_runtime_inputs_are_exact_and_deterministic(self) -> None:
        fake_now = SimpleNamespace(replace=lambda microsecond: SimpleNamespace(strftime=lambda pattern: "2026-08-16T12:34:56Z"))
        fake_datetime = SimpleNamespace(now=lambda timezone: fake_now)
        with mock.patch.object(self.module.datetime, "datetime", fake_datetime), mock.patch.object(self.module.secrets, "token_hex", return_value="a" * 64):
            issued, nonce, instance, raw, digest, authority = self.module.canonical_runtime_inputs()
        payload = json.loads(raw)
        self.assertEqual((issued, nonce, authority), ("2026-08-16T12:34:56Z", "a" * 64, self.module.AUTHORITY_ID))
        self.assertEqual(tuple(payload), ("schema_version", "artifact_type", "authority_instance_id", "issuer_id", "issued_at_utc", "invocation_nonce", "canonical_destination_path", "sealed_chain_identity", "single_use", "consumed"))
        self.assertEqual(tuple(payload["sealed_chain_identity"]), tuple(self.module.SEALED_CHAIN_IDENTITY))
        self.assertEqual(payload["authority_instance_id"], instance)
        self.assertEqual(hashlib.sha256(raw).hexdigest(), digest)

    def test_exact_normative_target_graph_has_112_unique_identities(self) -> None:
        def blob_bytes(path: Path, required_mode=None):
            relative = path.relative_to(self.module.TARGET).as_posix()
            result = subprocess.run(["git", "cat-file", "blob", f"{self.module.REQUIRED_HEAD}:{relative}"], cwd=ROOT, check=True, stdout=subprocess.PIPE)
            return result.stdout

        def git_read(*args, allowed=(0,)):
            result = subprocess.run(["git", "--no-replace-objects", "-C", str(ROOT), *args], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            self.assertIn(result.returncode, allowed)
            return result

        with mock.patch.object(self.module, "stable_regular_bytes", side_effect=blob_bytes), mock.patch.object(self.module, "git_read", side_effect=git_read):
            identities = self.module.verify_one_hundred_twelve_target_identities()
        self.assertEqual(len(identities), 112)
        self.assertEqual(len({item[0] for item in identities}), 112)
        self.assertNotIn(self.module.NON_NORMATIVE_IDENTITY_PATH, {item[0] for item in identities})

    def test_registry_create_is_relative_to_same_parent_fd_and_fsynced(self) -> None:
        context = {
            "execution_authority_artifact_id": self.module.AUTHORITY_ID,
            "authority_instance_id": "b" * 64,
            "invocation_nonce": "c" * 64,
            "issued_at_utc": "2026-08-16T12:34:56Z",
            "canonical_sha256": "d" * 64,
        }
        parent_fd, registry_fd = 41, 42
        descriptor = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_dev=7, st_ino=9)
        with mock.patch.object(self.module.os, "O_NOFOLLOW", 0x20000, create=True), \
             mock.patch.object(self.module.os, "open", return_value=registry_fd) as opened, \
             mock.patch.object(self.module.os, "fchmod", create=True), \
             mock.patch.object(self.module.os, "fstat", return_value=descriptor), \
             mock.patch.object(self.module.os, "stat", return_value=descriptor) as named_stat, \
             mock.patch.object(self.module.os, "fsync") as fsync, \
             mock.patch.object(self.module, "_write_record_once") as write_record:
            fd = self.module.open_and_reserve(context, parent_fd)
        self.assertEqual(fd, registry_fd)
        flags = self.module.os.O_WRONLY | self.module.os.O_CREAT | self.module.os.O_EXCL | 0x20000
        opened.assert_called_once_with(self.module.REGISTRY.name, flags, 0o600, dir_fd=parent_fd)
        named_stat.assert_called_once_with(self.module.REGISTRY.name, dir_fd=parent_fd, follow_symlinks=False)
        self.assertEqual(write_record.call_args.args[1]["state"], "reserved")
        fsync.assert_called_once_with(parent_fd)

    def test_consumption_record_is_distinct_and_fsynced_by_writer(self) -> None:
        context = {
            "execution_authority_artifact_id": self.module.AUTHORITY_ID, "authority_instance_id": "b" * 64,
            "invocation_nonce": "c" * 64, "issued_at_utc": "2026-08-16T12:34:56Z", "canonical_sha256": "d" * 64,
        }
        with mock.patch.object(self.module, "_write_record_once") as writer:
            self.module.consume_authority(42, context)
        self.assertEqual(writer.call_args.args[0], 42)
        self.assertEqual(writer.call_args.args[1]["state"], "consumed")

    def test_execute_orders_preflight_reserve_consume_constructor_then_stop(self) -> None:
        context = {
            "control_bundle_digest": self.module.CLOSED_BUNDLE_DIGEST,
            "verified_target_identities": 112,
            "verified_authority_identities": 4,
            "verified_total_identities_before_registry": 116,
            "issued_at_utc": "2026-08-16T12:34:56Z",
            "invocation_nonce": "e" * 64,
            "authority_instance_id": "f" * 64,
            "canonical_bytes": b"canonical\n",
            "canonical_sha256": hashlib.sha256(b"canonical\n").hexdigest(),
            "execution_authority_artifact_id": self.module.AUTHORITY_ID,
            "constructor_bytes": b"frozen",
        }
        order = []
        result = SimpleNamespace(
            canonical_bytes=context["canonical_bytes"], canonical_sha256=context["canonical_sha256"],
            authority_instance_id=context["authority_instance_id"], persistent_reservation_performed=False,
            destination_path=None, authority_instance_artifact_exists=False, authority_instance_exists=False,
            filesystem_effects=0, science_invocations=0,
        )
        with mock.patch.object(self.module, "preflight", side_effect=lambda: order.append("preflight") or context), \
             mock.patch.object(self.module, "open_verified_registry_parent", side_effect=lambda: order.append("parent") or 41), \
             mock.patch.object(self.module, "open_and_reserve", side_effect=lambda value, parent: order.append("reserve") or 42), \
             mock.patch.object(self.module, "consume_authority", side_effect=lambda fd, value: order.append("consume")), \
             mock.patch.object(self.module, "invoke_constructor", side_effect=lambda value: order.append("constructor") or result), \
             mock.patch.object(self.module.os, "close") as close:
            report = self.module.execute()
        self.assertEqual(order, ["preflight", "parent", "reserve", "consume", "constructor"])
        self.assertEqual([call.args[0] for call in close.call_args_list], [42, 41])
        self.assertEqual(report["status"], "H27_REVIEW4_CONSTRUCTOR_EXECUTION_GATE_TERMINAL_SUCCESS_STOP")
        self.assertTrue(report["authority_consumed"] and report["constructor_invoked_once"])
        self.assertFalse(report["destination_observed"] or report["materializer_invoked"] or report["science_or_locked_test"] or report["retry_authorized"])

    def test_preflight_failure_never_opens_registry(self) -> None:
        with mock.patch.object(self.module, "preflight", side_effect=PermissionError("drift")), mock.patch.object(self.module, "open_and_reserve") as reserve:
            with self.assertRaises(PermissionError):
                self.module.execute()
        reserve.assert_not_called()

    def test_post_consumption_constructor_failure_is_terminal_no_retry(self) -> None:
        context = {
            "control_bundle_digest": self.module.CLOSED_BUNDLE_DIGEST,
            "verified_target_identities": 112, "verified_authority_identities": 4,
            "verified_total_identities_before_registry": 116, "issued_at_utc": "2026-08-16T12:34:56Z",
            "invocation_nonce": "1" * 64, "authority_instance_id": "2" * 64,
            "canonical_bytes": b"x", "canonical_sha256": hashlib.sha256(b"x").hexdigest(),
            "execution_authority_artifact_id": self.module.AUTHORITY_ID,
            "constructor_bytes": b"frozen",
        }
        order = []
        with mock.patch.object(self.module, "preflight", return_value=context), \
             mock.patch.object(self.module, "open_verified_registry_parent", return_value=41), \
             mock.patch.object(self.module, "open_and_reserve", side_effect=lambda value, parent: order.append("reserve") or 42), \
             mock.patch.object(self.module, "consume_authority", side_effect=lambda fd, value: order.append("consume")), \
             mock.patch.object(self.module, "invoke_constructor", side_effect=lambda value: order.append("constructor") or (_ for _ in ()).throw(RuntimeError("terminal"))) as invoke, \
             mock.patch.object(self.module.os, "close"):
            with self.assertRaises(RuntimeError):
                self.module.execute()
        self.assertEqual(order, ["reserve", "consume", "constructor"])
        self.assertEqual(invoke.call_count, 1)

    def test_constructor_executes_frozen_bytes_after_live_path_changes(self) -> None:
        frozen = b"VALUE = 'frozen'\n"
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            live = target / "constructor.py"
            live.write_bytes(b"VALUE = 'mutated'\n")
            with mock.patch.object(self.module, "TARGET", target), \
                 mock.patch.object(self.module, "CONSTRUCTOR_PATH", "constructor.py"), \
                 mock.patch.object(self.module, "CONSTRUCTOR_BLOB", self.module.git_blob(frozen)), \
                 mock.patch.object(self.module, "CONSTRUCTOR_SIZE", len(frozen)), \
                 mock.patch.object(self.module, "CONSTRUCTOR_SHA256", hashlib.sha256(frozen).hexdigest()):
                loaded = self.module.load_constructor_from_frozen_bytes(frozen)
            self.assertEqual(loaded.VALUE, "frozen")
            self.assertEqual(live.read_bytes(), b"VALUE = 'mutated'\n")
            self.assertFalse((target / "__pycache__").exists())

    def test_source_has_no_materializer_or_destination_probe(self) -> None:
        source = SCRIPT.read_text(encoding="utf-8")
        self.assertNotIn("FINAL =", source)
        self.assertNotIn("STAGING =", source)
        self.assertNotIn("os.lstat(DESTINATION", source)
        self.assertNotIn("Path(DESTINATION_TEXT)", source)
        self.assertNotIn("materialize_h27", source)
        self.assertNotIn("spec_from_file_location", source)
        self.assertNotIn("exec_module", source)
        self.assertNotIn("locked_test", source.lower().replace('"science_or_locked_test"', ""))


if __name__ == "__main__":
    unittest.main()
