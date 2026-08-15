# H27 — runner dormant one-shot du parent control

La revue externe du commit
`a8662780533c9c613b22f709bd5da94d1526f314` conclut `PASS` pour le binding
administratif du contrat control-parent et son external seal.

Le lot courant ajoute uniquement :

- `scripts/h27_create_control_parent_one_shot.py` ;
- son identity binding et son external seal ;
- un test synthétique strict ;
- README et présent rapport.

Identités byte-exactes :

- runner : blob `96df05111a5e40a418e12fb2b3db4bd9516bcab3`, `9415`
  octets, SHA-256
  `42c3563aabfc3ede5090a0756ab4c58d601016190f502769859bc9279878261f` ;
- binding : blob `4a1b1ac62395d9880e747dc24395c2e2a0edce85`, `4881`
  octets, SHA-256
  `5d1bc87e54cbd0b9e6f7162767fa3eddfec5e6a1e63e3aa7bd2f74f89fc314bc`.
- external seal du binding : blob
  `449537a22bf1979273fd90e8bac7650170248f62`, `1811` octets, SHA-256
  `8b2959b65403151a6b4c8d2730aab5c2a72d0449db56eec0416b6e7030a34f8d`.

Avant toute observation de `/Users/amcarene/h27-admin/control`, le runner
rehash exactement sept identités uniques depuis la base d'objets Git, puis
exige macOS, `H27_CONTROL_PARENT_CREATE_EXECUTE=1` et zéro argument. Il ouvre
le parent avec `O_NOFOLLOW|O_DIRECTORY`, exige device/inode
`16777233/1445438`, sonde une seule fois l'absence de `control`, revalide le
parent et effectue `mkdir("control", 0700, dir_fd=parent_fd)` comme premier et
seul effet irréversible. Il fsync le parent, rouvre la cible sans suivre de
symlink, vérifie directory réel, mode `0700`, device/inode fd=entrée nommée,
revalide le parent, retourne succès et STOP.

Aucun `mkdir -p`, cleanup, retry, repair ou recreation. Tout échec après le
mkdir est terminal.

Portée non exécutée : aucun accès Mac, observation/création réelle du parent
control, registry, réservation/consommation, creator, bundle,
constructor/materializer, science ou locked-test.

État : `H27_CONTROL_PARENT_ONE_SHOT_RUNNER_PENDING_EXTERNAL_REVIEW_DORMANT`.

Validation locale : `6/6` tests ciblés, `486/486` tests H27 et
`git diff --check`. Ces tests sont administratifs/synthétiques uniquement ;
aucun locked-test ni donnée scientifique n'est utilisé.
