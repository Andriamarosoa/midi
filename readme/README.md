# Résumé unique — Guitar MIDI AI

> Dernière mise à jour manuelle : 2026-08-08
>
> Branche active : `codex/independent-note-neural-v2`
>
> Règle : ce fichier est le résumé chronologique unique du projet. Chaque
> étape terminée, active, suivante ou en anomalie doit y être inscrite.
## Objectif

Produire sur desktop un moteur causal audio de guitare vers MIDI, monophonique
et polyphonique, avec peu de notes fantômes, une latence compatible avec le
live et des entraînements reproductibles exécutés localement. Kaggle et Colab
ne sont plus utilisés sauf nouvelle autorisation explicite de l’utilisateur.

<!-- CURRENT_STATUS_START -->
## État courant

- Mise à jour : `2026-08-08T21:55:59+04:00`.
- Étape : `decoder_candidate_asset_evidence_contract`.
- Statut : `contrat d'empreintes audio/labels et correctif de lecture paresseuse
  vérifiés sur actifs synthétiques; revue externe requise avant toute
  préinscription réelle`.
- Résultat scientifique conservé : la tête `independent_note` précédente reste
  un résultat négatif, saturé près de 1, et ne doit promouvoir ni checkpoint ni
  seuil. Le test verrouillé reste fermé.
- Instrumentation candidat : `PolyphonicDecoder` accepte un collecteur optionnel
  `None` par défaut. Les features sont figées avant la porte; rang, sélection,
  émission et `event_id` ne sont ajoutés qu'après les décisions réelles. Le
  buffer est borné et drainable, tout débordement invalide le batch, et une
  erreur de collecte est mémorisée sans bloquer les événements MIDI. Une frame
  entière est remise en un seul batch après toutes ses décisions; une
  contention du collecteur échoue immédiatement sans attendre son verrou.
- Le snapshot manifeste lit et hache une fois les octets CSV puis construit les
  mêmes objets complets `ManifestItem` qui seront fournis à `PolyphonicCorpus`
  et au collecteur. Les chemins relatifs sont ancrés au manifeste. Les copies
  de snapshot/capacité validée, les chemins substitués et les wrappers de plan
  forgés échouent fermé avant toute collecte.
- Le plan canonique est persistant et immuable : écriture sans écrasement,
  relecture stricte, SHA du plan dans chaque batch, et re-vérification avant
  collecteur, ouverture ou agrégation. Le mineur train-only refusera aussi un
  groupe partagé entre train et validation.
- Preuve d'actifs : avant toute ouverture future, le contexte exigera un
  registre canonique, persistant et attesté des tailles/SHA-256 audio et labels
  de chaque capture train, lié au même manifeste, plan, `audio_member` et
  partition. Les labels sont rehachés juste avant leur lecture par le
  constructeur et l'audio juste avant son véritable chargement paresseux par
  `corpus.audio()`; le chemin `.npy` protégé ne conserve pas de `mmap` après
  cette vérification. Une couverture incomplète, un fichier modifié, un wrapper
  forgé ou des octets du registre modifiés échouent fermé. Aucune preuve réelle
  n'a encore été créée.
- Chaque ligne future porte la provenance immuable complète : `source_id`,
  `dataset_id`, `group_id`, `capture_id`, clé de fuite et partition. Les lots
  portant un autre manifeste/plan, une prise rejouée, un `event_id` dupliqué ou
  une couverture incomplète de partition seront refusés.
- Les codes de raisons existants du live sont centralisés sans changement. Les
  `event_id` v2 sont déterministes par identité physique/frame/pitch (la
  partition est volontairement exclue) et restent hors de
  `PolyphonicMidiEvent`.
- L'unité d'apprentissage est désormais définie : un vrai NoteOn
  `gate_eligible=True` et `emitted_noteon=True`. Le collapse temporel est
  supprimé; deux NoteOn réels restent distincts et un `event_id` dupliqué rend
  un futur artefact invalide.
- Infrastructure Ollama : le commit `af5437ee` conserve le verrou partagé
  jusqu'au déchargement vérifié, refuse les worktrees sales et les redirections,
  transporte le prompt par stdin, contrôle tous les composants des chemins et
  ne persiste plus le corps des réponses.
