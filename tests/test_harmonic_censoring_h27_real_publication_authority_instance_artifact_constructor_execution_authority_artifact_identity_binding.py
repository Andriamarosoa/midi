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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding import hundred_eight
ROOT=Path(__file__).resolve().parents[1]
B=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_identity_binding_external_seal.json';CB=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding.json';CBS=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
def hundred_twelve(binding):
 contract=json.loads((ROOT/binding['reviewed_contract']['path']).read_bytes());return [binding['reviewed_contract'],binding['contract_external_seal'],{'path':str(CB.relative_to(ROOT)).replace('\\','/'),'git_blob_sha1':'71439f93f56f5f499ba29d6ee7fe334ed2421735','size_bytes':3340,'raw_sha256':'1907b841a9defa5a9b3ac61ffc3660be6fb5447d63044d0816e8b2c94aae5d4d'},{'path':str(CBS.relative_to(ROOT)).replace('\\','/'),'git_blob_sha1':'ed4a944d70d49e33c66d0d73f04a2e3a682cb79c','size_bytes':1530,'raw_sha256':'02c01af0276f98e91c992b566c95a33b8354ca57b80fa1cb3c056dc2a7954b06'},*hundred_eight(contract)]
class TestArtifactBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_exact_114_and_seal(self):
  for raw in (self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['identity_binding']);cb=json.loads(CB.read_bytes());entries=[self.b['reviewed_artifact'],self.b['artifact_external_seal'],*hundred_twelve(cb)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(114,114));[chk(self,x) for x in entries]
 def test_values_state_graph_edges(self):
  artifact=json.loads((ROOT/self.b['reviewed_artifact']['path']).read_bytes());self.assertEqual(self.b['bound_artifact_values'],{'execution_authority_artifact_id':artifact['execution_authority_artifact_id'],'expected_git_head':artifact['expected_git_head'],'single_use':True,'consumed':False});self.assertTrue(all(self.b['preserved_guards'].values()));allowed={'execution_authority_artifact_exists','execution_authority_artifact_externally_reviewed','execution_authority_artifact_externally_sealed','execution_authority_artifact_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_fourteen_bound_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual((self.s['bound_identity_count'],self.s['artifact_id'],self.s['expected_git_head'],self.s['single_use'],self.s['consumed']),(114,artifact['execution_authority_artifact_id'],artifact['expected_git_head'],True,False));self.assertEqual(self.b['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  cb=json.loads(CB.read_bytes())
  for x in [self.b['reviewed_artifact'],self.b['artifact_external_seal'],*hundred_twelve(cb)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
