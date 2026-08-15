# H27 — préflight Mac lecture seule du runner exact

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Runner revu PASS : `5bfb382fbb72bdcb0a9a1b432361e64fc3030d36`

## Autorisation et portée

La revue externe autorisait uniquement un préflight Mac strictement en lecture
seule du runner exact. Aucun ACK, runner, checkout/detach, fetch, pull, registre,
autorité, creator, bundle, materializer, science ou locked test n'était
autorisé.

Toutes les lectures Git distantes ont utilisé `git --no-optional-locks`. Aucun
fichier n'a été créé, modifié, copié ou supprimé sur le Mac.

## État Mac vérifié

```text
platform          Darwin
checkout realpath /Users/amcarene/midi-worker/repository
ODB realpath      /Users/amcarene/midi-worker/repository/.git
HEAD              75322bc6b0fbf2afe458cc3ed5116c9cb8229cbf
symbolic HEAD     refs/heads/codex/independent-note-neural-v2
worktree status   clean
target type       commit
ACK               absent
.git/index.lock   absent
runner process    absent
```

La cible vérifiée est :

```text
7ee0a8977208bfa389e284b07207abc40a3517fd
```

## Blocage avant invocation

Les huit blobs exacts requis sont absents de l'ODB Mac :

```text
d1cdf1562a814cef271d606da331e96565fcc79a runner
d03385d842ca11631ba690d0a4bb70448c84480e runner binding
e574ddbcccb8bac791d9719fbee3e7fd5db8a047 runner binding seal
a514aa0270926dca1d8402ac84078a50754d2f17 transition binding
0f6a64b7477bde24968200a81d389b03a4a6ced0 transition binding seal
11fff0962fc0951a0bb06605e233d34756a2f4d9 transition contract
24a8c14fddd52eca148f961a31c39abaa4de018f transition contract seal
bda7e1fae7379996563e73d8bbcf1b2d7a871aa0 reviewed preflight evidence
```

Le runner exact ne peut donc pas encore être invoqué depuis son blob Git. Le
préflight s'arrête avant toute consommation. Il n'existe aucun fallback vers le
fichier du worktree.

## STOP

État terminal :
`H27_TARGET_CHECKOUT_EXACT_DETACH_PREFLIGHT_BLOCKED_REQUIRED_GIT_BLOBS_ABSENT_NO_EFFECT`.

La prochaine étape doit être définie et revue séparément : apport contrôlé des
objets Git exacts dans l'ODB Mac sans changer HEAD, index ou worktree. Aucun
fetch/synchronisation, ACK, runner ou detach n'est autorisé par ce rapport.
