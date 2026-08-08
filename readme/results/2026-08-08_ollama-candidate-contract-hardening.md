# Durcissement Ollama et contrat des candidats du décodeur

## Périmètre

Appliquer la revue des commits `6ae6d9d2`, `1fcb41ea` et du contrat
`90218d47`, sans connecter encore le minage au décodeur de production et sans
lancer de calcul expérimental.

Commit d'implémentation vérifié :
`af5437eebc4a1e41aebb6e5db546aea669befd11` sur
`codex/independent-note-neural-v2`.

## Correctifs Ollama

- `run` utilise `keep_alive=0`, puis demande explicitement le déchargement et
  interroge `/api/ps` avant de libérer `~/midi-worker/active.lock`.
- Le benchmark place également son déchargement vérifié dans un `finally`.
- Une impossibilité de prouver le déchargement conserve le verrou avec
  `requires_manual_inspection=true`, y compris lors d'une interruption pendant
  le nettoyage.
- Windows et Mac doivent avoir le même commit exact et des worktrees propres.
- Le prompt traverse SSH par stdin UTF-8 et n'apparaît plus dans les arguments
  du processus distant.
- L'API reste HTTP loopback, sans proxy ni redirection. Chaque composant d'un
  chemin de contexte est contrôlé contre le test verrouillé.
- Les rapports persistants omettent le corps des réponses et n'en gardent que
  le SHA-256 et la taille. L'affichage terminal demandé reste disponible.

## Correctifs du contrat candidat

- Le regroupement suit séparément `best_row` et `last_frame_index`; des scores
  décroissants sur des frames contiguës ne scindent plus un épisode.
- La clé d'épisode inclut prise, groupe de fuite, corpus, pitch et `event_id`.
- Le schéma contient maintenant les probabilités frame/onset, le score et la
  raison du candidat, le support harmonique, l'état onset audio et la
  polyphonie active.
- `post_gate_rank`, `post_gate_selected`, `emitted_noteon` et `event_id` sont
  explicitement séparés des features causales.
- Les lignes refusent les identifiants vides, types non JSON natifs,
  probabilités hors intervalle, valeurs non finies, rangs négatifs et états
  émission/sélection incohérents.
- `decoder.py` n'importe toujours pas ce module : aucun producteur, minage ou
  changement de décision du décodeur n'a été introduit.

## Vérifications

### Windows

- `python -B -m unittest tests.test_ollama_team
  tests.test_decoder_candidate_mining
  tests.test_mac_worker_transport_contract` : **38/38 réussis**.
- Compilation syntaxique en mémoire de quatre fichiers Python : réussie.
- Analyse syntaxique de `OLLAMA_TEAM.ps1` : réussie.
- `git diff --check` : réussi.

### Mac M4

- Checkout propre au commit exact `af5437ee` après `git pull --ff-only`.
- `python3 -B -m unittest tests.test_ollama_team
  tests.test_decoder_candidate_mining` : **23/23 réussis**.
- Appel réel du rôle `code_review` via le wrapper durci : terminé avec code 0,
  puis `active_lock=false`, `ollama_owner=null` et `running_models=[]`.
- Contexte Ollama :
  `scripts/local/ollama_team.py` SHA-256
  `7a4aa4c2b83eba99ee9e3fae221c8e20236c9acdd4f6f692481f7c338879d7e1`
  et `src/polyphonic/decoder_candidate_mining.py` SHA-256
  `4b92a7e8864507efb6b0c96ec30701ace1c2e683a8779935501a39b72de1609b`.
- Rapport local :
  `/Users/amcarene/midi/tmp/local/ollama_team/20260808T205831525138Z_code_review_qwen3-14b.json`,
  SHA-256
  `0da128ecd3c436aace1fcfe9de8ee2795b9fc14120880b46152ca08b45a1a2d6`.
  Les clés persistées excluent bien `response`; le rapport indique
  `response_characters=4150`, `locked_test_used=false` et le commit exact.

Le nom de cet artefact conserve l'heure brute du Mac, dont l'avance mesurée est
d'environ onze heures; il ne doit pas être lu comme une UTC réconciliée.

Le 14B n'a pas respecté la consigne de revue ciblée : il a produit un résumé
générique et cité un chemin inexistant. Ce résultat mesure une limite réelle du
modèle local et ne constitue pas une approbation.

## Revue externe

La revue ChatGPT reçue le 8 août approuve les commits `af5437ee` et `88a66ce`
sans défaut bloquant. Les 38 tests ciblés Windows ont été rejoués au commit
`88a66ce` et réussissent tous. Aucun code ni résultat expérimental n'a été
modifié pendant cette clôture documentaire.

La prochaine modification autorisée est limitée à l'instrumentation de
`decoder.py`, désactivée par défaut. Elle devra :

- capturer les features causales immédiatement avant la porte;
- ajouter rang, sélection et émission seulement après les décisions réelles;
- démontrer une parité événement par événement et état interne par état interne
  entre le décodeur sans collecte et le même décodeur avec collecte activée;
- produire des identifiants d'événement hors de l'objet public
  `PolyphonicMidiEvent`, avec une collecte bornée;
- figer l'encodage de `candidate_reason` avant tout entraînement;
- attribuer `source_id`, `group_id`, `capture_id` et la partition
  `fit/dev/calibration` avant tout futur minage, jamais après constitution de
  l'artefact.

Ces exigences sont des garde-fous pour le prochain commit; elles n'autorisent
encore aucun minage, entraînement, calcul validation, export, live ou accès au
test verrouillé.

## Décision

Le correctif est techniquement vérifié sur Windows et Mac. Aucun entraînement,
minage, validation officielle, export, live ou test verrouillé n'a été lancé.
La revue ChatGPT approuve le contrat durci. Une instrumentation isolée,
désactivée par défaut et couverte par les preuves de parité ci-dessus peut être
préparée dans un commit distinct; ce futur commit devra être revu avant tout
calcul.
