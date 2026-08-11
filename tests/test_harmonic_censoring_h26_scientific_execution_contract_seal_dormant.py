from pathlib import Path
import unittest
from src.polyphonic import harmonic_censoring_h26_scientific_execution_contract_seal as loader
class ScientificSealTests(unittest.TestCase):
    def test_exact_immutable(self):
        value=loader.load_scientific_execution_contract_external_seal(); self.assertFalse(value["creation_authorized_now"])
        with self.assertRaises(TypeError): value["creation_authorized_now"]=True
        with self.assertRaises(TypeError): value["current_state"]["p0_executed"]=True
        self.assertEqual(loader._deep_freeze_json([{"value":False}]),(loader.MappingProxyType({"value":False}),))
    def test_no_engine_or_data_import(self):
        source=Path(loader.__file__).read_text(); self.assertNotIn("harmonic_censoring_h26_engine",source); self.assertNotIn("numpy",source)
    def test_strict_json_rejects_duplicate_float_and_nonstandard_constants(self):
        invalid=(
            b'{"x":1,"x":2}',
            b'{"x":1.5}',
            b'{"x":NaN}',
            b'{"x":Infinity}',
            b'{"x":-Infinity}',
        )
        for raw in invalid:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError): loader._parse(raw)
if __name__=="__main__": unittest.main()
