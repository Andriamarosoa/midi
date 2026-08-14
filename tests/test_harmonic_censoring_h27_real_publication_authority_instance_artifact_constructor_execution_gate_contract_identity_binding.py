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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding import hundred_twelve
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
def hundred_sixteen(contract):
 roots=contract['reviewed_and_sealed_execution_authority_artifact_chain'];binding=json.loads((ROOT/roots[2]['path']).read_bytes());return [*roots,*hundred_twelve(json.loads((ROOT/binding['transitive_identity_source']['path']).read_bytes()))]
class TestExecutionGateContractBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_exact_seal_and_118_identities(self):
  for raw in (self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['identity_binding']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_sixteen(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(118,118));[chk(self,x) for x in entries]
 def test_source_authority_guards_state_and_edges(self):
  self.assertEqual(self.b['bound_runtime_source_model'],{'target_checkout_root':'/Users/amcarene/midi-worker/repository','target_checkout_expected_git_head':'46a6bdf81a56a7a7a10524d4e55092301a452207','administrative_control_bundle_root':'/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1','control_source_and_target_checkout_are_distinct':True,'implicit_current_checkout_or_path_selection_forbidden':True,'control_bundle_creation_requires_distinct_later_contract_review_and_authorization':True});self.assertEqual(self.b['bound_authority'],{'execution_authority_artifact_id':'45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e','single_use':True,'consumed':False});self.assertTrue(all(self.b['preserved_guards'].values()))
  allowed={'constructor_execution_gate_contract_exists','constructor_execution_gate_contract_externally_reviewed','constructor_execution_gate_contract_externally_sealed','constructor_execution_gate_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_eighteen_bound_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual((self.s['bound_identity_count'],self.s['single_use'],self.s['consumed'],self.b['public_edges_closed']),(118,True,False,8));self.assertFalse(any(self.s[k] for k in ('administrative_control_bundle_exists','persistent_registry_opened','identity_nonce_reserved','constructor_invoked_really','destination_observed','filesystem_materializer_population_science','locked_test_used','training_or_calibration_authorized')))
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes())
  for x in [self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_sixteen(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
