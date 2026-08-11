# H26 — planner dormant d'émission de l'activation

Statut : `PENDING_BATCH_EXTERNAL_REVIEW`. Le planner appelle les deux seal-loaders,
valide le candidat complet via le validateur approuvé, impose l'identité issuer et
l'heure UTC, puis retourne un plan immutable. Il ne crée aucun fichier.
