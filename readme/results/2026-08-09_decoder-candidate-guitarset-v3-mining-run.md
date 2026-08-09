# Minage V3 GuitarSet Policy A — résultat train-only non autorisant

## Verdict opérationnel

L'unique replay CPU V3 autorisé est terminé sans erreur. Il produit un corpus
de candidats causalement étiquetés plus représentatif que la passe de 72
prises : les trois partitions passent la porte préenregistrée, y compris les
cellules positives GuitarSet. Ce résultat est toutefois **non autorisant** :
`fit_authorized=false` reste une barrière explicite du protocole. Aucun fit,
calibration, validation officielle, sélection de seuil, export, live ou accès
au test verrouillé ne suit ce minage.

Cette passe ne mesure pas une amélioration de transcription : elle vérifie la
production, la provenance et la représentation d'un futur corpus train-only.

## Exécution vérifiée

| Élément | Valeur |
| --- | --- |
| Job Mac | `decoder-candidate-guitarset-v3-cpu-20260809` |
| Commit exécuté | `4ddc88666a1c55725c18a813c63ecd25a03bf298` |
| Périmètre | train-only, 90 prises canoniques (`6` par corpus × partition, sauf GuitarSet `12`) |
| Appareil | CPU forcé |
| Limite murale | `3 600 s` |
| Début / fin déclarés par le worker Mac | `2026-08-09T19:07:52Z` / `2026-08-09T19:41:24Z` |
| Durée, même horloge worker | 33 min 32 s |
| Sortie | `0` — `complete_non_authorizing` |
| Test verrouillé | `locked_test_used=false` |
| Autorisation de fit | `fit_authorized=false` |

Les horodatages ci-dessus sont ceux déclarés par le worker Mac ; ils ne sont
pas réconciliés avec l'horloge Windows. Le préflight a confirmé un worktree
propre, le CPU forcé, l'absence de verrou actif, la destination inexistante et
les empreintes scellées avant TensorFlow.

| Entrée scellée | SHA-256 |
| --- | --- |
| Manifeste | `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` |
| Plan Policy A v2 | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` |
| Registre d'actifs | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` |
| Checkpoint de transcription | `1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325` |
| Configuration d'inférence | `245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804` |
| Décodeur référence | `c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96` |
| Politique audio LF | `45edbb712415c5b62f10a1405678fc28cee083891131108b2875ce8f71abcd3e` |
| Protocole V3 | `db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683` |

## Artefacts et intégrité

Les artefacts bruts restent hors Git. Ils ont été téléchargés depuis le
worktree du worker Mac vers
`tmp/local/mac_results/decoder-candidate-guitarset-v3-cpu-20260809/` et
rehachés localement.

| Fichier | SHA-256 | Vérification |
| --- | --- | --- |
| `candidate_events.jsonl` | `fd852626f56b038837266b5336b318c8adf841c1aafbd01d36b362f7fe10150d` | 2 631 899 octets ; 3 139 lignes JSON ; 3 139 `event_id` uniques |
| `mining_report.json` | `e13a13be38710e7a15f9d6d222d0a7835aad204a1b7c821d8198d1ac9ccffe59` | 286 078 octets ; statut terminal et compteurs cohérents |

Le rapport brut confirme les 90 prises sélectionnées, le commit exécuté et
`locked_test_used=false`. Les fichiers ne sont pas ajoutés à Git afin de ne pas
versionner les artefacts générés volumineux.

## Comptages et réconciliation

| Partition | Faux NoteOn causaux (0) | NoteOn causaux (1) | Total |
| --- | ---: | ---: | ---: |
| `fit` | 694 | 244 | 938 |
| `dev` | 968 | 250 | 1 218 |
| `calibration` | 793 | 190 | 983 |
| **Total** | **2 455** | **684** | **3 139** |

| Corpus | fit (0 / 1) | dev (0 / 1) | calibration (0 / 1) |
| --- | ---: | ---: | ---: |
| `gaps_poly_mix` | 295 / 133 | 393 / 168 | 308 / 129 |
| `guitar_techs_poly_directinput` | 177 / 47 | 293 / 41 | 270 / 36 |
| `guitar_techs_poly_micamp` | 188 / 33 | 260 / 13 | 196 / 11 |
| `guitarset_poly_mix` | 34 / 31 | 22 / 28 | 19 / 14 |

Les invariants du replay sont vérifiés :

- 52 450 tentatives = 52 450 retenues + 0 perte ;
- 3 211 NoteOn éligibles et émis = 3 139 supervisés + 72 exclus par frame
  invalide + 0 hors audio ;
- 51 828 NoteOn du décodeur = 50 666 matchables causalement + 1 162 frames
  invalides + 0 hors audio ;
- 26 793 références = 13 227 matches du flux complet + 13 566 références
  manquées ; parmi les matches, 12 543 sont exclus du fit et 684 deviennent
  les cibles positives supervisées ;
- 1 786 NoteOn non instrumentés sont tous des retriggers explicitement exclus ;
  aucun autre motif non instrumenté n'est signalé.

## Porte de représentation

Le protocole impose au moins 8 exemples de chaque cible dans chaque cellule
corpus × partition et au moins 75 exemples de chaque cible par partition.

`representation_gate.passed=true` et `shortfalls=[]`. Les cellules GuitarSet
positives sont maintenant `31` (`fit`), `28` (`dev`) et `14`
(`calibration`) : elles dépassent toutes le minimum 8. Cette réussite ne
contourne pas la clause indépendante `fit_authorized=false`.

## Limites et suite autorisée

Le corpus V3 est une preuve de minage conforme et de représentation suffisante
selon cette porte ; il n'est ni une évaluation d'événements, ni une preuve que
la future tête réduira les faux NoteOn. Aucun modèle candidat n'a été entraîné
et aucun seuil n'a été calibré ou choisi.

La seule suite autorisée est une revue humaine du présent rapport et des deux
artefacts bruts avant de définir, explicitement, une hypothèse distincte. Aucun
nouveau replay, fit, calibration, validation, export, live, sélection de seuil
ou test verrouillé n'est autorisé par ce résultat seul.
