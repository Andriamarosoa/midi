# Contrat Dataset V5

## Format

Chaque morceau est stocké dans un fichier `.npz`.

## Champs obligatoires

| Champ | Dtype | Shape | Description |
|---|---|---:|---|
| `audio` | `float32` | `(N, 4096)` | Fenêtres audio causales |
| `visible_window` | `int32` | `(N,)` | Nombre d’échantillons réellement visibles |
| `prediction_age_ms` | `float32` | `(N,)` | Temps écoulé depuis l’attaque |
| `pitch_midi` | `int16/int32` | `(N,)` | Pitch MIDI, `-1` pour silence |
| `active` | `float32` | `(N,)` | Note active |
| `onset` | `float32` | `(N,)` | Première fenêtre d’attaque |
| `attack_phase` | `float32` | `(N,)` | Phase d’attaque |
| `release_phase` | `float32` | `(N,)` | Phase de release |
| `note_id` | `int32` | `(N,)` | Identifiant de note dans le morceau |
| `channel` | `int8/int32` | `(N,)` | Canal/corde GuitarSet |

## Champs harmoniques

| Champ | Dtype | Shape |
|---|---|---:|
| `fundamental_hz` | `float32` | `(N,)` |
| `harmonic_present` | `float32` | `(N, 20)` |
| `harmonic_amplitude` | `float32` | `(N, 20)` |
| `harmonic_offset_cents` | `float32` | `(N, 20)` |

## Règles

- `audio.shape[1]` doit être identique pour tous les fichiers.
- `visible_window` doit être compris entre `1` et `audio.shape[1]`.
- Une note active doit avoir un `pitch_midi` valide.
- Les exemples silencieux peuvent avoir `pitch_midi = -1`.
- Les fenêtres d’une même note partagent le même `note_id`.
- Le dataset builder doit être déterministe.
- Toute modification de schéma incrémente `dataset_version`.

## Version actuelle

```text
dataset_version = 2
sample_rate = 44100
hop_size = 256
max_window = 4096
visible_windows = [512, 1024, 2048, 4096]
```

## Révision V5.2 multi-source mono

V5.2 conserve le schéma NPZ de version 2 et change la provenance des
exemples. La révision de contenu est enregistrée sous
`v5.2-multisource-mono-1` dans `build_report.json`.

| Dataset | Entrée audio | Annotations | Usage V5.2 |
|---|---|---|---|
| GuitarSet | mix mono pickup officiel | JAMS `note_midi` | train/validation/test officiels par joueur |
| IDMT dataset1 | WAV mono | XML | train, notes seules hors dossiers Chords |
| IDMT dataset2 | WAV mono | XML | train, prises monophoniques `NO` uniquement |
| Guitar-TECHS | direct input et mic+amp | MIDI | train, P1/P2 single notes et scales |
| GAPS | audio à synthétiser depuis MIDI | MIDI | exclu du softmax V5.2, réservé au multi-label V6 |

Règles de construction :

- une fenêtre est conservée uniquement si une seule note annotée est active
  au temps de prédiction ;
- les notes hors de la plage MIDI 40--76 sont rejetées ;
- les sources 48 kHz sont rééchantillonnées à 44,1 kHz par filtrage
  polyphasé ; les annotations restent exprimées en secondes ;
- les deux captures synchronisées Guitar-TECHS partagent le même `group_id` ;
- le manifest enregistre `dataset_id`, `group_id`, `capture_id`, `split`,
  licence et chemins des sources ;
- les informations harmoniques absentes des corpus externes sont remplies à
  zéro. Elles ne doivent pas devenir une cible supervisée avant une règle de
  masquage explicite en V6.

## Schéma V3 — labels harmoniques multi-source

La construction harmonique utilise une nouvelle révision afin de ne pas
modifier les NPZ V5.2 pendant leur entraînement :

```text
dataset_version = 3
dataset_revision = v5.3-multisource-harmonics-1
```

Le champ suivant est ajouté :

| Champ | Dtype | Shape | Description |
|---|---|---:|---|
| `harmonic_label_valid` | `float32` | `(N, 20)` | 1 si la mesure du partiel peut participer à une loss, 0 sinon |

Les zéros de `harmonic_present`, `harmonic_amplitude` et
`harmonic_offset_cents` ne doivent être interprétés qu'aux positions où
`harmonic_label_valid = 1`. Ailleurs, ils signifient « inconnu ».

Dans la revision `v5.3-multisource-harmonics-1`, l'extracteur choisit le pic
maximal de chaque bande +/-35 cents. `harmonic_present` et
`harmonic_label_valid` sont donc identiques sur les donnees construites et ne
contiennent pas de vrais negatifs. V5.3 supervise l'amplitude et l'offset, mais
pas la presence. Une future cible de presence devra comparer le pic a un bruit
de fond local adaptatif.

Provenance des mesures :

- GuitarSet réutilise les 360 CSV calculés sur les canaux hexaphoniques
  débleedés, avec vérification du temps, du pitch et du `note_id` ;
- IDMT et Guitar-TECHS utilisent le même noyau FFT que GuitarSet sur la plus
  longue portion strictement monophonique de chaque note ;
- une mesure dont l'offset sort de la fenêtre ±35 cents est invalidée ;
- les amplitudes valides sont normalisées par note ;
- les mesures sont agrégées par note puis répétées sur ses fenêtres causales,
  comme dans le pipeline GuitarSet historique.

Commande de construction complète, à exécuter après la fin de V5.2 :

```powershell
.\.venv\Scripts\python.exe -m src.v5.external_data --extract-harmonics --output-dir data\processed\v5_3_harmonics
```

L'extraction est entièrement offline : elle n'ajoute aucun délai à
l'inférence live. Sur le pilote de 1 776 fenêtres, la construction passe de
8,01 s à 15,48 s et la taille disque de 13,45 Mio à 13,50 Mio.
