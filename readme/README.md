# Résumé unique — Guitar MIDI AI

> Dernière mise à jour manuelle : 2026-08-04
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
> Mise a jour effective : `2026-08-04T22:25:56+04:00` - etape
> `independent_note_validation_one_pass_diagnostic`.
>
> Le diagnostic validation-only est termine : le seuil `0,01` est inoperant
> (709 candidats eligibles, 0 rejet, probabilite minimum `0,48080769`, F1 onset
> inchange a `0,21760081`). La revue du commit `40aa1fe5` est appliquee : le
> diagnostic des douze seuils est maintenant impose au seul split validation,
> l'ancienne grille multi-passes est retiree, et les tests couvrent quantiles,
> comparaison stricte et absence de candidats (`44` tests). Aucun test verrouille,
> entrainement, export ou live n'a ete effectue. Une ancienne grille CPU
> terminee a confirme que `0,90` ne retire que 2 faux NoteOn et ne remplace pas
> le diagnostic a une passe. Le diagnostic a une passe est maintenant termine :
> mediane `0,98582065`, seulement 49/709 rejets hypothetiques a `0,90`, donc
> la porte seule ne peut pas corriger les 3389 faux NoteOn. Suite : revue
> ChatGPT du resultat avant toute modification ou nouveau calcul. Rapports :
> `readme/results/2026-08-05_independent-note-validation-diagnostic.md`.
> `readme/results/2026-08-05_independent-note-historical-grid.md`.
> `readme/results/2026-08-05_independent-note-one-pass-diagnostic.md`.

> Note d'horloge : le Mac a horodaté la fin brute à
> `2026-08-05T05:25:56Z`, mais son horloge était avancée d'environ 11 h.
> Le temps réconcilié ci-dessus est `2026-08-04T18:25:56Z`; les résultats et
> le JSON brut restent inchangés.

## État courant

- Mise à jour : `2026-08-04T23:07:03+04:00` (réconciliée, approximative ; l'horloge du Mac était avancée d'environ 11 h).
- Étape : `independent_note_absolute_partial_alignment_smoke`.
- Statut : `terminé — revue requise avant toute nouvelle évaluation ou tout entraînement`.
- Résultat établi : la tête précédente est saturée et ne doit pas être promue;
  `locked_test_used=false`. Le constructeur de cibles corrige maintenant la
  somme nécessaire entre décalage annotation-vers-classe et résidu du partiel.
- Vérification : compilation et 24 tests ciblés réussis. La tentative réduite
  refusée est archivée ; l'unique relance autorisée aux tailles fixes a terminé
  sur CPU avec `8192 / 2048 / 4096` exemples et 4 époques. Elle est strictement
  train-only : `validation_loaded=false`, `locked_test_used=false`, aucun
  export ou live, backbone gelé et parité exacte (`erreur max=0`, accord=1).
  Elle exerce le contrat de labels restauré avec succès, pas une baisse des faux
  NoteOn en validation ni une preuve autonome de sa justesse sémantique.
- Rapport :
  `readme/results/2026-08-04_independent-note-absolute-partial-alignment.md`.
  `readme/results/2026-08-04_independent-note-alignment-smoke-anomaly.md`.
  `readme/results/2026-08-04_independent-note-alignment-smoke.md`.

## Prochaine action réelle

1. Ne promouvoir ni le checkpoint précédent ni un seuil de porte.
2. Faire relire le résultat du smoke et son rapport détaillé par ChatGPT.
3. Ne pas promouvoir le seuil interne `0,01` : il n'est pas une mesure
   événementielle du décodeur et requiert une validation appariée distincte.
4. Conserver le test verrouillé fermé et ne lancer aucune nouvelle évaluation,
   aucun entraînement complet, export ou live avant une décision revue.

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
<!-- JOURNAL_END -->
## Rapports détaillés

- [2026-07-22 — entraînement polyphonique multi-source](results/2026-07-22_polyphonic-training.md)
- [2026-07-27 — validation du décodeur desktop polyphonique](results/2026-07-27_polyphonic-desktop-validation.md)
- [2026-07-28 — état du produit desktop monophonique](results/2026-07-28_mono-desktop-release.md)
- [2026-07-28 — reconstruction de `data/processed`](results/2026-07-28_processed-reconstruction.md)
- [2026-07-28 — incident de publication Kaggle](results/2026-07-28_kaggle-upload-incident.md)
- [2026-07-29 — validation du candidat desktop sélectionné](results/2026-07-29_desktop-candidate-validation.md)
- [2026-07-29 — validation de l’attaque causale adaptative](results/2026-07-29_adaptive-attack-validation.md)

Les rapports détaillés restent des preuves horodatées. Le présent fichier est
le seul résumé global et doit toujours refléter l’étape courante et la suite.
