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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_real_invocation_authorization_contract_identity_binding import hundred_four
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding.json'
S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
def hundred_eight(contract):
 chain=contract['reviewed_and_sealed_invocation_authorization_chain'];up=json.loads((ROOT/chain[0]['path']).read_bytes());return [*chain,*hundred_four(up)]
class TestExecutionAuthorityArtifactContractBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_canonical_seal_and_exact_110_identities(self):
  for raw in (self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['identity_binding']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_eight(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(110,110));[chk(self,x) for x in entries]
 def test_preserved_schema_state_graph_and_edges(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());schema=contract['future_artifact_schema'];preserved=self.b['preserved_artifact_schema'];self.assertEqual(preserved,{'exact_top_level_field_count':7,'schema_version_exact_integer':1,'artifact_type_exact':'h27_constructor_real_invocation_execution_authority','execution_authority_artifact_id_lowercase_hex64':True,'execution_authority_artifact_id_namespace':'H27_CONSTRUCTOR_REAL_INVOCATION_EXECUTION_AUTHORITY_V1','expected_git_head_exact_native_lowercase_hex40':True,'expected_git_head_distinct_later_reviewed_sealed_artifact_only':True,'current_head_fallback_or_automatic_selection_forbidden':True,'authorization_chain_identity_six_exact_ordered_fields':True,'single_use_exact_boolean':True,'consumed_initial_exact_boolean':False,'strict_json_and_canonical_order_rules_preserved':True,'all_six_future_artifact_rules_preserved':True});self.assertEqual(len(schema['exact_top_level_field_order']),preserved['exact_top_level_field_count']);self.assertEqual(schema['schema_version_exact_integer'],preserved['schema_version_exact_integer']);self.assertEqual(schema['artifact_type_exact'],preserved['artifact_type_exact']);self.assertEqual(schema['execution_authority_artifact_id_namespace'],preserved['execution_authority_artifact_id_namespace']);self.assertNotIn('expected_git_head',contract);self.assertEqual(len(contract['future_artifact_rules']),6);self.assertTrue(all(v is True for v in contract['future_artifact_rules'].values()))
  allowed={'execution_authority_artifact_contract_exists','execution_authority_artifact_contract_externally_reviewed','execution_authority_artifact_contract_externally_sealed','execution_authority_artifact_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_ten_bound_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual(self.b['public_edges_closed'],8);self.assertEqual(self.s['bound_identity_count'],110);self.assertTrue(self.s['artifact_schema_contract_preserved'] and self.s['expected_git_head_contract_preserved_without_value']);self.assertFalse(self.s['execution_authority_artifact_exists'] or self.s['expected_git_head_value_selected'])
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_historical_back_reference(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes())
  for x in [self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_eight(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
