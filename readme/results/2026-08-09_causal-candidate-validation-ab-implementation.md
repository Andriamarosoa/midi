# Implémentation A/B historique du filtre causal V1 — 9 août 2026

## Statut

Implémentation uniquement, sans exécution de validation. Une revue externe est
requise avant toute invocation Mac. Aucun checkpoint réel, actif audio, cohorte
historique, export, live ni test verrouillé n'a été chargé ou évalué pendant
cette étape.

## Contrat appliqué avant toute inférence

`load_sealed_validation_contract()` vérifie les octets et les SHA-256 de la
policy A/B, de la sélection des 12 prises, du modèle V1, du standardiseur, du
manifeste, du checkpoint de transcription, du YAML d'évaluation et du décodeur
de référence. Le préflight se produit avant l'import TensorFlow, le chargement
Keras et l'inférence de transcription. L'override audio est explicitement
refusé.

## Sémantique A/B implémentée

Chaque prise utilise une seule inférence de transcription et les mêmes masques
audio calculés une fois. Les branches A et B emploient deux instances de
décodeur indépendantes, initialisées avec la même configuration de base. A ne
voit jamais la tête V1. B construit les douze features depuis son propre état
causal, immédiatement avant la porte et avant ranking/sélection, puis applique
le seuil V1 scellé à `0,31`. Après une décision distincte, les états des deux
décodeurs peuvent diverger : c'est le comportement stateful à mesurer.

Le rapport est tenu en mémoire jusqu'à l'application mécanique de toutes les
règles préenregistrées. En cas de métrique manquante ou non finie, la décision
échoue fermée et aucun JSON final n'est publié. Les règles couvrent notamment
la baisse des faux NoteOn, rappel/F1 onset et causal, p50/p90 de latence
causale, retriggers, fragmentation, corpus et graves MIDI 40–51.

## Vérification locale synthétique

Commande exécutée après l'implémentation :

```powershell
python -B -m unittest tests.test_causal_candidate_validation tests.test_polyphonic_decoder tests.test_polyphonic_events tests.test_causal_candidate_fit tests.test_causal_candidate_validation_preregistration
```

Résultat : `66 tests` réussis en `7,859 s`. Les tests couvrent notamment une seule
inférence partagée, deux états de décodeur distincts, le calcul pré-porte des
features, un préflight qui échoue avant l'inférence et le refus fail-closed
d'une latence non finie. Ce sont exclusivement des tests synthétiques : ils ne
constituent pas la validation historique A/B.

## Correctif après revue externe de `0f5c209e`

Trois écarts de contrat ont été corrigés, toujours sans ouvrir d'actif réel ni
exécuter la cohorte historique :

1. La règle de rappel causal lit `recall_within_max_latency`, la clé réellement
   produite par `aggregate_strictly_causal_noteon_metrics()`. Le test construit
   maintenant cet agrégat réel et vérifie aussi le refus d'une latence non
   finie.
2. `fit_report_path` est une entrée obligatoire du préflight. Son SHA-256 est
   vérifié avant le modèle ou TensorFlow et le rapport final contient les huit
   empreintes exigées : modèle, standardiseur, rapport de fit, manifeste,
   sélection, checkpoint, YAML d'évaluation et décodeur de référence.
3. Les sections globales `paired_ab.reference` et `paired_ab.candidate`
   contiennent maintenant toutes deux `onset_offset`, calculé sur l'agrégat
   complet de leur branche.

Rejeu après correction : `66 tests` ciblés réussis en `8,147 s`, avec
`py_compile` et `git diff --check`. Cette preuve est synthétique et ne donne
aucune autorisation d'exécuter l'A/B Mac.

## Suite autorisée

Faire relire le code et les tests. Une autorisation distincte sera requise
avant l'unique passe CPU Mac sur les douze prises validation scellées.
