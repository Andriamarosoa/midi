# H23 — contrat claim, exécuteur scientifique et transcript

## Autorisation et portée

La revue externe de `84179a1d166e5719c0511040357e5b98025a5e4e`
approuve la preuve d’émission administrative et autorise uniquement la
définition contractuelle de la prochaine porte H23.

Ce commit ne modifie aucun source d’exécution, activation ou seal. Il
n’implémente pas le claim, ne crée aucun marker, ne synthétise aucune waveform
et n’exécute aucun test P0/P1/P2.

## Contrat

```text
configs/harmonic_censoring_h23_executor_claim_transcript_contract.json
taille       17 885 octets
SHA-256 brut 2d727fc660e40f601605067ae4d5c0c89e08de7a5efc7b704d8a24e526a10d4c
blob Git     5a81c1c016b0ab596f9ce688346c6a9af0549f5d
```

Le contrat lie les `175` fixtures, les `72` tests `27/35/10`, les quatre SHA
H23, le commit dormant `f384cea…`, l’activation administrative `31b116c…` et la
preuve `84179a1…`. Il déclare explicitement que le seal administratif actuel ne
pourra pas autoriser le futur exécuteur.

## Claim durable

Le claim futur devra utiliser `O_CREAT|O_EXCL|O_WRONLY` en mode `0600`, écrire
un JSON canonique, exécuter `fsync(file)`, fermer le fichier puis
`fsync(directory)` avant toute allocation ou synthèse de waveform.

L’existence seule du marker signifie « population consommée », même si le
fichier est partiel ou corrompu. Le marker ne pourra jamais être supprimé ou
remplacé. Toute erreur après `O_EXCL` interdit définitivement un retry de la
même population.

## Exécuteur fermé aux résultats du caller

L’unique entrée publique future sera :

```text
repository_root + claimed_process_local_capability
```

Le caller ne pourra fournir ni `H23AdministrativeTestResult`, ni booléens
pass/fail, ni sélection de fixtures/tests, ni seuil/tolérance. Les `175` IDs et
les `72` tests ordonnés seront dérivés uniquement du plan H23 résolu.

Claim, exécuteur, writer/verifier de transcript et finalizer devront être
implémentés dans le même commit, puis revus ensemble.

La future capability devra aussi snapshotter de manière immuable et attestée
le commit et le SHA de l’activation, le SHA du seal, les blobs sources, les
contrats/manifests, le runtime et tous les chemins. Après émission, le claim ne
pourra jamais reprendre une valeur d’autorité depuis l’environnement ou une
relecture mutable : une revalidation éventuelle pourra seulement confirmer
l’égalité au snapshot, sinon elle échouera avant `O_EXCL`.

## Transcript autoritatif

Le transcript sera un JSONL canonique LF append-only, chaîné par SHA-256 et
persisté après le marker. Il contiendra :

- un header liant marker, activation, seal, commit/blobs, contrats, manifests,
  runtime et hashes des listes ordonnées ;
- un événement par fixture synthétisée avec hashes spec/waveform/target ;
- un événement par test exécuté avec phase, ordre, décision et hash d’évidence ;
- un terminal avec outcome, compteurs, premier échec, suffixe non exécuté et
  hash du préfixe.

Chaque résultat de test sera `fsync` avant le suivant. Les index seront
contigus et chaque ligne liera le SHA exact de la précédente.

Les quatre types de ligne ont maintenant un envelope exact commun :

```text
schema_version
event_index
event_type
previous_event_sha256
```

Les seules valeurs de `event_type` sont `HEADER`, `FIXTURE_MATERIALIZED`,
`TEST_RESULT` et `TERMINAL`. Chaque type possède un jeu exhaustif de clés ;
aucun champ supplémentaire n’est accepté. Le hash précédent est celui des
octets canoniques exacts de la ligne précédente, LF terminal inclus. Le schéma
d’évidence et le SHA du contrat de test doivent correspondre à l’oracle
préenregistré pour le `test_id`.

## Finalisation depuis les octets persistés

Le finalizer futur n’acceptera aucun résultat ou chemin du caller. Il rouvrira
le marker et le transcript uniquement depuis les chemins de la capability
claimée, rehachera les octets, vérifiera la chaîne complète, les bindings, les
IDs, l’ordre, les comptes et la kill rule.

```text
succès : 72/72 PASS + couverture exacte des 175 fixtures
         → AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL

kill    : préfixe exact jusqu’au premier échec
          + suffixe NOT_RUN_BY_KILL_RULE

incident: H23_EXECUTION_INCONCLUSIVE_FAIL_CLOSED
          sans verdict scientifique
```

`AUTHORIZED_TO_PREPARE_TRAIN_PROTOCOL` ne signifie jamais
`TRAIN_AUTHORIZED`.

## Nouvelle chaîne d’autorisation obligatoire

Après revue de ce contrat :

```text
commit unique claim+executor+transcript
→ revue externe
→ nouveau seal+activation liant les nouveaux blobs
→ revue externe
→ worker exact
→ claim durable
→ une seule exécution scientifique
```

Le couple activation/seal de `31b116c…` est explicitement non réutilisable.

## Tests purs

```text
tests/test_harmonic_censoring_h23_executor_claim_transcript_contract.py
taille       13 373 octets
SHA-256 brut a36fe080c0f68bf73bdbd8789df20193579d66e83dd0356618367d22d430fa5c
blob Git     69bb0bcbc8f7813db5fb041b4236e595a875f589
```

Les `11` tests ne font que parser le JSON et vérifier ses invariants. Aucun
module scientifique, actif, modèle, waveform ou population n’est utilisé.

Résultats : `11` tests ciblés réussis en `0,002 s`, puis `69` tests
H23/H17/H20 réussis en `0,827 s`. `json.tool`, `py_compile` et
`git diff --check` réussissent.

## État

```text
contract_only                              true
claim_implementation_authorized            false
scientific_executor_implementation_authorized false
transcript_implementation_authorized       false
claim_authorized                           false
marker_created                             false
synthetic_population_consumed              false
waveforms_synthesized                      false
P0_P1_P2_executed                          false
real_data_used                             false
H17_population_used                        false
locked_test_used                           false
training_authorized                        false
```

La prochaine action est exclusivement la revue externe de ce contrat.
