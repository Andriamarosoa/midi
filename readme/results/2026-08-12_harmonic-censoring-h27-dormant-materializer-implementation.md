# H27 — loader et materializer dormants, sans matérialisation

## Portée autorisée

Ce lot implémente uniquement les contrôles structurels qui précèdent une future
matérialisation H27. Il part du commit de conception `83ec0978d1763b8bb25e47cc43d1f73d60adb6fd`
et lie, avant toute interprétation, les cinq blobs Git revus :

- préinscription : `869c70f7c643d8387645377a8cf5166b8728914d` ;
- cas zero-context : `1b57c27936cfb0befeceaf0c30ff73189f304672` ;
- spécifications des fixtures : `9aea04053a13a3f5cf81b461a58977c377600f5b` ;
- manifeste de tests : `594b33c8c579733718f7f0445d3780c9f60b2b2a` ;
- contrat de population : `fc82c1c7b3dec837a63c6f86afed9a5f724f7aad`.

Les cinq JSON scellés ne sont pas modifiés. Aucun waveform H27, masque H27,
record, index de population, FFT, NNLS, engine, recomputer, P0/P1/P2,
authority, claim, entraînement, calibration ou locked-test n'a été créé ou
exécuté.

## Implémentation

`harmonic_censoring_h27_contract.py` charge les blobs en octets Git LF,
refuse BOM, CRLF, clés JSON dupliquées et constantes non finies, puis fige
profondément les objets. Il réconcilie les 17 fixtures `4/4/2/7`, les 27 tests
`9/9/9`, les 11 obligations `R-ZERO`, la couverture P1, les 107 cellules P2,
les 124 identités futures et le masque role-major de 66 560 octets.

`harmonic_censoring_h27_materializer_dormant.py` fournit seulement :

- un inspecteur sans écriture qui dérive les 124 identités canoniques ;
- un encodeur de masque role-major générique, vérifiant indépendance des rôles
  et exceptions de support ;
- des rendus numériques **toy**, explicitement fournis par le test, pour
  vérifier l'ordre et l'égalité d'une collision ;
- deux frontières H27 réelles (`synthesize_h27_fixture` et
  `materialize_h27_population`) qui échouent avant allocation ou inspection de
  destination, car la capability n'a aucun issuer.

Le module ne dépend pas de H26 et ne peut pas publier la population
`H27_SYNTHETIC_V1`. Les rendus toy ne consultent aucun ID ni aucune recette H27
scellée et ne constituent pas une matérialisation.

## Correctif de revue fail-closed

La revue de `c1992d26` a relevé qu'un appelant aurait pu fournir les dimensions
ou rôles de production aux helpers numériques toy. Le correctif conserve les
interfaces mais refuse maintenant, **avant toute allocation ou accès NumPy**,
le nombre de samples `16640`, le taux `44100 Hz` et chacun des quatre rôles de
production. Les helpers sont limités à un domaine toy explicitement plus petit.
Les tests utilisent également une sentinelle NumPy afin de démontrer que ce
rejet est réellement antérieur au runtime numérique.

## Vérification locale

Commande exécutée depuis le worktree isolé :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest discover -s tests -p test_harmonic_censoring_h27*.py -v
```

Résultat : `8/8` tests réussis après correctif de revue. Ils couvrent notamment le binding des cinq
blobs, leur rejet après mutation d'octets, l'impossibilité d'émettre la
capability, l'échec avant accès à la destination, les 124 identités, le masque
role-major, `2^-80`, et les deux rendus indépendants byte-identiques d'une
collision toy.

`py_compile` des deux modules et du test, ainsi que `git diff --check`, ont
également réussi.

## STOP

État terminal :

`H27_DORMANT_MATERIALIZER_IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_MATERIALIZATION_NO_SCIENCE`

La prochaine étape exige une revue externe de ce code complet. Cette revue
peut demander un remplacement complet et cohérent des modules si elle détecte
un défaut. Elle ne doit pas autoriser à elle seule la matérialisation, les
tests P0/P1/P2 ou une autorité d'exécution.
