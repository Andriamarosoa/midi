# Intégration A/B synthétique explicite de la porte V2

Date : 2026-08-09

Portée : branchement logiciel et tests synthétiques uniquement. Aucun modèle
V1, standardiseur V1, checkpoint de transcription, audio, label, manifeste,
fit, calibration, validation historique, export, live ou test verrouillé n'a
été ouvert ou exécuté.

## Défaut identifié par la revue de `c8f2f4d`

Le constructeur de `PolyphonicDecoder` conserve correctement `pre_ranking` par
défaut pour V1. L'ancien helper A/B transmettait la porte candidate sans son
placement ; une future utilisation de ce chemin aurait donc répété V1 au lieu
d'exercer V2.

## Correctif fail-closed

`decode_shared_prediction_ab()` et `infer_once_then_decode_ab()` exigent
maintenant `candidate_gate_placement` avant toute inférence. La fonction
générique `decode_probabilities()` et l'évaluateur A/B imposent la même règle
lorsqu'une porte causale est présente. Un placement sans porte est aussi refusé.

Le runner historique scellé V1 passe explicitement `pre_ranking`. Ainsi, il ne
change pas de sémantique. Le futur chemin V2 doit passer explicitement
`post_ranking_pre_noteon`, qui est transmis au constructeur candidat de
`PolyphonicDecoder`. Il n'existe toujours aucune invocation V2 autorisée sur
des actifs réels.

Le rapport A/B enregistre maintenant le placement candidat lorsqu'une porte
causale est active, afin que toute future exécution ne puisse pas être décrite
à tort comme V2 alors qu'elle aurait utilisé V1.

## Preuves synthétiques

Les tests ajoutés vérifient :

1. l'absence ou une valeur inconnue de placement échoue avant l'appel de
   l'inférence partagée ;
2. le helper A/B garde explicitement V1 `pre_ranking` dans le test historique ;
3. V2 reçoit une seule prédiction synthétique, sélectionne deux candidats sur
   trois, appelle la porte seulement pour ces deux candidats, rejette le
   premier et n'émet que le second sans backfill ;
4. `decode_probabilities()`, le chemin dont se sert l'évaluateur, refuse aussi
   une porte sans placement et transmet V2 jusqu'au décodeur réel.
5. `evaluate_events()` refuse une usine de porte sans placement avant toute
   lecture de configuration ou chargement de modèle.

Vérification locale finale : `py_compile`, puis `51` tests ciblés en `1,029 s`
pour le décodeur/A-B et `30` tests de provenance/minage en `0,846 s`. Le
contrôle `git diff --check` est propre.

## Limites et étape suivante

Cette modification n'apporte ni lookahead, ni buffer, ni hop. Elle ne mesure
pas la latence réelle et ne le prétend pas. La seule prochaine action est la
revue externe du code et des tests synthétiques. Tout calcul réel — y compris
le chargement des artefacts V1 ou la réutilisation exploratoire des 12 prises —
reste interdit jusqu'à une autorisation séparée.
