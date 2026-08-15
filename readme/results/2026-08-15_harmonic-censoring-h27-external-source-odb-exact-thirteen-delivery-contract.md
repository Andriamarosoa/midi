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

## Identités du contrat

```text
contract blob    e37a417c279555796f50f31af78659f5dc3dc299
contract size    9482
contract sha256  4ba52b337a38cce65997b683ff0ecb0011df22033e9490f992914d1c557554b7
```

```text
seal blob        ed64996535b7d2b14d758c9839c738f42c5d7cab
seal size        4091
seal sha256      50c22c4d640df576fd127c8518d9eb2a65757cf0e4cf8390bf26221dabd4b605
```

## Validation locale

- tests ciblés : `5/5` en `0,010 s` ;
- suite H27 complète : `530/530` en `90,696 s` ;
- `py_compile` et `git diff --check` : réussis avant commit.

## STOP

Le receiver n'existe pas encore et aucun transport n'est autorisé. Prochaine
action unique : revue externe du contrat et de son seal exacts.
