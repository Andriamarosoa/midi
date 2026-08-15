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
contract blob  42eebb259f247715ddcb404c8c236418093b6a81
contract size  7477
contract sha   567712b4e5c4491498be68be65b2633a4537d2221d484bd4a4dcbdbaf16a5b7a

seal blob      4002015587573e9a3e0b8f6dbb6dcea93b967b6e
seal size      5382
seal sha       95120579e240b454a4bbac21236a4c993b80244ff11d687b27e7a550ed422272
```

Le contrat lie les huit payloads par chemin, blob SHA-1 Git, taille et SHA-256
brut. Les huit chemins et les huit IDs doivent être uniques.

La première revue externe du commit `3793e7d6...` rend `FAIL` uniquement parce
que l'interdiction de modifier les refs n'était pas accompagnée d'une preuve
avant/après. La correction courante ajoute cette capture et les deux
comparaisons byte-exactes dans le contrat, le seal, le test et la documentation,
sans ajouter d'implémentation ni d'effet Mac.

La seconde revue externe de `883a67ab...` confirme cette comparaison pour les
refs régulières mais rend `FAIL` parce que `for-each-ref` omet les root refs et
pseudorefs sans option dépendante de la version Git. La correction courante
conserve la commande portable des refs régulières et ajoute un scan stdlib
déterministe des fichiers racine Git aux noms majuscules, sans accès Mac.

La troisième revue externe de `dda47ec4...` confirme cette couverture avec le
backend `files`, mais rend `FAIL` car ce backend n'était pas lui-même imposé.
La correction courante exige désormais exactement :

```text
git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  rev-parse --show-ref-format
```

avec la sortie `files`, avant snapshot, juste avant le premier effet futur et
après les huit écritures. Le backend `reftable` échoue fermé.

## Frontière future préenregistrée

Avant la première écriture future, l'exécuteur devra :

1. vérifier Darwin, l'ACK dédié, zéro argument, checkout/ODB réels ;
2. vérifier HEAD, symbolic HEAD, worktree propre, absence de lock/processus et
   capturer l'identité byte-exacte de l'index ainsi qu'un snapshot déterministe
   byte-exact des refs régulières triées par nom ainsi que de toutes les root
   refs/pseudorefs présentes dans `.git` ;
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
HEAD, snapshots byte-identiques des refs régulières et root refs/pseudorefs,
index byte-identique,
worktree, lock, ACK runner et downstream flags doivent être revalidés.

Le snapshot futur des refs régulières est défini exactement par :

```text
git --no-optional-locks --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  for-each-ref --sort=refname \
  --format=%(refname)%00%(objectname)%00%(objecttype)%00
```

En complément, l'exécuteur futur utilise `os.scandir` stdlib sur la racine ODB,
sélectionne tous les noms correspondant à `^[A-Z][A-Z0-9_]*$`, refuse symlinks
et entrées non régulières, trie les noms par octets UTF-8, puis conserve nom,
présence et octets bruts de chaque fichier. Cela couvre `HEAD` et toutes les
root refs/pseudorefs majuscules présentes, sans dépendre de
`--include-root-refs`. Les deux snapshots restent en mémoire ; taille et
SHA-256 sont également archivés. L'égalité exacte est requise avant et après
l'effet.

Fetch, pull, sync, update-ref, checkout, switch, detach, fallback worktree,
payload supplémentaire, retry, cleanup, réparation ou récupération automatique
sont interdits. Un import partiel futur serait un échec terminal consommé, sans
revendication de rollback.

## Validation locale

- `py_compile` : réussi ;
- tests ciblés : `5/5` réussis en `0,003 s` ;
- suite H27 complète : `519/519` réussis en `61,380 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le contrat reste dormant et non approuvé. Prochaine action unique : revue
externe du contrat et du seal exacts. Aucun apport réel n'est autorisé.
