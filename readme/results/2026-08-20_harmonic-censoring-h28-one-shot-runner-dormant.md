# H28 — runner one-shot dormant et lié

## Résultat

Le runner de la future observation H28 est implémenté mais ne possède aucune
activation. Son import n'importe ni NumPy ni TensorFlow, ne crée aucun fichier
et n'émet aucune capability. Une invocation sans l'unique JSON d'activation
externe exact échoue avant tout accès scientifique.

## Frontière pré-CLAIM

Avant NumPy et avant toute création, le runner impose :

- contrat d'exécution au SHA-256
  `286179fd68cf93b0c35ac6e8a54632772ada863a6c6041cac6738298461a9dd7` ;
- trois contrats fixes et toutes leurs liaisons transitives size/SHA/Git blob ;
- activation stricte placée sous `tmp/local`, non suivie et non symlinkée ;
- `HEAD` exactement égal au commit activé et worktree propre ;
- output, staging, claim, failure et terminal tous absents ;
- Darwin arm64, CPython `3.11.9`, NumPy `1.26.4` ;
- environnement CPU/thread/locale exact et aucun TensorFlow importé.

NumPy est importé seulement après ces contrôles. Le CLAIM créé avec `O_EXCL`,
fsync et mode read-only consomme alors définitivement l'unique essai.

## Chemin post-CLAIM

Le runner active des gardes process-local, matérialise les six records en
mémoire, écrit une population staging scellée, puis pour chaque identité dans
l'ordre préenregistré exécute :

```text
moteur H28
→ recomputer indépendant H28
→ comparaison complète
→ sérialisation diagnostique fermée
```

Le verdict terminal est dérivé uniquement des six outcomes. `diagnostics.json`,
`report.json`, `COMPLETE.json`, l'index et les payloads sont fsync avant une
publication Darwin `renameatx_np(..., RENAME_EXCL)`. Toute exception après le
CLAIM écrit une preuve `FAILED_AFTER_CLAIM_NO_RETRY`, conserve le staging et
interdit nettoyage automatique ou seconde invocation.

## Validation

Les suites H28 et la régression H27 totalisent `47/47` tests réussis, plus
`py_compile` et `git diff --check`. Les tests vérifient notamment l'ordre
préflight→NumPy→CLAIM→science→publication, les contrats byte-exacts, l'absence
de retry, de `os.replace`, de locked-test et l'arrêt sans activation avant
NumPy/claim.

Aucun runtime Mac, activation, claim, payload, FFT, NNLS ou résultat scientifique
H28 n'a été utilisé.

Binding dormant du runner :

```text
configs/harmonic_censoring_h28_one_shot_runner_dormant_binding.json
SHA-256 51277979d1f97cf8e545941fd0cafa2b924136de3c0f8b1e6401a628b206b617
```

## Latence et suite

Le runner ne touche pas le produit live. Son futur temps CPU devra être mesuré
par record dans le rapport; aucune extrapolation n'est faite avant le préflight
Mac. La prochaine action est un contrôle Mac read-only du runtime, des chemins,
du worktree et de l'absence de destination/claim. La création de l'activation
reste une décision distincte et précède l'unique consommation.
