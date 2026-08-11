# H27 — contrat de conception des fixtures, tests et population future

## Portée

Ce lot contractuel part exactement du commit
`59d9115d3fdcb8cc0eeec543a67c723723a95103`. Il lie les blobs Git approuvés
`869c70f7c643d8387645377a8cf5166b8728914d` (préinscription H27) et
`1b57c27936cfb0befeceaf0c30ff73189f304672` (cas zero-context).

Il ne crée ni waveform, ni population, ni code scientifique, ni test
exécutable, ni materializer, ni engine/recomputer, ni authority, claim ou
capability. Aucun FFT, NNLS, locked-test, entraînement ou calibration n'a été
exécuté.

## Population baseline conçue

Le contrat fixe exactement 17 fixtures ordonnées :

- 4 positives : naissance isolée avec précontexte exact-zero, naissance avec
  overlap/exclusivité, fondamental masqué, support temporel exclusif ;
- 4 négatives : ancienne harmonique, décroissance, bande exclusive vide et
  variante high-band ;
- 2 états actifs : bypass causal low/high avant toute analyse spectrale ;
- 7 ambiguës : deux collisions exactes non nulles, sous-plancher, support
  précédent invalide, previous quasi-zero, current quasi-zero et current
  exact-zero.

Les paramètres hérités nécessaires sont recopiés dans les recettes H27. Les
IDs H26 ne sont que des métadonnées historiques, explicitement interdites comme
entrées de synthèse, scientifiques ou dépendances runtime.

Le correctif de revue ferme cette autonomie sans fallback : formules float64,
ordre d'accumulation, enveloppes, bruit, recettes baseline complètes et contrat
des deux collisions exactes sont intégralement déclarés dans H27. Les 15 cas
hors collision possèdent chacun une recette autoritaire ; `A01/A02` utilisent
exclusivement leur contrat de double rendu indépendant. Aucun champ
`IDENTICAL_TO_H26` ni défaut implicite ne subsiste.

La timeline reste `44100 Hz`, hop `256`, flux `16640` échantillons, avec les
quatre fenêtres `4096/8192` se terminant aux coordonnées H26 exactes.

## Sémantique zero-context

Un contexte `exact_zero` exige support complet, valeurs float64 finies et
égalité numérique `sample == 0.0` pour chaque échantillon requis. `-0.0` et
`0.0` sont équivalents. Aucun `atol`, RMS, seuil spectral, epsilon ou raccourci
de noise floor n'est permis.

Un seul échantillon non nul, y compris exactement `2^-80`, rend la vue
`quasi_zero` et réactive le plancher non nul H26. Un bit de support invalide
donne `INVALID_SUPPORT`, jamais un silence valide.

## Manifeste de tests conçu

Le manifeste contient exactement 27 tests : 9 P0, 9 P1 et 9 P2.

- P0 ferme les bindings, les 11 obligations `R-ZERO`, les quatre outcomes,
  les certificats positif/négatif, les collisions, les ambiguïtés, la causalité,
  les 12 exclusions scientifiques et la recomputation indépendante.
- P1 couvre chacune des 17 fixtures exactement une fois dans P1-001..008,
  puis P1-009 réconcilie `4/4/2/7` sans doublon, omission ou compensation.
- P2 préenregistre huit grilles totalisant exactement 107 futurs records :
  gain 9, phase 12, bruit 12, frontière exact-zero 4, cents/inharmonicité 18,
  permutations 32, runtimes 8 et hop-shift 12. P2-009 ne crée aucun waveform.

Chaque cellule possède désormais une identité canonique : ordre fixe des
grilles, ordre fixe des fixtures, axes nommés avec tokens ASCII fermés, produit
cartésien où l'axe gauche varie le plus lentement, puis `cell_id` construit par
concaténation ordonnée. Les deux runtimes Darwin/CPython sont recopiés avec
leurs empreintes et leur environnement exact. Les applications gain, phase,
bruit-remplacement, frontière zero, cents/inharmonicité, permutation et
hop-shift sont explicitement définies ; les 107 identités sont donc uniques et
déterminées avant matérialisation.

Les inverses zero/positive/negative/collision/causal/leakage/recompute sont
déclarés mais non exécutés. Les cellules stochastiques dériveront leur seed de
`SHA256(UTF8("H27|<fixture_id>|<grid_id>|<cell_id>"))`, avec les huit premiers
octets interprétés en entier non signé big-endian.

## Population future

Le design fixe 17 baseline + 107 P2 = 124 records, mais
`population_exists=false` et toutes les autorisations restent à `false`.
Une future matérialisation séparément autorisée devra utiliser une nouvelle
racine H27, create-exclusive, fichiers `0600`, fsync, rename no-replace
atomique, index publié en dernier, chemins contenus sans symlink, SHA-256 et
taille pour chaque payload. Elle ne pourra ni lire H26 ni resynthétiser pendant
la consommation scientifique.

## Contrôles structurels autorisés

Seuls le parsing JSON, les comptages, comparaisons de chaînes, SHA-256 de
texte/JSON et contrôles structurels sont permis pour ce lot. Les preuves
attendues sont : 17 IDs uniques, catégories `4/4/2/7`, 27 tests `9/9/9`, 11
obligations, couverture P1 exacte, 107 cellules P2 et absence de toute
autorisation, population, authority, claim ou capability.

## STOP

État terminal de ce lot :

`H27_FIXTURE_TEST_POPULATION_DESIGN_CONTRACTED_PENDING_EXTERNAL_REVIEW_NO_IMPLEMENTATION`

Une revue externe est obligatoire avant toute implémentation ou
matérialisation. Aucun P0/P1/P2 ne doit être exécuté à cette étape.
