# H25 — harness administratif pré-claim

## Autorisation

La revue externe du contrat `158d6356…` a autorisé uniquement :

```text
AUTHORIZED_TO_DEFINE_AND_IMPLEMENT_H25_PRECLAIM_ADMINISTRATIVE_LIFECYCLE_QUALIFICATION_HARNESS_ONLY
```

Cette étape implémente et teste le harness. Elle n'exécute aucune qualification
enregistrée et ne crée aucune autorité scientifique.

## Fichiers exécutables

```text
src/polyphonic/harmonic_censoring_h25_lifecycle_qualification.py
64327 octets
SHA-256 e2581ec3f4c50e3229fc1f0d87768597941c3db7d7005e48bf6dbe31e0f703e0

tests/test_harmonic_censoring_h25_lifecycle_qualification.py
17491 octets
SHA-256 081a4e2ee291ae6c3c4f68a4067e456b51dd9727b3e717d569a2f1ac0bca8dcf
```

Le module utilise uniquement la bibliothèque standard. Un test AST vérifie
l'absence de NumPy, `threading`, `multiprocessing` et d'import H24.

## Cycle implémenté

Chaque scénario utilise un nouveau namespace absolu `h25-admin-*` :

```text
preflight
→ surrogate claim O_EXCL
→ P0_boundary
→ P1_boundary
→ P2_boundary
→ success / failure / inconclusive
```

Le claim substitutif archive explicitement :

```text
scientific_capability_issued = false
scientific_claim_created = false
scientific_population_used = false
real_data_used = false
locked_test_used = false
training_authorized = false
```

Après chaque append, le transcript est relu et sa chaîne SHA-256 est
recalculée. Chaque frontière possède une preuve JSON canonique liée dans le
record. La recomputation publique relit claim, transcript, evidence et terminal
ou reçu forensique ; elle refuse toute dérive de hash, ordre, identité ou
frontière scientifique.

## Fermetures

Le nominal publie atomiquement staging vers success puis un terminal. Une
failure logique et une erreur opérationnelle conservent des états distincts.
Les erreurs de publication qui empêchent un terminal produisent un reçu
forensique lié au claim et aux octets de transcript encore disponibles.

Les états possibles sont :

```text
H25_ADMIN_LIFECYCLE_QUALIFIED
H25_ADMIN_LIFECYCLE_LOGICAL_FAILURE
H25_ADMIN_LIFECYCLE_INCONCLUSIVE_CONSUMED
H25_ADMIN_LIFECYCLE_PRECLAIM_ABORTED_NOT_CONSUMED
H25_ADMIN_LIFECYCLE_FORENSIC_INCONCLUSIVE_CONSUMED
```

## Inverses couverts

Les `19` scénarios exacts couvrent :

- nominal, failure logique P1 et erreur opérationnelle P1 ;
- EOF avant/après claim substitutif ;
- déconnexion du parent SSH et `SIGINT` après claim ;
- timeout preflight, claim, P0, P1, P2 et les trois fermetures ;
- échec d'écriture evidence ;
- échec de publication transcript, terminal ou renommage success.

Les scénarios pré-claim ne consomment aucun claim substitutif. Tous les
scénarios post-claim aboutissent à un terminal ou reçu forensique
préenregistré, sans retry ni suppression du claim.

## Correction de la couverture OS

La revue de `3d755c9c…` a refusé de compter les exceptions déterministes comme
preuve d'EOF, déconnexion, signal ou timeout réels. Le correctif ajoute donc
`13` probes OS jetables :

- le worker est lancé par `python -m`, depuis un fichier de configuration ;
- stdin est exclusivement un canal de contrôle, jamais le transport du script ;
- le parent ferme réellement le pipe avant ou après claim pour produire EOF ;
- un parent de transport intermédiaire quitte réellement avec `os._exit(0)`
  après claim, et le worker orphelin ferme l'exécution sur EOF ;
- le contrôleur envoie un vrai `SIGINT`/`SIGBREAK` au groupe du worker ;
- chaque timeout attend une durée monotonic réelle avant d'envoyer sa
  notification au point exact de la phase ;
- le contrôleur attend l'exit code, vérifie que le PID est mort, puis lie config,
  log, marqueur d'exit et résultat recomputé dans un reçu canonique ;
- la recomputation refuse toute altération du reçu, de la config ou du log.

Les probes déterministes antérieurs restent des tests unitaires, mais ne sont
plus présentés comme preuve OS.

## Validation locale

```text
python -m py_compile \
  src/polyphonic/harmonic_censoring_h25_lifecycle_qualification.py \
  tests/test_harmonic_censoring_h25_lifecycle_qualification.py

python -m unittest tests.test_harmonic_censoring_h25_lifecycle_qualification -v

Windows : 16 tests réussis en 6,394 s
git diff --check réussi
```

Sous le PTY Windows, le probe `SIGINT` est omis car la livraison console au
nouveau groupe n'est pas fiable. Le même test OS complet a donc été exécuté sur
le Mac arm64 cible depuis `/tmp/h25-lifecycle-harness-test` :

```text
test_real_OS_transport_signal_and_timeout_probes_terminate ... ok
Ran 1 test in 1,764 s
```

Ce test Mac parcourt les `13` probes, y compris le vrai `SIGINT`. Les tests
Windows et Mac créent uniquement des répertoires temporaires jetables et ne
constituent pas la qualification administrative enregistrée.

## Interdictions maintenues

Aucune capability ou claim H25 scientifique, population/manifest H25,
waveform, P0/P1/P2 scientifique, donnée réelle, H17, locked-test, modèle,
checkpoint, calibration ou entraînement n'a été utilisé ou autorisé.

La prochaine action est uniquement la revue externe de cette implémentation.
