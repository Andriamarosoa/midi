# Validation A/B appariée de la porte note indépendante

## Statut

Terminée sur CPU Mac, résultat négatif : le seuil préenregistré `0,01` ne modifie aucun événement final du décodeur sur les douze prises validation.

## Provenance

- Job : `independent-note-paired-validation-cpu-20260805`.
- Commit : `e091c3fc585135e180b1510ef14cdec3bfcef0c3`.
- Split : validation, 12 prises verrouillées, `locked_test_used=false`.
- Rapport brut local : `tmp/local/mac_results/independent-note-paired-validation-cpu-20260805/validation_events_independent_note_head_independent_note_paired_validation.json`.
- SHA-256 du rapport : `321639e338fe85e9dcdf69682f807feafc783d5bddec7b1464ae37def54303f`.
- Une inférence par prise a été réutilisée pour la référence (porte absente) et le candidat (seuil `0,01`), avec les SHA de manifeste, YAML, checkpoint et deux configurations contrôlés avant chargement du modèle.

## Résultats

Référence et candidat sont identiques : 3 639 notes de référence, 4 247 notes estimées, 858 appariées, 3 389 faux positifs, 2 781 manquantes, F1 onset `0,21760081`, et 160 retriggers. Le delta candidat moins référence est nul pour faux positifs, appariements, notes manquantes et F1.

Les métriques causales sont également identiques : 2 073 faux NoteOn, `69,92376` faux NoteOn/min, rappel causal `0,59742`, p50 `68,13 ms` et p90 `162,39 ms`. Dans MIDI 40–51 : 611 références, 1 007 estimations, 139 appariements, 868 faux positifs et F1 `0,17181706`, sans changement A/B.

## Décision

La porte `independent_note` au seuil `0,01` n'est pas promue : elle n'est pas rejetée pour régression, mais elle n'a aucun effet observable sur cette validation. Aucun seuil alternatif n'est exploré, aucun export, live, entraînement ou test verrouillé ne suit avant une nouvelle hypothèse revue.
