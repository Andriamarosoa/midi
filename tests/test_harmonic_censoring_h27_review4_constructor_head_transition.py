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
RUNNER = ROOT / "scripts/h27_review4_constructor_head_transition_once.py"


def load_module():
    spec = importlib.util.spec_from_file_location("h27_review4_transition_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestH27Review4ConstructorHeadTransition(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.module = load_module()

    def test_runner_and_test_are_canonical_lf(self) -> None:
        for path in (RUNNER, Path(__file__)):
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))

    def test_exact_constants_bundle_and_constructor_identities(self) -> None:
        self.assertEqual(self.module.ACK, "H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_EXECUTE")
        self.assertEqual(self.module.CONSTRUCTOR_ACK, "H27_REAL_PUBLICATION_CONSTRUCTOR_ONE_SHOT_EXECUTION_GATE")
        self.assertEqual(self.module.INITIAL_HEAD, "7ee0a8977208bfa389e284b07207abc40a3517fd")
        self.assertEqual(self.module.TARGET_HEAD, "46a6bdf81a56a7a7a10524d4e55092301a452207")
        self.assertEqual(self.module.CLOSED_BUNDLE_DIGEST, "879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe")
        self.assertEqual(self.module.CONSTRUCTOR_BLOB, "0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62")
        self.assertEqual((self.module.CONSTRUCTOR_SIZE, self.module.CONSTRUCTOR_SHA256), (12599, "0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807"))
        self.assertEqual(len(self.module.BUNDLE_FILES), 6)
        for relative, blob_id, size, digest in self.module.BUNDLE_FILES:
            raw = subprocess.run(
                ["git", "cat-file", "blob", blob_id], cwd=ROOT, check=True,
                stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            ).stdout
            self.assertEqual((hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest(), len(raw), hashlib.sha256(raw).hexdigest()), (blob_id, size, digest))

    def test_ack_is_distinct_and_constructor_ack_forbidden(self) -> None:
        with (
            mock.patch.object(self.module.sys, "platform", "darwin"),
            mock.patch.object(self.module.sys, "argv", ["runner"]),
            mock.patch.dict(os.environ, {self.module.ACK: "1", self.module.CONSTRUCTOR_ACK: "1"}, clear=True),
        ):
            with self.assertRaises(PermissionError):
                self.module.require_platform_ack_and_zero_arguments()
        with (
            mock.patch.object(self.module.sys, "platform", "darwin"),
            mock.patch.object(self.module.sys, "argv", ["runner"]),
            mock.patch.dict(os.environ, {self.module.ACK: "1"}, clear=True),
        ):
            self.module.require_platform_ack_and_zero_arguments()

    def test_git_environment_is_clean_and_closed(self) -> None:
        with mock.patch.dict(os.environ, {"GIT_DIR": "evil", "GIT_CONFIG_GLOBAL": "evil", "SAFE": "yes"}, clear=True):
            environment = self.module.clean_environment()
        self.assertEqual(environment["SAFE"], "yes")
        self.assertEqual({key: environment[key] for key in environment if key.startswith("GIT_")}, {
            "GIT_TERMINAL_PROMPT": "0", "GIT_NO_LAZY_FETCH": "1", "GIT_OPTIONAL_LOCKS": "0",
        })

    def test_publication_paths_block_before_checkout_subprocess(self) -> None:
        for existing in (self.module.REGISTRY, self.module.FINAL, self.module.STAGING):
            def lstat(path, *, target=existing):
                if path == target:
                    return mock.Mock()
                raise FileNotFoundError
            with mock.patch.object(self.module.os, "lstat", side_effect=lstat):
                with self.assertRaises(PermissionError):
                    self.module.require_publication_paths_absent()

        calls: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_realpaths"),
            mock.patch.object(self.module, "verify_control_bundle", return_value=self.module.CLOSED_BUNDLE_DIGEST),
            mock.patch.object(self.module, "verify_initial_git_state", return_value=b"refs"),
            mock.patch.object(self.module, "verify_constructor"),
            mock.patch.object(self.module, "require_publication_paths_absent", side_effect=PermissionError("present")),
            mock.patch.object(self.module, "perform_single_explicit_detach", side_effect=lambda: calls.append("checkout")),
        ):
            with self.assertRaises(PermissionError):
                self.module.transition()
        self.assertEqual(calls, [])

    def test_current_runner_pid_is_ignored_but_competing_runner_blocks_before_checkout(self) -> None:
        current_only = subprocess.CompletedProcess(
            ["ps"], 0,
            stdout=b"111 python h27_review4_constructor_head_transition_once.py\n",
            stderr=b"",
        )
        competing = subprocess.CompletedProcess(
            ["ps"], 0,
            stdout=(
                b"111 python h27_review4_constructor_head_transition_once.py\n"
                b"222 python h27_review4_constructor_head_transition_once.py\n"
            ),
            stderr=b"",
        )
        with (
            mock.patch.object(self.module.os, "getpid", return_value=111),
            mock.patch.object(self.module.subprocess, "run", return_value=current_only),
        ):
            self.module.require_no_active_processes()
        with (
            mock.patch.object(self.module.os, "getpid", return_value=111),
            mock.patch.object(self.module.subprocess, "run", return_value=competing),
        ):
            with self.assertRaisesRegex(PermissionError, "competing transition"):
                self.module.require_no_active_processes()

        checkout: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_realpaths"),
            mock.patch.object(self.module, "verify_control_bundle", return_value=self.module.CLOSED_BUNDLE_DIGEST),
            mock.patch.object(self.module, "verify_initial_git_state", return_value=b"refs"),
            mock.patch.object(self.module, "verify_constructor"),
            mock.patch.object(self.module, "require_publication_paths_absent"),
            mock.patch.object(self.module, "current_head", return_value=self.module.INITIAL_HEAD),
            mock.patch.object(self.module, "require_detached"),
            mock.patch.object(self.module, "require_clean_and_unlocked"),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module.os, "getpid", return_value=111),
            mock.patch.object(self.module.subprocess, "run", side_effect=[current_only, competing]),
            mock.patch.object(self.module, "perform_single_explicit_detach", side_effect=lambda: checkout.append("checkout")),
        ):
            with self.assertRaisesRegex(PermissionError, "competing transition"):
                self.module.transition()
        self.assertEqual(checkout, [])

    def test_exact_single_mutation_command_and_terminal_failure(self) -> None:
        expected = [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
            "-C", "/Users/amcarene/midi-worker/repository", "checkout", "--detach",
            "--no-recurse-submodules", self.module.TARGET_HEAD,
        ]
        completed = subprocess.CompletedProcess(expected, 0, stdout=b"", stderr=b"")
        with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run:
            self.module.perform_single_explicit_detach()
        self.assertEqual(run.call_count, 1)
        self.assertEqual(run.call_args.args[0], expected)
        self.assertEqual(run.call_args.kwargs["env"]["GIT_NO_LAZY_FETCH"], "1")
        failed = subprocess.CompletedProcess(expected, 1, stdout=b"partial", stderr=b"failed")
        with mock.patch.object(self.module.subprocess, "run", return_value=failed) as run:
            with self.assertRaisesRegex(PermissionError, "consumed and failed"):
                self.module.perform_single_explicit_detach()
        self.assertEqual(run.call_count, 1)

    def test_transition_order_revalidates_before_and_after_one_mutation(self) -> None:
        calls: list[str] = []
        heads = iter([self.module.INITIAL_HEAD, self.module.TARGET_HEAD])
        bundles = iter([self.module.CLOSED_BUNDLE_DIGEST] * 3)

        def mark(name, value=None):
            def action(*args, **kwargs):
                calls.append(name)
                return value
            return action

        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments", side_effect=mark("ack")),
            mock.patch.object(self.module, "verify_checkout_realpaths", side_effect=mark("roots")),
            mock.patch.object(self.module, "verify_control_bundle", side_effect=lambda: (calls.append("bundle"), next(bundles))[1]),
            mock.patch.object(self.module, "verify_initial_git_state", side_effect=mark("initial", b"refs")),
            mock.patch.object(self.module, "verify_constructor", side_effect=mark("constructor")),
            mock.patch.object(self.module, "require_publication_paths_absent", side_effect=mark("paths")),
            mock.patch.object(self.module, "require_no_active_processes", side_effect=mark("processes")),
            mock.patch.object(self.module, "current_head", side_effect=lambda: (calls.append("head"), next(heads))[1]),
            mock.patch.object(self.module, "require_detached", side_effect=mark("detached")),
            mock.patch.object(self.module, "require_clean_and_unlocked", side_effect=mark("clean")),
            mock.patch.object(self.module, "regular_refs_snapshot", side_effect=mark("refs", b"refs")),
            mock.patch.object(self.module, "perform_single_explicit_detach", side_effect=mark("checkout")),
        ):
            report = self.module.transition()
        self.assertEqual(calls.count("checkout"), 1)
        self.assertLess(calls.index("paths"), calls.index("checkout"))
        self.assertGreater(len(calls) - 1 - calls[::-1].index("paths"), calls.index("checkout"))
        self.assertEqual(calls.count("bundle"), 3)
        self.assertEqual(calls.count("constructor"), 3)
        self.assertEqual(report["status"], "H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_TERMINAL_SUCCESS_STOP")
        self.assertTrue(report["transition_attempt_consumed"])
        self.assertFalse(report["constructor_invoked"])

    def test_checkout_failure_stops_without_postchecks_or_retry(self) -> None:
        post: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_ack_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_realpaths"),
            mock.patch.object(self.module, "verify_control_bundle", return_value=self.module.CLOSED_BUNDLE_DIGEST),
            mock.patch.object(self.module, "verify_initial_git_state", return_value=b"refs"),
            mock.patch.object(self.module, "verify_constructor"),
            mock.patch.object(self.module, "require_publication_paths_absent"),
            mock.patch.object(self.module, "require_no_active_processes"),
            mock.patch.object(self.module, "current_head", return_value=self.module.INITIAL_HEAD),
            mock.patch.object(self.module, "require_detached"),
            mock.patch.object(self.module, "require_clean_and_unlocked"),
            mock.patch.object(self.module, "regular_refs_snapshot", return_value=b"refs"),
            mock.patch.object(self.module, "perform_single_explicit_detach", side_effect=PermissionError("consumed")) as checkout,
        ):
            with self.assertRaisesRegex(PermissionError, "consumed"):
                self.module.transition()
        self.assertEqual(checkout.call_count, 1)
        self.assertEqual(post, [])

    def test_source_has_one_mutation_call_and_no_forbidden_git_operations(self) -> None:
        source = inspect.getsource(self.module.transition)
        self.assertEqual(source.count("perform_single_explicit_detach()"), 1)
        mutation = inspect.getsource(self.module.perform_single_explicit_detach)
        self.assertIn('"checkout", "--detach", "--no-recurse-submodules", TARGET_HEAD', mutation)
        for token in ('"pull"', '"fetch"', '"merge"', '"reset"', '"rebase"', '"switch"', '"branch"'):
            self.assertNotIn(token, mutation)


if __name__ == "__main__":
    unittest.main()
