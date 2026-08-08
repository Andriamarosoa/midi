# Hypothèse — minage des candidats réels du décodeur

## Problème ciblé

La tête actuelle apprend des positives actives et des négatives harmoniques supervisées, alors que la porte du décodeur n'est consultée que pour ses propres candidats, avec support harmonique et état causal. Le résultat A/B nul à `0,01` suggère un décalage de population, non un défaut de câblage.

## Hypothèse

Une tête entraînée sur les candidats réellement proposés par le décodeur causal sur le split train distinguera mieux les faux NoteOn finaux des vraies notes indépendantes que la cible harmonique statique actuelle.

## Contrat proposé

1. Rejouer le checkpoint de base sur **train uniquement**, sans porte, et journaliser chaque candidat auquel le décodeur pourrait appliquer la porte : frame, pitch, score, raison, support harmonique, probabilité onset/frame et contexte causal.
2. Associer chaque candidat à la vérité de la même prise : positif si un NoteOn de même pitch est apparié causalement ; négatif dur si le candidat contribue à un faux NoteOn, avec un drapeau harmonique/octave lorsque applicable ; ignorer les candidats ambigus ou non supervisables.
3. Conserver `source_id`, `group_id`, `capture_id`, le split train et les identifiants de frame afin d'éviter toute fuite vers validation ou test.
4. Réentraîner seulement une tête légère sur ces exemples, avec équilibre explicite des négatifs durs et calibration interne issue du train ; le backbone reste gelé.
5. Avant toute validation officielle, vérifier sur un smoke train-only borné : couverture des candidats, distribution par corpus, absence de fuite, parité sauvegarde/rechargement et latence de la tête.

## Critère futur

Une éventuelle validation A/B devra utiliser une seule inférence par prise et un seuil fixé avant validation. Elle mesurera les faux NoteOn réellement retirés, les faux positifs harmoniques, rappel/F1, erreurs d'octave, graves MIDI 40–51, fragmentation, retriggers et latence. Aucun test verrouillé, export, live, sélection ou entraînement complet n'est autorisé par cette hypothèse seule.

## Décision actuelle

Cette note définit une piste, pas une autorisation de calcul. Elle doit être revue avant tout changement de labels, génération de candidats, smoke ou entraînement.

## Contrat exécutable pré-minage

Un exemple est une tentative de NoteOn **émise**, pas une frame candidate. Les candidats éligibles mais non sélectionnés ou non émis sont masqués dans ce premier cycle. Les tentatives contiguës d'une même prise, groupe, corpus, pitch et `event_id` sont réduites à l'épisode au score maximal. Le regroupement conserve séparément la meilleure ligne et la dernière frame observée, afin qu'une suite de scores décroissants ne crée pas de faux épisodes.

Chaque ligne déclare explicitement `frame_probability`, `onset_probability`,
`candidate_score`, `candidate_reason`, `harmonic_support`, la disponibilité et
la récence de l'onset audio, ainsi que la polyphonie active. `post_gate_rank`,
`post_gate_selected`, `emitted_noteon` et `event_id` restent des métadonnées
d'analyse postérieures à la décision et ne sont jamais des features de la
future tête. Des invariants refusent les identifiants vides, probabilités hors
de `[0,1]`, scores non finis, rangs négatifs et états émission/sélection
incohérents.

Les prises sont d'abord affectées avec `partition_train_groups()` et sa clé `leakage_group_key`, puis seulement minées : aucune répartition aléatoire de candidats n'est admise. Le label emploiera `latest_causal_same_pitch_one_to_one` avec latence maximale `250 ms`. Les features de la future tête sont strictement causales : frame/onset, score/raison/support du candidat, état audio-onset et polyphonie active ; ni vérité, ni futur, ni rang/sélection post-porte ne peuvent être des entrées.

Avant minage, le mineur devra vérifier SHA du commit, manifeste train, checkpoint, YAML, config décodeur, thresholds et toute config audio. Il devra produire les comptes par corpus, partition et classe avant de pouvoir autoriser un smoke.

Ce contrat corrigé reste volontairement isolé : il n'est pas encore importé
par `decoder.py`, ne produit aucun candidat et n'autorise aucun calcul.
