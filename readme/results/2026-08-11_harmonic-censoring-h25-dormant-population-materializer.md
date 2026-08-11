# H25 — materializer de population dormant

## Statut

`implementation_only_dormant_no_population_materialized`

Le module `harmonic_censoring_h25_population_materializer.py` implémente le
préflight standard-library-only, la synthèse déterministe, l’encodage `<f8`,
les JSON canoniques et le recomputer indépendant. Il n’importe pas NumPy au
chargement, ne possède aucun CLI et ne fournit aucun issuer de capability.
L’entrée de publication est donc fail-closed et ne peut pas matérialiser
`H25_SYNTHETIC_V1` dans ce commit.

Les tests utilisent seulement des enregistrements `TEST-ONLY-*` explicitement
hors population. Ils traversent les onze familles, les trois branches OOD et
les deux couleurs de bruit, vérifient deux générations identiques et
l’encodage de `133120` octets sans générer une des 36 fixtures scellées.

Aucun staging, index, receipt ou fichier de population H25 n’a été créé. Aucun
P0/P1/P2, donnée réelle, population prédécesseur, locked-test, modèle,
checkpoint, calibration ou entraînement n’a été utilisé.

La première revue a demandé deux durcissements. Le préflight compare désormais
explicitement macOS, Darwin, arm64, les deux formes de l’exécutable Python, le
venv root, CPU/GPU=0 et refuse tout framework GPU déjà importé avant NumPy. La
vérification finale reconstruit indépendamment index, provenance et receipt,
puis exige égalité de taille, SHA-256 et octets canoniques avant le rename.
