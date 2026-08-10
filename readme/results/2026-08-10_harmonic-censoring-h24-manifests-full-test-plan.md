# H24 — manifests et plan de test complet, sans synthèse

## Autorisation

La revue externe du correctif `ab2ebc4d…` approuve le contrat successeur H24 et
autorise uniquement la définition des manifests et du plan complet :

```text
AUTHORIZED_TO_DEFINE_H24_MANIFESTS_AND_FULL_TEST_PLAN_CONTRACT_ONLY
```

Ce commit ne matérialise aucune fixture et n’implémente ni evaluator ni oracle.

## Bindings canoniques

```text
contrat successeur H24
configs/harmonic_censoring_h24_successor_contract.json
8123 octets
184d3847a594ffaca263b45befe70d1f5aa63ade0a0ef599d969ba044f4e680a

manifest de population
configs/harmonic_censoring_h24_population_manifest.json
423453 octets
52c88c74c837ad3c6109be466df38bac862e10d93c187fe60e8c5da30bd4b02b

manifest de tests corrigé
configs/harmonic_censoring_h24_test_manifest.json
306434 octets
de8ea9c5c0f7d41ce19a5e0dfbbf323474a8e3a05a74dd9656fda5c52cf1dbae

contrat de liaison corrigé
configs/harmonic_censoring_h24_manifest_binding_contract.json
1982 octets
0ffbd5681be1bd9c55d43e8435af472c58d41e4f2c766cc449d8fd03272ffc77
```

Les quatre fichiers sont forcés en LF par `.gitattributes`.

## Population spécifiée

La cardinalité est redérivée explicitement :

```text
6 spécifications de base
+ 169 variantes one-factor fermées
= 175 spécifications H24
```

Le nombre est numériquement identique à H23, mais aucun ID, seed, waveform,
résultat ou autorisation n’est hérité. Chaque ID commence par `H24-F-`; le
mapping vers la spécification antérieure est bijectif et auditable. Les seeds
futurs utilisent un nouveau domaine :

```text
uint64_le(SHA256(UTF8("H24|" + fixture_id))[0:8])
```

Chaque ligne conserve la spécification synthétique complète et déclare
explicitement `waveform_synthesized=false` et
`scientific_outcome_present=false`.

## Plan de tests

La cardinalité est également redérivée question par question :

```text
1 nouveau test de graphe typé H24
+ 71 questions scientifiques réinscrites sous nouveaux IDs
= 72 spécifications de tests H24
```

Phases :

```text
P0 27
P1 35
P2 10
```

Le premier test est `H24-A01-GRAPH-DIRECTION`. Les autres IDs commencent par
`H24-`. Aucun outcome H23 n’est un input. Chaque test porte exact input,
procédure, oracle, inverse, métriques, artefacts, drawback et un evidence schema
explicite. Le champ métrique générique `pass_rule_boolean` est retiré ; les
verdicts devront être recomputés indépendamment depuis les opérandes persistés.

## Fermeture après revue de `4cfd4a60…`

La revue externe a refusé le passage à l’implémentation tant que trois éléments
restaient implicites. Le correctif demeure exclusivement JSON/tests/docs.

Le manifeste possède maintenant un `evidence_operator_contract` fermé. Il
définit les types JSON exacts, sépare booléen/entier/flottant, refuse les
non-finis, fixe l’égalité récursive, les shapes, l’ordre, les listes vides et
les tolérances. Les `27` opérateurs effectivement utilisés ont chacun une
sémantique normative, y compris `d08_traces_exact`,
`support_formula_exact`, `timing_components_exact` et
`ts01_evidence_exact`. La sentinelle `__PLAN_FIXTURE_IDS__` est la seule
sentinelle autorisée et son expansion est liée à la liste ordonnée du manifest
de population hashé. L’égalité suivante est obligatoire :

```text
set(opérateurs utilisés par les 72 tests)
==
set(registre des opérateurs)
```

Chaque test possède également un `fixture_selection` machine-readable en mode
`EXACT_IDS`. La liste `resolved_fixture_ids` est persistée directement dans le
record, vérifiée unique et contenue dans les 175 IDs liés. Une sélection vide
porte obligatoirement un motif analytique explicite. Aucun `exact_input`, texte
de procédure ou alias historique ne peut modifier cette sélection.

Enfin le binding distingue désormais deux instants sans modifier
rétroactivement le contrat successeur approuvé :

```text
snapshot successeur 184d3847…
→ manifests inexistants à cet instant historique

présent contrat lié
→ manifests définis
→ population non matérialisée
→ evaluators/oracles non implémentés
→ tests non exécutés
```

Les tests structurels incluent des mutations adversariales pour opérateur ou
sentinelle inconnu, opérateur manquant, fixture non liée, sélection vide sans
motif et transition d’état contradictoire.

Validation locale contractuelle après correction :

```text
106 tests H24 + H23 + H20 réussis en 1,371 s
git diff --check réussi
```

Cette suite n’a appelé aucun evaluator scientifique, n’a synthétisé aucune
waveform et n’a ouvert aucune donnée réelle ou locked-test.

## Kill rules

```text
premier échec P0
→ H24_SYNTHETIC_HYPOTHESIS_KILLED

premier échec P1/P2
→ H24_PRETRAIN_READINESS_NOT_DEMONSTRATED

succès complet futur
→ AUTHORIZED_TO_PREPARE_H24_TRAIN_PROTOCOL
→ jamais TRAIN_AUTHORIZED
```

L’ordre P0 → P1 → P2 et l’arrêt au premier échec sont obligatoires.

## Portée

Ces fichiers restent des spécifications contractuelles. Aucune waveform,
fixture concrète, exécution, donnée réelle, H17, modèle, checkpoint,
entraînement, calibration, export, live ou locked-test n’est autorisé. La
prochaine action est uniquement la seconde revue externe des manifests et du
plan corrigés. Aucune implémentation ou synthèse n’est autorisée par ce
correctif.
