# Modèle V5

## Entrées

```text
audio      : (batch, 4096, 1)
time_mask  : (batch, 4096)
```

## Baseline

```text
Mask
 ↓
Conv1D causal stride 4
 ↓
LayerNorm
 ↓
Conv1D causal stride 4
 ↓
LayerNorm
 ↓
4 blocs TCN résiduels
 ↓
Pooling hybride
 ↓
Dense partagé
 ↓
Pitch head
```

## Pooling hybride

Concaténation de :

- dernier état causal ;
- moyenne globale temporelle.

Le modèle ne doit contenir aucune `Lambda` Python non sérialisable.

## Sorties prévues

V5 initial :

```text
pitch
```

Extensions futures :

```text
pitch
onset
active
fundamental_hz
harmonic_present
harmonic_amplitude
harmonic_offset_cents
confidence
```

## V5.3 - auxiliaires harmoniques

V5.3 conserve le pitch softmax comme sortie principale et ajoute deux sorties
auxiliaires de 20 valeurs :

```text
harmonic_amplitude    : sigmoid, amplitude relative 0--1
harmonic_offset_cents : tanh borne a +/-35 cents
```

`harmonic_present` n'est pas appris dans cette experience : l'extracteur
actuel trouve un maximum spectral dans presque chaque bande harmonique et ne
fournit donc pas de vrais exemples negatifs. La loss d'offset est ponderee
continument par l'amplitude cible afin de reduire l'influence des pics faibles
sans seuil de presence manuel.

Les tetes partagent le meme embedding causal que le pitch. Elles n'ajoutent ni
lookahead ni delai algorithmique ; leur cout d'inference doit etre mesure avant
le streaming.

## Contraintes

- causalité stricte ;
- sérialisation `.keras` sans `safe_mode=False` ;
- export ONNX/TFLite visé ;
- aucune dépendance à GuitarSet dans `model.py`.
