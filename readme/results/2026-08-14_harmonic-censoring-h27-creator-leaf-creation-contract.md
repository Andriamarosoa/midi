# H27 — contrat de création one-shot du leaf `creator`

## Résultat administratif précédent

Après le PASS externe du runner corrigé au commit
`042974fde833d1ec13132520f003fba0b60ae044`, les bytes exacts du blob Git
`4fd4c77881f9801ec9d78494231a7c053b478da5` ont été exécutés une seule fois
sur le Mac avec l'ACK exact et zéro argument.

```json
{"status":"H27_ADMIN_ROOT_CREATED_TERMINAL_SUCCESS","verified_identity_count":7,"target_path":"/Users/amcarene/h27-admin","target_device":16777233,"target_inode":1445438,"publisher_authorization_consumed":false,"creator_child_created":false,"registry_opened":false,"control_bundle_created":false,"science_or_locked_test":false}
```

L'autorité de ce runner est terminalement consommée. Il ne doit jamais être
rejoué. Le publisher exact reste non consommé.

## Portée du lot courant

Le lot courant est strictement déclaratif : contrat + external seal + test +
documentation pour la future création one-shot de :

```text
/Users/amcarene/h27-admin/creator
```

Il ne contient aucun runner creator-leaf et n'accède à aucun filesystem Mac.

Le contrat fixe :

1. rehash de trois identités PASS du creator de la racine administrative ;
2. macOS, zéro argument et ACK futur exact
   `H27_CREATOR_LEAF_CREATE_EXECUTE=1` ;
3. parent exact `/Users/amcarene/h27-admin`, réel, préexistant, ouvert
   `O_NOFOLLOW` et ancré par `dirfd`/inode/device ;
4. unique probe d'absence de `creator` ;
5. revalidation du parent immédiatement avant effet ;
6. `mkdir("creator", dir_fd=parent_fd)` comme premier et seul effet
   irréversible ;
7. `fsync(parent_fd)`, ouverture `O_NOFOLLOW` du leaf et vérification
   inode/device ;
8. aucun `mkdir -p`, cleanup, retry, repair ou recreation ;
9. aucune observation des final/staging roots du publisher ;
10. aucun publisher, creator entrypoint, registre, réservation, consommation,
    control bundle ou science dans ce stage.

Le futur runner doit être un commit distinct, recevoir un PASS externe, être
identity-bound et scellé, puis être exécuté uniquement depuis ses bytes de blob
Git exacts. Aucun fallback checkout/worktree n'est permis.

## Identités

```text
contract
133719bcfca63bc05b5988a7f435d69d8794ef5e
4976 octets
65fca3a1d6c753ae8f9c4f26f14f5a26011b86923688e2f45f90d9cafdeccaed

external seal
90a3e827b595a71795d436224f252a518ef182d1
1424 octets
2d3d0ef988c717e33218890aeda3d9a83647b301bb6f9fed24d7f85b123487b5
```

## Validation locale sans effet

Le test compare les trois predecessor identities, la preuve terminale, les
paths/ACK, l'ordre exact des quatre préflights et sept étapes, le dictionnaire
exact des quatorze règles, les sept exigences du futur runner et tous les états
dormants.

```text
python -B -m unittest tests.test_harmonic_censoring_h27_creator_leaf_creation_contract
3/3 PASS

C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_harmonic_censoring_h27*.py"
443/443 PASS

git diff --check
PASS
```

## STOP

La seule prochaine action est la revue externe de ce contrat et de son seal.
Créer `creator`, relancer le publisher ou exécuter tout registre/bundle/science
reste interdit.
