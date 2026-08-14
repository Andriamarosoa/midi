# H27 — identity binding du contrat du fichier registry vide

Le contrat corrigé `ef866d365b79455508f5d2d866bbf1dc043f0f70` a reçu
`PASS`. Ce lot lie byte-exactement son contract, son seal et les quatre
prédécesseurs terminaux. Il préserve le parent `16777233 / 1448669`, le JSONL
exact, taille `0`, `nlink=1`, mode réel `0600`, ACK et compteurs `4/9/18/7`.

Aucun runner, accès Mac, JSONL, creator, bundle ou science. Seule la revue
externe du binding et de son seal est autorisée.

Identités exactes du lot :

- binding : `30e013f3dec986b031eed5a08c1b2f537742b5fb` / `3930` /
  `8d7131482ee43c7ac19cbdf1a3e9c24ac3700b784712ec07870f68581c7929db` ;
- seal : `f7abe0b02a4b721a9a28c15e25f94e099932e178` / `2212` /
  `15beb864045f9cacce11bae5f07a360e155fe4a7d8394e6f10d3bdd094187cda`.

Le test compare les six identités de chemins uniques, la frontière future
complète, l'état d'autorité terminal et le dictionnaire entier du seal. Il
refuse aussi toute référence arrière depuis les six objets liés vers le
binding ou son seal.

Validation locale avant commit : `3/3` tests ciblés, `469/469` tests H27 avec
le venv du dépôt, puis `git diff --check`. Aucun calcul scientifique ni accès
au locked-test.