- Vérification instrumentation Windows : 86 tests ciblés réussis. Par rapport
  au décodeur approuvé `f9ed9d0`, 512 frames couvrant porte active/inactive et
  voie legacy/causale ont une parité exacte des événements et de tout l'état
  décisionnel, y compris reset et panic.
- Vérification Mac : checkout propre au commit
  `f7514228800d8ad15db7d047dcadfbf8640cf4ee`; les mêmes 86 tests réussissent
  en 0,604 s (`OK`, deux tests Windows-only ignorés) et la compilation des six
  fichiers Python touchés réussit.
- Microbenchmark borné dense : ancien décodeur 175,77 µs/frame, nouveau chemin
  désactivé 162,53 µs/frame (aucune régression mesurée), collecte activée
  260,64 µs/frame, soit +98,11 µs et 1,69 % du hop de 5,805 ms.
- Étiquettes futures : les seuls exemples de fit sont les NoteOn gate-éligibles
  et émis. Le matcher causal same-pitch une-à-une reçoit cependant tous les
  NoteOn valides du flux réel, retriggers inclus, à la fin du hop et à 250 ms
  inclusifs, avant projection vers le fit. Un retrigger same-pitch ne peut donc
  plus laisser une référence disponible pour rendre positif un candidat tardif.
  Les frames invalides ou hors audio ne consomment pas de référence; les
  retriggers restent comptés comme exclusion explicite; toute autre NoteOn sans
  trace ou erreur de collecteur invalide le lot. Les features de fit sont
  projetées strictement depuis `CAUSAL_FEATURES`.
- Vérification du protocole Windows : compilation Python, `git diff --check`
  et **128 tests ciblés réussis en 7,438 s** ont été archivés avant le commit
  précédent. Le détail et la commande exacte sont archivés dans le rapport.
- Vérification du correctif retrigger Windows : compilation Python,
  `git diff --check` et **131 tests ciblés réussis en 8,993 s**. Les deux
  ordres same-pitch retrigger/candidat, le retrigger invalide et l'intégrité du
  plan au `drain()` sont couverts dans le nouveau rapport.
- Revue externe du commit `9e666eb0f83d556a2b74809d0ffee47c51966fa1` :
  **approuvée**. Un rejeu Windows indépendant de la même suite ciblée obtient
  aussi **131 tests réussis en 9,336 s**. Cette seconde durée est une mesure
  d'exécution distincte; elle ne remplace pas l'évidence historique à 8,993 s.
