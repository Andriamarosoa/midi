# V6.2 — ablation onset et harmoniques en flux continu

Date : 2026-07-18

## Sélection du checkpoint

La règle a été fixée avant lecture du test : maximiser l'AP onset parmi les
checkpoints dont le Top-1 pitch reste à moins de 0,5 point du meilleur et dont
l'AP active reste à moins de 0,1 point du meilleur.

`best_onset.keras` est sélectionné sur validation uniquement :

- Pitch Top-1 : 85,68 %, à 0,21 point du meilleur.
- Active AP exacte : 99,13 %.
- Onset AP exacte : 42,93 %.
- Seuil active : 0,193529.
- Seuil onset : 0,584915.

Sur le test fenêtré, ce checkpoint obtient : pitch Top-1 91,68 %, active F1
95,51 %, onset F1 50,58 % et onset AP 46,07 %.

## Protocole continu

- Quatre solos GuitarSet du joueur test 05.
- Durée totale : 103,48 s.
- 199 notes de référence évaluables.
- Même politique `detected_progressive` causale.
- Deux trames de stabilité, soit au maximum 5,805 ms de délai ajouté.
- Aucun lookahead.

Trois décodeurs rejouent exactement les mêmes prédictions :

1. baseline avec le détecteur onset externe existant ;
2. changements de pitch actifs autorisés par l'onset neuronal ;
3. même règle avec veto lorsque le pitch candidat correspond au partiel
   harmonique prédit le plus fort de la note courante.

## Résultats agrégés

| Mesure | Baseline V6.2 | Onset neuronal | Onset + harmonique |
|---|---:|---:|---:|
| Active F1 | 82,20 % | 82,20 % | 82,20 % |
| Précision conjointe | 76,00 % | 72,44 % | 72,38 % |
| Rappel pitch correctement gated | 70,84 % | 65,18 % | 65,09 % |
| Événements générés | 433 | 364 | 361 |
| Événements supportés | 280 | 247 | 245 |
| Événements non supportés | 141 | 97 | 96 |
| Fantômes par minute | 81,76 | 56,24 | 55,66 |
| Notes couvertes majoritairement | 161 / 199 | 141 / 199 | 141 / 199 |
| Notes totalement manquées | 9 / 199 | 35 / 199 | 35 / 199 |
| Retriggers contrôlés | 15 | 42 | 42 |
| Retriggers non supportés | 13 | 31 | 31 |
| Trames bloquées par les harmoniques | 0 | 0 | 33 |

L'onset neuronal continu, au seuil sélectionné sur validation fenêtrée, obtient
seulement 6,83 % de précision, 29,57 % de rappel et 11,10 % de F1. Son AP
pondérée sur les quatre morceaux est 6,49 %.

## Comparaison à la référence V6.0

La référence V6.0 sur les mêmes quatre morceaux avait 84,87 % de F1 activité,
79,50 % de précision conjointe, 52,18 fantômes/minute et 3 notes manquées.

La baseline V6.2 est donc déjà moins bonne en flux continu. Le gate onset ramène
les fantômes près du niveau V6.0 mais fait passer les notes manquées de 9 à 35.
Le veto harmonique ne retire que trois événements supplémentaires et n'améliore
pas la couverture.

## Latence

- Contexte onset : 512 échantillons = 11,61 ms de passé causal.
- Lookahead : 0 ms.
- Délai de stabilité maximal : 5,805 ms.
- V6.2 `tf.function`, moyenne selon source : 5,95 à 6,32 ms.
- V6.2 p95 : 6,96 à 10,01 ms.
- Budget par hop : 5,805 ms.

Les mesures TensorFlow CPU varient fortement entre chargements. Elles ne
permettent pas d'affirmer que V6.2 est plus rapide que V6.0. Le p95 V6.2 reste
dans tous les cas au-dessus du budget.

## Décision

- Ne pas remplacer V6.0 comme référence live.
- Rejeter les décodeurs `model_onset_gate` et
  `model_onset_harmonic_gate` dans leur forme actuelle.
- Conserver `best_onset.keras` comme artefact de recherche, pas comme modèle
  de production.
- Le prochain entraînement onset doit utiliser de vraies trames continues au
  pas de 256 échantillons, dérivées des `start_s`, `note_id` et annotations
  harmoniques existantes. Aucune nouvelle annotation manuelle n'est requise.
