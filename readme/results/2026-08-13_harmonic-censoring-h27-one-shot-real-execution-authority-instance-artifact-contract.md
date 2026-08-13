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
`969fc67b0e9cd024d2021226afb2ff971f81e242`, `7320` octets, SHA-256
`197b9f0d304d2b159b8194c584ce3b1c2fbb9edf7131e5a6a3b201d2b6cf2d56` ;
seal blob `62555d67cb90629852b31644bc7ddb01fbed16a5`, `1445` octets,
SHA-256
`dd36c8ee7d99930f38085766d16a6a51f757e9706ae287ec67ea9052458f05ae`.

Validation locale : `3/3` tests administratifs, `349/349` tests H27,
`py_compile` et `git diff --check` passent.

La premiere revue externe conclut `FAIL` sur deux ambiguïtes. La correction
conserve un seul ordre canonique explicite des dix champs, definit l'ID par
SHA-256 du namespace et des bindings exacts, puis exige l'unicite permanente
de l'ID et du nonce avec reservation terminale avant publication.

La deuxieme revue conclut `FAIL` sur l'ordre interne encore implicite du
sous-objet `sealed_chain_identity`. La correction exige maintenant exactement
l'ordre declare de ses six cles et teste qu'une permutation produit des bytes
non canoniques et doit etre rejetee.
