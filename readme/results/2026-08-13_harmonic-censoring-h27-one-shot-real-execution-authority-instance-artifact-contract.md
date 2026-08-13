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
`302b9ad2de7985c1636dd17ab859e3ac107e25ce`, `7168` octets, SHA-256
`ace62d0f8602597bd4fb2b4135ee25cbd218c9c7f5588086c3816741343b3261` ;
seal blob `064718b0d02a95a0b2f8484d0f43c36620546f7f`, `1445` octets,
SHA-256
`f26086db443d69910709cbda1450b57fe5dcb1c99d5afa0c6fd778e2c996ab7d`.

Validation locale : `3/3` tests administratifs, `349/349` tests H27,
`py_compile` et `git diff --check` passent.

La premiere revue externe conclut `FAIL` sur deux ambiguïtes. La correction
conserve un seul ordre canonique explicite des dix champs, definit l'ID par
SHA-256 du namespace et des bindings exacts, puis exige l'unicite permanente
de l'ID et du nonce avec reservation terminale avant publication.
