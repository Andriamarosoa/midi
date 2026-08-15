# H27 — contrat d'apport exact de treize blobs dans l'ODB source externe

Date : 2026-08-15
Branche : `codex/independent-note-neural-v2`
Autorisation amont : PASS de `c0bb8d20862f80cabc72ea64a5d437750b7c12e8`

## Portée

Contrat déclaratif, external seal, tests structurels et documentation seulement.
Aucun accès Mac, SSH, ACK, transport, écriture ODB, import cible, detach,
registre, autorité, creator, bundle, matérialisation, science ou locked test.

## Problème fermé par le contrat

Le préflight Mac a prouvé que l'ODB externe `/Users/amcarene/midi/.git` ne
contient aucun des treize blobs dont l'importer cible a besoin. Un fetch/pull,
push de ref, bundle, pack ou transfert de fichiers introduirait des objets ou
des mutations non bornés.

Le contrat définit donc un futur receiver Python auto-contenu, revu comme un
blob Git exact et transmis uniquement par stdin à :

```text
ssh -T amcarene@100.89.128.87 \
  env H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1 \
  /usr/bin/python3 -
```

Les treize payloads bruts seront intégrés au receiver sous forme base64
canonique. Aucun fichier receiver ou payload ne sera créé sur le Mac. Avant le
transport, le futur orchestrateur devra rehacher le receiver et relire les
treize blobs exclusivement depuis l'ODB Git du commit Windows exact
`c0bb8d20...`, puis prouver leur égalité avec le binding du receiver.

## Frontière distante

Le receiver futur devra, avant toute écriture :

- décoder, bufferiser et valider en mémoire les treize objets ;
- vérifier Darwin, l'ACK, zéro argument, les realpaths et le backend `files` ;
- imposer HEAD `eaed599a...`, symbolic HEAD, worktree propre et lock absent ;
- capturer refs régulières, root refs/pseudorefs, index et inventaire ODB ;
- vérifier que les treize blobs sont absents.

Le premier effet futur sera exactement treize appels ordonnés à :

```text
git --no-replace-objects \
  --git-dir=/Users/amcarene/midi/.git \
  hash-object -w --stdin
```

Le contrôle terminal exigera les treize blobs byte-exacts, exactement treize
nouveaux chemins loose-object, et aucune dérive de ref, HEAD, index, worktree
ou objet préexistant. Une interruption après l'ACK distant ou une écriture
partielle sera terminale consommée, sans retry, cleanup, réparation ou
rollback revendiqué.

La première revue de `aafb1d8a...` a rendu `FAIL` sur l'environnement Git :
`GIT_OBJECT_DIRECTORY`, `GIT_COMMON_DIR` ou un autre redirecteur hérité aurait
pu détourner l'écriture malgré `--git-dir`. La correction impose maintenant à
chaque subprocess Git, côté sender et receiver, de supprimer toute variable
dont le nom commence par `GIT_`, puis de réintroduire uniquement :

```text
GIT_TERMINAL_PROMPT=0
GIT_NO_LAZY_FETCH=1
```

Tout autre `GIT_*`, notamment les redirecteurs d'ODB, alternates, common-dir,
index, worktree ou configuration, est interdit. Les chemins Git sont choisis
uniquement par les arguments littéraux des commandes scellées.

La seconde revue de `7e238fca...` a rendu `FAIL` parce que la commande sender
`cat-file` ne contenait pas encore de sélecteur de dépôt littéral et dépendait
donc du CWD. Toutes les commandes Git sender doivent maintenant commencer par :

```text
git --no-optional-locks --no-replace-objects \
  -C C:\Users\user\Desktop\midi\tmp\local\worktrees\independent-note-neural-v2
```

La lecture de chaque payload est scellée comme ce préfixe suivi de
`cat-file blob <expected-sha1>`. Toute sélection implicite par CWD est
interdite.

## Identités du contrat

```text
contract blob    83fba2bc54bb22712680453bc3253b85aca50ca4
contract size    10717
contract sha256  c538c3567f46993f8a1a420a272db552d07ea7e2f2362142700d9670b31f0df2
```

```text
seal blob        b579a3604e1aa08d9485d10585ebba24febdf446
seal size        5112
seal sha256      5c6535d8178f03cee8f91e14fac448567603900cca2e1261758e10ae13166daa
```

## Validation locale

- tests ciblés : `7/7` en `0,010 s` ;
- suite H27 complète : `532/532` en `94,411 s` ;
- `py_compile` et `git diff --check` : réussis avant commit.

## STOP

Le receiver n'existe pas encore et aucun transport n'est autorisé. Prochaine
action unique : revue externe du contrat et de son seal exacts.
