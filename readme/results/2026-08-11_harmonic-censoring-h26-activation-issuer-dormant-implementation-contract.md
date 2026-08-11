# H26 — contrat d'implémentation dormante de l'issuer

Statut : `PENDING_BATCH_EXTERNAL_REVIEW`.

Ce contrat additif lève l'ancienne interdiction d'implémenter l'issuer uniquement
pour du code dormant et des tests avec adaptateurs factices. Son invocation,
la création d'une activation, le choix d'une racine et toute opération réelle
sur le filesystem restent interdits. Aucun contrat antérieur n'est modifié.
