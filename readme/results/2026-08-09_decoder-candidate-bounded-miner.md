# Mineur borné de candidats du décodeur — préparation sans calcul réel

## Statut

Implémentation prête à relire, mais **aucun minage réel n'a été lancé par ce
commit**. La revue de `8143f016…` autorise un unique minage train-only borné à
partir du plan Policy A et du registre d'actifs Mac. Cette implémentation rend
la future exécution reproductible et fail-closed ; la revue du code reste
requise avant de lancer le job Mac.

## Population strictement bornée

`configs/decoder_candidate_bounded_mining_v1.json` fige :

- manifeste SHA-256 `b28cb17…f1b8ed7` ; plan Policy A v2 `a8347e4e…893685f4` ;
  registre d'actifs `12dd74f2…e586507` ;
- checkpoint de transcription de base `1ce8ac44…1a411325`, YAML modèle,
  décodeur à porte nulle et politique audio, chacun verrouillé par SHA-256 ;
- une prise canonique par corpus (GAPS, Guitar-TECHS DI, Guitar-TECHS mic,
  GuitarSet) et par partition `fit/dev/calibration`, soit 12 prises ;
- maximum de `65 536` tentatives par prise : un dépassement invalide le lot.

Les 31 prises GAPS exclues par Policy A restent inaccessibles. Le CLI ne
possède aucun argument de split, seuil, recherche, GPU ou maximum de prises.

## Garde-fous avant le calcul futur

`src.polyphonic.mine_decoder_candidates` refuse, avant TensorFlow : commit Git
différent ou sale, les sept empreintes incorrectes, un manifeste différent du
YAML, une porte `independent_note` active, un registre/plan non revalidé et une
GPU visible. Chaque prise passe par le contexte scellé qui re-hache labels et
audio à leurs frontières de chargement. La cible reste le matcher causal sur
tous les NoteOn valides du flux réel, retriggers inclus, puis est projetée vers
les seuls NoteOn `gate_eligible` et émis.

La sortie, obligatoirement nouvelle sous `data/processed`, est écrite dans un
répertoire partiel puis renommée après succès. Elle contient seulement
`candidate_events.jsonl` et `mining_report.json` : SHA du JSONL, provenance,
compteurs par prise, globaux et par partition. Le rapport marque toujours
`fit_authorized=false`; il n'autorise aucun fit, calibration, validation,
sélection de seuil, export, live ou test verrouillé.

## Vérification sans données projet

La commande Windows suivante a réussi :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest `
  tests.test_mine_decoder_candidates `
  tests.test_decoder_candidate_labels `
  tests.test_decoder_candidate_mining `
  tests.test_decoder_candidate_snapshot_protocol `
  tests.test_decoder_candidate_asset_evidence
```

Résultat : **39 tests réussis en 0,956 s**. Ils couvrent le schéma fermé,
`locked_test_used=false`, la sélection fixe de 12 prises, le refus d'un
checkpoint substitué avant TensorFlow/modèle, l'unique construction du modèle
et l'écriture d'un artefact explicitement non autorisant. `py_compile` et
`git diff --check` passent. Aucun WAV, label projet, checkpoint réel,
inférence ou collecte n'a été exécuté.

La suite générale a ensuite réussi : **458 tests en 38,309 s**, dont trois
tests explicitement ignorés. Ses petites époques Keras appartiennent aux
fixtures synthétiques historiques de la suite de tests ; elles n'ont chargé ni
donnée, ni checkpoint, ni artefact du minage Policy A.

## Porte suivante

Faire relire ce commit. Après approbation seulement, synchroniser exactement
le commit revu sur le Mac puis exécuter une unique passe CPU avec le commit
fourni à `--expected-git-commit`, les trois artefacts préinscrits et le
checkpoint
`/Users/amcarene/midi-worker/checkpoints/1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325.keras`.
La suite s'arrête après inspection humaine du rapport de minage.
