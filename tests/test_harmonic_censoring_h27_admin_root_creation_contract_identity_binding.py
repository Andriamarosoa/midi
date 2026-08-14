from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_admin_root_creation_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_admin_root_creation_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual(
        (identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]),
        (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()),
    )
    return raw


class TestH27AdminRootCreationContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_binding_seal_and_five_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        entries = [
            self.binding["reviewed_contract"],
            self.binding["contract_external_seal"],
            *self.binding["reviewed_predecessor_chain"],
        ]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (5, 5))
        for entry in entries:
            check(self, entry)
        self.assertEqual(self.binding["reviewed_contract"]["reviewed_commit"], "20f43758b6349ce7de9aa8503a3a6e81334cd36a")
        self.assertEqual(self.binding["reviewed_contract"]["external_review_verdict"], "PASS")

    def test_closed_binding_and_future_runner_boundary(self) -> None:
        self.assertEqual(self.binding["transitive_identity_binding"], {
            "combined_unique_path_count": 5,
            "all_five_identities_must_be_rehashed": True,
            "duplicates_forbidden": True,
            "path_or_identity_drift_forbidden": True,
        })
        self.assertEqual(self.binding["bound_future_root"], {
            "platform_exact": "darwin",
            "acknowledgement_environment_exact": "H27_ADMIN_ROOT_CREATE_EXECUTE",
            "acknowledgement_value_exact": "1",
            "arguments_forbidden": True,
            "parent_path_exact": "/Users/amcarene",
            "target_leaf_exact": "h27-admin",
            "target_path_exact": "/Users/amcarene/h27-admin",
        })
        self.assertEqual(self.binding["preserved_future_runner_boundary"], {
            "distinct_later_commit_required": True,
            "external_review_pass_required": True,
            "exact_identity_binding_required": True,
            "external_identity_binding_seal_required": True,
            "execution_from_exact_reviewed_git_blob_bytes_only": True,
            "current_checkout_or_worktree_file_fallback_forbidden": True,
            "runner_forbidden_in_current_stage": True,
        })
        self.assertEqual(
            (self.seal["bound_unique_identity_count"], self.seal["future_acknowledgement_environment_exact"], self.seal["future_acknowledgement_value_exact"], self.seal["parent_path_exact"], self.seal["target_path_exact"]),
            (5, "H27_ADMIN_ROOT_CREATE_EXECUTE", "1", "/Users/amcarene", "/Users/amcarene/h27-admin"),
        )

    def test_dormant_state_and_no_back_reference(self) -> None:
        allowed = {"contract_exists", "contract_externally_reviewed", "contract_externally_sealed", "identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        for key in (
            "identity_binding_externally_reviewed",
            "runner_exists",
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
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_five_bound_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        for identity in [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *self.binding["reviewed_predecessor_chain"]]:
            raw = (ROOT / identity["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
