# Correctif sans calcul — scellement du protocole GuitarSet v3

## Anomalie de revue corrigée

La revue du commit `8c92eb08242a5481a72679e1f06d00473016ceea` a confirmé que
les sept actifs scientifiques du protocole étaient vérifiés, mais que le
fichier de protocole lui-même restait substituable par `--protocol`. Un JSON
externe pouvait donc conserver ces sept SHA-256 tout en changeant, par exemple,
la population GuitarSet ou les minima de représentation.

Cette correction ne lance aucun calcul scientifique. Elle ne modifie ni la
Policy A, ni les actifs, ni le checkpoint, ni le décodeur, ni la population
préréglée de 90 prises.

## Contrat fail-closed ajouté

Le schéma `3` est maintenant lié avant toute vérification Git, ouverture
d'actif, import TensorFlow ou replay aux deux valeurs suivantes :

```text
chemin : configs/decoder_candidate_guitarset_expansion_policy_a_v3.json
SHA-256 LF : db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683
```

Un protocole V3 hors de ce chemin échoue avec :

```text
Fail closed: GuitarSet expansion must use the sealed v3 protocol.
```

Le fichier au chemin canonique échoue également si ses octets diffèrent du SHA
préréglé. Le contrôle de chemin couvre la substitution externe ; le contrôle
de digest couvre une modification locale ou une conversion non attendue. Les
schémas historiques `1` et `2` restent parseables et sélectionnables dans leurs
tests de compatibilité, mais ne peuvent pas être pris pour le replay V3 de 90
prises.

## Vérifications sans données projet

Deux tests unitaires supplémentaires construisent un protocole V3 qui conserve
le même purpose et les mêmes sept SHA internes, mais met
`guitarset_poly_mix=13` :

1. un fichier externe est refusé avant `_require_expected_git_commit()` et
   `_require_cpu_tensorflow()` ;
2. le même contenu placé au chemin canonique est refusé pour SHA-256 incorrect,
   également avant Git et TensorFlow.

La vérification locale Windows au commit de ce correctif est :

```text
python -m py_compile src/polyphonic/mine_decoder_candidates.py tests/test_mine_decoder_candidates.py
python -m unittest tests.test_mine_decoder_candidates tests.test_decoder_candidate_snapshot_protocol tests.test_decoder_candidate_provenance tests.test_decoder_candidate_mining tests.test_decoder_candidate_labels tests.test_decoder_candidate_instrumentation tests.test_decoder_candidate_asset_evidence
git diff --check
```

Résultat : `69` tests ciblés réussis en `2,120 s`; `py_compile` et
`git diff --check` réussissent. Les avertissements TensorFlow observés dans la
suite existante ne correspondent à aucune exécution du mineur. Aucun actif
projet, checkpoint réel, inférence, minage, fit, calibration, validation,
export, live ou test verrouillé n'a été ouvert ou exécuté.

## Porte suivante

Faire relire ce seul correctif. Après approbation explicite, et seulement
après synchronisation du commit exact sur un worktree Mac propre, l'unique
replay CPU train-only de 90 prises pourra refaire son préflight complet. Il ne
pourra produire qu'un artefact candidat non autorisant ; toute discussion de
fit restera bloquée jusqu'à l'inspection de son rapport.
