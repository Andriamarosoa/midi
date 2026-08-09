# Runner V1 du fit causal — implémentation sans exécution

## Autorisation et périmètre

La revue de `76ebf937` autorise uniquement l'implémentation du runner V1 et
des tests synthétiques associés. Elle interdit toujours tout job Mac, fit réel,
calibration réelle, validation historique, export, live et test verrouillé.

Cette étape ajoute `src/polyphonic/run_causal_candidate_fit.py` et
`tests/test_run_causal_candidate_fit.py`. Aucun artefact V3 réel, checkpoint,
WAV, label ou modèle entraîné n'a été lu. Le seul TensorFlow observé par les
tests sert à construire la tête vide de l'ancien test d'architecture ; aucun
appel au runner ni à `Model.fit` n'a été effectué.

## Exécution future rendue fail-closed

`run_v1_fit()` n'accepte aucun argument permettant de modifier les poids,
l'optimiseur, les époques, la calibration ou les données. Il exige :

- l'accusé explicite `DECODER_CANDIDATE_FIT_EXECUTE=1` ;
- un worktree Git propre au commit exact fourni ;
- le préflight V3 déjà scellé (lignes candidates, rapport et protocole V3) ;
- `MIDI_FORCE_CPU=1` avant le premier import TensorFlow ;
- une destination et un répertoire partiel inexistants ;
- la spécification immuable `V1_EXECUTION_SPEC` : seed `47`, batch `64`,
  Adam `0,01`, maximum 40 époques, patience 5, `min_delta=1e-4`,
  `shuffle=false` et budget de 15 minutes.

Les vecteurs sont toujours obtenus depuis les lignes canoniques V3. Les poids
sont recalculés localement dans le runner pour `fit`, `dev` et `calibration` ;
aucun paramètre externe ne peut leur substituer une autre pondération.

## Séparation fit/dev/calibration

`model.fit` recevra exclusivement `fit.features`, `fit.targets` et
`fit.weights`. Aucun `validation_data` n'est passé à Keras. Un callback V1
évalue ensuite le modèle sur `dev` avec `training=False`, calcule la BCE
pondérée explicitement hors Keras et restaure les meilleurs poids en mémoire.
Le terme L2 agit sur l'apprentissage fit, jamais sur la métrique qui choisit
l'époque.

La calibration n'est atteignable qu'après `dev_signal.passed`. Elle est alors
une inférence train-only sur la partition calibration et ne peut participer ni
aux gradients, ni au choix d'époque. Si dev échoue, le rapport porte
`failed_dev_gate` et la calibration est absente.

## Artefacts futurs et parité

Après un futur fit autorisé, le runner écrira atomiquement :

- `causal_candidate_fit_v1.keras` ;
- `fit_standardizer.json`, avec les huit features, les 12 dimensions encodées,
  les moyennes/écarts-types fit-only, le SHA du modèle et le SHA des candidats ;
- `fit_report.json`, avec provenance V3, spec, comptes, historique BCE dev,
  verdict dev, grille calibration, SHA et erreur de parité sauvegarde/rechargement.

Le runner refuse tout écrasement. Il vérifie la parité de probabilités après
sauvegarde/rechargement avant de publier le répertoire final. Un dépassement du
budget de 15 minutes échoue sans publication d'artefact.

## Vérifications synthétiques

Commande locale exécutée :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m py_compile `
  src\polyphonic\causal_candidate_fit.py `
  src\polyphonic\run_causal_candidate_fit.py `
  tests\test_causal_candidate_fit.py `
  tests\test_run_causal_candidate_fit.py
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest `
  tests.test_run_causal_candidate_fit `
  tests.test_causal_candidate_fit `
  tests.test_decoder_candidate_mining `
  tests.test_decoder_candidate_labels `
  tests.test_mine_decoder_candidates
```

Résultat : **47 tests réussis en 5,388 s**. Les nouveaux tests couvrent la
reconstruction locale des poids, la persistance du standardiseur, le refus
avant tout accès sans accusé d'exécution, l'absence d'arguments de contournement
et l'évaluation dev en inférence avec restauration des meilleurs poids. Un
sous-processus neuf confirme aussi que `MIDI_FORCE_CPU=1` masque bien tout GPU
logique TensorFlow avant le modèle, y compris le GPU Metal du futur Mac.

## Porte suivante

Une nouvelle revue externe doit examiner ce runner. Elle devra notamment
confirmer qu'il n'existe aucun contournement de `V1_EXECUTION_SPEC`, qu'aucune
donnée dev/calibration n'entre dans les gradients et que la persistance du
standardiseur lie correctement les probabilités futures au modèle. Aucun fit
ne découle automatiquement de cette implémentation.
