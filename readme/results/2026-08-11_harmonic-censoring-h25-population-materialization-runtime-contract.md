# H25 — contrat de runtime, provenance et encodage de matérialisation

## Statut

`contract_only_population_not_materialized_external_review_required`

Ce changement répond uniquement à l’autorisation
`AUTHORIZED_TO_DEFINE_AND_COMMIT_H25_POPULATION_MATERIALIZATION_RUNTIME_PROVENANCE_AND_ENCODING_CONTRACT_ONLY`.
Il ne contient aucun materializer, aucune waveform et aucune exécution NumPy
scientifique.

## Entrées scellées

Le contrat lie les quatre fichiers déjà approuvés :

- contrat scientifique `ae837a647792c56c02a7d96a4328f62c1ecac03d0c0a839d59488c420cfff911` ;
- spécifications de fixtures `97295c09a0dc362a9337200ede62489e254fd5e548f36e2e170f21abb3b5ef6b` ;
- manifest population `33e21457240497322351275c3a82868d0eb06beb6676d6370ea85fae6933ba5f` ;
- manifest tests `58ce653325c785598fccd3cccffa7a77ab4944286df3baeb497bd20548544d29`.

La population reste exactement `36` IDs en ordre manifeste, avec
`12 positive / 12 negative / 12 ambiguous`. Aucun tri filesystem, omission,
substitution ou sélection caller n’est admis.

## Runtime de référence

La future matérialisation est liée à macOS `15.5` / Darwin `24.5.0`, arm64,
CPython `3.11.9`, NumPy `1.26.4`, CPU seul et un processus. Les cinq variables
de threads valent `1`; `PYTHONHASHSEED=0`, `LC_ALL=C`, `LANG=C` et `TZ=UTC`.

L’inspection administrative du runtime Mac a confirmé que l’extension NumPy
charge `libopenblas64_.0.dylib`, et non Accelerate. Le contrat lie le SHA-256
et la taille de l’extension `_multiarray_umath` et de la bibliothèque OpenBLAS.
Cette inspection n’a créé aucun tableau et n’a ouvert aucune donnée.

## Encodage canonique

Chaque waveform future contient `16640` valeurs IEEE-754 binary64 little-endian
brutes (`<f8`, C-order, sans header), soit exactement `133120` octets. Les
samples `0..8191` doivent être le bit-pattern positif `+0.0`; `-0.0`, NaN,
Inf et octets supplémentaires sont interdits.

Chaque fixture aura exactement trois fichiers :

1. `<ordinal>__<fixture_id>.f64le` ;
2. `<ordinal>__<fixture_id>.fixture.json` ;
3. `<ordinal>__<fixture_id>.target.json`.

Les JSON et JSONL utilisent UTF-8 sans BOM, clés triées, séparateurs compacts,
aucun NaN et un unique LF terminal. `population_index.jsonl` aura exactement
36 lignes et référencera les 108 fichiers dans l’ordre manifeste. Le receipt
fixe `P0/P1/P2=[0,0,0]`, `locked_test_used=false` et interdit toute lecture de
données réelles ou de populations prédécesseurs.

## Préflight et recomputation

Le futur préflight doit vérifier les hashes bruts avant parsing, les schémas,
les 36 IDs, le runtime complet, OpenBLAS, l’absence d’Accelerate et les chemins
absents avant tout import NumPy scientifique ou allocation de waveform. Toute
divergence est pré-claim, non consommatrice et ne crée aucun fichier de
population.

Une future exécution autorisée devra produire dans un staging privé, fsync,
reouvrir et rehacher chaque fichier, puis régénérer indépendamment les 36
fixtures avec des générateurs PCG64 frais. Tous les octets waveform/spec/target
doivent être identiques avant le rename atomique. Aucune identité byte-for-byte
cross-runtime n’est revendiquée.

## Limite

Ce contrat ne définit ni autorisation, ni capability, ni claim, ni seal, ni
implémentation. Même une future matérialisation réussie ne constituerait aucune
preuve P0/P1/P2 et n’autoriserait ni test, ni modèle, ni entraînement.
