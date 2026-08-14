# H27 — runner dormant one-shot de création du leaf `registry`

## Portée

Après le PASS externe du binding administratif `c18ec063...`, ce lot
implémente uniquement le runner dormant de création de
`/Users/amcarene/h27-admin/registry`, son identity binding, son external seal,
les tests et la documentation. Le runner n'est pas exécuté.

## Implémentation fermée

Avant toute observation du parent, le runner rehash les sept identités uniques
liées depuis l'object database Git exact. Il exige ensuite macOS, zéro argument
et `H27_REGISTRY_LEAF_CREATE_EXECUTE=1`.

Le parent `/Users/amcarene/h27-admin` est ouvert `O_NOFOLLOW` et le fd ainsi
que l'entrée nommée doivent correspondre à device `16777233` / inode
`1445438`. Après un unique probe d'absence et une revalidation,
`mkdir("registry", dir_fd=parent_fd)` est le premier et seul effet
irréversible. Le parent est fsync, le leaf créé est ouvert `O_NOFOLLOW`, son
inode/device est vérifié, puis le parent est revalidé avant succès.

Il n'existe aucun cleanup, retry, repair, recreation ou `mkdir -p`. Le JSONL
registry, creator entrypoint, réservation, consommation, control bundle,
constructor, materializer, science et locked-test restent hors portée.

## Identités

```text
runner
ca93c383d8cc61a6f3869318f1e462ab82a1c92a
11186 octets
589950570a4ad30c8953f568a6df9a3027ce64d2abab62bd817c48f8b62a729c

identity binding
e2b18cf3c2d10ee3ee1f898038548717dd748b9b
5253 octets
397f7ff3ce1d8c6f2f3cba3620814e7a502325ea13a45db246460a273e35ae79

external seal
c3b9954936a1d21252d06ddc9fb5583035f8db47
1933 octets
5cd640df7fef20f5b9716f51733d872ebe9b51b954391949566ce3d8e08a88f7
```

## Validation locale sans effet

Le test vérifie les huit paths, le rehash réel des sept blobs Git, l'ordre
normatif, l'unicité du `mkdir`, le tuple parent, les dictionnaires complets du
binding/seal et l'appel synthétique sans filesystem réel.

```text
python -B -m unittest tests.test_harmonic_censoring_h27_registry_leaf_creator
5/5 PASS

python -m py_compile scripts/h27_create_registry_leaf_one_shot.py
PASS

python -B -m unittest discover -s tests -p "test_harmonic_censoring_h27*.py"
463/463 PASS

git diff --check
PASS
```

## STOP

La seule action suivante est la revue externe du runner, binding et seal.
Aucune exécution Mac n'est autorisée dans ce lot.
