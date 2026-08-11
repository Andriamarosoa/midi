# Préinscription scientifique H26 — certificats bornés et ambiguïté explicite

## Portée

Ce commit définit uniquement un paquet déclaratif dormant pour un éventuel
successeur de H25. Il ne modifie aucun moteur, recomputer, runner ou test
exécutable. Il ne matérialise aucun signal et n'autorise aucune exécution.

La première revue externe a refusé le paquet déclaratif initial parce que ses
catégories étaient définies, mais pas tous les opérandes nécessaires à une
reproduction indépendante. La révision autorisée ferme uniquement ce défaut :
elle ne change ni hypothèse, ni population, ni catégorie, ni seuil, ni plan
P0/P1/P2.

H25 reste définitivement `H25_SYNTHETIC_HYPOTHESIS_KILLED`, son claim reste
consommé et ne confère aucune autorité à H26.

## Problème hérité

H25 a montré qu'une règle générique pouvait convertir :

```text
aucune évidence nouvelle
+ explication parfaite par l'ancienne source
```

en `NO_BIRTH`, même lorsque deux causes latentes autorisées étaient
observationnellement indiscernables. La leçon est :

> absence d'évidence indépendante ≠ preuve négative d'absence.

## Hypothèse H26

H26 préenregistre un resolver causal à quatre résultats fondé sur deux
certificats séparés :

- `BIRTH_SUPPORTED` exige un certificat positif identifiable ;
- `NO_BIRTH` exige un certificat négatif qui falsifie une proposition candidate
  **bornée** et préenregistrée ;
- `AMBIGUOUS` est obligatoire lorsque ni certificat n'est complet, lorsque le
  support est invalide, lorsque la contribution est sous le plancher de
  détection ou lorsque deux causes sont observationnellement équivalentes ;
- `ALREADY_ACTIVE_HISTORY` est réservé à une hauteur déjà active selon
  l'historique causal et contourne les décisions de naissance.

`NO_BIRTH` ne signifie donc pas « aucune vibration physique, même arbitrairement
faible, n'existe ». Il signifie que la proposition testée — au moins deux
supports partiels exclusifs et une contribution minimale déclarée — est
falsifiée par une observation valide avec une marge préenregistrée.
La borne doit être dérivée causalement de l'amplitude observée sur la bande
partagée et d'une enveloppe timbrale synthétique globale préenregistrée. Une
borne fournie par fixture, par target ou par label est interdite. Cette
proposition bornée ne prétend pas définir une limite universelle pour les
guitares réelles.

## Ordre de décision

L'ordre est contractuel :

1. historique actif → `ALREADY_ACTIVE_HISTORY` ;
2. support invalide → `AMBIGUOUS` ;
3. équivalence observationnelle → `AMBIGUOUS` ;
4. certificat positif complet → `BIRTH_SUPPORTED` ;
5. certificat négatif complet → `NO_BIRTH` ;
6. tout autre cas → `AMBIGUOUS`.

La règle d'équivalence a priorité sur tout score scalaire. Aucun tie-break
binaire ni compensation par moyenne de famille n'est permis.

## Seuils préenregistrés

Le contrat fixe avant toute observation :

```text
supports partiels exclusifs minimaux                         2
ratio d'énergie exclusif minimal de la proposition        0,02
borne supérieure négative observée                        0,002
marge négative minimale                                      10×
bins valides minimaux par support partiel                     3
vues courtes valides minimales                                2
onset positif minimal                                      0,05
amélioration résiduelle positive minimale                  0,10
onset négatif maximal                                     0,005
amélioration résiduelle négative maximale                 0,001
ATOL exact                                                1e-12
RTOL de recomputation                                     1e-10
```

Aucun seuil ne peut être modifié après observation.

## Fixtures nouvelles et non contradictoires

La population H26 est seulement spécifiée : `40` fixtures, `0` waveform.

```text
10 positives
10 négatives avec certificat borné
 8 historiques actives
12 ambiguës
```

Les six collisions exactes H26 diffèrent du cas limite H25 : chaque explication
latente contient une contribution non nulle et les deux décompositions complètes
devront synthétiser indépendamment les mêmes octets observables. Une source
latente de gain zéro ne peut plus servir de preuve de collision exacte.
La spécification fixe désormais complètement ces six paires : fond commun,
partiels présents et absents, enveloppe décroissante ancienne, enveloppe
d'attaque commune à l'alternative, phase, fréquence flottante canonique,
amplitudes, histoire causale et rendu indépendant en tableaux `<f8`. La
collision du rang ancien est retirée du fond commun puis ajoutée une seule fois
soit comme partiel ancien, soit comme fondamentale candidate. Les deux tableaux
complets doivent être byte-identical avant publication; sinon la fixture est
invalide.

Le gain de la fondamentale candidate est fixé à `old_source_gain / rang` afin
de compenser exactement la loi d'amplitude harmonique `1/rang`. Les supports
qualifiés d'exclusifs doivent en outre être disjoints, bande de tolérance
comprise, des harmoniques `1..8` de toutes les sources causalement actives.
Pour éviter une différence d'arrondi artificielle, les deux rendus utilisent
le même float64 canonique `rang × F0(old_pitch)` comme fréquence de collision ;
la relation avec le pitch candidat est contrôlée séparément.

