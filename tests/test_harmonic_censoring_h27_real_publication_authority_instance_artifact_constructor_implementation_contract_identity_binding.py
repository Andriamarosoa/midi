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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_implementation_contract import _ninety_two
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_instance_artifact_constructor_implementation_contract_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_one_shot_authority_instance_artifact_constructor_implementation_contract_identity_binding_external_seal.json'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
def ninety_six(contract):
 roots=contract['reviewed_and_sealed_authority_instance_artifact_chain'];artifact_contract=json.loads((ROOT/roots[0]['path']).read_bytes());return [*roots,*_ninety_two(artifact_contract)]
class TestBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_98_exact(self):
  for raw in (self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  chk(self,self.s['identity_binding']);contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());entries=[self.b['reviewed_contract'],self.b['contract_external_seal'],*ninety_six(contract)];self.assertEqual((len(entries),len({x['path'] for x in entries})),(98,98));[chk(self,x) for x in entries]
 def test_guards_boundary_state_and_edges(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes());self.assertEqual(self.b['preserved_constructor_guards'],{k:True for k in ('all_ninety_six_identities_rehashed_before_any_future_input_parse','exact_native_input_types_required_before_magic_methods','canonical_top_level_and_nested_orders_preserved','authority_instance_id_derivation_preserved','identity_nonce_persistent_uniqueness_and_terminal_reservation_preserved','constructor_implementation_requires_distinct_later_commit_and_external_review')});self.assertEqual(self.b['preserved_constructor_guards'],{k:contract['future_constructor_boundary'][k] for k in self.b['preserved_constructor_guards']})
  z=self.b['future_constructor_boundary'];self.assertEqual(z['module_path'],contract['future_constructor_boundary']['module_path']);self.assertEqual(z['entrypoint'],contract['future_constructor_boundary']['entrypoint']);self.assertIs(z['module_must_remain_absent'],True);self.assertNotEqual(subprocess.run(['git','cat-file','-e','1f46498d94949efe1a1c380a85fa046538fd8e94:'+z['module_path']],cwd=ROOT,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL).returncode,0)
  allowed={'constructor_contract_exists','constructor_contract_externally_reviewed','constructor_contract_externally_sealed','constructor_contract_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_ninety_eight_bound_identities_rehashed']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual(self.b['public_edges_closed'],8)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
 def test_no_backrefs(self):
  contract=json.loads((ROOT/self.b['reviewed_contract']['path']).read_bytes())
  for x in [self.b['reviewed_contract'],self.b['contract_external_seal'],*ninety_six(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw)
if __name__=='__main__':unittest.main()
