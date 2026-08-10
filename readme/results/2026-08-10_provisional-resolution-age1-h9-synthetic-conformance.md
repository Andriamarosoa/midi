# H9 — conformance synthétique du signal age-1 et de la cible causale

## Verdict

```text
age1_persistence_h9_synthetic_extractor_conformance_demonstrated
```

Statut terminal :

```text
provisional_resolution_age1_persistence_h9_synthetic_extractor_ready
```

Cette conclusion signifie uniquement que l'architecture passive S0/S1/D1, la
cible causale gelée et leur jointure exacte fonctionnent sur des entrées
synthétiques. Elle ne démontre aucune valeur prédictive de S1 et ne produit
aucune AUC, politique de résolution ou V3.

## Instrumentation passive

`PassiveAge1SignalCollector` est explicitement opt-in. Le constructeur du
décoder refuse sa composition avec :

- `provisional_state_resolver` ;
- `causal_candidate_gate` ;
- `independent_note_threshold` non nul.

Le collecteur observe le flux historique sans intervenir dans la génération,
le ranking, le contexte harmonique, la polyphonie, les transitions actives ou
les événements MIDI. Au début de chaque frame valide, avant les décisions de
release/retrigger/ranking/activation, il résout les événements en attente :

```text
frame courante = frame NoteOn + 1 → S1 exact et D1=S1-S0
frame courante > frame NoteOn + 1 → age1_observation_unavailable
```

Il n'interpole jamais et ne substitue jamais une frame ultérieure. Après les
décisions du hop, chaque vrai `note_on`, retrigger compris, crée une nouvelle
attente avec son S0 gelé. Si un retrigger arrive à `t`, l'ancien événement
same-pitch est d'abord observé à `t`, puis le retrigger crée une identité
distincte pour `t+1`.

Le schéma immuable contient exactement :

```text
frame_index, pitch, S0, age1_status, S1, D1
```

Aucun onset, audio, harmonique, score, raison, état de resolver ou target n'y
entre. Toutes les valeurs numériques présentes sont finies.

## Cible causale offline

`extract_exact_causal_age1_targets()` reçoit uniquement des événements et
références déjà fournis synthétiquement. Il réutilise directement :

- `decoder_event_time_s` ;
- `_event_noteon_reasons` ;
- `_event_matchability` ;
- `match_causal_note_ons` ;
- la latence maximale gelée de `250 ms`.

La population est le flux complet des NoteOn émis. Le matching reste causal,
same-pitch, one-to-one, et choisit la dernière référence same-pitch en attente.
Les frames invalides et événements hors audio sont exclus avec target nul. Une
coordonnée `(frame_index, pitch)` dupliquée échoue avant production.

Schéma cible exact :

```text
frame_index, pitch, true_noteon, target_status
```

## Jointure et attrition

La jointure pure exige l'égalité exacte et sans doublon des clés
`(frame_index, pitch)`. Son schéma scientifique est limité à :

```text
frame_index, pitch, S0, S1, D1, age1_status, true_noteon, target_status
```

L'aide d'agrégation ne compte que les cinq quantités d'attrition préenregistrées.
Elle ne calcule ni prévalence, ni AUC, ni IC, ni bootstrap.

## Preuves synthétiques

Les tests couvrent notamment : capture exacte à `t+1`, saut `t→t+2`, gel de
S0, D1 exact, retrigger same-pitch, parité événements/état entre décodeur nu et
instrumenté, chemins legacy/audio-aware, contexte harmonique, polyphonie,
release, retrigger, silence, saut `audio_hop_index`, causalité, mauvais pitch,
frontière `250 ms`, latest-pending, exclusions frame/audio, doublon fail-closed,
jointure exacte et refus des trois compositions qui changeraient la population.

Vérification locale : `py_compile`, `git diff --check` et `66` tests
synthétiques/contractuels ciblés réussis en `0,097 s`. Aucun test H9 n'a
besoin de TensorFlow, modèle, audio ou label réel.

## Portée scientifique

Les actifs H8 n'ont pas été ouverts par H9. Aucun signal, target ou équilibre
de classe réel n'a été observé. Aucune inférence, AUC ou réplication bootstrap
n'a été exécutée. Les indicateurs restent :

```text
scientific_execution_authorized=false
real_targets_extracted=false
real_signals_extracted=false
metrics_computed=false
h8_cohort_consumed=false
locked_test_used=false
consumed_v2_cohort_used=false
```

Une revue externe est requise avant tout contrat d'exécution scientifique.
