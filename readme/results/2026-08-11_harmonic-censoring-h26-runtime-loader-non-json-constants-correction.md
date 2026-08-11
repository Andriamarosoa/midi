# H26 - rejet des constantes numeriques non-JSON dans le loader runtime

Le pilote a approuve R3 et R4, puis rejete R5 avec le verdict
`REJECTED_H26_R5_CORRECTED_ORCHESTRATION_SEAL_LOADER_NON_STRICT_JSON_CONSTANTS`.

R9 `f208eba5fb054cff90ea3f1c5aca69f30d789cd4` ajoute uniquement un
`parse_constant` fail-closed. `NaN`, `Infinity` et `-Infinity` levent desormais
`ValueError`, avec un test explicite pour chaque constante. Les bindings, le
seal, R3/R4, le deep-freeze et la dormance sont inchanges.

Le blob loader R5
`28b32bc0981c8d0c92ed9d0c911982482eee8d76` reste historique. Le blob loader
effectif R9 est `8f8f603b2330b5684aa1c64cc50d41ccacf2eaba`.

Aucun runtime, observateur reel, filesystem runtime, science ou locked-test n'a
ete utilise.