- Vérification du correctif d'actifs Windows : compilation Python, `git diff
  --check` et **136 tests ciblés réussis en 9,718 s**, dont un parcours réel
  synthétique préinscription -> relecture -> ouverture, le rejet d'une mutation
  audio après construction mais avant `corpus.audio()`, et le cache de conteneur
  audio partagé. La vérification initiale du contrat à 134 tests en 9,429 s
  reste archivée dans son rapport propre.
- Limite avant minage : aucun plan réel ni artefact candidat n'a été généré ou
  persisté; aucun décodeur ni mineur n'a été exécuté. Les chemins sont liés au
  snapshot manifeste, mais la preuve préenregistrée des octets d'audio/labels
  est une précondition distincte avant leur première ouverture réelle.
- `locked_test_used=false`; aucun entraînement, minage, calcul validation,
  export ou live n'a été exécuté.
- Rapports :
  `readme/results/2026-08-05_decoder-candidate-mining-hypothesis.md`,
  `readme/results/2026-08-08_ollama-local-team.md` et
  `readme/results/2026-08-08_ollama-candidate-contract-hardening.md`, puis
  `readme/results/2026-08-08_decoder-candidate-instrumentation.md`,
  `readme/results/2026-08-08_decoder-candidate-instrumentation-review.md` et
  `readme/results/2026-08-08_decoder-candidate-provenance-contract.md`, puis
  `readme/results/2026-08-08_decoder-candidate-snapshot-label-protocol.md` et
  `readme/results/2026-08-08_decoder-candidate-retrigger-causal-matching-fix.md`,
  puis `readme/results/2026-08-08_decoder-candidate-retrigger-causal-matching-review.md`
  et `readme/results/2026-08-08_decoder-candidate-asset-evidence-contract.md`,
  puis `readme/results/2026-08-08_decoder-candidate-asset-evidence-lazy-audio-fix.md`.

## Prochaine action réelle

1. Faire relire le correctif de chargement paresseux du contrat d'empreintes,
   sans créer de plan ou de registre réel.
2. Après approbation explicite seulement, préenregistrer sur le Mac le plan
   réel et la preuve versionnée des actifs audio/labels, puis faire relire ces
   deux éléments avant la toute première collecte.
3. Ne promouvoir ni checkpoint ni seuil, et ne lancer aucun minage avant la
   revue de la préinscription réelle.
4. Conserver le test verrouillé fermé; aucun entraînement, validation, export
   ou live n'est autorisé par cette étape.

## État archivé — dual-stream du 30 juillet (remplacé)

- Mise à jour : `2026-07-30T08:13:17+04:00`
- Étape : `dual_stream_bass_local_train`
- Statut historique au 30 juillet : `en cours à cet instant`, désormais
  remplacé et non actif.
- Détail : décision permanente appliquée : aucun upload, appel API, kernel
  ou calcul Kaggle/Colab ne sera utilisé sans nouvelle autorisation explicite.
  Le desktop dispose d'un i7-1355U, de 15,64 Gio de RAM et de TensorFlow
  2.15.1 CPU sans GPU CUDA. Les 572 enregistrements train et 182 validation,
  soit 754 paires audio/labels, sont présents sous `data/processed`; les 114
  enregistrements test restent verrouillés. L'initialisation locale utilise
  `polyphonic_multisource_20260728_192326/epochs/epoch-08.keras`, 4 272 336
  octets, SHA-256
  `aaec718882bd1344461ecffa3475dceb10edcad5b2e265b1494977f6e1c9834c`.
  `model.summary()` est remplacé par `model_overview.json` et une seule ligne
  `MODEL_OVERVIEW` flushée. Les 308 tests de non-régression passent. Le smoke
  minimal 256/128 puis le smoke représentatif local 8 192/2 048 passent avec
  reprise A/B, `locked_test_used=false`, génération 6, 342 996 paramètres et transfert
  des 25 couches compatibles; les 7 nouvelles couches graves sont
  correctement initialisées. Le smoke représentatif entraîne à 169,89
  exemples/s sur 128 batches et valide en environ 4 s. La projection issue de
  ces mesures est d'environ 3 h 10 pour 8 époques, avec une marge pratique de
  4 à 6 h en cas de chauffe ou d'activité concurrente.
- Surveillance : train complet local démarré à `08:08:46+04:00`, run
  `polyphonic_dual_stream_bass_20260730_080855`, PID lanceur 11256 et PID
  TensorFlow 41032. Au batch 650/3 750 de l'époque 1/8, le débit réel est
  171,68 exemples/s et la projection restante est de 3 h 02. La génération
  recovery A est fraîche à `08:13:04+04:00`; aucune erreur n'est présente.
  L'automation `suivi-train-local-dual-stream` vérifie localement toutes les
  dix minutes et ne signale que les fins d'époque, pauses, anomalies ou la fin.
  Logs :
  `tmp/local/dual_stream_bass_train_20260730_080846.stdout.log` et
  `.stderr.log`. Le test verrouillé reste exclu.

## Étapes archivées — plan dual-stream du 30 juillet (non actif)

> Ces étapes appartiennent au plan dual-stream remplacé ci-dessus. Elles ne
> doivent ni être exécutées ni interprétées comme le plan actuel.

1. Capturer la même suite live sans puis avec capodastre, au même niveau et avec WAV/trace complète : cordes graves isolées, accords ouverts/barrés, strums lents/rapides, octaves et harmoniques. Comparer énergie fondamentale/partiels, probabilités par hauteur, erreurs d'octave et notes manquantes. Cette capture servira au diagnostic, pas au test verrouillé.
2. Conserver le remplacement par transposition +12/−12 uniquement comme diagnostic offline désactivé ; ne pas confondre ce test négatif avec la future architecture à deux flux.
3. Laisser achever l'unique train CPU local de 8 époques, avec un worker, logs
   flushés, reprise A/B toutes les 32 batches et arrêt récupérable à six heures.
4. Après achèvement seulement, classer et sélectionner sur validation, puis
   comparer les graves MIDI 40–51, les erreurs d'octave, les accords et chaque
   corpus.
5. Dans une expérience suivante seulement, corriger le contrat des masques harmoniques, sur-échantillonner les onsets/accords MIDI 40–51 sans réduire le reste et ajouter un objectif fondamentale/résonance fondé sur `note_id` et les colonnes harmoniques existantes.
6. Ouvrir le test verrouillé une seule fois après la sélection finale, puis produire le lanceur desktop stable et ses limites documentées.
<!-- CURRENT_STATUS_END -->

## État technique consolidé
### Produit monophonique

- Périmètre accepté : guitare propre monophonique, MIDI 40–76.
- Parité TFLite et ONNX validée.
- Inférence compatible avec le live.
- Limite : une sortie softmax unique ne transcrit pas les accords.
### Produit polyphonique V2.2
- Entrée causale : 4096 échantillons à 44,1 kHz, hop 256.
- Le V2.2 n'a pas trois branches de fenêtres explicites : contexte principal
  4096 et branche onset limitée aux 512 derniers échantillons seulement.
- Sorties : notes actives, onsets, amplitudes harmoniques et offsets en cents.
- Ancien train : 8 époques, 240 000 exemples par époque.
- Checkpoint sélectionné : époque 8.
- F1 frame validation : 0,5381.
- F1 onset événementiel pondéré : 0,2294.
- Limites : notes fantômes, fragmentation, offsets imprécis et domaine
  Guitar-TECHS plus faible.
- Le décodeur desktop a amélioré le F1 onset global de 0,1535 à 0,1751, au
  prix d’un rappel plus faible.
- TFLite float16 batch 1 : p95 de 2,17 ms, hors latence audio matérielle.
### Données reconstruites

- Toutes les données dérivées sont sous `data/processed`.
- 868 enregistrements : 572 train, 182 validation, 114 test verrouillé.
- Sources du manifest polyphonique : GuitarSet, GAPS et Guitar-TECHS
  direct/micro.
- IDMT-SMT-Guitar est conservé pour le diagnostic, mais n’entre pas dans le
  train polyphonique actuel.
- 62 476 notes disposent d’une supervision harmonique.
- Aucune fuite de groupe détectée entre les splits.
### Limite harmonique à corriger

`note_id` relie les notes aux mesures harmoniques. Cependant,
`note_harmonic_present` sert actuellement principalement de masque : les
harmoniques absentes ne constituent pas suffisamment d’exemples négatifs.
Le modèle ne possède donc pas encore de classification explicite
fondamentale contre harmonique/résonance. Lorsqu'une fréquence supérieure est
à la fois un partiel d'une fondamentale plus grave et une note volontairement
jouée, le décodeur ne peut l'identifier que partiellement : il la conserve si
elle possède un onset propre suffisamment fort, mais peut la supprimer lorsque
cet onset est faible. Une protection d'accord sans preuve indépendante serait
également dangereuse, car elle transformerait des résonances en notes fantômes.
## Journal des étapes
<!-- JOURNAL_START -->
- 2026-07-22 — **terminé** — entraînement polyphonique multi-source V2.2 sur
  GuitarSet, GAPS et Guitar-TECHS ; époque 8 sélectionnée, test verrouillé.
- 2026-07-22 — **terminé** — classement validation-only, sélection musicale,
  exports TFLite/ONNX et contrôles de parité.
- 2026-07-27 — **terminé** — validation du décodeur desktop ; diminution des
  notes fantômes et harmoniques parasites, mais rappel encore insuffisant.
- 2026-07-28 — **terminé** — suppression du périmètre Android, nettoyage des
  anciennes versions et adoption des branches Git.
- 2026-07-28 — **terminé** — reconstruction reproductible de
  `data/processed`, sans fuite entre train, validation et test.
- 2026-07-28 — **terminé** — préparation du pipeline Kaggle privé :
  packaging sans test, smoke/train P100, reprise, supervision et récupération.
<!-- PROJECT_TASK:kaggle_training_dataset_upload:START -->
- 2026-07-28 — **terminé** — `kaggle_training_dataset_upload` : pipeline Kaggle P100 validé avec succès sur le compte `miranacareneandrisoa`, commit `8bccadc6`, TensorFlow 2.20/Keras 3. Le smoke attache les 16 shards, charge les NPY tronqués, entraîne une époque de 256 exemples, valide sur 128 exemples et produit `best.keras`, `last.keras`, `final.keras`, l'archive et le rapport. Archive 17111040 octets, SHA-256 `830aa93d81d814a2f3109b9a62e26612348d90f53c3e4000078c6bcd95070117` conforme ; `locked_test_used=false`. Les quatre corpus sont présents dans les pools. Les métriques smoke (val_frame_micro_f1=0.061205, val_onset_micro_f1=0.002302) vérifient l'exécution, pas la qualité.
<!-- PROJECT_TASK:kaggle_training_dataset_upload:END -->
<!-- PROJECT_TASK:checkpoint_validation_selection:START -->
- 2026-07-28 — **terminé** — `checkpoint_validation_selection` : Sélection musicale Kaggle validation-only terminée et validée sur 12 enregistrements équilibrés (3 par corpus), candidate unique epoch-08. Archive 51548160 octets, SHA-256 ec9725179092a10d43af2dbbef9b61cc69f632c6038bc1b567041f3c120f7d28 conforme ; selection.json, selected.keras, thresholds.json et decoder_config.json présents ; selected.keras identique à epoch-08 ; locked_test_used=false. Métriques : F1 onset global 0,173294, F1 onset pondéré 0,233170, F1 onset+offset pondéré 0,127564. Limites réelles : 3160 faux positifs, 2994 notes manquantes, 71,44 faux NoteOn/min ; F1 onset Guitar-TECHS direct 0,039755 et micro 0,052980, contre GuitarSet 0,333844 et GAPS 0,212366. Latence causale NoteOn p50 65,63 ms, p90 164,74 ms.
<!-- PROJECT_TASK:checkpoint_validation_selection:END -->
<!-- PROJECT_TASK:skill_project_contract:START -->
- 2026-07-28 — **terminé** — `skill_project_contract` : skill
  guitar-audio-midi-researcher enrichi avec le contrat permanent du projet,
  puis rendu autonome : lecture complète obligatoire de `readme/README.md`,
  vérification Git/artifacts avant toute action, interrogation des compteurs
  réels à chaque demande de progression sans extrapolation, puis mise à jour
  de la même entrée de journal en fin d’étape ; validation réussie
<!-- PROJECT_TASK:skill_project_contract:END -->
<!-- PROJECT_TASK:desktop_candidate_validation:START -->
- 2026-07-29 — **terminé** — `desktop_candidate_validation` : Checkpoint Kaggle epoch-08 installé localement et exporté : parité TFLite/ONNX 100 % sur 96 exemples, ONNX p95 3,25 ms. Le TFLite est bit à bit identique au bundle stable (SHA-256 4a4df49d...), donc les poids sont reproduits ; seuls les seuils diffèrent. Deux benchmarks TFLite stricts restent instables malgré des p95 sous 5,80 ms. Après correction d’un WAV Guitar-TECHS temporaire écrêté, l’A/B donne F1 onset 0,0882 vers 0,0870 et faux positifs 33 vers 34 ; GuitarSet donne 0,2966 vers 0,3025 mais onset+offset 0,2542 vers 0,2437 et fragmentation 2 vers 4. Candidat non promu ; bundle v2_2_0 conservé. Runtime corrigé : fallback à 1 thread si la recommandation benchmark est absente. Test verrouillé non utilisé.
<!-- PROJECT_TASK:desktop_candidate_validation:END -->
<!-- PROJECT_TASK:adaptive_attack_validation:START -->
- 2026-07-29 — **terminé** — `adaptive_attack_validation` : Audit WAV Guitar-TECHS corrigé : l'ancien extrait était écrêté à 99,94 % par une conversion int16 incorrecte dans un script temporaire ; train et évaluations officielles non affectés. Ablation validation-only sur les 12 enregistrements exacts : faux NoteOn causaux 2118 vers 1389 (-34,4 %), erreurs d'octave 444 vers 310, F1 onset pondéré 0,2332 vers 0,2409 et Guitar-TECHS direct 0,0398 vers 0,0459. Régression : rappel causal 0,4636 vers 0,3968, F1 GAPS 0,2124 vers 0,1824 et F1 global 0,1733 vers 0,1604. Pipeline p95 3,30 à 4,17 ms sous le hop 5,80 ms, sans délai algorithmique. Candidat installé séparément, bundle stable inchangé, test verrouillé non utilisé.
<!-- PROJECT_TASK:adaptive_attack_validation:END -->
<!-- PROJECT_TASK:live_ab_adaptive_attack:START -->
- 2026-07-29 — **anomalie** — `live_ab_adaptive_attack` : L'audit du train annulé confirme un goulot d'étranglement I/O, pas une erreur CUDA. Le smoke P100 représentatif du snapshot `834b318a` est `COMPLETE` : staging 1 508 fichiers/8 643 963 647 octets en 208,70 s, entraînement-validation 8 192/2 048 en 29,85 s à 274,73 exemples/s, archive 17 745 920 octets et SHA-256 vérifié, `locked_test_used=false`; projection mesurée 2,00 h pour 8 époques avec staging. La reprise exacte et le transport inter-kernels sont poussés; le garde 16 shards du commit `5a5a2eff` porte le total à 305 tests. Le retry recovery P100 est `COMPLETE` : archive 26 685 440 octets et SHA-256 conformes, `locked_test_used=false`, roundtrip Keras 3 strict validé en génération 6/slot B avec Adam 128 et LR conservé. La phase 1 `guitar-midi-recovery-phase1-5a5a2eff` s'est figée à 170,3485 s pendant `model.summary()`, avant tout marqueur de reprise ou entraînement, puis a été supprimée manuellement le `2026-07-30`; aucun output terminal n'était publié et le quota final vérifié est 24,00/30 h. Les doublons du log sont un défaut de collecte Kaggle, pas la preuve de deux processus. Le correctif poussé `68084816` ajoute les jalons `RECOVERY_PREFLIGHT`, borne le processus entier à 10 minutes et rend `PROCESS_TIMEOUT` explicite. La provenance Kaggle est aussi corrigée en lisant `source_metadata.json` à la racine du dataset avant le fallback; 307 tests passent. Prochaine porte : supprimer l'affichage tabulaire de `model.summary()` dans le cloud, valider localement, publier le nouveau snapshot, puis lancer une seule phase 1 diagnostique; aucune phase 2 avant archive validée. MCP bloqué par HTTP 403 `oauthClients.use`. Test verrouillé exclu.
  - Surveillance `2026-07-30T07:52:29+04:00` : terminée; le slug est inaccessible et absent de la liste réelle des kernels. Aucune relance effectuée.
  - Mise à jour `2026-07-30T08:05:22+04:00` : la porte cloud
    précédente est annulée. Le contrat persistant interdit désormais Kaggle
    et Colab sans nouvelle autorisation explicite. `model.summary()` est
    remplacé par un aperçu compact; le smoke CPU local représentatif
    8 192/2 048 passe à 169,89 exemples/s, reprise A/B génération 6,
    `locked_test_used=false`. Le train complet sera local, unique et
    récupérable. Les 308 tests de non-régression passent.
  - Démarrage `2026-07-30T08:08:46+04:00` : run local
    `polyphonic_dual_stream_bass_20260730_080855`, PID TensorFlow 41032,
    époque 1/8, reprise A/B toutes les 32 batches et budget récupérable de
    six heures. Au batch 50/3 750, débit 151,25 exemples/s et projection
    dynamique 3 h 31. Test verrouillé exclu.
  - Surveillance `2026-07-30T08:13:17+04:00` : batch 650/3 750 de
    l'époque 1/8, 171,68 exemples/s, environ 3 h 02 restantes, recovery A/B
    valides et aucune erreur. L'automation locale
    `suivi-train-local-dual-stream` contrôle le run toutes les dix minutes
    sans utiliser Kaggle ni le test verrouillé.
<!-- PROJECT_TASK:live_ab_adaptive_attack:END -->
<!-- PROJECT_TASK:ollama_local_team:START -->
- 2026-08-08 — **terminé** — `ollama_local_team` : routeur local versionné
  pour `qwen3:8b`, `qwen3:14b` et `qwen3.6:latest`, appelé par SSH depuis
  Windows et partageant le verrou atomique du worker TensorFlow. Le correctif
  `af5437ee` maintient désormais ce verrou jusqu'au déchargement confirmé,
  refuse les worktrees sales, les proxies/redirections et tout composant de
  chemin test verrouillé, transporte les prompts par stdin et retire les corps
  de réponse des rapports persistants. Validation cumulée du correctif : 38
  tests Windows et 23 tests Mac, appel réel suivi de
  `active_lock=false/running_models=[]`, `locked_test_used=false`. La réponse
  générique du 14B n'est pas une revue valide. L'API directe réseau reste
  fermée sur `127.0.0.1:11434`; aucun modèle local ne possède l'autorité
  d'éditer, de commiter ou de remplacer les preuves réelles.
<!-- PROJECT_TASK:ollama_local_team:END -->
<!-- PROJECT_TASK:decoder_candidate_mining_contract:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_mining_contract` : le
  contrat isolé corrige le découpage des épisodes avec `best_row` et
  `last_frame_index`, ajoute les features causales manquantes, sépare les
  métadonnées post-porte et impose des invariants JSON fail-closed. Les scores
  décroissants, les `event_id` distincts et les états incohérents sont testés.
  Les commits `af5437ee` et `88a66ce` sont approuvés par la revue externe et les
  38 tests ciblés Windows ont été rejoués avec succès. Aucun branchement dans
  `decoder.py`, minage, entraînement ou calcul validation n'a été effectué;
  test verrouillé fermé. La prochaine tâche distincte est une instrumentation
  désactivée par défaut, soumise à une nouvelle revue avant tout calcul.
