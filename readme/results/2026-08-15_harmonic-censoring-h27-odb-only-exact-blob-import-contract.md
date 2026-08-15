# H27 — contrat d'apport ODB-only des huit blobs exacts

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `0c3a90776c48f3edd5a05f98653e253084637d4d`

## Portée

Contrat déclaratif, external seal, test déterministe et documentation
uniquement. Aucun apport de blob, accès Mac, ACK, runner, detach, registre,
autorité, creator, bundle, materializer, science ou locked test.

## Identités

```text
contract blob  902cb51ec2e220ba0bdaf9d2fef90bf3dc174a10
contract size  6461
contract sha   75d5583ffbb6dafcdc5b78f50d20b74c39640cd12f68a2b30ecab215a173e76e

seal blob      3e3348c543c94720323e17271164e2febfc35bac
seal size      4608
seal sha       55f1add9ad5e25ed5e5766e5010c3cb5286e97485de3cddfe6dfe0259b032f73
```

Le contrat lie les huit payloads par chemin, blob SHA-1 Git, taille et SHA-256
brut. Les huit chemins et les huit IDs doivent être uniques.

La première revue externe du commit `3793e7d6...` rend `FAIL` uniquement parce
que l'interdiction de modifier les refs n'était pas accompagnée d'une preuve
avant/après. La correction courante ajoute cette capture et les deux
comparaisons byte-exactes dans le contrat, le seal, le test et la documentation,
sans ajouter d'implémentation ni d'effet Mac.

## Frontière future préenregistrée

Avant la première écriture future, l'exécuteur devra :

1. vérifier Darwin, l'ACK dédié, zéro argument, checkout/ODB réels ;
2. vérifier HEAD, symbolic HEAD, worktree propre, absence de lock/processus et
   capturer l'identité byte-exacte de l'index ainsi qu'un snapshot déterministe
   byte-exact de toutes les refs triées par nom ;
3. recevoir hors du checkout cible exactement huit payloads et tous les garder
   en mémoire, sans staging fichier ;
4. valider les huit triples d'identité et leur hash Git sans `-w` ;
5. revalider l'état initial, le même snapshot de refs et l'index, puis exiger
   les huit blobs absents ;
6. écrire une seule fois chaque blob dans l'ordre déclaré avec :

```text
git --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  hash-object -w --stdin
```

Chaque retour doit être l'ID attendu. Ensuite, les huit blobs, HEAD, symbolic
HEAD, snapshot byte-identique de toutes les refs, index byte-identique,
worktree, lock, ACK runner et downstream flags doivent être revalidés.

Le snapshot futur est défini exactement par :

```text
git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  for-each-ref --sort=refname \
  --format=%(refname)%00%(objectname)%00%(objecttype)%00
```

Ses octets bruts restent en mémoire ; taille et SHA-256 sont également
archivés. L'égalité des octets, et pas seulement d'un booléen déclaratif, est
requise avant et après l'effet.

Fetch, pull, sync, update-ref, checkout, switch, detach, fallback worktree,
payload supplémentaire, retry, cleanup, réparation ou récupération automatique
sont interdits. Un import partiel futur serait un échec terminal consommé, sans
revendication de rollback.

## Validation locale

- `py_compile` : réussi ;
- tests ciblés : `5/5` réussis en `0,002 s` ;
- suite H27 complète : `519/519` réussis en `68,123 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le contrat reste dormant et non approuvé. Prochaine action unique : revue
externe du contrat et du seal exacts. Aucun apport réel n'est autorisé.
