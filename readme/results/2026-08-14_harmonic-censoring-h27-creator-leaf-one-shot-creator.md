# H27 — runner dormant one-shot du leaf `creator`

## Portée

Ce lot implémente uniquement le futur runner one-shot qui pourra créer le leaf
exact `/Users/amcarene/h27-admin/creator` après une nouvelle revue externe. Il
n'exécute pas le runner, n'observe pas le filesystem Mac et ne consomme aucune
autorité creator-leaf ou publisher.

## Chaîne d'identité

Le runner rehash, depuis l'object database Git exacte, les deux racines PASS du
contrat creator-leaf puis leurs cinq prédécesseurs transitifs. Les huit chemins
incluant le runner sont uniques.

| Objet | Git blob | Octets | SHA-256 brut |
|---|---:|---:|---:|
| `scripts/h27_create_creator_leaf_one_shot.py` | `848c65d0039b0ef60a5752835ce4a9b84be47c73` | 10474 | `04e5102eefa562b4cc9780c28be4ea365bdd37fc8e69c31d4c2f1bd670db86e1` |
| binding du runner | `31b3dc73c72cd56a50bc986b3ba4ce150e3bdf5f` | 4968 | `58b3581ea89f9a85fd313cad44008544740fce4a2604534d57bf90bcd378c266` |
| seal externe du binding | `d79d8af625dd4137d4574ba0ea46f19e7b906355` | 1812 | `dd7fd03429f01b5e8722f57e8a32963f3a29a27bdc83dfcc0ea555e4f04a194e` |

## Ordre one-shot scellé

1. rehash des sept identités prédécesseures ;
2. vérification macOS, `H27_CREATOR_LEAF_CREATE_EXECUTE=1` et zéro argument ;
3. ouverture `O_NOFOLLOW` du parent exact `/Users/amcarene/h27-admin` ;
4. vérification du dirfd et de l'entrée nommée contre device `16777233`, inode
   `1445438` ;
5. probe unique de l'absence de `creator`, relatif au dirfd ;
6. revalidation exacte du parent ;
7. `mkdir("creator")` comme premier et seul effet irréversible ;
8. `fsync` du parent, ouverture `O_NOFOLLOW` et vérification inode/device du
   leaf créé ;
9. dernière revalidation exacte du parent puis succès terminal.

Aucun `mkdir -p`, retry, cleanup, repair, publisher, creator entrypoint,
registre, bundle, locked-test ou science n'est accessible dans ce runner.

## Validation locale sans effet réel

```text
python -m py_compile scripts/h27_create_creator_leaf_one_shot.py
python -B -m unittest tests.test_harmonic_censoring_h27_creator_leaf_creator
.....
Ran 5 tests
OK
git diff --check
```

Les tests synthétiques vérifient la chaîne d'identité, l'ordre des appels, le
seul effet `mkdir`, le tuple terminal exact du parent et les états dormants.

## État et prochaine action

`creator` n'a pas été observé ni créé. L'autorité admin-root reste consommée,
l'autorité creator-leaf et le publisher restent non consommés. La seule action
suivante est la revue externe du runner exact, de son binding et de son seal.
Une exécution réelle demeure interdite avant PASS explicite.
