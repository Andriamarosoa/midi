import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "configs" / "harmonic_censoring_h24_successor_contract.json"


class HarmonicCensoringH24SuccessorContractTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.raw = CONTRACT_PATH.read_bytes()
        cls.contract = json.loads(cls.raw.decode("utf-8"))

    def test_contract_is_canonical_json_with_lf(self):
        self.assertNotIn(b"\r", self.raw)
        self.assertTrue(self.raw.endswith(b"\n"))
        self.assertEqual(
            self.raw,
            (json.dumps(self.contract, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
        )
        self.assertEqual(len(hashlib.sha256(self.raw).hexdigest()), 64)

    def test_scope_is_contract_only(self):
        scope = self.contract["scope"]
        self.assertTrue(scope["contract_only"])
        for key, value in scope.items():
            if key != "contract_only":
                self.assertFalse(value, key)

    def test_H23_is_terminal_and_cannot_be_reused(self):
        closed = self.contract["predecessor_closure"]
        self.assertEqual(closed["terminal_status"], "H23_SYNTHETIC_HYPOTHESIS_KILLED")
        self.assertEqual(closed["terminal_test_id"], "A01")
        self.assertTrue(closed["synthetic_population_consumed"])
        self.assertTrue(closed["retry_forbidden"])
        self.assertTrue(closed["reinterpretation_forbidden"])
        identity = self.contract["successor_identity"]
        self.assertEqual(identity["hypothesis_name"], "H24")
        self.assertTrue(identity["must_not_reuse_H23_population_ids"])
        self.assertTrue(identity["must_not_reuse_H23_test_ids"])
        self.assertFalse(identity["current_population_manifest_exists"])
        self.assertFalse(identity["current_test_manifest_exists"])

    def test_H1_is_identity_not_a_proper_harmonic_edge(self):
        relations = self.contract["harmonic_graph_semantics"]["relation_partition"]
        identity = relations["fundamental_reflexive_relation"]
        proper = relations["proper_harmonic_relation"]
        self.assertEqual(identity["rank"], 1)
        self.assertEqual(identity["required_invariant"], "q(p,1)==p")
        self.assertFalse(identity["is_proper_harmonic_edge"])
        self.assertFalse(identity["is_ascending_edge"])
        self.assertEqual(proper["rank_minimum"], 2)
        self.assertEqual(proper["rank_maximum"], 20)
        self.assertEqual(proper["required_invariant"], "q(p,h)>p")
        self.assertTrue(proper["is_proper_harmonic_edge"])
        self.assertTrue(proper["is_ascending_edge"])

    def test_edge_schema_preserves_rank_and_type(self):
        graph = self.contract["harmonic_graph_semantics"]
        self.assertEqual(
            graph["edge_record_schema"],
            ["source_pitch", "harmonic_rank", "observation_coordinate", "relation_type"],
        )
        self.assertTrue(graph["edge_record_extra_fields_forbidden"])
        self.assertIn("C4 never explains C3", graph["graph_invariants"])

    def test_successor_A01_has_primary_and_four_distinct_inverses(self):
        test = self.contract["first_successor_test_contract"]
        self.assertEqual(test["id"], "H24-A01-GRAPH-DIRECTION")
        self.assertEqual(test["phase"], "P0")
        self.assertEqual(
            test["primary_oracle"],
            {
                "all_H1_relations_are_identity": True,
                "all_H2_to_H20_relations_are_strictly_ascending": True,
                "no_relation_is_descending": True,
                "C4_to_C3_relation_count": 0,
            },
        )
        inverses = test["inverse_mutations"]
        self.assertEqual([item["id"] for item in inverses], [
            "H24-A01-I1", "H24-A01-I2", "H24-A01-I3", "H24-A01-I4"
        ])
        self.assertTrue(all(item["required_result"] == "FAIL" for item in inverses))
        self.assertTrue(test["producer_pass_boolean_forbidden"])
        self.assertTrue(test["oracle_must_recompute_from_persisted_typed_edges"])

    def test_no_manifest_or_execution_is_authorized(self):
        forbidden = set(self.contract["forbidden_now"])
        self.assertIn("creating_H24_waveforms", forbidden)
        self.assertIn("creating_H24_fixture_or_test_manifests", forbidden)
        self.assertIn("implementing_H24_evaluators_or_oracles", forbidden)
        self.assertIn("running_any_H24_test", forbidden)
        self.assertIn("locked_test", forbidden)
        self.assertEqual(
            self.contract["next_action"], "external_review_of_this_contract_only"
        )


if __name__ == "__main__":
    unittest.main()
