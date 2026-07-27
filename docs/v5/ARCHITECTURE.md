# Architecture V5

## Objectif

Séparer strictement les responsabilités afin que les évolutions du modèle ne cassent pas le dataset, le loader ou le streaming.

## Modules

### `manifest.py`

Responsable de :

- charger `manifest.csv` ;
- valider les chemins NPZ ;
- extraire `player_id`, `source_id`, style et variante ;
- construire les splits train/validation/test.

Interdit :

- charger les tableaux audio ;
- construire les batches ;
- connaître TensorFlow.

### `cache.py`

Responsable de :

- charger les NPZ une seule fois ;
- conserver les tableaux utiles en RAM ;
- fournir un accès par `file_id` ;
- mesurer la mémoire utilisée.

Interdit :

- mélanger les exemples ;
- appliquer le gain ;
- créer les labels.

### `dataset.py`

Responsable de :

- construire l’index global `(file_id, sample_id)` ;
- filtrer les exemples valides ;
- exposer les métadonnées ;
- fournir la distribution des classes.

### `sampler.py`

Responsable de :

- mélanger les indices ;
- parcourir chaque exemple une fois par époque ;
- fournir éventuellement un échantillonnage légèrement équilibré ;
- rester déterministe avec une seed.

### `dataloader.py`

Responsable de :

- convertir les indices en batches ;
- appliquer gain, masque causal et clipping ;
- retourner `inputs`, `targets`, `metadata`.

### `frontend.py`

Responsable de la préparation audio partagée entre entraînement et streaming.

### `model.py`

Responsable uniquement de :

```text
audio + time_mask → sorties du réseau
```

Aucun accès fichier, aucune logique de split, aucun code de reporting.

### `evaluate.py`

Responsable de :

- top-1 ;
- top-3 ;
- précision par âge ;
- précision par fenêtre ;
- précision par pitch ;
- précision par joueur ;
- matrice de confusion ;
- erreurs en demi-tons et octaves.

## Flux d’entraînement

```text
manifest.csv
  ↓
split par joueur
  ↓
cache RAM
  ↓
index global
  ↓
shuffle déterministe
  ↓
batches
  ↓
model.fit()
  ↓
évaluation test
```

## Flux streaming

```text
microphone
  ↓
ring buffer
  ↓
fenêtre causale
  ↓
time_mask
  ↓
même frontend
  ↓
même modèle
  ↓
pitch + confiance
```
