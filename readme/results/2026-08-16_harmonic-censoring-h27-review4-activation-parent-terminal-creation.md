# H27 Review 4 — création terminale du parent activation

## Verdict opérationnel

`H27_REVIEW4_ACTIVATION_PARENT_CREATION_TERMINAL_SUCCESS_STOP`.

La revue externe de l'arrêt pré-consommation a confirmé que l'autorité de
publication n'était pas consommée. Elle a autorisé une seule action séparée :
créer le parent `activation` en `0700`, puis STOP sans publisher.

## Action unique

Une unique invocation Python distante a exécuté :

```text
open /Users/amcarene/h27-admin O_DIRECTORY|O_NOFOLLOW
→ fstat == stat du parent
→ absence relative de activation
→ mkdir("activation", 0700, dir_fd=parent_fd)
→ open relatif activation O_DIRECTORY|O_NOFOLLOW
→ directory + inode/dev + mode 0700 exacts
→ fsync(parent_fd)
→ STOP
```

Le résultat terminal exact est :

```json
{"status":"H27_REVIEW4_ACTIVATION_PARENT_CREATION_TERMINAL_SUCCESS_STOP","path":"/Users/amcarene/h27-admin/activation","mode":"0700","publisher_invoked":false,"destination_observed":false,"publication_registry_created":false,"materializer_or_science":false}
```

## Frontières conservées

- aucune utilisation de `mkdir -p` ;
- aucun chmod ou réparation d'une entrée préexistante ;
- aucun accès à `h27-materialization-v1.json` ;
- aucune création du registre de publication ;
- aucun lancement du publisher dans le même SSH ;
- aucun materializer, P0/P1/P2, science, locked-test, training ou calibration ;
- aucune répétition du constructor gate consommé.

## STOP

La prochaine action est uniquement la revue externe de cette preuve. Une
nouvelle invocation du publisher exact exige une autorisation séparée.
