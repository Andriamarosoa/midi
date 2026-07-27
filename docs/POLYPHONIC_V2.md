# Guitar MIDI AI — pipeline polyphonique V2

## Contrat produit

La V2 vise la guitare propre et causale, avec jusqu’à six notes MIDI
simultanées dans la plage 40–76. La V1 monophonique reste conservée comme
baseline et comme solution de repli.

Le modèle reçoit une fenêtre glissante de 4096 échantillons à 44,1 kHz. Il
n’utilise ni échantillon futur ni post-traitement avec lookahead.

## Labels utilisés

Les cibles ne créent pas de nouvelle sémantique musicale. Elles sont dérivées
des annotations existantes :

- `active` devient un vecteur multi-hot de 37 notes ;
- `onset` devient un vecteur multi-hot de 37 notes ;
- `note_id` conserve l’identité de chaque événement pour l’évaluation ;
- `harmonic_number`, amplitude et décalage en cents supervisent 20 partiels
  pour chaque fondamentale GuitarSet.

Une note hors de la plage 40–76 ne devient jamais un faux silence. La fenêtre
est masquée pour la loss. Les superpositions impossibles de plus de six notes
et deux événements simultanés du même MIDI sont également exclues de la loss.

## Audit des sources

L’audit reproductible se trouve dans
`runs/polyphonic/source_audit.json`.

| Source | Enregistrements | Avec polyphonie | Notes | Durée active polyphonique |
|---|---:|---:|---:|---:|
| GuitarSet | 360 | 359 | 62 476 | 50,72 % |
| GAPS | 401 audités | 401 | 367 090 | 73,71 % |
| Guitar-TECHS | 104 annotations | 100 | 18 934 | 57,96 % |
| IDMT-SMT-Guitar | 667 annotations | 251 | 5 767 | 22,32 % |

GAPS utilise uniquement ses 300 éléments officiellement assignés : 240 train,
30 validation groupée par `scorehash` et 30 tests officiels verrouillés. Les
101 lignes sans split sont exclues des comparaisons.

## Harmoniques et données mixtes

GuitarSet fournit des pistes hexaphoniques debleedées : les partiels peuvent
être attribués à leur vraie fondamentale. Les enregistrements GAPS sont des
mélanges polyphoniques stéréo. Mesurer un pic spectral dans ce mélange ne
permet pas de savoir à quelle note il appartient ; fabriquer ces labels
introduirait les notes de l’accord dans les harmoniques de leurs voisines.

La loss harmonique est donc masquée pour GAPS, mais la tête reste présente et
continue d’être supervisée par les 62 476 notes GuitarSet. GAPS supervise les
têtes `frame` et `onset`.

## Architecture

```text
audio causal 4096 + masque temporel
              │
              ▼
       CNN causal + TCN
              │
       pooling last + moyen
        ┌─────┼──────────────┐
        ▼     ▼              ▼
 frame 37  onset 37   harmoniques 37×20
 sigmoid   sigmoid     amplitude + cents
```

Le softmax monophonique est remplacé par des sigmoids indépendants. Le tronc
CNN/TCN compatible est initialisé avec les poids V6 monophoniques ; les
nouvelles têtes sont apprises à partir de zéro.

## Décodeur live

L’état MIDI appartient globalement à chaque hauteur, jamais à une corde de
guitare. Un onset convaincant peut déclencher immédiatement une note. La voie
de secours `frame` demande deux observations, soit un seul hop supplémentaire
(5,805 ms). La disparition doit être stable pendant trois hops pour éviter le
chattering.

Un candidat ressemblant au partiel d’une note grave active reçoit un seuil
plus strict uniquement s’il ne possède pas sa propre preuve d’onset. Cela
supprime les résonances sans supprimer aveuglément les vraies notes d’accord.

## Validation obligatoire

- seuils sélectionnés exclusivement sur validation ;
- test GuitarSet joueur 05 et test GAPS officiel jamais utilisés pour régler ;
- métriques séparées silence, monophonie et polyphonie ;
- événements générés → annotations (notes fantômes) ;
- annotations → événements générés (notes manquantes) ;
- métriques onset et onset+offset ;
- parité TFLite et ONNX ;
- latence modèle, boucle interne et pipeline matériel.

Les résultats finaux sont ajoutés uniquement après la fin de l’entraînement et
la validation du meilleur checkpoint.

## Extensions multi-source contrôlées

La V2.1 ajoute GAPS à parts égales avec GuitarSet dans le sampler, avec une
augmentation de gain de ±6 dB appliquée uniquement au train. Les métriques de
validation restent séparables par source afin qu’une amélioration sur GAPS ne
cache pas une régression GuitarSet.

Guitar-TECHS est préparé pour une ablation V2.2 : P1 train, P2 validation et
P3 test. Les captures `directinput` et `micamp` d’une même interprétation
partagent toujours le même groupe. IDMT est préparé séparément par groupes
d’exercices, mais reste exclu de la configuration produit déployable tant que
les contraintes de sa licence CC-BY-NC-ND-4.0 ne sont pas levées.

Chaque époque V2.1 est conservée. Les checkpoints non dominés sur F1 `frame`
et F1 `onset` sont départagés sur validation continue avec les événements
`note_id`, les notes fantômes et les notes manquantes. Les tests verrouillés ne
sont ouverts qu’après ce choix unique.

## Parité produit

L’export produit un seul modèle causal à quatre sorties : `frame`, `onset`,
`harmonic_amplitude` et `harmonic_offset_cents`. Le bundle contient aussi le
SHA-256 du modèle et la configuration complète du décodeur. Les runtimes
desktop lisent ce même contrat afin de garder les mêmes états MIDI, seuils,
temporisations et règles anti-harmoniques.
