import hashlib
import json
from copy import deepcopy
import math
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


def validate_closed_test_plan(test_plan, population, binding):
    population_ids = population["fixture_ids"]
    population_id_set = set(population_ids)
    operator_contract = test_plan["evidence_operator_contract"]
    operator_registry = operator_contract["operator_registry"]
    sentinel_registry = operator_contract["sentinel_registry"]
    operators_used = set()
    for record in test_plan["tests"]:
        selection = record["fixture_selection"]
        assert set(selection).issubset(
            {
                "mode",
                "profile_name_for_audit_only",
                "resolved_fixture_ids",
                "text_fields_must_not_change_selection",
                "all_ids_must_exist_in_bound_population_manifest",
                "empty_selection_reason",
            }
        )
        assert selection["mode"] == "EXACT_IDS"
        resolved = selection["resolved_fixture_ids"]
        assert type(resolved) is list
        assert len(resolved) == len(set(resolved))
        assert all(type(item) is str and item in population_id_set for item in resolved)
        assert selection["text_fields_must_not_change_selection"] is True
        assert selection["all_ids_must_exist_in_bound_population_manifest"] is True
        if not resolved:
            assert type(selection.get("empty_selection_reason")) is str
            assert selection["empty_selection_reason"]
        elif "empty_selection_reason" in selection:
            raise AssertionError("nonempty fixture selection cannot carry an empty reason")
        if record["id"] == "H24-A01-GRAPH-DIRECTION":
            continue
        schema = record["evidence_schema"]
        for side in ("primary_rules", "inverse_rules"):
            for rule in schema[side]:
                assert set(rule) == {"name", "operator", "expected", "rtol", "atol"}
                assert type(rule["name"]) is str and rule["name"]
                operator = rule["operator"]
                assert operator in operator_registry
                operators_used.add(operator)
                assert type(rule["rtol"]) in (int, float)
                assert type(rule["atol"]) in (int, float)
                assert math.isfinite(float(rule["rtol"])) and rule["rtol"] >= 0
                assert math.isfinite(float(rule["atol"])) and rule["atol"] >= 0
                if not operator_registry[operator]["uses_rtol_atol"]:
                    assert rule["rtol"] == 0.0 and rule["atol"] == 0.0
                expected = rule.get("expected")
                if type(expected) is str and expected.startswith("__"):
                    assert expected in sentinel_registry
    assert operators_used == set(operator_registry)
    assert set(sentinel_registry) == {"__PLAN_FIXTURE_IDS__"}
    assert operator_contract["closed_world"] is True
    assert operator_contract["unknown_operator_or_sentinel"] == "FAIL_BEFORE_EVALUATION"

    transition = binding["successor_snapshot_transition"]
    assert transition["successor_snapshot_sha256"] == digest(
        json.dumps(
            json.loads(SUCCESSOR.read_text(encoding="utf-8")),
            indent=2,
            ensure_ascii=False,
        ).encode("utf-8")
        + b"\n"
    )
    assert transition["successor_snapshot_state"] == {
        "population_manifest_exists": False,
        "test_manifest_exists": False,
        "meaning": "historical state at approval of the immutable successor snapshot",
    }
    assert transition["bound_manifest_state_after_this_contract"] == {
        "population_manifest_defined": True,
        "test_manifest_defined": True,
        "population_materialized": False,
        "evaluators_implemented": False,
        "oracles_implemented": False,
        "tests_executed": False,
    }
    assert transition["retroactive_mutation_of_successor_forbidden"] is True


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

    def test_operator_and_sentinel_registry_is_exactly_closed(self):
        validate_closed_test_plan(self.tests, self.population, self.binding)
        contract = self.tests["evidence_operator_contract"]
        self.assertEqual(len(contract["operator_registry"]), 27)
        self.assertEqual(set(contract["sentinel_registry"]), {"__PLAN_FIXTURE_IDS__"})
        self.assertEqual(
            contract["primitive_contract"]["strict_equal"]["NaN_or_infinity"],
            "FAIL_BEFORE_COMPARISON",
        )
        self.assertFalse(
            contract["primitive_contract"]["finite_numeric"]["boolean_accepted"]
        )

    def test_unknown_or_missing_operator_and_sentinel_are_rejected(self):
        missing = deepcopy(self.tests)
        missing["evidence_operator_contract"]["operator_registry"].pop("eq")
        with self.assertRaises(AssertionError):
            validate_closed_test_plan(missing, self.population, self.binding)

        unknown = deepcopy(self.tests)
        unknown["tests"][1]["evidence_schema"]["primary_rules"][0][
            "operator"
        ] = "unknown_operator"
        with self.assertRaises(AssertionError):
            validate_closed_test_plan(unknown, self.population, self.binding)

        sentinel = deepcopy(self.tests)
        sentinel["tests"][1]["evidence_schema"]["primary_rules"][0][
            "expected"
        ] = "__UNKNOWN_SENTINEL__"
        with self.assertRaises(AssertionError):
            validate_closed_test_plan(sentinel, self.population, self.binding)

    def test_every_test_has_exact_machine_readable_fixture_selection(self):
        population_ids = set(self.population["fixture_ids"])
        self.assertEqual(len(self.tests["tests"]), 72)
        for record in self.tests["tests"]:
            selection = record["fixture_selection"]
            self.assertEqual(selection["mode"], "EXACT_IDS")
            resolved = selection["resolved_fixture_ids"]
            self.assertEqual(len(resolved), len(set(resolved)))
            self.assertTrue(set(resolved).issubset(population_ids))
            self.assertTrue(selection["text_fields_must_not_change_selection"])
            if not resolved:
                self.assertTrue(selection["empty_selection_reason"])
        self.assertEqual(
            next(record for record in self.tests["tests"] if record["id"] == "H24-I01")[
                "fixture_selection"
            ]["resolved_fixture_ids"],
            self.population["fixture_ids"],
        )

    def test_fixture_selection_mutations_are_rejected(self):
        unknown = deepcopy(self.tests)
        unknown["tests"][0]["fixture_selection"]["resolved_fixture_ids"] = [
            "H24-F-NOT-BOUND"
        ]
        with self.assertRaises(AssertionError):
            validate_closed_test_plan(unknown, self.population, self.binding)

        unexplained_empty = deepcopy(self.tests)
        unexplained_empty["tests"][0]["fixture_selection"].pop(
            "empty_selection_reason"
        )
        with self.assertRaises(AssertionError):
            validate_closed_test_plan(unexplained_empty, self.population, self.binding)

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
        self.assertTrue(
            references["every_test_has_machine_readable_exact_fixture_selection"]
        )
        self.assertTrue(
            references[
                "selection_is_never_inferred_from_exact_input_procedure_or_other_free_text"
            ]
        )

    def test_successor_snapshot_transition_is_explicit_and_adversarially_closed(self):
        validate_closed_test_plan(self.tests, self.population, self.binding)
        mutated = deepcopy(self.binding)
        mutated["successor_snapshot_transition"][
            "bound_manifest_state_after_this_contract"
        ]["population_manifest_defined"] = False
        with self.assertRaises(AssertionError):
            validate_closed_test_plan(self.tests, self.population, mutated)

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
            "external_review_of_corrected_H24_manifests_and_full_test_plan_only",
        )


if __name__ == "__main__":
    unittest.main()
