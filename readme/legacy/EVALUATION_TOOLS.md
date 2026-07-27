# Outils de diagnostic pitch

## Par âge réel de prédiction

```powershell
python -m src.train.evaluate_by_age --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\v1_fixed\best.keras" --validation-indices "runs\v1_fixed\validation_indices.npy"
```

## Par note MIDI

```powershell
python -m src.train.evaluate_by_pitch --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\v1_fixed\best.keras" --validation-indices "runs\v1_fixed\validation_indices.npy"
```

## Matrice de confusion

```powershell
python -m src.train.confusion_matrix --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\v1_fixed\best.keras" --validation-indices "runs\v1_fixed\validation_indices.npy"
```

La matrice CSV est générée par défaut dans :

```text
runs/v1_fixed/confusion_matrix.csv
```
