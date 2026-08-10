# H10 — clôture end-of-stream et métriques H7 synthétiques

## Verdict

```text
age1_persistence_h10_synthetic_metric_conformance_demonstrated
```

Statut terminal :

```text
provisional_resolution_age1_persistence_h10_synthetic_metric_engine_ready
```

Ce verdict signifie uniquement que la clôture du cycle de vie, l'AUC, le
bootstrap par groupes et la logique de verdict H7 sont déterministes sur des
données synthétiques. Il ne signifie pas que S1 est prédictif ou que H7 passe.

## Fin d'enregistrement fail-closed

`PassiveAge1SignalCollector.require_no_pending_age1_at_end()` doit être appelé à
la fin de chaque enregistrement. S'il reste un NoteOn sans frame séquentielle
réellement observée à `t+1`, il lève exactement :

```text
age1_signal_execution_invalid: unresolved_age1_pending_at_end_of_recording
```

Le pending reste intact. Aucune frame n'est synthétisée, la dernière frame n'est
pas substituée, l'événement n'est pas supprimé et il n'est pas reclassé en saut
d'horloge. Un vrai saut `t→t+2` conserve séparément le statut déjà gelé
`age1_observation_unavailable`.

## Ligne groupée

Le wrapper immuable contient uniquement :

```text
recording_key, corpus_category, leakage_group_key, scientific_row
```

Ces trois identités sont exclusivement des métadonnées de rapport et de
rééchantillonnage. Elles n'entrent pas dans S0, S1, D1, target ou un classifieur.

## Éligibilité primaire

Une ligne entre dans l'AUC S1 seulement si :

- `age1_status == age1_observation_available` ;
- `target_status == matchable` ;
- `true_noteon` vaut exactement `0` ou `1` ;
- S1 est fini.

Il n'y a aucune imputation. Moins de `200` lignes produit
`age1_signal_insufficient_valid_observations`. Une population mono-classe
produit `age1_signal_single_class`. Toute preuve malformed/non-finie déclarée
produit `age1_signal_execution_invalid` avant métrique.

## ROC-AUC exacte

L'implémentation average-rank est exactement équivalente à :

```text
P(S1_positive > S1_negative)
+ 0,5 × P(S1_positive == S1_negative)
```

Les targets doivent être binaires et les scores finis. Les égalités reçoivent
exactement un demi-crédit. Une seule classe est explicitement indéfinie. Les
cas synthétiques donnent `1,0` pour l'ordre parfait, `0,0` pour l'ordre inverse,
`0,5` lorsque tout est lié et `0,875` pour le cas mixte calculé à la main.

## Bootstrap Policy H8 exact

```text
RNG                       numpy.random.Generator(numpy.random.PCG64(721629268))
réplicats                 10000
unité                     leakage_group_key
groupes tirés/réplicat    G, avec remise
lignes                    toutes les lignes du groupe, avec multiplicité
réplicats valides minimum 9500
IC                        numpy.percentile([2.5,97.5], method="linear")
```

Une réplication mono-classe est invalide et exclue des percentiles. Si moins de
`9500` restent valides, le statut est `group_resampling_inconclusive`, sans
retry ni seed alternatif. L'API n'expose aucun override du nombre de réplicats,
du seed ou du minimum.

Les tests incluent plusieurs recordings dans un même groupe, des vues direct/mic
partageant un groupe, un grand groupe et plusieurs petits, et la répétition
complète des lignes lorsqu'un groupe est tiré plusieurs fois. L'ordre d'entrée
inverse produit un rapport JSON canonique byte-identique.

## IC, verdict et diagnostics

Le verdict primaire est positif uniquement si les deux conditions passent :

```text
global S1 ROC-AUC >= 0,60
borne basse IC95 % > 0,50
```

Les frontières `0,60` inclusive et `0,50` strictement exclue sont testées.
Sinon, lorsque l'expérience est valide, le verdict est
`age1_persistence_signal_not_demonstrated`.

S0 et D1 peuvent recevoir une AUC descriptive sans influencer le verdict.
L'orientation D1 est figée avant données comme
`higher_D1_predicts_true_noteon_persistence`, cohérente avec une persistance
plus forte du signal vrai. Les AUC par corpus sont non-gating ; un corpus
mono-classe reçoit `auc_unavailable_single_class`.

## Portée

Le commit se fonde sur H9 accepté au commit
`963cf72c8e60e2d669e659de037f910658637984` et scelle les blobs H9
`27026d368081fadc4fa282954428f0377020e723` et
`706f45d4579e6887d4a11d9f17eea9c59cae6280`.

Aucun actif H8, audio, label, modèle ou checkpoint n'a été ouvert. Aucun signal,
target, équilibre de classe ou résultat réel n'a été produit. Les tests
n'utilisent que des objets synthétiques. Les indicateurs restent :

```text
scientific_execution_authorized=false
real_targets_extracted=false
real_signals_extracted=false
real_metrics_computed=false
h8_cohort_consumed=false
locked_test_used=false
consumed_v2_cohort_used=false
```

Une revue externe est obligatoire avant tout contrat d'exécution H7 réel.

Le contrat H10 fait `3511` octets et a le SHA-256
`533c5eb5062666181a98885cc588ef10a46bbf36c3618aed794ba3facd911e0f`.

Vérification locale : `py_compile`, `git diff --check` et `71` tests
synthétiques/contractuels ciblés réussis en `5,032 s`. Cette commande exclut
volontairement le test structurel H8 afin de ne pas relire son artefact de
cohorte pendant la preuve H10.
