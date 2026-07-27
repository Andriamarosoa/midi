# Dataset streaming V2

## Fichiers

```text
src/dataset/
├── __init__.py
├── build_stream_dataset.py
├── inspect_dataset.py
├── visualize_sample.py
├── dataset.py
└── split_dataset.py
```

## Construire un dataset

```powershell
python -m src.dataset.build_stream_dataset --wav "data\GuitarSet\audio_hex-pickup_original\00_BN1-129-Eb_comp_hex.wav" --jams "data\GuitarSet\annotation\00_BN1-129-Eb_comp.jams" --harmonic-csv "data\processed\00_BN1-129-Eb_comp_hex.csv"
```

## Inspecter

```powershell
python -m src.dataset.inspect_dataset --npz "data\dataset\stream\00_BN1-129-Eb_comp_hex.npz"
```

## Visualiser un exemple

```powershell
python -m src.dataset.visualize_sample --npz "data\dataset\stream\00_BN1-129-Eb_comp_hex.npz" --index 0
```

## Créer les splits

```powershell
python -m src.dataset.split_dataset --manifest "data\dataset\stream\manifest.csv"
```
