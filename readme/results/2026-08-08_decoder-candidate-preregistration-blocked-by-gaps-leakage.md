# Anomalie de préinscription — chevauchement GAPS train/validation

## Opération autorisée et périmètre

La revue stricte de `d16b25f7c754f85483f97abcb47e11ea25ab06d5` a autorisé une
seule action sur le Mac : préinscrire le plan group-safe persistant et le
registre d'empreintes des actifs **train**. Elle n'autorisait aucun replay du
décodeur, aucune collecte, aucun minage, entraînement, validation, export,
live ou test verrouillé.

Le checkout Mac `/Users/amcarene/midi` a été synchronisé par fast-forward sur
`d16b25f7`. Aucun processus Python `src.polyphonic` n'était actif. Le checkout
a reçu un lien local vers le répertoire de données déjà présent sous
`/Users/amcarene/midi-worker/data/processed`; ce lien ne copie ni ne modifie
aucune donnée.

## Résultat : arrêt fail-closed avant le hachage des actifs

La création du plan, avec le manifeste exact :

```text
data/processed/polyphonic_harmonic_presence_v1/manifest_train_validation.csv
SHA-256 b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
seed 47
```

s'est arrêtée dans `candidate_train_items_only()` avant toute écriture de plan
et avant le hachage d'un actif. Le garde a détecté un chevauchement de groupe
de fuite entre train et validation : dix joueurs du corpus `gaps_poly_mix`.

| Joueur GAPS | Train | Validation |
| --- | ---: | ---: |
| bradford_werner | 1 | 1 |
| carlina_flores | 2 | 1 |
| david_tutmark | 3 | 1 |
| edson_lopes | 15 | 2 |
| ken_takizawa | 1 | 1 |
| maria_linnemann | 2 | 1 |
| per_olov_kindgren | 1 | 1 |
| petra_polackova | 2 | 1 |
| stephanie_jones | 2 | 1 |
| thu_le | 2 | 1 |

Le manifeste conserve par ailleurs `572` prises train et `182` prises
validation. Ce chevauchement de joueurs rendrait une collecte train-only
incompatible avec la validation officielle ; le refus est donc le résultat
attendu du contrat group-safe.

## Intégrité de l'échec

Le répertoire de destination de la préinscription a été créé vide avant le
garde, puis constaté vide et supprimé par `rmdir` (non récursif). Il n'existe :

- aucun plan réel JSON ;
- aucun registre réel d'empreintes ;
- aucun SHA de plan ou de registre à promouvoir ;
- aucun hash d'audio ou labels ;
- aucun artefact candidat ni poids.

`locked_test_used=false`. Le test verrouillé n'a pas été lu.

## Suite bloquée

Il ne faut pas contourner ce garde ni retrier avec un sous-ensemble manuel.
La prochaine décision scientifique doit définir et faire relire une politique
de split GAPS réellement group-safe (par exemple répartition complète des
joueurs entre train/validation et conséquences sur les cohortes). Seulement
après un manifeste versionné/revu sans chevauchement train/validation pourra
être créée une **nouvelle** préinscription immuable, suivie de sa propre revue.
