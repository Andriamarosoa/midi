# H27 — publisher one-shot de la source creator, dormant

Date : 2026-08-14

## Portee

Ce lot ferme uniquement les trois bloqueurs de la revue du draft non versionne :

- ancrage stable du parent administratif contre le TOCTOU ;
- relecture byte-exacte staging/final depuis les memes descripteurs verifies ;
- identite Git immuable du publisher qui sera eventuellement execute plus tard.

Aucune publication, observation des roots final/staging, ouverture de registre,
reservation, consommation, creation de bundle, invocation du creator, population,
science ou locked-test n'a eu lieu.

## Implementation

Le publisher est maintenant versionne dans
`scripts/h27_publish_reviewed_creator_source_one_shot.py`.

Avant toute observation des deux roots, il exige macOS, l'acknowledgement exact,
l'absence d'arguments, le Git object database exact, les `139` identites revues,
le blob exact de l'entrypoint, le manifest canonique et le parent exact. Le parent
est ouvert avec `O_NOFOLLOW`, compare par `(st_dev, st_ino)` au chemin attendu et
garde ouvert ; probes, `mkdir`, writes et `renameatx_np(RENAME_EXCL)` utilisent ce
meme `dirfd`.

Chaque fichier est ouvert avec `O_NOFOLLOW`, controle par `fstat`, lu depuis ce
meme fd, puis controle a nouveau. Le set ferme du repertoire et son identite sont
reverifies. Le staging reste le premier effet irreversible ; aucun cleanup,
retry, repair ou republication n'est implemente.

## Identites

```text
publisher
22fbc4ae6da12fd7ab7a55b630a87fbac73b07db
16875 octets
80d46a6d695e1b2f10b24bf8ffd24024521862776d21c4c9027c1b76ec3b43fc

identity binding
11b68809991352a42430cde7ecb301e441abb542
2984 octets
f700f00c10cb96fd310f98d7d9baa53ad32ae42529622b9385e41f2254b41e03

external seal
cc627c2257545445238988fe4c4470628df1deba
1317 octets
256d24c31b59c2b75122dc58546a2ec124fbd8b2546ce4c64b2141c102ac13d3
```

## Validation locale

```text
py_compile : PASS
test cible publisher : 3/3 PASS
suite H27 : 430/430 PASS
git diff --check : PASS
```

Le test dry-run remplace uniquement la lecture du Git object database Mac par le
Git local et confirme `139` chemins uniques ; il n'appelle jamais `publish()`.

## Etat et suite

Etat : `DORMANT_PENDING_EXTERNAL_REVIEW`.

La prochaine action autorisee est la revue externe du publisher, de son binding
et de son seal exacts. La publication reelle reste interdite avant verdict PASS.
