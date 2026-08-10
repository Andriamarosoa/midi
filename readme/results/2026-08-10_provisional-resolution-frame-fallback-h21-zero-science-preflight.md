# H21 — Scellement zéro-science des actifs et du runtime H17

## Statut

`provisional_resolution_frame_fallback_h21_zero_science_preflight_sealed`

H21 ferme uniquement les valeurs opérationnelles laissées `null` par H20. Il
n’implémente, n’importe et n’invoque aucun runner scientifique. Il ne crée ni
destination de résultat, ni marqueur d’autorisation, ni état de consommation.

## Exécution contrôlée sur le worker Mac prévu

Le helper standard-library a été exécuté sur le checkout exact H20 :

```text
repository : /Users/amcarene/midi-worker/repository
commit     : 79c02c0aa07df4c17cda2bb4eac9fd9cf47f97c5
Python     : /Users/amcarene/midi-worker/.venv/bin/python
version    : CPython 3.11.9
système    : Darwin 24.5.0 arm64
NumPy      : 1.26.4
TensorFlow : 2.15.1 (distribution seulement, aucun import)
Keras      : 2.15.0 (distribution seulement, aucun import)
CPU futur  : MIDI_FORCE_CPU=1
```

Les versions de paquets proviennent uniquement de `importlib.metadata`. Aucun
GPU n’a été interrogé et TensorFlow/Keras n’ont pas été importés.

## Liaison préalable et inventaire brut

Avant le premier hachage d’actif, le helper a vérifié le commit/bloc H20, H18a,
H17, H17a, H19a, le décodeur, l’extracteur causal, l’univers de groupes, le
grouping et les trois sources du target. Le manifeste brut reste lié au SHA-256
`b28cb17c…`.

L’inventaire correspond exactement aux identités H18a :

```text
prises                         146
groupes de fuite                51
classification                  fresh_discovery_only_not_independent_validation
chemins audio résolus uniques   87
chemins labels résolus uniques 146
```

Pour chaque prise, le JSON conserve identité, groupe, corpus, chemins logiques
et résolus, `audio_member`, tailles brutes et SHA-256 audio/labels. Les chemins
ont été résolus par `Path.resolve(strict=True)`; chaque fichier devait être
régulier et lisible. Les octets ont été lus en blocs de 1 MiB uniquement pour
taille et SHA-256, avec cache par chemin résolu. Aucun audio n’a été décodé et
aucun label n’a été parsé.

Le checkpoint exact a été lu comme octets bruts uniquement :

```text
taille  : 5 587 783 octets
SHA-256 : 1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325
chargé  : non
```

## Chemins futurs scellés mais non créés

```text
destination
/Users/amcarene/midi-worker/repository/tmp/local/provisional_resolution_frame_fallback_h17_real_execution

marqueur
/Users/amcarene/midi-worker/repository/tmp/local/provisional_resolution_frame_fallback_h17_real_execution.authorization.json
```

La destination, le marqueur, son `.claimed` et son état de consommation étaient
absents avant et après H21. Le blob du futur runner reste explicitement `null`.

## Artefact H21

```text
configs/provisional_resolution_frame_fallback_h21_zero_science_preflight.json
taille  : 152 080 octets
SHA-256 : acb8ced104ec99afd7f6f966be17b84ce4d436e5582137b6ec6048a90dfe3331
```

Le JSON a été écrit canoniquement en UTF-8/LF, clés triées, séparateurs
déterministes, sans horodatage, via temporaire + `fsync` + `os.replace`.

Vérifications locales après rapatriement binaire :

```text
28 tests H17a/H19a/H20/H21 réussis en 4,189 s
py_compile réussi
git diff --check réussi
```

## Limites et interdictions

H21 n’a interprété aucun contenu scientifique et n’a exécuté aucun modèle,
inférence, décodeur, raison, target, métrique ou bootstrap. La population H18a
reste non consommée. Aucun fit, validation historique, test verrouillé, export
ou live n’est autorisé. H22 et tout runner réel nécessitent une revue externe et
une autorisation séparées.
