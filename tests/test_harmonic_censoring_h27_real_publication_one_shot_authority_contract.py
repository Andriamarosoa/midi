from __future__ import annotations
import hashlib,json
from pathlib import Path
import unittest
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as m
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as a
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as p
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant as r
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as b
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as g
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as q
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as c
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_contract.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def sixty_four(chain):
 ec=json.loads((ROOT/chain[0]['path']).read_bytes()); roots=ec['reviewed_and_sealed_destination_contract_chain']; db=json.loads((ROOT/roots[2]['path']).read_bytes()); dc=json.loads((ROOT/db['reviewed_contract']['path']).read_bytes()); dr=dc['reviewed_and_sealed_dormant_boundary']; old=json.loads((ROOT/dc['transitive_identity_source']['path']).read_bytes()); ar=old['upstream_roots']; e=json.loads((ROOT/ar[0]['path']).read_bytes()); f=[e['reviewed_contract'],e['contract_external_seal'],*e['reviewed_and_sealed_dormant_publication_simulator']]; o=json.loads((ROOT/e['transitive_upstream_binding']['path']).read_bytes())['upstream_entries'];return [*roots,*dr,*ar,*f,*o]
class TestContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.c=json.loads(C.read_bytes());cls.s=json.loads(S.read_bytes())
 def test_68_exact(self):
  chk(self,self.s['contract']);entries=[*self.c['reviewed_and_sealed_execution_authorization_chain'],*sixty_four(self.c['reviewed_and_sealed_execution_authorization_chain'])];self.assertEqual(len(entries),68);self.assertEqual(len({x['path'] for x in entries}),68)
  for x in entries:chk(self,x)
 def test_closed(self):
  for k,v in self.c['current_state'].items():self.assertIs(v,k=='one_shot_authority_contract_exists',k)
  z=self.c['dependency_graph'];self.assertTrue(z['acyclic']);self.assertFalse(z['self_hash_present'] or z['historical_back_reference_present'])
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_canonical(self):
  for raw in (C.read_bytes(),S.read_bytes()):self.assertNotIn(b'\r',raw);self.assertTrue(raw.endswith(b'\n'))
if __name__=='__main__':unittest.main()
