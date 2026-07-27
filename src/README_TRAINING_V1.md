# Entraînement V1

## Fichiers

```text
src/
├── dataset/
│   └── tf_dataset.py
├── model/
│   ├── __init__.py
│   └── cnn_tcn.py
└── train/
    ├── __init__.py
    ├── check_loader.py
    └── train_v1.py
```

## Dépendance TensorFlow pour Python 3.9

```powershell
python -m pip install "tensorflow==2.15.*"
```

Ajouter au `pyproject.toml` :

```toml
"tensorflow>=2.15,<2.16"
```

## Vérifier le loader

```powershell
python -m src.train.check_loader --npz "data\dataset\stream\00_BN1-129-Eb_comp_hex.npz"
```

## Entraîner

```powershell
python -m src.train.train_v1 --npz "data\dataset\stream\00_BN1-129-Eb_comp_hex.npz" --epochs 30
```

Sorties :

```text
runs/v1/
├── best.keras
├── final.keras
└── history.csv
```

## Important

Ce premier entraînement sur un seul morceau sert uniquement à vérifier le pipeline.
La séparation train/validation par exemples d'un même morceau provoque une fuite de
contexte. Pour une mesure fiable, utiliser plusieurs morceaux et séparer par fichier.
