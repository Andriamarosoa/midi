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

Un exemple est une tentative de NoteOn **émise**, pas une frame candidate. Les candidats éligibles mais non sélectionnés ou non émis sont masqués dans ce premier cycle. Les tentatives contiguës d'une même prise et même pitch sont réduites à l'épisode au score maximal. Chaque ligne conserve `gate_eligible`, `rank`, `selected`, `emitted_noteon`, `event_id`, frame, pitch, raison, score et support harmonique.

Les prises sont d'abord affectées avec `partition_train_groups()` et sa clé `leakage_group_key`, puis seulement minées : aucune répartition aléatoire de candidats n'est admise. Le label emploiera `latest_causal_same_pitch_one_to_one` avec latence maximale `250 ms`. Les features de la future tête sont strictement causales : frame/onset, score/raison/support du candidat, rang/sélection, état audio-onset et polyphonie active ; ni vérité ni futur ne peuvent être des entrées.

Avant minage, le mineur devra vérifier SHA du commit, manifeste train, checkpoint, YAML, config décodeur, thresholds et toute config audio. Il devra produire les comptes par corpus, partition et classe avant de pouvoir autoriser un smoke.
