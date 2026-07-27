# Entrée audio mono en streaming

Ce module fournit uniquement l'entrée temps réel du futur prédicteur :

- capture micro mono ;
- hop de 256 échantillons ;
- ring buffer de 4096 échantillons ;
- fenêtres causales préallouées de 512, 1024, 2048 et 4096 échantillons ;
- aucun calcul lourd dans le callback audio.

## Fichiers

```text
src/
└── stream/
    ├── __init__.py
    ├── ring_buffer.py
    ├── live_input.py
    └── test_ring_buffer.py
```

## Dépendances

Ajouter au `pyproject.toml` :

```toml
dependencies = [
    "numpy>=1.23,<2.0",
    "sounddevice>=0.4.6,<0.6",
]
```

Puis :

```powershell
python -m pip install -e .
```

## Tester le ring buffer

```powershell
python -m src.stream.test_ring_buffer
```

## Lancer le micro

```powershell
python -m src.stream.live_input
```

Avec un périphérique particulier :

```powershell
python -m src.stream.live_input --device 1
```

Lister les périphériques :

```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

## Où brancher le modèle

Dans `live_input.py`, remplacer :

```python
prediction_placeholder(...)
```

par l'appel au modèle.

Le dictionnaire `windows` contient :

```python
windows[512]
windows[1024]
windows[2048]
windows[4096]
```

Chaque tableau est un `float32` mono et contient les échantillons les plus récents.

À 44,1 kHz :

- 512 = 11,61 ms ;
- 1024 = 23,22 ms ;
- 2048 = 46,44 ms ;
- 4096 = 92,88 ms ;
- hop 256 = nouvelle prédiction toutes les 5,80 ms.
