# H27 — Review 4 constructor HEAD transition terminal execution

Date : 2026-08-16

## Autorisation et identité

La revue externe du correctif `f4485f20da16f9342789cddca189e8d593efff01`
rend `PASS — exécutable` et autorise une unique invocation SSH vers
`amcarene@100.89.128.87` du runner exact :

```text
scripts/h27_review4_constructor_head_transition_once.py
size_bytes=15975
git_blob_sha1=037703a9e710c3eebbd349e8801c6fc5913e7582
raw_sha256=665f2a878973a7e03bd24ea0fac06c583f889a993ff575da697a498969571d32
ACK=H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_EXECUTE=1
arguments=0
```

Le bootstrap distant unique utilise le root neuf
`/Users/amcarene/h27-review4-f4485f20`, télécharge le fichier depuis le commit
exact, vérifie taille/SHA-256/blob Git avant renommage atomique, puis exécute
le runner dans `env -i`. L'ACK constructor reste donc absent.

## Résultat terminal du runner

Le runner émet avant le retour du shell :

```json
{"status":"H27_REVIEW4_CONSTRUCTOR_HEAD_TRANSITION_TERMINAL_SUCCESS_STOP","initial_head":"7ee0a8977208bfa389e284b07207abc40a3517fd","target_head":"46a6bdf81a56a7a7a10524d4e55092301a452207","target_is_exact_ancestor":true,"distance_commits":11,"detached":true,"worktree_clean":true,"index_lock_absent":true,"regular_refs_unchanged":true,"control_bundle_digest":"879d547c6fa4f1da36b83733bd658f10f48582fb6130470bb4657b70e55253fe","constructor_authority_id":"45f4dc4ff73284f1355eb125dc36d8c8bad2372818bf5f80b85b758ea69ae64e","constructor_git_blob_sha1":"0c1a2aca42baa77edbd77ab42c0bd0cefaaa2b62","constructor_size_bytes":12599,"constructor_raw_sha256":"0b8ad2a7efcd875b0102619eefe7ca9f015d9349693959803b9004bccf15b807","constructor_registry_absent":true,"constructor_final_absent":true,"constructor_staging_absent":true,"transition_attempt_consumed":true,"constructor_ack_present":false,"registry_opened":false,"authority_reserved":false,"authority_consumed":false,"constructor_invoked":false,"materializer_invoked":false,"science_or_locked_test":false}
```

Le checkout a donc atteint le HEAD exact requis par le gate constructor. Tous
les postchecks du runner sont passés après l'unique `checkout --detach`.

## Anomalie post-succès du wrapper

Après l'écriture de `runner.exitcode`, la copie de stdout et la preuve terminale
ci-dessus, le shell bootstrap rend :

```text
/bin/bash: line 90: exit: 0\r: numeric argument required
ssh_exitcode=255
```

Le CR provient de la terminaison ajoutée par le transport PowerShell à la
dernière ligne du script stdin. Cette erreur survient après le succès complet
du runner et après tous ses postchecks; elle ne remet pas le checkout en état
ambigu. Elle interdit néanmoins toute interprétation du code SSH seul comme
preuve de succès.

Conformément à la frontière approuvée, la transition est consommée dès le
lancement du subprocess checkout. Aucun retry, reset, cleanup, repair, seconde
observation SSH ou nouvelle invocation n'a été effectué.

## STOP

Le résultat scientifique reste inchangé : aucun constructor, ouverture de
registre, réservation/consommation de l'autorité constructor, staging/final,
materializer, P0/P1/P2, waveform/data, science, locked-test, training ou
calibration. STOP absolu avant le constructor et revue externe obligatoire de
cette preuve terminale et de l'anomalie post-succès.
