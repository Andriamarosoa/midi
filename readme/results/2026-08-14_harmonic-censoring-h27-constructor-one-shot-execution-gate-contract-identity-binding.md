# H27 - binding du contrat du gate one-shot

La revue externe de `6be05ef36794e4a42c133f9542fa2a30fa618496`
conclut `PASS`. Ce lot ajoute uniquement l'identity binding administratif du
contrat corrige du gate one-shot et son seal externe.

Contrat + seal + 116 predecesseurs forment 118 chemins uniques rehashes. Le
binding preserve les deux sources runtime exactes, le HEAD cible
`46a6bdf8...`, l'ID d'autorite `45f4dc4f...`, `single_use=true`,
`consumed=false`, l'ordre fail-closed et les huit edges fermes.

Aucun bundle administratif, registre, reservation, consommation, invocation,
destination, filesystem, materializer, population ou science n'est ouvert.

Binding exact : blob `d11e21aa00ca09d107ebe4ef4b537a707f2f89b9`,
`3817` octets, SHA-256
`7fb124b55865624faf26d45795c1708a18b100a94689aff6a2e5f1a90e10c463`.
Seal exact : blob `8a9b96602dd3c940a7c336cbc4a5f15b6a2f7355`, `1754`
octets, SHA-256
`710c18649b6e97c272b7ab041d6d71f53e969a40d2a4a97115f6ccc62a00ff39`.

Validation locale : `3/3` tests administratifs, `394/394` tests H27 et
`git diff --check` sans anomalie.
