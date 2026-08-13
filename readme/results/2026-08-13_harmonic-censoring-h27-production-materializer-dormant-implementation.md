# H27 — implémentation dormante du futur matérialiseur de production

## Verdict du lot

Le matérialiseur de production demandé par la revue externe est implémenté
pour inspection, mais reste inconditionnellement non activable. Ce lot n'a
créé ni seal de ce nouveau blob, ni activation, authority, capability, claim,
population, payload ou index. Aucun calcul scientifique H27 n'a été exécuté.

Parent revu :
`7f049c8b9c92bf8f3ef70060c59bf5b726994288`.

## Séparation des deux modules

La référence dormante historique reste inchangée :

```text
src/polyphonic/harmonic_censoring_h27_materializer_dormant.py
Git blob 394f25a51f854cf629ef184694c4dcf1a45904b8
future activation execution target = false
```

Le nouveau target de production est distinct :

```text
src/polyphonic/harmonic_censoring_h27_production_materializer_dormant.py
Git blob e1b712c096a00d8ff225858b15387667f2b495ee
SHA-256 9b47955b0f16cbcf0b959812083468499d3c36a8b518a8a6adc7842a7513246a
```

Ces empreintes identifient l'implémentation proposée à la revue. Elles ne sont
pas un seal d'exécution et ne sont pas injectées dans le contrat d'activation
existant par ce lot.

## Frontière dormante

`H27ProductionMaterializationCapability` n'a ni constructeur ni issuer. La
fonction publique `materialize_h27_production_population()` appelle un refus
inconditionnel comme première instruction, avant d'inspecter NumPy, le plan ou
un chemin. Les copies et sérialisations d'une instance forgée sont également
refusées. Aucun registre mutable ne peut transformer une instance en
capability valide.

La destination n'est pas fournie par l'appelant. Les deux chemins POSIX sont
fixes :

```text
/Users/amcarene/h27-admin/population/.h27-synthetic-v1.staging
/Users/amcarene/h27-admin/population/h27-synthetic-v1
```

## Logique préparée sous la barrière

L'implémentation réconcilie administrativement :

```text
17 records baseline
107 records P2
124 records au total
```

Elle encode les recettes H27 autonomes, les enveloppes, le bruit PCG64, les
deux collisions rendues indépendamment puis comparées byte à byte, les huit
grilles P2, les quatre plans de masque role-major de 16 640 octets et les
exceptions exactes. L'ordre des identités est comparé à
`canonical_h27_record_identities()` avant toute publication future.

Chaque ligne future de l'index possède exactement, dans cet ordre :

```text
record_identity
record_directory
population_namespace
payload_sha256
candidate_pitch
active_pitches
proposal_hop_end
resolution_hop_end
cents
inharmonicity
```

La publication préparée écrit chaque payload en `O_EXCL`/`0600`, fsync les
fichiers, écrit l'index canonique en dernier, rehache les payloads, puis utilise
`renameatx_np(RENAME_EXCL)` et fsync le répertoire parent. Une staging
partielle reste non autoritative et n'est jamais effacée ou recyclée.

## Vérifications exécutées

```text
python -m py_compile
python -m unittest discover -s tests -p 'test_harmonic_censoring_h27*.py'
git diff --check
```

Résultat ciblé : `35 tests réussis`. Les tests du nouveau module couvrent le
refus avant tout accès, l'absence de registre/issuer, la non-copiabilité, la
forme exacte des chemins et champs, l'ordre déterministe d'un petit produit
cartésien administratif et l'encodage JSON canonique sur données toy.

Le chargement administratif du plan revu a aussi confirmé `124` identités,
de `baseline/H27-F-P01` à
`p2/P2_HOP_SHIFT_V1/H27-F-A07/shift_hops=0`, sans synthèse audio.

## État terminal

```text
nouveau module implémenté                   true
nouveau module revu extérieurement          false
nouveau module scellé                       false
contrat d'activation modifié                false
issuer / capability / claim                 absent
population / payload / index                absent
NumPy scientifique / FFT / NNLS             non exécutés
P0 / P1 / P2                                non exécutés
locked-test                                 non utilisé
training / calibration                      non exécutés
```

Prochaine action unique : revue externe du code et de ses empreintes. Toute
création de seal, binding d'activation, authority, capability, claim ou
matérialisation exige une autorisation séparée après cette revue.
