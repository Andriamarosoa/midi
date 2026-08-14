# H27 - binding du contrat de creation du bundle

La revue externe de `e875d5831f45fdf2fa7c8f9c62d2206a98bd0d98`
conclut `PASS`. Ce lot ajoute uniquement l'identity binding administratif du
contrat de creation du bundle immuable et son seal externe.

Contrat + seal + 120 predecesseurs forment 122 chemins uniques rehashes. Le
binding preserve le manifeste ferme de six fichiers, les chemins exacts, la
source par blobs Git, les 13 etapes et les regles terminales.

Aucun bundle n'est observe ou cree. Aucun filesystem, registre, reservation,
consommation, invocation, destination, population ou science n'est ouvert.

Binding exact : blob `0385ba78d55f3c2e3af987132c985e60be612ddc`,
`3261` octets, SHA-256
`226cfc34329f9ef7545f95ae415c0b6f151bf4694c39bae3e80e18defec8f4d1`.
Seal exact : blob `706df7a6fdc437fac2965b25aeaee06a7783b538`, `1475`
octets, SHA-256
`3e98fbbf9ba9821eba5d8c578e51023ff3a807e9128b0e8bab451832229adced`.

Validation locale : `3/3` tests administratifs, `400/400` tests H27 et
`git diff --check` sans anomalie.
