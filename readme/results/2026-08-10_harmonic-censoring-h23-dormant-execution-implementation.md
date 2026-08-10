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
taille       21 335 octets
SHA-256 brut de20cab9d542426af6b772ca60ce4af4a13ec67023ef36b6b8aecefcb884a25e
blob Git     e280aac30f5cde835989c177b45d850e9ed9199b

src/polyphonic/run_harmonic_censoring_h23_synthetic.py
taille       15 057 octets
SHA-256 brut cf2cf6c0fa3b9e3b48a1607d03174eacdd3511c3db790b154c4e00673dadd0d6
blob Git     3699212be4db17df99acfddb864c0a25f56dcea4
```

Les deux sources sont forcées en LF par `.gitattributes`. Elles n’importent ni
NumPy, ni TensorFlow, ni loader de données, ni décodeur.

## Capability fail-closed

`AttestedH23SyntheticExecutionCapability` refuse toute construction publique,
est immuable, non copiable et non sérialisable. La construction et le registre
faible process-local sont enfermés dans une closure unique : aucun token,
registre ou helper d’attestation n’est exposé comme attribut du module. Une
dataclass, un mapping, un clone
`object.__new__`, `copy`, `deepcopy`, `pickle` ou `dataclasses.replace` ne donne
aucune autorité.

Cette closure n’est pas présentée comme une frontière contre une introspection
CPython hostile. Le contrat limite désormais explicitement ce mécanisme aux API
supportées et exige un worker mono-usage sans code non fiable. Une frontière OS
sera obligatoire avant d’élargir ce modèle de menace.

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

Le claim n’est plus seulement inatteignable : il est explicitement **non
implémenté** dans ce commit :

```text
H23_CONSUMPTION_CLAIM_IMPLEMENTED = false
```

Son API publique lève inconditionnellement `PermissionError` et ne contient
aucun chemin `O_EXCL`, marker ou registre claimed. Le claim persistant devra
être ajouté dans le même futur commit revu que l’exécuteur scientifique.

Le runner conserve explicitement :

```text
PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED = false
```

Il ne référence pas la fonction de claim. Même un objet attesté futur serait
refusé avant consommation tant qu’un exécuteur scientifique séparément revu
n’existe pas.

Les seules fonctions actives sont administratives et pures : elles valident un
préfixe de tests déjà résolus et construisent des **brouillons explicitement
non autoritatifs**, sans champ `global_go_status`. Un brouillon ne porte que
`proposed_global_go_status` :

- succès uniquement avec les `72` tests ;
- kill scientifique avec premier échec et suffixe `NOT_RUN_BY_KILL_RULE` ;
- incident opérationnel `H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED`, sans verdict
  scientifique.

Le code de future finalisation sait vérifier une capability claimée, relire le
marker réel, reconstruire le draft et forcer la destination scellée. Mais il
commence maintenant par refuser inconditionnellement tant que
`PRODUCTION_H23_SCIENTIFIC_EXECUTOR_IMPLEMENTED=false` ou que le claim n’est pas
implémenté. Il n’existe donc dans ce commit aucun chemin vers
`authoritative=true` ou `global_go_status`, même avec une capability légitime.

## Vérifications autorisées

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest tests.test_harmonic_censoring_h23_execution_dormant
```

Résultat : `11 tests réussis en 0,015 s`.

La suite contractuelle élargie H23/H17/H20 donne `53 tests réussis en 0,658 s`.
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
