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
943034b75504eefc6986e5eb5b7237b63cd36155
5981 octets
ccdc38bef19ea77391bd551c308d5bbb0dafd955435764b3c0685123c3c0d671

external seal
e697b7fe342583d7d153a9fcd717b43e28f7c581
1868 octets
9de62a4856758d9784de4f3e8963e8994a8f5198558a67ee88febab1d017065d
```

La micro-correction après revue exige désormais explicitement que le mode
réel soit `0600` sur le fd créé puis sur le fd rouvert et l'entrée nommée. Le
test compare les quatre préflights, les neuf étapes, le dictionnaire exact des
18 règles, les sept exigences runner et le seal complet exact.

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
