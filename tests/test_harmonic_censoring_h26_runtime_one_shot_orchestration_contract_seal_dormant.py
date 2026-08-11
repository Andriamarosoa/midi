from pathlib import Path
import unittest
from src.polyphonic import harmonic_censoring_h26_runtime_one_shot_orchestration_contract_seal as loader

class RuntimeOrchestrationSealTests(unittest.TestCase):
    def test_exact_seal_and_contract(self):
        value=loader.load_runtime_one_shot_orchestration_contract_external_seal(); self.assertFalse(value["creation_authorized_now"])
        with self.assertRaises(TypeError): value["creation_authorized_now"]=True
        with self.assertRaises(TypeError): value["current_state"]["observer_invoked"]=True
        self.assertEqual(loader._deep_freeze_json([{"value":False}]),(loader.MappingProxyType({"value":False}),))
    def test_no_runtime_symbols(self):
        source=Path(loader.__file__).read_text()
        for forbidden in ("observe_primary_runtime","import numpy","otool","write_bytes","mkdir("): self.assertNotIn(forbidden,source)

if __name__=="__main__": unittest.main()
