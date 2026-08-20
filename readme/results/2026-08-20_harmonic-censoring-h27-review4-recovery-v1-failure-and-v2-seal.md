# H27 Review 4 — Recovery V1 terminale, Recovery V2 scellée

## Recovery V1

Le premier bloc SSH s'est arrêté avant toute mutation sur un contrôle local trop
strict du symlink du venv. Le reviewer a autorisé une reprise pré-ACK unique.
Cette reprise a vérifié les neuf composants byte-exacts, exporté l'ACK puis
invoqué le runner une fois. Le runner s'est arrêté dans `preclaim()` : le
binding imposait `0400` aux neuf composants, tandis que les deux lectures de
l'activation exigeaient `0600`. Aucun AUTHORITY, CLAIM, staging, final,
terminal, record, NumPy/plan ou science n'a été créé. Le root
`/Users/amcarene/h27-admin-recovery-v1` est conservé intact. Recovery V1 est
non rejouable parce que son ACK et son invocation unique ont été consommés.

## Recovery V2

Le runner commun lit désormais l'activation en `0400` avant et après CLAIM.
Recovery V2 utilise un root, une activation, un authority instance, un nonce,
des destinations et un entrypoint nouveaux sous
`/Users/amcarene/h27-admin-recovery-v2`. Son préflight atteste en lecture seule
les deux prédécesseurs : la lignée historique consommée et le root Recovery V1
échoué préclaim, avec ses neuf fichiers exacts et l'absence de ses cinq sorties.

La composition V2 contient exactement neuf composants, conserve le
matérialiseur historique byte-identique et le runtime venv attesté. Le vrai
plan figé reste `124` identités uniques (`17 baseline + 107 P2`). Les tests
ciblés passent sans données réelles, science, P0/P1/P2, locked-test ou train.

État : `RECOVERY_V2_SEALED_PENDING_EXTERNAL_PASS_NO_MAC_EXECUTION`.
