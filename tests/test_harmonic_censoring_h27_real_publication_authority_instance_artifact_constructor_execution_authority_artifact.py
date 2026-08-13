from __future__ import annotations
import hashlib,json,re
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
A=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact.json'
S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_external_seal.json'
B=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding.json'
BS=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
class TestExecutionAuthorityArtifact(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.ar=A.read_bytes();cls.sr=S.read_bytes();cls.a=json.loads(cls.ar);cls.s=json.loads(cls.sr);cls.b=json.loads(B.read_bytes())
 def test_exact_canonical_artifact_schema_id_and_seal(self):
  self.assertNotIn(b'\r',self.ar);self.assertFalse(self.ar.startswith(b'\xef\xbb\xbf'));self.assertTrue(self.ar.endswith(b'\n'));self.assertEqual(self.ar,json.dumps(self.a,separators=(',',':'),ensure_ascii=True).encode()+b'\n')
  self.assertEqual(list(self.a),['schema_version','artifact_type','execution_authority_artifact_id','expected_git_head','authorization_chain_identity','single_use','consumed']);self.assertIs(type(self.a['schema_version']),int);self.assertEqual(self.a['schema_version'],1);self.assertEqual(self.a['artifact_type'],'h27_constructor_real_invocation_execution_authority');self.assertRegex(self.a['expected_git_head'],r'^[0-9a-f]{40}$');self.assertEqual(self.a['expected_git_head'],'46a6bdf81a56a7a7a10524d4e55092301a452207');self.assertIs(self.a['single_use'],True);self.assertIs(self.a['consumed'],False)
  chain=self.a['authorization_chain_identity'];self.assertEqual(list(chain),['contract_git_blob_sha1','contract_size_bytes','contract_raw_sha256','binding_git_blob_sha1','binding_size_bytes','binding_raw_sha256']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());schema=contract['future_artifact_schema'];self.assertEqual(chain,schema['authorization_chain_identity_exact_values']);payload='\0'.join([schema['execution_authority_artifact_id_namespace'],self.a['expected_git_head'],chain['contract_raw_sha256'],chain['binding_raw_sha256']]).encode('ascii');self.assertEqual(self.a['execution_authority_artifact_id'],hashlib.sha256(payload).hexdigest());self.assertRegex(self.a['execution_authority_artifact_id'],r'^[0-9a-f]{64}$');chk(self,self.s['execution_authority_artifact']);self.assertEqual((self.s['expected_git_head'],self.s['execution_authority_artifact_id']),(self.a['expected_git_head'],self.a['execution_authority_artifact_id']))
 def test_exact_112_upstream_and_closed_runtime(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],{'path':str(B.relative_to(ROOT)).replace('\\','/'),'git_blob_sha1':'71439f93f56f5f499ba29d6ee7fe334ed2421735','size_bytes':3340,'raw_sha256':'1907b841a9defa5a9b3ac61ffc3660be6fb5447d63044d0816e8b2c94aae5d4d'},{'path':str(BS.relative_to(ROOT)).replace('\\','/'),'git_blob_sha1':'ed4a944d70d49e33c66d0d73f04a2e3a682cb79c','size_bytes':1530,'raw_sha256':'02c01af0276f98e91c992b566c95a33b8354ca57b80fa1cb3c056dc2a7954b06'},*hundred_eight(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(112,112));[chk(self,x) for x in entries];self.assertEqual(self.s['bound_predecessor_identity_count'],112)
  self.assertTrue(self.s['expected_git_head_explicitly_selected_from_externally_reviewed_pass_commit'] and self.s['expected_git_head_automatic_current_head_derivation_forbidden'] and self.s['artifact_canonical_schema_and_identity_verified'] and self.s['dependency_graph_acyclic']);self.assertFalse(self.s['self_hash_present'] or self.s['historical_back_reference_present'] or self.s['persistent_registry_opened'] or self.s['identity_nonce_reserved'] or self.s['constructor_invoked_really'] or self.s['authority_instance_artifact_exists'] or self.s['destination_observed'] or self.s['filesystem_materializer_population_science'] or self.s['locked_test_used'] or self.s['training_or_calibration_authorized']);self.assertEqual(self.s['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs_in_upstream(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes())
  for x in [self.b['reviewed_contract'],self.b['contract_external_seal'],*hundred_eight(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(A.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
