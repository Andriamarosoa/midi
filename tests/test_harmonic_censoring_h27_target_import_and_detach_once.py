from __future__ import annotations

import hashlib
import importlib.util
import inspect
import os
from pathlib import Path
import subprocess
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/h27_target_import_and_detach_once.py"


def load_module():
    spec = importlib.util.spec_from_file_location("h27_target_import_and_detach_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestH27TargetImportAndDetachOnce(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_embeds_exact_eight_reviewed_payloads_without_source_odb(self) -> None:
        module = self.module

        def hash_only(arguments, *, stdin=None, expected=(0,)):
            self.assertEqual(arguments, ["hash-object", "--stdin"])
            assert stdin is not None
            return subprocess.CompletedProcess(arguments, 0, (module.git_blob(stdin) + "\n").encode("ascii"), b"")

        with mock.patch.object(module, "target_git", side_effect=hash_only):
            payloads = module.decode_and_prevalidate_all()
        expected = [
            "d1cdf1562a814cef271d606da331e96565fcc79a",
            "d03385d842ca11631ba690d0a4bb70448c84480e",
            "e574ddbcccb8bac791d9719fbee3e7fd5db8a047",
            "a514aa0270926dca1d8402ac84078a50754d2f17",
            "0f6a64b7477bde24968200a81d389b03a4a6ced0",
            "11fff0962fc0951a0bb06605e233d34756a2f4d9",
            "24a8c14fddd52eca148f961a31c39abaa4de018f",
            "bda7e1fae7379996563e73d8bbcf1b2d7a871aa0",
        ]
        self.assertEqual(list(payloads), expected)
        for identity in module.PAYLOADS:
            raw = payloads[str(identity["git_blob_sha1"])]
            self.assertTrue(module.identity_ok(identity, raw))
        source = RUNNER.read_text(encoding="utf-8")
        self.assertNotIn("/Users/amcarene/midi/.git", source)
        self.assertNotIn("SOURCE_GIT_DIR", source)
        self.assertNotIn("ssh ", source.lower())

    def test_archive_tamper_fails_before_target_hash_prevalidation(self) -> None:
        module = self.module
        with (
            mock.patch.object(module, "EMBEDDED_ARCHIVE_BASE64", module.EMBEDDED_ARCHIVE_BASE64[:-1] + "A"),
            mock.patch.object(module, "target_git") as target_git,
        ):
            with self.assertRaises(PermissionError):
                module.decode_and_prevalidate_all()
        target_git.assert_not_called()

    def test_closed_git_environment_and_exact_ack(self) -> None:
        module = self.module
        with mock.patch.dict(os.environ, {"GIT_DIR": "bad", "GIT_CONFIG_COUNT": "9", "KEEP": "yes"}, clear=True):
            environment = module.clean_git_environment()
        self.assertEqual(environment, {
            "KEEP": "yes",
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_NO_LAZY_FETCH": "1",
        })
        self.assertEqual(module.ACK_ENV, "H27_TARGET_IMPORT_AND_DETACH_EXECUTE")
        with (
            mock.patch.object(module.sys, "platform", "darwin"),
            mock.patch.object(module.sys, "argv", ["runner"]),
            mock.patch.dict(os.environ, {module.ACK_ENV: "1"}, clear=True),
        ):
            module.require_platform_ack_and_zero_arguments()

    def test_exact_detach_command_and_no_retry(self) -> None:
        module = self.module
        completed = subprocess.CompletedProcess([], 0, b"", b"")
        with mock.patch.object(module, "run_git", return_value=completed) as run:
            module.perform_single_explicit_detach()
        run.assert_called_once_with([
            "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
            "-C", "/Users/amcarene/midi-worker/repository", "checkout", "--detach",
            "--no-recurse-submodules", "7ee0a8977208bfa389e284b07207abc40a3517fd",
        ])
        source = inspect.getsource(module.import_and_detach_once)
        self.assertEqual(source.count("write_exact_payloads(payloads)"), 1)
        self.assertEqual(source.count("perform_single_explicit_detach()"), 1)
        self.assertNotIn("while ", source)

    def test_terminal_root_refs_allow_only_exact_head_detach(self) -> None:
        module = self.module
        before = ((b"HEAD", (module.SYMBOLIC_HEAD + "\n").encode()), (b"ORIG_HEAD", b"a" * 40 + b"\n"))
        after = ((b"HEAD", (module.TARGET_HEAD + "\n").encode()), (b"ORIG_HEAD", b"a" * 40 + b"\n"))
        with mock.patch.object(module, "root_refs_snapshot", return_value=after):
            module.require_only_head_root_ref_changed(before)
        drifted = ((b"HEAD", (module.TARGET_HEAD + "\n").encode()), (b"ORIG_HEAD", b"b" * 40 + b"\n"))
        with mock.patch.object(module, "root_refs_snapshot", return_value=drifted):
            with self.assertRaises(PermissionError):
                module.require_only_head_root_ref_changed(before)

    def test_combined_order_and_terminal_report(self) -> None:
        module = self.module
        calls: list[str] = []
        payloads = {str(item["git_blob_sha1"]): b"x" for item in module.PAYLOADS}
        before: dict[str, tuple[int, int, int, int, int]] = {}
        after = {
            "objects/" + str(item["git_blob_sha1"])[:2] + "/" + str(item["git_blob_sha1"])[2:]: (1, 1, 1, 1, 1)
            for item in module.PAYLOADS
        }

        def mark(name, value=None):
            def action(*args, **kwargs):
                calls.append(name)
                return value
            return action

        patches = [
            mock.patch.object(module, "require_platform_ack_and_zero_arguments", side_effect=mark("platform")),
            mock.patch.object(module, "verify_checkout_and_odb_realpaths", side_effect=mark("paths")),
            mock.patch.object(module, "require_reference_storage_files", side_effect=mark("backend")),
            mock.patch.object(module, "require_baseline", side_effect=mark("baseline")),
            mock.patch.object(module, "regular_refs_snapshot", side_effect=[b"refs"] * 5),
            mock.patch.object(module, "root_refs_snapshot", side_effect=[((b"HEAD", b"x"),)] * 3),
            mock.patch.object(module, "index_snapshot", side_effect=[(True, b"index")] * 3),
            mock.patch.object(module, "require_conflicting_runner_absent", side_effect=mark("process")),
            mock.patch.object(module, "decode_and_prevalidate_all", side_effect=mark("payloads", payloads)),
            mock.patch.object(module, "require_target_commit", side_effect=mark("commit")),
            mock.patch.object(module, "require_all_target_blobs_absent", side_effect=mark("absent")),
            mock.patch.object(module, "object_paths_snapshot", side_effect=[before, after]),
            mock.patch.object(module, "write_exact_payloads", side_effect=mark("write")),
            mock.patch.object(module, "require_all_target_blobs_exact", side_effect=mark("exact")),
            mock.patch.object(module, "perform_single_explicit_detach", side_effect=mark("detach")),
            mock.patch.object(module, "require_terminal_detached_state", side_effect=mark("terminal")),
            mock.patch.object(module, "require_only_head_root_ref_changed", side_effect=mark("root-final")),
        ]
        for patch in patches:
            patch.start()
        try:
            report = module.import_and_detach_once()
        finally:
            for patch in reversed(patches):
                patch.stop()
        self.assertLess(calls.index("payloads"), calls.index("write"))
        self.assertLess(calls.index("write"), calls.index("detach"))
        self.assertLess(calls.index("detach"), calls.index("terminal"))
        self.assertLess(calls.index("terminal"), calls.index("root-final"))
        self.assertEqual(calls.count("write"), 1)
        self.assertEqual(calls.count("detach"), 1)
        self.assertEqual(report["status"], "H27_TARGET_EXACT_EIGHT_BLOB_IMPORT_AND_DETACH_TERMINAL_SUCCESS")
        self.assertEqual((report["payload_count"], report["detached"], report["science_or_locked_test"]), (8, True, False))

    def test_prevalidation_failure_never_reaches_first_write(self) -> None:
        module = self.module
        with (
            mock.patch.object(module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(module, "verify_checkout_and_odb_realpaths"),
            mock.patch.object(module, "require_reference_storage_files"),
            mock.patch.object(module, "require_baseline"),
            mock.patch.object(module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(module, "root_refs_snapshot", return_value=()),
            mock.patch.object(module, "index_snapshot", return_value=(False, b"")),
            mock.patch.object(module, "require_conflicting_runner_absent"),
            mock.patch.object(module, "decode_and_prevalidate_all", side_effect=PermissionError("bad payload")),
            mock.patch.object(module, "write_exact_payloads") as write,
            mock.patch.object(module, "perform_single_explicit_detach") as detach,
        ):
            with self.assertRaises(PermissionError):
                module.import_and_detach_once()
        write.assert_not_called()
        detach.assert_not_called()

    def test_second_new_runner_pid_blocks_before_import_or_detach(self) -> None:
        module = self.module
        other_pid = os.getpid() + 1000
        ps = subprocess.CompletedProcess(
            [], 0,
            (
                f"{os.getpid()} /usr/bin/python3 h27_target_import_and_detach_once.py\n"
                f"{other_pid} /usr/bin/python3 h27_target_import_and_detach_once.py\n"
            ).encode("utf-8"),
            b"",
        )
        with (
            mock.patch.object(module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(module, "verify_checkout_and_odb_realpaths"),
            mock.patch.object(module, "require_reference_storage_files"),
            mock.patch.object(module, "require_baseline"),
            mock.patch.object(module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(module, "root_refs_snapshot", return_value=((b"HEAD", b"head"),)),
            mock.patch.object(module, "index_snapshot", return_value=(True, b"index")),
            mock.patch.object(module, "run_git", return_value=ps),
            mock.patch.object(module, "decode_and_prevalidate_all") as decode,
            mock.patch.object(module, "write_exact_payloads") as write,
            mock.patch.object(module, "perform_single_explicit_detach") as detach,
        ):
            with self.assertRaises(PermissionError):
                module.import_and_detach_once()
        decode.assert_not_called()
        write.assert_not_called()
        detach.assert_not_called()


if __name__ == "__main__":
    unittest.main()
