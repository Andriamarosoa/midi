# H27 Review 5A — exécuteur scientifique dormant

## État

`H27_REVIEW5A_IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_REAL_EXECUTION`

Review 4 reste close au terminal `H27_REVIEW4_TERMINAL_SUCCESS`, avec la
population scellée de 124 records (`17 baseline + 107 P2`). Ce lot implémente
la frontière scientifique suivante sans l'activer.

## Implémentation

- contrat exact de Review 5 : 27 tests ordonnés, 9 par phase, premier échec
  terminal et aucun retry ;
- capability process-local non constructible par l'API nominale, émise au
  maximum une fois après un claim durable et liée au SHA de l'index ;
- loader fail-closed : index SHA, schéma, ordre des 124 identités, topologie,
  chemins réguliers non symlinkés et bindings attestés avant lecture payload ;
- moteur et recomputer indépendants exécutés et comparés pour chaque record ;
- `P2-007` lance le CPython secondaire scellé seulement lorsque son tour est
  atteint, vérifie Python/NumPy/OpenBLAS et rapproche quatre résultats
  secondaires des quatre résultats primaires ;
- runner macOS one-shot : contrôles Git/runtime/blobs/index avant claim,
  outputs nouveaux seulement, écritures atomiques `O_EXCL + fsync + replace`,
  terminal inconclusif sur toute erreur opérationnelle après consommation ;
- terminal de réussite préenregistré :
  `H27_REVIEW5_SCIENCE_27_OF_27_PASS_STOP_BEFORE_POST_SCIENCE` ;
- contrat post-science distinct, encore design-only, qui interdit entraînement,
  génération/sélection de checkpoint, calibration et locked-test.

## Validation locale non scientifique

Commande ciblée :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest \
  tests.test_harmonic_censoring_h27_review5_scientific_execution \
  tests.test_harmonic_censoring_h27_engine_recomputer_dormant \
  tests.test_harmonic_censoring_h27_materializer_dormant
```

Résultat vérifié après binding et seal : `28 tests`, succès. Les tests utilisent uniquement des
bindings temporaires et des résultats synthétiques ; aucune waveform H27 réelle
n'est lue. `py_compile` et `git diff --check` passent également.

## Autorisations

```text
real_execution=false
scientific_authority=false
scientific_claim=false
P0/P1/P2=false
locked_test=false
training=false
calibration=false
checkpoint_selection=false
```

Une revue externe du code complet, de son identity binding et de son seal est
obligatoire avant de créer une activation ou de toucher au payload Mac.

Chaîne soumise : implémentation `189e4e7499a6a1a719f152365bfc792f4d1fa4ac`,
identity binding `0c0af9d98dbca919592f845391cba57af9fcd14a`, puis seal externe.
