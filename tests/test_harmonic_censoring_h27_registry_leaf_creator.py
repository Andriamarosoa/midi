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
RUNNER = ROOT / "scripts/h27_create_registry_leaf_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_registry_leaf_creator_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_registry_leaf_creator_identity_binding_external_seal.json"


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
    spec = importlib.util.spec_from_file_location("h27_registry_leaf_creator_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestRegistryLeafCreator(unittest.TestCase):
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
        identities = [self.binding["runner"], *self.binding["approved_contract_chain"], *self.binding["transitive_contract_identities"]]
        self.assertEqual((len(identities), len({item["path"] for item in identities})), (8, 8))
        for identity in identities[1:]:
            check(self, identity)
        self.assertEqual(self.binding["runner"], self.seal["runner"])

    def test_exact_seven_identity_git_blob_preflight(self) -> None:
        def local_blob(blob_sha1: str) -> bytes:
            return subprocess.run(["git", "cat-file", "blob", blob_sha1], cwd=ROOT, check=True, stdout=subprocess.PIPE).stdout

        with (
            mock.patch.object(self.module, "read_blob", side_effect=local_blob),
            mock.patch.object(self.module, "require_git_database"),
        ):
            verified = self.module.verify_identity_graph()
        self.assertEqual((len(verified), len(set(verified))), (7, 7))
        source = inspect.getsource(self.module.verify_identity_graph)
        self.assertLess(source.index("require_git_database()"), source.index("read_blob("))

    def test_exact_binding_order_and_dormant_state(self) -> None:
        source = inspect.getsource(self.module.create)
        ordered = [
            "verify_identity_graph()", "require_environment()", "open_verified_parent()",
            "probe_target_absence_once(parent_fd)", "require_parent_fd_still_named(parent_fd)",
            "os.mkdir(TARGET_LEAF, mode=0o700, dir_fd=parent_fd)", "os.fsync(parent_fd)",
            "open_created_leaf(parent_fd)", "verify_created_leaf(parent_fd, leaf_fd)",
        ]
        positions = [source.index(token) for token in ordered] + [source.rindex("require_parent_fd_still_named(parent_fd)")]
        self.assertEqual(positions, sorted(positions))
        self.assertEqual(source.count("os.mkdir("), 1)
        self.assertNotIn("rmtree", source)
        self.assertNotIn("unlink", source)
        self.assertEqual(self.binding["execution_binding"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_REGISTRY_LEAF_CREATE_EXECUTE=1",
            "arguments_forbidden": True,
            "git_object_database_exact": "/Users/amcarene/midi-worker/repository/.git",
            "parent_path_exact": "/Users/amcarene/h27-admin",
            "parent_expected_device_exact": 16777233,
            "parent_expected_inode_exact": 1445438,
            "parent_fd_and_named_entry_must_match_terminal_identity": True,
            "target_leaf_exact": "registry",
            "target_path_exact": "/Users/amcarene/h27-admin/registry",
            "execution_from_exact_reviewed_git_blob_only": True,
            "checkout_or_worktree_fallback_forbidden": True,
        })
        self.assertEqual(self.binding["identity_graph"], {
            "combined_unique_path_count_including_runner": 8,
            "runner_rehashes_seven_predecessor_identities_before_parent_observation": True,
            "duplicates_forbidden": True,
            "path_or_identity_drift_forbidden": True,
            "acyclic": True,
            "self_hash_present": False,
        })
        self.assertEqual(self.binding["creation_safeguards"], {
            "all_seven_predecessor_identities_rehashed_before_parent_observation": True,
            "parent_opened_o_nofollow_and_anchored_by_verified_dirfd": True,
            "parent_fd_and_named_entry_match_terminal_device_inode_before_probe_effect_and_success": True,
            "single_target_absence_probe_relative_to_parent_dirfd": True,
            "exact_leaf_mkdir_first_and_only_irreversible_effect": True,
            "mkdir_parents_forbidden": True,
            "parent_fsynced_after_creation": True,
            "created_leaf_opened_o_nofollow_and_inode_device_verified": True,
            "cleanup_retry_repair_or_recreation_forbidden": True,
            "registry_jsonl_creator_entrypoint_bundle_constructor_materializer_and_science_forbidden": True,
        })
        self.assertEqual(self.binding["authority_state"], {
            "admin_root_creation_authority_terminally_consumed": True,
            "admin_root_creator_retry_forbidden": True,
            "publisher_authority_terminally_consumed": True,
            "publisher_retry_forbidden": True,
            "registry_leaf_creation_authority_unconsumed": True,
        })
        self.assertEqual((self.module.PARENT_EXPECTED_DEVICE, self.module.PARENT_EXPECTED_INODE), (16777233, 1445438))
        true_state = {"runner_exists", "admin_root_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in true_state, key)
        seal_true = {
            "future_arguments_forbidden", "future_execution_from_exact_reviewed_git_blob_only",
            "admin_root_creation_authority_terminally_consumed", "publisher_authority_terminally_consumed",
        }
        for key, value in self.seal.items():
            if isinstance(value, bool):
                self.assertIs(value, key in seal_true, key)
        self.assertEqual(self.seal, {
            "schema_version": 1,
            "seal_id": "H27_REGISTRY_LEAF_ONE_SHOT_CREATOR_IDENTITY_BINDING_EXTERNAL_SEAL_V1",
            "status": "SEALED_PENDING_EXTERNAL_REVIEW_RUNNER_DORMANT_NO_FILESYSTEM_NO_REGISTRY_OPEN_NO_BUNDLE_NO_SCIENCE",
            "identity_binding": {
                "path": "configs/harmonic_censoring_h27_registry_leaf_creator_identity_binding.json",
                "git_blob_sha1": "e2b18cf3c2d10ee3ee1f898038548717dd748b9b",
                "size_bytes": 5253,
                "raw_sha256": "397f7ff3ce1d8c6f2f3cba3620814e7a502325ea13a45db246460a273e35ae79",
            },
            "runner": {
                "path": "scripts/h27_create_registry_leaf_one_shot.py",
                "git_blob_sha1": "ca93c383d8cc61a6f3869318f1e462ab82a1c92a",
                "size_bytes": 11186,
                "raw_sha256": "589950570a4ad30c8953f568a6df9a3027ce64d2abab62bd817c48f8b62a729c",
            },
            "approved_contract_binding_commit": "c18ec0632e23edeca59816246c947a585f918af4",
            "future_acknowledgement_environment_exact": "H27_REGISTRY_LEAF_CREATE_EXECUTE=1",
            "future_arguments_forbidden": True,
            "future_parent_path_exact": "/Users/amcarene/h27-admin",
            "future_parent_expected_device_exact": 16777233,
            "future_parent_expected_inode_exact": 1445438,
            "future_target_path_exact": "/Users/amcarene/h27-admin/registry",
            "future_execution_from_exact_reviewed_git_blob_only": True,
            "admin_root_creation_authority_terminally_consumed": True,
            "publisher_authority_terminally_consumed": True,
            "registry_leaf_creation_authority_consumed": False,
            "runner_externally_reviewed": False,
            "runner_externally_sealed": False,
            "parent_observed_by_registry_runner": False,
            "registry_leaf_observed": False,
            "registry_leaf_created": False,
            "registry_jsonl_observed": False,
            "registry_opened": False,
            "authority_reserved": False,
            "authority_consumed": False,
            "creator_entrypoint_executed": False,
            "control_bundle_created": False,
            "constructor_or_materializer_executed": False,
            "science_or_locked_test": False,
            "next_action": "External review of the exact dormant registry-leaf runner, identity binding and seal only",
        })

    def test_parent_identity_requires_exact_terminal_tuple(self) -> None:
        mode = 0o040700
        expected = mock.Mock(st_mode=mode, st_dev=16777233, st_ino=1445438)
        wrong_device = mock.Mock(st_mode=mode, st_dev=16777234, st_ino=1445438)
        wrong_inode = mock.Mock(st_mode=mode, st_dev=16777233, st_ino=1445439)
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
            mock.patch.object(self.module, "verify_created_leaf", side_effect=mark("verify_leaf", (16777233, 1445600))),
            mock.patch.object(self.module.os, "close", side_effect=mark("close")),
        ):
            result = self.module.create()
        self.assertEqual(calls, ["identities", "environment", "open_parent", "probe", "parent", "mkdir", "fsync", "open_leaf", "verify_leaf", "parent", "close", "close"])
        self.assertEqual(calls.count("mkdir"), 1)
        self.assertEqual(result["verified_identity_count"], 7)
        self.assertEqual(result["status"], "H27_REGISTRY_LEAF_CREATED_TERMINAL_SUCCESS")
        self.assertFalse(result["registry_jsonl_observed"])
        self.assertFalse(result["registry_opened"])


if __name__ == "__main__":
    unittest.main()
