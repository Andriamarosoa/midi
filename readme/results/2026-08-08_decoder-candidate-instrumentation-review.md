# Revue de clôture — instrumentation des candidats du décodeur

## Décision

Les commits `f7514228800d8ad15db7d047dcadfbf8640cf4ee` (implémentation) et
`d4492c3b9a337b87341b1612b07eac3f05ce8997` (preuve Mac) sont approuvés pour
l'étape **instrumentation-only**. Cette décision ne promeut aucun checkpoint ni
seuil et n'autorise pas le minage.

## Vérifications rejouées

Le 2026-08-08, dans le worktree propre
`codex/independent-note-neural-v2` au commit `d4492c3`, la commande suivante a
réussi :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest \
  tests.test_decoder_candidate_mining \
  tests.test_decoder_candidate_instrumentation \
  tests.test_polyphonic_decoder \
  tests.test_polyphonic_desktop_contract \
  tests.test_product_decoder \
  tests.test_polyphonic_validate_live_input_level \
  tests.test_ollama_team \
  tests.test_mac_worker_transport_contract
```

Résultat : **86 tests réussis en 6,895 s**. `git diff --check` réussit et le
worktree est propre. Les inspections locales Windows et Mac ne montrent aucun
processus `src.polyphonic.train`, `evaluate_events` ou
`smoke_neural_independent_note` actif.

## Points de code confirmés

- Le collecteur est optionnel et `None` par défaut. Les traces et leurs calculs
  supplémentaires ne sont construits que si l'instrumentation est active.
- Les voies legacy et causale capturent les données avant la porte, puis
  n'ajoutent rang, sélection et émission qu'après les décisions MIDI réelles.
  Les événements MIDI publics restent inchangés.
- Une frame est envoyée au collecteur une seule fois après ses décisions. Une
  contention de verrou ou une exception est mémorisée, arrête l'observation et
  laisse la sortie MIDI intacte.
- Le buffer borné transporte les compteurs de pertes; `require_complete()`
  refuse un futur batch incomplet. Les codes de raisons conservent le contrat
  historique du live.
- Le test de parité versionné compare événements et état du décodeur avec et
  sans collecteur sur les voies legacy/causale, porte active/inactive, reset,
  panic et drainage intermédiaire.

La comparaison historique contre `f9ed9d0` et le microbenchmark restent des
preuves documentées dans le rapport d'instrumentation; leur harness différentiel
exact n'est pas versionné. La parité dynamique instrumentée/non instrumentée,
elle, est versionnée et vient d'être rejouée.

## Limites qui bloquent le minage

1. La provenance brute n'est pas encore complète : un artefact devra persister
   `source_id`, `dataset_id`, `group_id`, `capture_id`, la clé de fuite et une
   partition déterministe `fit/dev/calibration` assignée au niveau groupe avant
   la collecte, jamais après coup.
2. `event_id` identifie un vrai NoteOn et inclut sa frame. Le collapse actuel
   filtre les lignes non émises puis exige le même `event_id` pour les grouper;
   il devient donc un no-op sur le producteur réel. Le prochain contrat doit
   choisir explicitement entre suppression du collapse et introduction d'un
   `candidate_episode_id` distinct.

`locked_test_used=false`. Aucun minage, entraînement, validation officielle,
export ou live n'a été réalisé par cette revue.

## Suite autorisée

Un seul travail préparatoire est autorisé : un commit sans calcul qui définit
et teste le contrat complet de provenance et d'unité d'apprentissage. Il devra
être relu avant toute première production d'artefact train-only.
