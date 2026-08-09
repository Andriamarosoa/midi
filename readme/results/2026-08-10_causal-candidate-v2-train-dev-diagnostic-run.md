# Diagnostic V2 train/dev CPU : résultat exploratoire non promotionnel

Branche : `codex/independent-note-neural-v2`
Commit exécuté : `522acc1e71d8baeafcede67a3f14e71fece73f9b`

État : `complete_exploratory_non_promotional`. Le runner s'est arrêté après
son rapport et n'autorise aucune suite automatique.

## Exécution bornée et preuve brute

| Élément | Valeur vérifiée |
|---|---|
| Job Mac | `causal-candidate-v2-train-dev-retry-cpu-20260810` |
| Module | `src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic` |
| Device / timeout | CPU / `900 s` |
| Début / fin bruts worker | `2026-08-10T01:48:18Z` / `2026-08-10T02:00:18Z` |
| Durée / sortie | `720 s` / `exited_zero`, code `0` |
| Test verrouillé / validation historique | `false` / `0` prise |

Le stdout terminal contient `stop_after_report=true`, le stderr est vide et le
verrou lourd est libéré. Le rapport brut est conservé sur le Mac sous :

```text
/Users/amcarene/midi-worker/repository/tmp/
  causal_candidate_v2_train_dev_diagnostic_20260809/reports/
    train_events_1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325_causal_candidate_v2_train_dev_diagnostic.json
```

Il a aussi été rapatrié localement sous `tmp/local/mac_results/`. Source Mac
et copie locale sont identiques : `793 812` octets, SHA-256
`43e28b4ebfe33f5ad0f28be1c4b61704af8cebc08012458cbd645d3027b9acf9`.

## Provenance scellée et protocole

Le rapport atteste le manifeste `b28cb17…ed7`, le plan Policy A
`a8347e4e…685f4`, le registre d'actifs `12dd74f2…6507`, la politique V3
`db55930a…3683`, le checkpoint `1ce8ac44…1325`, le modèle V1
`b9320cd0…8a59e`, le standardiseur `0600aa1a…5e3b`, le YAML
`24528578…9804`, le décodeur référence `c16be482…5f96` et la politique audio
`45edbb71…cd3e`.

La cohorte est exactement train/dev : `6` GAPS, `6` Guitar-TECHS direct, `6`
Guitar-TECHS mic/amp et `12` GuitarSet. Le rapport confirme une inférence de
transcription commune par prise, des masques audio communs, deux états de
décodeur indépendants après divergence, le seuil V1 `0,31` inchangé et le
placement candidat `post_ranking_pre_noteon`.

## Décisions de porte V2

Les 30 diagnostics `causal_candidate_gate` donnent `1 281` candidats
post-sélection éligibles et `61` rejets (`4,76 %`) au seuil `0,31` :

| Corpus | Éligibles | Rejets V2 |
|---|---:|---:|
| GAPS | 581 | 10 |
| Guitar-TECHS direct | 359 | 33 |
| Guitar-TECHS mic/amp | 291 | 18 |
| GuitarSet | 50 | 0 |
| **Total** | **1 281** | **61** |

Ces valeurs concernent la porte V2 causale, non le champ historique
`independent_note_gate`. Les 61 décisions internes ne sont pas 61 NoteOn
supprimés : le décodeur est causal et stateful ; seuls les événements finaux
ci-dessous permettent d'interpréter l'effet.

## Résultats A/B globaux

| Mesure | Référence | V2 candidat | Delta candidat - référence |
|---|---:|---:|---:|
| NoteOn estimés | 17 594 | 17 584 | -10 |
| Faux NoteOn onset | 14 031 | 14 022 | -9 |
| NoteOn onset appariés | 3 563 | 3 562 | -1 |
| Notes onset manquées | 5 491 | 5 492 | +1 |
| F1 onset | 0,26741219 | 0,26743750 | +0,00002531 |
| Faux NoteOn causaux | 13 285 | 13 275 | -10 |
| Appariements causaux | 4 309 | 4 309 | 0 |
| Rappel causal à 250 ms | 0,47592224 | 0,47592224 | 0 |
| Faux NoteOn/min causal | 236,82663 | 236,64836 | -0,17827 |
| p50 causal | 46,95800 ms | 46,95860 ms | +0,00060 ms |
| p90 causal | 145,30012 ms | 145,56531 ms | +0,26519 ms |
| Retriggers | 677 | 677 | 0 |
| Fragments excédentaires | 796 | 796 | 0 |
| Faux positifs à intervalle harmonique | 1 449 | 1 447 | -2 |
| Faux NoteOn d'octave | 1 569 | 1 566 | -3 |

La tranche MIDI `40–51` est strictement inchangée : `577` appariements,
`2 968` faux positifs et F1 `0,21096892` dans les deux branches. Le p90 gagne
seulement `0,26519 ms`, inférieur à un hop de `5,80499 ms`.

## Résultats par corpus

| Corpus | Delta faux NoteOn onset | Delta F1 onset | Delta faux NoteOn causaux | Delta rappel causal | Delta p90 causal |
|---|---:|---:|---:|---:|---:|
| GAPS | -3 | -0,00012829 | -4 | 0 | +0,16608 ms |
| Guitar-TECHS direct | -2 | +0,00010071 | -2 | 0 | 0 ms |
| Guitar-TECHS mic/amp | -4 | +0,00019659 | -4 | 0 | 0 ms |
| GuitarSet | 0 | 0 | 0 | 0 | 0 ms |

## Interprétation et limite

Sur cette cohorte exploratoire, la même tête V1 et le même seuil appliqués
après ranking/sélection modifient enfin les événements MIDI et retirent neuf
faux NoteOn, sans dégrader le rappel causal ni la bande grave. Le gain reste
petit, ne touche pas GuitarSet et coûte un appariement onset standard.

La partition dev a contribué au choix de l'époque V1 : ce résultat n'est pas
une validation indépendante et ne justifie ni promotion, ni changement de
seuil, ni sélection de modèle. Les 12 validations historiques et le test
verrouillé restent fermés. La seule prochaine action autorisée est une revue
externe du rapport ; aucun fit, calibration/recalibration, nouveau V2,
validation historique, export ou live ne doit suivre automatiquement.
