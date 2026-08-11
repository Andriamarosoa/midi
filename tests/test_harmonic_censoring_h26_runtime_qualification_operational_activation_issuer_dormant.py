from dataclasses import FrozenInstanceError
import unittest

from src.polyphonic.harmonic_censoring_h26_runtime_qualification_operational_activation_issuance_planner import H26ActivationIssuancePlan
from src.polyphonic.harmonic_censoring_h26_runtime_qualification_operational_activation_issuer import publish_prevalidated_activation_with_adapter

class FakeAdapter:
    def __init__(self, existing=()): self.paths=set(existing); self.calls=[]
    def exists(self,path): self.calls.append(("exists",path)); return path in self.paths
    def create_exclusive(self,path,data):
        self.calls.append(("create",path,data));
        if path in self.paths: raise FileExistsError(path)
        self.paths.add(path)
    def sync_file(self,path): self.calls.append(("sync_file",path))
    def rename_no_replace(self,source,destination):
        self.calls.append(("rename",source,destination));
        if destination in self.paths: raise FileExistsError(destination)
        self.paths.remove(source); self.paths.add(destination)
    def sync_directory(self,path): self.calls.append(("sync_directory",path))

def plan():
    return H26ActivationIssuancePlan("id","a"*64,b"{}\n","/root","/root/activation/activation.json","/root/activation/.activation.json.staging","issuer","2026-08-11T20:00:00Z")

class DormantIssuerTests(unittest.TestCase):
    def test_fake_adapter_exact_sequence_and_immutable_receipt(self):
        adapter=FakeAdapter(); receipt=publish_prevalidated_activation_with_adapter(plan(),adapter)
        self.assertEqual([call[0] for call in adapter.calls],["exists","exists","create","sync_file","rename","sync_directory"])
        self.assertTrue(receipt.published)
        with self.assertRaises(FrozenInstanceError): receipt.published=False

    def test_collision_fails_before_create(self):
        value=plan(); adapter=FakeAdapter((value.final_path,))
        with self.assertRaises(FileExistsError): publish_prevalidated_activation_with_adapter(value,adapter)
        self.assertFalse(any(call[0]=="create" for call in adapter.calls))

    def test_failure_preserves_staging_and_has_no_retry(self):
        class Fail(FakeAdapter):
            def sync_file(self,path): super().sync_file(path); raise OSError("terminal")
        adapter=Fail(); value=plan()
        with self.assertRaises(OSError): publish_prevalidated_activation_with_adapter(value,adapter)
        self.assertIn(value.staging_path,adapter.paths)
        self.assertEqual(sum(call[0]=="create" for call in adapter.calls),1)

if __name__ == "__main__": unittest.main()
