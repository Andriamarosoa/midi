# H27 Review 5B — exécution V1 consommée, échec bootstrap import

## Résultat définitif V1

La chaîne Review 5A V4 et son activation externe Review 5B avaient reçu `PASS`.
L'unique invocation Mac a ensuite créé son CLAIM avant d'échouer sur :

```text
ModuleNotFoundError: No module named 'src.polyphonic.harmonic_censoring_h27_contract'
```

L'exécution V1 est donc définitivement consommée, sans retry autorisé.

- execution ID : `8ecc2fbb-c48e-43a1-a712-682d8cf03de4` ;
- activation nonce : `19fbda53-fdf5-46c4-bdfa-973488119aba` ;
- activation SHA-256 : `6c9f54ff89ab4bab6fa10d45e6b18b4d472ac7907558841298ba0b62c4ccc0f3` ;
- claim SHA-256 : `9733d4d9b1a12a29b0456458b13436f1d1cb5ec26b5698ba359b4d89e1fc2625` ;
- terminal SHA-256 : `2545cf8e56495043565370248f271a47ea8617c5fafdee5ec0c9c0508f5419d1` ;
- COMPLETE SHA-256 : `baceb446a48172f5197d8cbcaef75b30d6a6dd143ab76619d15b7507d0ed98c9` ;
- terminal : `H27_EXECUTION_INCONCLUSIVE` ;
- P0/P1/P2 : `0/0/0` ;
- locked test et entraînement : non utilisés.

Les trois artefacts restent intacts sous
`/Users/amcarene/h27-admin-recovery-v2/science/review5-v1`.

## Lignée recovery locale

Le correctif place explicitement la racine du dépôt dans `sys.path` dès le
bootstrap du script, avant tout import `src.polyphonic`. Une régression lance le
script par son chemin absolu, depuis un CWD externe et sans `PYTHONPATH`, puis
exige l'import réel du module ayant échoué sur Mac.

La recovery utilise un nouvel output
`/Users/amcarene/h27-admin-recovery-v2/science/review5-recovery-v1`, un nouvel
acknowledgement `H27_REVIEW5_RECOVERY_SCIENTIFIC_EXECUTE` et une nouvelle
variable d'activation `H27_REVIEW5_RECOVERY_ACTIVATION_PATH`. Le contrat lie et
revérifie les SHA des claim/terminal/COMPLETE V1 consommés avant toute nouvelle
activation.

Cette étape est locale uniquement. Aucun nouveau SSH scientifique, activation,
CLAIM, P0/P1/P2, locked-test ou entraînement n'est autorisé avant binding, seal
et nouvelle revue stricte de la lignée recovery.
