from pathlib import Path
from unittest import mock
import unittest
from src.polyphonic import harmonic_censoring_h26_runtime_one_shot_orchestration_contract_seal as loader

class RuntimeOrchestrationSealTests(unittest.TestCase):
    def test_exact_seal_and_contract(self):
        value=loader.load_runtime_one_shot_orchestration_contract_external_seal(); self.assertFalse(value["creation_authorized_now"])
        self.assertEqual(value["correction_contract_git_blob_sha"], loader.CORRECTION_CONTRACT_GIT_BLOB_SHA)
        self.assertEqual(value["historical_contract_binding"]["git_blob_sha"], loader.HISTORICAL_CONTRACT_GIT_BLOB_SHA)
        with self.assertRaises(TypeError): value["creation_authorized_now"]=True
        with self.assertRaises(TypeError): value["current_state"]["observer_invoked"]=True
        self.assertEqual(loader._deep_freeze_json([{"value":False}]),(loader.MappingProxyType({"value":False}),))
    def test_seal_blob_is_checked_before_parse(self):
        with mock.patch.object(loader,"CORRECTION_SEAL_GIT_BLOB_SHA","0"*40), mock.patch.object(loader,"_parse") as parse:
            with self.assertRaisesRegex(ValueError,"seal blob mismatch"):
                loader.load_runtime_one_shot_orchestration_contract_external_seal()
            parse.assert_not_called()
    def test_duplicate_keys_are_rejected(self):
        with self.assertRaisesRegex(ValueError,"duplicate JSON key"):
            loader._parse(b'{"a":1,"a":2}')
    def test_no_runtime_symbols(self):
        source=Path(loader.__file__).read_text()
        for forbidden in ("observe_primary_runtime","import numpy","otool","write_bytes","mkdir("): self.assertNotIn(forbidden,source)

if __name__=="__main__": unittest.main()
