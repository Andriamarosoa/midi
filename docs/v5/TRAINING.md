# Entraînement V5

## Split officiel

Par joueur :

```text
train       : 00, 01, 02, 03
validation  : 04
test        : 05
```

Aucun joueur ne doit apparaître dans plusieurs splits.

## Split V5.2

Le champ `split` explicite du manifest est prioritaire sur le joueur :

- GuitarSet 00--03 : train ;
- GuitarSet 04 : validation ;
- GuitarSet 05 : test ;
- IDMT et Guitar-TECHS : train uniquement.

Le test reste donc constitué exclusivement de GuitarSet jamais vu. Un
`group_id` ne peut appartenir qu'à un seul split ; cette contrainte empêche
notamment les captures direct input et mic+amp d'une même performance de
fuir entre train et validation/test.

La configuration `pitch_v5_2.yaml` désactive les poids de classes pour isoler
l'effet du changement de données. V5.1 a montré que les poids plafonnés à 10
amélioraient le macro rare mais dégradaient fortement le top-1 global.

Deux expériences contrôlées utilisent le même manifest, le même test et les
mêmes hyperparamètres :

1. `pitch_v5_2_guitarset_mono.yaml` filtre `guitarset_mono_mix` ;
2. `pitch_v5_2.yaml` inclut GuitarSet, IDMT et Guitar-TECHS.

La seconde ne doit être interprétée comme un gain des données externes qu'en
comparaison directe avec la première.

## Normalisation

Le gain global est calculé uniquement sur le train.

```text
gain = target / percentile(train_peaks)
```

avec limitation par `max_gain`.

## Époque

Une époque complète doit voir chaque exemple exactement une fois.

```text
shuffle(global_indices)
  ↓
batch 0
batch 1
...
```

Pas de tirage aléatoire avec remise par batch dans le mode standard.

## Callbacks

- `ModelCheckpoint` sur `val_top1` ;
- `EarlyStopping` avec restauration des meilleurs poids ;
- `ReduceLROnPlateau` sur `val_loss` ;
- `CSVLogger` ;
- `TerminateOnNaN`.

## Sorties de run

```text
runs/v5/<run_id>/
├── best.keras
├── final.keras
├── config.json
├── dataset_statistics.json
├── normalization.json
├── split_report.json
├── history.csv
├── reports/
└── plots/
```

## Experience V5.3 GuitarSet harmonique

La premiere experience V5.3 reste limitee a `guitarset_mono_mix` afin de ne
pas confondre l'effet des tetes harmoniques avec le melange multi-source :

```powershell
.\.venv\Scripts\python.exe -m src.v5.train --config configs\pitch_v5_3_guitarset_harmonics.yaml
```

Le checkpoint est choisi sur `val_pitch_top1`. L'evaluation finale recharge
toujours `best.keras`, meme si la limite d'epochs est atteinte avant le
declenchement de l'early stopping.

## Reproductibilité

Chaque run sauvegarde :

- seed ;
- configuration complète ;
- chemins des fichiers ;
- distribution des classes ;
- git commit si disponible ;
- versions Python, TensorFlow et NumPy.