Trois fixtures contiennent une contribution non nulle sous le plancher de
détection ; elles sont explicitement `AMBIGUOUS`, jamais `NO_BIRTH`. Trois
autres couvrent des supports invalides et restent elles aussi ambiguës.

## Mesures et perturbations fermées

Les quatre vues causales, la Hann symétrique, le `rfft`, la normalisation de
puissance, les bandes triangulaires de `35` cents, leurs trois bins valides, les
dénominateurs, l'onset court, la base harmonique et le NNLS déterministe à `512`
sweeps sont maintenant définis algorithmiquement. Le profil global
`GLOBAL_SYNTHETIC_TIMBRE_V1` donne aussi une formule unique du minorant et de la
marge négative; aucune constante propre à une fixture ne peut être injectée.

Les grilles P2 ne sont plus des catégories ouvertes : gain `[0.5,1,2]`, phases
`[0,pi/2,pi,3pi/2]`, bruit blanc/rose × SNR `[30,20,10]` avec seed SHA-256,
cents `[-25,0,25]` × inharmonicité `[0,0.0004,0.004]`, shifts de hops
`[-2,-1,0]`, huit permutations exactes et deux identités runtime binaires. Les
masks, comptes, appartenances et résultats sont exacts; les opérandes flottants
cross-runtime utilisent uniquement la tolérance préenregistrée.

## Synthèse baseline déterministe

Une seconde revue a approuvé la fermeture des mesures, collisions et grilles,
mais a refusé l'implémentation tant que les `34` fixtures hors A01–A06 ne
déterminaient pas chacune un waveform unique. La correction déclarative
autorisée ajoute une recette exhaustive par fixture sans changer aucun ID,
ordre, outcome, seuil ou test.

Le contrat fixe maintenant le tableau initial `<f8`, les ordres source/partiel/
sample, l'addition float64, deux enveloppes algorithmiques, les sources et
partiels réellement présents, gains, onsets, phases, cents et inharmonicité,
ainsi que `NONE` ou la recette complète de bruit. Les négatifs déclarent la
candidate physiquement absente; les faibles A07–A09 conservent une candidate
physique non nulle; A10–A12 construisent d'abord le waveform puis appliquent
uniquement les masks. H01–H08 adoptent explicitement la convention
`SILENT_STATE_ONLY`. Les trois seeds baseline sont stockées comme chaînes
uint64 décimales exactes afin d'éviter une perte de précision JSON.

`baseline_waveform_recipes` est l'unique entrée de synthèse de ces `34`
fixtures. Les anciens champs `parameters` deviennent des assertions de
cohérence : toute divergence doit échouer avant allocation. A01–A06 restent
inchangées et demeurent gouvernées exclusivement par leur contrat de collision
déjà approuvé.

## Tests préenregistrés

Le manifest définit `27` tests dormants et non exécutés :

- P0 `9` : intégrité, sémantique des quatre issues, certificats, collisions
  non nulles, ambiguïté, causalité, fuite de target et recomputation ;
- P1 `9` : résultats exacts de toutes les familles, sans compensation ;
- P2 `9` : gain, phase, bruit/plancher, cents/inharmonicité, bandes de pitch,
  permutations, second runtime, causalité et réconciliation globale.

La première erreur arrêtera une future exécution et marquera tous les tests
suivants `NOT_RUN_BY_KILL_RULE`. Les statuts préenregistrés sont :

```text
P0 fail  H26_PREREGISTRATION_OR_IDENTIFIABILITY_INVALID
P1 fail  H26_CERTIFICATE_HYPOTHESIS_NOT_DEMONSTRATED
P2 fail  H26_ROBUSTNESS_NOT_DEMONSTRATED
erreur   H26_EXECUTION_INCONCLUSIVE
```

## Causalité, runtime et provenance

Les vues causales restent `4096` et `8192` samples, finissent au même hop et
sont comparées aux vues finissant exactement un hop plus tôt. Une proposition
`PENDING_NEW` doit se résoudre après un hop ; aucune lecture future n'est
permise.

Toute future matérialisation ou exécution nécessiterait des contrats de runtime,
SHA, autorité, capability, claim, transcript et fermeture entièrement nouveaux.
Les namespaces sont `H26_SYNTHETIC_V1` et `H26_TEST_V1`. Aucun blob, population,
claim ou autorité H25 ne peut être réutilisé comme autorité H26.

La prochaine étape est une nouvelle revue externe de ce paquet déclaratif
corrigé. Toute implémentation, matérialisation ou exécution reste interdite.

## Frontière d'autorisation

Cette préinscription n'autorise pas :

- l'implémentation d'un moteur ou recomputer H26 ;
- une modification de `_derive_outcome` H25 ;
- la matérialisation ou génération d'une fixture ;
- un runner, une capability ou un claim ;
- P0/P1/P2 ;
- une donnée réelle, un modèle, entraînement ou calibration ;
- le test verrouillé.

La prochaine étape éventuelle est une revue externe de ce paquet déclaratif,
avant toute implémentation.
