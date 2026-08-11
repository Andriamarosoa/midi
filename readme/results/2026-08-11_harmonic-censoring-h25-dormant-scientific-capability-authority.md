# H25 — capability scientifique et autorité one-shot dormantes

## Verdict d'entrée

Le pilote externe a approuvé le bloc moteur/recomputer au commit :

```text
de73a8f99e206e0677e48ef38427287f24f7f5d5
APPROVED_H25_DORMANT_SCIENTIFIC_EVIDENCE_COMPLETENESS_CORRECTION
```

La portée accordée est strictement :

```text
AUTHORIZED_TO_DEFINE_AND_IMPLEMENT_H25_DORMANT_SCIENTIFIC_CAPABILITY_CONTRACT_AND_ONE_SHOT_AUTHORITY_ONLY
```

## Bindings fermés

Le nouveau contrat lie exactement :

```text
base scientifique approuvée  de73a8f99e206e0677e48ef38427287f24f7f5d5
engine blob                  171602b54a8023e2c85c128aca14ec053da176ad
recomputer blob              9b1c878b6e99b07c3aeff1cd2e80a3c5bf21ff0f
runner dormant blob          09777f18f198ca94e6b1155652fc5c1b460977dd

population index             814d8c368ac67ce65ed20c9e90e634ceffe706db1cc5e642cc3c61ff37ab5f53
runtime provenance           cadc154a84674f6e58cf412d71f73407d0c07388f3bf470fa2368a1b810825db
population receipt           dbab85910151ce25c186f478797c86604a94e6cf486dda7e0c4b7b8eeb4fddd9

qualification administrative
54bd361a99223dd24d6e4f0883ace47572965604c406efe69e5564f675d14ee1
```

Les cinq inputs Git scellés sont le contrat scientifique, le contrat runtime,
les spécifications de fixtures, le manifest population et le manifest des 27
tests. Le futur issuer vérifiera leurs octets, blobs Git et l'ascendance du
commit avant toute capability.

## Capability et consommation

`AttestedH25ScientificCapability` n'a aucun constructeur public. Son
attestation est liée à l'identité de l'objet dans le processus ; copie,
deepcopy et sérialisation sont refusées. La capability brute n'est jamais
retournée : seul `IssuedH25ScientificAuthority` est exposé.

Le wrapper est verrouillé et passe irréversiblement de :

```text
ISSUED
→ CONSUMED_BEFORE_DELEGATION
```

avant l'appel au runner. Une exception du delegate ne restaure jamais
l'autorité et une seconde exécution est refusée.

## Cycle one-shot implémenté

Le chemin futur est unique :

```text
preflight
→ capability process-local
→ claim O_CREAT|O_EXCL|O_WRONLY mode0600
→ fsync fichier + parent
→ import NumPy et rehash population après claim
→ P0 puis P1 puis P2
→ transcript 27 records
→ terminal atomique
```

Le premier échec scientifique produit immédiatement le suffixe complet
`NOT_RUN_BY_KILL_RULE`. Une erreur opérationnelle post-claim produit
`OPERATIONAL_ERROR` puis `NOT_RUN_BY_OPERATIONAL_FAILURE`. Si la fermeture
ordinaire elle-même échoue, un terminal forensique atomique ne contient aucun
verdict scientifique fabriqué et classe l'exécution
`H25_EXECUTION_INCONCLUSIVE_CONSUMED`.

## Observation P2-007

Aucune observation cross-runtime ne peut être injectée par un appelant. Le
futur seal/activation devra lier une commande secondaire exacte et son timeout.
Après claim, le runner lance automatiquement ce processus avec stdin fermé,
capture uniquement stdout/stderr, exige code retour zéro et un objet exact :

```text
runtime_id
fixture_measurements  36, ordre manifest
test_records          27, ordre manifest
```

Le recomputer approuvé compare ensuite lui-même cette observation détaillée à
l'observation primaire. Un timeout, stderr, code non nul, JSON partiel ou
schéma différent devient inconclusif consommé, sans retry ou substitution.

## Dormance effective

Les artefacts requis suivants sont absents :

```text
configs/harmonic_censoring_h25_scientific_execution_authorization_seal.json
configs/harmonic_censoring_h25_scientific_execution_activation.json
H25_SCIENTIFIC_EXECUTION_AUTHORIZATION_COMMIT
H25_SCIENTIFIC_EXECUTION_AUTHORIZATION_SEAL_SHA256
```

L'issuer vérifie cette transition avant le contrat, le plan, la population ou
NumPy et échoue donc immédiatement dans ce commit.

```text
capability scientifique émise    non
claim scientifique créé          non
population scientifique ouverte  non
P0 / P1 / P2                     0 / 0 / 0
donnée réelle / locked-test      non / non
modèle / training                non / non
```

La prochaine transition est uniquement la revue externe de ce bloc. Aucun
seal, activation, binding OS, capability, claim ou P0 n'est autorisé ici.

## Validation locale TEST-ONLY

```text
py_compile capability + runner + tests                 réussi
tests H25 autorisés hors probes lifecycle real-OS      74/74 réussis
git diff --check                                       réussi
```

Les tests de lifecycle ajoutés emploient uniquement des chemins temporaires
`TEST-ONLY-H25`. Ils couvrent la dormance pré-contrat, l'attestation par
identité, l'absence de delegate arbitraire, la consommation avant délégation,
le claim `O_EXCL`, l'impossibilité de retry, la fermeture opérationnelle à 27
records et le transport secondaire stdout fermé. Aucun test n'ouvre le
répertoire publié des 36 fixtures.
