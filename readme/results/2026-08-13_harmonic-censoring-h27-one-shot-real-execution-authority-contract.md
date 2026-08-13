# H27 - contrat de la future autorite d'execution reelle one-shot

La revue externe de `b29d90a18461cd05ed003ab4cab53f7f49e04c1b`
conclut `PASS` sur l'identity binding du contrat d'autorisation d'issuance.
Cette etape ajoute uniquement le contrat declaratif et le seal externe de la
future autorite d'execution reelle one-shot.

Le contrat lie les quatre identites PASS/scellees de l'autorisation d'issuance
et leurs 84 identites amont, soit 88 chemins uniques a rehasher avant toute
future consommation. Il impose une autorite strictement single-use et l'ordre
futur `rehash 88 -> consume -> observe absence -> create-exclusive`. Le succes
ou tout echec apres consommation est terminal et tout retry est interdit.

Aucune instance d'autorite n'est creee, accordee ou consommee. Aucun issuer
n'est invoque; aucune destination n'est observee et aucune operation filesystem,
materializer, population ou science n'est autorisee. Les huit edges historiques
restent fermes. `locked_test_used=false`; entrainement et calibration restent
interdits.

Le contrat, son seal, le test administratif, le README et ce rapport doivent
etre revus avant toute etape ulterieure distincte.

Identites avant commit : contrat blob
`40757fa14d3df8b2aca2e12924faf7be329b9687`, `5300` octets, SHA-256
`c23b4ceaf67dba8dc9d16ab7b279906823ae1b1259ba07aa8e8e2a2bf23210bb` ;
seal blob `3d644e8eb2bc0ca8c71cb7c9d7302feb1c1c28c2`, `1484` octets,
SHA-256
`ef3d3c4bf4d54a5b64b2a928c3fb36d79c9c52956c24844f43a83e307d4efc83`.

Validation locale : `3/3` tests administratifs, `343/343` tests H27,
`py_compile` et `git diff --check` passent.
