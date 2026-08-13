from __future__ import annotations
import hashlib,json
from pathlib import Path
import subprocess,unittest
from src.polyphonic import harmonic_censoring_h27_activation_capable_production_materializer_dormant as m
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_dormant as a
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_publication_dormant as p
from src.polyphonic import harmonic_censoring_h27_future_bridge_activation_artifact_real_publication_dormant as r
from src.polyphonic import harmonic_censoring_h27_future_bridge_dormant as b
from src.polyphonic import harmonic_censoring_h27_future_bridge_operational_activation_connection_dormant as g
from src.polyphonic import harmonic_censoring_h27_issuer_authority_claim_capability_dormant as q
from src.polyphonic import harmonic_censoring_h27_one_shot_execution_composition_dormant as c
from tests.test_harmonic_censoring_h27_real_publication_one_shot_authority_issuer_one_shot_real_execution_authority_instance_artifact_contract_identity_binding import _ninety_two
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_instance_artifact_constructor_implementation_contract.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_instance_artifact_constructor_implementation_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
class TestContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.c=json.loads(C.read_bytes());cls.s=json.loads(S.read_bytes())
 def test_96_exact(self):
  chk(self,self.s['contract']);roots=self.c['reviewed_and_sealed_authority_instance_artifact_chain'];ac=json.loads((ROOT/roots[0]['path']).read_bytes());entries=[*roots,*_ninety_two(ac)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(96,96));[chk(self,x) for x in entries]
 def test_boundary_closed(self):
  z=self.c['future_constructor_boundary'];self.assertEqual(z['module_path'],'src/polyphonic/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor.py');self.assertEqual(z['entrypoint'],'construct_h27_real_publication_authority_instance_artifact');self.assertIs(z['module_must_not_exist_at_contract_step'],True);self.assertNotEqual(subprocess.run(['git','cat-file','-e','c80a7c73264ece3354f1f8e03acecd0f061d99a0:'+z['module_path']],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode,0)
  guards=('all_ninety_six_identities_rehashed_before_any_future_input_parse','exact_native_input_types_required_before_magic_methods','canonical_top_level_and_nested_orders_preserved','authority_instance_id_derivation_preserved','identity_nonce_persistent_uniqueness_and_terminal_reservation_preserved','constructor_implementation_requires_distinct_later_commit_and_external_review')
  for guard in guards:self.assertIs(z[guard],True,guard)
  ac=json.loads((ROOT/self.c['reviewed_and_sealed_authority_instance_artifact_chain'][0]['path']).read_bytes());schema=ac['future_artifact_schema'];rules=ac['future_instance_rules']
  self.assertEqual(schema['exact_top_level_field_order'],['schema_version','artifact_type','authority_instance_id','issuer_id','issued_at_utc','invocation_nonce','canonical_destination_path','sealed_chain_identity','single_use','consumed'])
  self.assertEqual(schema['sealed_chain_identity_exact_fields'],['contract_git_blob_sha1','contract_size_bytes','contract_raw_sha256','binding_git_blob_sha1','binding_size_bytes','binding_raw_sha256'])
  self.assertEqual(schema['authority_instance_id_derivation'],'lowercase_hex(sha256(ascii(namespace + NUL + issuer_id + NUL + issued_at_utc + NUL + invocation_nonce + NUL + canonical_destination_path + NUL + sealed_chain_identity.contract_raw_sha256 + NUL + sealed_chain_identity.binding_raw_sha256)))')
  for key in ('object_key_order_must_equal_exact_top_level_field_order','nested_object_key_order_must_equal_sealed_chain_identity_exact_fields','authority_instance_id_unique_in_namespace_and_never_reusable','invocation_nonce_unique_in_h27_namespace_and_never_reusable','persistent_used_identity_and_nonce_registry_required_before_creation','identity_or_nonce_reserved_terminally_before_artifact_publication','unknown_or_missing_fields_rejected','duplicate_json_keys_rejected','non_finite_json_values_rejected'):self.assertIs(schema[key],True,key)
  self.assertIs(rules['creation_grant_and_consumption_require_distinct_later_commit_and_external_review'],True)
  for k,v in self.c['current_state'].items():self.assertIs(v,k=='constructor_contract_exists',k)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_graph_and_backrefs(self):
  z=self.c['dependency_graph'];self.assertTrue(z['acyclic']);self.assertFalse(z['self_hash_present'] or z['historical_back_reference_present']);roots=self.c['reviewed_and_sealed_authority_instance_artifact_chain'];ac=json.loads((ROOT/roots[0]['path']).read_bytes())
  for x in [*roots,*_ninety_two(ac)]:self.assertNotIn(C.name.encode(),(ROOT/x['path']).read_bytes());self.assertNotIn(S.name.encode(),(ROOT/x['path']).read_bytes())
if __name__=='__main__':unittest.main()
