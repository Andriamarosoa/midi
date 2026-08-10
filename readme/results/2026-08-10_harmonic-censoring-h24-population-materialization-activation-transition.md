# H24 — transition d'activation du matérialiseur de population

## Portée

Ce commit applique uniquement l'autorisation externe
`AUTHORIZED_TO_CREATE_H24_POPULATION_MATERIALIZATION_ACTIVATION_COMMIT_ONLY`.
Il rafraîchit le seal et le contrat d'activation afin de les lier au bridge
NumPy dormant déjà revu. Il ne confère aucune autorité d'exécution.

## Liaison exacte revue

- commit matérialiseur : `c51d8eaf7dbb8370456d92f9a76ec3f336d98016` ;
- blob source matérialiseur : `1f76391592ab0f4725147504bcb059f0c3d89e50` ;
- contrat de matérialisation SHA-256 :
  `b48aa4f417a9857983c79809efe24137d6b82ad0984d20e906286477f05a14ca` ;
- seal rafraîchi SHA-256 :
  `a4f8e48efacdadb57c75e9ac2db7d66673cd98d5672d7626dfaa28c5828d2b81` ;
- contrat d'activation rafraîchi SHA-256 :
  `3c40e7d001f1bfecd48bd20999e35476a96d083ab9db12d86873d9bdcf4d1b6b`.

Le seal reproduit exactement la topologie des quatre fichiers du commit
matérialiseur revu. Le commit d'activation est distinct et ne s'auto-référence
pas : son SHA devra être injecté depuis l'OS uniquement après revue externe.

## Topologie fermée du commit d'activation

Le contrat exige exactement les six fichiers suivants :

1. `configs/harmonic_censoring_h24_population_materialization_activation_contract.json`
2. `configs/harmonic_censoring_h24_population_materialization_authorization_seal.json`
3. `readme/README.md`
4. `readme/results/2026-08-10_harmonic-censoring-h24-population-materialization-activation-transition.md`
5. `tests/test_harmonic_censoring_h24_population_materialization_activation_contract.py`
6. `tests/test_harmonic_censoring_h24_population_materializer_dormant.py`

## Dormance maintenue

Le statut est
`activation_commit_created_pending_external_review_no_runtime_authority`.
Pendant cette transition :

- aucune variable OS d'autorisation n'est définie ;
- aucune capability opérationnelle n'est émise ;
- aucun claim ni marker n'est créé ;
- NumPy réel n'est pas importé ;
- aucun waveform ni population n'est matérialisé ;
- P0, P1, P2, H17, données réelles, entraînement et locked-test restent
  interdits.

La séquence restante est : revue externe du commit exact et du seal, puis
autorisation séparée d'injecter le binding OS exact, puis seulement le
préflight zéro-science et l'unique claim durable. La matérialisation future
devra encore s'arrêter avant P0/P1/P2 pour une nouvelle revue.

## Vérification locale

La suite ciblée H24/H23/H20 réussit avec `171` tests en `2,362 s`.
`py_compile` et `git diff --check` réussissent également. Cette transition ne
produit aucune mesure scientifique.
