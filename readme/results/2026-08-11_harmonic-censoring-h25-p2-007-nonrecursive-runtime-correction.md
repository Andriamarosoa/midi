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

La prochaine opération interne est de commiter ce bloc d'implémentation, puis
de produire un nouveau seal lié aux blobs de ce commit. Les deux commits seront
soumis ensemble à la revue externe avant toute activation.
