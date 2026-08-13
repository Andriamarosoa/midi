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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_identity_binding import ninety_six
ROOT=Path(__file__).resolve().parents[1];C=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_real_invocation_authorization_contract.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_real_invocation_authorization_contract_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def hundred(chain):
 binding=json.loads((ROOT/chain[2]['path']).read_bytes());roots=binding['upstream_roots'];contract_binding=json.loads((ROOT/roots[0]['path']).read_bytes());contract=json.loads((ROOT/contract_binding['reviewed_contract']['path']).read_bytes());return [*roots,contract_binding['reviewed_contract'],contract_binding['contract_external_seal'],*ninety_six(contract)]
class TestContract(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.cr=C.read_bytes();cls.sr=S.read_bytes();cls.c=json.loads(cls.cr);cls.s=json.loads(cls.sr)
 def test_canonical_contract_seal_and_104_exact(self):
  for raw in (self.cr,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['contract']);chain=self.c['reviewed_and_sealed_constructor_chain'];entries=[*chain,*hundred(chain)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(104,104));[chk(self,x) for x in entries]
 def test_order_guards_authorization_state_and_edges(self):
  expected=['load_distinct_reviewed_and_sealed_execution_authority_artifact','validate_expected_git_head_exact_native_lowercase_hex40','verify_runtime_head_equals_expected_git_head_and_clean_worktree','rehash_all_one_hundred_four_predecessor_identities','validate_exact_native_runtime_types_before_magic_methods','validate_canonical_top_level_and_nested_orders_and_values','validate_strict_timestamp_nonce_issuer_destination_and_id_derivation','open_persistent_identity_nonce_registry','atomically_reserve_identity_and_nonce_terminally','invoke_constructor_once','verify_canonical_bytes_match_reserved_identity','first_destination_observation_probes_absence','create_exclusive_without_overwrite','terminal_success_or_terminal_post_reservation_failure_without_retry'];self.assertEqual(self.c['future_fail_closed_order'],expected);self.assertTrue(all(self.c['preserved_constructor_guards'].values()))
  artifact=self.c['future_execution_authority_artifact_requirement'];preflight=self.c['future_git_preflight'];self.assertTrue(all(artifact.values()));self.assertTrue(all(preflight.values()));self.assertLess(expected.index('verify_runtime_head_equals_expected_git_head_and_clean_worktree'),expected.index('rehash_all_one_hundred_four_predecessor_identities'));self.assertLess(expected.index('rehash_all_one_hundred_four_predecessor_identities'),expected.index('open_persistent_identity_nonce_registry'))
  allowed={'contract_and_external_seal_creation_authorized'}
  for k,v in self.c['authorization'].items():self.assertIs(v,k in allowed,k)
  for k,v in self.c['current_state'].items():self.assertIs(v,k=='real_invocation_authorization_contract_exists',k)
  graph=self.c['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_four_predecessor_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual(self.c['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  chain=self.c['reviewed_and_sealed_constructor_chain']
  for x in [*chain,*hundred(chain)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(C.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
