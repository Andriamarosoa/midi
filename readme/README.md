# Guitar MIDI AI 1.0.0

Moteur causal de transcription **guitare → MIDI**, utilisable en direct sur Windows ou sur un fichier WAV.

## Live polyphonique desktop V2.2.1

Le moteur polyphonique desktop utilise le bundle
`artifacts\guitar_midi_polyphonic_v2_2_0` (produit 2.2.1). Le nombre de
threads recommandé, 3, vient des métadonnées : il ne faut donc pas forcer
`--threads 1`.

Capture de diagnostic reproductible pendant 60 secondes :

```powershell
.\START_LIVE_POLYPHONIC.bat `
  --audio-device "1" --midi-device "0" --console-midi `
  --duration-s 60 `
  --record-wav runs\polyphonic\live_v221.wav `
  --debug-npz runs\polyphonic\live_v221.npz `
  --report-json runs\polyphonic\live_v221.json
```

Le nivellement automatique est désactivé par défaut : sur validation, il
récupérait très peu de notes faibles mais ajoutait beaucoup de notes fantômes
et de fragmentation. `--auto-level` reste une option explicite
d'expérimentation. `--audio-gain` agit avant le gate, l'onset, le WAV et le
modèle ; garder `1.0` sauf diagnostic mesuré, car une valeur trop forte peut
écrêter et créer de fausses harmoniques.

Le décodeur applique désormais le seuil fort déjà configuré (`0.90`) aux
notes créées sans attaque physique récente. Sur 12 validations, cela retire
4 387 fausses notes et 328 faux harmoniques, mais manque 279 notes vraies
supplémentaires. Ce compromis est volontaire pour le profil desktop
anti-fantômes ; les accords GAPS très denses perdent davantage de rappel.

Le produit 1.0 combine le modèle V6.0 `pitch + active + harmoniques` et la porte V6.3.3 de transition entraînée à partir des labels existants `onset`, `note_id` et harmoniques. Les modèles TFLite et ONNX restent disponibles pour le runtime desktop.

## Démarrage rapide Windows

Lister les interfaces :

```powershell
.\.venv\Scripts\python.exe -m src.product.live --list-devices
```

Lancer le live avec les périphériques par défaut :

```powershell
.\START_LIVE.bat
```

L'entrée automatique ouvre réellement le périphérique système et son équivalent
WASAPI au contrat 44,1 kHz/256, puis conserve la latence négociée la plus basse.
Le pin d'entrée WDM-KS n'est plus choisi automatiquement : sur la puce Realtek
de validation, il contourne le gain microphone et livre un signal presque
silencieux malgré une latence annoncée excellente. Un index explicite reste
toujours honoré. La sortie FluidSynth continue, elle, d'utiliser WDM-KS quand
ce backend est sain.

Pour une sortie audio locale directe, sans Microsoft GS Wavetable Synth :

```powershell
.\.venv\Scripts\python.exe -m src.product.live `
  --artifacts artifacts\guitar_midi_v1_0_0 `
  --soundfont "C:\Users\user\Downloads\FluidR3 GM.sf2" --no-midi
```

Cette option requiert `pyfluidsynth` ainsi que la bibliothèque native
FluidSynth. Ils sont installés dans l'environnement de développement actuel;
le SoundFont reste un fichier externe choisi explicitement.

La sortie FluidSynth utilise un bloc de rendu de 128 échantillons indépendant
du hop modèle de 256. Cela réduit l'attente des commandes MIDI sans modifier
les fenêtres ou les décisions du réseau.

Le stress WDM-KS de 30 s avait mesuré 3,38 ms dans chaque sens, mais il ne
contenait aucune note et ne validait donc pas la sensibilité du microphone.
Une capture instrumentée a ensuite mesuré seulement −82,3 dBFS en médiane et
aucune détection sur ce pin, contre un signal exploitable et 230 NoteOn avec
l'entrée Realtek système. Le mode sûr conserve la sortie WDM-KS à 3,38 ms et
utilise automatiquement l'entrée fonctionnelle la plus rapide (17,41 ms MME
sur la machine de validation). Cela représente environ 20,79 ms d'I/O
négociée. La latence acoustique exacte nécessite encore une mesure loopback.

La même option fonctionne avec `START_LIVE_POLYPHONIC.bat`. Sans
`--soundfont`, la sortie MIDI WinMM historique reste inchangée. Avec un
SoundFont et sans `--no-midi`, les événements sont envoyés aux deux sorties.

```powershell
.\START_LIVE_POLYPHONIC.bat `
  --soundfont "C:\Users\user\Downloads\FluidR3 GM.sf2" `
  --no-midi --console-midi
