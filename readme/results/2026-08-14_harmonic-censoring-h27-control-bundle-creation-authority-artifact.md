# H27 - artefact administratif d'autorite de creation du bundle

La revue externe de `7ee0a8977208bfa389e284b07207abc40a3517fd`
conclut `PASS`. Ce lot cree uniquement l'artefact administratif distinct et son
seal, tous deux non consommes. Le HEAD d'execution est fixe explicitement au
commit PASS `7ee0a8977208bfa389e284b07207abc40a3517fd`.

L'artefact respecte les huit champs exacts ; son identifiant
`4e1072559ff1ef5ec1e2fb0e4ec72b3baca2d98811fabfb568e9380951129c76`
est recalcule depuis les sept champs canoniques. `single_use=true` et
`consumed=false`.

Aucun bundle, observation, filesystem, registre, reservation, consommation,
invocation, destination, population ou science n'est ouvert.

Identites exactes :

- artefact : `9f8ebc7c89502dfab04b724d8da173e647758365` / `920` octets /
  `da2718b4349a6d51af1c5b1c1a1f86346d8f80e9b419283d58af21f8270b78d1` ;
- seal : `167e772f720cf6cd1bd4a7dca390c58d863711a5` / `2003` octets /
  `40d742e38cca7a55a2ee39769ceaf71e9d73ab6f22d25e3abd9ce9590829cf86`.

Validation locale sans calcul scientifique : test cible `3/3`, suite H27
`409/409`, puis `git diff --check` propre avant commit.
