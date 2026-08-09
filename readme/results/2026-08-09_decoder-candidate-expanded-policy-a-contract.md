# Contrat sans calcul — extension Policy A à six prises par cellule

## Motif

La revue du pilote `83afcf34` valide le pipeline et ses 429 candidats, mais
interdit le fit : sa population `fit` ne compte que 123 exemples (`23`
positifs), et certaines cellules GuitarSet × partition ne contiennent qu'une
classe. Cette étape ne lance aucune lecture d'actif, inférence, collecte,
minage, entraînement, calibration, validation, export, live ou test verrouillé.
Elle préenregistre seulement une prochaine population plus large, à relire
avant toute exécution.

## Sélection fixe proposée

Le fichier
`configs/decoder_candidate_extended_policy_a_6percell.json` conserve sans
changement le manifeste, le plan Policy A v2, le registre d'actifs, checkpoint,
YAML, décodeur à porte nulle et politique audio déjà scellés. Il fixe :

- CPU obligatoire et `locked_test_used=false` ;
- les mêmes quatre corpus train (`gaps_poly_mix`, Guitar-TECHS direct/mic et
  `guitarset_poly_mix`) ;
- six prises canoniques, triées par `(dataset_id, source_id, capture_id)`, dans
  chacune des 12 cellules corpus × partition `fit`/`dev`/`calibration` ;
- donc exactement `4 × 3 × 6 = 72` prises, ou un échec avant TensorFlow si une
  cellule Policy A ne possède pas ces six prises ;
- au plus `65 536` tentatives par prise, avec toute perte invalidant l'artefact.

Les prises GAPS exclues par Policy A restent exclues : ni la validation
historique ni ses dix joueurs chevauchants ne sont modifiés. La sélection ne
fait ni filtrage manuel, ni recherche de seuil, ni rééquilibrage après avoir vu
les résultats.

## Porte de représentation préenregistrée

Le second minage ne pourra être présenté que comme un corpus candidat à revoir
si, en plus de toutes les contraintes de provenance et d'intégrité, son rapport
montre au minimum :

| Contrôle | Seuil requis |
| --- | ---: |
| Cellule corpus × partition × cible 0 | 8 exemples |
| Cellule corpus × partition × cible 1 | 8 exemples |
| Partition entière, cible 0 | 75 exemples |
| Partition entière, cible 1 | 75 exemples |
| Tentatives perdues | 0 |

Ces seuils ne constituent **pas** une autorisation de fit automatique. Ils
servent uniquement à éviter de réexaminer une extension qui reproduirait une
cellule à classe unique. Même s'ils sont satisfaits, une revue humaine devra
examiner les distributions réelles, la dépendance entre corpus, les retriggers
exclus et les diagnostics causaux avant de définir une hypothèse de fit.

Le schéma de protocole `2` rend cette porte exécutable : le futur
`mining_report.json` inscrira `representation_gate.passed` et chaque manque
par cellule ou partition. La valeur ne modifiera jamais `fit_authorized`, qui
reste systématiquement `false` dans ce mineur.

## Vérification sans données projet

`py_compile`, `git diff --check` et les **45 tests synthétiques ciblés** ont
réussi en 1,772 s. Ils couvrent notamment le schéma v2 fermé, les six sélections
canoniques par cellule, les seuils de couverture et leurs manques, ainsi que la
réconciliation de flux complet avec une frame invalide de retrigger. Aucun WAV,
label projet, checkpoint réel, inférence ou collecte n'a été ouvert durant ces
tests.

## Réconciliation complétée avant l'exécution future

Le pilote laissait 137 NoteOn hors du matcher causal sans ventilation explicite
au niveau du flux complet. Le mineur expose désormais, dans chaque futur lot et
son agrégat, les deux compteurs :

```text
decoder_noteons
= causal_matchable_decoder_noteons
+ full_flow_invalid_frame
+ full_flow_outside_audio
```

Les exclusions propres à la population `gate_eligible` restent aussi
distinctes. Ainsi une frame invalide de retrigger ou d'un autre chemin émis ne
peut plus disparaître de la réconciliation globale.

## Porte suivante

Faire revoir ce contrat et le correctif de comptage. Aucun second minage, fit,
calibration, validation officielle, sélection de seuil, export, live ou test
verrouillé n'est autorisé avant cette revue.
