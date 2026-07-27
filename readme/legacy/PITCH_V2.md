# Pitch-only V2

Cette version corrige l'effondrement vers la classe MIDI dominante.

## Changements

- entraînement uniquement sur le pitch ;
- batches réellement équilibrés par note MIDI ;
- une normalisation globale calculée sur le train uniquement ;
- dernier état causal au lieu de `GlobalAveragePooling1D` ;
- split par `note_id` conservé ;
- diagnostics compatibles avec la normalisation V2.

## Entraîner

```powershell
python -m src.train.train_pitch_only --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --epochs 60
```

Sorties :

```text
runs/pitch_v2/
├── best.keras
├── final.keras
├── history.csv
├── normalization.json
├── train_indices.npy
├── validation_indices.npy
└── training_report.json
```

## Évaluer par âge

```powershell
python -m src.train.evaluate_by_age --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\pitch_v2\best.keras" --validation-indices "runs\pitch_v2\validation_indices.npy" --normalization "runs\pitch_v2\normalization.json"
```

## Évaluer par fenêtre

```powershell
python -m src.train.evaluate_by_window --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\pitch_v2\best.keras" --validation-indices "runs\pitch_v2\validation_indices.npy" --normalization "runs\pitch_v2\normalization.json"
```

## Évaluer par pitch

```powershell
python -m src.train.evaluate_by_pitch --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\pitch_v2\best.keras" --validation-indices "runs\pitch_v2\validation_indices.npy" --normalization "runs\pitch_v2\normalization.json"
```

## Matrice de confusion

```powershell
python -m src.train.confusion_matrix --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\pitch_v2\best.keras" --validation-indices "runs\pitch_v2\validation_indices.npy" --normalization "runs\pitch_v2\normalization.json"
```
