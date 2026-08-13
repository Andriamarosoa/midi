# H27 - binding du contrat d'autorisation d'invocation du constructor

La revue externe de `8382475d7a0d7bfb5e5ccb7f75dd3f874afd6cea`
conclut `PASS`. Ce lot ajoute uniquement l'identity binding administratif du
contrat corrige et son seal. Contrat + seal + 104 predecesseurs forment 106
chemins uniques rehashes.

L'exigence d'un futur `expected_git_head` exact, lie par un artefact distinct
revu/scelle, et l'ordre fail-closed sont preserves. Aucun artefact runtime,
HEAD concret, registre, reservation ou invocation n'existe; huit edges fermes.

Identites exactes : binding blob
`59f774870b82ea5366648aa658e3d3e0279a33f5`, `2921` octets, SHA-256
`4bd6b3738482e2f5bd19e6bd2fbfc1bceb0008980de7481bad4b3eee5c2b51b8` ;
seal blob `73d4a277178899d6c0f44c24bf565d7bfca929c7`, `1492` octets,
SHA-256 `4248bb41ce9e0608822117708f6f487298cfff07d2e345f6ad99cdc33d561a23`.

Validation locale : `3/3` tests administratifs et `376/376` tests H27.
