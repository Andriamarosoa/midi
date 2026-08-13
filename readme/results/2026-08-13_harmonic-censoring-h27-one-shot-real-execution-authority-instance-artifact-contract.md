# H27 - contrat du futur artefact d'instance d'autorite one-shot

La revue externe de `46944859860f8dc2b07b7e4fa0a34bd7150ef81c`
conclut `PASS` sur le binding du contrat de l'autorite reelle one-shot. Cette
etape ajoute uniquement le contrat declaratif et le seal externe du futur
artefact d'instance d'autorite.

Le contrat lie les quatre identites PASS/scellees du contrat d'autorite et leurs
88 identites amont, soit 92 chemins uniques a rehasher avant toute future
creation. Il fixe exactement les champs, types, identites issuer/destination et
liaisons a la chaine scellee de l'artefact futur. L'instance doit etre single-use
et non reutilisable; l'ordre reste `rehash -> consume -> observe absence ->
create-exclusive`, avec terminalite et retry interdit.

Aucune instance n'est creee, accordee ou consommee. Aucun issuer n'est invoque;
aucune destination, operation filesystem, materializer, population ou science
n'est autorisee. Les huit edges restent fermes. `locked_test_used=false`;
entrainement et calibration restent interdits.

Identites avant commit : contrat blob
`b2e2a3d7ee8d554c4e7d4c988d17a7b8e5a39c22`, `6393` octets, SHA-256
`dffe596e893b34d3ecf840e7a038ef4e8849d744db6b95ccd250e3a9a1e0e020` ;
seal blob `17a7666fa71e00346a388d2f6e7bcae69c0e1b81`, `1445` octets,
SHA-256
`405d64c1b53a7125ef95a1def76db0880cb98aeba721576ba54851379c3f13ac`.

Validation locale : `3/3` tests administratifs, `349/349` tests H27,
`py_compile` et `git diff --check` passent.
