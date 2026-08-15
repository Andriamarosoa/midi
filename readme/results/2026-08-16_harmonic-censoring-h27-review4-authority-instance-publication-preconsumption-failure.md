# H27 Review 4 — arrêt pré-consommation du publisher authority-instance

## Verdict opérationnel

`PRECONSUMPTION_FAILURE_STOP_PENDING_EXTERNAL_REVIEW`.

Le commit `d296bfee703f9aa3b59904cf8a231a0a4091d3fe` avait reçu un
`PASS — exécutable`. L'autorisation couvrait un seul SSH et une seule invocation
du publisher exact, puis STOP quelle que soit l'issue.

## Source matérialisée et vérifiée

La source a été matérialisée hors du checkout cible dans :

```text
/Users/amcarene/h27-review4-authority-publisher-d296bfee/
└── h27_review4_authority_instance_artifact_publish_once.py
```

Le bootstrap LF sans retry a produit la preuve suivante avant l'invocation :

```text
size=27101
git_blob_sha1=799dc5bb305eaf2952ab3c95e60cdd633dfc8567
sha256=0688b959f6edc04b15282ff5c1ee6caec0e16c5e8dd537e1cedc786d7ac4dea7
```

Ces trois valeurs correspondent exactement à la source autorisée.

## Arrêt observé

Le runner a terminé avec un statut non nul et un traceback avant toute sortie
JSON terminale :

```text
execute()
→ preflight(registry_parent_fd)
→ open_verified_parent(DESTINATION.parent)
→ Path.resolve(strict=True)
→ FileNotFoundError: /Users/amcarene/h27-admin/activation
```

Le parent attendu de la destination n'existe pas :

```text
/Users/amcarene/h27-admin/activation
```

Dans le code revu, `open_verified_parent(DESTINATION.parent)` précède
strictement `consume_publication_authority(registry_parent_fd)`. La frontière
irréversible — création `O_CREAT|O_EXCL` du registre de publication — n'a donc
pas été atteinte par ce chemin observé. Cette conclusion repose sur le traceback
et l'ordre du runner exact; aucun second SSH de constat n'est lancé.

## Frontières conservées

- un seul SSH a été lancé ;
- aucun retry ou seconde invocation ;
- aucune création automatique du parent manquant ;
- aucun cleanup de la source matérialisée ;
- aucun statut de succès terminal ;
- aucun materializer, P0/P1/P2, science, locked-test, training ou calibration ;
- aucune répétition du constructor gate déjà consommé.

## STOP

La seule prochaine action est la revue externe de cette preuve
pré-consommation. Toute création du parent activation ou nouvelle invocation
nécessite une autorisation séparée et explicite.
