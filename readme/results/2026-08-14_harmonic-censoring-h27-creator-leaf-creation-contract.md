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
   `O_NOFOLLOW` et ancré par `dirfd` ; le fd et l'entrée nommée doivent tous
   deux correspondre exactement au device `16777233` / inode `1445438` de la
   création terminale ;
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
8a03300a483bfc962ce8577e59e32df964d79a0e
5148 octets
1c3412c459301b5e0f0c90f4ce2eb0bc926aa7e160e7c7efc43eed134fafec54

external seal
c86b6da60f834480a64db5e806a9cebc119de815
1652 octets
af370f69c2bfffcc2559f9473039fbf05e968d64c7f0c72a6170d96f65f38257
```

## Validation locale sans effet

Le test compare les trois predecessor identities, la preuve terminale, les
paths/ACK, l'ordre exact des quatre préflights et sept étapes, le dictionnaire
exact des quatorze règles, les sept exigences du futur runner et tous les états
dormants.
La micro-correction après revue lie mécaniquement l'identité future attendue
du parent à l'identité terminale archivée, et le seal reflète ces valeurs
exactes. Une suppression/remplacement au même chemin doit donc échouer avant
le probe de `creator`.

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
