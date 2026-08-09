# Hypothese V2 — porte causale apres ranking, avant NoteOn

Date : 2026-08-09
Portee : contrat preenregistre uniquement. Aucun code de decodeur, modele,
standardiseur, actif audio/label, inference, fit, recalibration, validation,
export, live ou test verrouille n'a ete ouvert ou execute pour cette etape.

## Motivation unique

La passe A/B historique V1 archivee au commit `f893aa55e6e5b00eddda7b4833a8cf4775c9f511`
a confirme que la tete causale, au seuil gele `0,31`, a rejete `9` des `711`
candidats internes eligibles. Pourtant, les deux branches ont produit les memes
`4 247` evenements MIDI finaux : aucun faux NoteOn, rappel, F1, latence,
retrigger ou fragment n'a change.

Le rapport brut conserve hors Git a l'empreinte
`8f048ad173015c2a89d3cde5ca106cc45c6bad05f6023f36c92ba4e12c28d1c3`
est la source de ce constat. Cette V2 ne change donc ni le modele, ni les
donnees, ni le seuil : elle isole seulement le point auquel la meme decision
est appliquee dans le decodeur stateful.

## Hypothese preregistree

> Le signal appris par V1 est-il utile pour les NoteOn retenus, mais applique
> trop tot, avant ranking et selection de polyphonie maximale ?

La reference reste :

```text
candidats -> controles existants -> ranking -> selection maximum_polyphony
          -> mutation etat -> NoteOn
```

La future branche V2, si elle est distinctement autorisee, sera :

```text
candidats -> controles existants -> ranking -> selection maximum_polyphony
          -> porte causale V1 -> mutation etat des acceptes -> NoteOn des acceptes
```

Le ranking et la population selectionnee restent donc reels et stateful. Il
ne faut pas forcer artificiellement les deux branches a conserver les memes
candidats apres une divergence.

## Invariants de placement

La porte V2 ne voit que les candidats deja selectionnes par le ranking et
`maximum_polyphony`, et qui satisfont la definition d'eligibilite V1 inchangee.
Ses 12 entrees encodees et ses huit valeurs causales brutes sont figees comme
en V1, depuis l'etat causal de la branche candidate avant ranking/selection.
Ni rang post-porte, ni selection post-porte, ni emission, ni identifiant,
cible, provenance, futur ou etat mute ne peut devenir une entree du modele.

Un candidat selectionne puis rejete :

- n'emet aucun `NoteOn` ;
- ne devient pas actif et n'occupe aucune place de polyphonie ;
- ne subit pas les remises a zero qui appartiennent a une note emise ;
- ne declenche pas de protection d'accord ;
- ne provoque ni reranking ni remplissage de sa place pendant le meme hop.

Les retriggers restent explicitement hors de la population de porte V2. Aucun
lookahead, buffer audio ou hop supplementaire n'est autorise.

## Artefacts geles

V2 reutilise sans modification les artefacts V1 suivants :

| Element | SHA-256 / valeur |
|---|---|
| Modele causal V1 | `b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e` |
| Standardiseur V1 | `0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b` |
| Seuil | `0,31` |
| Checkpoint de transcription | `1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325` |
| YAML d'evaluation | `245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804` |
| Decodeur de reference | `c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96` |
| Manifeste | `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` |

Le contrat machine lisible est
`configs/causal_candidate_fit_v2_post_ranking_pre_noteon_contract.json`.

## Integrite de la validation historique

Les douze prises validation ont deja servi a constater le defaut de placement
V1. Elles ne sont donc pas une validation independante de V2. Ce contrat
interdit toute nouvelle A/B sur cette cohorte et toute selection de seuil ou de
modele. Une utilisation ulterieure, seulement apres autorisation distincte,
devrait etre decrite comme exploratoire et non comme une validation vierge.

## Etape suivante bloquee

La seule action immediate est une revue externe du present contrat. Une future
implementation devra d'abord demontrer synthetiquement la parite du chemin
desactive, l'ordre selection-puis-porte, l'absence de mutation/backfill apres
rejet, la conservation exacte des 12 features et l'absence de latence ajoutee.
Tout acces reel aux artefacts ou toute evaluation train/validation reste hors
de cette autorisation. `locked_test_used=false` est maintenu.
