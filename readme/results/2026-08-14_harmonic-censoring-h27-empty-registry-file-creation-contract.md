# H27 — contrat one-shot du fichier registry vide

## Portée

Après le PASS externe de la création terminale du leaf `registry`, ce lot
définit uniquement le contrat déclaratif de la future création exclusive du
fichier initialement vide :

```text
/Users/amcarene/h27-admin/registry/h27-control-bundle-creation-authority-v1.jsonl
```

Aucun runner n'est ajouté et aucune action Mac n'est effectuée.

## Frontière

Le parent exact `/Users/amcarene/h27-admin/registry` est lié au tuple terminal
device `16777233` / inode `1448669`. Le futur runner devra rehasher quatre
preuves, imposer macOS, zéro argument et
`H27_REGISTRY_FILE_CREATE_EXECUTE=1`, puis ouvrir le parent `O_NOFOLLOW` et
conserver son dirfd.

Après un unique probe d'absence et une revalidation, l'ouverture exclusive
`O_CREAT|O_EXCL|O_NOFOLLOW` du leaf exact en mode `0600` sera le premier et
seul effet irréversible. Le fichier devra rester un regular file de 0 octet,
`nlink=1`. Il sera fsync, le parent sera fsync, puis le fichier sera rouvert et
son fd comparé à l'entrée nommée avant une dernière revalidation du parent.

Aucune ligne JSONL, réservation, consommation, creator entrypoint, bundle,
constructor, materializer, science ou locked-test n'est autorisé. Aucun retry,
cleanup, repair ou recreation n'est permis après le premier effet.

## Identités

```text
contract
0ba34b0ab41b45b340e80cd6ee2dc72e1381b841
5892 octets
9d9fbce3bc5baeb90fbdbcc2f1690ae3c2ee73270dbaeaaa809568ce3e80fa61

external seal
8604c164c42855b68f136d8dbb8099dfc2a1c806
1868 octets
cfd02ecb552b8f3bcecb51e6e6b3fa93c1c9b3af43f1531ec9ec8cec69590a68
```

## Validation locale sans effet

```text
python -B -m unittest tests.test_harmonic_censoring_h27_registry_file_creation_contract
3/3 PASS

python -B -m unittest discover -s tests -p "test_harmonic_censoring_h27*.py"
466/466 PASS

git diff --check
PASS
```

## STOP

La seule prochaine action est la revue externe de ce contrat et de son seal.
La création réelle du fichier reste interdite.
