# H27 — exécution terminale du creator leaf

## Autorisation

La revue externe de `406f04db0c3315b82ad91f02ffb71a425512f61b`
a rendu `PASS` et autorisé une seule exécution réelle du runner Git blob exact
`848c65d0039b0ef60a5752835ce4a9b84be47c73`, exclusivement pour créer
`/Users/amcarene/h27-admin/creator`.

## Préflight opérationnel

- branche Mac : `codex/independent-note-neural-v2` ;
- HEAD Mac exact : `406f04db0c3315b82ad91f02ffb71a425512f61b` ;
- worktree Mac propre ;
- aucune observation préalable de la cible par Codex ;
- exécution des octets de l'object database Git, sans fallback vers le fichier
  du worktree.

Commande one-shot :

```sh
git cat-file blob 848c65d0039b0ef60a5752835ce4a9b84be47c73 \
  | H27_CREATOR_LEAF_CREATE_EXECUTE=1 python3 -
```

## Résultat terminal exact

```json
{"status":"H27_CREATOR_LEAF_CREATED_TERMINAL_SUCCESS","verified_identity_count":7,"parent_path":"/Users/amcarene/h27-admin","parent_device":16777233,"parent_inode":1445438,"target_path":"/Users/amcarene/h27-admin/creator","target_device":16777233,"target_inode":1447071,"publisher_authorization_consumed":false,"source_published":false,"creator_entrypoint_executed":false,"registry_opened":false,"control_bundle_created":false,"science_or_locked_test":false}
```

Le processus retourne le code `0`. Le parent correspond encore exactement au
tuple terminal scellé. Le leaf créé est un répertoire réel vérifié par fd et
entrée nommée, sur device `16777233`, inode `1447071`.

## Consommation et STOP

L'autorité creator-leaf est consommée terminalement. Le runner exact ne doit
jamais être rejoué. Aucun retry, cleanup, repair ou recreation n'a eu lieu.
Après le résultat, aucun publisher, source, creator entrypoint, registre,
bundle, materializer, science ou locked-test n'a été exécuté.

La seule prochaine action est la revue externe de cette preuve terminale.
