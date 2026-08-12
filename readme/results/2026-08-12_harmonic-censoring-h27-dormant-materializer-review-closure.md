# H27 — clôture de revue du loader et materializer dormants

## Verdict externe

Le pilote externe a approuvé le commit
`b3153024ce4a90a2af6aa344e4ddc08d1408637f` après revue du delta, des deux
frontières de capability, des helpers toy et des tests.

La correction fail-closed impose un domaine toy structurellement distinct de
H27 : taille au plus `4096`, fréquence au plus `32000 Hz`, et interdiction des
quatre rôles de production. Les appels avec `16640`, `44100` ou un rôle H27
échouent avant allocation et avant accès à NumPy. Les appels de synthèse et de
publication restent inatteignables : aucune capability ne peut être émise et
le contrôle est inconditionnel même contre `object.__new__`.

## Preuves locales

Les contrôles déjà exécutés sur le worktree isolé sont :

```text
8/8 tests H27 réussis
py_compile réussi
git diff --check réussi
```

Les cinq blobs H27 scellés sont inchangés. Aucun waveform, mask, record, index
de population, authority, claim, receipt, FFT, NNLS, P0/P1/P2, locked-test,
entraînement ou calibration n'a été créé ou exécuté.

## État et limite

Le lot `loader strict + materializer dormant + helpers toy confinés + tests
structurels` est clos. Cette clôture ne donne aucune autorisation de
matérialisation ni de science H27.

La prochaine action reste une décision/contrat séparé pour la phase
engine/recomputer dormante ; elle devra être soumise à revue avant toute
autorité ou exécution réelle.
