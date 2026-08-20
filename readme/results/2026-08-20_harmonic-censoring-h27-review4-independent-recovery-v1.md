# H27 Review 4 — lignée indépendante Recovery V1

## Portée

Ce lot ferme uniquement la préparation locale des sous-étapes restantes de
Review 4. Il ne rejoue pas l'activation consommée archivée par
`8ff8049a3745208bc9bab1fb79f073ca12fcb073` et n'ouvre aucune partie de Review 5.

## Corrections et lignée

- `f2ea3b82f4e58278711f1e9826a2db9694c47e40` fournit le second argument
  obligatoire de `parse_strict_json(raw, label)` et exerce le vrai contrat H27.
- `6b339e5b7fdb254adbc2801abc6fd7baaf8bac38` préenregistre la lignée indépendante.
- `1d01ce9e6ae518b10c6578fbcc72ee0fc25aab22` implémente l'activation et le runner recovery.
- `697e76d22a2e84ca8075040ce34b2cc907bc0e05` lie la composition d'exécution.
- `fb1702aeebdb37c01c76af1226d5ecd9bebdf1c7` lie activation, runtime et matérialiseur.
- `61ed9df1e80453ba2c3b980009a420bb5378c160` scelle la compatibilité du matérialiseur.
- `ca6fca422b4c1b4625273921f949125475e4b7c7` scelle l'exécution recovery complète.

Le nouveau root est exclusivement `/Users/amcarene/h27-admin-recovery-v1`.
L'ancien root `/Users/amcarene/h27-admin` est seulement une source d'attestation
read-only de l'AUTHORITY et du CLAIM consommés; il n'est jamais un credential.

## Identités finales

| Artefact | Git blob | Octets | SHA-256 |
|---|---:|---:|---:|
| recovery contract | `242f3f4e...` | 5 079 | `e8d000ed...` |
| activation recovery | `4220e0de...` | 2 382 | `a5f1e68b...` |
| base runner corrigé | `53a5d243...` | 28 265 | `94dc4fe6...` |
| entrypoint recovery | `181c0afa...` | 3 659 | `e23193d3...` |
| compatibility binding | `96924dae...` | 2 366 | `fa44e6a3...` |
| compatibility seal | `596206fa...` | 860 | `f1fb8026...` |
| execution binding | `362b6976...` | 5 245 | `b4edfa8e...` |
| execution external seal | `a9a648e9...` | 1 377 | `4a154834...` |

Le matérialiseur demeure strictement inchangé : `8cdafbd6...` / 33 706 /
`2ecaabf1...`.

## Validation locale

Commande :

```text
python -m py_compile scripts/h27_review4_execute_once.py scripts/h27_review4_recovery_v1_execute_once.py tests/test_harmonic_censoring_h27_review4_recovery_v1_runner.py
python -m unittest tests.test_harmonic_censoring_h27_review4_materializer tests.test_harmonic_censoring_h27_materialization_recovery_v1_contract tests.test_harmonic_censoring_h27_review4_recovery_v1_runner tests.test_harmonic_censoring_h27_materialization_recovery_v1_execution_binding
git diff --check
```

Résultat : 30 tests, 29 réussis et 1 skip POSIX attendu sous Windows. Le test
réel dormant charge les cinq blobs scientifiques au HEAD cible
`46a6bdf81a56a7a7a10524d4e55092301a452207` et obtient exactement 124 identités
uniques, dont 17 baseline et 107 P2.

## Frontière

Aucun SSH ni effet Mac n'a été produit. Aucun ACK, activation recovery,
AUTHORITY, CLAIM, staging, population, terminal, P0/P1/P2, science, locked-test,
training ou calibration n'a été exécuté.

Prochaine action unique : pousser ce lot et obtenir une revue externe byte-exacte.
Après `PASS` explicite seulement, le bootstrap vérifiera les neuf composants
avant ACK puis invoquera une seule fois le runner recovery. Succès ou échec
après consommation sera terminal et sans retry.
