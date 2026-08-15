from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import stat
import subprocess
from types import SimpleNamespace
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/h27_review4_authority_instance_artifact_publish_once.py"


def load_module():
    spec = importlib.util.spec_from_file_location("h27_review4_authority_instance_artifact_publish_once_test", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestH27Review4AuthorityInstanceArtifactPublish(unittest.TestCase):
    def setUp(self) -> None:
        self.module = load_module()

    def test_import_is_inert_and_exact_consumed_artifact_is_frozen(self) -> None:
        raw = self.module.canonical_artifact_bytes()
        payload = json.loads(raw)
        self.assertEqual(self.module.ACK, "H27_REVIEW4_AUTHORITY_INSTANCE_ARTIFACT_PUBLISH_EXECUTE")
        self.assertEqual(self.module.REQUIRED_HEAD, "46a6bdf81a56a7a7a10524d4e55092301a452207")
        self.assertEqual(self.module.DESTINATION_TEXT, "/Users/amcarene/h27-admin/activation/h27-materialization-v1.json")
        self.assertEqual(tuple(payload), (
            "schema_version", "artifact_type", "authority_instance_id", "issuer_id",
            "issued_at_utc", "invocation_nonce", "canonical_destination_path",
            "sealed_chain_identity", "single_use", "consumed",
        ))
        self.assertEqual(payload["authority_instance_id"], "d44941a8c1c6674e5da89c40a7e3188c4e6318f7c5759ce490577d8bde81437a")
        self.assertEqual(payload["issued_at_utc"], "2026-08-16T08:36:14Z")
        self.assertEqual(payload["invocation_nonce"], "c8c7dc8162910a140bc1699b488478b8f9f343a855973453671f6cacdfcea165")
        self.assertTrue(payload["single_use"])
        self.assertFalse(payload["consumed"])
        self.assertEqual((len(raw), self.module.git_blob(raw), hashlib.sha256(raw).hexdigest()), (
            882, "dc85ee260763f9f9e65bbafbd776bf8611a67d9c",
            "89d03ce3ea8f31a253b4e245e0357236e20860d409c27f0779a003d058fe91d2",
        ))

    def test_platform_ack_and_zero_arguments_fail_closed(self) -> None:
        with mock.patch.object(self.module.sys, "platform", "darwin"), mock.patch.object(self.module.sys, "argv", ["runner"]), mock.patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(PermissionError):
                self.module.require_platform_ack_and_zero_arguments()
        with mock.patch.object(self.module.sys, "platform", "darwin"), mock.patch.object(self.module.sys, "argv", ["runner", "extra"]), mock.patch.dict(os.environ, {self.module.ACK: "1"}, clear=True):
            with self.assertRaises(PermissionError):
                self.module.require_platform_ack_and_zero_arguments()

    def test_exact_normative_graph_has_ninety_two_unique_identities(self) -> None:
        def blob_bytes(path: Path, required_mode=None):
            relative = path.relative_to(self.module.TARGET).as_posix()
            return subprocess.run(
                ["git", "cat-file", "blob", f"{self.module.REQUIRED_HEAD}:{relative}"],
                cwd=ROOT, check=True, stdout=subprocess.PIPE,
            ).stdout

        def git_read(*args, allowed=(0,)):
            result = subprocess.run(
                ["git", "--no-replace-objects", "-C", str(ROOT), *args],
                check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            )
            self.assertIn(result.returncode, allowed)
            return result

        with mock.patch.object(self.module, "stable_regular_bytes", side_effect=blob_bytes), mock.patch.object(self.module, "git_read", side_effect=git_read):
            identities = self.module.verify_ninety_two_target_identities()
        self.assertEqual(len(identities), 92)
        self.assertEqual(len({item[0] for item in identities}), 92)

    def test_constructor_terminal_registry_is_exact_reserved_then_consumed(self) -> None:
        raw = self.module.expected_constructor_registry_bytes()
        records = [json.loads(line) for line in raw.splitlines()]
        self.assertEqual([item["state"] for item in records], ["reserved", "consumed"])
        self.assertEqual({item["authority_instance_id"] for item in records}, {self.module.AUTHORITY_INSTANCE_ID})
        with mock.patch.object(self.module, "stable_regular_bytes_at", return_value=raw) as stable:
            self.module.verify_constructor_terminal(41)
        stable.assert_called_once_with(41, self.module.CONSTRUCTOR_REGISTRY.name, required_mode=0o600)

    def test_consumption_is_exclusive_relative_and_fsynced(self) -> None:
        descriptor = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_dev=7, st_ino=9)
        with mock.patch.object(self.module.os, "O_NOFOLLOW", 0x20000, create=True), \
             mock.patch.object(self.module.os, "open", return_value=42) as opened, \
             mock.patch.object(self.module.os, "fchmod", create=True), \
             mock.patch.object(self.module.os, "fstat", return_value=descriptor), \
             mock.patch.object(self.module.os, "stat", return_value=descriptor), \
             mock.patch.object(self.module.os, "write", side_effect=lambda fd, raw: len(raw)) as write, \
             mock.patch.object(self.module.os, "fsync") as fsync:
            fd = self.module.consume_publication_authority(41)
        self.assertEqual(fd, 42)
        flags = self.module.os.O_WRONLY | self.module.os.O_CREAT | self.module.os.O_EXCL | 0x20000
        opened.assert_called_once_with(self.module.PUBLICATION_REGISTRY.name, flags, 0o600, dir_fd=41)
        record = json.loads(bytes(write.call_args.args[1]))
        self.assertEqual(record["state"], "consumed")
        self.assertEqual(record["publication_authority_id"], self.module.PUBLICATION_AUTHORITY_ID)
        self.assertFalse(record["retry_authorized"])
        self.assertEqual([call.args[0] for call in fsync.call_args_list], [42, 41])

    def test_write_all_completes_short_writes_without_rerunning_transaction(self) -> None:
        raw = b"abcdef"
        with mock.patch.object(self.module.os, "write", side_effect=[2, 1, 3]) as write:
            self.module.write_all(42, raw, "test")
        self.assertEqual(write.call_count, 3)
        self.assertEqual(bytes(write.call_args_list[0].args[1]), b"abcdef")
        self.assertEqual(bytes(write.call_args_list[1].args[1]), b"cdef")
        self.assertEqual(bytes(write.call_args_list[2].args[1]), b"def")

    def test_atomic_rename_uses_macos_renameatx_np_exclusive_without_fallback(self) -> None:
        calls = []

        class RenameAtx:
            argtypes = None
            restype = None

            def __call__(self, source_fd, source, destination_fd, destination, flags):
                calls.append((source_fd, source, destination_fd, destination, flags))
                return 0

        renameatx = RenameAtx()
        libc = SimpleNamespace(renameatx_np=renameatx)
        with mock.patch.object(self.module.sys, "platform", "darwin"), \
             mock.patch.object(self.module.ctypes, "CDLL", return_value=libc):
            self.module.atomic_exclusive_rename_at(44, self.module.STAGING_NAME, self.module.DESTINATION.name)
        self.assertEqual(calls, [(
            44, os.fsencode(self.module.STAGING_NAME), 44,
            os.fsencode(self.module.DESTINATION.name), self.module.RENAME_EXCL,
        )])
        self.assertEqual(renameatx.restype, self.module.ctypes.c_int)
        self.assertEqual(renameatx.argtypes[-1], self.module.ctypes.c_uint)

        with mock.patch.object(self.module.sys, "platform", "darwin"), \
             mock.patch.object(self.module.ctypes, "CDLL", side_effect=OSError("unavailable")), \
             mock.patch.object(self.module.os, "rename", create=True) as rename, \
             mock.patch.object(self.module.os, "replace") as replace:
            with self.assertRaises(PermissionError):
                self.module.atomic_exclusive_rename_at(44, self.module.STAGING_NAME, self.module.DESTINATION.name)
        rename.assert_not_called()
        replace.assert_not_called()

    def test_destination_is_first_observed_then_staged_and_renamed_exclusively(self) -> None:
        raw = self.module.canonical_artifact_bytes()
        descriptor = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_dev=3, st_ino=5)
        order = []

        def observed(*args, **kwargs):
            name = args[0]
            order.append("final_stat" if name == self.module.DESTINATION.name else "staging_stat")
            if name == self.module.DESTINATION.name and order.count("final_stat") == 1:
                raise FileNotFoundError
            return descriptor

        def opened(*args, **kwargs):
            order.append("staging_open")
            return 43

        def renamed(parent_fd, source_name, destination_name):
            order.append("exclusive_rename")
            self.assertEqual((parent_fd, source_name, destination_name), (44, self.module.STAGING_NAME, self.module.DESTINATION.name))

        with mock.patch.object(self.module.os, "O_NOFOLLOW", 0x20000, create=True), \
             mock.patch.object(self.module.os, "stat", side_effect=observed), \
             mock.patch.object(self.module.os, "open", side_effect=opened) as open_mock, \
             mock.patch.object(self.module.os, "fchmod", create=True), \
             mock.patch.object(self.module.os, "fstat", return_value=descriptor), \
             mock.patch.object(self.module.os, "write", side_effect=lambda fd, value: order.append("write") or len(value)), \
             mock.patch.object(self.module.os, "fsync", side_effect=lambda fd: order.append("file_fsync" if fd == 43 else "parent_fsync")), \
             mock.patch.object(self.module.os, "close"), \
             mock.patch.object(self.module, "atomic_exclusive_rename_at", side_effect=renamed), \
             mock.patch.object(self.module, "stable_regular_bytes_at", return_value=raw):
            self.module.first_destination_observation_and_publish(44, raw)
        self.assertEqual(order[:7], [
            "final_stat", "staging_open", "staging_stat", "write", "file_fsync",
            "exclusive_rename", "final_stat",
        ])
        self.assertLess(order.index("exclusive_rename"), order.index("parent_fsync"))
        flags = self.module.os.O_WRONLY | self.module.os.O_CREAT | self.module.os.O_EXCL | 0x20000
        open_mock.assert_called_once_with(self.module.STAGING_NAME, flags, 0o600, dir_fd=44)
        self.assertNotEqual(open_mock.call_args.args[0], self.module.DESTINATION.name)

    def test_destination_appearing_before_exclusive_rename_is_never_overwritten(self) -> None:
        raw = self.module.canonical_artifact_bytes()
        descriptor = SimpleNamespace(st_mode=stat.S_IFREG | 0o600, st_nlink=1, st_dev=3, st_ino=5)
        with mock.patch.object(self.module.os, "O_NOFOLLOW", 0x20000, create=True), \
             mock.patch.object(self.module.os, "stat", side_effect=[FileNotFoundError(), descriptor]), \
             mock.patch.object(self.module.os, "open", return_value=43) as opened, \
             mock.patch.object(self.module.os, "fchmod", create=True), \
             mock.patch.object(self.module.os, "fstat", return_value=descriptor), \
             mock.patch.object(self.module.os, "write", side_effect=lambda fd, value: len(value)), \
             mock.patch.object(self.module.os, "fsync"), \
             mock.patch.object(self.module.os, "close"), \
             mock.patch.object(self.module, "atomic_exclusive_rename_at", side_effect=FileExistsError("destination appeared")) as renamed, \
             mock.patch.object(self.module, "stable_regular_bytes_at") as reread:
            with self.assertRaises(FileExistsError):
                self.module.first_destination_observation_and_publish(44, raw)
        opened.assert_called_once()
        renamed.assert_called_once_with(44, self.module.STAGING_NAME, self.module.DESTINATION.name)
        reread.assert_not_called()

    def test_execute_orders_ack_preflight_revalidation_consumption_observation_stop(self) -> None:
        identities = (("a", "b", 1, "c"),)
        context = {"canonical_bytes": self.module.canonical_artifact_bytes(), "identities": identities}
        order = []

        with mock.patch.object(self.module, "require_platform_ack_and_zero_arguments", side_effect=lambda: order.append("ack")), \
             mock.patch.object(self.module, "open_verified_parent", side_effect=lambda path: order.append("open_registry" if path == self.module.CONSTRUCTOR_REGISTRY.parent else "open_activation") or (41 if path == self.module.CONSTRUCTOR_REGISTRY.parent else 44)), \
             mock.patch.object(self.module, "preflight", side_effect=lambda fd: order.append("preflight") or context), \
             mock.patch.object(self.module, "verify_checkout", side_effect=lambda: order.append("checkout")), \
             mock.patch.object(self.module, "verify_ninety_two_target_identities", side_effect=lambda: order.append("identities") or identities), \
             mock.patch.object(self.module, "verify_constructor_terminal", side_effect=lambda fd: order.append("constructor_registry")), \
             mock.patch.object(self.module, "require_no_active_processes", side_effect=lambda: order.append("processes")), \
             mock.patch.object(self.module, "reverify_parent", side_effect=lambda fd, path: order.append("reverify_parent")), \
             mock.patch.object(self.module, "consume_publication_authority", side_effect=lambda fd: order.append("consume") or 42), \
             mock.patch.object(self.module, "first_destination_observation_and_publish", side_effect=lambda fd, raw: order.append("observe_publish")), \
             mock.patch.object(self.module.os, "close"):
            report = self.module.execute()

        self.assertEqual(order[:4], ["ack", "open_registry", "preflight", "open_activation"])
        self.assertLess(order.index("consume"), order.index("observe_publish"))
        self.assertEqual(order.count("consume"), 1)
        self.assertEqual(order.count("observe_publish"), 1)
        self.assertEqual(report["status"], "H27_REVIEW4_AUTHORITY_INSTANCE_ARTIFACT_PUBLICATION_TERMINAL_SUCCESS_STOP")
        self.assertTrue(report["publication_authority_consumed"] and report["destination_created_exclusive"])
        self.assertTrue(report["destination_published_by_atomic_exclusive_rename"])
        self.assertFalse(report["materializer_invoked"] or report["science_or_locked_test"] or report["retry_authorized"])

    def test_preflight_failure_never_consumes_or_observes_destination(self) -> None:
        with mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"), \
             mock.patch.object(self.module, "open_verified_parent", return_value=41), \
             mock.patch.object(self.module, "preflight", side_effect=PermissionError("drift")), \
             mock.patch.object(self.module, "consume_publication_authority") as consume, \
             mock.patch.object(self.module, "first_destination_observation_and_publish") as publish, \
             mock.patch.object(self.module.os, "close"):
            with self.assertRaises(PermissionError):
                self.module.execute()
        consume.assert_not_called()
        publish.assert_not_called()

    def test_post_consumption_failure_is_terminal_without_internal_retry(self) -> None:
        identities = (("a", "b", 1, "c"),)
        context = {"canonical_bytes": self.module.canonical_artifact_bytes(), "identities": identities}
        with mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"), \
             mock.patch.object(self.module, "open_verified_parent", side_effect=[41, 44]), \
             mock.patch.object(self.module, "preflight", return_value=context), \
             mock.patch.object(self.module, "verify_checkout"), \
             mock.patch.object(self.module, "verify_ninety_two_target_identities", return_value=identities), \
             mock.patch.object(self.module, "verify_constructor_terminal"), \
             mock.patch.object(self.module, "require_no_active_processes"), \
             mock.patch.object(self.module, "reverify_parent"), \
             mock.patch.object(self.module, "consume_publication_authority", return_value=42) as consume, \
             mock.patch.object(self.module, "first_destination_observation_and_publish", side_effect=OSError("terminal")) as publish, \
             mock.patch.object(self.module.os, "close"):
            with self.assertRaises(OSError):
                self.module.execute()
        consume.assert_called_once()
        publish.assert_called_once()


if __name__ == "__main__":
    unittest.main()
