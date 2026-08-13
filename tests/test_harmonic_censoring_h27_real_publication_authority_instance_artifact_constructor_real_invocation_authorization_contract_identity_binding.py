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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_real_invocation_authorization_contract import hundred
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_real_invocation_authorization_contract_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_real_invocation_authorization_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def hundred_four(contract):return [*contract['reviewed_and_sealed_constructor_chain'],*hundred(contract['reviewed_and_sealed_constructor_chain'])]
class TestBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_canonical_and_106_exact(self):
  for raw in (self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['identity_binding']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_four(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(106,106));[chk(self,x) for x in entries]
 def test_head_contract_order_state_graph_edges(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());head=self.b['preserved_git_head_contract'];self.assertTrue(all(head.values()));req=contract['future_execution_authority_artifact_requirement'];pre=contract['future_git_preflight'];self.assertTrue(req['expected_git_head_required'] and req['expected_git_head_exact_native_string'] and req['expected_git_head_lowercase_hex40'] and req['expected_git_head_bound_by_artifact_identity_and_external_seal'] and req['automatic_head_selection_or_current_head_fallback_forbidden']);self.assertTrue(all(pre.values()));self.assertTrue(self.b['preserved_fail_closed_order_exact']);self.assertEqual(contract['future_fail_closed_order'][0:4],['load_distinct_reviewed_and_sealed_execution_authority_artifact','validate_expected_git_head_exact_native_lowercase_hex40','verify_runtime_head_equals_expected_git_head_and_clean_worktree','rehash_all_one_hundred_four_predecessor_identities'])
  allowed={'authorization_contract_exists','authorization_contract_externally_reviewed','authorization_contract_externally_sealed','authorization_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_six_bound_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual(self.b['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes())
  for x in [self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_four(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
