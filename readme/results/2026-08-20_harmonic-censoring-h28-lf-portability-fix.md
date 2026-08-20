# H28 — correction de portabilité LF avant CLAIM

Date : `2026-08-20`.

## Résultat

Le premier préflight Mac du runner H28 s'est arrêté avant activation, NumPy,
CLAIM, rendu de payload et calcul scientifique. Les tests ont détecté que
`src/polyphonic/harmonic_censoring_h27_review4_materializer.py` était lié par
H28 à sa représentation CRLF du worktree Windows (`34416` octets), alors que le
blob Git historique et le checkout Mac utilisent LF (`33706` octets).

Ce défaut ne consomme aucune exécution H28 et ne produit aucun résultat
scientifique.

## Correction

- ajout de `text eol=lf` pour le matérialiseur H27 historique ;
- conservation exacte du blob Git historique
  `8cdafbd6a08ea893daa2d6f41cb62166bf9162cd` ;
- liaison H28 aux octets LF portables : taille `33706`, SHA-256
  `2ecaabf1e1880688244b06ecb03a9b3eb7831d4659e209aa11e36b7b60948be3` ;
- rescellement transitif des contrats timing, engine/recomputer,
  materializer, exécution one-shot et binding runner ;
- test de régression explicite interdisant CRLF pour cette dépendance.

Les seuils, Hann, FFT x8, bandes de 35 cents, NNLS, fixtures P01/N01,
horizons N/N+1/N+2, population, targets et verdicts préenregistrés ne changent
pas.

## Validation locale sans science

```text
48 tests réussis
py_compile réussi
git diff --check réussi
```

Aucun locked-test, entraînement, calibration, activation, CLAIM, payload,
population ou calcul H28 n'a été exécuté.

## État d'arrêt

`H28_ONE_SHOT_RUNNER_LF_PORTABLE_PENDING_MAC_RECHECK_NO_ACTIVATION_NO_CLAIM_NO_SCIENCE`

La prochaine action est uniquement de rejouer le préflight Mac au commit exact
de cette correction. L'activation reste absente jusque-là.
