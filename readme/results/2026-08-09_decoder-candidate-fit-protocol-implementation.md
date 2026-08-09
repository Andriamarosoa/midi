# Implémentation V1 du protocole de fit causal — sans exécution

## Décision et périmètre

La revue externe du commit `e90321a1` autorisait uniquement l'implémentation
du protocole de fit V1, ses gardes et ses tests synthétiques. Cette étape
implémente ce contrat dans `src/polyphonic/causal_candidate_fit.py` et ajoute
ses tests dans `tests/test_causal_candidate_fit.py`.

Elle n'exécute **aucun fit** : aucune ligne candidate V3 réelle, aucun
checkpoint réel, aucune calibration, validation historique, export, live ou
test verrouillé n'a été chargé. Le test d'architecture construit seulement une
tête vide sur des données synthétiques ; le test de parité emploie un faux
modèle en mémoire et un fichier temporaire, sans poids entraîné.

## Contrat codé

Le préflight futur lit les octets de `candidate_events.jsonl`,
`mining_report.json` et du protocole V3 une seule fois, les hache avant parsing
et refuse toute divergence avec les SHA V3 préenregistrés. Il vérifie aussi :

- le rapport terminal `complete_non_authorizing` ;
- `locked_test_used=false` et `fit_authorized=false` ;
- le commit de minage, le but V3, les sept SHA scientifiques et les comptes
  `fit/dev/calibration` de la population V3 ;
- les partitions train-only, l'unicité globale des `event_id` et la provenance
  complète de chaque ligne.

La projection est verrouillée sur les huit `CAUSAL_FEATURES` pré-porte : cinq
valeurs numériques (dont `log1p(active_polyphony)`), deux booléens et le
one-hot de cinq raisons, soit exactement 12 dimensions. Elle refuse la cible,
le pitch, la frame, la provenance, toute information post-porte et le futur.

Les statistiques de normalisation proviennent exclusivement de `fit`. Les
poids sont recalculés dans chaque partition selon
`N_partition / (6 × groupes_cellule × lignes_du_groupe)`. Ainsi `dev` et
`calibration` n'emploient jamais `N_fit`.

La métrique qui devra choisir l'époque est la BCE pondérée dev écrite
explicitement dans le module. Elle ne réutilise pas `model.val_loss` et ne
contient donc pas le terme L2. Le signal dev et la grille fixe de calibration
restent des fonctions séparées ; aucune fonction ne les exécute automatiquement.

## Reproductibilité et sortie future

`CandidateFitExecutionSpec` fige seed `47`, batch `64`, Adam `0,01`, 40
époques maximum, patience `5`, `min_delta=1e-4` et `shuffle=false`. L'ordre
des lignes est canonique avant partition ; `configure_deterministic_cpu_tensorflow`
exige `MIDI_FORCE_CPU=1`, refuse TensorFlow déjà importé ou tout GPU exposé,
fixe les graines Python/NumPy/TensorFlow et active les opérations déterministes.

La tête reste volontairement minimale : `Dense(1, sigmoid)` avec
`GlorotUniform(seed=47)` et L2=`1e-3`. Elle est construite non compilée et le
module ne contient ni CLI ni appel à `Model.fit`.

`verify_saved_model_parity` est préparé pour le futur runner revu : il refuse
d'écraser un `.keras`, compare les prédictions avant/après sauvegarde-rechargement
et échoue au-delà de sa tolérance. Cette fonction n'a pas été appelée sur un
modèle ou un artefact réel dans cette étape.

## Vérifications locales synthétiques

Commande exécutée depuis le worktree :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m py_compile `
  src\polyphonic\causal_candidate_fit.py tests\test_causal_candidate_fit.py
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest `
  tests.test_causal_candidate_fit tests.test_decoder_candidate_mining `
  tests.test_decoder_candidate_labels tests.test_mine_decoder_candidates
```

Résultat : **42 tests réussis en 2,015 s**. Ils couvrent notamment la dimension
12, le standardiseur fit-only, l'équilibrage groupe/famille, les poids locaux
dev/calibration, les six cellules obligatoires, les SHA et le protocole scellé,
le refus de lignes non train-only, le budget déterministe et la parité de
sauvegarde/rechargement synthétique. `py_compile` et `git diff --check` ont
également été exécutés. Une recherche statique confirme qu'il n'existe aucun
appel `fit(` dans le nouveau module.

## Limites et prochaine porte

Cette implémentation ne prouve aucune amélioration MIDI. Le décalage de
distribution connu entre les NoteOn réellement émis ayant fourni les labels et
les candidats qui seront vus par une future porte demeure à mesurer dans une
validation A/B ultérieure, jamais déduite du fit interne.

La seule prochaine action est une **nouvelle revue externe du code**. Même une
approbation ne déclenche pas automatiquement de fit : l'autorisation et la
commande d'un unique fit CPU train-only devront être données séparément. Le
test verrouillé demeure fermé.
