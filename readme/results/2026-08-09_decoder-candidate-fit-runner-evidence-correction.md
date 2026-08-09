# Correctif d'observabilite du runner de fit causal V1

## Portee

Cette correction repond a la revue de `5de7f7ef`. Elle ne lance aucun fit
reel, n'ouvre aucun artefact V3, WAV, label, checkpoint ou split du projet,
et ne cree aucun modele ou rapport scientifique. Elle modifie seulement le
runner futur et ses tests synthetiques.

## Corrections avant le fit unique

Le runner materialise maintenant explicitement l'unique entree Keras avant
`Model.fit` : la matrice de features est un `numpy.ndarray` `float32` de forme
`(candidats, 12)` et les cibles/poids sont des vecteurs `float32`. Les formes,
valeurs finies et dimensions sont verifiees avant l'appel Keras. Le chemin du
fit ne depend donc plus de l'interpretation par Keras de tuples Python imbriques.

Le futur `fit_report.json` conservera, avant publication atomique :

- `training_history` par epoque : `epoch`, `keras_fit_loss`,
  `dev_weighted_bce`, `dev_weighted_brier` et `dev_auc_by_family` ;
- `weight_evidence` par `partition x family x target`, avec le nombre de
  groupes et de lignes, la somme et le minimum/maximum des poids, plus la
  decomposition par `leakage_group_key` ;
- `inference_cost` mesure apres restauration des meilleurs poids sur toutes les
  lignes train-only du run : nombre de candidats, secondes ecoulees et
  microsecondes par candidat.

Le choix d'epoque reste exclusivement fonde sur la BCE dev hors L2. Ces
nouvelles observations ne modifient ni le modele, ni les gradients, ni la
calibration. Si un fit futur termine avec `calibration.threshold=null`, son
statut `complete_non_authorizing` devra etre interprete comme un resultat
negatif de seuil, et jamais comme une promotion.

## Preuve synthetique du vrai chemin Keras

Un nouveau test execute effectivement une epoque Keras sur six lignes fit
synthetiques, sans chemin d'artefact V3. Il traverse la meme fonction interne
que le runner, verifie les tableaux `float32`, le callback dev en inference,
la perte fit et le schema de preuves du rapport. Il ne lance ni preflight V3,
ni minage, ni fit sur donnees projet.

Commande locale executee :

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

Resultat : **48 tests reussis en 5,921 s**. Le test Keras affiche une epoque
synthetique et aucune donnee projet n'est lue. `locked_test_used=false` par
portee : aucun chemin test verrouille, validation officielle, export ou live
n'est execute.

## Contrainte du futur lancement autorisable

Apres revue externe explicite de ce correctif, l'unique fit reel ne devra pas
etre lance directement avec `python -m src.polyphonic.run_causal_candidate_fit`.
Il devra passer exclusivement par le worker lourd Mac partage,
`scripts/remote/mac_worker.sh start`, avec `device=cpu` et une limite murale
externe de **900 secondes**. Le verrou atomique `active.lock` du worker garantit
alors un seul job lourd; `MIDI_FORCE_CPU=1` est defini par ce worker avant le
premier import TensorFlow. Aucun fit ne decoule automatiquement de ce commit.

## Suite

Revue externe de ce correctif uniquement. Sans approbation, aucun fit,
calibration, validation historique, export, live ou test verrouille ne doit
etre lance.
