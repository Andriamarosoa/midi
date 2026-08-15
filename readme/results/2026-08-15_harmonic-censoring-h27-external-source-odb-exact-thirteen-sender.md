# H27 — sender dormant de préparation des treize blobs exacts

## Verdict local

Le sender/orchestrateur local est implémenté, scellé et testé, mais reste
strictement dormant en attente d'une revue externe. Aucun SSH, ACK distant,
transport, apport d'objet, import, detach, downstream, waveform, entraînement
ou locked-test n'a été exécuté.

État :
`H27_EXTERNAL_SOURCE_ODB_EXACT_THIRTEEN_SENDER_IMPLEMENTED_DORMANT_PENDING_EXTERNAL_REVIEW_NO_SSH_NO_DELIVERY`.

## Portée réalisée

Le nouveau runner
`scripts/h27_prepare_exact_thirteen_source_odb_delivery.py` couvre uniquement
les quatre étapes pré-SSH autorisées :

1. exigence Windows, ACK local de préparation, zéro argument, HEAD
   `c0bb8d20862f80cabc72ea64a5d437750b7c12e8`, branche exacte et worktree
   propre ;
2. chargement et rehash du receiver exact depuis son blob Git revu ;
3. lecture ODB et rehash des treize blobs dans l'ordre du contrat, extraction
   AST sans exécution de `EMBEDDED_OBJECTS`, décodage base64 canonique et
   égalité byte-exacte sender/receiver ;
4. construction en mémoire de l'invocation exacte
   `ssh -T amcarene@100.89.128.87 env H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1 /usr/bin/python3 -`,
   puis arrêt avant toute exécution SSH.

Chaque subprocess Git supprime tous les `GIT_*` hérités, réintroduit seulement
`GIT_TERMINAL_PROMPT=0` et `GIT_NO_LAZY_FETCH=1`, et emploie le préfixe
littéral scellé avec `-C` vers le worktree isolé. Aucun fichier checkout ne
sert de source au receiver, aux contrats ou aux payloads.

Le `main()` ne transporte rien : il ne peut produire qu'un résumé JSON de
préparation avec `transport_executed=false`. La préparation réelle n'a pas été
lancée dans cette phase, car le worktree de développement se trouve
volontairement après le HEAD sender historique scellé. Les tests utilisent des
mocks pour ce garde-fou et une lecture réelle mais strictement read-only de
l'ODB pour vérifier les identités.

## Identités exactes

- sender : blob `8bdcc68e7cc6e27bc507f568b44f1978e95a728c`, `13032` octets,
  SHA-256 `9245a1d0b98806f1092703ee03295557e6d5904c3443d7aca56ae0397d9f2b9d` ;
- identity binding : blob `cf17caf8c51871a8bf7ceb0e723b0d4a46e54fb9`, `4714` octets,
  SHA-256 `07088b7a82b481b470c63060d63e16b23af5e482e857aa127acfdb1380ea5d1b` ;
- external seal : blob `55df7177f8549a9cd24dc84de107db083739ee50`, `4624` octets,
  SHA-256 `bc2d43c7dea3442e3ade56194bb19b67a4775d8410190c1a8fc1c50c91164e14`.

Le receiver reste celui revu : blob
`9d32cac8ddb29e43975a6b82f5c1c39a91f93df4`, `119406` octets, SHA-256
`996c4539a357b13af65012de84ed836179389f111dd1849eb1ca165d15374000`.
Les treize payloads représentent exactement `75730` octets bruts.

## Validation

- tests sender ciblés : `7/7` en `1.638 s` ;
- suite H27 complète : `547/547` en `97.046 s` ;
- `py_compile` : réussi ;
- `git diff --check` : réussi.

Le test d'intégration rehash le receiver et les treize blobs réels depuis
l'ODB local, sans mutation. Le test de frontière construit le tuple SSH exact
et démontre que `subprocess.run` n'est jamais appelé dans cette phase de
préparation simulée.

## Latence et science

Impact live : nul, car ce lot est uniquement administratif et dormant. Aucune
inférence ou donnée scientifique n'est ouverte. `locked_test_used=false`.

## STOP et prochaine action

STOP avant SSH. La seule action suivante est la revue externe du sender, de son
binding et de son seal exacts. Restent interdits sans nouveau `PASS` explicite :
SSH, ACK distant, transport stdin, écriture ODB, import, detach et downstream.
