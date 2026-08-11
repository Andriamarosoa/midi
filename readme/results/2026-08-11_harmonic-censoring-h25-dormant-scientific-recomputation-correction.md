# H25 — correction du moteur scientifique dormant et de la recomputation

## Portée

Ce correctif répond au verdict externe
`REJECTED_H25_DORMANT_SCIENTIFIC_ENGINE — INDEPENDENT_RECOMPUTATION_AND_PREREGISTERED_TEST_COVERAGE_DEFECTS`.
Il ne lit aucun des 36 waveforms publiés, n'exécute aucun P0/P1/P2 et ne crée
aucune authority, capability, claim, seal ou activation scientifique.

```text
population scientifique ouverte    non
P0 / P1 / P2 exécutés              0 / 0 / 0
données réelles / locked-test      non
modèle / checkpoint / training     non
tests utilisés                      TEST-ONLY-H25 uniquement
```

## Recomputation réellement indépendante

`harmonic_censoring_h25_recomputer.py` n'importe plus le moteur H25, ses
fonctions, ses constantes, ses structures de plan ou NumPy. Il possède ses
propres boucles standard-library pour :

- reconstruire le graphe H1 et H2…H20 ;
- recalculer l'opérateur scalaire depuis `power`, `frequencies_hz` et le pitch ;
- reconstruire les masques, baseline, normalisation, null et résiduel ;
- rejouer les transitions causales d'état actif ;
- redériver les catégories depuis les features et l'état, sans faire confiance
  au champ `outcome` du producteur.

Le producteur ne persiste plus une seconde « référence scalaire » qu'il aurait
lui-même calculée. Il persiste les bins spectraux bruts et sa sortie vectorisée ;
le recomputer calcule ensuite sa propre référence. Une falsification du champ
`outcome` est refusée même si elle correspond à l'oracle nominal du fixture.

## Bornes causales et état actif

P0-007 distingue désormais explicitement :

```text
target short/long current end     16383
target short/long previous end    16127
resolution hop end                16639, uniquement pour P1/résolution
```

L'état actif n'est plus un simple `active_pitches_by_fixture` fourni par
l'appelant. Chaque fixture doit fournir une `H25CausalReplayTrace` liée à son
ID, bornée au sample `16383`, avec état initial et transitions `note_on` /
`note_off`. Le producteur et le recomputer rejouent séparément cette trace ;
toute transition future ou divergence des pitches dérivés est refusée.

## Couverture des oracles corrigée

- P0-002 compare une fréquence obtenue par scaling idéal du spectre à une
  coordonnée obtenue par remapping relatif, sur H1…H20 et `s=0..88`.
- P0-004 persiste et compare les SHA waveform, curves/features et états causaux
  des deux explications latentes avant d'accepter `AMBIGUOUS`.
- P0-006 fait recalculer au recomputer les opérandes base et gain ×4.
- P0-009 persiste les résultats forward/reverse au lieu d'un booléen déclaré.
- P2-001 persiste les deux résultats avant/après modification du suffixe futur.
- P2-002 exécute exactement les translations `0, 1, 2, 4` hops et conserve la
  catégorie ainsi que le délai de résolution d'un hop.
- P2-005 lie les décisions aux masques opérateur recalculés aux frontières.
- P2-006 exécute trois permutations de fixtures et restitue l'ordre manifest.
- P2-007 vérifie le replay déterministe même-runtime, mais reste fail-closed tant
  qu'une observation sérialisée d'un second runtime n'est pas fournie.
- P2-008 exige des compteurs réellement injectés par l'instrumentation du futur
  runner ; ils ne sont plus fabriqués comme constantes par le producteur.
- P2-009 dérive l'attrition des listes d'IDs effectivement observées.

Les inverses ne modifient plus le champ `outcome` après calcul. Ils modifient le
waveform, la trace d'état ou un input de politique ; les perturbations interdites
(shift 100 cents non déclaré, coordinate 128 emit-capable, attribution forcée,
résolution au target hop) sont refusées avant évaluation.

## Validation locale autorisée

```text
py_compile du moteur et du recomputer                        réussi
15 tests du moteur dormant TEST-ONLY                         réussis
60 tests H25 autorisés hors probes lifecycle real-OS        réussis en 0,672 s
git diff --check                                             réussi
```

La suite de 60 tests couvre contrats/manifests, materializer dormant, runtime,
authority/seal et moteur scientifique dormant. Les probes real-OS historiques
ne sont pas relancés dans cette correction car leur écart PTY Windows avait été
reproduit indépendamment du moteur et aucune modification de ce harness n'est
autorisée ici.

## État après correction

Le runner scientifique reste volontairement dormant et échoue avant import
NumPy ou accès population. La prochaine action est une nouvelle revue externe
de ce correctif. L'exécution de la population, P0, P1, P2 et toute transition
d'autorité restent interdites.

## Durcissement de complétude après seconde revue

Une seconde revue externe a accepté la séparation du recomputer, mais a refusé
la complétude des preuves du premier correctif. Les changements suivants
ferment ces derniers points sans exécution scientifique :

- P0-004 compare désormais deux explications latentes du même fixture pour
  chacun de A01…A06 ; aucun pairing artificiel A01↔A04 n'existe ;
- P0-002 exige l'égalité exacte de l'ensemble
  `fixture × candidate × H1..H20 × s=0..88`, sans omission ni doublon ;
- P0-009 et P2-006 persistent et recomputent toutes les permutations de
  fixtures, candidats, transforms et graphe ;
- les inverses précédemment représentés par `accepted_by_input_schema=false`
  persistent maintenant uniquement la mutation brute ; le recomputer applique
  sa propre politique fermée pour démontrer le rejet ;
- tout replay commence avec `initial_active_pitches=[]`, vérifie l'ID fixture et
  dérive l'état actif uniquement des transitions causales ;
- P2-007 exige deux observations détaillées, chacune avec 36 mesures fixture et
  27 records test ordonnés. Le recomputer compare lui-même catégories, masques,
  structures et floats ; aucun booléen résumé n'est accepté.

Validation après ce durcissement :

```text
21 tests du moteur dormant TEST-ONLY                         réussis
66 tests H25 autorisés hors probes lifecycle real-OS        réussis en 1,157 s
py_compile                                                   réussi
git diff --check                                             réussi
P0 / P1 / P2                                                 0 / 0 / 0
```
