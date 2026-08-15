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
runner blob    83160f4b80e623a09f646e910d63069e26f6cc79
runner size    17726
runner sha256  c29dd8ff53fec81e55228d9b7ec33643004fe4f0edb7393a226a2b94577d45bc

binding blob   606be5191e3390110be9fc6ec73d161f34d61172
binding size   4604
binding sha256 9ad5199c0d0fbadf63dd4daef03eb9c240e35d8a87bc1e1234df20c0a1ad24ee

seal blob      43bd762e7e33327f5dc9a06ef7ab80c8898f8b19
seal size      3840
seal sha256    223215c40859b6412342c92e31d032fd79180b8e612182f7298384f59fc05f79
```

## Validation locale

- `py_compile` runner + test : réussi ;
- tests ciblés contrat + importer : `10/10` en `0,030 s` ;
- suite H27 complète : `524/524` en `82,721 s` ;
- `git diff --check` : réussi avant commit.

## STOP

Le runner reste dormant. Prochaine action unique : revue externe du runner,
de son binding et de son seal exacts. Aucun accès Mac ni import réel n'est
autorisé par ce lot.
