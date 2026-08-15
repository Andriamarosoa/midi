from __future__ import annotations

import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import subprocess
import unittest
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_transition_contract.json"
RUNNER = ROOT / "scripts/h27_detach_target_checkout_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_runner_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_target_checkout_detach_runner_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


def load_module():
    spec = importlib.util.spec_from_file_location("h27_checkout_detach_runner_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestTargetCheckoutDetachRunner(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.contract = json.loads(CONTRACT.read_bytes())
        cls.runner_raw = RUNNER.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_runner_binding_seal_and_six_path_graph(self) -> None:
        for raw in (self.runner_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.binding["runner"])
        check(self, self.seal["identity_binding"])
        check(self, self.seal["runner"])
        identities = [
            self.binding["runner"],
            *self.binding["approved_transition_chain"],
            self.binding["reviewed_preflight_evidence"],
        ]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (6, 6))
        for identity in identities[1:]:
            check(self, identity)
        self.assertEqual(self.binding["runner"], self.seal["runner"])

    def test_exact_five_identity_git_blob_preflight(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(
                ["git", "cat-file", "blob", blob_sha1],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout

        original = self.module.read_blob
        try:
            self.module.read_blob = local_blob
            verified = self.module.verify_identity_graph()
        finally:
            self.module.read_blob = original
        self.assertEqual((len(verified), len(set(verified))), (5, 5))

    def test_exact_binding_boundary_and_dormant_state(self) -> None:
        self.assertEqual(self.binding["identity_graph"], {
            "combined_unique_path_count_including_runner": 6,
            "runner_rehashes_five_predecessor_identities_after_realpath_and_before_head_observation": True,
            "duplicates_forbidden": True, "path_or_identity_drift_forbidden": True,
            "acyclic": True, "self_hash_present": False,
        })
        self.assertEqual(self.binding["execution_binding"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_TARGET_CHECKOUT_DETACH_EXECUTE=1",
            "arguments_forbidden": True,
            "checkout_path_exact": "/Users/amcarene/midi-worker/repository",
            "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "initial_head_exact": "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf",
            "target_head_exact": "7ee0a8977208bfa389e284b07207abc40a3517fd",
            "target_object_type_exact": "commit",
            "mutation_command_exact": ["git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false", "-C", "/Users/amcarene/midi-worker/repository", "checkout", "--detach", "--no-recurse-submodules", "7ee0a8977208bfa389e284b07207abc40a3517fd"],
            "execution_from_exact_reviewed_git_blob_only": True,
            "checkout_or_worktree_source_fallback_forbidden": True,
        })
        self.assertEqual(self.binding["administrative_identity_gate"], {
            "operation_exact": "verify_five_predecessor_identities",
            "after_transition_step_exact": "verify_checkout_and_odb_realpaths",
            "before_transition_step_exact": "verify_initial_head_exact",
            "predecessor_identity_count_exact": 5,
        })
        expected_contract_order = [
            "verify_platform_and_zero_arguments", "verify_checkout_and_odb_realpaths",
            "verify_initial_head_exact", "verify_initial_worktree_clean",
            "verify_target_object_exists_and_type_is_commit",
            "reverify_initial_head_and_cleanliness",
            "perform_single_explicit_detach_to_exact_target_sha_as_first_and_only_mutation",
            "verify_target_head_exact", "verify_detached_state", "verify_worktree_clean",
            "terminal_success_then_stop",
        ]
        self.assertEqual(self.binding["normative_transition_order"], expected_contract_order)
        self.assertEqual(self.binding["normative_transition_order"], self.contract["future_fail_closed_order"])
        self.assertEqual(self.seal["future_normative_transition_order"], self.contract["future_fail_closed_order"])
        self.assertEqual(self.binding["transition_safeguards"], {
            "clean_git_environment_before_every_git_process": True,
            "optional_locks_disabled_for_all_read_only_git_commands": True,
            "hooks_disabled_for_all_checkout_git_commands": True,
            "submodule_recursion_disabled": True,
            "target_commit_type_verified_before_mutation": True,
            "initial_head_and_cleanliness_reverified_immediately_before_mutation": True,
            "single_checkout_detach_subprocess_call": True,
            "fetch_pull_merge_reset_rebase_and_branch_mutation_absent": True,
            "no_retry_reset_cleanup_repair_or_automatic_recovery_after_failure": True,
            "terminal_head_detached_and_clean_verified": True,
            "registry_authority_creator_bundle_constructor_materializer_and_science_forbidden": True,
        })
        self.assertEqual(self.binding["current_state"], {
            "runner_exists": True, "runner_externally_reviewed": False,
            "runner_externally_sealed": False, "runner_executed": False,
            "acknowledgement_set": False, "mac_checkout_transition_executed": False,
            "registry_opened": False, "authority_reserved": False,
            "authority_consumed": False, "creator_invoked": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
        })

    def test_static_and_synthetic_normative_order_has_one_mutation(self) -> None:
        source = inspect.getsource(self.module.transition)
        ordered = [
            "require_platform_and_zero_arguments()", "verify_checkout_and_odb_realpaths()",
            "verify_identity_graph()", "require_initial_head_exact()",
            "require_worktree_clean()", "require_target_object_commit()",
            "require_initial_head_exact()", "require_worktree_clean()",
            "perform_single_explicit_detach()", "require_target_head_exact()",
            "require_detached_state()", "require_worktree_clean()",
        ]
        cursor = -1
        for token in ordered:
            cursor = source.index(token, cursor + 1)
        self.assertEqual(source.count("perform_single_explicit_detach()"), 1)

        calls: list[str] = []

        def mark(name: str, result=None):
            def action(*args, **kwargs):
                calls.append(name)
                return result
            return action

        with (
            mock.patch.object(self.module, "require_platform_and_zero_arguments", side_effect=mark("platform")),
            mock.patch.object(self.module, "verify_checkout_and_odb_realpaths", side_effect=mark("realpaths")),
            mock.patch.object(self.module, "verify_identity_graph", side_effect=mark("identities", {str(i): b"" for i in range(5)})),
            mock.patch.object(self.module, "require_initial_head_exact", side_effect=mark("head")),
            mock.patch.object(self.module, "require_worktree_clean", side_effect=mark("clean")),
            mock.patch.object(self.module, "require_target_object_commit", side_effect=mark("target")),
            mock.patch.object(self.module, "perform_single_explicit_detach", side_effect=mark("detach")),
            mock.patch.object(self.module, "require_target_head_exact", side_effect=mark("target_head")),
            mock.patch.object(self.module, "require_detached_state", side_effect=mark("detached")),
        ):
            result = self.module.transition()
        self.assertEqual(calls, [
            "platform", "realpaths", "identities", "head", "clean", "target",
            "head", "clean", "detach", "target_head", "detached", "clean",
        ])
        self.assertEqual(calls.count("detach"), 1)
        self.assertEqual(result["status"], "H27_TARGET_CHECKOUT_EXACT_DETACH_TERMINAL_SUCCESS")

    def test_all_read_only_git_commands_disable_optional_locks(self) -> None:
        completed = mock.Mock(returncode=0, stdout=b"", stderr=b"")
        with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run:
            self.module.git_read(["status", "--porcelain=v1", "--untracked-files=all"])
            self.module.git_read(["rev-parse", "--verify", "HEAD"])
            self.module.git_read(["cat-file", "-t", self.module.TARGET_HEAD])
            self.module.git_read(["symbolic-ref", "-q", "HEAD"], expected_returncodes=(0, 1))
            self.module.read_blob("a" * 40)

        commands = [call.args[0] for call in run.call_args_list]
        checkout_prefix = [
            "git", "--no-optional-locks", "-c", "core.hooksPath=/dev/null",
            "-C", "/Users/amcarene/midi-worker/repository",
        ]
        self.assertEqual(commands[:4], [
            [*checkout_prefix, "status", "--porcelain=v1", "--untracked-files=all"],
            [*checkout_prefix, "rev-parse", "--verify", "HEAD"],
            [*checkout_prefix, "cat-file", "-t", self.module.TARGET_HEAD],
            [*checkout_prefix, "symbolic-ref", "-q", "HEAD"],
        ])
        self.assertEqual(commands[4], [
            "git", "--no-optional-locks",
            "--git-dir=/Users/amcarene/midi-worker/repository/.git",
            "cat-file", "blob", "a" * 40,
        ])
        transition_reads: list[list[str]] = []

        def record_transition_read(arguments, *, expected_returncodes=(0,)):
            transition_reads.append(arguments)
            return subprocess.CompletedProcess(arguments, 0, stdout=b"", stderr=b"")

        with (
            mock.patch.object(self.module, "require_platform_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_and_odb_realpaths"),
            mock.patch.object(self.module, "verify_identity_graph", return_value={str(i): b"" for i in range(5)}),
            mock.patch.object(self.module, "require_initial_head_exact"),
            mock.patch.object(self.module, "require_target_object_commit"),
            mock.patch.object(self.module, "perform_single_explicit_detach"),
            mock.patch.object(self.module, "require_target_head_exact"),
            mock.patch.object(self.module, "require_detached_state"),
            mock.patch.object(self.module, "git_read", side_effect=record_transition_read),
        ):
            self.module.transition()
        status = ["status", "--porcelain=v1", "--untracked-files=all"]
        self.assertEqual(transition_reads, [status, status, status])

    def test_detach_command_exact_and_failure_is_terminal(self) -> None:
        expected = [
            "git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false",
            "-C", "/Users/amcarene/midi-worker/repository", "checkout", "--detach",
            "--no-recurse-submodules", "7ee0a8977208bfa389e284b07207abc40a3517fd",
        ]
        completed = mock.Mock(returncode=0, stdout=b"", stderr=b"")
        with mock.patch.object(self.module.subprocess, "run", return_value=completed) as run:
            self.module.perform_single_explicit_detach()
        self.assertEqual(run.call_args.args[0], expected)
        self.assertFalse(run.call_args.kwargs["check"])

        calls: list[str] = []
        with (
            mock.patch.object(self.module, "require_platform_and_zero_arguments"),
            mock.patch.object(self.module, "verify_checkout_and_odb_realpaths"),
            mock.patch.object(self.module, "verify_identity_graph", return_value={str(i): b"" for i in range(5)}),
            mock.patch.object(self.module, "require_initial_head_exact"),
            mock.patch.object(self.module, "require_worktree_clean"),
            mock.patch.object(self.module, "require_target_object_commit"),
            mock.patch.object(self.module, "perform_single_explicit_detach", side_effect=PermissionError("terminal")),
            mock.patch.object(self.module, "require_target_head_exact", side_effect=lambda: calls.append("post")),
        ):
            with self.assertRaises(PermissionError):
                self.module.transition()
        self.assertEqual(calls, [])

    def test_exact_external_seal(self) -> None:
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_TARGET_CHECKOUT_EXACT_DETACH_ONE_SHOT_RUNNER_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
            "status": "SEALED_PENDING_EXTERNAL_REVIEW_RUNNER_DORMANT_NO_MAC_CHECKOUT_CHANGE_NO_REGISTRY_NO_CREATOR_NO_BUNDLE_NO_SCIENCE",
            "identity_binding": {"path": "configs/harmonic_censoring_h27_target_checkout_detach_runner_identity_binding.json", "git_blob_sha1": "d03385d842ca11631ba690d0a4bb70448c84480e", "size_bytes": 4927, "raw_sha256": "3db676881b0fca2265c09801be5fbb94d98bbf475429a7113deee872a68970df"},
            "runner": {"path": "scripts/h27_detach_target_checkout_one_shot.py", "git_blob_sha1": "d1cdf1562a814cef271d606da331e96565fcc79a", "size_bytes": 10428, "raw_sha256": "e0fd3a4794cc2fdb266b9f3b89da25fa1260f6575e31dc3d95f761ed313b833f"},
            "approved_transition_binding_commit": "1c523581c866890c932268b54b66575871741acd",
            "verified_predecessor_identity_count": 5,
            "future_platform_exact": "darwin",
            "future_acknowledgement_environment_exact": "H27_TARGET_CHECKOUT_DETACH_EXECUTE=1",
            "future_arguments_forbidden": True,
            "future_execution_from_exact_reviewed_git_blob_only": True,
            "future_checkout_path_exact": "/Users/amcarene/midi-worker/repository",
            "future_git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "future_initial_head_exact": "75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf",
            "future_target_head_exact": "7ee0a8977208bfa389e284b07207abc40a3517fd",
            "future_target_object_type_exact": "commit",
            "future_mutation_command_exact": ["git", "-c", "core.hooksPath=/dev/null", "-c", "advice.detachedHead=false", "-C", "/Users/amcarene/midi-worker/repository", "checkout", "--detach", "--no-recurse-submodules", "7ee0a8977208bfa389e284b07207abc40a3517fd"],
            "future_administrative_identity_gate": {"operation_exact": "verify_five_predecessor_identities", "after_transition_step_exact": "verify_checkout_and_odb_realpaths", "before_transition_step_exact": "verify_initial_head_exact", "predecessor_identity_count_exact": 5},
            "future_normative_transition_order": ["verify_platform_and_zero_arguments", "verify_checkout_and_odb_realpaths", "verify_initial_head_exact", "verify_initial_worktree_clean", "verify_target_object_exists_and_type_is_commit", "reverify_initial_head_and_cleanliness", "perform_single_explicit_detach_to_exact_target_sha_as_first_and_only_mutation", "verify_target_head_exact", "verify_detached_state", "verify_worktree_clean", "terminal_success_then_stop"],
            "future_single_attempt_only": True,
            "future_optional_locks_disabled_for_all_read_only_git_commands": True,
            "future_retry_reset_cleanup_repair_or_automatic_recovery_forbidden": True,
            "runner_externally_reviewed": False, "runner_externally_sealed": False,
            "runner_executed": False, "acknowledgement_set": False,
            "mac_checkout_transition_executed": False, "registry_opened": False,
            "authority_reserved": False, "authority_consumed": False,
            "creator_invoked": False, "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "next_action": "External review of the exact dormant transition runner, identity binding and this seal only; no Mac execution",
        })


if __name__ == "__main__":
    unittest.main()
