# H27 — publication terminale de la source creator revue

## Autorisation et préflight

La revue externe du lot dormant au HEAD
`242f7ae505763d69c6ffc14ea4454fded4a635f0` a rendu `PASS` et autorisé une
seule exécution du publisher terminal-parent exact :

```text
Git blob  60287a98eb0a7ff227bfcff49e72935b4a40dafc
octets    17187
SHA-256   c84a64767a2cf3912ae8aaca0d74accc634b1219b202825a74a36d0c72481859
```

Le dépôt Mac était propre et synchronisé exactement sur ce HEAD. L'exécution a
utilisé les octets de l'object database Git, jamais le fichier du worktree :

```sh
git cat-file blob 60287a98eb0a7ff227bfcff49e72935b4a40dafc \
  | H27_REVIEWED_CREATOR_SOURCE_PUBLISH_EXECUTE=1 python3 -
```

## Résultat exact

```json
{"status":"H27_REVIEWED_CREATOR_SOURCE_PUBLISHED_TERMINAL_SUCCESS","identity_count":139,"entrypoint_git_blob_sha1":"2091028d44bf9c8e1ab05b7d6656719ebc260832","entrypoint_size_bytes":44063,"entrypoint_raw_sha256":"0f0dd5867c82b1237736d03f48a6176171c4459b9106bca251ab53778092e42f","manifest_size_bytes":790,"manifest_raw_sha256":"1d21fc852bec98310f331b2122fb1b2005ab2fd4d2a1b0c5cdd270a1c6dc9a0f","closed_source_digest":"bc0d75ebf043018b677652b414d122d7dcbdd4c5a7fef0a38eef9b93b4c6d51d","creator_entrypoint_executed":false,"registry_opened":false,"science_or_locked_test":false}
```

Le code retour est `0`. La publication atomique contient exactement
`h27_reviewed_control_bundle_creator.py` et `manifest.json`; les bytes ont été
relus depuis leurs fd, le set fermé revérifié, puis le staging renommé avec
exclusion et fsync.

## Consommation et STOP

L'autorité publisher est consommée terminalement. Le blob `60287a98...` ne
doit jamais être réexécuté. Aucun retry, cleanup, repair ou republication n'a
eu lieu. Après le succès, le creator entrypoint publié n'a pas été exécuté ; le
registre n'a pas été ouvert, aucune autorité bundle n'a été réservée/consommée,
aucun bundle, materializer, science ou locked-test n'a été lancé.

La seule prochaine action est la revue externe de cette preuve terminale.
