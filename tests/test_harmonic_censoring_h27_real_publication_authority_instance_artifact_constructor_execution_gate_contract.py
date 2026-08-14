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
C=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
class TestExecutionGateContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cr=C.read_bytes();cls.sr=S.read_bytes();cls.c=json.loads(cls.cr);cls.s=json.loads(cls.sr)
 def test_exact_seal_and_116_predecessors(self):
  for raw in (self.cr,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['contract']);roots=self.c['reviewed_and_sealed_execution_authority_artifact_chain'];binding=json.loads((ROOT/roots[2]['path']).read_bytes());entries=[*roots,*hundred_twelve(json.loads((ROOT/binding['transitive_identity_source']['path']).read_bytes()))];self.assertEqual((len(entries),len({x['path'] for x in entries})),(116,116));[chk(self,x) for x in entries]
 def test_exact_order_rules_state_and_edges(self):
  self.assertEqual(self.c['future_fail_closed_order'],['load_gate_external_seal_from_exact_administrative_control_bundle_path','verify_gate_contract_bytes_from_exact_administrative_control_bundle_path','load_four_exact_execution_authority_artifact_chain_files_from_administrative_control_bundle','verify_target_checkout_head_equals_expected_git_head','verify_target_checkout_worktree_clean','rehash_four_control_bundle_identities_and_one_hundred_twelve_target_checkout_identities','open_persistent_registry','reserve_exact_artifact_id_and_nonce_once','consume_exact_execution_authority_artifact_atomically','invoke_exact_sealed_constructor_from_target_checkout_once'])
  source=self.c['future_runtime_source_model'];self.assertEqual(source['target_checkout_root'],'/Users/amcarene/midi-worker/repository');self.assertEqual(source['target_checkout_expected_git_head'],'46a6bdf81a56a7a7a10524d4e55092301a452207');self.assertEqual(source['administrative_control_bundle_root'],'/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1');self.assertTrue(all(v for k,v in source.items() if k not in ('target_checkout_root','target_checkout_expected_git_head','administrative_control_bundle_root')))
  self.assertTrue(all(self.c['future_gate_rules'].values()));self.assertEqual(self.c['bound_authority'],{'execution_authority_artifact_id':'45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e','expected_git_head':'46a6bdf81a56a7a7a10524d4e55092301a452207','single_use':True,'consumed':False});self.assertTrue(self.c['transitive_identity_source']['all_one_hundred_sixteen_identities_must_be_rehashed_before_registry_open'])
  allowed={'constructor_execution_gate_contract_exists'}
  for k,v in self.c['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.c['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_sixteen_predecessor_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual((self.s['bound_identity_count'],self.s['execution_authority_artifact_id'],self.s['expected_git_head'],self.s['target_checkout_root'],self.s['administrative_control_bundle_root'],self.s['control_source_and_target_checkout_are_distinct'],self.s['single_use'],self.s['consumed'],self.c['public_edges_closed']),(116,'45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e','46a6bdf81a56a7a7a10524d4e55092301a452207','/Users/amcarene/midi-worker/repository','/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1',True,True,False,8));self.assertTrue(self.s['dependency_graph_acyclic']);self.assertFalse(self.s['self_hash_present'] or self.s['historical_back_reference_present']);self.assertFalse(any(self.s[k] for k in ('persistent_registry_opened','identity_nonce_reserved','constructor_invoked_really','destination_observed','filesystem_materializer_population_science','locked_test_used','training_or_calibration_authorized')))
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  roots=self.c['reviewed_and_sealed_execution_authority_artifact_chain'];binding=json.loads((ROOT/roots[2]['path']).read_bytes())
  for x in [*roots,*hundred_twelve(json.loads((ROOT/binding['transitive_identity_source']['path']).read_bytes()))]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(C.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
