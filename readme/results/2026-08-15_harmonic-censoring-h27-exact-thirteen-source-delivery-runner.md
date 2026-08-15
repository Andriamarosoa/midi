# H27 — runner de livraison des treize blobs source

## État

Review 2/5 implémentée en un seul lot. Aucun nouveau contrat, binding, seal ou
micro-gate n'est ajouté. Aucun SSH, ACK distant, objet, import, detach,
downstream, locked test ou calcul scientifique n'a été exécuté.

## Runner

`scripts/h27_deliver_exact_thirteen_source_odb_once.py` :

- exige Windows et zéro argument ;
- lit depuis l'ODB Git le receiver exact
  `9d32cac8ddb29e43975a6b82f5c1c39a91f93df4`, `119406` octets,
  SHA-256 `996c4539a357b13af65012de84ed836179389f111dd1849eb1ca165d15374000` ;
- supprime tout environnement `GIT_*`, puis réintroduit uniquement
  `GIT_TERMINAL_PROMPT=0` et `GIT_NO_LAZY_FETCH=1`, interdisant prompt et lazy
  fetch promisor avant la frontière SSH ;
- parse `EMBEDDED_OBJECTS` par AST/literal uniquement, sans exécuter le
  receiver, et exige treize paths et blob IDs uniques ;
- exécute au maximum une fois :

```text
ssh -T amcarene@100.89.128.87 env H27_SOURCE_ODB_EXACT_THIRTEEN_EXECUTE=1 /usr/bin/python3 -
```

- envoie les octets receiver exacts par stdin, `shell=False`, sans fichier
  temporaire, scp, sftp, rsync ou opération Git réseau ;
- applique un timeout de 900 secondes ; toute erreur après lancement est
  terminale/potentiellement consommée et n'entraîne aucun second SSH ;
- exige `returncode=0`, stderr vide et exactement une ligne JSON ;
- ferme le key set terminal et contrôle status, 13 IDs ordonnés, ODB source,
  HEAD/branche/refs/index/worktree inchangés, target ODB/import/detach/
  downstream/science/locked-test faux ;
- produit un résumé local terminal puis STOP.

Le receiver self-contained réalise lui-même le préflight Mac, exige les treize
objets absents, écrit exactement les treize loose blobs, les relit, vérifie le
delta ODB exact et l'absence de toute autre mutation. Aucun second SSH de
vérification n'est donc permis ou nécessaire.

## Tests

- tests ciblés après correction : `6/6` ;
- `py_compile` : réussi ;
- aucune connexion réseau dans les tests.

## STOP

STOP avant SSH. Prochaine action unique : review 2/5 du runner, du test et de
ce rapport dans un seul commit. En cas de `PASS`, une seule exécution réelle du
runner sera autorisée ; en cas d'échec après lancement, aucun retry automatique.
