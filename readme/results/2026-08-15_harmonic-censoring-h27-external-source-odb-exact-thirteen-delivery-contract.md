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

## Identités du contrat

```text
contract blob    659b9ef28b6e69516838fad7f6d9c9488b0d8ece
contract size    10312
contract sha256  f60657abee4b5d647dff607bd5b6de30115f612fbf631e88dc1b22aa37552a3e
```

```text
seal blob        72d6019e828cf4efcac5a674806710bf63459c5c
seal size        4556
seal sha256      677d6aa55eb866b7f2db2825c3dda04be35eaf03a65c4d5383bb1355a51e594c
```

## Validation locale

- tests ciblés : `6/6` en `0,014 s` ;
- suite H27 complète : `531/531` en `94,395 s` ;
- `py_compile` et `git diff --check` : réussis avant commit.

## STOP

Le receiver n'existe pas encore et aucun transport n'est autorisé. Prochaine
action unique : revue externe du contrat et de son seal exacts.
