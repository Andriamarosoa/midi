# H27 — contrat de création one-shot du leaf `registry`

## Portée

Après le PASS externe de la correction administrative `9d810613...`, ce lot
définit uniquement le contrat déclaratif de la future création one-shot de :

```text
/Users/amcarene/h27-admin/registry
```

Il ne contient aucun runner et n'accède à aucun filesystem Mac. La racine
administrative terminale reste `/Users/amcarene/h27-admin`, device `16777233`,
inode `1445438`. Les autorités admin-root et publisher sont consommées et ne
doivent jamais être rejouées ; la source creator publiée reste inchangée.

## Frontière fermée

Le futur runner devra rehasher les trois preuves scellées, imposer macOS, zéro
argument et l'ACK exact `H27_REGISTRY_LEAF_CREATE_EXECUTE=1`, puis ouvrir le
parent exact avec `O_NOFOLLOW`. Le fd et l'entrée nommée devront tous deux
correspondre au tuple terminal avant l'unique probe d'absence du leaf.

Après revalidation, `mkdir("registry", dir_fd=parent_fd)` sera le premier et
seul effet irréversible. Le parent sera fsync, le leaf créé sera ouvert avec
`O_NOFOLLOW`, son inode/device sera vérifié, puis le parent sera vérifié une
dernière fois. Aucun retry, cleanup, repair, recreation ou `mkdir -p` ne sera
permis.

Le JSONL `h27-control-bundle-creation-authority-v1.jsonl` ne doit être ni
observé, ni ouvert, ni créé dans ce stage. Réservation, consommation,
creator-entrypoint, control bundle, constructor, materializer, science et
locked-test restent interdits.

## Identités

```text
contract
ae1b651794fe4e379d91c92a20b806f78e67b723
5406 octets
a6f913fba0fae3e76c5586c7730982f4b095d16909a18c6c943465ade634559c

external seal
381b979bb26ae5a2b4244483317dbc77de05f783
1818 octets
dd5792eb147c82cb47d79a915bd0fca78a8c690a3f0ba149b7d5639c46fbc0cc
```

## Validation locale sans effet

Le test ferme les bytes LF, les trois identités predecessor, le tuple du
parent, le leaf/path/ACK exacts, les quatre préflights, sept étapes, quatorze
règles, sept exigences du futur runner et tous les états dormants.

```text
python -B -m unittest tests.test_harmonic_censoring_h27_registry_leaf_creation_contract
3/3 PASS

python -B -m unittest discover -s tests -p "test_harmonic_censoring_h27*.py"
455/455 PASS

git diff --check
PASS
```

## STOP

Seule une revue externe du contrat et de son seal est autorisée. Aucun runner
et aucune action Mac ne sont autorisés par ce lot.
