# H23 — implémentation dormante de la capability et du runner

## Autorisation

La revue externe du contrat corrigé `ee00bcf6115a42cb550f6aac855d032f55cbf62e`
a conclu `APPROUVÉ` et autorisé uniquement l’implémentation de la capability et
du runner en mode dormant. Cette étape n’ajoute aucun seal, n’émet aucune
capability, ne crée aucun marker, ne synthétise aucune waveform et n’exécute
aucun test P0/P1/P2.

## Fichiers d’exécution ajoutés

```text
src/polyphonic/harmonic_censoring_h23_execution_capability.py
taille       24 259 octets
SHA-256 brut b82e385b097b5eddf99ee5d45b80c81076ea3b711f6add719b4df42fa97b0c8e
blob Git     5e9f6c9865c55bbaa0504c99083d410d5ccb0aa2

src/polyphonic/run_harmonic_censoring_h23_synthetic.py
taille       9 403 octets
SHA-256 brut 1ea448deb56dc29a1d489485e76b5c4019cf5cfe9df97a3704c22f13c942c7f5
blob Git     6fbdd8b92210429a7da1b8ac35d91942df16188d
```

Les deux sources sont forcées en LF par `.gitattributes`. Elles n’importent ni
NumPy, ni TensorFlow, ni loader de données, ni décodeur.

## Capability fail-closed

`AttestedH23SyntheticExecutionCapability` possède un constructeur privé, est
immuable, non copiable, non sérialisable et n’est reconnue que par identité via
un registre faible process-local. Une dataclass, un mapping, un clone
`object.__new__`, `copy`, `deepcopy`, `pickle` ou `dataclasses.replace` ne donne
aucune autorité.

Le futur parser de seal exige séparément les six droits :

```text
capability_issuance_authorized
synthetic_execution_authorized
scientific_execution_authorized
P0_execution_authorized
P1_execution_authorized
P2_execution_authorized
```

Il refuse aussi tout droit data/train/H17/locked-test, lie les contrats et les
manifests, le commit d’implémentation, son ensemble exact de fichiers, les deux
blobs source, le runtime et trois chemins one-shot distincts.

Dans ce commit :

```text
H23_AUTHORIZATION_SEAL_SHA256 = None
```

La factory échoue donc dès sa première instruction, avant résolution du plan,
inspection NumPy, accès aux destinations ou claim. Le fichier de seal réservé
n’existe pas.

## Claim et runner dormants

Le mécanisme futur de claim est codé en `O_EXCL`, persiste
`synthetic_population_consumed=true` et ne supprime jamais le marker après une
erreur. Il est toutefois inatteignable sans capability attestée.

Le runner conserve explicitement :

```text
PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED = false
```

Il ne référence pas la fonction de claim. Même un objet attesté futur serait
refusé avant consommation tant qu’un exécuteur scientifique séparément revu
n’existe pas.

Les seules fonctions actives sont administratives et pures : elles valident un
préfixe de tests déjà résolus, construisent l’un des trois terminaux scellés et
publient un JSON par staging + rename atomique :

- succès uniquement avec les `72` tests ;
- kill scientifique avec premier échec et suffixe `NOT_RUN_BY_KILL_RULE` ;
- incident opérationnel `H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED`, sans verdict
  scientifique.

## Vérifications autorisées

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest tests.test_harmonic_censoring_h23_execution_dormant
```

Résultat : `11 tests réussis en 0,029 s`.

La suite contractuelle élargie H23/H17/H20 donne `53 tests réussis en 0,605 s`.
`py_compile` et `git diff --check` réussissent.

Les tests utilisent uniquement des mappings synthétiques, le resolver dormant
déjà approuvé et des répertoires temporaires. Ils ne synthétisent aucun son et
ne chargent aucun actif, modèle ou population.

## État

```text
capability_code_implemented             true
runner_administrative_shell_implemented true
production_scientific_executor          false
authorization_seal_exists               false
capability_issued                       false
consumption_claimed                     false
waveforms_synthesized                   false
P0_P1_P2_executed                       false
real_data_used                          false
H17_population_used                     false
locked_test_used                        false
training_authorized                     false
```

La prochaine étape est la revue externe de ce commit d’implémentation. Aucun
seal ne peut être défini avant cette revue, et aucune exécution n’est autorisée.
