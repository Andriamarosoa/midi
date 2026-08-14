from __future__ import annotations

import hashlib
import json
from pathlib import Path
import unittest

from tests.test_harmonic_censoring_h27_reviewed_control_bundle_creator_contract import hundred_twenty_six_predecessors

ROOT = Path(__file__).resolve().parents[1]
BINDING = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_contract_identity_binding.json"
SEAL = ROOT / "configs/harmonic_censoring_h27_reviewed_control_bundle_creator_contract_identity_binding_external_seal.json"


def blob(raw: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def check(test: unittest.TestCase, identity: dict[str, object]) -> bytes:
    raw = (ROOT / str(identity["path"])).read_bytes()
    test.assertEqual((identity["git_blob_sha1"], identity["size_bytes"], identity["raw_sha256"]), (blob(raw), len(raw), hashlib.sha256(raw).hexdigest()))
    return raw


def hundred_thirty(contract: dict[str, object]) -> list[dict[str, object]]:
    roots = contract["reviewed_and_sealed_authority_chain"]
    authority_binding = json.loads((ROOT / roots[2]["path"]).read_bytes())
    return [*roots, *hundred_twenty_six_predecessors(authority_binding)]


class TestReviewedCreatorContractIdentityBinding(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.raw = BINDING.read_bytes()
        cls.seal_raw = SEAL.read_bytes()
        cls.binding = json.loads(cls.raw)
        cls.seal = json.loads(cls.seal_raw)

    def test_exact_seal_and_132_identities(self) -> None:
        for raw in (self.raw, self.seal_raw):
            self.assertNotIn(b"\r", raw)
            self.assertFalse(raw.startswith(b"\xef\xbb\xbf"))
            self.assertTrue(raw.endswith(b"\n"))
        check(self, self.seal["identity_binding"])
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        entries = [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *hundred_thirty(contract)]
        self.assertEqual((len(entries), len({entry["path"] for entry in entries})), (132, 132))
        for entry in entries:
            check(self, entry)

    def test_preserved_contract_state_and_edges(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        preserved = self.binding["preserved_contract"]
        definition = contract["future_creator_definition"]
        self.assertEqual(preserved, {
            "static_preflight_step_count": len(contract["future_static_preflight_before_registry_open"]),
            "one_shot_effect_step_count": len(contract["future_one_shot_effect_order"]),
            "bundle_creation_step_count": len(contract["exact_thirteen_bundle_creation_steps"]),
            "creator_rule_count": len(contract["future_creator_rules"]),
            "registry_record_field_count": len(contract["future_registry_jsonl_schema"]["record_exact_top_level_order"]),
            "registry_transition_rule_count": len(contract["future_registry_transition_rules"]),
            "implementation_control_root_exact": definition["implementation_control_root_exact"],
            "implementation_entrypoint_exact": definition["implementation_entrypoint_exact"],
            "implementation_manifest_exact": definition["implementation_manifest_exact"],
            "target_checkout_expected_head_exact": definition["target_checkout_expected_head_exact"],
            "persistent_registry_path_exact": definition["persistent_registry_path_exact"],
            "record_id_byte_exact": True,
            "prior_record_sha_includes_lf": True,
            "all_existing_states_permanently_non_reusable": True,
            "reservation_first_irreversible_effect": True,
            "consumption_before_bundle_observation": True,
            "terminal_no_retry": True,
        })
        self.assertEqual((preserved["static_preflight_step_count"], preserved["one_shot_effect_step_count"], preserved["bundle_creation_step_count"], preserved["creator_rule_count"], preserved["registry_record_field_count"], preserved["registry_transition_rule_count"]), (10, 7, 13, 12, 11, 11))
        allowed = {"creator_contract_exists", "creator_contract_externally_reviewed", "creator_contract_externally_sealed", "creator_contract_identity_binding_exists"}
        for key, value in self.binding["current_state"].items():
            self.assertIs(value, key in allowed, key)
        graph = self.binding["dependency_graph"]
        self.assertTrue(graph["acyclic"] and graph["all_one_hundred_thirty_two_bound_identities_rehashed"])
        self.assertFalse(graph["self_hash_present"] or graph["historical_back_reference_present"])
        self.assertEqual((self.seal["bound_identity_count"], self.seal["static_preflight_step_count"], self.seal["one_shot_effect_step_count"], self.seal["bundle_creation_step_count"], self.seal["creator_rule_count"], self.seal["registry_record_field_count"], self.seal["registry_transition_rule_count"], self.seal["public_edges_closed"]), (132, 10, 7, 13, 12, 11, 11, 8))
        for key in ("creator_implemented", "persistent_registry_opened", "identity_nonce_reserved", "authority_consumed", "bundle_path_observed", "administrative_control_bundle_exists", "filesystem_operation_authorized", "science_or_locked_test"):
            self.assertIs(self.seal[key], False, key)

    def test_no_backrefs(self) -> None:
        contract = json.loads((ROOT / self.binding["reviewed_contract"]["path"]).read_bytes())
        for entry in [self.binding["reviewed_contract"], self.binding["contract_external_seal"], *hundred_thirty(contract)]:
            raw = (ROOT / entry["path"]).read_bytes()
            self.assertNotIn(BINDING.name.encode("ascii"), raw)
            self.assertNotIn(SEAL.name.encode("ascii"), raw)


if __name__ == "__main__":
    unittest.main()
