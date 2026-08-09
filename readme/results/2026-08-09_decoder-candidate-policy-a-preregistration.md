# Préinscription réelle Policy A — plan candidat et preuve d'actifs

## Autorisation et périmètre exécuté

La revue externe de `8190e3bff09d730fe830c59576a704e62c49320f` a autorisé une
seule opération sur le Mac : créer puis relire le plan de partitions Policy A
et le registre d'empreintes des actifs **éligibles**. Elle n'autorise ni replay
du décodeur, ni collecte de candidats, minage, entraînement, validation,
export, live ou test verrouillé.

L'opération a été exécutée dans `/Users/amcarene/midi`, branche
`codex/independent-note-neural-v2`, au commit exact :

```text
8190e3bff09d730fe830c59576a704e62c49320f
```

Le checkout était propre et aucun processus `src.polyphonic` actif n'a été
observé avant le lancement. Le contexte n'importe ni modèle ni TensorFlow pour
cette opération : il a seulement créé le plan persistant, haché les fichiers
audio/labels admissibles et réécrit le registre canonique.

## Résolution locale des chemins, sans copie de données

Le premier préflight lecture seule a constaté que les chemins du manifeste
pointaient vers `~/midi/data`, tandis que les mêmes actifs déjà présents sur le
Mac étaient sous `/Users/amcarene/midi-worker/data`. Aucune donnée ne manquait :
les 842 références absentes du checkout correspondaient exactement à trois
racines locales déjà disponibles.

Trois liens symboliques locaux ont donc été créés, sans copie, téléchargement
ni modification des datasets :

```text
/Users/amcarene/midi/data/GuitarSet
  -> /Users/amcarene/midi-worker/data/GuitarSet
/Users/amcarene/midi/data/processed/polyphonic_v2_1_gaps
  -> /Users/amcarene/midi-worker/data/processed/polyphonic_v2_1_gaps
/Users/amcarene/midi/data/processed/polyphonic_v2_2_guitar_techs
  -> /Users/amcarene/midi-worker/data/processed/polyphonic_v2_2_guitar_techs
```

Ils sont sous `data/`, qui est ignoré par Git. Le préflight suivant a confirmé
zéro chemin d'actif éligible manquant avant toute écriture immuable.

## Préflight du manifeste complet

| Contrôle | Résultat |
| --- | --- |
| Manifeste | `data/processed/polyphonic_harmonic_presence_v1/manifest_train_validation.csv` |
| SHA-256 avant et après | `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` |
| Lignes train historiques | 572 |
| Lignes validation historiques, inchangées | 182 |
| Exclusions Policy A | 31 prises `gaps_poly_mix`, 10 joueurs |
| Prises train éligibles au plan/registre | 541 |
| Chemins d'actifs éligibles manquants | 0 |
| `locked_test_used` | `false` |

Les dix joueurs exclus sont : Bradford Werner, Carlina Flores, David Tutmark,
Edson Lopes, Ken Takizawa, Maria Linnemann, Per-Olov Kindgren, Petra
Poláčková, Stephanie Jones et Thu Le. Aucun autre corpus-aware overlap n'a été
découvert.

## Artefacts persistants et relecture

Le plan est créé avec la seed `47`, écrit sans écrasement, relu, validé contre
le même snapshot manifeste, puis utilisé pour créer le registre. Une relecture
indépendante a ensuite confirmé que le registre couvre exactement les identités
du plan et aucune exclusion.

| Artefact Mac local | Taille | SHA-256 |
| --- | ---: | --- |
| `tmp/local/decoder_candidate_policy_a_preregistration_20260809/decoder_candidate_partition_plan_v2.json` | 145 859 octets | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` |
| `tmp/local/decoder_candidate_policy_a_preregistration_20260809/decoder_candidate_asset_evidence_v1.json` | 198 950 octets | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` |
| `tmp/local/decoder_candidate_policy_a_preregistration_20260809/preregistration_report.json` | 2 687 octets | `332aedcf99796694796e736b17d6c9940652dbcfa4700478b517569f6d58cdd1` |

Le plan porte le schéma `2` et la politique
`preserve_historical_validation_exclude_train_validation_leakage_groups_then_corpus_aware_hash_70_15_15_v1`.

| Partition | Prises | Groupes | GAPS | Guitar-TECHS DI | Guitar-TECHS mic | GuitarSet |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| fit | 335 | 145 | 151 | 32 | 32 | 120 |
| dev | 102 | 32 | 28 | 7 | 7 | 60 |
| calibration | 104 | 32 | 30 | 7 | 7 | 60 |
| total | 541 | 209 | 209 | 46 | 46 | 240 |

L'invariant final relu est : `541` identités de plan = `541` entrées de
registre ; intersection avec les `31` exclusions = vide.

## Limites et arrêt obligatoire

La préinscription a pris `2,801 s`. Ce temps couvre le plan, les empreintes et
le registre, pas une inférence ou une mesure de latence live. Aucun modèle,
checkpoint, seuil ou événement MIDI n'a été chargé ou promu.

Les artefacts bruts restent volontairement locaux et ignorés par Git, mais les
trois chemins, tailles et SHA-256 ci-dessus permettent leur audit sans les
reproduire. Ils sont immuables : ne pas les recréer ni les écraser.

La prochaine action autorisée est **uniquement une revue externe de cette
préinscription**. Aucun minage train-only ne peut commencer avant son
approbation explicite.
