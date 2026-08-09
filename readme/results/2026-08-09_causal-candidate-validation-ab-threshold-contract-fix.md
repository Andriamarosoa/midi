# Correctif pré-métrique du contrat A/B historique

Date : 2026-08-09
Portée : archivage d'une anomalie pré-métrique et correctif sans calcul.

## Invocation arrêtée avant l'évaluation

L'unique tentative opérationnelle autorisée par la revue de
`4ab4f1ec7442d9a9e942e4f1c8888734b7c2d653` a utilisé exactement :

```text
job_id             causal-candidate-validation-ab-cpu-20260809
commit             4ab4f1ec7442d9a9e942e4f1c8888734b7c2d653
module             src.polyphonic.run_causal_candidate_validation
device             cpu
wall timeout       900 s
module arguments   aucun
```

Le worker Mac était propre au commit attendu, son script était identique à la
version Git, `active.lock` était absent, le job ID et la destination A/B étaient
neufs. Le préflight spécialisé a confirmé CPU/900 s sans importer TensorFlow.
L'état terminal est `exited_nonzero`, code `1`, fini à
`2026-08-09T22:34:34Z`, puis le verrou a été libéré.

L'erreur exacte est :

```text
KeyError: 'frame'
src/polyphonic/evaluate_events.py:874
frame_threshold = float(thresholds["frame"])
```

Les huit SHA avaient déjà été contrôlés et le checkpoint de transcription avait
été chargé. L'exception survient avant la construction de `PolyphonicSequence`
et avant la boucle sur les 12 prises. Le dossier
`tmp/causal_candidate_validation_ab_v1_20260809` est absent après l'arrêt :
aucun rapport, métrique, audio/label, inférence de prise, export, live ou test
verrouillé n'a été produit.

## Cause et correctif

Dans `evaluate_events`, la présence d'un `decoder_config_path` rendait bien
`thresholds` vide, mais le code lisait ensuite inconditionnellement les clés
`frame` et `onset`. Cette dépendance était incohérente : le décodeur de
référence scellé contient déjà ces deux valeurs et la destination fraîche ne
doit pas introduire de fichier `thresholds.json` libre.

Le correctif ajoute `_load_evaluation_decoder_config()` :

- un décodeur explicite est lu directement, sans thresholds externe ;
- l'ancien fallback ne lit `thresholds.json` que lorsqu'il n'y a aucun
  décodeur explicite ;
- la configuration décodeur est validée avant de lire le manifeste ou de
  charger le checkpoint.

Il ne change ni la policy, ni la sélection des 12 prises, ni le seuil candidat
`0,31`, ni les huit SHA, ni le décodeur stateful, ni les règles de décision.

## Vérification sans reprise

```text
py_compile : evaluate_events.py, causal_candidate_validation.py,
             run_causal_candidate_validation.py et tests associés
unittest  : 54 tests ciblés réussis en 8,912 s
```

Les tests ajoutés vérifient qu'un décodeur scellé fonctionne sans
`thresholds.json` dans une destination fraîche, que le fallback historique
lit toujours ses thresholds lorsqu'il n'y a pas de décodeur, et que la
configuration est résolue avant le manifeste et le checkpoint. Aucun nouvel appel Mac, actif
réel, modèle, inférence, validation, export, live ou test verrouillé n'a été
effectué pendant ce correctif.

## Prochaine action

Faire relire ce seul correctif. Une nouvelle autorisation explicite sera
requise avant une unique relance CPU de l'A/B historique ; aucun fit,
recalibrage, recherche de seuil, export, live ou test verrouillé n'est permis.
