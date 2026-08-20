from __future__ import annotations

import ast
import copy
import hashlib
from pathlib import Path
import pickle
import unittest

from src.polyphonic import harmonic_censoring_h28_materializer_dormant as materializer
from src.polyphonic import harmonic_censoring_h28_timing_contract as timing
from src.polyphonic.harmonic_censoring_h28_timing_contract import RECORD_ORDER


ROOT = Path(__file__).resolve().parents[1]


def _function_ast(source: str, name: str) -> str:
    node = next(
        item for item in ast.parse(source).body
        if isinstance(item, ast.FunctionDef) and item.name == name
    )
    return ast.dump(node, include_attributes=False)


class _ExplodingDependency:
    def __getattribute__(self, name: str) -> object:
        raise AssertionError(f"materialization dependency was touched: {name}")


class H28DormantMaterializerTests(unittest.TestCase):
    def test_byte_exact_materializer_contract(self):
        path = ROOT / "configs/harmonic_censoring_h28_materializer_dormant_contract.json"
        raw = path.read_bytes()
        self.assertEqual(
            hashlib.sha256(raw).hexdigest(),
            "09e704b1171b48fc64cb537149113d600322e52a3aac825c4b4cf1e87dff01ef",
        )
        document = timing._strict_json(raw, label="H28 dormant materializer contract")
        self.assertEqual(document["schema_identity"], "H28_DORMANT_MATERIALIZER_DESIGN_V1")
        binding = document["implementation_binding"]
        implementation = (ROOT / binding["path"]).read_bytes()
        blob = hashlib.sha1(
            b"blob " + str(len(implementation)).encode("ascii") + b"\0" + implementation
        ).hexdigest()
        self.assertEqual(len(implementation), binding["size_bytes"])
        self.assertEqual(hashlib.sha256(implementation).hexdigest(), binding["sha256"])
        self.assertEqual(blob, binding["git_blob"])
        self.assertTrue(all(
            value is False for value in document["authorization_boundary"].values()
        ))

    def test_materialization_capability_has_no_issuer_copy_or_pickle_path(self):
        with self.assertRaisesRegex(PermissionError, "no issuer"):
            materializer.H28MaterializationCapability()
        forged = object.__new__(materializer.H28MaterializationCapability)
        with self.assertRaises(TypeError):
            copy.copy(forged)
        with self.assertRaises(TypeError):
            copy.deepcopy(forged)
        with self.assertRaises(TypeError):
            pickle.dumps(forged)

    def test_public_materializer_fails_before_numpy_contract_or_filesystem(self):
        exploding = _ExplodingDependency()
        with self.assertRaisesRegex(PermissionError, "not issued"):
            materializer.materialize_h28_records_in_memory(
                exploding, object(), exploding
            )

    def test_metadata_only_descriptor_plan_is_exact_and_complete(self):
        descriptors = materializer.plan_h28_materialization_descriptors(ROOT)
        self.assertEqual(tuple(item.record_identity for item in descriptors), RECORD_ORDER)
        self.assertEqual(
            tuple(item.proposal_hop_end for item in descriptors),
            (16383, 16383, 16639, 16639, 16895, 16895),
        )
        self.assertEqual(
            tuple(item.resolution_hop_end for item in descriptors),
            (16639, 16639, 16895, 16895, 17151, 17151),
        )
        self.assertEqual(
            tuple((item.candidate_pitch, item.active_pitches) for item in descriptors),
            ((40, ()), (52, (40,)), (40, ()), (52, (40,)), (40, ()), (52, (40,))),
        )

    def test_rendering_primitives_preserve_h27_formula_ast(self):
        h27_source = (
            ROOT / "src/polyphonic/harmonic_censoring_h27_review4_materializer.py"
        ).read_text(encoding="utf-8")
        h28_source = (
            ROOT / "src/polyphonic/harmonic_censoring_h28_materializer_dormant.py"
        ).read_text(encoding="utf-8")
        normalized = (
            h28_source.replace("H28", "H27")
            .replace("h28", "h27")
            .replace("H27MaterializationCapability", "H27ProductionMaterializationCapability")
            .replace("require_h27_materialization_capability", "_require_capability")
        )
        for function_name in ("_numeric", "_f0", "_envelope", "_accumulate_sources"):
            with self.subTest(function=function_name):
                self.assertEqual(
                    _function_ast(normalized, function_name),
                    _function_ast(h27_source, function_name),
                )

    def test_geometry_and_historical_prefix_proofs_are_closed(self):
        self.assertEqual(materializer.SAMPLE_COUNT, 17152)
        self.assertEqual(materializer.H27_PREFIX_SAMPLE_COUNT, 16640)
        source = (
            ROOT / "src/polyphonic/harmonic_censoring_h28_materializer_dormant.py"
        ).read_text(encoding="utf-8")
        self.assertIn("waveform[: H27_PREFIX_SAMPLE_COUNT * 8]", source)
        self.assertIn("H27_BASELINE_PAYLOAD_SHA256", source)
        self.assertIn("H28 waveform prefix differs from H27 baseline", source)
        self.assertIn("H28 N mask semantics differ from H27 baseline", source)

    def test_dormant_materializer_has_no_publication_or_numpy_import(self):
        source = (
            ROOT / "src/polyphonic/harmonic_censoring_h28_materializer_dormant.py"
        ).read_text(encoding="utf-8")
        self.assertNotIn("import numpy", source)
        self.assertNotIn("os.open", source)
        self.assertNotIn("write_bytes", source)
        self.assertNotIn("mkdir(", source)
        self.assertNotIn("replace(", source)


if __name__ == "__main__":
    unittest.main()
