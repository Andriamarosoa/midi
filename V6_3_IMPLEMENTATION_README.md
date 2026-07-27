# V6.3 / V6.3.1 - onset causal continu

## But

V6.3 apprend une attaque intentionnelle sur la vraie grille live de 256
echantillons. Il ne remplace pas V6.0 : c'est un module causal autonome de 512
echantillons destine a filtrer les changements de pitch suspects.

Les labels ne sont pas inventes manuellement :

- `start_s` fournit le temps de l'attaque ;
- `note_id` conserve les retriggers, y compris deux notes MIDI identiques ;
- `end_s` separe sustain et release ;
- les colonnes harmoniques du CSV selectionnent les queues de notes difficiles ;
- un accord simultane reste un seul evenement pour la sortie onset binaire.

## Dataset

```powershell
python -m src.v6.onset_continuous_dataset --overwrite
python -m src.v6.validate_continuous_onset_dataset
```

Contrat valide sur les 360 enregistrements GuitarSet :

| Split | Joueurs | Exemples | Attaques | Negatifs |
|---|---|---:|---:|---:|
| Train | 00-03 | 305 336 | 71 703 | 233 633 |
| Validation | 04 | 72 617 | 16 387 | 56 230 |
| Test | 05 | 64 203 | 13 895 | 50 308 |

Chaque trame est alignee sur le hop 256. Les phases negatives conservees sont
pre-attaque, decay, sustain, release, silence et queue harmonique. Le rapport
exhaustif est dans
`data/dataset/v6_3_continuous_onset/validation_report.json`.

## Experiences controlees

V6.3 utilise un pooling moyenne + maximum global. V6.3.1 reutilise exactement
les memes donnees et hyperparametres, mais remplace ce pooling par huit bandes
temporelles ordonnees. Ce changement conserve la position du transitoire dans
les 512 derniers echantillons.

| Mesure | V6.3 | V6.3.1 temporel |
|---|---:|---:|
| Meilleure AUC-PR validation extraite | 55,83 % | 56,97 % |
| F1 evenementiel continu joueur 04 | 38,48 % | 42,16 % |
| F1 evenementiel continu joueur 05 | 36,26 % | 38,18 % |
| AP trame continue joueur 05 | 43,99 % | 46,86 % |
| Latence `tf.function` batch 1 p95 | 3,32 ms | 4,12 ms |

V6.3.1 est donc meilleur, mais son detecteur evenementiel autonome reste trop
faible pour remplacer le detecteur live.

## Ablation du decodeur

Un premier decodeur faisait aussi produire les retriggers de meme MIDI au
reseau onset. Il est rejete : a seuil bas, un niveau onset maintenu declenchait
une nouvelle note toutes les 80 ms.

Le decodeur corrige garde les retriggers existants de V6.0 et utilise V6.3.1
uniquement pour autoriser les changements de pitch actifs. Le seuil 0,029395 a
ete choisi parmi 302 candidats sur quatre solos du joueur 04, avant lecture des
quatre solos du joueur 05. 93 seuils satisfaisaient toutes les contraintes
relatives a V6.0.

Resultat test sur 103,48 s et 199 notes evaluables :

| Mesure | V6.0 comparable | V6.3.1 + retrigger V6.0 |
|---|---:|---:|
| Active F1 | 84,873 % | 84,873 % |
| Precision conjointe | 79,502 % | 79,531 % |
| Fantomes/minute | 52,764 | 50,445 |
| Evenements generes | 369 | 365 |
| Notes manquantes | 5 | 5 |
| Retriggers non supportes | 15 | 15 |

L'ancien resume indiquait 52,18 fantomes/minute et 3 notes manquantes. Le
recalcul comparable explique l'ecart : 91 evenements suspects sur 103,48 s
donnent 52,764/min, et les 3 notes correspondaient aux sorties brutes alors que
les 5 notes ci-dessus correspondent aux deux decodeurs stabilises. Les decisions
doivent toujours comparer la meme definition.

## Decision

- V6.0 reste la reference live.
- V6.3 est rejete comme gate complet.
- V6.3.1 avec retriggers V6.0 est conserve comme ablation de recherche : il
  retire quatre evenements sans regression mesuree, mais le gain est trop petit
  pour justifier sa latence sequentielle.
- Aucun lookahead n'a ete ajoute. Le contexte onset est uniquement passe :
  512 echantillons, soit 11,61 ms.

La prochaine experience utile doit cibler directement les changements de pitch
proposes par V6.0 sur les joueurs 00-03, avec les memes `start_s`, `note_id` et
profils harmoniques comme verite terrain et negatifs difficiles. Elle devra etre
validee sur 04 puis testee sur 05, sans modifier simultanement V6.0.

## Artefacts principaux

