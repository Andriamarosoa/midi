# AGENTS.md — Règles pour assistants IA

## Règles générales

1. Lire les documents V5 avant toute modification.
2. Ne jamais modifier le schéma NPZ sans mettre à jour `DATASET.md`.
3. Ne jamais introduire d’accès disque dans `model.py`.
4. Ne jamais mélanger train, validation et test.
5. Ne jamais changer le split officiel sans justification documentée.
6. Toute modification doit être testable indépendamment.
7. Toute nouvelle dépendance doit être documentée.
8. Les scripts doivent fonctionner sous Windows PowerShell.
9. Les commandes PowerShell doivent être fournies sur une seule ligne.
10. Ne pas créer de nouveaux fichiers quand une modification ciblée suffit.

## Qualité

- utiliser des types explicites ;
- valider les entrées ;
- fournir des messages d’erreur utiles ;
- éviter les constantes magiques ;
- conserver la compatibilité Python 3.9 ;
- éviter les `Lambda` Keras non sérialisables.

## Validation minimale

Avant de considérer une tâche terminée :

```text
python -m compileall src/v5
```

Puis exécuter les tests associés.

## Changements de performance

Toujours fournir :

- temps avant ;
- temps après ;
- mémoire avant ;
- mémoire après ;
- impact top-1/top-3 si applicable.
