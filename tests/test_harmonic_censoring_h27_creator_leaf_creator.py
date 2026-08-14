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
RUNNER = ROOT / "scripts/h27_create_creator_leaf_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_creator_leaf_creator_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_creator_leaf_creator_identity_binding_external_seal.json"


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
    spec = importlib.util.spec_from_file_location("h27_creator_leaf_creator_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestCreatorLeafCreator(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.runner_raw = RUNNER.read_bytes()
        cls.binding_raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.binding_raw)
        cls.seal = json.loads(cls.seal_raw)
        cls.module = load_module()

    def test_exact_runner_binding_seal_and_eight_path_graph(self) -> None:
        for raw in (self.runner_raw, self.binding_raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.binding["runner"])
        check(self, self.seal["identity_binding"])
        check(self, self.seal["runner"])
        identities = [
            self.binding["runner"],
            *self.binding["approved_contract_chain"],
            *self.binding["transitive_contract_identities"],
        ]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (8, 8))
        for identity in identities[1:]:
            check(self, identity)
        self.assertEqual(self.binding["runner"], self.seal["runner"])

    def test_exact_seven_identity_git_blob_preflight(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(
                ["git", "cat-file", "blob", blob_sha1],
                cwd=ROOT,
                check=True,
                stdout=subprocess.PIPE,
            ).stdout

        original_read_blob = self.module.read_blob
        original_require_git_database = self.module.require_git_database
        try:
            self.module.read_blob = local_blob
            self.module.require_git_database = lambda: None
            verified = self.module.verify_identity_graph()
        finally:
            self.module.read_blob = original_read_blob
            self.module.require_git_database = original_require_git_database
        self.assertEqual((len(verified), len(set(verified))), (7, 7))
        source = inspect.getsource(self.module.verify_identity_graph)
        self.assertLess(source.index("require_git_database()"), source.index("read_blob("))

    def test_exact_terminal_parent_binding_order_and_dormant_state(self) -> None:
        source = inspect.getsource(self.module.create)
        ordered = [
            "verify_identity_graph()",
            "require_environment()",
            "open_verified_parent()",
            "probe_target_absence_once(parent_fd)",
            "require_parent_fd_still_named(parent_fd)",
            "os.mkdir(TARGET_LEAF, mode=0o700, dir_fd=parent_fd)",
            "os.fsync(parent_fd)",
            "open_created_leaf(parent_fd)",
            "verify_created_leaf(parent_fd, leaf_fd)",
            "require_parent_fd_still_named(parent_fd)",
        ]
        positions = [source.index(token) for token in ordered[:-1]] + [source.rindex(ordered[-1])]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("os.mkdir("), 1)
        self.assertNotIn("rmtree", source)
        self.assertNotIn("unlink", source)
        self.assertEqual(
            self.binding["execution_binding"],
            {
                "platform_exact": "darwin",
                "acknowledgement_environment_exact": "H27_CREATOR_LEAF_CREATE_EXECUTE=1",
                "arguments_forbidden": True,
                "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
                "parent_path_exact": "/Users/amcarene/h27-admin",
                "parent_expected_device_exact": 16777233,
                "parent_expected_inode_exact": 1445438,
                "parent_fd_and_named_entry_must_match_terminal_identity": True,
                "target_leaf_exact": "creator",
                "target_path_exact": "/Users/amcarene/h27-admin/creator",
                "execution_from_exact_reviewed_git_blob_only": True,
                "checkout_or_worktree_fallback_forbidden": True,
            },
        )
        self.assertEqual(
            self.binding["identity_graph"],
            {
                "combined_unique_path_count_including_runner": 8,
                "runner_rehashes_seven_predecessor_identities_before_parent_observation": True,
                "duplicates_forbidden": True,
                "path_or_identity_drift_forbidden": True,
                "acyclic": True,
                "self_hash_present": False,
            },
        )
        self.assertEqual(
            self.binding["creation_safeguards"],
            {
                "all_seven_predecessor_identities_rehashed_before_parent_observation": True,
                "parent_opened_o_nofollow_and_anchored_by_verified_dirfd": True,
                "parent_fd_and_named_entry_match_terminal_device_inode_before_probe_effect_and_success": True,
                "single_target_absence_probe_relative_to_parent_dirfd": True,
                "exact_leaf_mkdir_first_and_only_irreversible_effect": True,
                "mkdir_parents_forbidden": True,
                "parent_fsynced_after_creation": True,
                "created_leaf_opened_o_nofollow_and_inode_device_verified": True,
                "cleanup_retry_repair_or_recreation_forbidden": True,
                "publisher_creator_entrypoint_registry_bundle_and_science_forbidden": True,
            },
        )
        self.assertEqual(
            self.binding["authority_state"],
            {
                "admin_root_creation_authority_terminally_consumed": True,
                "admin_root_creator_retry_forbidden": True,
                "creator_leaf_creation_authority_unconsumed": True,
                "publisher_authorization_consumed": False,
            },
        )
        self.assertEqual(
            (self.module.PARENT_EXPECTED_DEVICE, self.module.PARENT_EXPECTED_INODE),
            (16777233, 1445438),
        )
        self.assertEqual(
            {
                "contract_commit": self.seal["approved_contract_binding_commit"],
                "ack": self.seal["future_acknowledgement_environment_exact"],
                "arguments_forbidden": self.seal["future_arguments_forbidden"],
                "parent": self.seal["future_parent_path_exact"],
                "device": self.seal["future_parent_expected_device_exact"],
                "inode": self.seal["future_parent_expected_inode_exact"],
                "target": self.seal["future_target_path_exact"],
                "exact_blob_only": self.seal["future_execution_from_exact_reviewed_git_blob_only"],
                "admin_root_consumed": self.seal["admin_root_creation_authority_terminally_consumed"],
            },
            {
                "contract_commit": "3021fa1dfe1bf3645ab3ae8d50927df3feaf1dfd",
                "ack": "H27_CREATOR_LEAF_CREATE_EXECUTE=1",
                "arguments_forbidden": True,
                "parent": "/Users/amcarene/h27-admin",
                "device": 16777233,
                "inode": 1445438,
                "target": "/Users/amcarene/h27-admin/creator",
                "exact_blob_only": True,
                "admin_root_consumed": True,
            },
        )
        true_state = {"runner_exists", "admin_root_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in true_state, key)
        for key in (
            "creator_leaf_creation_authority_consumed",
            "runner_externally_reviewed",
            "runner_externally_sealed",
            "parent_observed_by_creator_runner",
            "creator_leaf_observed",
            "creator_leaf_created",
            "publisher_authorization_consumed",
            "source_published",
            "creator_entrypoint_executed",
            "registry_opened",
            "control_bundle_created",
            "science_or_locked_test",
        ):
            self.assertIs(self.seal[key], False, key)

    def test_parent_identity_requires_exact_terminal_tuple(self) -> None:
        directory_mode = 0o040700
        expected = mock.Mock(st_mode=directory_mode, st_dev=16777233, st_ino=1445438)
        wrong_device = mock.Mock(st_mode=directory_mode, st_dev=16777234, st_ino=1445438)
        wrong_inode = mock.Mock(st_mode=directory_mode, st_dev=16777233, st_ino=1445439)
        self.assertTrue(self.module.parent_identity_ok(expected, expected))
        self.assertFalse(self.module.parent_identity_ok(expected, wrong_device))
        self.assertFalse(self.module.parent_identity_ok(expected, wrong_inode))

    def test_synthetic_call_order_has_single_effect(self) -> None:
        calls: list[str] = []

        def mark(name, result=None):
            def action(*args, **kwargs):
                calls.append(name)
                return result
            return action

        with (
            mock.patch.object(self.module, "verify_identity_graph", side_effect=mark("identities", {str(i): b"" for i in range(7)})),
            mock.patch.object(self.module, "require_environment", side_effect=mark("environment")),
            mock.patch.object(self.module, "open_verified_parent", side_effect=mark("open_parent", 17)),
            mock.patch.object(self.module, "probe_target_absence_once", side_effect=mark("probe")),
            mock.patch.object(self.module, "require_parent_fd_still_named", side_effect=mark("parent")),
            mock.patch.object(self.module.os, "mkdir", side_effect=mark("mkdir")),
            mock.patch.object(self.module.os, "fsync", side_effect=mark("fsync")),
            mock.patch.object(self.module, "open_created_leaf", side_effect=mark("open_leaf", 18)),
            mock.patch.object(self.module, "verify_created_leaf", side_effect=mark("verify_leaf", (16777233, 1445500))),
            mock.patch.object(self.module.os, "close", side_effect=mark("close")),
        ):
            result = self.module.create()
        self.assertEqual(
            calls,
            ["identities", "environment", "open_parent", "probe", "parent", "mkdir", "fsync", "open_leaf", "verify_leaf", "parent", "close", "close"],
        )
        self.assertEqual(calls.count("mkdir"), 1)
        self.assertEqual(result["verified_identity_count"], 7)
        self.assertEqual(result["status"], "H27_CREATOR_LEAF_CREATED_TERMINAL_SUCCESS")
        self.assertFalse(result["publisher_authorization_consumed"])


if __name__ == "__main__":
    unittest.main()
