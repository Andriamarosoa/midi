# Grille historique de la porte de note indépendante — validation

## Contrat et intégrité

- Job Mac CPU : `independent-note-threshold-grid-cpu-20260805`.
- Commit exécuté : `a4f37676b4791e83d9842ade4da07eb9bfaa1d46`.
- Fin réconciliée : `2026-08-04T18:12:03Z` (`2026-08-04T22:12:03+04:00`),
  code de sortie `0`. L'horodatage brut du Mac, conservé comme provenance,
  était `2026-08-05T05:12:03Z` alors que son horloge était avancée d'environ
  11 h; aucun résultat n'est recalculé.
- Split : validation, 12 enregistrements, `locked_test_used=false`.
- Aucun entraînement, export, live ou test verrouillé n'a été exécuté.

## Résultats observés

| Seuil actif | Faux NoteOn | Notes estimées | Notes appariées | F1 onset | Rejets porte |
| --- | ---: | ---: | ---: | ---: | ---: |
| 0,50 | 3389 | 4247 | 858 | 0,21760081 | 1 |
| 0,60 | 3389 | 4247 | 858 | 0,21760081 | 4 |
| 0,70 | 3389 | 4247 | 858 | 0,21760081 | 9 |
| 0,80 | 3389 | 4247 | 858 | 0,21760081 | 20 |
| 0,90 | 3387 | 4245 | 858 | 0,21765601 | 58 |

Le rappel est inchangé pour tous les seuils (`0,23577906`) et les 858 notes
appariées restent identiques. A `0,90`, le gain est seulement de deux faux
positifs et `+0,00005520` de F1. Cette porte seule ne corrige donc pas le
problème principal de 3389 faux NoteOn.

## Limite méthodologique

Cette exécution employait l'ancienne grille qui relançait une évaluation complète
pour chaque seuil. Elle ne constitue pas le diagnostic contre-factuel à une passe
du commit `5ce370d` : les ensembles de candidats diffèrent déjà entre lignes
(709 à 723), car chaque seuil modifiait l'état du décodeur. La grille est
conservée comme preuve empirique, mais ne doit pas être réutilisée pour choisir
un seuil. La suite autorisée est une seule passe validation avec le collecteur
multi-seuils, après revue du présent résultat.
