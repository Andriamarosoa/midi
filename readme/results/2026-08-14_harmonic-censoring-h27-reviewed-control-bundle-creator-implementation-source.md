# H27 - entrypoint Git dormant du reviewed control-bundle creator

La revue externe de `b93d6580ff19b7a514cefdae18a00c0f0c0457e6`
conclut `PASS`. Ce lot cree uniquement dans Git l'entrypoint futur du creator,
son identity binding administratif et son external seal. La racine
`/Users/amcarene/h27-admin/creator/h27-reviewed-control-bundle-creator-v1`
n'est ni creee ni observee.

L'entrypoint est import-effect-free et verrouille le chemin source, le manifest
canonique, le Git object database explicite, les 130 identites amont, les six
fichiers du bundle, le registre preexistant, la reservation/consommation, la
publication atomique macOS sans overwrite et les sorties terminales sans retry.
Son execution reelle reste interdite.

La premiere revue externe de `b8d0c9c7879dfe656e582f5b3a53e6a04ba41627`
conclut `FAIL` sur quatre surfaces fail-closed. La micro-correction du meme
stage rejette desormais tout JSON duplique/non canonique et `schema_version`
booleen, valide chaque record registre byte-exactement avec sa chaine de
transitions, ouvre le registre par `O_NOFOLLOW` puis `fstat`, et distingue un
append prouve inchange d'un append incertain afin de ne jamais creer deux
branches apres un echec de write/fsync.

La deuxieme revue de `a9c60a4336638fa433a0cb978c1c892e1fb4848b`
confirme les quatre corrections fonctionnelles mais conclut `FAIL` sur un claim
de binding trop fort. Le claim universel de fsync terminal est remplace par
quatre invariants exacts : retour seulement apres fsync reussi, propagation
sans branche concurrente d'un append incertain, et terminal_failure unique
seulement apres append prouve inchange ou echec de publication. L'entrypoint
reste strictement byte-identique.

Identites exactes :

- entrypoint : `2091028d44bf9c8e1ab05b7d6656719ebc260832` / `44063` octets /
  `0f0dd5867c82b1237736d03f48a6176171c4459b9106bca251ab53778092e42f` ;
- binding : `3eea754aeb355780e082e9de9bbdeec350b66152` / `6091` octets /
  `0d0844952802dfe4b29c5c04104a4128c9a480171255f1aa6178a4cdbdd44367` ;
- seal : `aa3ebc704e5cb874cb09430eccdc5fc616ebb1cc` / `1649` octets /
  `1dd748ed7dce831128b42f6d5c1646952f5aaff2cff912071f2853e7e6ab1d23`.

Aucun filesystem administratif, registre, reservation, consommation, bundle,
invocation ou science n'a ete execute.

Validation locale sans calcul scientifique : `py_compile`, test cible `3/3`,
suite H27 `427/427`, puis `git diff --check` propre avant commit.
