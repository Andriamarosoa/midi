from __future__ import annotations

import ast
import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path
import pickle
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h27_production_materializer_dormant as reviewed
from src.polyphonic import harmonic_censoring_h27_review4_materializer as review4

ROOT = Path(__file__).resolve().parents[1]
SCIENTIFIC_HELPERS = (
    "_canonical_json_bytes", "_numeric", "_f0", "_envelope", "_accumulate_sources",
    "_add_noise", "_render_recipe", "_render_collision", "_grid_cells",
    "_fixture_active_pitches", "_descriptors", "_transformed_recipe", "_mask_bytes", "_render_record",
)

def normalized_function(module: object, name: str) -> str:
    tree = ast.parse(inspect.getsource(getattr(module, name)))
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "H27ProductionMaterializationCapability":
            node.id = "CAPABILITY"
    return ast.dump(tree, include_attributes=False)

def load_runner():
    path = ROOT / "scripts/h27_review4_execute_once.py"
    spec = importlib.util.spec_from_file_location("h27_review4_runner_test", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

class Review4MaterializerTests(unittest.TestCase):
    def test_scientific_functions_remain_mechanically_identical(self) -> None:
        for name in SCIENTIFIC_HELPERS:
            self.assertEqual(normalized_function(reviewed, name), normalized_function(review4, name), name)

    def test_no_token_issuer_or_mutable_registry_exists(self) -> None:
        source = inspect.getsource(review4)
        self.assertNotIn("_CAPABILITY_TOKEN", source)
        self.assertNotIn("_ISSUED", source)
        self.assertNotIn("_issue_review4_capability", source)

    def test_capability_public_construction_copy_and_pickle_fail(self) -> None:
        with self.assertRaises(PermissionError):
            review4.H27ProductionMaterializationCapability()
        forged = object.__new__(review4.H27ProductionMaterializationCapability)
        for operation in (copy.copy, copy.deepcopy, pickle.dumps):
            with self.assertRaises((PermissionError, TypeError)):
                operation(forged)

    def test_object_new_forgery_fails_before_publish(self) -> None:
        forged = object.__new__(review4.H27ProductionMaterializationCapability)
        binding = review4.H27Review4CapabilityBinding("0"*64, "1"*64, "2"*40, "3"*64, 0, "4"*64)
        session = review4.H27Review4Session(forged, binding, lambda value: binding, -1, -1, -1)
        with mock.patch.object(review4, "_publish") as publish:
            with self.assertRaises(PermissionError):
                review4.materialize_h27_production_population(session, lambda root: object(), Path("."))
        publish.assert_not_called()

    def test_binding_and_seal_match_exact_materializer_bytes(self) -> None:
        raw = (ROOT / "src/polyphonic/harmonic_censoring_h27_review4_materializer.py").read_bytes()
        blob = hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
        sha = hashlib.sha256(raw).hexdigest()
        binding_raw = (ROOT / "configs/harmonic_censoring_h27_review4_materializer_identity_binding.json").read_bytes()
        binding = json.loads(binding_raw)
        seal = json.loads((ROOT / "configs/harmonic_censoring_h27_review4_materializer_external_seal.json").read_bytes())
        self.assertEqual((binding["materializer"]["git_blob_sha1"], binding["materializer"]["size_bytes"], binding["materializer"]["raw_sha256"]), (blob, len(raw), sha))
        self.assertEqual(seal["materializer"], binding["materializer"])
        self.assertEqual(seal["identity_binding"]["git_blob_sha1"], hashlib.sha1(b"blob "+str(len(binding_raw)).encode()+b"\0"+binding_raw).hexdigest())

    def test_runner_is_frozen_post_claim_descriptor_relative_and_non_scientific(self) -> None:
        source = (ROOT / "scripts/h27_review4_execute_once.py").read_text(encoding="utf-8")
        self.assertNotIn("spec_from_file_location", source)
        self.assertNotIn("SourceFileLoader", source)
        self.assertIn("compile(raw,filename", source)
        self.assertLess(source.index("claim_fd,claim_raw=write_new_at"), source.index('critical_objects["materialize_h27_production_population"]('))
        self.assertIn("os.O_DIRECTORY|os.O_NOFOLLOW", source)
        self.assertIn("p0_executed\":False", source)
        self.assertIn("p1_executed\":False", source)
        self.assertIn("p2_executed\":False", source)
        self.assertIn("baseline_population_materialized\":True", source)
        self.assertNotIn("run_h27_engine", source)
        self.assertNotIn("run_h27_independent_recomputer", source)

    def test_attested_consumer_accepts_only_exact_pair_once(self) -> None:
        runner = load_runner()
        capability = object()
        binding = review4.H27Review4CapabilityBinding("a"*64, "b"*64, "c"*40, "d"*64, 7, "e"*64)
        consumer = runner.attested_consumer(capability, binding, 1, 2, 3)
        next(consumer)
        with mock.patch.object(runner.os, "getpid", return_value=7), mock.patch.object(
            runner, "read_fd", side_effect=(b"code", b"authority", b"claim")
        ), mock.patch.object(runner, "digest", side_effect=("e"*64, "a"*64, "b"*64)):
            self.assertIs(consumer.send((capability, binding)), binding)
            with self.assertRaises(StopIteration):
                consumer.send((capability, binding))

    def test_attested_consumer_rejects_wrong_pair_and_post_claim_drift(self) -> None:
        runner = load_runner()
        capability = object()
        binding = review4.H27Review4CapabilityBinding("a"*64, "b"*64, "c"*40, "d"*64, 7, "e"*64)
        wrong = runner.attested_consumer(capability, binding, 1, 2, 3); next(wrong)
        with self.assertRaises(PermissionError):
            wrong.send((object(), binding))
        drift = runner.attested_consumer(capability, binding, 1, 2, 3); next(drift)
        with mock.patch.object(runner.os, "getpid", return_value=7), mock.patch.object(
            runner, "read_fd", return_value=b"changed"
        ), mock.patch.object(runner, "digest", return_value="0"*64):
            with self.assertRaisesRegex(PermissionError, "code drift"):
                drift.send((capability, binding))

if __name__ == "__main__":
    unittest.main()
