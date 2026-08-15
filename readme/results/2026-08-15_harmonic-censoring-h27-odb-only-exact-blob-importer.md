# H27 — importer dormant one-shot des huit blobs Git exacts

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont initiale : PASS de `dffce1f9a144be60968b7912e99c761ec058ee0f`
Correction Git 2.39 autorisée par : PASS de `5abab29c2687d41e54cc2e63f99f97afb87f0166`

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

- backend de refs `files` prouvé par repository format exact `0`, absence
  exacte de `extensions.refStorage`, `.git/refs` réel non-symlink et
  `.git/reftable` absent ;
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
runner blob    4520d69b04eec017f90a6a1c717519e6a303538d
runner size    18954
runner sha256  5fee4f5d08ff7640a5e1542f7dd6aeb873a03d0e8a38d35335b8870552d645af

binding blob   0bba45c130c9f83ace74a91d92e48d53525740e7
binding size   5067
binding sha256 0d751be65f812678ddc59a7f57b3af68d215d626c93aebdbeb65bfd417aa8077

seal blob      68cdc76688cee5364b54a8febc6b2d9a46e0994e
seal size      4314
seal sha256    e45c26cddd2335fc4236dd62d0011a5208104d9d46e79e4241aeb0bc5e0530aa
```

## Validation locale

- `py_compile` runner + test : réussi ;
- tests ciblés contrat + importer : `11/11` en `0,222 s` ;
- suite H27 complète : `525/525` en `85,741 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le runner reste dormant. Prochaine action unique : revue externe du runner,
de son binding et de son seal exacts. Aucun accès Mac ni import réel n'est
autorisé par ce lot.
