# H26 — implémentation dormante de la pile scientifique

## Portée

Cette étape implémente uniquement la pile autorisée après l'approbation externe
du paquet déclaratif H26. Elle ne crée aucun issuer d'autorité et ne consomme
aucune fixture H26.

Implémenté :

- chargement strict des trois JSON scellés et vérification de leurs SHA-256 ;
- validation des 40 fixtures, 34 recettes, 6 collisions et 27 tests ordonnés ;
- synthétiseur déterministe futur, deux rendus indépendants des collisions et
  matérialisation atomique, tous inaccessibles sans capability ;
- masques de validité dérivés uniquement des paramètres scellés ;
- fenêtres causales, Hann symétrique, FFT avec padding ×8, noyaux 35 cents,
  support exclusif, ratios, onset, base harmonique, NNLS 512 sweeps, résidu et
  profil `GLOBAL_SYNTHETIC_TIMBRE_V1` ;
- resolver ordonné à quatre issues ;
- transforms P2 déterministes : gain, phase, bruit blanc/rose, cents et
  inharmonicité, décalage de hop, permutations et identités runtime ;
- opérandes bruts persistables, recomputer indépendant et structure de
  transcript avec kill rule.

Les constantes numériques utilisées par la frontière scientifique sont
construites depuis le contrat scellé. `expected`, `category`, `family`, cible,
onset de vérité et état futur ne peuvent pas entrer dans le recomputer.

## Frontières préservées

```text
materialization capability issuer : absent
scientific capability issuer      : absent
waveform H26 produite              : 0
test P0/P1/P2 exécuté              : 0
runtime scientifique secondaire   : non lancé
donnée réelle / modèle / train     : non utilisé
locked-test                        : non utilisé
```

Les tests n'utilisent que le chargement déclaratif, des contrôles structurels
et de petits opérandes artificiels qui ne correspondent à aucune fixture H26.

## Vérifications locales

```text
python -B -m py_compile ...                                  PASS
python -B -m unittest tests.test_harmonic_censoring_h26_dormant_stack
29 tests en 0,370 s                                          PASS
git diff --check                                             PASS
```

Une exécution exploratoire de toutes les anciennes suites H25 avec H26 n'est
pas retenue comme validation : 97 tests ont passé, tandis que 17 anciens tests
H25 supposant encore l'état pré-activation ont échoué face aux artefacts de
clôture H25 désormais présents. Aucun échec ne traverse un fichier H26 et cette
étape ne modifie pas H25.

## Décision

Le commit reste `implementation-only`, sans autorisation de matérialisation ou
d'exécution. Il doit être relu avant tout futur seal, capability, fixture,
waveform, P0/P1/P2 ou claim H26.

## Correctif après rejet externe de `9ea6ed4a`

La revue stricte a refusé la première implémentation. Le correctif courant :

- rend les deux classes capability inconstructibles sans aucun token de module ;
- gèle récursivement tout le plan JSON et refuse les mutations imbriquées ;
- remplace les entrées waveform/masques libres par un futur binding vérifiable
  au SHA de l'index, aux SHA des waveforms et du masque exact ;
- dérive l'équivalence uniquement de deux tableaux float64 non nuls et
  byte-identiques, jamais de l'identité du fixture ;
- centralise le centre fréquentiel cents+B et l'utilise pour synthèse, bandes,
  exclusivité et base harmonique ;
- représente explicitement `PENDING_NEW` au hop de proposition, puis une issue
  terminale exactement 256 samples plus tard ;
- applique `transform_order` à l'énumération 24..96 de la courbe de dilution,
  tout en canonisant la courbe finale ;
- fait revalider au recomputer la frontière causale, la courbe 24..96 et l'état
  terminal.

Ce correctif reste entièrement dormant et n'a produit aucune observation H26.

## Correctif après rejet externe de `62c6ab70`

La seconde revue a relevé trois défauts de câblage dans des chemins futurs que
la dormance rendait inaccessibles aux tests initiaux. Le correctif courant :

- retire l'argument invalide `transform_order` de
  `exclusive_partial_ranks()` et le transmet uniquement à
  `extract_raw_operands()`, où il gouverne réellement la grille de dilution ;
