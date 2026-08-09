# Correctif de préflight du mineur borné — sans calcul réel

## Contexte et décision

La revue externe de `0e124352f52637d3a895b615c771ee14b0de09e5` a refusé le
premier replay Mac et a relevé deux bloqueurs concrets. Aucun minage, ouverture
d'actif Policy A, inférence, entraînement, validation, export, live ni test
verrouillé n'a été lancé pendant ce correctif.

## Correctifs appliqués

1. `--expected-git-commit` n'est plus validé par le validateur SHA-256. Le
   nouveau validateur exige exactement un SHA Git complet minuscule de 40
   caractères (`[0-9a-f]{40}`), puis compare `git rev-parse HEAD` et exige un
   worktree sans modification indexée, non indexée ou non suivie.
2. `src.polyphonic.mine_decoder_candidates` ne charge plus `data.py`, le
   contexte de minage, `PolyphonicSequence` ou Keras à l'import du CLI. Les
   annotations sont sous `TYPE_CHECKING`; les imports runtime restent derrière
   le préflight pur.
3. L'ordre effectif est désormais : protocole fermé, commit Git propre,
   destination, sept SHA-256, lien YAML-manifeste, `MIDI_FORCE_CPU=1` et
   visibilité GPU vide, puis seulement contexte scellé/données et modèle.
   Ainsi aucune empreinte incorrecte ne peut initialiser TensorFlow.

## Vérification locale sans données projet

La commande suivante a réussi sur Windows :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest `
  tests.test_mine_decoder_candidates `
  tests.test_decoder_candidate_labels `
  tests.test_decoder_candidate_mining `
  tests.test_decoder_candidate_snapshot_protocol `
  tests.test_decoder_candidate_asset_evidence
```

Résultat : **41 tests réussis en 2,025 s**. `py_compile` pour le CLI et son
test, puis `git diff --check`, réussissent aussi.

Le nouveau test de préflight crée un dépôt Git temporaire propre et des seuls
fichiers synthétiques. Après avoir scellé le SHA du checkpoint, il le remplace,
exécute le chemin réel `run_bounded_train_only_mining()` dans un sous-processus
Python vierge, puis vérifie les deux propriétés : l'erreur porte bien sur
`checkpoint_sha256` et `tensorflow` est absent de `sys.modules` avant comme
après l'échec. Un second test appelle la véritable validation Git avec le SHA
historique réel à 40 caractères `0e124352f52637d3a895b615c771ee14b0de09e5`;
seules les commandes Git sont simulées, pas la fonction testée.

Les autres tests de la suite ciblée peuvent importer TensorFlow pour leurs
fixtures synthétiques historiques. Cette activité de test ne constitue ni une
inférence, ni un replay, ni une ouverture des actifs/checkpoints réels Policy
A; la preuve de l'absence de TensorFlow au préflight est celle du sous-processus
isolé ci-dessus.

## Limites et porte suivante

Le commit ne modifie ni la population Policy A (12 prises canoniques prévues),
ni les sept empreintes, ni la logique de décodage/labels, ni les sorties
atomiques non autorisantes. `fit_authorized=false` et
`locked_test_used=false` restent obligatoires. Le mineur corrigé exige encore
une revue externe avant toute synchronisation Mac ou unique replay train-only.