<!-- PROJECT_TASK:decoder_candidate_mining_contract:END -->
<!-- PROJECT_TASK:decoder_candidate_instrumentation:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_instrumentation` : collecteur
  optionnel désactivé par défaut ajouté aux voies legacy et causale. Snapshot
  pré-porte immuable, métadonnées post-décision, identifiants déterministes hors
  événement MIDI, encodage des raisons compatible avec le live, buffer borné,
  overflow fail-closed, remise par frame non bloquante et erreur de collecte
  fail-open. Les 86 tests Windows et Mac passent; le Mac ignore explicitement
  deux tests Windows-only. Les 512 frames sont identiques au décodeur `f9ed9d0`
  pour événements et état. Le chemin désactivé ne montre aucune régression
  mesurable; l'overhead activé est 98,11 µs/frame dans le benchmark dense. Mac
  propre au commit exact `f751422`. Revue de clôture de `f751422` et
  `d4492c3` approuvée : les 86 tests documentés sont rejoués localement avec
  succès (`86/86`, 6,895 s), l'arbre est propre et aucun processus scientifique
  n'est actif sur Windows ou Mac. La parité instrumentation désactivée/activée,
  les snapshots pré-porte, la remise non bloquante et les erreurs fail-open
  sont confirmés. Aucun minage, entraînement, validation, export, live ou test
  verrouillé n'est autorisé par cette clôture.
<!-- PROJECT_TASK:decoder_candidate_instrumentation:END -->
<!-- PROJECT_TASK:decoder_candidate_provenance_contract:START -->
- 2026-08-08 — **terminé** — `decoder_candidate_provenance_contract` : sans
  calcul scientifique, le protocole v1 est complété par le snapshot manifeste
  attesté, le plan canonique immuable, le contexte train-only et les labels
  causales. Les mêmes objets `ManifestItem` du CSV hashé alimentent le corpus
  et le collecteur; copies de snapshot/capacité/plan, chemins substitués,
  mélange de SHA, duplicats de prises/IDs et couverture de partition incomplète
  échouent fermé. Les labels utilisent un matcher same-pitch strictement causal
  (250 ms, fin de hop), excluent frames invalides et retriggers documentés, et
  refusent toute autre trace manquante ou erreur de collecteur. Les features
  sont projetées strictement hors cible/provenance/post-porte. Tests Windows :
  compilation, diff propre et suite ciblée complète OK; résultat exact archivé
  dans `2026-08-08_decoder-candidate-snapshot-label-protocol.md`. Aucun plan
  réel, artefact, minage, entraînement, validation, export, live ou test
  verrouillé n'a été produit. Les empreintes des actifs audio/labels restent à
  préenregistrer avant toute ouverture réelle. La revue de `a06e9641` a trouvé
  un faux positif de labels : un retrigger same-pitch exclu du fit ne consommait
  pas sa référence avant le matching d'un candidat ultérieur. Le correctif
  applique désormais le matcher à tous les NoteOn valides du flux avant de
  projeter uniquement les résultats entraînables, et sépare les matches complets
  des matches exclus du fit. Il exige aussi un plan réellement persistant pour
  construire la capacité collecteur et le revérifie au `drain()`. Compilation,
  `git diff --check` et 131 tests ciblés Windows passent en 8,993 s, puis un
  rejeu indépendant passe en 9,336 s. La revue externe du commit `9e666eb0`
  est approuvée. Aucune donnée projet n'a été ouverte; la prochaine étape est
  uniquement la préinscription réelle, soumise à une nouvelle revue avant tout
  minage.
<!-- PROJECT_TASK:decoder_candidate_provenance_contract:END -->
<!-- PROJECT_TASK:decoder_candidate_asset_evidence_contract:START -->
- 2026-08-08 — **en revue** — `decoder_candidate_asset_evidence_contract` :
  ajout sans calcul scientifique d'un registre canonique d'empreintes pour les
  actifs que le futur mineur pourrait ouvrir. Chaque entrée train lie identité
  physique, partition préassignée, `audio_member`, taille et SHA-256 du
  conteneur audio et des labels; aucun chemin hôte n'est persisté, le manifeste
  déjà hashé restant son ancre. Le registre est écrit sans écrasement, relu et
  attesté; le contexte refuse d'ouvrir tout corpus sans ce registre. La revue
  de `7440d093` approuve le format mais a relevé la fenêtre du chargement audio
  paresseux. Le correctif vérifie désormais les labels à l'entrée du
  constructeur et l'audio à l'entrée de `corpus.audio()`. Un parcours
  synthétique réel `pre_register -> reload -> open_recording` prouve le refus
  d'un audio muté après construction du corpus; le cache de conteneur partagé
  est aussi couvert. Compilation, `git diff --check` et 136 tests ciblés
  Windows passent en 9,718 s. Aucun manifeste réel, plan réel, actif projet,
  minage, entraînement, validation, export, live ou test verrouillé n'a été
  ouvert ou produit. Revue externe requise avant la préinscription réelle sur
  le Mac.
<!-- PROJECT_TASK:decoder_candidate_asset_evidence_contract:END -->
<!-- JOURNAL_END -->
## Rapports détaillés

- [2026-07-22 — entraînement polyphonique multi-source](results/2026-07-22_polyphonic-training.md)
- [2026-07-27 — validation du décodeur desktop polyphonique](results/2026-07-27_polyphonic-desktop-validation.md)
- [2026-07-28 — état du produit desktop monophonique](results/2026-07-28_mono-desktop-release.md)
- [2026-07-28 — reconstruction de `data/processed`](results/2026-07-28_processed-reconstruction.md)
- [2026-07-28 — incident de publication Kaggle](results/2026-07-28_kaggle-upload-incident.md)
- [2026-07-29 — validation du candidat desktop sélectionné](results/2026-07-29_desktop-candidate-validation.md)
- [2026-07-29 — validation de l’attaque causale adaptative](results/2026-07-29_adaptive-attack-validation.md)
- [2026-08-05 — hypothèse de minage des candidats du décodeur](results/2026-08-05_decoder-candidate-mining-hypothesis.md)
- [2026-08-08 — équipe Ollama locale](results/2026-08-08_ollama-local-team.md)
- [2026-08-08 — durcissement Ollama et contrat candidat](results/2026-08-08_ollama-candidate-contract-hardening.md)
- [2026-08-08 — instrumentation des candidats du décodeur](results/2026-08-08_decoder-candidate-instrumentation.md)
- [2026-08-08 — revue de clôture de l'instrumentation](results/2026-08-08_decoder-candidate-instrumentation-review.md)
- [2026-08-08 — contrat de provenance des candidats du décodeur](results/2026-08-08_decoder-candidate-provenance-contract.md)
- [2026-08-08 — protocole snapshot et labels causales des candidats](results/2026-08-08_decoder-candidate-snapshot-label-protocol.md)
- [2026-08-08 — correctif causal des retriggers candidats](results/2026-08-08_decoder-candidate-retrigger-causal-matching-fix.md)
- [2026-08-08 — revue du correctif causal des retriggers](results/2026-08-08_decoder-candidate-retrigger-causal-matching-review.md)
- [2026-08-08 — contrat d'empreintes des actifs candidats](results/2026-08-08_decoder-candidate-asset-evidence-contract.md)
- [2026-08-08 — correctif de lecture paresseuse des actifs candidats](results/2026-08-08_decoder-candidate-asset-evidence-lazy-audio-fix.md)

Les rapports détaillés restent des preuves horodatées. Le présent fichier est
le seul résumé global et doit toujours refléter l’étape courante et la suite.
