# Hypothèse v3 sans calcul — extension canonique GuitarSet

## Motif préenregistré

Le minage étendu de 72 prises, archivé au commit `74f60ec`, est intègre mais
reste non autorisant : seules deux cellules échouent à la porte inchangée de
8 exemples par classe et par corpus × partition.

| Cellule observée | Positifs | Minimum |
| --- | ---: | ---: |
| `guitarset_poly_mix / dev / cible 1` | 6 | 8 |
| `guitarset_poly_mix / calibration / cible 1` | 7 | 8 |

Trois prises GuitarSet de cette sélection n'ont produit aucun candidat
supervisé. Ce constat local ne justifie ni une baisse rétroactive de la porte,
ni un nouvel ordre de 72 prises, ni un fit.

## Population unique proposée

Le nouveau protocole
`configs/decoder_candidate_guitarset_expansion_policy_a_v3.json` fixe une
seule population de **90 prises**, traitée comme un corpus complet dans une
future et unique passe CPU :

Son SHA-256 canonique LF est
`db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683`.

| Corpus | Prises canoniques par partition | Total sur fit/dev/calibration |
| --- | ---: | ---: |
| `gaps_poly_mix` | 6 | 18 |
| `guitar_techs_poly_directinput` | 6 | 18 |
| `guitar_techs_poly_micamp` | 6 | 18 |
| `guitarset_poly_mix` | 12 | 36 |
| **Total** | **30** | **90** |

La sélection reste le début de l'ordre canonique Policy A
`(dataset_id, source_id, capture_id)`. Les six premières prises de GuitarSet
restent donc identiques au minage précédent, auxquelles s'ajoutent les six
suivantes par partition. Rejouer les 90 prises dans un seul artefact évite de
fusionner a posteriori des JSONL de deux exécutions distinctes. Il ne s'agit
pas d'une boucle : le nombre 12 est fixé avant tout calcul et l'exécution ne
s'arrête jamais au moment où une cellule atteindrait 8.

Si le plan Policy A ne fournit pas les 12 prises GuitarSet dans une partition,
la sélection échoue avant chargement du modèle ou replay. Les groupes restent
ceux du plan Policy A ; aucune validation historique ne change et les groupes
GAPS exclus restent inéligibles.

## Invariants conservés

Les sept entrées scellées restent exactement celles du minage approuvé :
manifeste, plan Policy A v2, registre d'actifs, checkpoint, YAML, décodeur de
référence à porte nulle et politique audio LF. Le protocole conserve aussi :

- CPU obligatoire, `locked_test_used=false` et au plus 65 536 tentatives par
  prise ;
- la même porte de représentation : 8 par cellule et 75 par classe/partition ;
- `fit_authorized=false` indépendamment du résultat de la porte ;
- l'interdiction de calibration, validation officielle, sélection de seuil,
  export, live et test verrouillé.

Le schéma `3` accepte uniquement une table ordonnée de comptes entiers positifs qui
couvre exactement les quatre corpus scellés. Les schémas 1 et 2 conservent
leur entier uniforme ; ils ne changent ni de sens ni de sélection. La méthode
`recordings_for_dataset()` rend explicite le compte fixé par corpus et la
sélection réconcilie exactement `3 × (6 + 6 + 6 + 12) = 90` identités uniques.

## Vérification sans données projet

Cette étape ne lance aucun minage, ouverture d'actif, inférence, entraînement,
calibration, validation, export, live ou accès au test verrouillé. La
compilation Python, `git diff --check` et les 67 tests synthétiques ciblés
des contrats de mineur, provenance, labels, instrumentation et actifs
réussissent en `2,157 s`. Ils couvrent
le parseur strict du schéma 3, les sept SHA identiques, la règle LF, le refus
d'une table de comptes incomplète ou non canonique et la sélection de 90
prises sans réordonner les cellules non-GuitarSet.

## Porte suivante

Faire relire ce contrat et son code avant toute synchronisation Mac. Après une
approbation explicite seulement, une unique passe CPU train-only de 90 prises
pourra être préflightée avec les sept SHA, un worktree propre, un verrou absent
et une destination inédite. Son unique sortie sera un corpus candidat et son
rapport, à examiner avant toute discussion de fit.
