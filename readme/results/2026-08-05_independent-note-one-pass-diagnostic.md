# Diagnostic one-pass de la porte de note indépendante

## Contrat vérifié

- Job Mac CPU : `independent-note-one-pass-diagnostic-cpu-20260805`.
- Commit : `0a235d2ecc5a82564897eb347caee26e2842a7eb`.
- Fin : `2026-08-05T05:25:56Z`, code de sortie `0`.
- Split : `validation`, 12 enregistrements, `locked_test_used=false`.
- Aucun entraînement, export, live ou test verrouillé.
- Rapport brut (hors Git) :
  `/Users/amcarene/midi-worker/repository/tmp/independent-note-neural-train-gate-git-20260805/reports/validation_events_independent_note_head_independent_note_one_pass_diagnostic.json`.
- SHA-256 du rapport brut :
  `4de61c0a447e8e8fcf6914cd00b11867309bcf6ac0a2f3cab0804024e2e5c4f6`.

## Provenance

| Élément | SHA-256 |
| --- | --- |
| Checkpoint `independent_note_head.keras` | `b09282a1865cf8dfb5e1bd79e8d11e033251a144f3fe8965c1d0656c9e5dd19a` |
| Configuration modèle | `245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804` |
| Seuils frame/onset | `87c61b2850ae5f4b2796150193abb9e688fe2cb701e89a1f822b9963f9d47fb6` |
| Configuration décodeur | `fd0480ed107b52fb85f48a0d6cf2b99c8f93ca43b6e0f9b7f60ee54274c81079` |

Commande logique : `src.polyphonic.evaluate_events`, avec `--split validation`,
`--maximum-recordings 12`, le checkpoint et les trois fichiers de configuration
ci-dessus, sans grille, sans option de test verrouillé.

## Résultat du même ensemble de candidats

La porte active reste à `0,01` et ne rejette aucun des 709 candidats. Les
probabilités sont massivement proches de 1 : min `0,48080769`, p01
`0,65972247`, p05 `0,88579741`, médiane `0,98582065`, p95 `0,99880720`, p99
`0,99971801`, max `0,99987316`; méthode de quantiles `numpy.linear`.

| Seuil diagnostique | Rejets hypothétiques sur les mêmes 709 candidats |
| --- | ---: |
| 0,001 | 0 |
| 0,005 | 0 |
| 0,010 | 0 |
| 0,020 | 0 |
| 0,050 | 0 |
| 0,100 | 0 |
| 0,200 | 0 |
| 0,500 | 1 |
| 0,600 | 4 |
| 0,700 | 8 |
| 0,800 | 18 |
| 0,900 | 49 |

Les métriques événementielles de l'exécution active sont : 3639 références,
4247 estimées, 858 appariées, 3389 faux positifs, 2781 manquantes, précision
`0,20202496`, rappel `0,23577906`, F1 onset `0,21760081`, 160 retriggers.

## Conclusion limitée

Sur ces 12 enregistrements validation, la tête de note indépendante est trop
confiante pour servir seule de filtre de faux NoteOn : même le seuil `0,90` ne
pourrait bloquer que 49/709 candidats. Cette mesure ne sélectionne pas un seuil
ni un checkpoint et ne préjuge pas du split validation complet, du test verrouillé
ou d'une autre tête. Toute suite doit d'abord être revue.