- conserve les quatre fenêtres preregistrées au hop cible `16383` et borne
  `maximum_sample_read` à ce même hop, tandis que l'état terminal reste à
  `16639`, exactement 256 samples plus tard ;
- ajoute le chemin racine attesté à `H26BoundObservation`, relit et rehache
  l'index scellé ainsi que ses fichiers au moment de la consommation, compare
  les métadonnées et octets fournis au record, puis n'utilise que les tableaux
  reconstruits depuis cet index ;
- fait confronter indépendamment par le recomputer tout payload P2 au test,
  à la grille, à la cellule et au fixture scellés, avec coordonnées baseline
  ou `P2_HOP_SHIFT_V1` exactes ;
- ajoute un test artificiel du chemin complet du producer qui aurait échoué
  sur l'ancienne signature, un adversarial de construction directe de
  `H26BoundObservation`, un contrôle des endpoints et un contrôle P2.

La portée reste strictement dormante : aucun index H26 réel, waveform H26,
P0/P1/P2, runtime secondaire, authority, capability, claim, donnée réelle,
modèle, entraînement ou locked-test n'a été créé ou exécuté.

## Correctif après rejet externe de `082a0db8`

La troisième revue a confirmé les corrections précédentes, mais a refusé la
liaison incomplète entre les cellules P2 qui modifient le signal ou le masque
et les octets effectivement consommés. Le correctif courant :

- porte l'index futur à un schéma v2 comprenant des records P2 distincts pour
  chaque `fixture_id/test_id/grid_id/cell`, chacun avec ses propres SHA de
  waveform, masque et alternate éventuel ;
- lie `H26BoundObservation` à ces trois coordonnées P2 et refuse une observation
  baseline lorsque le producer demande une transformation P2 ;
- reconstruit la transformation depuis le plan scellé, exige l'identité exacte
  avec la cellule demandée, puis relit et rehache le seul record P2 correspondant
  avant de mesurer les octets reconstruits ;
- matérialiserait, uniquement après une future autorisation séparée, les
  waveforms et masques propres à chaque cellule ; le décalage de hop reste lié
  aux onsets, cible, résolution et frontière de validité de sa recette ;
- impose au recomputer l'ordre brut exact de la grille de dilution : `24..96`
  en baseline/ascending et `96..24` en descending, au lieu d'accepter un simple
  ensemble de pitches ;
- ajoute les inverses artificiels demandés (baseline + P2, cellule différente,
  ordre opposé) et un chemin positif complet prouvant que le tableau transmis
  à `extract_raw_operands()` provient du record P2 exact.

La portée reste inchangée et strictement dormante : aucun index ou signal H26
réel, aucune phase P0/P1/P2, aucun runtime, issuer, capability, claim, donnée,
modèle, entraînement ou locked-test n'a été créé, chargé ou exécuté.

## Correctif après rejet externe de `f6bb6f10`

La quatrième revue a validé le binding P2 général et limité le refus au seul
câblage du masque `P2_HOP_SHIFT_V1`. Le correctif courant :

- conserve le masque entièrement valide des fixtures P09/P10 lorsqu'aucune
  `valid_time_support_start_sample` n'est déclarée, même pour `-2/-1` hops ;
- décale strictement la frontière déclarée de A10/A12 par `sample_shift`, sans
  clipping ni padding ;
- vérifie les bytes du masque fourni par l'appelant contre le record P2 rebindé,
  puis transmet uniquement `rebound.sample_valid` aux mesures scientifiques ;
- ne compare donc plus un masque P2 correctement transformé au masque baseline ;
- teste artificiellement les deux cellules négatives de P09/P10, les trois
  cellules de A10/A12, l'acceptation producer avec coordonnées décalées et le
  rejet inverse d'un masque baseline déclaré comme hop-shift P2.

La pile reste dormante : aucune waveform ou population H26 réelle, aucun
P0/P1/P2, runtime, issuer, capability, claim, donnée, modèle, entraînement ou
locked-test n'a été créé, chargé ou exécuté.
