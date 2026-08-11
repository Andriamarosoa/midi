from pathlib import Path
import tempfile
import unittest
from unittest import mock

from src.polyphonic import harmonic_censoring_h26_runtime_qualification_operational_activation_issuer_implementation_contract_seal as loader

class IssuerImplementationSealTests(unittest.TestCase):
    def test_exact_is_immutable(self):
        result = loader.load_issuer_implementation_contract_external_seal()
        self.assertFalse(result["creation_authorized_now"])
        with self.assertRaises(TypeError): result["creation_authorized_now"] = True

    def test_modified_seal_fails_before_parse(self):
        root = Path(loader.__file__).resolve().parents[2]
        source = root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuer_dormant_implementation_contract_external_seal.json"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "seal.json"; changed.write_bytes(source.read_bytes() + b" ")
            with mock.patch.object(loader, "_json") as parser:
                with self.assertRaisesRegex(ValueError, "seal blob mismatch"):
                    loader.load_issuer_implementation_contract_external_seal(seal_path=changed)
            parser.assert_not_called()

    def test_crlf_contract_converges(self):
        root = Path(loader.__file__).resolve().parents[2]
        source = root / "configs" / "harmonic_censoring_h26_runtime_qualification_operational_activation_issuer_dormant_implementation_contract.json"
        with tempfile.TemporaryDirectory() as directory:
            changed = Path(directory) / "contract.json"; changed.write_bytes(source.read_bytes().replace(b"\n", b"\r\n"))
            loader.load_issuer_implementation_contract_external_seal(contract_path=changed)

if __name__ == "__main__": unittest.main()
