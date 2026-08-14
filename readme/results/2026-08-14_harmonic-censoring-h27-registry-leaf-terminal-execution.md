# H27 — exécution terminale du creator registry-leaf

## Autorisation

La revue externe de la micro-correction
`57e3f5be80ed12192776425799c58a7a4305ba6c` a rendu `PASS` et autorisé une
seule exécution réelle du runner exact blob Git :

```text
ca93c383d8cc61a6f3869318f1e462ab82a1c92a
```

uniquement pour créer `/Users/amcarene/h27-admin/registry`.

## Préflight

Le Mac a été synchronisé proprement sur le commit PASS exact
`57e3f5be80ed12192776425799c58a7a4305ba6c`. Le worktree était propre. Aucun
chemin administratif cible n'a été observé hors du runner.

Les bytes ont été fournis exclusivement depuis l'object database Git :

```text
git cat-file blob ca93c383d8cc61a6f3869318f1e462ab82a1c92a
| H27_REGISTRY_LEAF_CREATE_EXECUTE=1 python3 -
```

Zéro argument a été transmis.

## Résultat terminal

```json
{"status":"H27_REGISTRY_LEAF_CREATED_TERMINAL_SUCCESS","verified_identity_count":7,"parent_path":"/Users/amcarene/h27-admin","parent_device":16777233,"parent_inode":1445438,"target_path":"/Users/amcarene/h27-admin/registry","target_device":16777233,"target_inode":1448669,"admin_root_creation_authority_consumed":true,"publisher_authority_consumed":true,"registry_jsonl_observed":false,"registry_opened":false,"authority_reserved":false,"authority_consumed":false,"creator_entrypoint_executed":false,"control_bundle_created":false,"constructor_or_materializer_executed":false,"science_or_locked_test":false}
```

Le code retour SSH/runner est `0`. Les sept identités ont été rehashées avant
l'observation du parent. Le parent est resté device `16777233` / inode
`1445438`; le leaf créé est device `16777233` / inode `1448669`.

## Consommation et STOP

L'autorité registry-leaf est terminalement consommée. Le blob `ca93c383...`
ne doit jamais être rejoué. Aucun retry, cleanup, repair ou recreation n'a eu
lieu.

STOP immédiat après le résultat : le JSONL
`h27-control-bundle-creation-authority-v1.jsonl` n'a été ni observé, ni ouvert,
ni créé. Creator entrypoint, réservation, consommation d'autorité bundle,
control bundle, constructor, materializer, science et locked-test restent faux.

La seule action suivante est la revue externe de cette preuve terminale.
