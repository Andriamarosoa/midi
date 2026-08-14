# H27 - contrat du gate one-shot du constructeur

La revue externe de `5a0b8d3d3f301ed4357bd1853af778bd6794f406`
conclut `PASS`. Ce lot definit uniquement le contrat declaratif et le seal
externe du futur gate one-shot qui pourra consommer l'artefact d'autorite et
invoquer le constructeur deja scelle.

La chaine lie artefact, seal, binding, binding seal et 112 identites amont,
soit 116 chemins uniques a rehasher. L'ordre futur est ferme : artefact exact,
HEAD attendu, worktree propre, rehash116, registre, reservation, consommation
atomique, puis invocation unique. `single_use=true` et `consumed=false` restent
inchanges dans ce lot.

Aucun registre n'est ouvert, aucune identite/nonce n'est reservee, aucune
autorite n'est consommee et aucune invocation, destination, ecriture filesystem,
population ou science n'a lieu.

Contrat exact : blob `5a1aed6aabe7febec24edfd576bff662549853b2`,
`4942` octets, SHA-256
`1f212478270765cd6abee687fadd94b9f1fcf0eaa417db39bbf6984342a1598b`.
Seal exact : blob `d7a5b9c52f1f7932157cf73e38cee10910518491`, `1438`
octets, SHA-256
`5748b0de70d8cce98dba3b197fb069d3112bfe405786f45bea3e6fdfc237e088`.

Validation locale : `3/3` tests administratifs cibles, `391/391` tests H27 et
`git diff --check` sans anomalie.
