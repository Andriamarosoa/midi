# H26 — conception de remédiation après P0 consommé

Date : 2026-08-12

## Portée

```text
authorization = AUTHORIZED_H26_P0_REMEDIATION_DESIGN_CONTRACT_ONLY_FROM_E2A8A454
base_commit = e2a8a4549c7fd4c91329f73b31d0b384b1fd8c8e
status = DESIGN_ONLY_PENDING_EXTERNAL_REVIEW_NO_IMPLEMENTATION
historical_p0_terminal_status = H26_P0_INCONCLUSIVE_CONSUMED
historical_retry_allowed = false
```

Cette étape ne modifie ni le moteur, ni le recomputer, ni le materializer, ni
le runner, ni la population, ni les artefacts P0 consommés. Elle n'exécute
aucun calcul scientifique.

## Options examinées

### A — contexte précédent silencieux explicite

`H26_REMEDIATION_A_ROLE_AWARE_ZERO_POWER_CONTEXT` est l'option sémantique
préférée.

Une vue `previous_short` ou `previous_long` entièrement observée et exactement
silencieuse devient un contexte valide avec spectre et puissance totale
exactement nuls. Aucun epsilon, bruit ou signal artificiel n'est ajouté. La vue
`current_short` conserve la règle actuelle strictement positive, car elle
alimente les ratios, le NNLS et les certificats.

Cette option résout directement la cause P01 et conserve les seuils et les
oracles. Elle change néanmoins la définition scientifique actuelle de
`valid_total_power`. Elle ne peut donc pas être appliquée silencieusement à
H26 : elle exige une nouvelle préinscription successeur avant implémentation.

### B — fixture avec précontexte non nul

`H26_REMEDIATION_B_NONZERO_PRECONTEXT_FIXTURE_REDESIGN` n'est pas retenue en
premier choix. Elle change la question causale, les bytes et la population au
lieu de définir le statut scientifique d'un silence pré-onset valide. Un bruit
ajouté uniquement pour contourner l'exception est explicitement interdit.

### C — clôture H26 et successeur

`H26_REMEDIATION_C_CLOSE_H26_AND_PREREGISTER_SUCCESSOR` est une frontière de
gouvernance obligatoire : H26 reste consommé. Elle ne constitue toutefois pas
à elle seule une sémantique de remédiation. Le successeur devra préenregistrer
l'option A sous de nouvelles identités.

## Table sémantique avant/après

| Sujet | H26 historique | Option A future |
|---|---|---|
| `current_short` nul | spectre invalide | inchangé : analyse invalide, aucun ratio/NNLS/certificat |
| `current_long` nul | spectre invalide | inchangé : analyse invalide, persistence indisponible, contexte requis invalide, `AMBIGUOUS` avant les certificats |
| `previous_short` nul et masque valide | spectre invalide | contexte valide, `T=0`, onset rise `=1` si current valide |
| `previous_long` nul et masque valide | spectre invalide | contexte valide, `T=0`, persistence `=1` si current valide |
| masque invalide avec samples nuls | support invalide | inchangé : jamais reclassé silence valide |
| vues non nulles | calcul H26 actuel | strictement inchangé |
| silence seul | ne suffit pas à `NO_BIRTH` | inchangé |
| ordre de décision | history → support → équivalence → positif → négatif → ambigu | inchangé |

Les clauses exactes à remplacer dans une future préinscription successeur sont
`measurement_definitions.spectrum.valid_total_power`,
`measurement_definitions.short_window_onset_rise.formula` et
`measurement_definitions.long_window_persistence.formula`. Les clauses
`causal_contract.previous_views_end_one_hop_earlier`,
`ambiguity_region.includes` et `decision_order` doivent être réaffirmées sans
modification.

## Invariants et absence de fuite

- hop `256`, vues previous exactement un hop avant, aucune lecture future ;
- quatre outcomes et ordre décisionnel inchangés ;
- seuils positifs/négatifs inchangés ;
- silence valide distinct du support invalide ;
- `current_short=0` ne peut jamais atteindre ratio, NNLS ou certificat ;
- `current_long=0` rend l'analyse longue invalide, masque la persistence et
  conduit à `AMBIGUOUS` avant les certificats ;
- silence précédent seul ne constitue jamais un certificat négatif ;
- `H01` conserve le bypass history et `A01` le bypass equivalence ;
- les cas N01-like non nuls conservent les mêmes calculs ;
- aucune règle ne dépend de `fixture_id`, `expected`, `family`, `category`,
  `ground_truth_onset` ou `latent_label`.

Le contrat conserve exactement les seuils `0.02`, `0.05`, `0.10`, `0.002`,
`0.005`, `0.001` et la marge `10.0`.

## Cas synthétiques déclaratifs

Le fichier
`configs/harmonic_censoring_h26_p0_remediation_synthetic_cases.json` définit
onze cas data-only : previous-short nul, previous-long nul, current-short nul,
current sous le plancher, masque invalide, parité non nulle, N01-like, bypass
history, priorité collision exacte, garde de fuite et current-long nul. Aucun
résultat ne vient du moteur.

Le choix pour `R-ZERO-003` est explicite : un current-short nul rend l'analyse
courante invalide et conduit à `AMBIGUOUS`, jamais à `NO_BIRTH` par absence.
`R-ZERO-011` impose symétriquement qu'un current-long nul rend la persistence
indisponible et le contexte requis invalide, puis conduit à `AMBIGUOUS` avant
tout certificat.

## Population et identités futures

La population `H26_SYNTHETIC_V1` reste une preuve historique immutable,
réutilisable en lecture seule pour forensique et comparaison de régression.
Elle est inéligible à une science successeur et ne sera jamais modifiée ou
rematérialisée dans le même namespace.

Identités proposées pour une future préinscription séparée :

```text
hypothesis_id = H27_ROLE_AWARE_ZERO_CONTEXT_V1
population_namespace = H27_SYNTHETIC_V1
test_namespace = H27_TEST_V1
```

Une nouvelle population, une nouvelle authority runtime et une nouvelle
authority/claim scientifique seront obligatoires. Aucun artefact H26 consommé
ne pourra servir d'autorisation.

## Interdictions et arrêt

Sont notamment interdits : branche P01, oracle leakage, epsilon caché, bruit
post-hoc, omission de `previous_short`, suppression ou réutilisation de la
claim, changement du résultat historique, édition silencieuse de la prereg
H26, écrasement du namespace existant et modification de seuil.

```text
documentary_state = H26_P0_REMEDIATION_DESIGN_CONTRACTED_PENDING_EXTERNAL_REVIEW_NO_IMPLEMENTATION
implementation_authorized = false
scientific_execution_authorized = false
retry_authorized = false
```

STOP externe obligatoire après ce package. Même si le design est approuvé,
une préinscription successeur séparée devra précéder toute implémentation.
