from pathlib import Path
import unittest
from src.polyphonic import harmonic_censoring_h26_materialization_operationalization_contract_seal as loader
class MaterializationOperationalizationSealTests(unittest.TestCase):
    def test_exact_immutable(self):
        value=loader.load_materialization_operationalization_contract_external_seal(); self.assertFalse(value["creation_authorized_now"])
        with self.assertRaises(TypeError): value["creation_authorized_now"]=True
        with self.assertRaises(TypeError): value["current_state"]["materializer_invoked"]=True
        self.assertEqual(loader._deep_freeze_json([{"value":False}]),(loader.MappingProxyType({"value":False}),))
    def test_real_materializer_symbol_absent(self):
        source=Path(loader.__file__).read_text(); self.assertNotIn("materialize_h26_population",source); self.assertNotIn("import numpy",source)
if __name__=="__main__": unittest.main()
