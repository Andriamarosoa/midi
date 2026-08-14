# H27 — identity binding du contrat creator-leaf

Portée strictement administrative après le PASS externe de
`e22296126b8119fd2422d79f85597536e02f6bb8` : identity binding + external seal
du contrat de future création one-shot de `/Users/amcarene/h27-admin/creator`.

Le binding rehash cinq paths uniques : contrat PASS, seal du contrat et trois
identités PASS du creator admin-root. Il préserve le parent terminal exact
`/Users/amcarene/h27-admin`, device `16777233`, inode `1445438`, l'ACK
`H27_CREATOR_LEAF_CREATE_EXECUTE=1`, les compteurs `4/7/14/7`, le publisher
non consommé et l'interdiction de runner/filesystem/registre/bundle/science.

```text
binding
08b359b0de2fb24bf9521447dec98586626286d8
3989 octets
83c7419c5eb66656ba85f4cb77945119b5c09d8e6405b72a12501af21bcba34a

seal
a6da2009e074eabbf4c56e528eb86b078bdd80a1
1595 octets
e22b065cf1dce56e8f9f197c660cb3be9d9fd1d24bccec6a956cce1dc1f6d7ea
```

Aucun runner n'est ajouté et aucun accès Mac n'est effectué. La prochaine
action unique est la revue externe de ces bytes exacts.

Validations locales sans effet : test ciblé `3/3`, suite H27 `446/446` et
`git diff --check` PASS.
