# H24 — harness dormant

Date : `2026-08-10`

## Autorisation reçue

La revue externe de `16e612bad8e61ea554d194a5fc88f74b07f4f7d9` a rendu :

```text
APPROUVÉ comme manifests + plan complet H24 contractuellement fermés
AUTHORIZED_TO_IMPLEMENT_H24_DORMANT_HARNESS_ONLY
```

La portée excluait explicitement la matérialisation des 175 fixtures, toute
synthèse de waveform, l’exécution P0/P1/P2, les données réelles, H17, les
modèles/checkpoints, l’entraînement, la calibration et le locked-test.

## Contrat d’implémentation

Le fichier
`configs/harmonic_censoring_h24_dormant_harness_contract.json` lie exactement :

```text
successor
184d3847a594ffaca263b45befe70d1f5aa63ade0a0ef599d969ba044f4e680a

population manifest
52c88c74c837ad3c6109be466df38bac862e10d93c187fe60e8c5da30bd4b02b

test manifest
7f87e486ffc6fdc2bfa60a5c617eca9b1ce78c570c1d72910173193ad1f7b416

manifest binding
242c00d4d5fd3b9e777676b563f28b94b724159bde81307aebbba9e46608a1b5
```

Son propre SHA-256 est :

```text
72675c6dda2128aa0036b7f0f2379de535fd74445a029f020f24f3f6f15fff39
```

Tous les droits opérationnels restent à `false`. Ce contrat ne contient ni
activation, ni capability de production, ni claim/marker.

Le contrat conserve aussi explicitement l’état historique du test manifest
(`implementation_exists=false`) et enregistre séparément l’état présent :
loader, traducteur de recettes, registre dormant et recomputer implémentés,
mais producteurs non callables, population non matérialisée et tests
scientifiques non exécutés. Le manifest approuvé n’est pas réécrit
rétroactivement.

## Implémentation

`src/polyphonic/harmonic_censoring_h24.py` :

- charge les cinq JSON en UTF-8/LF, refuse doublons, non-finis et dérive de SHA ;
- vérifie la liaison successor/population/tests/binding ;
- résout exactement `175` spécifications et `72` sélections machine-readable ;
- exige `27` opérateurs exactement égaux aux opérateurs utilisés et une seule
  sentinelle `__PLAN_FIXTURE_IDS__` ;
- produit des recettes immutables, sans tableau audio ni appel DSP ;
- refuse inconditionnellement matérialisation et exécution scientifique ;
- atteste par identité les plans issus du loader : `dataclasses.replace()` ou
  une construction directe ne crée aucune autorité.

`src/polyphonic/harmonic_censoring_h24_operators.py` :

- implémente les `27` opérateurs fermés avec types JSON exacts ;
- distingue `bool`, `int` et `float`, refuse NaN/Inf et types Python non JSON ;
- développe la sentinelle seulement depuis le manifest de population lié ;
- valide non-vacuité et cardinalité avant sentinelle puis opérateur ;
- impose `H24-A02.analytic_pairs == 42` ;
- recompute les décisions depuis `primary`/`inverse` persistés ;
- refuse les champs producteur `pass`/`verdict` ;
- fournit le recomputer A01 fermé à partir de `typed_edges`, sans accepter un
  booléen producteur comme autorité.

### Correction après première revue du harness

La revue de `77a7dcc34269f13ec09ba936d261ad1e9daefefa` a confirmé la
dormance, les bindings, le registre et les 27 opérateurs, mais a identifié que
le premier recomputer A01 exigeait seulement que chacun des sept payloads
inverses soit invalide. Sept tableaux vides pouvaient donc satisfaire
`inverse_pass` sans représenter les mutations préenregistrées.

Le correctif compare maintenant chaque payload au `primary.typed_edges` valide
et impose exactement :

```text
I1  une seule H1 dont la coordonnée devient non-identité
I2  une seule H2-H20 dont la coordonnée devient la source
I3  un seul record descendant ajouté, sans retrait ni autre changement
I4  le seul relation_type d’une H1 devient PROPER_HARMONIC_ASCENT
I5  exactement une relation retirée
I6  exactement un duplicata strict ajouté
I7  exactement une coordonnée augmentée de +0.25, toujours > source
```

Les comparaisons de collections sont indépendantes de l’ordre et conservent la
multiplicité. Toute seconde suppression, modification de type additionnelle,
mutation répétée sous le mauvais ID ou payload vide fait échouer l’inverse.

Le registre contient exactement une entrée par test : le producteur est nommé
mais `DORMANT`, non callable, et le recomputer est indépendant. Aucun runner ou
CLI H24 n’a été ajouté.

## Tests administratifs et adversariaux

Les nouveaux tests couvrent notamment :

- SHA et cardinalités `175 / 72 / 27 / 1` ;
- traduction déterministe des 175 recettes sans waveform ;
- immutabilité et refus d’un plan forgé ;
- fermeture inconditionnelle des trois frontières de production/exécution ;
- dérive d’octets avant résolution ;
- sémantique positive des 27 opérateurs ;
- tableaux vides refusés ;
- A02 `0`, `1` et `42` éléments ;
- sentinelle liée et sentinelle inconnue ;
- recomputation depuis operands et rejet d’un verdict producteur ;
- rejet des types non JSON.

Validation locale :

```text
126 tests H24 + H23 + H20 réussis en 1,997 s
python -m py_compile réussi
git diff --check réussi
```

Cette validation n’a synthétisé aucune waveform, n’a matérialisé aucune
fixture, n’a exécuté aucun test scientifique P0/P1/P2 et n’a ouvert aucune
donnée réelle, population H17, modèle, checkpoint ou locked-test.

## État de sortie

```text
loader strict                         implémenté
traduction specs -> recettes          implémentée, pure et dormante
registre 72 producteurs/evaluators    implémenté, producteurs non callables
27 opérateurs + sentinelle             implémentés
recomputers operands-only             implémentés
population H24 matérialisée           non
waveform synthétisée                  non
P0/P1/P2 exécuté                      non
capability/claim/marker               absent
```

La prochaine étape est uniquement la revue sémantique externe de ce harness.
Une autorisation séparée reste obligatoire avant toute création de population.
