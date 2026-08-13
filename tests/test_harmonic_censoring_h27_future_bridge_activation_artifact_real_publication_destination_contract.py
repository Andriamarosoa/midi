from __future__ import annotations
import hashlib, json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract.json"
SEAL=ROOT/"configs/harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_destination_contract_external_seal.json"

def blob(raw:bytes)->str:return hashlib.sha1(b"blob "+str(len(raw)).encode()+b"\0"+raw).hexdigest()
def check(t,item):
    raw=(ROOT/item["path"]).read_bytes()
    t.assertEqual((item["git_blob_sha1"],item["size_bytes"],item["raw_sha256"]),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))

class DestinationContractTests(unittest.TestCase):
    def setUp(self):
        self.c=json.loads(CONTRACT.read_bytes());self.s=json.loads(SEAL.read_bytes())
    def test_destination_is_exact_absent_and_unauthorized(self):
        d=self.c["canonical_destination"]
        self.assertEqual(d["destination_path"],"/Users/amcarene/h27-admin/activation/h27-materialization-v1.json")
        self.assertTrue(d["path_is_absolute"] and d["path_is_unique_and_immutable"])
        self.assertFalse(d["destination_exists"] or d["creation_authorized"] or d["write_authorized"] or d["overwrite_or_replace_authorized"])
    def test_contract_seal_and_sixty_identities(self):
        check(self,self.s["contract"])
        roots=self.c["reviewed_and_sealed_dormant_boundary"]
        source=json.loads((ROOT/self.c["transitive_identity_source"]["path"]).read_bytes())
        upstream=source["upstream_roots"]
        earlier=json.loads((ROOT/upstream[0]["path"]).read_bytes())
        fifty_four=[earlier["reviewed_contract"],earlier["contract_external_seal"],*earlier["reviewed_and_sealed_dormant_publication_simulator"]]
        old=json.loads((ROOT/earlier["transitive_upstream_binding"]["path"]).read_bytes())["upstream_entries"]
        items=[*roots,*upstream,*fifty_four,*old]
        self.assertEqual(len(items),60);self.assertEqual(len({x["path"] for x in items}),60)
        for item in items:check(self,item)
    def test_graph_and_state_are_closed(self):
        g=self.c["dependency_graph"];self.assertTrue(g["acyclic"]);self.assertFalse(g["self_hash_present"] or g["historical_back_reference_present"])
        for k,v in self.c["current_state"].items():self.assertIs(v,k=="destination_contract_exists",k)
        self.assertEqual(self.s["public_edges_closed"],8);self.assertFalse(self.s["destination_exists"] or self.s["write_authorized"] or self.s["locked_test_used"])

if __name__=="__main__":unittest.main()
