# H27 — identity binding du contrat registry-leaf

## Résultat précédent

La revue externe du commit `e07e26111bbcf0343a7b57f30c154ab667154fcf`
rend `PASS` au contrat déclaratif et à son seal pour la future création du leaf
exact `/Users/amcarene/h27-admin/registry`.

## Portée du lot

Ce lot ajoute uniquement l'identity binding administratif du contrat PASS,
son external seal, un test et la documentation. Il relie byte-exactement le
contrat, son seal et leurs trois predecessor identities déjà fermées.

Le binding conserve le parent exact `/Users/amcarene/h27-admin`, son tuple
terminal device `16777233` / inode `1445438`, la cible `registry`, l'ACK futur
`H27_REGISTRY_LEAF_CREATE_EXECUTE=1` et les compteurs `4 / 7 / 14 / 7`.
Les autorités admin-root et publisher restent terminalement consommées et non
rejouables. La source creator publiée reste inchangée.

Registry leaf et JSONL restent non observés, non créés et non ouverts. Aucun
runner, creator entrypoint, réservation, consommation, bundle, constructor,
materializer, science ou locked-test n'est autorisé.

## Identités

```text
identity binding
5a48c974f5ada84378a5f9010f24436e61a7968a
3787 octets
96adb1dcf9b024d8c62e319c5a1c0c19cce541165e568c2c138442c3a4454d27

external seal
f21eccb486b1fd7dfdd3ded43ba732a85561b54b
2078 octets
0723b935874e3e240a36c3b6a11976df320c70ce3b30692c74eaec7f1b0531f7
```

## Validation locale sans effet

Le test rehash le contrat, son seal et les trois prédécesseurs, puis compare
exactement la future frontière, l'état des autorités, le graphe d'identités et
tous les états dormants.

```text
python -B -m unittest tests.test_harmonic_censoring_h27_registry_leaf_creation_contract_identity_binding
3/3 PASS

python -B -m unittest discover -s tests -p "test_harmonic_censoring_h27*.py"
458/458 PASS

git diff --check
PASS
```

## STOP

Seule la revue externe du binding et de son seal est autorisée. Aucun runner
et aucune action Mac ne sont inclus.
