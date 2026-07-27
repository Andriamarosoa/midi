# CLAUDE.md — Plan d’exécution V5

## Mission

Implémenter V5 sans casser V4.

V4 reste la baseline fonctionnelle.

## Ordre obligatoire

### Étape 1 — Cache

Créer `src/v5/cache.py`.

Critères :

- charge chaque NPZ une seule fois ;
- mesure la RAM ;
- valide les champs requis ;
- aucun chargement pendant l’époque.

### Étape 2 — Dataset

Créer `src/v5/dataset.py`.

Critères :

- index global `(file_id, sample_id)` ;
- filtres actifs/pitch ;
- distributions sauvegardées ;
- accès O(1).

### Étape 3 — Sampler

Créer `src/v5/sampler.py`.

Critères :

- shuffle par époque ;
- chaque exemple vu une fois ;
- déterminisme par seed ;
- mode équilibré optionnel.

### Étape 4 — DataLoader

Créer `src/v5/dataloader.py`.

Critères :

- batches `audio`, `time_mask`, `pitch` ;
- aucun accès disque ;
- clipping et gain global ;
- compatible `tf.keras.utils.Sequence`.

### Étape 5 — Train

Créer `src/v5/train.py`.

Critères :

- split par joueur ;
- sauvegarde complète du run ;
- callbacks ;
- reprise possible ;
- évaluation automatique.

### Étape 6 — Evaluate

Créer `src/v5/evaluate.py`.

Critères :

- mêmes rapports que V4 ;
- pas de matérialisation inutile ;
- types numériques forcés ;
- résultats reproductibles.

## Commandes minimales

```powershell
python -m compileall src\v5
```

```powershell
python -m src.v5.train --config "configs\pitch_v5.yaml"
```

## Interdictions

- ne pas modifier `src/v4` ;
- ne pas modifier les NPZ existants ;
- ne pas ajouter de nouvelles têtes avant la stabilisation du loader ;
- ne pas optimiser le modèle avant d’avoir mesuré le pipeline V5.

## Critère de fin V5

V5 est accepté si :

- le train complet parcourt chaque exemple une fois ;
- aucun NPZ n’est rouvert pendant une époque ;
- les résultats sont reproductibles ;
- les rapports sont générés ;
- le modèle reste rechargeable ;
- la mémoire maximale est documentée.
