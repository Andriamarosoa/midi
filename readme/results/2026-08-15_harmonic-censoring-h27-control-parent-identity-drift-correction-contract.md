# H27 — contrat correctif de dérive d'identité du parent control

Après le `PASS` du runner dormant au commit
`6cfc210f2f96217b713baf1a84b5d09558023a73`, le préflight Mac en lecture
seule a observé :

```text
/Users/amcarene/h27-admin
historique scellé : device 16777233 / inode 1445438
observation actuelle : device 16777234 / inode 1445438
real directory=true, symlink=false
/Users/amcarene/h27-admin/control absent
```

Le blob runner `96df05111a5e40a418e12fb2b3db4bd9516bcab3` n'a pas été
exécuté. Aucun ACK, probe par le runner, `mkdir` ou autre effet n'a eu lieu.
Il reste non consommé mais son autorisation d'exécution est révoquée et il est
classé stale sous la frontière actuelle.

Le présent lot lie sans les modifier les sept identités historiques : contrat,
seal, binding, seal du binding, runner stale, binding du runner et seal du
binding du runner. Il distingue l'ancien fait terminal du nouveau fait Mac
rapporté, puis définit seulement une future frontière corrective
`16777234 / 1445438`. La cible, le mode `0700`, l'ACK, le probe unique,
l'unique `mkdir`, le fsync, la réouverture no-follow, les vérifications et
l'interdiction de retry/cleanup restent inchangés.

Identité du contrat correctif : blob
`f4c45904c72a8f2e12a3ea7d8d79bea276fefd3e`, `5475` octets, SHA-256
`9c7cae98c0590c88c0af17ae03102a617498ab4e3b98531905a59f95da228fe2`.

External seal : blob `527bb2d0b7cd5da384fcb4efb1ac5fee186b355c`,
`2002` octets, SHA-256
`b576bdccaf863c54d9867695bf0d67482c88d1fda7860b0c86701a75d81ec3b7`.

Portée : contrat correctif, external seal, test, README et présent rapport
uniquement. Aucun nouveau runner, action Mac, ACK, mkdir, registry, authority,
creator, bundle, constructor/materializer, science ou locked-test.

État :
`H27_CONTROL_PARENT_IDENTITY_DRIFT_CORRECTION_CONTRACT_PENDING_EXTERNAL_REVIEW`.

Validation locale : `4/4` tests ciblés, `490/490` tests H27, JSON strict,
`py_compile` et `git diff --check`. Aucun locked-test ni donnée scientifique.
