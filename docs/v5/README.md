# MIDI V5 — Streaming Foundation

## Vision

MIDI V5 est la fondation stable du moteur de reconnaissance audio monophonique en temps réel.

L’objectif n’est pas seulement de prédire une note, mais de produire une estimation progressive et causale à mesure que davantage d’audio devient disponible.

Le même pipeline doit servir :

- l’entraînement ;
- l’évaluation offline ;
- l’inférence temps réel sur PC ;
- l’export ONNX/TFLite ;
- les futurs déploiements Android.

## Principes

1. Une seule représentation d’entrée : `audio + time_mask`.
2. Aucun accès disque dans le modèle.
3. Aucun accès disque pendant une époque d’entraînement.
4. Le dataset est versionné et documenté.
5. Les splits sont reproductibles.
6. Les métriques sont générées automatiquement.
7. Toute modification du format NPZ exige une migration.
8. Toute nouvelle fonctionnalité doit avoir un test.
9. Toute architecture doit rester causale.
10. Les performances doivent être mesurées avant et après chaque changement.

## Pipeline global

```text
Manifest
  ↓
NPZ Cache
  ↓
Global Sample Index
  ↓
Sampler
  ↓
Batch Loader
  ↓
Audio Frontend
  ↓
CNN causal
  ↓
TCN causal
  ↓
Shared Embedding
  ↓
Task Heads
  ↓
Evaluation / Streaming
```

## Structure cible

```text
src/v5/
├── config.py
├── manifest.py
├── cache.py
├── dataset.py
├── sampler.py
├── dataloader.py
├── frontend.py
├── model.py
├── losses.py
├── metrics.py
├── evaluate.py
├── inference.py
├── train.py
└── utils.py
```

## Statut

V4 reste la baseline fonctionnelle.

V5 remplace uniquement l’infrastructure de données et la reproductibilité. Les changements d’architecture du réseau doivent être évalués séparément.
