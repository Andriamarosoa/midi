# Streaming V5

## Paramètres de référence

```text
sample_rate = 44100 Hz
hop_size = 256 samples
hop_duration = 5.80 ms
max_window = 4096 samples
max_window_duration = 92.88 ms
```

## Pipeline

```text
Microphone
  ↓
Ring Buffer 4096
  ↓
Nouveau hop 256
  ↓
Fenêtre causale
  ↓
Masque visible
  ↓
Frontend partagé
  ↓
Modèle V5
  ↓
Pitch + confiance
```

## Règles temps réel

- aucune allocation importante dans la boucle audio ;
- aucun accès disque ;
- pas de traitement non causal ;
- le callback audio ne lance pas directement l’inférence lourde ;
- communication via buffer SPSC ou file lock-free ;
- mesure de latence obligatoire.

## Décision progressive

Le système peut produire :

```text
11.6 ms  → hypothèse faible
23.2 ms  → hypothèse mise à jour
46.4 ms  → confirmation intermédiaire
92.9 ms  → confirmation stable
```

La confiance doit évoluer avec l’âge de la note.

## Latence

La latence bout en bout doit inclure :

- buffer d’entrée ;
- fenêtre disponible ;
- inférence ;
- décision ;
- sortie MIDI/audio.
