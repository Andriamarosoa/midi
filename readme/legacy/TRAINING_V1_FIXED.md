# Training V1 corrigé

Corrections :

- split stable par `note_id` avant tout shuffle ;
- aucune fenêtre d'une même note dans train et validation ;
- silences répartis séparément ;
- métriques pitch pondérées et masquées ;
- pondération optionnelle des classes de pitch ;
- checkpoint basé sur `val_pitch_top1` ;
- rapport top-1/top-3 par taille de fenêtre.

## Entraîner

```powershell
python -m src.train.train_v1 --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --epochs 40
```

## Évaluer par fenêtre

```powershell
python -m src.train.evaluate_by_window --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --model "runs\v1_fixed\best.keras" --validation-indices "runs\v1_fixed\validation_indices.npy"
```

## Désactiver temporairement l'équilibrage pitch

```powershell
python -m src.train.train_v1 --npz "data\processed\stream\00_BN1-129-Eb_comp_hex.npz" --no-pitch-balance
```