- V6.3 : `runs/v6/onset_v6_3_continuous_20260718_172541`
- V6.3.1 : `runs/v6/onset_v6_3_1_temporal_pool_20260718_180341`
- Selection 04 : `decoder_threshold_selection_external_retrigger.json`
- Ablation 05 : `continuous_decoder_ablation_v63_external_retrigger/aggregate.json`

------------------------------------------------------------------------

# V6.3.2 - gate de transition V6.0

## Changement controle

V6.3.2 ne re-entraine pas V6.0. Il apprend seulement a accepter ou refuser un
changement `pitch actif -> autre pitch actif` deja propose par V6.0 pendant au
moins deux trames. L'entree contient 20 mesures causales deja disponibles :
probabilites active/pitch, variation des probabilites, intervalle, duree de la
note courante, attaque detectee, RMS, flux spectral et amplitudes harmoniques
predites par V6.0.

`start_s`, `end_s` et `note_id` de GuitarSet donnent la verite terrain. Les
colonnes harmoniques des CSV renforcent les faux changements lies a un
harmonique, mais elles ne sont pas requises en live. Le modele a 481 parametres.

## Dataset de transitions

Seuls les 180 enregistrements `solo` sont utilises, car le decodeur V6.0 evalue
ici une sortie monophonique. Le split par joueur reste strict.

| Split | Joueurs | Transitions | Accepter | Rejeter | Negatifs harmoniques CSV |
|---|---|---:|---:|---:|---:|
| Train | 00-03 | 8 224 | 4 738 | 3 486 | 178 |
| Validation | 04 | 1 594 | 880 | 714 | 42 |
| Test | 05 | 813 | 470 | 343 | 4 |

Le validateur confirme l'identite des splits, l'alignement causal sur le hop,
la plage MIDI et l'absence de valeur non finie.

## Classification hors decodeur

| Mesure | Validation 04 | Test 05 |
|---|---:|---:|
| Average precision | 85,39 % | 89,45 % |
| F1 au seuil 0,352173 | 80,06 % | 83,16 % |
| Rejet des negatifs harmoniques | 69,05 % | 100 % (4/4) |

La latence `tf.function` batch 1 du gate est de 0,574 ms en moyenne et 1,090 ms
au percentile 95. Le gate n'est appele qu'au moment d'une transition stable.

## Validation dans le decodeur

Le seuil du decodeur est choisi sur quatre solos du joueur 04 seulement. La
regle minimise les fantomes sous les contraintes suivantes par rapport a V6.0 :
notes manquantes, precision conjointe, F1 active et retriggers non supportes ne
doivent pas empirer.

Le seuil sur 04 est 0,0131145. Il retire cinq evenements : 70,159 devient
67,260 fantomes/minute, avec 11 notes manquantes dans les deux cas. Le seuil de
classification 0,352173 aurait davantage filtre (38,848 fantomes/minute), mais
aurait ajoute deux notes manquantes et un retrigger non supporte ; il est donc
infeasible selon le contrat fixe avant test.

Sur les quatre solos verrouilles du joueur 05 (103,48 s, 199 notes), aucune des
77 transitions n'est sous le seuil sur 04. V6.3.2 reproduit donc exactement
V6.0 :

| Mesure | V6.0 | V6.3.2 |
|---|---:|---:|
| Active F1 | 84,873 % | 84,873 % |
| Precision conjointe | 79,502 % | 79,502 % |
| Fantomes/minute | 52,764 | 52,764 |
| Evenements generes | 369 | 369 |
| Notes manquantes | 5 | 5 |
| Retriggers non supportes | 15 | 15 |

L'inverse validation au seuil zero reproduit bit pour bit les sorties V6.0 sur
les quatre sources 04 et les quatre sources 05. Le gate n'ajoute aucun lookahead
ni trame de stabilisation.

## Decision V6.3.2

- V6.3.2 n'est pas integree au live : elle ne donne aucun gain strict sur le
  test verrouille.
- V6.0 reste la reference.
- La bonne AP prouve que les transitions sont separables, mais le label binaire
  `support present` n'encode pas le cout sequentiel d'un veto : garder l'ancienne
  note peut supprimer une vraie note ou modifier un retrigger.
- Une experience suivante devrait apprendre le gain de decodeur (fantome retire
  contre trames correctes et note de reference perdue), toujours avec
  `onset/start_s`, `note_id` et les profils harmoniques, plutot qu'ajouter une
  autre tete de classification generale.

## Artefacts V6.3.2

- Dataset : `data/dataset/v6_3_2_transition_gate`
- Run : `runs/v6/transition_gate_v6_3_2_20260718_191447`
- Selection 04 : `decoder_threshold_selection.json`
- Test 05 : `continuous_transition_gate_ablation/aggregate.json`
- Decision : `deployment_decision.json`
