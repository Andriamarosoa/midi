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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_gate_contract_identity_binding import hundred_sixteen
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'configs/harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
def hundred_twenty(contract):
 roots=contract['reviewed_and_sealed_gate_contract_chain'];gate=json.loads((ROOT/roots[0]['path']).read_bytes());return [*roots,*hundred_sixteen(gate)]
class TestControlBundleCreationContractBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_exact_seal_and_122_identities(self):
  for raw in (self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['identity_binding']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_twenty(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(122,122));[chk(self,x) for x in entries]
 def test_bundle_guards_state_and_edges(self):
  self.assertEqual(self.b['bound_bundle'],{'final_bundle_root':'/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1','staging_bundle_root':'/Users/amcarene/h27-admin/control/.h27-constructor-execution-gate-v1.staging','source_git_object_database':'/Users/amcarene/midi-worker/repository/.git','closed_manifest_file_count':6,'manifest_paths_and_identities_exact':True,'immutable_after_publication':True});self.assertEqual(list(self.b['preserved_guards']),['rehash_one_hundred_twenty_precedes_bundle_observation','exact_git_blob_source_only','checkout_file_reads_forbidden','exact_thirteen_step_order','exact_twelve_creation_rules','no_symlink_escape','exclusive_staging_and_no_overwrite','fsync_rehash_atomic_rename_order','post_first_effect_failure_terminal','retry_after_first_effect_forbidden','distinct_later_authority_and_review_required']);self.assertTrue(all(self.b['preserved_guards'].values()))
  allowed={'control_bundle_creation_contract_exists','control_bundle_creation_contract_externally_reviewed','control_bundle_creation_contract_externally_sealed','control_bundle_creation_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_twenty_two_bound_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual((self.s['bound_identity_count'],self.s['bundle_file_count'],self.b['public_edges_closed']),(122,6,8));self.assertFalse(any(self.s[k] for k in ('administrative_control_bundle_exists','bundle_path_observed','filesystem_operation_authorized','persistent_registry_opened','identity_nonce_reserved','constructor_invoked_really','destination_observed','science_or_locked_test')))
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes())
  for x in [self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_twenty(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
