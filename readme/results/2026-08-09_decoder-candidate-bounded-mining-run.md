# Minage borné Policy A — passe CPU train-only terminée

## Statut et périmètre

L'unique passe autorisée de minage des candidats du décodeur est terminée avec
succès sur le Mac, mais reste **strictement non autorisante**. Elle a produit
un corpus de candidats causaux pour revue humaine ; elle n'autorise ni
entraînement, ni calibration, ni validation, ni sélection de seuil, ni export,
ni live, ni accès au test verrouillé.

| Élément | Valeur vérifiée |
| --- | --- |
| Job | `decoder-candidate-bounded-mining-cpu-20260809` |
| Commit exécuté | `f4eb87a49645263c21ac480ec6d655f677029e53` |
| Appareil | CPU forcé (`MIDI_FORCE_CPU=1`) |
| Fenêtre maximale | 3 600 s |
| Début / fin UTC | `2026-08-09T16:31:30Z` / `2026-08-09T16:37:47Z` |
| Code de sortie | `0` |
| État produit | `complete_non_authorizing` |
| Test verrouillé | `locked_test_used=false` |
| Autorisation de fit | `fit_authorized=false` |

Avant TensorFlow, le préflight a confirmé le worktree Mac propre et le commit
exact, l'absence de verrou/processus de minage, une destination inexistante et
les sept empreintes attendues : manifeste `b28cb17…`, plan Policy A v2
`a8347e4e…`, registre d'actifs `12dd74f2…`, checkpoint `1ce8ac44…`, YAML
`24528578…`, décodeur référence `c16be482…` et politique audio LF
`45edbb71…`.

## Artefacts bruts conservés sur le Mac

Répertoire :
`/Users/amcarene/midi/data/processed/decoder_candidate_bounded_policy_a_20260809`

| Fichier | SHA-256 | Contrôle |
| --- | --- | --- |
| `candidate_events.jsonl` | `19cb073a33439a0b5befef7c7ef3c2aa2892b11e57b9042c821a05d79911c2c1` | 429 lignes JSON valides |
| `mining_report.json` | `3ad78ede370992c4a08c545b91e4079c1a52edfe969514d0275d70b0275dc0fc` | rapport terminal conforme |

Le SHA du JSONL inscrit dans `mining_report.json` correspond aux octets lus
après le job. Les 429 `event_id` sont non vides et uniques. Les lignes ne
contiennent que les partitions train `fit`, `dev` et `calibration`, et leurs
12 identités `(dataset_id, source_id, capture_id)` correspondent à la
sélection préinscrite.

## Comptage de la population supervisée

| Partition | Faux NoteOn causaux (0) | NoteOn causaux (1) | Total |
| --- | ---: | ---: | ---: |
| `fit` | 100 | 23 | 123 |
| `dev` | 124 | 51 | 175 |
| `calibration` | 111 | 20 | 131 |
| **Total** | **335** | **94** | **429** |

La ventilation corpus × partition × cible du JSONL recopie exactement celle du
rapport. Elle révèle déjà une forte hétérogénéité à examiner avant tout fit :
GuitarSet ne fournit que quatre positifs dans `fit`, six négatifs dans `dev` et
deux négatifs dans `calibration`; il ne fournit pas les deux classes dans
chacune de ces trois petites sélections. Il serait donc prématuré d'en déduire
une capacité de généralisation ou de choisir une pondération.

## Réconciliation du replay

- Tentatives : `7 438` totales = `7 438` retenues + `0` perte.
- NoteOn du décodeur : `7 303` = `7 134` instrumentés + `169` retriggers
  explicitement non instrumentés. Aucun autre motif non instrumenté n'est
  rapporté.
- NoteOn émis éligibles à la porte : `436` = `429` supervisés + `7` exclus car
  frame de label invalide + `0` hors audio.
- Matcher causal du flux complet : `7 166` NoteOn matchables = `1 608` matches
  causaux + `5 558` faux NoteOn causaux. Parmi ces matches, `1 514` ne sont pas
  projetés dans les cibles supervisées, ce qui est attendu : la population
  d'apprentissage se limite aux candidats pré-porte éligibles et émis.
- Références valides : `3 418` = `1 608` matches + `1 810` manquées.

Ces compteurs sont des diagnostics de collecte, pas des métriques de qualité
du futur modèle. Le déséquilibre observé (`335` négatifs contre `94` positifs)
doit être traité comme une contrainte de la prochaine hypothèse, non comme une
raison de lancer un fit immédiatement.

## Porte suivante

Faire revoir ce rapport, les deux SHA d'artefacts et la distribution par
partition/corpus par ChatGPT avant toute suite. Aucun calcul supplémentaire
n'est autorisé sur la seule base de ce minage : en particulier aucun fit,
calibration, validation officielle, export, live, recherche de seuil ou test
verrouillé.
