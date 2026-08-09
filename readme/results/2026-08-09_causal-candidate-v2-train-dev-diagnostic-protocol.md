# Protocole V2 — diagnostic train-only sur la partition dev

Date : 2026-08-09

Portée : préinscription documentaire et test de cohérence JSON uniquement.
Ce commit ne crée aucun runner, ne charge aucun modèle, standardiseur,
checkpoint, audio, label, manifeste ou registre d'actifs, et ne réalise ni
inférence, fit, calibration, validation, export, live ni test verrouillé.

## Pourquoi cette cohorte

Les 12 prises validation historiques ont révélé le défaut de placement V1. Une
A/B V2 sur ces mêmes prises ne serait donc pas une validation indépendante et
reste interdite.

Le premier diagnostic proposé utilise uniquement la partition `dev` déjà
préassignée par le plan Policy A et la règle canonique V3 :

| Corpus | Prises dev canoniques |
| --- | ---: |
| GAPS | 6 |
| Guitar-TECHS direct input | 6 |
| Guitar-TECHS mic/amp | 6 |
| GuitarSet | 12 |
| **Total** | **30** |

Ces prises sont des prises `train`, contrôlées par le plan group-safe et le
registre d'actifs existants. Elles ont cependant servi au choix de l'époque V1.
Le résultat V2 sera donc exclusivement un **diagnostic exploratoire train-only** :
il ne peut ni promouvoir V2, ni choisir un seuil, ni changer le modèle.

## Expérience préenregistrée

Le futur runner, qui n'est pas encore autorisé à être implémenté, devra
réutiliser exactement :

- la tête V1, son standardiseur et le seuil `0,31` ;
- le checkpoint de transcription, le YAML, le décodeur référence et la
  politique audio déjà scellés ;
- la politique V3 SHA-256 `db55930…5683`, le plan Policy A
  `a8347e4e…3685f4` et le registre d'actifs `12dd74f2…586507` ;
- une unique inférence de transcription par prise, les mêmes masques audio et
  deux décodeurs indépendants.

La branche référence n'a pas de porte. La branche candidate doit imposer
explicitement `post_ranking_pre_noteon`, utiliser les mêmes 12 features V1
figées, puis appliquer la même tête et le même seuil. Aucun override audio,
backfill, lookahead, buffer ou hop supplémentaire n'est autorisé.

Avant TensorFlow ou l'ouverture d'un actif, le runner devra vérifier les
empreintes, recharger le plan et le registre persistants, dériver exactement
les 30 identités depuis la règle V3 et refuser tout élément validation ou test.
Il devra ensuite s'arrêter après le rapport A/B global, par corpus et par
prise, avec placement, compteurs de porte et métriques causales archivés.

## Décision et limites

Il n'existe volontairement aucun seuil de succès automatique dans ce protocole.
Une amélioration ou une dégradation éventuelle sera descriptive et nécessitera
une nouvelle revue avant toute autre expérience. La validation historique, la
calibration, tout ajustement du seuil `0,31`, le fit, l'export, le live et le
test verrouillé restent fermés.

Le contrat machine lisible est
`configs/causal_candidate_fit_v2_train_dev_diagnostic_protocol.json`.

## Vérification documentaire

`py_compile`, `53` tests contrat/A-B/décodeur en `0,405 s`, `30` tests de
provenance/minage en `0,711 s` et `git diff --check` passent. Ces tests ne
chargent aucun artefact V1 ni aucune prise réelle.
