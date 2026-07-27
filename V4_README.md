# V4 multi-file GuitarSet

La V4 charge les 360 NPZ via `manifest.csv` sans concaténer tout le dataset en RAM.

Split par interprète:
- train: 00, 01, 02, 03
- validation: 04
- test: 05

Commande:
```powershell
python -m src.v4.train --config "configs\pitch_v4.yaml"
```

Sorties: `runs/v4/pitch_v4_<timestamp>/`.

Attention: le test est matérialisé en RAM à la fin pour les rapports. Si la mémoire est insuffisante, réduisez temporairement `test_players` ou adaptez l'évaluation en streaming.
