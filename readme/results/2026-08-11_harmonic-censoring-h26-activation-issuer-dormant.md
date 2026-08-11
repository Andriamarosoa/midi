# H26 — issuer/publisher dormant de l'activation

Statut : `PENDING_BATCH_EXTERNAL_REVIEW`. Le module n'expose aucun adapter réel.
Il applique seulement, sur un adapter injecté, la séquence create-exclusive,
sync, rename-no-replace et directory-sync. Les tests emploient un faux filesystem;
aucune activation ou racine réelle n'est créée et aucun retry n'existe.
