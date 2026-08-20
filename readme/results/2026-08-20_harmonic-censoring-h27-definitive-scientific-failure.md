# H27 — clôture définitive sur échec scientifique P0-003

## Verdict

H27 est clos comme hypothèse scientifique échouée. L'unique exécution Mac
Review 5B Recovery autorisée a terminé avec :

```text
H27_PREREGISTRATION_OR_IDENTIFIABILITY_INVALID
```

Ce résultat est scientifique et prévu par la kill rule, non un incident
opérationnel. Aucun retry, aucune nouvelle recovery et aucune modification des
fixtures destinée à faire passer P0-003 ne sont autorisés sous H27.

## Autorité et consommation

- HEAD Mac : `7313de15e6395b23fb275cdb45a5819f71299848` ;
- activation :
  `/Users/amcarene/h27-admin/activation/h27-review5-recovery-v1.json` ;
- activation SHA-256 :
  `c7b6f3e564ec74c35b381e2033780874ee7b8ab0ccb92efbfcc827cff1ab8caf` ;
- execution ID : `83af50ec-0048-4a35-872d-9fd7a949575e` ;
- activation nonce : `efcec520-fce4-4d8c-8533-e40b92962d0f` ;
- CLAIM SHA-256 :
  `f47bf69c59b823579c4b632836cabfe60721ec8a8893dcb37ed9911b2990ef00` ;
- output immuable :
  `/Users/amcarene/h27-admin-recovery-v2/science/review5-recovery-v1`.

La première commande de synchronisation s'est arrêtée avant l'entrypoint Python
à cause d'une expansion PowerShell dans un contrôle shell. Une vérification
read-only a alors confirmé HEAD exact et destination recovery absente. L'unique
invocation scientifique a ensuite été exécutée une seule fois; après son CLAIM,
aucune réparation, suppression, seconde invocation ou retry n'a eu lieu.

## Résultats ordonnés

| Ordre | Test | Résultat | Reçu SHA-256 |
|---:|---|---|---|
| 1 | `H27-T-P0-001` | `PASS` | `bdf2c408bcc95841cb41587a34a61ee7922d5de26760c951e26cafaaa797ce5b` |
| 2 | `H27-T-P0-002` | `PASS` | `aafa1e5b4a0bef196d405c864d187226887bd76141a3417e529624e0ba614b13` |
| 3 | `H27-T-P0-003` | `FAIL` | `154e072b35dcd4e7abd910564ee15c740f6970c987f75617de44de933f522096` |

Le bilan terminal est :

```text
tests_passed     = 2
tests_failed     = 1
tests_not_run    = 24
P1/P2            = non exécutés
locked_test_used = false
training_used    = false
calibration_used = false
checkpoint       = non sélectionné
```

P0-003 exigeait un représentant exact par outcome avec l'ordre de décision
hérité. Les quatre représentants ont produit :

| Fixture | Outcome observé | Certificat / raison |
|---|---|---|
| `baseline/H27-F-P01` | `AMBIGUOUS` | `certificate_gap_or_conflict` |
| `baseline/H27-F-N01` | `AMBIGUOUS` | `certificate_gap_or_conflict` |
| `baseline/H27-F-H01` | `ALREADY_ACTIVE_HISTORY` | `ACTIVE_HISTORY` |
| `baseline/H27-F-A01` | `AMBIGUOUS` | `EQUIVALENCE` |

P01 et N01 devaient fournir les représentants `BIRTH_SUPPORTED` et `NO_BIRTH`.
Ils sont tous deux `AMBIGUOUS`; l'identifiabilité préenregistrée n'est donc pas
démontrée. L'exécution a évalué huit records uniques, seize évaluations au total,
avec `AMBIGUOUS=7` et `ALREADY_ACTIVE_HISTORY=1`.

## Artefacts terminaux

- `scientific_report.json` :
  `4240075f1c54032c749154ae097cab6f8128483f5246ae54ee0926b2b7022714` ;
- `terminal.json` :
  `a7e913d6b6a0801766f12c39f1c9b1ddc626c9ee8fd757a9e38076bc702c6c83` ;
- `COMPLETE.json` :
  `fa9028b43efdcb6d3cc4abe1b879ac79615d80b2e07c794ae39b66caac0fa5f4`.

Le répertoire final contient exactement le CLAIM, les trois reçus ordonnés, le
rapport scientifique, le terminal et le marker COMPLETE.

## Décision

Review 5C est interdite : son préalable `27/27 PASS` n'existe pas. Aucun
training, checkpoint, calibration, locked-test ou validation finale ne peut
être exécuté sous H27. Toute suite scientifique doit être préenregistrée comme
une hypothèse distincte, avec de nouvelles fixtures, règles et autorité one-shot.
