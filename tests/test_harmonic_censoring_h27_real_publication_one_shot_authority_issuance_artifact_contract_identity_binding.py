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
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuance_artifact_contract_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_issuance_artifact_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def sixty_four(chain):
 ec=json.loads((ROOT/chain[0]['path']).read_bytes());roots=ec['reviewed_and_sealed_destination_contract_chain'];db=json.loads((ROOT/roots[2]['path']).read_bytes());dc=json.loads((ROOT/db['reviewed_contract']['path']).read_bytes());dr=dc['reviewed_and_sealed_dormant_boundary'];old=json.loads((ROOT/dc['transitive_identity_source']['path']).read_bytes());ar=old['upstream_roots'];e=json.loads((ROOT/ar[0]['path']).read_bytes());f=[e['reviewed_contract'],e['contract_external_seal'],*e['reviewed_and_sealed_dormant_publication_simulator']];o=json.loads((ROOT/e['transitive_upstream_binding']['path']).read_bytes())['upstream_entries'];return [*roots,*dr,*ar,*f,*o]
class TestBinding(unittest.TestCase):
 def setUp(self):self.b=json.loads(B.read_bytes());self.s=json.loads(S.read_bytes())
 def test_74_exact_identities(self):
  chk(self,self.s['identity_binding']);chk(self,self.b['reviewed_contract']);chk(self,self.b['contract_external_seal']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());roots=contract['reviewed_and_sealed_one_shot_authority_chain'];authority=json.loads((ROOT/roots[0]['path']).read_bytes());execroots=authority['reviewed_and_sealed_execution_authorization_chain'];entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*roots,*execroots,*sixty_four(execroots)];self.assertEqual(len(entries),74);self.assertEqual(len({x['path'] for x in entries}),74)
  for x in entries:chk(self,x)
 def test_closed_state_and_preserved_invariants(self):
  allowed={'issuance_artifact_contract_exists','issuance_artifact_contract_externally_reviewed','issuance_artifact_contract_externally_sealed','issuance_artifact_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());schema=contract['future_artifact_schema'];inv=self.b['preserved_contract_invariants'];self.assertEqual(schema['fields']['issuer_id']['exact_value'],inv['issuer_id']);self.assertEqual(schema['fields']['predecessor_identity_count']['exact_value'],inv['predecessor_identity_count']);self.assertEqual(schema['fields']['predecessor_manifest_sha256']['exact_value'],inv['predecessor_manifest_sha256']);self.assertEqual((self.b['public_edges_closed'],inv['public_edges_closed']),(8,8));self.assertTrue(self.b['dependency_graph']['acyclic']);self.assertFalse(self.b['dependency_graph']['self_hash_present']);self.assertFalse(self.b['dependency_graph']['historical_back_reference_present'])
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_canonical(self):
  for raw in (B.read_bytes(),S.read_bytes()):self.assertNotIn(b'\r',raw);self.assertTrue(raw.endswith(b'\n'))
if __name__=='__main__':unittest.main()
