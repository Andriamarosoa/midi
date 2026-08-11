from __future__ import annotations

import ast
from pathlib import Path
import unittest
from unittest import mock

from src.polyphonic.harmonic_censoring_h24 import load_h24_dormant_harness_plan
from src.polyphonic.harmonic_censoring_h24_evidence_producers import (
    H24_EXACT_EVIDENCE_PRODUCERS_IMPLEMENTED,
    H24_EXACT_EVIDENCE_PRODUCER_REGISTRY,
    H24EvidenceProducerContext,
    _FORBIDDEN_RESYNTHESIS_SYMBOLS,
    _NO_RESYNTHESIS_OVERRIDES,
)
from src.polyphonic.harmonic_censoring_h24_operators import (
    recompute_h24_persisted_evidence,
)
from src.polyphonic import harmonic_censoring_h24_scientific_capability as capability
from src.polyphonic import run_harmonic_censoring_h24_scientific as runner


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "src/polyphonic/harmonic_censoring_h24_evidence_producers.py"


class H24EvidenceProducerImplementationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.plan = load_h24_dormant_harness_plan(ROOT)

    def test_registry_is_exact_ordered_72_surface(self) -> None:
        self.assertTrue(H24_EXACT_EVIDENCE_PRODUCERS_IMPLEMENTED)
        self.assertTrue(runner.H24_EVIDENCE_PRODUCER_REGISTRY_IMPLEMENTED)
        self.assertIs(
            runner._H24_EVIDENCE_PRODUCER_REGISTRY,
            H24_EXACT_EVIDENCE_PRODUCER_REGISTRY,
        )
        self.assertEqual(tuple(H24_EXACT_EVIDENCE_PRODUCER_REGISTRY), self.plan.test_ids)
        self.assertEqual(len(H24_EXACT_EVIDENCE_PRODUCER_REGISTRY), 72)
        self.assertTrue(all(callable(item) for item in H24_EXACT_EVIDENCE_PRODUCER_REGISTRY.values()))

    def test_a01_producer_emits_closed_operands_and_recomputer_passes(self) -> None:
        test = self.plan.tests[0]
        evidence = H24_EXACT_EVIDENCE_PRODUCER_REGISTRY[test.test_id](object(), test)
        self.assertEqual(set(evidence), {"primary", "inverse"})
        self.assertNotIn("pass", evidence)
        self.assertNotIn("verdict", evidence)
        outcome = recompute_h24_persisted_evidence(self.plan, test.test_id, evidence)
        self.assertTrue(outcome.primary_pass)
        self.assertTrue(outcome.inverse_pass)

    def test_generic_producer_uses_exact_sealed_schema_without_verdict(self) -> None:
        test = next(item for item in self.plan.tests if item.test_id == "H24-A06")
        context = H24EvidenceProducerContext(np=None, predecessor_context=object())
        evidence = H24_EXACT_EVIDENCE_PRODUCER_REGISTRY[test.test_id](context, test)
        schema = test.as_dict()["evidence_schema"]
        self.assertEqual(
            set(evidence["primary"]), {item["name"] for item in schema["primary_rules"]}
        )
        self.assertEqual(
            set(evidence["inverse"]), {item["name"] for item in schema["inverse_rules"]}
        )
        self.assertFalse({"pass", "passed", "verdict", "final_pass"}.intersection(evidence))
        self.assertTrue(
            recompute_h24_persisted_evidence(self.plan, test.test_id, evidence).final_pass
        )

    def test_import_builds_registry_but_invokes_no_producer(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
        invoked_registry_subscripts = [
            node
            for node in calls
            if isinstance(node.func, ast.Subscript)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "H24_EXACT_EVIDENCE_PRODUCER_REGISTRY"
        ]
        self.assertEqual(invoked_registry_subscripts, [])

    def test_every_reused_predecessor_evaluator_is_statically_resynthesis_free(self) -> None:
        predecessor_path = ROOT / "src/polyphonic/run_harmonic_censoring_h23_synthetic.py"
        tree = ast.parse(predecessor_path.read_text(encoding="utf-8"))
        functions = {
            node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        calls = {
            name: {
                call.func.id
                for call in ast.walk(node)
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
            }
            for name, node in functions.items()
        }

        def reaches_forbidden(name: str, seen: set[str]) -> bool:
            if name in seen:
                return False
            seen.add(name)
            direct = calls.get(name, set())
            return bool(direct.intersection(_FORBIDDEN_RESYNTHESIS_SYMBOLS)) or any(
                reaches_forbidden(callee, seen)
                for callee in direct
                if callee in functions
            )

        required_overrides = {
            name.removeprefix("_measure_")
            for name in functions
            if name.startswith("_measure_") and reaches_forbidden(name, set())
        }
        self.assertEqual(required_overrides, set(_NO_RESYNTHESIS_OVERRIDES))

    def test_h24_override_source_never_calls_resynthesis_symbols(self) -> None:
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        called = {
            node.func.attr
            for node in ast.walk(tree)
            if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == "_h23"
        }
        self.assertFalse(called.intersection(_FORBIDDEN_RESYNTHESIS_SYMBOLS))

    def test_future_authority_binds_all_executable_producer_sources(self) -> None:
        source = (ROOT / "src/polyphonic/harmonic_censoring_h24_scientific_capability.py").read_text(encoding="utf-8")
        for symbol in (
            "H24_PRODUCER_SOURCE_RELATIVE_PATH",
            "H24_PREDECESSOR_RUNNER_SOURCE_RELATIVE_PATH",
            "H24_PREDECESSOR_HARNESS_SOURCE_RELATIVE_PATH",
            "H24_PREDECESSOR_CONTRACT_RELATIVE_PATH",
        ):
            self.assertIn(symbol, source)
        for field in (
            "producer_source_blob",
            "predecessor_runner_source_blob",
            "predecessor_harness_source_blob",
            "predecessor_contract_sha256",
        ):
            self.assertGreaterEqual(source.count(field), 8)

    def test_public_issuer_still_refuses_before_registry_or_population(self) -> None:
        with mock.patch.object(runner, "_require_complete_producer_registry") as registry:
            with self.assertRaisesRegex(PermissionError, "no OS-bound activation"):
                runner.main([])
        registry.assert_not_called()

    def test_dormant_seal_and_activation_files_are_present(self) -> None:
        self.assertTrue((ROOT / capability.H24_SCIENTIFIC_SEAL_RELATIVE_PATH).is_file())
        self.assertTrue((ROOT / capability.H24_SCIENTIFIC_ACTIVATION_RELATIVE_PATH).is_file())


if __name__ == "__main__":
    unittest.main()
