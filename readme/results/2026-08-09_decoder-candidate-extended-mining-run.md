# Minage étendu Policy A — résultat train-only non autorisant

## Verdict opérationnel

La seule passe CPU autorisée du protocole étendu Policy A est terminée sans
erreur, mais la porte de représentation est **refusée**. Le corpus obtenu ne
doit donc servir ni au fit, ni à la calibration, ni à une validation officielle.
Il ne justifie aucun export, live, choix de seuil ou accès au test verrouillé.

Le refus provient exclusivement de deux cellules positives GuitarSet trop peu
représentées. Il ne démontre pas une erreur des labels ni une régression du
décodeur : aucun modèle de candidats n'a été entraîné dans cette étape.

## Exécution vérifiée

| Élément | Valeur |
| --- | --- |
| Job Mac | `decoder-candidate-extended-mining-cpu-20260809` |
| Commit exécuté | `42a88b0df71f7517220d063f6ff391d5ea23e035` |
| Périmètre | train-only, 72 prises canoniques (`6 × 4 corpus × 3 partitions`) |
| Appareil | CPU forcé (`MIDI_FORCE_CPU=1`) |
| Limite murale | 3 600 s |
| Début / fin UTC | `2026-08-09T17:49:18Z` / `2026-08-09T18:18:38Z` |
| Durée observée | 29 min 20 s |
| Sortie | `0` — `complete_non_authorizing` |
| Test verrouillé | `locked_test_used=false` |
| Autorisation de fit | `fit_authorized=false` |

Le préflight a confirmé avant le replay : worktree propre, aucun verrou ou
processus de minage actif, destination inexistante, CPU forcé et les sept
empreintes attendues.

| Entrée scellée | SHA-256 |
| --- | --- |
| Manifeste | `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` |
| Plan Policy A v2 | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` |
| Registre d'actifs | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` |
| Checkpoint de transcription | `1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325` |
| Configuration d'inférence | `245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804` |
| Décodeur référence | `c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96` |
| Politique audio LF | `45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e` |
| Protocole étendu v2 | `b3a7c5c0b93b443a71f0564fbdbad158fede778032645776b91073f69e53a6ac` |

## Artefacts et intégrité

Les artefacts bruts restent hors Git, sur le Mac :
`/Users/amcarene/midi/data/processed/decoder_candidate_extended_policy_a_6percell_20260809`.

| Fichier | SHA-256 | Vérification |
| --- | --- | --- |
| `candidate_events.jsonl` | `88d8a088ea8cde5667c7aa8d6337df7e06fa923ea9fcd147b11e8ea4abbf492f` | 3 057 lignes JSON ; 3 057 `event_id` uniques |
| `mining_report.json` | `82c9137f104bc3eb9be632b1027c2752d35bb8a7c14c0665fda129cb63e4a7c1` | statut terminal et comptages cohérents |

Les 3 057 lignes appartiennent toutes à la sélection préinscrite. Elles couvrent
69 identités de prises, tandis que la sélection en comporte 72 : les trois
prises GuitarSet suivantes n'ont émis aucun candidat supervisé et ne produisent
donc aucune ligne. C'est une observation de population, non une corruption
d'artefact.

- `guitarset_poly_mix / 01_BN2-131-B_solo / mono_pickup_mix`
- `guitarset_poly_mix / 02_BN1-129-Eb_solo / mono_pickup_mix`
- `guitarset_poly_mix / 02_BN2-131-B_solo / mono_pickup_mix`

L'audit des groupes trouve 54 groupes physiques uniques et aucun groupe qui
traverse les partitions. Les 18 groupes Guitar-TECHS sont, comme prévu,
partagés entre les vues direct-input et mic/amp, mais restent chacun dans une
seule partition ; les deux vues ne doivent pas être considérées comme 36
performances indépendantes pour une hypothèse de fit ultérieure.

## Comptages et réconciliation

| Partition | Faux NoteOn causaux (0) | NoteOn causaux (1) | Total |
| --- | ---: | ---: | ---: |
| `fit` | 676 | 228 | 904 |
| `dev` | 958 | 228 | 1 186 |
| `calibration` | 784 | 183 | 967 |
| **Total** | **2 418** | **639** | **3 057** |

| Corpus | fit (0 / 1) | dev (0 / 1) | calibration (0 / 1) |
| --- | ---: | ---: | ---: |
| `gaps_poly_mix` | 295 / 133 | 393 / 168 | 308 / 129 |
| `guitar_techs_poly_directinput` | 177 / 47 | 293 / 41 | 270 / 36 |
| `guitar_techs_poly_micamp` | 188 / 33 | 260 / 13 | 196 / 11 |
| `guitarset_poly_mix` | 16 / 15 | 12 / 6 | 10 / 7 |

Les invariants du replay sont vérifiés :

- 49 650 tentatives = 49 650 retenues + 0 perte ;
- 48 787 NoteOn du décodeur = 47 649 matchables causalement + 1 138 frames
  invalides + 0 hors audio ;
- 3 128 NoteOn éligibles et émis = 3 057 supervisés + 71 exclus par frame
  invalide + 0 hors audio ;
- 24 096 références = 11 870 matches causaux + 12 226 références manquées ;
- les 1 442 NoteOn non instrumentés sont tous des retriggers explicitement
  exclus ; aucun autre motif non instrumenté n'est présent.

## Porte de représentation

Le protocole exige au moins 8 exemples de chaque cible dans chaque cellule
corpus × partition, ainsi qu'au moins 75 exemples de chaque cible par
partition. Les totaux de partition passent, mais deux cellules échouent :

| Cellule | Positifs observés | Minimum |
| --- | ---: | ---: |
| `guitarset_poly_mix / dev / cible 1` | 6 | 8 |
| `guitarset_poly_mix / calibration / cible 1` | 7 | 8 |

`representation_gate.passed=false`. Cette décision est mécanique et conserve
`fit_authorized=false`, même si les autres cellules et les totaux de partition
sont suffisants.

## Limites et suite autorisée

Ce résultat améliore la taille brute du pilote, mais ne rend pas le corpus
représentatif selon le contrat préenregistré. Les prises GuitarSet sans candidat
et les deux cellules positives déficitaires doivent guider la prochaine
hypothèse, sans réinterpréter a posteriori le seuil de la porte.

La seule suite autorisée est une **revue humaine de ce rapport** pour décider
d'une hypothèse distincte, train-only et préenregistrée. Aucun nouveau replay,
fit, calibration, validation, export, live, sélection de seuil ou test
verrouillé n'est autorisé par ce résultat.
