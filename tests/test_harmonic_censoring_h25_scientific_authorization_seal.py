import json
import os
from pathlib import Path
import sys
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h25_secondary_runtime_observer as observer
from src.polyphonic import harmonic_censoring_h25_scientific_capability as capability
from src.polyphonic import run_harmonic_censoring_h25_scientific as runner


ROOT = Path(__file__).resolve().parents[1]
OBSERVER = ROOT / "src/polyphonic/harmonic_censoring_h25_secondary_runtime_observer.py"
PROJECTION = (
    ROOT / "configs/harmonic_censoring_h25_p2_007_nonrecursive_projection_contract.json"
)


class H25P2007CorrectionDormantTests(unittest.TestCase):
    def test_projection_contract_is_explicit_finite_and_true_cross_runtime(self) -> None:
        contract = json.loads(PROJECTION.read_text(encoding="utf-8"))
        records = contract["ordered_test_records"]
        runtime = contract["runtime_observation"]
        self.assertEqual(records["count"], 27)
        self.assertEqual(records["ordinary_record_count"], 26)
        self.assertEqual(
            records["P2_007_record_kind"],
            "H25_P2_007_NONRECURSIVE_SELF_CORE_V1",
        )
        self.assertEqual(
            set(records["P2_007_excluded_recursive_fields"]),
            {"current_runtime_observation", "cross_runtime_observation", "test_records"},
        )
        self.assertTrue(records["minimal_identity_only_seed_records_forbidden"])
        self.assertTrue(runtime["current_and_secondary_scientific_runtime_ids_must_differ"])
        self.assertTrue(runtime["transport_difference_alone_never_satisfies_cross_runtime"])

    def test_observer_is_dormant_before_contract_runtime_claim_numpy_or_population(self) -> None:
        self.assertFalse((ROOT / capability.AUTHORIZATION_SEAL).exists())
        self.assertFalse((ROOT / capability.ACTIVATION_RECORD).exists())
        source = OBSERVER.read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        numpy_before = sys.modules.get("numpy")
        with mock.patch.object(observer, "_validate_dormant_contract") as contract, mock.patch.object(
            observer, "_require_secondary_runtime_before_numpy"
        ) as runtime, mock.patch.object(observer, "_claim_marker") as claim, mock.patch.object(
            observer, "_load_context_after_claim"
        ) as population:
            with self.assertRaisesRegex(PermissionError, "seal and activation are absent"):
                observer.run_h25_secondary_runtime_observer(ROOT)
        contract.assert_not_called()
        runtime.assert_not_called()
        claim.assert_not_called()
        population.assert_not_called()
        self.assertIs(sys.modules.get("numpy"), numpy_before)

    def test_runner_uses_nonrecursive_self_projection_without_minimal_seed(self) -> None:
        source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn("def _p2_007_self_record", source)
        self.assertIn("recompute_h25_p2_007_self_record", source)
        self.assertNotIn("seed = MappingProxyType", source)
        self.assertNotIn('"status": "PASS"', source)
        observer_source = OBSERVER.read_text(encoding="utf-8")
        self.assertIn("_derive_recomputed_runtime_test_records(context, identity)", observer_source)
        self.assertIn("observed_test_records=records", observer_source)

    def test_scientific_and_transport_identity_are_separate_in_code(self) -> None:
        capability_source = Path(capability.__file__).read_text(encoding="utf-8")
        self.assertIn('{"scientific_runtime", "transport"}', capability_source)
        self.assertIn("_require_secondary_runtime_before_numpy", capability_source)
        runner_source = Path(runner.__file__).read_text(encoding="utf-8")
        self.assertIn('_canonical(identity["scientific_runtime"])', runner_source)
        self.assertIn('_canonical(identity["transport"])', runner_source)

    def test_current_tree_remains_preseal_pre_activation_and_zero_science(self) -> None:
        contract = json.loads((ROOT / capability.CAPABILITY_CONTRACT).read_text(encoding="utf-8"))
        self.assertFalse((ROOT / capability.AUTHORIZATION_SEAL).exists())
        self.assertFalse((ROOT / capability.ACTIVATION_RECORD).exists())
        self.assertIsNone(os.environ.get(capability.AUTHORIZATION_COMMIT_ENV))
        self.assertIsNone(os.environ.get(capability.AUTHORIZATION_SEAL_SHA256_ENV))
        self.assertFalse(contract["scope"]["scientific_capability_emitted_now"])
        self.assertFalse(contract["scope"]["scientific_claim_created_now"])
        self.assertEqual(contract["scope"]["P0_P1_P2_executed_counts"], [0, 0, 0])
        for name in (
            "claim_path", "staging_directory", "success_directory",
            "terminal_path", "forensic_terminal_path",
        ):
            self.assertFalse((ROOT / contract["one_shot_execution"][name]).exists())


if __name__ == "__main__":
    unittest.main()
