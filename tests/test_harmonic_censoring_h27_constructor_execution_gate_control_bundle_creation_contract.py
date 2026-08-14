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
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract.json';S=ROOT/'configs/harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
class TestControlBundleCreationContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cr=C.read_bytes();cls.sr=S.read_bytes();cls.c=json.loads(cls.cr);cls.s=json.loads(cls.sr)
 def test_exact_seal_manifest_and_120_predecessors(self):
  for raw in (self.cr,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['contract']);roots=self.c['reviewed_and_sealed_gate_contract_chain'];gate=json.loads((ROOT/roots[0]['path']).read_bytes());entries=[*roots,*hundred_sixteen(gate)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(120,120));[chk(self,x) for x in entries];manifest=self.c['closed_six_file_manifest'];self.assertEqual((len(manifest),len({x['path'] for x in manifest})),(6,6));[chk(self,x) for x in manifest]
 def test_exact_paths_order_rules_state_and_edges(self):
  d=self.c['bundle_definition'];self.assertEqual((d['final_bundle_root'],d['staging_bundle_root'],d['source_git_object_database']),('/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1','/Users/amcarene/h27-admin/control/.h27-constructor-execution-gate-v1.staging','/Users/amcarene/midi-worker/repository/.git'));self.assertTrue(all(v for k,v in d.items() if k not in ('administrative_root','control_parent','final_bundle_root','staging_bundle_root','source_git_object_database')));self.assertEqual(len(self.c['future_fail_closed_creation_order']),13);self.assertTrue(all(self.c['future_creation_rules'].values()));self.assertTrue(self.c['transitive_identity_source']['all_one_hundred_twenty_identities_must_be_rehashed_before_any_bundle_path_observation'])
  allowed={'control_bundle_creation_contract_exists'}
  for k,v in self.c['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.c['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_twenty_predecessor_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual((self.s['bound_identity_count'],self.s['bundle_file_count'],self.c['public_edges_closed']),(120,6,8));self.assertFalse(any(self.s[k] for k in ('administrative_control_bundle_exists','bundle_path_observed','filesystem_operation_authorized','persistent_registry_opened','identity_nonce_reserved','constructor_invoked_really','destination_observed','science_or_locked_test')))
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  roots=self.c['reviewed_and_sealed_gate_contract_chain'];gate=json.loads((ROOT/roots[0]['path']).read_bytes())
  for x in [*roots,*hundred_sixteen(gate)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(C.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
