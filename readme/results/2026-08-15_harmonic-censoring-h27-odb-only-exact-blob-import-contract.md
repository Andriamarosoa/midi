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
contract blob  a2c1b55cf4f128fcccce21a1823ad60c85f8d0ff
contract size  5967
contract sha   3e784445a6f058c2658f86383cdd0b7f6b59c7214f884546b7f1b59a98ab7321

seal blob      40b601b483811e42a10f377e3e6a2046e878a98a
seal size      4250
seal sha       ca98b7a8ec865c02f6e8e06f7f78fa3f11d7378f64164dcd8ba9160ebcf56599
```

Le contrat lie les huit payloads par chemin, blob SHA-1 Git, taille et SHA-256
brut. Les huit chemins et les huit IDs doivent être uniques.

## Frontière future préenregistrée

Avant la première écriture future, l'exécuteur devra :

1. vérifier Darwin, l'ACK dédié, zéro argument, checkout/ODB réels ;
2. vérifier HEAD, symbolic HEAD, worktree propre, absence de lock/processus et
   capturer l'identité byte-exacte de l'index ;
3. recevoir hors du checkout cible exactement huit payloads et tous les garder
   en mémoire, sans staging fichier ;
4. valider les huit triples d'identité et leur hash Git sans `-w` ;
5. revalider l'état initial puis exiger les huit blobs absents ;
6. écrire une seule fois chaque blob dans l'ordre déclaré avec :

```text
git --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  hash-object -w --stdin
```

Chaque retour doit être l'ID attendu. Ensuite, les huit blobs, HEAD, symbolic
HEAD, index byte-identique, worktree, lock, ACK runner et downstream flags
doivent être revalidés.

Fetch, pull, sync, update-ref, checkout, switch, detach, fallback worktree,
payload supplémentaire, retry, cleanup, réparation ou récupération automatique
sont interdits. Un import partiel futur serait un échec terminal consommé, sans
revendication de rollback.

## Validation locale

- `py_compile` : réussi ;
- tests ciblés : `5/5` réussis en `0,002 s` ;
- suite H27 complète : `519/519` réussis en `69,215 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le contrat reste dormant et non approuvé. Prochaine action unique : revue
externe du contrat et du seal exacts. Aucun apport réel n'est autorisé.
