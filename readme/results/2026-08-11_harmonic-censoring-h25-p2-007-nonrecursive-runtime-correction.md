# H25 — correction P2-007 non récursive et vrai runtime secondaire

## Autorité

La correction est limitée aux portées externes :

```text
AUTHORIZED_TO_CORRECT_AND_RESEAL_H25_P2_007_NONRECURSIVE_RECORD_PROJECTION_AND_TRUE_SECONDARY_RUNTIME_IDENTITY_ONLY
AUTHORIZED_TO_PREPARE_AND_BIND_H25_ISOLATED_SECONDARY_SCIENTIFIC_RUNTIME_FOR_P2_007_ONLY
```

Le seal rejeté `e82874c5…` est supprimé avant toute activation. Aucune
capability, claim, population ou phase scientifique n'a été ouverte.

## Projection finie des 27 records

Les records transportés par P2-007 sont désormais :

```text
26 records ordinaires
  evidence exacte du producteur
  + recomputation primary/inverse/final

1 record H25-T-P2-007
  projection H25_P2_007_NONRECURSIVE_SELF_CORE_V1
```

Le `self/core` contient les `36` mesures, leur second replay dans le même
runtime, l'identité scientifique, l'identité transport et les deux IDs
dérivés. Il exclut exactement `current_runtime_observation`,
`cross_runtime_observation` et `test_records`. Le recomputer redérive son
ordre, ses IDs, la parité du replay et ses booléens ; aucun record identité-only
provisoire et aucun `PASS` préfabriqué ne subsiste.

## Runtime scientifique secondaire

Un environnement isolé a été créé sur le Mac, sans appeler l'observer ou le
moteur H25 :

```text
/Users/amcarene/midi-worker/h25-secondary-runtime-cpython39-numpy1264
base       /usr/bin/python3
CPython    3.9.6 arm64
NumPy      1.26.4, wheel binaire, sans dépendance supplémentaire
pip freeze numpy==1.26.4
```

Identité relevée :

```text
Python résolu
/Library/Developer/CommandLineTools/Library/Frameworks/Python3.framework/Versions/3.9/bin/python3.9
size 102352
SHA  5c5950c62eee5fd227a67e4bdfcde81c9add59799bba0949635f3d5ba9661c26

NumPy _multiarray_umath
/Users/amcarene/midi-worker/h25-secondary-runtime-cpython39-numpy1264/lib/python3.9/site-packages/numpy/core/_multiarray_umath.cpython-39-darwin.so
size 3164512
SHA  e870618cf0f8a4b73a928649aba064eee859f8e25a7912344c979f1d03679194

OpenBLAS ILP64
/Users/amcarene/midi-worker/h25-secondary-runtime-cpython39-numpy1264/lib/python3.9/site-packages/numpy/.dylibs/libopenblas64_.0.dylib
size 23198400
SHA  dde2b735d01caa531885115ea853b5a4172b935167b95a1acb2a10243e0d97e7
```

L'identité scientifique contient Python, plateforme, exécutable, NumPy,
multiarray, BLAS et environnement exact. L'identité de transport contient
seulement commande et observer. `runtime_id` est dérivé exclusivement de
l'identité scientifique ; une différence de transport seule ne peut plus
satisfaire P2-007.

## Dormance

```text
seal actif / activation / OS binding   non / non / non
capability / claim                     non / non
observer exécuté                       non
population ouverte                     non
P0 / P1 / P2                           0 / 0 / 0
real data / locked test                non / non
modèle / training / calibration        non / non / non
```

## Nouveau seal

Le correctif a été figé avant le seal au commit :

```text
a638aa990e29950ed693337b13a26ea7e18ee397
authority blob   f016d89b69efbfa27ef2b3f1f6c8a81a131012f5
runner blob      8ebce2f41afbf2f99fe0504533cdd3c7cede7799
engine blob      171602b54a8023e2c85c128aca14ec053da176ad
recomputer blob  662c520b11cdd36f8b1a6f2b10f8b69eb4668511
```

Le nouveau seal lie ce commit, le contrat de capability au SHA
`20a04138eebe1ee786b73178fa074e105ad08d3a516d978a4d87494b8ddbf173`,
la population et la qualification inchangées, ainsi que la commande du venv
CPython 3.9 et le payload observer (`10746` octets, SHA
`5e94fe71426d7db3a4b95467d079a8e4069c9a050f3cac7379d1398e8534e3ef`).

Ce seal attend une revue externe. Il ne constitue ni l'activation Git, ni les
bindings OS nécessaires à l'issuer. Aucune exécution n'est autorisée par le
présent commit seul.

La vérification finale du bloc scellé réussit : `py_compile`,
`git diff --check` et `86` tests H25 autorisés en `1,976 s`. La qualification
real-OS, l'observer secondaire, la population et P0/P1/P2 n'ont pas été
exécutés par cette vérification.
