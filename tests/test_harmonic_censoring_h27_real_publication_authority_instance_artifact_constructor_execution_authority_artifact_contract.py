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
C=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract.json'
S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_execution_authority_artifact_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()));return raw
class TestExecutionAuthorityArtifactContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cr=C.read_bytes();cls.sr=S.read_bytes();cls.c=json.loads(cls.cr);cls.s=json.loads(cls.sr)
 def test_canonical_seal_and_exact_108_predecessors(self):
  for raw in (self.cr,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['contract']);chain=self.c['reviewed_and_sealed_invocation_authorization_chain'];up=json.loads((ROOT/chain[0]['path']).read_bytes());entries=[*chain,*hundred_four(up)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(108,108));[chk(self,x) for x in entries]
 def test_closed_schema_head_binding_state_and_edges(self):
  s=self.c['future_artifact_schema'];self.assertEqual(s['exact_top_level_field_order'],['schema_version','artifact_type','execution_authority_artifact_id','expected_git_head','authorization_chain_identity','single_use','consumed']);self.assertEqual(s['authorization_chain_identity_exact_fields'],['contract_git_blob_sha1','contract_size_bytes','contract_raw_sha256','binding_git_blob_sha1','binding_size_bytes','binding_raw_sha256']);self.assertIs(type(s['schema_version_exact_integer']),int);self.assertEqual(s['schema_version_exact_integer'],1);self.assertEqual(s['artifact_type_exact'],'h27_constructor_real_invocation_execution_authority');self.assertIs(s['execution_authority_artifact_id_lowercase_hex64'],True);self.assertEqual(s['execution_authority_artifact_id_namespace'],'H27_CONSTRUCTOR_REAL_INVOCATION_EXECUTION_AUTHORITY_V1');self.assertTrue(s['expected_git_head_exact_native_string'] and s['expected_git_head_lowercase_hex40'] and s['expected_git_head_value_must_be_explicitly_supplied_in_distinct_later_reviewed_artifact_commit'] and s['current_head_fallback_or_automatic_selection_forbidden']);self.assertNotIn('expected_git_head',self.c)
  self.assertEqual(s['execution_authority_artifact_id_derivation'],'lowercase_hex(sha256(ascii(namespace + NUL + expected_git_head + NUL + authorization_chain_identity.contract_raw_sha256 + NUL + authorization_chain_identity.binding_raw_sha256)))');chain=self.c['reviewed_and_sealed_invocation_authorization_chain'];v=s['authorization_chain_identity_exact_values'];self.assertEqual(list(v),s['authorization_chain_identity_exact_fields']);self.assertEqual(v,{'contract_git_blob_sha1':chain[0]['git_blob_sha1'],'contract_size_bytes':chain[0]['size_bytes'],'contract_raw_sha256':chain[0]['raw_sha256'],'binding_git_blob_sha1':chain[2]['git_blob_sha1'],'binding_size_bytes':chain[2]['size_bytes'],'binding_raw_sha256':chain[2]['raw_sha256']})
  self.assertIs(s['single_use_exact_boolean'],True);self.assertIs(s['consumed_initial_exact_boolean'],False)
  for key in ('unknown_or_missing_fields_rejected','duplicate_json_keys_rejected','non_finite_json_values_rejected','object_key_order_must_equal_exact_top_level_field_order','nested_object_key_order_must_equal_authorization_chain_identity_exact_fields','canonical_utf8_lf_no_bom_compact_json_preserving_exact_field_order'):self.assertIs(s[key],True,key)
  rules=self.c['future_artifact_rules'];self.assertEqual(list(rules),['all_one_hundred_eight_predecessor_identities_rehashed_before_artifact_input_parse','exact_native_types_before_magic_methods','artifact_id_and_expected_git_head_bound_by_canonical_bytes_and_external_seal','artifact_creation_requires_distinct_later_commit_and_external_review','artifact_strictly_single_use_and_non_reusable','no_registry_reservation_invocation_or_destination_observation_at_contract_step']);self.assertTrue(all(value is True for value in rules.values()))
  self.assertEqual(self.s['reviewed_invocation_authorization_binding_commit'],'a786d5730b488694728088368a33e7584f8f13e7');self.assertEqual(self.s['bound_predecessor_identity_count'],108)
  for key in ('expected_git_head_schema_defined_without_value','execution_authority_artifact_identity_derivation_defined','authorization_chain_identity_exact','dependency_graph_acyclic'):self.assertIs(self.s[key],True,key)
  for key in ('self_hash_present','historical_back_reference_present','execution_authority_artifact_exists','expected_git_head_value_selected','persistent_registry_opened','identity_nonce_reserved','constructor_invoked_really','authority_instance_artifact_exists','destination_observed','filesystem_materializer_population_science','locked_test_used','training_or_calibration_authorized'):self.assertIs(self.s[key],False,key)
  for k,v in self.c['current_state'].items():self.assertIs(v,k=='execution_authority_artifact_contract_exists',k)
  graph=self.c['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_eight_predecessor_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual(self.c['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_historical_back_reference(self):
  chain=self.c['reviewed_and_sealed_invocation_authorization_chain'];up=json.loads((ROOT/chain[0]['path']).read_bytes())
  for x in [*chain,*hundred_four(up)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(C.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
