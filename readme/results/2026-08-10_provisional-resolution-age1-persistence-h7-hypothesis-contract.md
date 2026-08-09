# H7 — hypothèse de persistance same-pitch à l'âge 1

## Statut

```text
provisional_resolution_age1_persistence_hypothesis_defined
```

H7 est un contrat d'hypothèse, sans accès aux données et sans calcul. Il ne
valide aucun signal, target, resolver, seuil, âge de production, politique ou
V3.

## Signal unique

La question future est volontairement limitée : la probabilité frame du même
pitch, exactement une frame séquentielle après son `NoteOn`, distingue-t-elle
les vrais des faux NoteOn ?

```text
S1 = current_frame_probability à age_frames=1
     orientation : plus haut => NoteOn plus probablement vrai

S0 = frame_probability_at_noteon
     comparateur descriptif uniquement

D1 = S1 - S0
     diagnostic mécanistique de décroissance uniquement
```

S1 ne peut être combiné à aucun autre champ. D1 ne peut pas sauver un résultat
primaire négatif. Les champs audio, onset, harmonique, polyphonie, score et
raison candidat sont interdits comme filtre, strate ou feature H7.

Si le clock passe directement à un âge supérieur à 1, l'observation est
indisponible et comptée comme attrition. Aucun âge ultérieur n'est substitué ou
recherché.

## Target causal figé

La vérité n'entre jamais dans `ProvisionalObservation`. Pour le futur diagnostic
offline seulement, H7 réutilise les fonctions versionnées existantes :

- `truth_notes()` conserve les références `note_evaluation_valid` dont
  `end > start`;
- `decoder_event_time_s()` date la frame `i` à la fin de son hop,
  `(i+1)*hop_size/sample_rate`;
- `_event_matchability()` exclut les frames invalides/hors audio au lieu de les
  transformer en négatifs;
- `match_causal_note_ons()` traite les prédictions chronologiquement, exige le
  même pitch, interdit toute référence future, limite la latence à `250 ms`,
  choisit la dernière référence causale pending et impose le one-to-one.

Une prédiction présente dans `matches` reçoit `true_noteon=1`; une prédiction
présente dans `false_prediction_indices` reçoit `0`. Un événement ambigu,
dupliqué, invalide ou non partitionné échoue fermé ou est exclu selon la
sémantique existante. Aucune nouvelle règle de vérité ne peut être inventée.

## Métrique et décision préenregistrées

La métrique primaire future est `ROC-AUC(S1, true_noteon)`. Le signal sera
`age1_persistence_signal_demonstrated` seulement si les deux conditions passent :

```text
ROC-AUC globale >= 0,60
borne basse de l'IC 95 % group-resampled > 0,50
```

Sinon, si le test est valide, le verdict terminal est
`age1_persistence_signal_not_demonstrated`.

Le bootstrap futur échantillonne exactement `G` groupes avec remise par
réplicat et inclut toutes les observations de chaque groupe avec multiplicité.
Les réplicats mono-classe sont exclus. L'IC percentile bilatéral utilise
`[2,5 %, 97,5 %]`. Le nombre de réplicats, la seed et le minimum de réplicats
valides restent non résolus et devront être scellés avant toute métrique.

Le groupe doit provenir de `leakage_group_key()` et garder ensemble les captures
d'une même performance. Aucun bootstrap par ligne, frame, NoteOn ou recording
ne peut le remplacer. La préparation future devra prouver l'identité des
groupes; sinon H7 est `grouping_identity_not_established`.

## Données, attrition et états inconclusifs

Aucune cohorte n'est sélectionnée. Une future préparation séparée devra sceller
les recordings, groupes, manifeste, actifs, paramètres bootstrap et minimum
d'observations. La cohorte V2 indépendante consommée et le test verrouillé sont
interdits.

Le rapport futur devra compter les NoteOn considérés, ceux disposant exactement
de l'âge 1, les sauts de clock, les targets ambigus/non matchables et les valeurs
malformées/non finies. Aucune imputation n'est autorisée.

Les états inconclusifs sont distincts d'un résultat négatif : target non
définissable, groupe non prouvé, bootstrap insuffisant, observations âge 1
insuffisantes, target mono-classe ou exécution invalide. Aucun de ces états ne
déclenche un retry ou une expérience de remplacement automatique.

## Limite

Le contrat machine-readable est :
`configs/provisional_resolution_age1_persistence_h7_hypothesis_contract.json`.

La prochaine étape autorisée après revue est uniquement la préparation scellée
d'une future exécution discovery. Elle ne peut pas calculer les distributions,
choisir les paramètres après observation, ouvrir la cohorte V2 ou modifier le
décodeur/runtime.

Vérification contractuelle locale : `py_compile`, `git diff --check` et `105`
tests structurels/synthétiques ciblés réussis en `0,317 s`. Il ne s'agit pas
d'un calcul scientifique.