```

Rester silencieux pendant la calibration (une seconde normalement, jusqu'à
trois secondes si le bruit n'est pas encore stable). Le gate de présence fige
alors deux seuils de bruit avec hystérésis; le détecteur d'attaque peut continuer
à s'adapter sans apprendre la guitare comme du silence. Cela n'ajoute aucun hop
aux NoteOn après la calibration. Une surcharge transitoire
déclenche un panic MIDI, vide les blocs devenus périmés, réinitialise le
contexte causal puis reprend automatiquement. Un flux microphone arrêté ou
une sortie audio durablement défaillante provoque un arrêt propre avec une
raison explicite dans le rapport JSON.

La ligne d'état polyphonique affiche aussi `input=...dBFS`. Pendant une note
normale, une valeur qui reste sous environ −60 dBFS indique un mauvais endpoint,
un niveau matériel trop bas ou une entrée non adaptée à la guitare.

## WAV vers MIDI

```powershell
.\TRANSCRIBE_WAV.bat entree.wav sortie.mid
```

Le fichier JSON placé à côté du MIDI contient les événements et la latence d'inférence. Le chemin WAV utilise exactement le moteur causal du live, avec une seconde de silence ajoutée uniquement pour sa calibration.

## Résultats du bundle livré

| Contrôle | Résultat |
|---|---:|
| Parité TFLite décisions pitch/active/gate | 100 % |
| Parité ONNX décisions pitch/active/gate | 100 % |
| TFLite pitch isolé, p95, 1 thread | 1,41 ms |
| Live Windows 20 s, retard pipeline p95 | 31,66 ms |
| Live Windows, pertes audio | 0 |
| Live Windows, inférences sautées | 2,01 % |
| GuitarSet joueur 05, fantômes profil sûr | 28,42/min |
| Référence V6.3.3 joueur 05 | 51,02/min |
| Guitar‑TECHS direct, pitch top‑1 | 94,67 % |
| Guitar‑TECHS micro+ampli, pitch top‑1 | 90,20 % |
| IDMT D1, pitch top‑1 | 81,20 % |
| IDMT D2, pitch top‑1 | 49,73 % — hors domaine garanti |

Le profil `safe_low_ghost` privilégie la réduction des fausses notes. Il peut fusionner des répétitions rapides de la même hauteur : 10 notes manquantes sur 199 au test verrouillé, contre 5 dans la référence plus permissive. La régression stricte est donc marquée échouée dans le rapport, tandis que le contrat produit anti‑fantômes est accepté.

## Domaine supporté

- Guitare monophonique propre, plage MIDI 40–76.
- GuitarSet, Guitar‑TECHS direct/micro et IDMT D1 ont été mesurés.
- Les harmoniques V5.3 sont validées sur GuitarSet, Guitar‑TECHS et IDMT.
- IDMT D2 n'est pas garanti en raison de sa forte chute de pitch.
- GAPS est disponible mais polyphonique. Une softmax unique ne peut pas représenter ses accords ; son intégration correcte exige une tête multi‑label par classe MIDI. GAPS n'est donc ni ignoré ni utilisé avec un faux label monophonique.

## Artefacts et preuves

Le dossier [artifacts/guitar_midi_v1_0_0](../artifacts/guitar_midi_v1_0_0) contient les modèles TFLite/ONNX/SavedModel, `metadata.json`, `release_manifest.json` et les rapports : parité, latence, stride, backpressure, WAV causal, multisource et harmoniques externes.

La distribution PC est également fournie sous forme de `midi-1.0.0-py3-none-any.whl` ; les modèles restent dans le bundle d'artefacts afin que leurs hashes puissent être contrôlés séparément.

`external_smoke_guitar_techs.wav` est un extrait de 8 s de `Guitar-TECHS/P1_scales/directinput_A.wav` (Guitar‑TECHS, licence CC‑BY‑4.0) accompagné du MIDI réellement produit et de son rapport JSON. Il sert uniquement de smoke test reproductible hors GuitarSet.

Tests principaux :

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests
```

Les historiques V1→V6 sont classés dans `readme/versions` et
`readme/legacy`. L'organisation des entrées et sorties audio est décrite dans
`readme/DATA_LAYOUT.md`. Le runtime polyphonique V2.2 demeure expérimental :
sa qualité événementielle en live doit encore être améliorée avant de
remplacer le profil monophonique stable.
