# H26 — implémentation dormante du qualificateur runtime

## Portée

Cette étape applique uniquement :

```text
AUTHORIZED_TO_IMPLEMENT_H26_DORMANT_MATERIALIZATION_RUNTIME_QUALIFIER_WITH_CORRECTED_CONTRACT_BINDING_ONLY
```

Le parent direct est `89cc0659de3afb5194afcf8e7ea9ac6c300e1f92`.
Le changement est limité au module dormant, à son fichier de tests artificiels,
au présent rapport et au résumé global. Aucun fichier `configs/` n'est modifié.

## Binding corrigé

Le premier token du pilote indiquait par erreur le blob `c1e503ab…`, qui est
celui du contrat rejeté au commit `7f2bdf2f…`. Le test du loader a échoué avant
toute autre action. La preuve Git a été soumise au pilote, qui a supersédé ce
token et confirmé le binding exact :

```text
contrat runtime approuvé   89cc0659de3afb5194afcf8e7ea9ac6c300e1f92
blob Git réel              c3a021872dfd3a99b6977fdef1302d5edc755fea

contrat authority          236a84b4eb928b102bc1548fb2b32d1bffda2e63
blob authority             dd5bcbff325e74f74e7bde4d425a11ac84aa264d

implémentation revue       60b8d90bcbb5fb6e3a82d839bae706a359ab310e
blob materializer          2991c69db8a8816d0261c1fb6bb4e339e9408c11
```

Le loader refuse explicitement l'ancien blob, un mauvais commit, un mauvais
blob, toute mutation des octets, les clés JSON dupliquées, les constantes non
finies et le JSON tronqué. Il calcule le blob Git depuis les mêmes octets lus;
seule la normalisation texte Git CRLF vers LF est admise pour un checkout
Windows, et un caractère CR isolé est refusé.

## Architecture dormante

Le module sépare strictement deux plans :

```text
observation réelle, capability obligatoire et actuellement inaccessible
                                  ↓
validation/classification pure sur objets immuables artificiels
                                  ↓
record déterministe construit sans statut fourni par l'appelant
```

Le loader retourne une représentation gelée du contrat, de l'identité runtime
et des dix variables de contrôle. Les observations utilisent une identité à
sept champs, trois preuves binaires séparées et une liste immuable de variables
d'environnement.

La capability `H26RuntimeQualificationCapability` refuse sa construction. Il
n'existe ni issuer, factory, singleton, token ou variable d'environnement pour
l'obtenir. Même un objet forgé via `object.__new__` est refusé avant le premier
appel lazy à `importlib.import_module("numpy")`. Le module n'importe jamais
NumPy au chargement.

## Classification et record

La classification pure produit exactement :

- preuve requise inaccessible ou mal formée →
  `H26_MATERIALIZATION_RUNTIME_QUALIFICATION_INCONCLUSIVE_CONSUMED`;
- preuves comparables complètes et au moins un mismatch →
  `H26_MATERIALIZATION_RUNTIME_DISQUALIFIED`;
- preuves complètes et toutes égalités exactes →
  `H26_MATERIALIZATION_RUNTIME_QUALIFIED`.

Seules les dix clés preregistrées sont comparées. Une clé absente ou incorrecte
disqualifie; `PATH`, `HOME` et toute autre variable non listée sont ignorées.
Les preuves exécutables valides sont requises sans inventer de SHA attendu;
les tailles et SHA NumPy/OpenBLAS sont comparés exactement au contrat.

Le builder n'accepte aucun `terminal_status` de l'appelant. Il crée en mémoire
un record `H26_MATERIALIZATION_RUNTIME_QUALIFICATION_RECORD_V1`, conserve
`observed_runtime` à ses sept champs canoniques, projette séparément les dix
variables observées et maintient les preuves binaires à plat. Le JSON est
déterministe, fini et sans auto-SHA. Le writer atomique futur exige la
capability inaccessible avant toute création de fichier.

Aucun vrai record n'est produit par cette étape.

## Validation artificielle autorisée

Commandes exécutées :

```text
python -m py_compile \
  src/polyphonic/harmonic_censoring_h26_runtime_qualification.py \
  tests/test_harmonic_censoring_h26_runtime_qualification_dormant.py

python -m unittest \
  tests.test_harmonic_censoring_h26_runtime_qualification_dormant
```

Résultat final : `17 tests` réussis en `0,011 s`.

Les cas couvrent notamment le blob corrigé accepté, l'ancien blob refusé, les
croisements commit/blob, capability directe et forgée, absence d'import NumPy,
observation artificielle exacte, mismatches Python/Darwin/NumPy/BLAS, clés
d'environnement absentes ou fausses, preuves manquantes/inaccessibles,
représentation runtime canonique, statut dérivé, sérialisation déterministe,
auto-SHA refusé et writer inaccessible avant création.

Le premier échec sur `c1e503ab…` était un échec correct de garde et non une
qualification. Aucun observer réel, NumPy, BLAS, runtime secondaire ou actif
scientifique n'a été ouvert.

## Frontière maintenue

Toujours aucun issuer, authority, capability utilisable, claim, seal,
destination réelle, runtime record réel, SHA de record, qualification du
runtime, matérialisation, waveform, population, index, P2 record, P0/P1/P2,
donnée réelle, modèle, entraînement, calibration ou locked-test.

Une nouvelle revue externe de cette seule implémentation dormante est
obligatoire. Son approbation ne constituera aucune autorisation de qualifier le
runtime réel.
