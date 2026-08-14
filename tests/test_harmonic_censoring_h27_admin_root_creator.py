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
RUNNER = ROOT / "scripts/h27_create_admin_root_one_shot.py"
BINDING = ROOT / "configs/harmonic_censoring_h27_admin_root_creator_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_admin_root_creator_identity_binding_external_seal.json"


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
    spec = importlib.util.spec_from_file_location("h27_admin_root_creator_test_subject", RUNNER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


class TestAdminRootCreator(unittest.TestCase):
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
        try:
            self.module.read_blob = local_blob
            verified = self.module.verify_identity_graph()
        finally:
            self.module.read_blob = original_read_blob
        self.assertEqual((len(verified), len(set(verified))), (7, 7))

    def test_exact_one_shot_order_and_dormant_state(self) -> None:
        source = inspect.getsource(self.module.create)
        ordered = [
            "require_environment()",
            "verify_identity_graph()",
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
        safeguards = self.binding["creation_safeguards"]
        self.assertEqual(len(safeguards), 10)
        self.assertTrue(all(safeguards.values()))
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key == "runner_exists", key)
        for key in (
            "runner_externally_reviewed",
            "runner_externally_sealed",
            "parent_observed",
            "target_observed",
            "target_created",
            "publisher_authorization_consumed",
            "creator_child_created",
            "source_published",
            "registry_opened",
            "control_bundle_created",
            "science_or_locked_test",
        ):
            self.assertIs(self.seal[key], False, key)

    def test_synthetic_call_order_has_single_effect(self) -> None:
        calls: list[str] = []

        def mark(name, result=None):
            def action(*args, **kwargs):
                calls.append(name)
                return result
            return action

        with (
            mock.patch.object(self.module, "require_environment", side_effect=mark("environment")),
            mock.patch.object(self.module, "verify_identity_graph", side_effect=mark("identities", {str(i): b"" for i in range(7)})),
            mock.patch.object(self.module, "open_verified_parent", side_effect=mark("open_parent", 17)),
            mock.patch.object(self.module, "probe_target_absence_once", side_effect=mark("probe")),
            mock.patch.object(self.module, "require_parent_fd_still_named", side_effect=mark("parent")),
            mock.patch.object(self.module.os, "mkdir", side_effect=mark("mkdir")),
            mock.patch.object(self.module.os, "fsync", side_effect=mark("fsync")),
            mock.patch.object(self.module, "open_created_leaf", side_effect=mark("open_leaf", 18)),
            mock.patch.object(self.module, "verify_created_leaf", side_effect=mark("verify_leaf", (3, 5))),
            mock.patch.object(self.module.os, "close", side_effect=mark("close")),
        ):
            result = self.module.create()
        self.assertEqual(
            calls,
            ["environment", "identities", "open_parent", "probe", "parent", "mkdir", "fsync", "open_leaf", "verify_leaf", "parent", "close", "close"],
        )
        self.assertEqual(calls.count("mkdir"), 1)
        self.assertEqual(result["verified_identity_count"], 7)
        self.assertEqual(result["status"], "H27_ADMIN_ROOT_CREATED_TERMINAL_SUCCESS")


if __name__ == "__main__":
    unittest.main()
