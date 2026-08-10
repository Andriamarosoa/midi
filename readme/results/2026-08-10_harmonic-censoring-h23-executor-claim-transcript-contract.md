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
taille       14 736 octets
SHA-256 brut 0a333f6fea4ab9b8dcf94384fd19cc9f019a5f36016e4e03078c5ac797e25ed3
blob Git     fc3ec602d5ba0a623d454cb3c5d2a0bb883ba74a
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
taille       10 872 octets
SHA-256 brut db7551362cca36c3040d5b0d7b4482965504de210f9e2ad67c2799d89b52c388
blob Git     20df650d9338adccd0b7894e5b533465956f3627
```

Les `10` tests ne font que parser le JSON et vérifier ses invariants. Aucun
module scientifique, actif, modèle, waveform ou population n’est utilisé.

Résultats : `10` tests ciblés réussis en `0,001 s`, puis `68` tests
H23/H17/H20 réussis en `0,835 s`. `json.tool`, `py_compile` et
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
