# Smoke Mac — alignement absolu des partiels

## Statut

Terminé avec succès : ce smoke borné confirme que le contrat de labels harmoniques restauré est exécutable sur le Mac. Il ne constitue ni une validation officielle du décodeur, ni une sélection de seuil, ni une promotion du modèle.

## Provenance et intégrité

- Job Mac : `independent-note-alignment-smoke-fixed-cpu-20260804`.
- Commit exécuté : `a9cb13865a37e43d74a30a7093a3244306f88e40`.
- Mode : CPU forcé, un worker, queue 1, budget 60 min.
- Fin brute Mac : `2026-08-05T06:07:03Z`. L'horloge du Mac était avancée d'environ 11 h ; fin réconciliée approximative : `2026-08-04T19:07:03Z` (`2026-08-04T23:07:03+04:00`).
- Rapport brut local : `tmp/local/mac_results/independent-note-alignment-smoke-fixed-cpu-20260804/independent_note_train_gate.json`.
- SHA-256 du rapport : `e21e5930d0ae1deac2be33a2a9c8534111c717bc82f39f3f7ff2a1df5da983e1`.
- Artefact Keras temporaire : `independent_note_head.keras`, SHA-256 `d4d2101ff6f7f4da9cee4eb9ee6b24e5c347cc0493039a1618a6d02e730a0adc`.
- Configuration SHA-256 : `245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804`.
- Manifeste SHA-256 : `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7`.
- Sidecar de décalages fondamentaux SHA-256 : `8ebf0935e7024bf684adf0a08b6dc3e767af2da8e1040c08abbfbeff40969d55`.
- Checkpoint initial SHA-256 : `1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325`.
- `locked_test_used=false`; le préflight confirme 572 enregistrements train, 182 validation et 0 test. La validation officielle n'est pas chargée.

## Contrat exécuté

Les partitions internes train-only sont exactement `8192 / 2048 / 4096` (fit/dev/calibration), pour quatre époques. Seules les couches de la tête `independent_note` sont entraînables ; le backbone est gelé. Le budget n'a pas été dépassé. Aucun entraînement complet, export, test verrouillé ou live n'a été lancé.

Les pertes fit/dev passent respectivement de `0,2803 / 0,1293` à `0,0679 / 0,0570` entre les époques 1 et 4. Ce sont des mesures de smoke interne, non des métriques de transcription événementielle.

## Porte interne

Sur la cohorte calibration : 9 120 candidats supervisés, dont 7 378 notes indépendantes et 1 742 harmoniques seules. Le Brier de la tête est `0,02333`, meilleur que le prédicteur constant (`0,08031`) ; ces deux mesures sont pondérées par la fiabilité des labels. Au seuil interne sélectionné `0,01`, le rappel des notes indépendantes est `1,0` dans chacun des quatre corpus et le rappel pondéré de retrait des harmoniques seules est `8,43 %`. Ce dernier chiffre n'est pas un comptage brut de candidats rejetés.

Cette porte déclare explicitement nécessiter une validation appariée du décodeur : elle ne mesure pas le delta de faux NoteOn final. Le seuil `0,01` ne doit donc pas être promu.

## Contrôles

La parité du modèle sauvegardé est exacte : erreur absolue maximale `0,0`, accord des décisions `1,0`. Le smoke exerce avec succès le contrat de coordonnées restauré et confirme sa compatibilité avec le pipeline d'entraînement. Sa justesse sémantique repose aussi sur la formule revue et les tests ciblés du commit précédent : intervalle harmonique + décalage annotation fractionnaire vers classe MIDI arrondie + résidu du partiel mesuré.

## Décision

Le smoke est une réussite technique limitée. Aucune nouvelle évaluation, aucun entraînement complet, aucune sélection, aucun export, aucun live et aucune ouverture du test verrouillé ne doivent suivre avant revue ChatGPT et décision explicite sur la prochaine hypothèse.
