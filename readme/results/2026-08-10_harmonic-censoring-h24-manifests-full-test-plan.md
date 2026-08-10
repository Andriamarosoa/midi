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

manifest de tests
configs/harmonic_censoring_h24_test_manifest.json
191407 octets
930eeffd8443b0d2e38fca15f6efaf949e66f74dcba0f2e007a461d5e803318e

contrat de liaison
configs/harmonic_censoring_h24_manifest_binding_contract.json
1276 octets
6529b9578f9b556ab6c31f928d04eeb3cbf17284e3260ada0ce50668827319b0
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
prochaine action est uniquement la revue externe des manifests et du plan.
