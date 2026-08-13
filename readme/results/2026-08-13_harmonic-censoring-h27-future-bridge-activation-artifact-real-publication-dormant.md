# H27 — frontière dormante de future publication réelle

Date : 2026-08-13

## Portée

Cette étape suit le verdict externe `PASS` du binding administratif au commit
`285daa719a38884cca1dadb3571c6cb7bba2cacf`. Elle ajoute un module Python
distinct et son test synthétique. Elle ne crée aucune destination et n’exécute
aucune opération réelle de publication.

## Implémentation bornée

Le module :

- vérifie les octets exacts du binding administratif et de son seal ;
- recharge les deux racines contrat/seal, les quatre artefacts du simulateur et
  les 48 upstream ;
- recalcule blob Git, taille et SHA-256 des 54 identités uniques avant toute
  sonde ;
- réutilise le payload canonique strict déjà revu ;
- exige les 17 exigences fail-closed du contrat, dans l’ordre exact ;
- exige une destination absente ;
- consomme le one-shot immédiatement avant la première sonde create-exclusive ;
- impose que toutes les sondes create/write/flush/fsync/visibility/reopen restent
  sans effet ;
- rend succès et erreur post-consommation terminaux sans retry.

Le nouvel edge public
`publish_h27_future_bridge_activation_artifact_real` reste exactement
`().__getitem__`. Avec les sept prédécesseurs, huit edges sont fermés.

## État observé par les tests

- `verified_identities=54` ;
- `destination_path=null` ;
- `artifact_created=false` ;
- `artifact_written=false` ;
- connexions fausses ;
- `materializer_invocations=0` ;
- `science_invocations=0` ;
- `terminal=true`.

Le module n’importe ni n’appelle directement `os.open`, `O_EXCL`,
`write_bytes` ou NumPy. Les tests n’utilisent que des sondes injectées qui
doivent toutes répondre qu’aucun effet n’a eu lieu.

## Vérifications locales

- tests ciblés : `7/7` en `0.563 s` ;
- suite H27 avec le venv du dépôt : `289/289` en `46.577 s` ;
- `py_compile` : PASS ;
- `git diff --check` : PASS.

Aucun audio, population, TensorFlow, locked-test ou calcul scientifique n’est
utilisé.

## STOP

Le module exact attend une revue externe de code. Toute destination réelle,
exécution de `open/write/O_EXCL/fsync/rename`, création d’artefact, connexion,
authority/claim/capability, invocation du materializer ou science reste
interdite.
