from __future__ import annotations
import hashlib,json
from pathlib import Path
import unittest
from tests.test_harmonic_censoring_h27_constructor_execution_gate_control_bundle_creation_contract_identity_binding import hundred_twenty
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract.json';S=ROOT/'configs/harmonic_censoring_h27_control_bundle_creation_authority_artifact_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
class TestBundleCreationAuthorityArtifactContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cr=C.read_bytes();cls.sr=S.read_bytes();cls.c=json.loads(cls.cr);cls.s=json.loads(cls.sr)
 def test_exact_seal_and_124_predecessors(self):
  for raw in (self.cr,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['contract']);roots=self.c['reviewed_and_sealed_bundle_creation_contract_chain'];contract=json.loads((ROOT/roots[0]['path']).read_bytes());entries=[*roots,*hundred_twenty(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(124,124));[chk(self,x) for x in entries]
 def test_closed_schema_rules_and_state(self):
  self.assertEqual(self.c['future_artifact_canonical_top_level_order'],['schema_version','artifact_type','creation_authority_artifact_id','expected_execution_git_head','authorization_chain_identity','bundle_definition_identity','single_use','consumed']);schema=self.c['future_artifact_schema'];self.assertEqual(list(schema),self.c['future_artifact_canonical_top_level_order']);self.assertEqual(schema['artifact_type']['exact_value'],'h27_immutable_control_bundle_creation_authority');self.assertEqual(schema['bundle_definition_identity']['final_bundle_root_exact'],'/Users/amcarene/h27-admin/control/h27-constructor-execution-gate-v1');self.assertTrue(schema['single_use']['exact_value']);self.assertFalse(schema['consumed']['exact_value']);self.assertEqual(list(self.c['future_artifact_rules']),['strict_json_no_duplicate_keys_no_nan_no_infinity','canonical_utf8_lf_no_bom','exact_top_level_and_nested_key_order_required','unknown_or_missing_field_rejected','artifact_id_unique_in_persistent_registry','separate_real_artifact_commit_external_review_and_seal_required','artifact_creation_does_not_create_or_observe_bundle','consumption_only_by_future_reviewed_bundle_creator','post_consumption_failure_terminal','retry_after_consumption_forbidden']);self.assertTrue(all(self.c['future_artifact_rules'].values()))
  allowed={'control_bundle_creation_authority_artifact_contract_exists'}
  for k,v in self.c['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.c['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_twenty_four_predecessor_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual((self.s['bound_predecessor_identity_count'],self.s['single_use'],self.s['future_artifact_exists'],self.s['public_edges_closed']),(124,True,False,8));self.assertFalse(any(self.s[k] for k in ('administrative_control_bundle_exists','bundle_path_observed','filesystem_operation_authorized','persistent_registry_opened','authority_consumed','science_or_locked_test')))
 def test_no_backrefs(self):
  roots=self.c['reviewed_and_sealed_bundle_creation_contract_chain'];contract=json.loads((ROOT/roots[0]['path']).read_bytes())
  for x in [*roots,*hundred_twenty(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(C.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
