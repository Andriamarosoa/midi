# H27 — préinscription du contexte silencieux dépendant du rôle

Date : 2026-08-12

## Frontière

```text
authorization = AUTHORIZED_H27_ROLE_AWARE_ZERO_CONTEXT_PREREGISTRATION_CONTRACT_ONLY_FROM_0C297B58
base_commit = 0c297b588d0c89d348b1c9a828eddceab169be86
hypothesis_id = H27_ROLE_AWARE_ZERO_CONTEXT_V1
population_namespace = H27_SYNTHETIC_V1
test_namespace = H27_TEST_V1
status = PREREGISTERED_PENDING_EXTERNAL_REVIEW_NO_IMPLEMENTATION
```

H27 modifie une seule règle scientifique : un silence exact et entièrement
supporté est un contexte valide uniquement pour `previous_short` et
`previous_long`. Les deux vues `current_*` conservent la règle de puissance
strictement positive de H26.

## Matrice des quatre rôles

| Rôle | zéro exact + support valide | non-zéro au-dessus du plancher | non-zéro sous le plancher | support invalide |
|---|---|---|---|---|
| `current_short` | invalide | valide | invalide | invalide |
| `previous_short` | contexte valide, `T=0` | valide | invalide | invalide |
| `current_long` | invalide | valide | invalide | invalide |
| `previous_long` | contexte valide, `T=0` | valide | invalide | invalide |

Le silence exact exige un support complet, 100 % des échantillons `float64`
finis et chaque valeur numériquement égale à `0.0`. Il n'utilise ni seuil RMS,
ni seuil spectral, ni tolérance absolue, ni epsilon, ni bruit, ni identité de
fixture. Un quasi-silence non nul reste soumis au plancher H26.

## Conséquences exactes

- `current_short=0` : analyse invalide, aucun ratio, NNLS, residual improvement
  ou certificat ; hors bypass antérieur, outcome `AMBIGUOUS`.
- `previous_short=0` avec current valide : contexte valide `T=0`, onset rise
  exactement `1`, sans epsilon.
- `current_long=0` : analyse longue invalide, persistence indisponible, contexte
  requis invalide, aucun certificat ; hors bypass, `AMBIGUOUS`.
- `previous_long=0` avec current valide : contexte valide `T=0`, persistence
  exactement `1`, qui reste diagnostique et n'est jamais un certificat seul.

## Invariants hérités

Les quatre outcomes, l'ordre history → support/contexte → équivalence →
certificat positif → certificat négatif → ambiguous, la causalité 44 100 Hz / hop
256 / vues 4096 et 8192 / previous à un hop / résolution à un hop / zéro futur,
ainsi que Hann, padding, FFT, bandes, NNLS, grille de pitch, bounded claim,
collision exacte et exclusions d'oracle restent inchangés pour toute vue non
nulle.

Les seuils restent exactement :

```text
positive: exclusive >= 0.02, onset >= 0.05, residual >= 0.10
negative: exclusive <= 0.002, onset <= 0.005, residual <= 0.001, margin >= 10.0
minimum exclusive partials = 2
minimum valid bins = 3
```

Silence seul ne suffit jamais à `NO_BIRTH`. Support invalide n'est jamais
zero-filled. Aucun champ `fixture_id`, `expected`, `family`, `category`,
`ground_truth_onset` ou `latent_label` ne participe à la classification.

## Obligations data-only

`configs/harmonic_censoring_h27_zero_context_synthetic_cases.json` reprend les
onze cas `R-ZERO-001..011` approuvés. Ce sont des attentes déclaratives, sans
Python, moteur ou résultat exécuté.

## Population et autorités futures

`H26_SYNTHETIC_V1` reste immutable, utilisable seulement comme référence
forensique/régression et inéligible à la science successeur.
`H27_SYNTHETIC_V1` n'existe pas encore : aucune alias, copie scientifique ou
mutation en place n'est permise. Une future matérialisation devra produire un
nouveau manifest, index et de nouveaux SHA sous autorisation séparée.

H27 exigera trois objets nouveaux et distincts : authority runtime/
matérialisation, authority d'exécution scientifique et claim scientifique
durable single-use. Aucun objet H26 consommé n'est réutilisable. Maximum futur :
une authority et une claim par exécution autorisée, sans retry.

## Kill rules et STOP

```text
P0 -> H27_PREREGISTRATION_OR_IDENTIFIABILITY_INVALID
P1 -> H27_CERTIFICATE_HYPOTHESIS_NOT_DEMONSTRATED
P2 -> H27_ROBUSTNESS_NOT_DEMONSTRATED
operational failure after claim -> H27_EXECUTION_INCONCLUSIVE
stop_after_first_failed_test = true
later_tests_marked_not_run = true
retry_allowed = false
```

Les IDs de tests et les fixtures H27 ne sont pas définis dans cette étape.

```text
documentary_state = H27_ROLE_AWARE_ZERO_CONTEXT_PREREGISTERED_PENDING_EXTERNAL_REVIEW_NO_IMPLEMENTATION
implementation_authorized = false
materialization_authorized = false
scientific_execution_authorized = false
locked_test_authorized = false
```

STOP externe obligatoire. Aucun code, test exécutable, population, authority,
claim, FFT, NNLS, locked-test, entraînement, calibration ou modèle n'est créé
ou lancé.
