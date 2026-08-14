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

1. macOS, zéro argument et ACK exact `H27_ADMIN_ROOT_CREATE_EXECUTE=1` ;
2. accès au seul object database Git
   `/Users/amcarene/midi-worker/repository/.git` ;
3. rehash byte-exact de sept identités predecessor uniques ;
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
769c075121e26c267e586c8b109c30ac5379e9aa
9336 octets
be2c4841e861974627c6bf543c586dac1d35a969136a90ef39ca54020c4ec00a

identity binding
42c680c98d0a8af1aef4ea279034da563d886ce3
4537 octets
1fbdbb2250155e6a332d4edb8a20f20ba04b00b5846dd7b1ae890bfd7d91d18c

external seal
3ae077848263ddab9275a63199e69958991d155c
1432 octets
a333a6b4f56fb84ab0fa3a0801503002c81655fab4524388e1ca25e765c11693
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
`mkdir`, sans accéder au Mac ni au filesystem cible.

## STOP

État : `RUNNER_DORMANT_PENDING_EXTERNAL_REVIEW`.

La seule prochaine action est la revue externe du runner, de son binding et de
son seal exacts. La création réelle de `/Users/amcarene/h27-admin` reste
interdite jusqu'à un nouveau PASS et une autorisation explicite séparée.
