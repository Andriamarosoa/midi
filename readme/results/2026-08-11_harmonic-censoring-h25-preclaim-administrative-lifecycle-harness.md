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
32935 octets
SHA-256 40d90373ac0249cd0b257f284f6738e7fd5ac732ba9800ba3b334072bc3de055

tests/test_harmonic_censoring_h25_lifecycle_qualification.py
12362 octets
SHA-256 e29813486a1da469b313a16adf265e55e77fb6527c6306f97123fb9ae4a92aa7
```

Le module utilise uniquement la bibliothèque standard. Un test AST vérifie
l'absence de NumPy, `subprocess`, `threading`, `multiprocessing` et d'import
H24.

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

## Validation locale

```text
python -m py_compile \
  src/polyphonic/harmonic_censoring_h25_lifecycle_qualification.py \
  tests/test_harmonic_censoring_h25_lifecycle_qualification.py

python -m unittest \
  tests.test_harmonic_censoring_h25_lifecycle_qualification -v

14 tests réussis en 1,003 s
git diff --check réussi
```

Les tests créent uniquement des répertoires temporaires jetables et ne
constituent pas la qualification administrative enregistrée.

## Interdictions maintenues

Aucune capability ou claim H25 scientifique, population/manifest H25,
waveform, P0/P1/P2 scientifique, donnée réelle, H17, locked-test, modèle,
checkpoint, calibration ou entraînement n'a été utilisé ou autorisé.

La prochaine action est uniquement la revue externe de cette implémentation.
