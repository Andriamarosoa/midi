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

## Exécution consommée

La correction `GIT_NO_LAZY_FETCH=1` au commit `21b4da72...` a reçu `PASS final`
de la Review 2/5. Le runner exact blob `76cd11c4...` a été chargé depuis Git et
exécuté une seule fois.

Résultat local :

```text
elapsed = 1.794 s
SSH returncode = 1
ConsumedDeliveryFailure: single SSH returned 1; retry forbidden
```

Aucun second SSH, retry, cleanup ou receiver n'a été lancé. Le runner avait
bien capturé stdout/stderr, mais son chemin RC non nul ne les inclut ni ne les
persiste avant de lever. Leur contenu et même leurs digests sont donc perdus.
L'état distant est classé inconnu : zéro, une partie ou les treize objets
peuvent être présents. Aucun import cible, detach, downstream, locked test ou
science n'a été exécuté.

Review 3/5 est bloquée jusqu'à une décision externe. Les seules suites sûres
sont l'arrêt terminal ou une autorisation explicite d'observation read-only
séparée des treize OIDs et de l'état Git source ; la relance du receiver reste
interdite.

## Observation read-only consommée

La revue externe a ensuite autorisé exactement une observation SSH séparée,
strictement read-only, sans ACK, receiver, écriture d'objet, reset, mutation de
ref/index/worktree, import ou cleanup. Elle devait contrôler l'état Git source
et lire localement les treize blobs avec `GIT_NO_LAZY_FETCH=1`.

Cette observation a été exécutée une seule fois. Résultat terminal :

```text
status = H27_READ_ONLY_OBSERVATION_CONSUMED_FAILURE
elapsed = 1.487 s
ssh_returncode = 1
stdout_size = 0
stdout_sha256 = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
stderr_size = 155
stderr_sha256 = edb72e4982741a81d3913b389b674abe820da9db57f2e10b51b2e76a6d266ccd
```

Le contenu stderr n'a pas été exposé par l'enveloppe terminale, et stdout est
vide. L'observation ne fournit donc aucune preuve sur la présence des treize
objets ni sur l'état Git distant. Conformément à son contrat, elle n'est pas
relancée. Le receiver reste consommé, aucun second SSH n'est autorisé, Review
3/5 ne peut pas commencer et ce chemin H27 est placé en STOP terminal jusqu'à
une nouvelle décision de conception explicitement revue. Aucun import cible,
downstream, locked test, entraînement, calibration ou calcul scientifique n'a
été effectué.
