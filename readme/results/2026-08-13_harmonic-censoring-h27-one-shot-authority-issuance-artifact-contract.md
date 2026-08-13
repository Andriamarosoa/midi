# H27 - contrat du futur artefact d'issuance one-shot

Le commit `630b81d1ad8f13b21e79778d512083201da2fc60` est revu PASS.
Le contrat lie quatre artefacts one-shot et 68 identites amont, soit 72 chemins
rehashes. Il definit seulement le format et les preconditions; aucun artefact,
authority, claim, capability, destination ou calcul n'est cree ou ouvert.

La revue externe initiale de `007614a4` conclut FAIL : le schema n'etait pas
ferme et le compteur 72 ne liait pas cryptographiquement les identites. La
correction fixe l'ordre et les types des neuf champs, interdit tout champ
supplementaire, atteste l'issuer exact, derive l'artifact_id, impose nonce
hex64 unique et timestamp RFC3339 UTC strict, et lie le manifeste canonique des
72 identites au SHA-256 `8861519a...`. Des tests adversariaux couvrent chaque
contrainte. Aucun artefact reel n'est produit.

La seconde revue de `0d528cb9` conclut FAIL sur l'unique issuer `h26-...`,
incompatible avec deux sources H27 scellees. La correction utilise exactement
`h27-execution-codex-mac-primary`, le relit depuis
`fixed_paths_and_counts.issuer_identity` du contrat de composition H27 et
rejette explicitement l'ancien issuer H26.
