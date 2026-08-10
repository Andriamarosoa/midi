import hashlib
import json
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs"
SUCCESSOR = CONFIG / "harmonic_censoring_h24_successor_contract.json"
POPULATION = CONFIG / "harmonic_censoring_h24_population_manifest.json"
TESTS = CONFIG / "harmonic_censoring_h24_test_manifest.json"
BINDING = CONFIG / "harmonic_censoring_h24_manifest_binding_contract.json"


def load(path):
    raw = path.read_bytes()
    return raw, json.loads(raw.decode("utf-8"))


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class HarmonicCensoringH24ManifestContractsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.successor_raw, cls.successor = load(SUCCESSOR)
        cls.population_raw, cls.population = load(POPULATION)
        cls.tests_raw, cls.tests = load(TESTS)
        cls.binding_raw, cls.binding = load(BINDING)

    def test_all_files_are_canonical_UTF8_LF_JSON(self):
        for raw, payload in (
            (self.population_raw, self.population),
            (self.tests_raw, self.tests),
            (self.binding_raw, self.binding),
        ):
            self.assertNotIn(b"\r", raw)
            self.assertTrue(raw.endswith(b"\n"))
            self.assertEqual(
                raw,
                (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8"),
            )

    def test_binding_hashes_exact_bytes(self):
        self.assertEqual(
            self.binding["H24_successor_contract"]["sha256"], digest(self.successor_raw)
        )
        self.assertEqual(
            self.binding["H24_population_manifest"]["sha256"], digest(self.population_raw)
        )
        self.assertEqual(
            self.binding["H24_test_manifest"]["sha256"], digest(self.tests_raw)
        )
        self.assertEqual(
            self.tests["H24_population_manifest_sha256"], digest(self.population_raw)
        )

    def test_population_cardinality_is_explicitly_rederived(self):
        derivation = self.population["derivation"]
        self.assertEqual(derivation["base_specification_count"], 6)
        self.assertEqual(derivation["one_factor_variant_specification_count"], 169)
        self.assertEqual(derivation["derived_total_specification_count"], 175)
        self.assertEqual(derivation["cardinality_equation"], "6+169=175")
        self.assertTrue(
            derivation["same_numeric_count_as_H23_is_incidental_to_explicit_rederivation"]
        )
        self.assertEqual(self.population["fixture_count"], 175)

    def test_population_ids_specs_and_seeds_are_new_and_bijective(self):
        records = self.population["fixture_specifications"]
        ids = [record["fixture_id"] for record in records]
        old_ids = [record["predecessor_fixture_id"] for record in records]
        self.assertEqual(ids, self.population["fixture_ids"])
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(old_ids), len(set(old_ids)))
        self.assertTrue(all(item.startswith("H24-F-") for item in ids))
        self.assertTrue(set(ids).isdisjoint(old_ids))
        for record in records:
            expected_seed = int.from_bytes(
                hashlib.sha256(("H24|" + record["fixture_id"]).encode()).digest()[:8],
                "little",
                signed=False,
            )
            self.assertEqual(record["synthesis_seed"], expected_seed)
            self.assertFalse(record["waveform_synthesized"])
            self.assertFalse(record["scientific_outcome_present"])
            self.assertTrue(record["specification_re_preregistered_not_outcome_inherited"])

    def test_population_scope_is_zero_science(self):
        scope = dict(self.population["scope"])
        self.assertTrue(scope.pop("manifest_contract_only"))
        self.assertTrue(all(value is False for value in scope.values()))

    def test_test_count_is_question_by_question_rederived(self):
        derivation = self.tests["derivation"]
        self.assertEqual(derivation["new_graph_direction_test_count"], 1)
        self.assertEqual(derivation["other_scientific_questions_re_preregistered_count"], 71)
        self.assertEqual(derivation["derived_total_test_count"], 72)
        self.assertEqual(derivation["cardinality_equation"], "1+71=72")
        self.assertTrue(derivation["predecessor_outcomes_are_never_inputs"])
        self.assertEqual(self.tests["phase_counts"], {"P0": 27, "P1": 35, "P2": 10})
        self.assertEqual(self.tests["test_count"], 72)

    def test_test_ids_namespaces_phases_and_records_are_closed(self):
        records = self.tests["tests"]
        ids = [record["id"] for record in records]
        self.assertEqual(ids, self.tests["test_ids"])
        self.assertEqual(ids[0], "H24-A01-GRAPH-DIRECTION")
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue(all(item.startswith("H24-") for item in ids))
        self.assertTrue(all(record["namespace"] == "H24_TEST_V1" for record in records))
        self.assertTrue(all(record["outcome_carried_forward"] is False for record in records))
        self.assertTrue(all(record["producer_pass_boolean_allowed"] is False for record in records))
        self.assertTrue(all(record["implementation_exists"] is False for record in records))
        self.assertTrue(all(record["test_executed"] is False for record in records))
        self.assertTrue(all("pass_rule_boolean" not in record["metrics"] for record in records))
        for phase in ("P0", "P1", "P2"):
            self.assertEqual(
                self.tests["phase_test_ids"][phase],
                [record["id"] for record in records if record["phase"] == phase],
            )

    def test_every_test_has_explicit_evidence_schema(self):
        for record in self.tests["tests"]:
            schema = record["evidence_schema"]
            self.assertTrue(schema)
            if record["id"] == "H24-A01-GRAPH-DIRECTION":
                self.assertIn("typed_edges", schema["primary_required_fields"])
                self.assertEqual(len(schema["inverse_required_fields"]), 7)
            else:
                self.assertTrue(schema["primary_rules"])
                self.assertTrue(schema["inverse_rules"])
                self.assertTrue(schema["producer_verdict_field_forbidden"])
                self.assertTrue(schema["independent_recomputation_required"])

    def test_fixture_references_resolve_only_into_H24_population(self):
        references = self.tests["fixture_reference_contract"]
        self.assertEqual(
            references["conceptual_base_aliases"],
            {key: "H24-F-" + key for key in ("S1C", "S1P", "S2", "S3", "S4", "S5")},
        )
        self.assertTrue(
            references["all_resolved_fixture_references_must_exist_in_bound_population_manifest"]
        )
        self.assertTrue(references["free_text_does_not_authorize_unlisted_fixture"])
        self.assertTrue(references["predecessor_waveform_or_outcome_reuse_forbidden"])

    def test_kill_rules_are_closed_and_never_authorize_training(self):
        rules = self.tests["kill_rules"]
        self.assertEqual(rules["P0_first_failure"], "H24_SYNTHETIC_HYPOTHESIS_KILLED")
        self.assertEqual(
            rules["P1_or_P2_first_failure"],
            "H24_PRETRAIN_READINESS_NOT_DEMONSTRATED",
        )
        self.assertTrue(rules["stop_at_first_failure"])
        self.assertEqual(
            rules["success_status"], "AUTHORIZED_TO_PREPARE_H24_TRAIN_PROTOCOL"
        )
        self.assertTrue(rules["success_never_means_training_authorized"])

    def test_binding_authorizes_only_contract_definition(self):
        authorization = dict(self.binding["authorization"])
        self.assertTrue(authorization.pop("manifest_and_test_plan_definition_authorized"))
        self.assertTrue(all(value is False for value in authorization.values()))
        self.assertEqual(
            self.binding["next_action"],
            "external_review_of_H24_manifests_and_full_test_plan_only",
        )


if __name__ == "__main__":
    unittest.main()
