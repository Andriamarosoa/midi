# H27 — importer dormant one-shot des huit blobs Git exacts

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `dffce1f9a144be60968b7912e99c761ec058ee0f`

## Portée

Implémentation dormante uniquement du one-shot importer conforme au contrat
ODB-only approuvé, identity binding, external seal, tests synthétiques et
documentation. Aucun accès Mac, aucun ACK, aucun apport de blob, detach,
registre, autorité, creator, bundle, matérialisation, science ou locked test.

## Frontière d'entrée

Le runner exige macOS, zéro argument, l'ACK exact
`H27_ODB_ONLY_BLOB_IMPORT_EXECUTE=1` et un ODB Git source fourni par
`H27_ODB_ONLY_BLOB_IMPORT_SOURCE_GIT_DIR`. Cet ODB source doit être un
répertoire réel, absolu, non-symlink et extérieur au checkout cible. Aucun
fallback vers un checkout ou fichier n'existe : contrat, seal et huit
payloads sont lus uniquement par `git cat-file blob` depuis cet ODB externe.

Avant la première écriture, le runner garde les huit payloads en mémoire et
vérifie pour chacun taille, SHA-256 brut, SHA-1 de blob Git et résultat de
`hash-object --stdin` sans `-w`.

La première revue de l'implémentation au commit `e17524d8...` a rendu `FAIL`
sur l'ordre de ces deux phases : chaque payload était prévalidé immédiatement
après sa lecture. La micro-correction sépare désormais mécaniquement la boucle
qui lit/bufferise les huit payloads de la boucle suivante qui effectue les huit
prévalidations. Le test enregistre les événements et exige les dix lectures
source (contrat, seal, huit payloads) avant le premier `hash-object --stdin`.

## Frontière d'effet

Le runner vérifie et revalide :

- backend de refs exact `files` ;
- HEAD `75322bc6...`, symbolic HEAD, worktree propre et absence d'index lock ;
- absence de l'ACK et du processus du runner de detach ;
- snapshots byte-exacts des refs régulières, root refs/pseudorefs et index ;
- absence initiale des huit blobs cibles.

Le premier effet irréversible est ensuite exactement huit appels ordonnés à :

```text
git --no-replace-objects \
  --git-dir=/Users/amcarene/midi-worker/repository/.git \
  hash-object -w --stdin
```

Chaque retour doit être l'ID prévu. Le terminal relit les huit blobs et exige
leurs trois identités exactes, puis revalide backend, HEAD, symbolic HEAD,
worktree, lock, ACK/processus, refs et index. Un inventaire des chemins
d'objets impose exactement les huit nouveaux loose objects attendus et refuse
tout autre ajout, retrait ou dérive de métadonnées des objets préexistants.

Tout échec après le premier `-w` est terminal consommé : aucun retry, cleanup,
réparation, rollback revendiqué ou récupération automatique.

## Identités

```text
runner blob    80f0aeb847df2af6ccef7cd02242caa0dcfeacb0
runner size    18087
runner sha256  911bd1efecc223eb18a6e637190a18f990c856c6b7f1af31f9b3f46299170687

binding blob   f47f9d944a44472de6f339d93807e12bf5503e39
binding size   4604
binding sha256 9812a8de86eb02b63d149a1fa5b04ea9be8b4489f50cc8a4971536d262087e31

seal blob      08172eedbae3bc7502e07f607cdfc8a42f2c6e88
seal size      3840
seal sha256    1ab74c0180167a54d086a941dd4c79b2069a1a1e1693fb7d8e04c198191ff3ad
```

## Validation locale

- `py_compile` runner + test : réussi ;
- tests ciblés contrat + importer : `10/10` en `0,033 s` ;
- suite H27 complète : `524/524` en `94,095 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le runner reste dormant. Prochaine action unique : revue externe du runner,
de son binding et de son seal exacts. Aucun accès Mac ni import réel n'est
autorisé par ce lot.
