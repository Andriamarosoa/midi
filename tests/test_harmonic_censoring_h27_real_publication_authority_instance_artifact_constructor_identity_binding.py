from __future__ import annotations
import hashlib,json,subprocess
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
from tests.test_harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_implementation_contract_identity_binding import ninety_six
ROOT=Path(__file__).resolve().parents[1];B=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_identity_binding.json';S=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_identity_binding_external_seal.json';MS=ROOT/'configs/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor_external_review_seal.json';MODULE=ROOT/'src/polyphonic/harmonic_censoring_h27_real_publication_authority_instance_artifact_constructor.py'
def blob(x):return hashlib.sha1(b'blob '+str(len(x)).encode()+b'\0'+x).hexdigest()
def chk(t,x):
 raw=(ROOT/x['path']).read_bytes();t.assertEqual((x['git_blob_sha1'],x['size_bytes'],x['raw_sha256']),(blob(raw),len(raw),hashlib.sha256(raw).hexdigest()))
class TestBinding(unittest.TestCase):
 @classmethod
 def setUpClass(cls):cls.br=B.read_bytes();cls.sr=S.read_bytes();cls.mr=MS.read_bytes();cls.b=json.loads(cls.br);cls.s=json.loads(cls.sr)
 def test_exact_module_and_canonical_admin_files(self):
  for raw in (self.mr,self.br,self.sr):self.assertNotIn(b'\r',raw);self.assertFalse(raw.startswith(b'\xef\xbb\xbf'));self.assertTrue(raw.endswith(b'\n'))
  reviewed=self.b['reviewed_effect_free_implementation'];committed=subprocess.run(['git','show',f"{reviewed['reviewed_commit']}:{reviewed['path']}"],cwd=ROOT,check=True,capture_output=True).stdout;self.assertEqual(committed,MODULE.read_bytes());chk(self,reviewed);chk(self,self.b['implementation_external_review_seal']);chk(self,self.s['identity_binding'])
 def test_100_predecessors_and_102_bound_paths(self):
  roots=self.b['upstream_roots'];contract_binding=json.loads((ROOT/roots[0]['path']).read_bytes());contract=json.loads((ROOT/contract_binding['reviewed_contract']['path']).read_bytes());expanded=[contract_binding['reviewed_contract'],contract_binding['contract_external_seal'],*ninety_six(contract)];predecessors=[*roots,*expanded];bound=[self.b['reviewed_effect_free_implementation'],self.b['implementation_external_review_seal'],*predecessors];self.assertEqual((len(expanded),len(predecessors),len(bound)),(98,100,102));self.assertEqual(len({x['path'] for x in bound}),102);[chk(self,x) for x in bound]
 def test_guards_graph_state_edges_and_backrefs(self):
  self.assertTrue(all(self.b['preserved_guards'].values()));allowed={'constructor_module_exists','constructor_module_externally_reviewed','constructor_module_externally_sealed','constructor_identity_binding_exists'}
  for k,v in self.b['current_state'].items():self.assertIs(v,k in allowed,k)
  graph=self.b['dependency_graph'];self.assertTrue(graph['acyclic'] and graph['all_one_hundred_predecessor_identities_rehashed'] and graph['all_one_hundred_two_bound_identities_unique']);self.assertFalse(graph['self_hash_present'] or graph['historical_back_reference_present']);self.assertEqual(self.b['public_edges_closed'],8)
  roots=self.b['upstream_roots'];contract_binding=json.loads((ROOT/roots[0]['path']).read_bytes());contract=json.loads((ROOT/contract_binding['reviewed_contract']['path']).read_bytes())
  for x in [*roots,contract_binding['reviewed_contract'],contract_binding['contract_external_seal'],*ninety_six(contract)]:raw=(ROOT/x['path']).read_bytes();self.assertNotIn(B.name.encode(),raw);self.assertNotIn(S.name.encode(),raw);self.assertNotIn(MS.name.encode(),raw)
  for e in (c.execute_h27_one_shot_composition,b.invoke_h27_future_bridge,g.activate_and_connect_h27_future_bridge,a.construct_h27_future_bridge_activation_artifact,p.simulate_h27_future_bridge_activation_artifact_publication,r.publish_h27_future_bridge_activation_artifact_real,q.issue_h27_materialization_authority_and_capability,m.materialize_h27_activation_capable_production_population):self.assertIs(type(e),type(().__getitem__))
if __name__=='__main__':unittest.main()
