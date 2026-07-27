# Évaluation V5

## Métriques principales

- top-1 ;
- top-3 ;
- accuracy macro par pitch ;
- erreur absolue moyenne en demi-tons ;
- erreurs ±1 demi-ton ;
- erreurs d’octave ;
- matrice de confusion.

## Rapports obligatoires

```text
reports/
├── summary.md
├── metrics.json
├── prediction_age_ms.csv
├── visible_window.csv
├── pitch_midi.csv
├── player_id.csv
├── source_id.csv
└── confusion.csv
```

## Comparaison d’expériences

Une comparaison n’est valide que si :

- le split est identique ;
- la seed est enregistrée ;
- le dataset version est identique ;
- les métriques sont calculées sur le même test ;
- les fenêtres et la normalisation sont identiques.

## Baselines

- hasard top-1 sur 49 classes : environ 2,04 % ;
- hasard top-3 : environ 6,12 % ;
- V4 doit rester la baseline de comparaison.

## Ventilation V5.2

Le rapport V5.2 ajoute `dataset_id.csv` afin de mesurer séparément chaque
corpus sur les splits qui en contiennent. La métrique test principale reste
calculée sur GuitarSet joueur 05 pour conserver un test jamais vu.

## Rapports V5.3

`reports/harmonic_metrics.json` compare les sorties auxiliaires a des
baselines constantes :

- MAE d'amplitude sur les partiels valides et baseline zero ;
- MAE d'offset en cents, ponderee par l'amplitude, et baseline zero.

Une tete harmonique n'est consideree utile que si elle bat sa baseline sans
degradation reproductible du pitch.
