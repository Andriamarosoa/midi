# H27 - binding du contrat d'artefact d'instance d'autorite

La revue externe de `0e3abcf37c4909cd0b6eebdb5f43a2f051868f24`
conclut `PASS` sur le contrat corrige du futur artefact d'instance d'autorite.
Cette etape ajoute uniquement son identity binding administratif et le seal
externe du binding.

Le binding lie le contrat PASS, son seal et ses 92 predecesseurs : 94 chemins
uniques sont recomposes et rehashes. Il preserve les ordres canoniques du
top-level et de `sealed_chain_identity`, la derivation de l'ID, l'unicite
permanente de l'ID et du nonce, le registre et la reservation terminale, ainsi
que l'ordre one-shot et l'interdiction de retry.

Aucune instance d'autorite ou artefact reel n'est cree, accorde ou consomme.
Aucun issuer n'est invoque; destination, filesystem, materializer, population
et science restent fermes. Les huit edges restent fermes et
`locked_test_used=false`.

Identites avant commit : binding blob
`544d1b6cfc058028dde9a97defabf0da2de160ee`, `3482` octets, SHA-256
`11d9c682b5b43712f1e125120221afb4edb8123355aaf6cdf7ede564f7233da9` ;
seal blob `e370b22b2ab5c1336caf56ff324b9cff0c8220b6`, `1532` octets,
SHA-256
`828372a4b193b416182fa3ca605a89b7490430d8f608812d1590a6bd80ccdbf8`.

Validation locale : `3/3` tests administratifs, `352/352` tests H27,
`py_compile` et `git diff --check` passent.
