from __future__ import annotations
import hashlib,json
from pathlib import Path
import unittest
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_contract.json';B=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_contract_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def sixty_four(chain):
 ec=json.loads((ROOT/chain[0]['path']).read_bytes());roots=ec['reviewed_and_sealed_destination_contract_chain'];db=json.loads((ROOT/roots[2]['path']).read_bytes());dc=json.loads((ROOT/db['reviewed_contract']['path']).read_bytes());dr=dc['reviewed_and_sealed_dormant_boundary'];old=json.loads((ROOT/dc['transitive_identity_source']['path']).read_bytes());ar=old['upstream_roots'];e=json.loads((ROOT/ar[0]['path']).read_bytes());f=[e['reviewed_contract'],e['contract_external_seal'],*e['reviewed_and_sealed_dormant_publication_simulator']];o=json.loads((ROOT/e['transitive_upstream_binding']['path']).read_bytes())['upstream_entries'];return [*roots,*dr,*ar,*f,*o]
class TestBinding(unittest.TestCase):
 def setUp(self):self.c=json.loads(C.read_bytes());self.b=json.loads(B.read_bytes());self.s=json.loads(S.read_bytes())
 def test_70(self):
  chk(self,self.s['identity_binding']);chain=self.c['reviewed_and_sealed_execution_authorization_chain'];entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*chain,*sixty_four(chain)];self.assertEqual(len(entries),70);self.assertEqual(len({x['path'] for x in entries}),70)
  for x in entries:chk(self,x)
 def test_closed(self):
  allow={'one_shot_authority_contract_exists','one_shot_authority_contract_externally_reviewed','one_shot_authority_contract_externally_sealed','one_shot_authority_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allow,k)
  self.assertTrue(self.b['dependency_graph']['acyclic']);self.assertEqual(self.b['public_edges_closed'],8)
 def test_canonical(self):
  for raw in (B.read_bytes(),S.read_bytes()):self.assertNotIn(b'\r',raw);self.assertTrue(raw.endswith(b'\n'))
if __name__=='__main__':unittest.main()
