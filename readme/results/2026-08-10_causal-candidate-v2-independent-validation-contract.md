# Contrat — évaluation indépendante de la porte causale V2

## Statut

Contrat uniquement, en attente de revue externe. Cette étape n'ouvre aucun
audio, label, checkpoint, modèle ou runner et ne calcule aucune métrique.
Elle ne modifie pas les résultats du diagnostic V2 train/dev archivé le
10 août.

## Pourquoi une nouvelle cohorte

Le diagnostic V2 train/dev a confirmé le mécanisme prévu : la même tête V1,
au même seuil `0,31`, peut rejeter des candidats lorsqu'elle est déplacée
après la sélection et avant le NoteOn. Son effet observé est toutefois très
faible (`10` faux NoteOn causaux en moins sur les 30 prises train/dev) et ne
justifie ni promotion, ni nouveau seuil, ni nouvel entraînement.

La prochaine question est donc préenregistrée sans toucher au modèle : cet
effet survit-il sur une cohorte de validation qui n'a participé ni au fit
V1/V2, ni à la formulation de V2, ni au diagnostic V2 train/dev ?

## Frontière d'indépendance et audit de faisabilité

Le manifeste complet reste scellé par SHA-256
`b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7`.
L'audit a lu uniquement ses colonnes d'identité, de split, de groupe, de
joueur et de capture, ainsi que la sélection historique de 12 prises V1
(`configs/causal_candidate_fit_v1_validation_selection_12.json`, SHA-256
`8c3cf53c7f5dcf086b70767e28499c3164aa307059652a6d0a2fc87159f9dcbc`).

Après exclusion stricte de toute clé et de tout groupe de fuite déjà exposé
par ces 12 prises, il reste :

| Corpus | Après exclusion de clé | Après exclusion de groupe |
|---|---:|---:|
| GAPS | 27 | 26 |
| Guitar-TECHS direct input | 43 | 40 |
| Guitar-TECHS mic/amp | 43 | 40 |
| GuitarSet | 57 | 0 |

GuitarSet ne peut pas être déclaré indépendant : toutes ses prises validation
appartiennent à `guitarset:player:04`, déjà présent dans la cohorte historique.
Il est donc absent de cette expérience. Cette absence est une limite de portée,
jamais un résultat « effet nul GuitarSet ».

## Cohorte gelée

Le protocole versionné
`configs/causal_candidate_fit_v2_independent_validation_protocol.json` fixe
30 identités exactes :

- 10 GAPS, une par groupe de fuite indépendant ;
- 10 groupes physiques Guitar-TECHS, chacun avec exactement une prise direct
  input et sa prise mic/amp (20 prises) ;
- 0 GuitarSet.

La liste n'est pas choisie d'après les métriques, l'audio ou les labels. Elle
est dérivée du manifeste scellé avec la graine `47`, puis inscrite explicitement
dans le contrat. Toute divergence entre liste, règle, manifeste, groupe de
fuite ou plan Policy A (`a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4`)
devra échouer avant l'ouverture d'un actif.

## Intervention strictement gelée

L'éventuelle exécution future devra conserver sans variation :

- checkpoint de transcription `1ce8ac44…` ;
- modèle V1 `b9320cd0…` et standardiseur `0600aa1a…` ;
- 12 features V1, seuil `0,31`, placement
  `post_ranking_pre_noteon` ;
- configuration d'évidence audio `45edbb71…`, YAML d'évaluation `24528578…`
  et décodeur référence `c16be482…` ;
- une seule inférence de transcription et les mêmes masques audio pour A/B.

La référence reste sans porte. Le candidat ne change ni modèle, ni features,
ni seuil : seul le placement V2 déjà implémenté est employé.

## Décision préenregistrée

Toutes les règles ci-dessous doivent passer pour conclure à une preuve
indépendante positive :

- réduction relative globale des faux NoteOn causaux d'au moins 1 % ;
- aucune hausse des faux NoteOn causaux dans chacun des trois corpus ;
- baisse du rappel causal à 250 ms limitée à `0,002` globalement et `0,005`
  par corpus ;
- baisse de F1 onset limitée à `0,001` globalement et `0,002` par corpus ;
- aucune hausse des retriggers ni des fragments excédentaires ;
- hausse de p50 et p90 causal limitée à un hop, soit
  `5,804988662131519 ms` ;
- aucune conclusion GuitarSet et aucune promotion automatique, même si toutes
  les règles passent.

Une règle manquante, non finie ou échouée conduit à un résultat non positif.

## Étapes encore interdites

Avant une nouvelle revue externe, sont interdits : implémentation du runner,
création du registre d'actifs validation, chargement de modèle, accès audio ou
labels, inférence, fit, calibration, recherche de seuil, réutilisation des 12
prises historiques, export, live et test verrouillé.

Si le contrat est approuvé, l'étape suivante sera seulement la préparation
synthétique et fail-closed du runner, avec une preuve séparée de provenance des
actifs validation. Une passe CPU réelle nécessitera encore une autorisation
distincte.
