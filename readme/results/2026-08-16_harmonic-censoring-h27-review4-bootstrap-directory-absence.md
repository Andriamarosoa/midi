# H27 Review 4 — arrêt bootstrap avant mutation

## Autorisation

La revue externe de `78a704337b2c81c57f7e087f5ab2c12a8633189d`
a rendu `PASS` et autorisé un unique bloc SSH : matérialisation hors checkout des
six artefacts scellés, vérification de leurs identités avant ACK, runner one-shot,
puis STOP.

## Résultat de l'unique tentative

Le SSH unique vers `amcarene@100.89.128.87` a terminé avec `rc=1` avant toute
matérialisation :

```text
stat: /Users/amcarene/h27-admin/review4: stat: No such file or directory
LOCAL_SSH_RC=1
```

Le bootstrap exigeait que ce répertoire existe déjà, soit régulier/non-symlink,
appartienne à l'utilisateur courant et soit en mode `0700`. Le contrat de revue
autorisait la matérialisation *sous* ce chemin, mais le script bootstrap n'en a
pas créé le parent.

## Frontière de consommation

L'échec a eu lieu avant :

- tout décodage base64 et toute création de fichier;
- tout export de `H27_REVIEW4_MATERIALIZATION_EXECUTE`;
- toute invocation Python du runner;
- toute création d'authority ou claim;
- tout staging ou population;
- toute science, P0/P1/P2, locked-test ou entraînement.

Cette tentative SSH n'est pas relancée automatiquement. La prochaine action
nécessite une revue explicite d'un bootstrap corrigé qui crée exactement
`/Users/amcarene/h27-admin/review4` en `0700`, le réouvre sans suivre de lien,
vérifie owner/mode, puis reprend les mêmes six octets scellés. Le runner,
materializer, bindings et seals restent inchangés.
