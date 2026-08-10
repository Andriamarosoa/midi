# H23 — correction dormante des oracles exacts et de la recomputation

## Verdict externe à l'origine de cette étape

La revue externe de `907bece46fcf3e88cd44e267a74378127ddca913`
n'a pas approuvé la création d'un nouveau seal. Elle a relevé deux défauts :

1. plusieurs familles de tests étaient réduites à des contrôles génériques au
   lieu d'exécuter exactement leur `exact_input`, leur procédure, leur oracle
   et leur règle de passage ;
2. le producteur et le finalizer partageaient des booléens de décision, ce qui
   permettait à une inverse falsifiée ou à un `passed=true` incohérent de se
   certifier lui-même.

La revue a autorisé uniquement une correction d'implémentation dormante. Elle
n'a autorisé ni seal, ni activation, ni claim, ni marker, ni waveform, ni
P0/P1/P2.

## Registre fermé 72/72

Le runner possède désormais un registre explicite `test_id -> evaluator` et le
module pur `harmonic_censoring_h23_oracles.py` possède le registre correspondant
`test_id -> recomputer specification`. Les deux ensembles doivent être
strictement égaux aux 72 identifiants du plan. Il n'existe plus de dispatch par
préfixe ni de fallback par famille.

Chaque évaluateur porte le nom `_measure_<test_id>` et produit deux ensembles
de mesures brutes : `primary` et `inverse`. Les helpers DSP peuvent être
partagés, mais aucun helper générique ne décide à la place de l'oracle propre à
un test. Les inverses de rejet passent elles aussi par un validateur réellement
appelé ; le texte `REJECTED` est la disposition observée de cet appel.

## Recomputation indépendante

Le module des oracles est volontairement pur : il n'importe ni NumPy, ni le
synthétiseur, ni le producteur de transcript. Pour chaque test il impose :

- les clés exactes des mesures primaires et inverses ;
- les types et catégories attendus ;
- les opérateurs, tolérances et relations exactes ;
- la recomputation séparée du résultat primaire, de l'inverse et du résultat
  final.

Le finalizer relit les mesures persistées et appelle ce recomputer. Les champs
`oracle_comparison`, `pass_rule_boolean`, `inverse.passed` et `event.passed`
restent uniquement des duplications contrôlées : ils doivent tous être égaux au
résultat recalculé depuis les mesures. Ils ne sont jamais une source d'autorité.

Deux tests adversariaux prouvent explicitement que :

- des mesures incompatibles restent refusées même si tous les booléens
  persistés annoncent `true` ;
- une inverse falsifiée est refusée même si le producteur annonce sa réussite.

## Validation sans science

Commande ciblée finale :

```powershell
python -B -m unittest tests.test_harmonic_censoring_h23_harness tests.test_harmonic_censoring_h23_execution_dormant tests.test_harmonic_censoring_h23_claim_transcript_implementation tests.test_harmonic_censoring_h23_exact_oracle_registry tests.test_harmonic_censoring_h23_execution_capability_contract tests.test_harmonic_censoring_h23_executor_claim_transcript_contract tests.test_provisional_resolution_frame_fallback_h20_contract
```

Résultat : `74 tests réussis`. `py_compile` et `git diff --check` réussissent.
Ces tests sont contractuels et utilisent uniquement des objets administratifs
ou des répertoires temporaires. Aucun des 72 évaluateurs scientifiques n'est
appelé par cette validation.

## Limites et prochaine frontière

Cette correction ne crée aucune autorité d'exécution :

```text
nouveau seal / activation       absent
claim / marker production       absent
waveform synthétisée            non
P0 / P1 / P2 exécuté            non
population H17 / donnée réelle  non
modèle / checkpoint             non
locked-test                     non
```

La revue externe a également demandé un durcissement TOCTOU distinct avant
tout futur seal. Il n'est pas inclus ici afin de garder une frontière de revue
unique. L'étape suivante est donc la revue externe de cette correction 72/72 ;
si elle est approuvée, un second commit dormant traitera le TOCTOU, puis sera
lui-même revu. Aucun seal ne doit être créé avant ces deux approbations.
