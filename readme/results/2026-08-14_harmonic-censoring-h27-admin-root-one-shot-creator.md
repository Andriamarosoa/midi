# H27 — runner dormant one-shot de création de la racine administrative

## Portée

Ce lot applique uniquement la portée autorisée après le PASS externe de
`fba12da62f2271d574a9fb46c8a20260cf55a1f1` : implémentation dormante du
runner one-shot de création de `/Users/amcarene/h27-admin`, identity binding,
external seal, test et mise à jour documentaire.

Aucune commande de ce runner n'a été exécutée. Aucun chemin Mac n'a été
observé ou créé. Publisher, creator, registre, réservation, consommation,
control bundle, science et locked test restent hors portée.

## Implémentation fermée

Le runner `scripts/h27_create_admin_root_one_shot.py` impose, dans cet ordre :

1. accès au seul object database Git
   `/Users/amcarene/midi-worker/repository/.git` ;
2. rehash byte-exact de sept identités predecessor uniques ;
3. macOS, zéro argument et ACK exact `H27_ADMIN_ROOT_CREATE_EXECUTE=1` ;
4. ouverture de `/Users/amcarene` avec `O_NOFOLLOW`, contrôle realpath,
   répertoire, inode et device, puis conservation du `dirfd` ;
5. unique probe d'absence du leaf `h27-admin` relatif au `dirfd` ;
6. nouvelle vérification du parent ;
7. `mkdir("h27-admin", 0700, dir_fd=parent_fd)`, premier et seul effet
   irréversible ;
8. `fsync` du parent, ouverture `O_NOFOLLOW` du leaf créé et vérification de
   son inode/device contre l'entrée nommée ;
9. dernière vérification du parent puis succès terminal.

Il n'existe aucun chemin de cleanup, repair, retry, `mkdir -p` ou fallback vers
les fichiers du checkout/worktree. Le publisher précédent n'est pas consommé.

## Identités

```text
runner
4fd4c77881f9801ec9d78494231a7c053b478da5
9401 octets
f29d33c589d8a2d1fbf88e8ed5b995b471d38fd1854683daaf8feeaf998de1b0

identity binding
283312559e7c9a2cdfe52ed7102a7821ccb4e96b
4537 octets
2bf1dc2ec905ae6a736f852ad5e6a5dff01357844ae643751ea11eb2b5423a8b

external seal
696ca0c006202c63a1942b3da71078097b64c257
1432 octets
b28c1e91399bfea56782c7405e76aa240df1f96b09ff12684368c487a1908dd8
```

Le graphe lié contient huit paths uniques en incluant le runner. À
l'exécution, le runner rehash les deux racines contract-binding/seal et leurs
cinq identités transitives avant toute observation du parent administratif.

## Validation locale sans effet

```text
python -B -m unittest tests.test_harmonic_censoring_h27_admin_root_creator
4/4 PASS

C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest discover -s tests -p "test_harmonic_censoring_h27*.py"
440/440 PASS

python -m py_compile scripts/h27_create_admin_root_one_shot.py
PASS

git diff --check
PASS
```

Le test synthétique vérifie dynamiquement l'ordre des appels et l'unicité du
`mkdir`, sans accéder au Mac ni au filesystem cible. Après la première revue,
le test verrouille aussi comme dictionnaires exacts `execution_binding`, les
dix `creation_safeguards` et les trois claims correspondants du seal ; l'ordre
normatif est exactement `rehash -> ACK/macOS/0 args -> open parent`.

## STOP

État : `RUNNER_DORMANT_PENDING_EXTERNAL_REVIEW`.

La seule prochaine action est la revue externe du runner, de son binding et de
son seal exacts. La création réelle de `/Users/amcarene/h27-admin` reste
interdite jusqu'à un nouveau PASS et une autorisation explicite séparée.
