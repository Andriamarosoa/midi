# H27 Review 4 — arrêt préclaim au chargement du contrat figé

## Autorisation et inspection runtime

La revue externe de `7ac1be49b43d269234d56c74f53c6cff1f1197e1` a rendu
`PASS — reprise autorisée, sans modifier le runtime scellé`. Un bloc SSH unique
a commencé par une inspection strictement read-only via :

```text
/Users/amcarene/midi-worker/.venv/bin/python
```

Sans importer NumPy, l'inspection a confirmé :

```text
H27_REVIEW4_READ_ONLY_RUNTIME_AND_BOUNDARY_INSPECTION_PASS
RESOLVED_EXECUTABLE /Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11
NUMPY_DISTRIBUTION 1.26.4
NUMPY_MULTIARRAY /Users/amcarene/midi-worker/.venv/lib/python3.11/site-packages/numpy/core/_multiarray_umath.cpython-311-darwin.so
OPENBLAS /Users/amcarene/midi-worker/.venv/lib/python3.11/site-packages/numpy/.dylibs/libopenblas64_.0.dylib
```

Elle a aussi revalidé les six fichiers bootstrap, les quatre répertoires admin
en `0700` et l'absence des cinq destinations one-shot.

## Arrêt du runner

Après cette réussite et l'ACK, le runner scellé a été invoqué exactement une
fois avec le même executable de venv et l'environnement exact. Il a terminé
`rc=1` dans `preclaim()` lors de l'exécution du contrat figé :

```text
File "src/polyphonic/harmonic_censoring_h27_contract.py", line 97, in <module>
    @dataclass(frozen=True)
File "dataclasses.py", line 712, in _is_type
    ns = sys.modules.get(cls.__module__).__dict__
AttributeError: 'NoneType' object has no attribute '__dict__'
LOCAL_SSH_RC=1
```

La cause immédiate est que `frozen_module()` construit un `ModuleType` puis
exécute ses octets sans inscrire temporairement ce module dans `sys.modules`.
Le décorateur standard `dataclass` consulte cette entrée pendant la définition
de classe.

## Frontière

L'exception intervient dans `preclaim()` avant son retour vers
`consume_and_run()`. Aucun fichier AUTHORITY ou CLAIM, capability consommée,
chargement de plan, import NumPy scientifique, staging, population, terminal,
P0/P1/P2, entraînement ou locked-test n'a eu lieu.

Les six artefacts et les parents administratifs restent intacts. Aucun retry,
remplacement ou réparation n'est effectué. Une nouvelle revue doit décider du
correctif du runner et de son nouveau binding/seal avant toute invocation.
