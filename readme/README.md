# Résumé unique — Guitar MIDI AI

> Dernière mise à jour manuelle : 2026-08-10
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

- Mise à jour : `2026-08-10`.
- Étape : `provisional_resolution_age1_persistence_h10_synthetic_metric_conformance`.
- Statut : `terminé — provisional_resolution_age1_persistence_h10_synthetic_metric_engine_ready, aucune exécution scientifique autorisée`.
- H10 positif sur objets synthétiques uniquement : une fin d'enregistrement avec
  NoteOn encore pending échoue sous `age1_signal_execution_invalid` /
  `unresolved_age1_pending_at_end_of_recording`, sans synthèse de frame,
  suppression ou reclassification clock-skip. Le wrapper groupé garde
  `recording_key`, `corpus_category` et `leakage_group_key` hors du payload
  scientifique. L'AUC binaire average-rank attribue un demi-crédit exact aux
  égalités. Le bootstrap utilise exclusivement `10000` tirages de `G` groupes
  avec remise via `numpy.random.Generator(numpy.random.PCG64(721629268))`, toutes
  leurs lignes avec multiplicité, minimum `9500` réplications valides et
  percentiles linéaires `[2,5;97,5]`. La décision positive exige simultanément
  AUC S1 `>=0,60` et borne basse `>0,50`; S0/D1 et corpus restent descriptifs.
  Aucun actif H8, signal/target réel, modèle ou métrique réelle n'a été utilisé.
  Contrat :
  `configs/provisional_resolution_age1_persistence_h10_synthetic_metric_conformance.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h10-synthetic-metric-conformance.md`.
- H9 positif sur données synthétiques uniquement : un collecteur passif observe
  chaque vrai NoteOn du décodeur historique, retriggers compris, gèle
  `S0=frame_probability_at_noteon`, puis capture `S1` au même pitch exactement
  à `age_frames=1` avant les décisions de la frame suivante. Un saut d'horloge
  produit `age1_observation_unavailable`, sans interpolation ni substitution.
  Le collecteur est incompatible fail-closed avec le resolver H4/H6, la porte
  causale V1/V2 et le seuil independent-note. Une cible offline pure réutilise
  le matcher causal gelé : same-pitch, aucune référence future, one-to-one,
  dernière référence en attente, maximum `250 ms`. La jointure exige l'identité
  exacte `(frame_index,pitch)`. La parité MIDI et état interne du décodeur nu et
  instrumenté est démontrée sur les chemins legacy/audio-aware, harmoniques,
  polyphonie, release, retrigger, silence et sauts de hop. Aucun actif H8,
  modèle, target/signal réel, métrique, AUC ou bootstrap n'a été utilisé.
  Contrat :
  `configs/provisional_resolution_age1_persistence_h9_synthetic_conformance.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-h9-synthetic-conformance.md`.
- Préparation H8 scellée sans modèle ni métrique : le SHA brut du contrat H7 a
  été vérifié, puis toutes les prises `dev` Policy A ont été considérées sans
  plafond, équilibrage ou sélection manuelle. Après exclusion entière des
  groupes de la cohorte V2 consommée et du test verrouillé, la cohorte contient
  `101` prises et `31` groupes; une seule prise `dev`, du groupe verrouillé
  `gaps:player:sanja_plohl`, est exclue. Les intersections finales V2/test
  valent zéro. Les 101 audio et 101 labels ont uniquement été hachés comme
  octets bruts et concordent avec le registre Policy A historique. L'artefact
  canonique de `112013` octets a le SHA-256
  `4dd76bd13c33ccb3946bfdbcf6f575d4550fb0c5588095e23da3b6e3f84bce1f`.
  H8 fige `10000` réplicats bootstrap group-safe, le seed `721629268`, au moins
  `9500` réplicats valides et au moins `200` observations age-1, sans exécuter
  bootstrap, AUC, cibles ou signaux. Contrats :
  `configs/provisional_resolution_age1_persistence_h8_preparation.json` et
  `configs/provisional_resolution_age1_persistence_h8_selected_cohort.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-persistence-h8-preparation.md`.
- Hypothèse H7 préenregistrée sans données ni calcul : le seul signal primaire
  futur est `S1=current_frame_probability` du même pitch à `age_frames=1`;
  `S0=frame_probability_at_noteon` reste descriptif et `D1=S1-S0` uniquement
  mécanistique. Aucun autre champ H5, audio, onset, harmonique, polyphonie,
  score, raison, interaction ou modèle ne peut filtrer ou sauver H7. Le target
  réutilise le matcher causal one-to-one existant, same-pitch, sans référence
  future et à latence maximale `250 ms`, avec ses blobs Git figés. La future
  décision exige `ROC-AUC >= 0,60` et borne basse de l'IC 95 % bootstrap par
  groupes `> 0,50`. Le grouping doit provenir de `leakage_group_key`; bootstrap
  ligne/frame/NoteOn/recording interdit. Cohorte, actifs, nombre de réplicats,
  seed et minimums valides restent non résolus. La cohorte V2 consommée et le
  test verrouillé restent interdits. Contrat :
  `configs/provisional_resolution_age1_persistence_h7_hypothesis_contract.json`.
  Rapport :
  `readme/results/2026-08-10_provisional-resolution-age1-persistence-h7-hypothesis-contract.md`.
- Conformance synthétique H6 positive : `ProvisionalObservation` est désormais
  une dataclass immuable contenant exactement les 15 champs H5. Les preuves
  `*_at_noteon` sont gelées à l'émission et toutes les observations d'une frame
  partagent les mêmes snapshots pré-résolution de contexte harmonique et de
  polyphonie. Le décodeur valide toutes les observations, calcule toutes les
  décisions, puis les valide toutes avant la première mutation. Un résultat
  invalide tardif, une exception tardive ou une valeur numérique non finie ne
  produit donc ni confirmation/rejet partiel ni événement MIDI de résolution.
  `audio_onset_available` décrit explicitement le hop courant, pas le latch
  historique. Les compositions avec la porte causale V1/V2 ou
  `independent_note_threshold` échouent au constructeur avec
  `unsupported_pending_separate_contract`. Les scénarios H3/H4 et le chemin
  désactivé restent conformes. Les 98 tests ciblés passent en `0,297 s`.
  Aucun resolver réel, seuil, durée, population, donnée, modèle, inférence ou
  validation n'a été utilisé. Rapport :
  `readme/results/2026-08-10_provisional-resolution-h5-h6-synthetic-conformance.md`.
- Contrat causal H5 défini sans calcul : le futur resolver ne pourra recevoir
  qu'une `ProvisionalObservation` immuable et construite par le décodeur au
  point causal courant. Quinze champs sont classés par provenance, disponibilité
  et temporalité; labels, vérité MIDI, futur, métriques, cohorte V2, accès au
  décodeur, fichiers, réseau, modèle externe et état caché sont interdits.
  `HOLD/CONFIRM/REJECT/PREEMPT`, les erreurs atomiques et l'ordre intra-frame
  sont formalisés. Les seuils, la durée maximale, la population éligible et la
  stratégie runtime d'erreur restent non résolus. H4 + causal gate V1/V2 et H4
  + `independent_note_threshold` sont explicitement
  `unsupported_pending_separate_contract`. Aucun code fonctionnel du décodeur,
  donnée, modèle ou calcul scientifique n'est inclus. Contrat :
  `configs/provisional_resolution_evidence_contract_h5.json`. Rapport :
  `readme/results/2026-08-10_provisional-resolution-evidence-h5-contract.md`.
- Prototype synthétique H4 positif et strictement opt-in : chaque nouveau
  `NoteOn` peut être conservé comme état émis provisoire, tandis que le contexte
  harmonique et le budget de sélection n'utilisent que les notes confirmées.
  Une résolution injectée `HOLD/CONFIRM/REJECT` permet de tester l'architecture
  sans modèle ni données. Dans le scénario de polyphonie H3, le faux MIDI 60
  est préempté par un `NoteOff` avant que MIDI 61 soit émis dans la même frame,
  sans backfill ni dépassement du maximum. Dans le scénario harmonique H3, le
  faux MIDI 60 provisoire ne devient plus une base H2 : A et B gardent un
  support `0.0` et émettent toutes deux MIDI 72. `CONFIRM` contextualise la note
  sans second `NoteOn`; `REJECT` émet un `NoteOff` et nettoie l'état. Lorsque
  H4 est absent, les chemins legacy et audio-aware conservent leur comportement
  historique. Aucun resolver réel, politique de confirmation, donnée, audio,
  TensorFlow, modèle V1/V2, fit ou validation n'a été utilisé. Rapport :
  `readme/results/2026-08-10_decoder-provisional-state-isolation-h4-synthetic-intervention.md`.
- Le diagnostic H3 précédent reste la preuve causale motivant H4 : deux
  décodeurs identiques reçoivent une perturbation normale uniquement à `t0`,
  puis des entrées strictement identiques dès `t1`. Le faux MIDI 60 persistant
  dans B consomme l'unique slot de polyphonie et devient une base harmonique H2.
  Verdict : `state_contamination_demonstrated`. Rapport :
  `readme/results/2026-08-10_decoder-state-contamination-h3-synthetic-diagnostic.md`.
- Clôture provenance-only Attempt4 : l'unique exécution autorisée au commit
  `df2a2a0641d7897195ee0712002bcc48e97858e6` a créé son marker persistant,
  acquis le lease et créé sa destination, puis a atteint le timeout externe
  exact de `900 s`. Le marker fait `628` octets, SHA-256
  `00c677be7d78771e1b8c82d6bdf394dc8c9af64441a7f12f99c02f832908f1b0`.
  La destination est vide, le lock vide reste présent, et aucun processus ne
  subsiste. Aucun rapport ni métrique A/B n'a été publié. Le point scientifique
  atteint reste indéterminable : une métrique a pu exister seulement en mémoire.
  Par conséquent, `ab_metrics_produced=unknown`, `ab_metrics_observed=false`,
  le verdict V2 indépendant est `inconclusive_fail_closed`, la cohorte n'est
  plus réutilisable comme validation indépendante et tout retry est interdit.
  Le marker, le lock et la destination ne doivent pas être supprimés. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-attempt4-post-claim-timeout.md`.
- Demande d'autorisation attempt3, sans exécution : attempt2 a consommé son
  approval et son marker, puis s'est arrêtée avant TensorFlow et avant tout
  actif scientifique parce que le registre d'evidence attendu était absent du
  checkout worker. Sa destination et le verrou sont restés absents; aucune
  métrique A/B n'a été produite ou observée et la cohorte scientifique reste
  non consommée. Le registre historique a ensuite été matérialisé au chemin
  exact du worker, avec SHA-256
  `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee`.
  Une nouvelle demande canonique scelle le job
  `causal-candidate-v2-independent-cpu-20260810-attempt3`, sa destination, son
  futur approval et son marker, tous distincts des tentatives 1 et 2. Avant de
  créer le marker attempt3, le module TensorFlow-free exige désormais que ce
  registre existe au chemin exact et que ses octets correspondent au SHA
  scellé. Aucun approval, marker, worker ou calcul attempt3 n'existe encore.
  Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-attempt2-premetric-infrastructure-failure.md`.
- Incident pré-métrique du job indépendant V2 : l'unique autorisation du commit
  `78f46628f430b9cdbe0e2b9ea042f05d0b141762` a été revendiquée, puis le
  runner s'est arrêté avant TensorFlow et avant toute ouverture d'actif avec
  `Fail closed: independent validation asset-evidence read is not authorized`.
  Le marqueur persistant fait `370` octets, SHA-256
  `c0b544e2faed44df45985ccb9abfd13ed067966e907fe4f0f4c2bb83433225eb`;
  il ne sera jamais supprimé ni réutilisé. La destination et le verrou lourd
  sont absents, aucun rapport scientifique n'existe et la cohorte n'est pas
  consommée. L'autorisation, elle, est consommée. Le correctif en cours ajoute
  uniquement une capability d'évidence spécifique à l'exécution, tout en
  maintenant fermé le lecteur générique. Aucun retry, nouveau job, approval,
  marqueur, actif réel, TensorFlow, inférence ou métrique n'était autorisé par
  ce correctif. Le commit `c78b1e1c` est désormais approuvé; seule la demande
  distincte attempt2 ci-dessus est en revue, sans autoriser son exécution.
  Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-premetric-infrastructure-failure.md`.
- Jalon historique d'autorisation indépendante V2, désormais consommé : le runner gelé
  `6246ea18c49a6c3c3b8e2ce1303c9a6afffac6ee` est approuvé et reste
  byte-identique. Une demande canonique scelle CPU, `900 s`, job, destination,
  contrat et evidence; son module TensorFlow-free exige un futur fichier
  d'approbation externe lié au HEAD exact et un worktree propre. Ce fichier a
  ensuite été matérialisé et consommé par la tentative pré-métrique décrite
  ci-dessus. Le premier appel a créé avant attestation un marqueur persistant
  `O_EXCL`, jamais supprimé, empêchant tout retry cross-process. Aucun marqueur
  réel n'existait encore à ce jalon; il existe désormais et interdit toute
  réutilisation. Le test verrouillé reste fermé. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-one-job-authorization-request.md`.
- Jalon historique du correctif pre-science du runner indépendant : le manifeste attesté est
  désormais chargé directement par le lecteur sans TensorFlow; une primitive
  explicite prépare le runtime CPU seulement après contrat, Git, cohorte,
  preuve globale des 60 actifs, six SHA et lease atomique. La configuration
  CPU précède strictement les imports `data`/`evaluate_events`; chaque paire
  audio/labels est rehachée immédiatement avant l'ouverture du même objet et
  son corpus est fermé dans un `finally`. La capability one-job attestée sera
  revendiquée atomiquement dès la première invocation publique et ne pouvait
  jamais être réutilisée, même après un échec pre-lease. À ce jalon, aucune
  factory d'autorisation ni exécution réelle n'existait encore. `83` tests
  synthétiques passaient en `8,288 s`; la revue externe et l'autorisation ont
  ensuite mené à l'incident pré-métrique désormais en correction.
- Anomalie pré-métrique V2 vérifiée : le job unique
  `causal-candidate-v2-train-dev-cpu-20260809`, lancé au commit approuvé
  `ddd15be4fbf7e47205a0025f80821e2446ef9720` avec CPU et `900 s`, termine
  `exited_nonzero`/code `1` à l'horodatage brut worker
  `2026-08-10T01:02:26Z` (non réconcilié). L'accusé V2 et le
  préflight worker ont passé, mais le runner ne trouve pas
  `repository/tmp/local`, où il attend le plan Policy A et le registre
  d'actifs locaux scellés. Il échoue donc pendant `load_sealed_v2_diagnostic_contract`,
  avant TensorFlow, modèle, checkpoint, audio, labels, inférence ou métrique.
  La destination V2 et le verrou actif sont tous deux absents après l'arrêt;
  les 30 prises, les 12 validations historiques et le test verrouillé restent
  inutilisés. Aucune relance n'était alors autorisée : il fallait d'abord revoir
  la matérialisation contrôlée des artefacts locaux manquants. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-train-dev-preflight-missing-local-artifacts.md`.
- Suivi de matérialisation, sans écriture : les deux fichiers originaux requis
  (`decoder_candidate_partition_plan_v2.json` SHA
  `a8347e4e…3685f4` et `decoder_candidate_asset_evidence_v1.json` SHA
  `12dd74f2…e586507`) sont absents de tout `C:\Users\user\Desktop\midi` et
  de `/Users/amcarene/midi-worker`; ils ne sont pas versionnés et `tmp/` est
  ignoré par Git. Aucun SHA source n'est donc disponible à comparer ou copier.
  Aucun dossier Mac, transfert, Python ou relance n'a été effectué. Ils ne
  seront pas régénérés : fournir les deux originaux depuis une sauvegarde ou
  indiquer leur emplacement est nécessaire avant une nouvelle revue. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-artifact-materialization-blocked.md`.
- Récupération source, lecture seule : les deux originaux sont retrouvés dans
  l'ancien checkout Mac `/Users/amcarene/midi/tmp/local/decoder_candidate_policy_a_preregistration_20260809/`.
  Le plan fait `145 859` octets et son SHA-256 est exactement
  `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4`; le
  registre fait `198 950` octets et son SHA-256 est exactement
  `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507`.
  À ce jalon, aucun dossier destination, copie, reformatage ou lancement V2
  n'avait suivi. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-artifact-source-recovered.md`.
- Matérialisation binaire atomique V2 vérifiée : le worker Mac n'avait aucun
  job actif ni verrou, et le dossier destination était absent. Chaque original
  a été copié localement vers un fichier `.part` dans le dossier final
  `midi-worker/repository/tmp/local/decoder_candidate_policy_a_preregistration_20260809/`,
  contrôlé par taille et SHA-256, puis renommé atomiquement sur le même
  système de fichiers et recontrôlé. Le plan source/destination fait `145 859`
  octets, SHA-256
  `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4`; le
  registre source/destination fait `198 950` octets, SHA-256
  `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507`.
  Aucun `.part` résiduel ni verrou n'est présent après l'opération. Aucun JSON
  n'a été parsé ou réécrit; Python, TensorFlow, audio, labels, modèle,
  inférence et métrique restaient absents. La revue externe a ensuite autorisé
  l'unique passe décrite ci-dessous. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-artifact-materialization.md`.
- Résultat terminal de l'unique diagnostic V2 CPU train/dev : le nouveau job
  `causal-candidate-v2-train-dev-retry-cpu-20260810`, au commit exact
  `522acc1e71d8baeafcede67a3f14e71fece73f9b`, a terminé `exited_zero` à
  l'horodatage brut worker `2026-08-10T02:00:18Z`, après `720 s` et dans le
  timeout externe de `900 s`. Le rapport brut fait `793 812` octets, SHA-256
  `43e28b4ebfe33f5ad0f28be1c4b61704af8cebc08012458cbd645d3027b9acf9`;
  il confirme CPU, les 30 prises train/dev `6/6/6/12`, zéro validation
  historique et `locked_test_used=false`. La porte V2 gelée à `0,31`, placée
  `post_ranking_pre_noteon`, a traité `1 281` candidats et en a rejeté `61`
  (`4,76 %`). Elle retire `9` faux NoteOn standards (`14 031 → 14 022`),
  tandis que l'appariement onset baisse de `1` et que le rappel causal reste
  identique. Les faux NoteOn causaux passent de `13 285` à `13 275`, sans
  changement de retriggers, fragmentation ni MIDI `40–51`; p90 causal augmente
  de `0,265 ms`, bien sous un hop de `5,805 ms`. C'est une observation
  exploratoire train/dev non promotionnelle : ni fit, ni calibration, ni
  validation historique, ni export/live ni test verrouillé ne sont autorisés.
  Le verrou est libéré et le runner demande explicitement l'arrêt après son
  rapport. La seule prochaine action est la revue externe du résultat. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-train-dev-diagnostic-run.md`.
- Contrat et runner synthétique d'évaluation indépendante V2, sans calcul réel : le manifeste scellé et la
  sélection historique de 12 prises ont été audités par métadonnées uniquement.
  La prochaine cohorte est gelée à `30` prises validation inédites : `10` GAPS,
  `10` Guitar-TECHS direct input et `10` Guitar-TECHS mic/amp, avec exclusion
  stricte de toute clé et de tout groupe de fuite historique. GuitarSet est
  explicitement hors périmètre : ses `60` prises validation appartiennent toutes
  au joueur `04`, déjà exposé par la cohorte historique. Le modèle V1, le
  standardiseur, les 12 features, le seuil `0,31`, la politique audio et le
  placement `post_ranking_pre_noteon` restent gelés ; les seuils de faux NoteOn,
  rappel, F1, fragmentation et latence sont préenregistrés. Aucun audio, label,
  modèle, actif, inférence, fit, calibration, export, live ou test verrouillé
  n'a été ouvert. Le nouveau module pur recalcule ces 30 clés depuis le
  manifeste complet avant de comparer la liste gelée, vérifie l'exclusion des
  groupes historiques et Policy A, force le placement V2 et applique les règles
  de décision fail-closed sur un rapport synthétique. Il n'a ni CLI ni accès
  aux actifs : la construction/lecture d'asset evidence et toute passe CPU
  restent interdites. Rapports :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-contract.md`
  et
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-runner-implementation.md`.
- Preuve byte-level V2 indépendante, toujours synthétique : le nouveau
  registre canonique ne peut couvrir que les `30` clés validation et les `20`
  groupes de fuite dérivés, liés au SHA du protocole et du manifeste. Chaque
  entrée portable contient seulement l'identité, le membre audio, la taille
  et le SHA-256 des deux fichiers `audio`/`labels` ; elle ne contient aucun
  chemin. Sa création exige un snapshot exact du manifeste et ne peut lire que
  les octets des actifs sélectionnés. La lecture du JSON ne charge aucun actif
  et le futur runner devra rehacher chaque fichier juste avant son ouverture.
  Le registre est JSON canonique immuable, réouvert et attesté par identité ;
  une copie/altération ou un item clone échoue. `41` tests ciblés
  provenance/V2 passent sur fichiers factices uniquement. Aucun actif projet,
  modèle, inférence, job Mac, fit, calibration, export, live ou test verrouillé
  n'a été ouvert. La seule action suivante est la revue externe de cette
  implémentation ; toute construction de preuve réelle reste interdite.
  Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-implementation.md`.
- Correctif de revue de cette preuve byte-level, toujours synthétique : la
  revue externe de `3d889f05` avait refusé l'ancienne API, car un cohort
  construit à la main et un registre JSON canonique aux digests inventés
  pouvaient encore franchir des étapes de provenance. La nouvelle API exige
  désormais un cohort et une demande d'évidence attestés par le chargeur
  scellé, bloque builder/reader tant que leurs flags versionnés sont `false`,
  rehache les 60 actifs entre build et publication, puis ne rend un registre
  utilisable qu'après rehash complet identité/métadonnées/octet. Une future
  étape de lecture devra aussi figer le SHA du registre et le SHA du protocole
  de construction; les deux autorisations sont mutuellement exclusives. Le
  lecteur de snapshot est maintenant sans TensorFlow. Les 14 tests nouveaux
  sans TensorFlow passent en `2,868 s`; la suite provenance élargie compte 44
  tests en `10,340 s`, sans actif projet, modèle, Mac, inférence ou calcul
  scientifique. Aucun registre réel n'est créé : la seule action suivante
  reste la revue externe de ce correctif. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-review-fix.md`.
- Autorisation builder V2 indépendante, sans accès aux actifs : la seconde
  revue externe du correctif `5fd4fc8` est approuvée. Le nouveau protocole
  scellé (SHA-256 `d63655c3…9ba015`) autorise uniquement
  `independent_validation_asset_evidence_build` : le builder pourra, lors de
  l'étape distincte autorisée, hacher et publier atomiquement la preuve des
  `30` audio et `30` labels de la cohorte validation indépendante. Il garde
  `reader_authorized_now=false` et ne contient encore ni SHA source de preuve
  ni SHA attendu de registre. Le lecteur/validateur, tout chargement de modèle,
  décodage d'actif, évaluation, fit, calibration, export, live et test
  verrouillé restent interdits. Ce commit ne lance pas le builder et n'ouvre
  aucun actif projet. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-builder-authorization.md`.
- Construction unique de la preuve d'actifs V2 indépendante : après préflight
  Mac propre au commit `e241bd8`, le builder byte-level autorisé a haché sans
  décodage les `30` audio et `30` labels de la cohorte scellée, puis publié le
  JSON canonique immuable à
  `/Users/amcarene/midi/tmp/local/causal_candidate_v2_independent_validation_asset_evidence_20260810.json`.
  Le registre fait `17 873` octets, SHA-256
  `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee`,
  est lié au manifeste `b28cb17c…f1b8ed7` et au protocole builder
  `d63655c3…9ba015`; aucun fichier `.part` ne subsiste et le worktree Mac est
  propre. Le protocole courant est aussitôt refermé (SHA-256
  `79c11de0…5cd0e7`, builder/reader `false/false`) afin d'interdire toute
  seconde construction avant revue. Aucun JSON n'est lu/validé, aucun modèle,
  checkpoint, TensorFlow, inférence, évaluation, fit, calibration, export,
  live ou test verrouillé n'est utilisé. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-build.md`.
- Contrat lecteur V2 indépendant, sans lecture : après la revue post-build, le
  protocole scellé (SHA-256 `6bf7619a…c8ab3e`) fixe enfin les deux valeurs que
  devra vérifier un lecteur futur : registre `10307a64…22aee` et protocole
  builder source `d63655c3…9ba015`. Il laisse le builder fermé, autorise
  uniquement l'opération lecteur/revalidateur future et interdit toujours
  décodage, modèle, évaluation, fit, calibration, export, live et test
  verrouillé. Cette étape ne relit pas le JSON et ne rehache aucun actif ; sa
  seule suite est une revue externe du contrat lecteur. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-reader-authorization.md`.
- Revalidation unique de la preuve d'actifs V2 indépendante : après préflight
  Mac propre au commit `e667a5c`, le lecteur a vérifié le JSON canonique et son
  SHA `10307a64…22aee`, sa liaison au protocole builder `d63655c3…9ba015`, puis
  a rehaché avec succès les `30` audio et `30` labels de la cohorte scellée.
  Il retourne uniquement la capacité de preuve validée et s'arrête : aucun
  décodage, TensorFlow, modèle, checkpoint, inférence, métrique, évaluation,
  fit, calibration, export, live ou test verrouillé. Le protocole courant est
  aussitôt refermé (SHA-256 `def274de…a34119`, builder/reader `false/false`),
  donc aucune seconde revalidation ne peut démarrer avant revue. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-asset-evidence-revalidation.md`.
- Contrat d'exécution V2 indépendant, déclaratif uniquement : le nouveau
  protocole versionné SHA-256 `269efb65…ae63ed` lie le protocole indépendant
  fermé `def274de…a34119`, le registre revalidé `10307a64…22aee`, son
  protocole builder source `d63655c3…9ba015`, le manifeste, la sélection
  historique et le plan Policy A. Il gèle la cohorte validation indépendante
  `10/10/10/0` (`30` prises, `20` groupes), tous les artefacts V1/V2, le seuil
  `0,31`, les 12 features et le placement `post_ranking_pre_noteon`. Son seul
  état est `external_review` : builder, lecteur, runner, accès aux actifs,
  modèle, TensorFlow et tout calcul réel restent interdits. Il exige d'un futur
  runner revu qu'il rehache le registre et les `30` audio + `30` labels avant
  toute ouverture, exécute une seule passe CPU A/B puis s'arrête sans promotion
  ni retry. Compilation et `19` tests synthétiques/provenance passent en
  `1,650 s`, sans actif projet ni TensorFlow. Rapport :
  `readme/results/2026-08-10_causal-candidate-v2-independent-validation-execution-contract.md`.
- Correctif d'intégration V2 sans calcul : le worker Windows n'autorise
  désormais l'accusé dédié qu'au module exact
  `src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic`, avec CPU,
  timeout externe exactement `900 s`, zéro argument et `ExpectedCommit` complet
  égal au HEAD local; le worker Mac revalide le même commit puis exige le
  littéral `DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE=1` avant TensorFlow. Le
  runner lit, hache et parse maintenant les mêmes octets de la politique audio
  scellée, exige `onset_adapt_temporal_background=true`, puis transmet cette
  unique métadonnée interne à l'évaluateur. Les masques sont donc calculés une
  fois et partagés par les deux décodeurs A/B ; toute surcharge audio appelant
  reste refusée. `py_compile`, `bash -n`, `git diff --check` et `46` tests
  ciblés (PowerShell/Bash, runner V2, A/B et décodeur) passent en `9,044 s`, sans
  synchronisation Mac, actif projet, inférence, fit, calibration, validation,
  export, live ni test verrouillé. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-runner-integration-fix.md`.
- Runner d'exécution réelle V2, sans exécution : la première mesure proposée
  est limitée aux `30` prises canoniques V3 dont la partition préassignée est
  `dev` (`6` GAPS, `6` Guitar-TECHS DI, `6` Guitar-TECHS mic/amp, `12`
  GuitarSet). Le plan Policy A, le registre d'actifs, les artefacts V1, le
  seuil `0,31`, les masques audio et le placement
  `post_ranking_pre_noteon` y sont gelés. Cette cohorte n'est pas indépendante,
  car elle a servi au choix de l'époque V1 : elle est explicitement
  **train-only exploratoire et non promotionnelle**, sans sélection de seuil ou
  de modèle. Les 12 prises validation restent exclues. Le nouveau module sans
  CLI fixe les chemins, l'accusé worker, CPU, la tête/standardiseur V1, le
  seuil `0,31` et le placement `post_ranking_pre_noteon`. Avant TensorFlow ou
  un actif, il rehash le protocole LF, les artefacts V1, la politique V3, le
  plan et le registre ; il dérive ensuite les 30 identités depuis le manifeste
  pur, puis exige que le contexte attesté reproduise exactement cette sélection
  avant tout chargement de modèle. Aucune exécution n'est autorisée avant revue
  externe du runner. Compilation, `git diff --check`, `52` tests
  A/B/V2/événements en `0,551 s` et `54` tests provenance/minage en `1,848 s`
  passent sans ouvrir les chemins Mac scellés. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-train-dev-diagnostic-runner-implementation.md`.
- Intégration A/B V2 sans actif réel : chaque chemin avec une porte causale doit
  désormais déclarer explicitement son placement avant toute inférence. Le
  runner scellé V1 passe explicitement `pre_ranking`, conservant son expérience
  historique. Le chemin candidat V2 transmet explicitement
  `post_ranking_pre_noteon` jusqu'à `PolyphonicDecoder`; une omission ou un
  placement inconnu échoue. Les preuves synthétiques vérifient une seule
  inférence, l'appel de la porte uniquement sur les deux candidats sélectionnés
  parmi trois, le rejet du premier et l'absence de backfill. `51` tests ciblés
  A/B/décodeur en `1,029 s` et `30` tests de provenance/minage en `0,846 s`
  passent. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-synthetic-integration.md`.
- Implémentation V2 sans actif réel : `PolyphonicDecoder` conserve le placement
  V1 `pre_ranking` par défaut et ajoute uniquement
  `post_ranking_pre_noteon`. Dans les chemins audio-aware et legacy, V2
  conserve un snapshot V1 figé après pré-ranking, classe puis sélectionne les
  candidats, applique la porte seulement aux sélectionnés, puis ne mute/émet
  que les acceptés. Un rejet conserve `activation_count` et
  `attack_activation_pending`, n'a aucune place active persistante, garde sa
  position de sélection sans backfill et n'entre pas dans `protected_chord`.
  Les tests synthétiques ciblés passent : `46` en `0,422 s` puis `30` en
  `0,769 s` (76 au total), sans
  modèle V1, standardiseur, actif projet, fit, calibration, validation,
  export, live ni test verrouillé. Aucune mesure de latence réelle n'est faite;
  V2 n'ajoute toutefois ni lookahead, buffer ni hop par construction. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-synthetic-implementation.md`.
- Contrat V2 préenregistré et désormais implémenté synthétiquement : la tête
  causale V1, son standardiseur, ses 12 features et le
  seuil gelé `0,31` restent inchangés. Seul le placement futur est défini :
  après ranking et sélection `maximum_polyphony`, juste avant les seules
  mutations liées à l'acceptation/émission d'un nouveau `NoteOn`. Les mises à
  jour causales pré-ranking déjà présentes (evidence d'activation, releases,
  retriggers et graces) restent identiques à la référence. Un candidat
  sélectionné puis rejeté ne devient pas actif; `activation_count` et
  `attack_activation_pending` restent exactement dans leur état post-pré-ranking
  sans reset V2. Il ne crée aucune place active persistante, mais sa position
  dans la sélection du hop reste consommée et n'est ni rouverte ni backfillée.
  Toutes les décisions de porte précèdent la protection d'accord, qui ne voit
  que les candidats acceptés. Les features restent celles de V1, figées après
  les mises à jour pré-ranking et avant ranking/sélection, sans information
  post-porte ni future. Les retriggers restent inchangés. Les 12 prises validation ayant
  déjà révélé le défaut V1, elles sont explicitement interdites dans ce contrat
  V2 et ne pourront être employées plus tard qu'avec une autorisation distincte
  et une interprétation exploratoire. Aucun modèle, actif, inférence, fit,
  recalibration, recherche de seuil, validation, export, live ou test verrouillé
  n'a été ouvert ou exécuté. Rapport :
  `readme/results/2026-08-09_causal-candidate-v2-post-ranking-hypothesis.md`.
- Résultat terminal vérifié : l'unique job CPU
  `causal-candidate-fit-v1-cpu-20260809` termine avec `exit_code=0`,
  `complete_non_authorizing`, 14 époques enregistrées et meilleure époque 9,
  au commit exact `578a9d6583b2e5a68a312bd8dccf8e19a77b58b7`. Le préflight
  scellé V3, les comptes `694/244`, `968/250`, `793/190`, la parité Keras
  `0,0`, les trois SHA d'artefacts et `locked_test_used=false` sont vérifiés.
  La calibration train-only retourne `0,31`, sans promouvoir ce seuil. Une
  anomalie non corrigée est archivée : le dossier de sortie porte un caractère
  CR final transmis par le transport SSH direct; les octets restent intègres,
  aucune copie, renommage ou reprise n'est faite. Seule la revue du rapport
  a approuvé le résultat interne sans promouvoir le seuil. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-v1-run.md`.
- Correctif sans calcul : `MAC_WORKER.ps1` ne permet l'accusé
  `DECODER_CANDIDATE_FIT_EXECUTE=1` que pour le runner causal approuvé et le
  transporte par stdin via `Invoke-Ssh`; `mac_worker.sh` refuse tout argument
  contenant CR avant Git, TensorFlow ou écriture. Les artefacts V1 existants,
  y compris leur dossier anormal, restent inchangés. Une préinscription A/B
  versionnée fixe les 12 prises validation, la référence sans porte, le modèle
  `b9320cd0…`, le standardiseur `0600aa1a…`, le seuil non promu `0,31`, une
  seule inférence de transcription par prise et les critères de décision. Elle
  interdit encore fit, recalibration, recherche de seuil, export, live et test
  verrouillé. Aucun Mac job ni calcul validation n'a été lancé. Rapport :
  `readme/results/2026-08-09_causal-candidate-fit-v1-transport-and-validation-preregistration.md`.
- Révision de contrat sans calcul après revue externe de `64ccc768` : l'A/B ne
  prétend plus conserver les mêmes candidats après la première divergence. Il
  impose une seule inférence et les mêmes masques audio, puis deux états de
  décodeur causaux indépendants; les features de la branche candidate sont
  calculées juste avant sa porte depuis son état propre. Toute surcharge audio
  est interdite. Les deltas de latence causale `p50` et `p90` sont maintenant
  chacun limités à `+1` hop (`5,804988662 ms`). L'implémentation et l'exécution
  restent interdites jusqu'à la revue de cette révision.
- Implémentation A/B sans calcul : `causal_candidate_validation.py` vérifie les
  SHA de la policy, sélection, modèle, standardiseur, manifeste, checkpoint,
  YAML et décodeur avant chargement. Elle partage l'inférence et les masques
  audio, puis fourche uniquement deux états de décodeur; la tête candidate voit
  les features pré-porte, jamais la référence. 66 tests ciblés passent en
  `7,859 s`; aucun modèle ou actif réel, aucune validation, export, live ou
  test verrouillé n'a été exécuté. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-implementation.md`.
- Correctif de revue A/B sans calcul : le verdict emploie désormais la métrique
  réellement émise `recall_within_max_latency`; le SHA-256 du `fit_report` est
  vérifié avant le modèle et les huit empreintes exigées sont archivées dans le
  résultat. Les agrégats `onset_offset` sont présents pour A et B. Le rejeu
  synthétique ciblé passe `66` tests en `8,147 s`; aucune prise validation ni
  actif réel n'a été ouvert. Une nouvelle revue externe reste obligatoire avant
  toute exécution Mac.
- Invocation Mac sans calcul : le module
  `src.polyphonic.run_causal_candidate_validation` ne possède aucun CLI et
  construit exclusivement en interne les huit chemins scellés, y compris le
  dossier historique à suffixe CR sans jamais le transmettre au shell. Le worker
  n'accepte cette seule exécution que via l'accusé dédié, sans argument de
  module, avec CPU, exactement `900` s et un commit Git complet égal au HEAD
  local. Son préflight spécifique ne charge pas TensorFlow : le runner vérifie
  d'abord les huit SHA puis impose CPU avant l'import. La destination est neuve
  par construction. `py_compile`, les parseurs PowerShell/Bash et 26 tests
  ciblés passent; aucun actif, checkpoint, prise validation, inférence,
  validation, export, live ou test verrouillé n'a été ouvert ou exécuté.
  La revue externe finale de cette invocation est la seule action préalable à
  une commande Mac. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-invocation-contract.md`.
- Anomalie pré-métrique close de la première invocation A/B : le job CPU
  `causal-candidate-validation-ab-cpu-20260809`, au commit
  `4ab4f1ecâ€¦`, a terminé `exited_nonzero` à `2026-08-09T22:34:34Z` après le
  préflight worker, les huit SHA et le chargement du checkpoint, mais avant
  toute boucle/inférence sur les 12 prises. Cause : `evaluate_events` lisait
  inconditionnellement `thresholds["frame"]` alors que le décodeur scellé
  contient déjà les seuils et qu'aucun `thresholds.json` n'est autorisé dans la
  destination fraîche. Aucun rapport, audio/label, métrique, export, live ou
  test verrouillé n'a été produit; la destination A/B reste absente et le
  verrou est libéré. Correctif sans calcul : la configuration décodeur est
  maintenant résolue avant manifeste/checkpoint et ne lit les thresholds que
  si aucun décodeur explicite n'existe. `py_compile` et 54 tests ciblés passent
  en `8,912 s`. La revue externe a autorisé une seule relance. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-threshold-contract-fix.md`.
- Résultat vérifié de cette unique relance CPU : le job Mac
  `causal-candidate-validation-ab-retry-cpu-20260809`, au commit exact
  `17d94580af0f293f66a05072388fa1df62f27a89`, termine `exited_zero` à
  `2026-08-09T22:53:39Z` en `complete_non_authorizing`. Le rapport brut
  (372 794 octets, SHA-256 `8f048ad173015c2a89d3cde5ca106cc45c6bad05f6023f36c92ba4e12c28d1c3`)
  confirme `split=validation`, 12 prises équilibrées, les huit SHA scellés,
  une inférence commune par prise, deux états de décodeur indépendants et
  `locked_test_used=false`. La porte causale V1 à `0,31` a rejeté 9 des 711
  candidats internes observés, mais n'a modifié aucun NoteOn final : faux
  positifs `3389 → 3389`, F1 onset `0,21760081 → 0,21760081`, rappel causal
  `0,59741687 → 0,59741687`, latences p50/p90 inchangées à `68,131/162,388 ms`.
  La règle préenregistrée exigeait au moins un faux positif en moins ; elle est
  seule en échec, donc `all_rules_passed=false`. Aucune promotion, nouveau fit,
  recalibration, recherche de seuil, export, live ou test verrouillé n'est
  autorisé. Rapport :
  `readme/results/2026-08-09_causal-candidate-validation-ab-v1-run.md`.
- Revue externe de `f893aa55…` : résultat approuvé et V1 formellement clôturée.
  Les 9 rejets internes sont réels, mais `0/4247` événement MIDI final a changé.
  Cette absence de transfert entre la population entraînée (NoteOn émis) et la
  population vue avant ranking est désormais une limite observée, non une raison
  de régler à nouveau le seuil. Une porte éventuelle après ranking/sélection,
  juste avant NoteOn, serait une nouvelle hypothèse architecturale à
  préenregistrer séparément ; aucune implémentation ni calcul ne suit cette
  revue.
- Résultat vérifié : le job Mac
  `decoder-candidate-guitarset-v3-cpu-20260809` a terminé avec `exit_code=0`
  et l'état `complete_non_authorizing` au commit
  `4ddc88666a1c55725c18a813c63ecd25a03bf298`. Les 90 prises train-only ont
  produit 3 139 candidats supervisés (684 positifs causaux, 2 455 faux NoteOn),
  0 perte et 3 139 `event_id` uniques. La porte de représentation passe, y
  compris GuitarSet positif `31/28/14` pour fit/dev/calibration, mais
  `fit_authorized=false` reste obligatoire. `locked_test_used=false`; aucun
  fit, calibration, validation, export, live, choix de seuil ou test verrouillé
  n'est autorisé. Les horodatages du worker Mac sont conservés dans le rapport
  sans réconciliation : début `2026-08-09T19:07:52Z`, fin
  `2026-08-09T19:41:24Z`. Rapport :
  `readme/results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md`.
- Revue externe : V3 est approuvé comme corpus train-only suffisamment
  représenté. Il n'autorise ni un quatrième minage, ni un fit automatique. La
  prochaine hypothèse, sans calcul, préenregistre une tête logistique causale,
  ses 12 entrées pré-porte, sa pondération group-safe, le choix dev et la
  calibration interne au train. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-hypothesis-v1.md`.
- Implémentation vérifiée, sans exécution de fit :
  `src/polyphonic/causal_candidate_fit.py` scelle les deux artefacts V3 et le
  protocole V3 avant toute lecture de ligne, contrôle le statut non autorisant,
  les sept empreintes, le commit, le but et les comptes par partition. Il
  projette exclusivement les 12 features pré-porte, standardise sur `fit`,
  calcule les poids localement par partition et expose la BCE dev sans L2, la
  calibration déterministe et la parité sauvegarde/rechargement sans écrasement.
  Le budget figé utilise seed `47` et `shuffle=false`. Les 42 tests synthétiques
  ciblés passent en `2,015 s`; aucune ligne V3 réelle, aucun checkpoint réel,
  aucune gradient update, calibration, validation, export, live ni test
  verrouillé n'a été exécuté. La revue externe de cette implémentation est la
  seule action préalable à toute autorisation distincte de fit. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-protocol-implementation.md`.
- Revue externe de `76ebf937` : l'implémentation V1 est approuvée, sans
  autoriser un job Mac. Le runner maintenant ajouté ne possède aucun réglage
  de spec ou de poids, exige un accusé d'exécution, CPU, Git exact et les
  artefacts V3 scellés. Il entraîne uniquement `fit`, observe `dev` hors
  gradients pour choisir l'époque par BCE hors L2, et n'ouvre calibration
  qu'après le verdict dev. Il persistera le standardiseur lié au modèle et
  appliquera un budget de 15 min ; les 47 tests synthétiques ciblés passent en
  `5,388 s`. Aucun fit, artefact V3 réel, calibration, validation, export,
  live ni test verrouillé n'a été exécuté. Une nouvelle revue externe du
  runner est obligatoire. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-runner-implementation.md`.
- Résultat vérifié : le job Mac `decoder-candidate-extended-mining-cpu-20260809`
  a terminé sans erreur au commit `42a88b0d…`, avec `locked_test_used=false`,
  3 057 candidats supervisés (639 positifs, 2 418 négatifs), zéro perte et
  aucun `event_id` dupliqué. La porte échoue uniquement pour les positifs
  GuitarSet `dev=6` et `calibration=7`, sous le minimum préenregistré de 8.
  Aucun fit, calibration, validation, export, live, choix de seuil ou test
  verrouillé n'est donc autorisé. Rapport :
  `readme/results/2026-08-09_decoder-candidate-extended-mining-run.md`.
- Hypothèse suivante, sans calcul : le contrat v3 conserve les mêmes sept SHA,
  la porte à 8 et la Policy A, mais fixe une population unifiée de 90 prises
  (6 par cellule sauf GuitarSet à 12 par partition). Le correctif au blocage
  de revue lie de plus toute exécution du schéma 3 au seul fichier versionné
  `configs/decoder_candidate_guitarset_expansion_policy_a_v3.json` et à son
  SHA-256 LF `db55930a…5683`, avant Git, actifs ou TensorFlow. Les substitutions
  par chemin externe ou octets modifiés échouent fermées. Aucun calcul ne suit ;
  la revue externe du correctif est approuvée. L'unique replay CPU V3 est
  maintenant terminé ; aucun second lancement ni changement de contrat n'est
  autorisé avant la revue du rapport terminal. Rapports :
  `readme/results/2026-08-09_decoder-candidate-guitarset-expansion-hypothesis.md`
  et `readme/results/2026-08-09_decoder-candidate-guitarset-protocol-binding-fix.md`,
  puis `readme/results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md`.
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
  collecteur, ouverture ou agrégation. La politique A, désormais versionnée au
  schéma 2, conserve la validation historique et exclut automatiquement du
  futur minage toute capture train dont le groupe corpus-aware est déjà en
  validation. Les identités exclues sont elles-mêmes persistées et rematchées
  contre le manifeste complet; aucun sous-ensemble manuel ne peut passer.
- Preuve d'actifs : avant toute ouverture future, le contexte exigera un
  registre canonique, persistant et attesté des tailles/SHA-256 audio et labels
  de chaque capture train, lié au même manifeste, plan, `audio_member` et
  partition. Les labels sont rehachés juste avant leur lecture par le
  constructeur et l'audio juste avant son véritable chargement paresseux par
  `corpus.audio()`; le chemin `.npy` protégé ne conserve pas de `mmap` après
  cette vérification. Une couverture incomplète, un fichier modifié, un wrapper
  forgé ou des octets du registre modifiés échouent fermé. La preuve réelle
  Policy A de 541 actifs est enregistrée. Les trois replays train-only approuvés
  (12, 72 puis 90 prises) ont ouvert uniquement leurs actifs sélectionnés après
  revalidation du registre ; ce texte remplace l'ancienne assertion, devenue
  obsolète, qu'aucun actif n'avait encore été ouvert.
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
- Vérification de la politique A Windows : compilation Python, `git diff
  --check` et **138 tests ciblés réussis en 8,696 s**. Les nouveaux fixtures
  GAPS synthétiques vérifient l'exclusion train déterministe, la persistance
  exacte des captures exclues, le refus d'un sous-ensemble manuel et
  l'impossibilité de construire leur collecteur.
- Vérification initiale du mineur borné Windows : les 39 tests ciblés passent en
  `1,044 s`; la suite générale passe ensuite à **458 tests en 38,309 s**
  (trois ignorés). Les éventuelles mini-époques visibles dans cette seconde
  suite sont uniquement des fixtures synthétiques historiques : aucun WAV,
  label, checkpoint ou artefact réel Policy A n'a été ouvert.
- Correctif de préflight du mineur borné Windows : la revue externe de
  `0e124352…` a relevé (a) la confusion entre SHA Git à 40 caractères et
  SHA-256, et (b) l'import de TensorFlow via `data.py` avant les empreintes.
  Le CLI charge désormais `data`/le contexte uniquement après les sept SHA,
  le lien YAML-manifeste et le préflight CPU; le SHA Git possède son validateur
  dédié. `py_compile`, `git diff --check` et **41 tests ciblés en 2,025 s**
  passent, dont un sous-processus vierge prouvant qu'un checkpoint substitué
  échoue avec `tensorflow` absent de `sys.modules`. Aucun actif Policy A,
  checkpoint réel, inférence, replay, collecteur ou artefact n'a été ouvert ou
  produit par ce correctif.
- Anomalie de préflight Mac après l'approbation de `9ed93e7` : six empreintes
  scellées concordent, mais la politique audio versionnée vaut `bf4c…` dans le
  checkout Windows CRLF et `45ed…` dans le blob Git / checkout macOS LF. Le
  job s'est arrêté avant TensorFlow, contexte, checkpoint, actif, replay ou
  écriture. Le correctif force LF pour les quatre configurations versionnées
  scellées et remplace l'empreinte audio par le SHA canonique Git `45ed…`.
  `py_compile`, `git diff --check` et **42 tests ciblés en 1,721 s** passent;
  une revue externe du correctif est obligatoire avant une nouvelle
  synchronisation et l'unique minage.
- Préinscription Policy A Mac terminée au commit `8190e3bf` : manifeste stable
  `b28cb17…` avant/après, validation historique inchangée (`182` lignes),
  `31` exclusions `gaps_poly_mix` couvrant les dix joueurs attendus, `541`
  prises planifiées et `541` entrées de registre. SHA plan v2
  `a8347e4e…` ; SHA registre `12dd74f2…`. Aucune exclusion n'est dans le
  registre, `locked_test_used=false`, et aucun replay/minage/entraînement ou
  autre calcul scientifique n'a démarré.
- Préinscription Mac de `d16b25f7` : le checkout est synchronisé et inactif,
  mais le garde group-safe a refusé le manifeste
  `b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7` avant
  toute écriture ou hachage. Dix joueurs `gaps_poly_mix` chevauchent train et
  validation (31 prises train, 11 validation au total). Le répertoire de sortie
  vide a été supprimé ; aucun plan, registre, actif ouvert, artefact candidat,
  minage ou test verrouillé n'existe. Le choix utilisateur A conserve cette
  validation; il ne modifie ni le manifeste ni les données et prépare seulement
  l'exclusion déterministe versionnée des prises train concernées.
- Autorisation externe de la préinscription Policy A (`8143f016…`) : le premier
  minage peut uniquement produire un corpus candidat et ses compteurs de
  provenance, sans fit ni validation. Le mineur versionné fige sept empreintes
  (manifeste, plan, registre, checkpoint de transcription, YAML, décodeur,
  politique audio), exige CPU et un commit Git propre exact, puis limite le
  rejeu à 12 prises canoniques train (`1 × corpus × fit/dev/calibration`). Il
  écrit atomiquement sous `data/processed`, refuse toute perte de collecte et
  marque `fit_authorized=false`. **Aucun minage réel n'a encore été lancé : la
  revue externe de cette implémentation est la porte suivante.**
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
  puis `readme/results/2026-08-08_decoder-candidate-asset-evidence-lazy-audio-fix.md`
  et `readme/results/2026-08-08_decoder-candidate-preregistration-blocked-by-gaps-leakage.md`,
  puis `readme/results/2026-08-09_decoder-candidate-gaps-policy-a-contract.md`
  et `readme/results/2026-08-09_decoder-candidate-policy-a-preregistration.md`.

## Prochaine action réelle

1. Variante V1 close : ne pas modifier le seuil `0,31`, ne pas refaire son fit
   et ne pas relancer cette validation.
2. Attendre une décision explicite avant de préenregistrer une hypothèse
   distincte de porte après ranking/sélection, juste avant l'émission NoteOn.
3. Conserver le test verrouillé fermé : aucun nouveau fit, recalibration,
   validation, export, live ou sélection/promotion de seuil n'est autorisé à
   cette étape.

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
- 2026-08-08 — **terminé** — `decoder_candidate_asset_evidence_contract` :
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
  Windows passent en 9,718 s. La revue externe de `d16b25f7` est approuvée et
  a autorisé la seule préinscription Mac. Celle-ci s'est arrêtée avant toute
  écriture ou hachage : le manifeste `b28cb17...` comporte dix groupes GAPS
  chevauchant train/validation. Le répertoire de sortie vide a été supprimé;
  aucun plan, registre, actif projet, minage, entraînement, validation, export,
  live ou test verrouillé n'a été produit. La revue de `d4280e0` est approuvée
  et n'autorise qu'un futur commit de politique, sans données ni calcul : le
  choix entre préserver la validation actuelle (A) et créer une nouvelle
  validation group-safe (B) appartient à l'utilisateur avant toute tentative.
  Mise à jour du 2026-08-09 : l'utilisateur a choisi **A**. Le schéma 2 du plan
  persiste désormais chaque capture train exclue parce que son groupe
  corpus-aware est présent dans validation, puis rematche cette liste contre le
  manifeste complet. La validation elle-même reste inchangée, toute liste train
  fournie manuellement échoue, et les objets exposés au futur contexte ne
  couvrent que les prises planifiées. Tests synthétiques uniquement; aucun plan
  réel, registre, actif projet, minage, entraînement, validation, export, live
  ou test verrouillé n'a été exécuté. La revue externe de `8190e3b` a ensuite
  autorisé l'unique préinscription réelle. Elle a réussi sur le Mac au même
  commit : manifeste `b28cb17…` stable avant/après, `31` exclusions GAPS/10
  joueurs, `541` captures planifiées et `541` entrées d'actifs, plan v2 SHA
  `a8347e4e…`, registre SHA `12dd74f2…`, aucune exclusion dans le registre et
  `locked_test_used=false`. Les trois artefacts bruts locaux et leur SHA sont
  archivés dans le rapport du 2026-08-09. Aucun replay, collecteur, minage,
  entraînement, validation, export, live ou test verrouillé n'a démarré. La
  revue externe de cette préinscription est maintenant approuvée. Un mineur
  train-only borné est implémenté sans calcul réel : CPU obligatoire, commit
  Git exact/worktree propre, sept SHA avant TensorFlow, 12 prises
  préassignées, écriture atomique sous `data/processed`, aucune perte tolérée
  et `fit_authorized=false`. La revue externe de `0e124352…` a ensuite trouvé
  deux défauts avant le premier replay : le SHA Git à 40 caractères était
  vérifié comme un SHA-256, et `data.py` importait TensorFlow au chargement du
  CLI avant les empreintes. Le correctif diffère les imports runtime
  `data`/contexte/Keras après les sept empreintes, le lien YAML-manifeste et le
  préflight CPU; il ajoute une validation Git dédiée et un test frais qui
  confirme qu'un mauvais SHA de checkpoint échoue avec TensorFlow absent.
  `py_compile`, `git diff --check` et 41 tests ciblés passent en 2,025 s.
  Aucun actif Policy A, checkpoint réel, inférence, replay, collecteur, minage,
  entraînement, validation, export, live ou test verrouillé n'a été exécuté.
  Une dernière revue externe de ce correctif est obligatoire avant l'unique
  replay Mac. Après l'approbation de `9ed93e7`, le préflight Mac a trouvé une
  nouvelle divergence avant tout CLI ou import TensorFlow : la politique audio
  versionnée était hachée en CRLF sur Windows (`bf4c…`) mais en LF sur macOS,
  comme le blob Git (`45ed…`). Les six autres entrées sont conformes; aucun
  actif, checkpoint, contexte, replay ni sortie n'a été ouvert ou produit. Le
  correctif impose LF pour les quatre configurations versionnées scellées et
  adopte `45ed…` dans le protocole. `py_compile`, `git diff --check` et 42
  tests ciblés passent en 1,721 s. La revue externe de `f4eb87a` est approuvée.
  L'unique minage CPU train-only a donc été exécuté sur le Mac : préflight
  complet réussi (`7/7` SHA, worktree propre, CPU forcé, verrou absent), job
  `decoder-candidate-bounded-mining-cpu-20260809` terminé avec `exit_code=0`
  en 6 min 17 s et `locked_test_used=false`. Les artefacts Mac
  `candidate_events.jsonl` (`19cb073a…`) et `mining_report.json`
  (`3ad78ede…`) sont intègres. Ils contiennent 12 prises préinscrites, 429
  candidats supervisés (`94` positifs causaux, `335` faux NoteOn), zéro perte
  de collecte et aucun motif non instrumenté autre que 169 retriggers exclus.
  La revue externe de `83afcf34` approuve le pilote, mais confirme qu'il est
  insuffisant pour le fit : `fit` ne contient que 123 exemples, dont 23
  positifs, et certaines cellules GuitarSet n'ont qu'une classe. Le résultat
  reste **non autorisant** (`fit_authorized=false`). Le prochain contrat,
  également sans calcul, fixe six prises canoniques par corpus et partition
  (72 prises) et des seuils préenregistrés de représentation avant toute revue
  ultérieure, publiés automatiquement comme une porte non autorisante. Il
  complète aussi la réconciliation future du flux complet avec
  les compteurs `full_flow_invalid_frame` et `full_flow_outside_audio`. Les 45
  tests synthétiques ciblés, `py_compile` et `git diff --check` passent. La
  revue ChatGPT de ce nouveau contrat est obligatoire avant tout second minage.
  Aucun fit, calibration, validation, sélection de seuil, export, live ou test
  verrouillé n'est permis.
- Mise à jour du `2026-08-09T22:18:38+04:00` : le second minage CPU train-only
  autorisé a terminé au commit `42a88b0d…` sur les 72 prises canoniques, après
  préflight complet des sept SHA. Il produit 3 057 lignes supervisées
  (639 positives, 2 418 négatives), zéro tentative perdue, 3 057 `event_id`
  uniques, 54 groupes physiques sans croisement de partition et
  `locked_test_used=false`. Trois prises GuitarSet sélectionnées n'ont pas
  produit de candidat supervisé, ce qui est conservé comme constat de
  population. La porte préenregistrée échoue uniquement pour les positifs
  `guitarset_poly_mix` (`dev=6`, `calibration=7`, minimum 8) ;
  `fit_authorized=false` est maintenu. Aucun fit, calibration, validation,
  export, live, sélection de seuil ou test verrouillé ne suit. La seule étape
  suivante est la revue humaine du rapport
  `readme/results/2026-08-09_decoder-candidate-extended-mining-run.md` avant
  de définir une hypothèse distincte.
- Hypothèse v3 désormais implémentée, sans calcul :
  `configs/decoder_candidate_guitarset_expansion_policy_a_v3.json` scelle à
  nouveau les mêmes entrées et fixe 90 prises canoniques, soit 6 par
  corpus × partition sauf 12 pour GuitarSet. Les premiers six GuitarSet sont
  conservés et les six suivants par partition sont ajoutés dans le même corpus
  candidat futur ; la porte reste à 8 et `fit_authorized=false` reste
  inconditionnel. Les schémas précédents gardent leur sélection uniforme et le
  schéma 3 refuse une table de comptes incomplète. Compilation, `git diff
  --check` et 67 tests synthétiques ciblés passent en 2,157 s. Aucune donnée
  projet, inférence, minage, fit, calibration, validation, export, live ou test
  verrouillé n'a été exécuté. La revue externe de `8c92eb0` a relevé que le
  CLI pouvait encore recevoir un autre JSON v3 tout en gardant les sept SHA
  internes. Le correctif suivant exige donc, avant Git, actifs ou TensorFlow,
  le chemin exact du protocole v3 versionné et son SHA-256 LF
  `db55930a9faadc12fb7b08e52e0baac3543e3d5cb654844ea93e0d727a563683`.
  Les deux substitutions testées (`guitarset=13` par chemin externe, puis
  contenu canonique modifié) échouent avant TensorFlow. `py_compile`,
  `git diff --check` et 69 tests synthétiques ciblés passent en `2,120 s`.
  Aucun actif projet, inférence, minage, fit, calibration, validation, export,
  live ou test verrouillé n'avait été exécuté au moment de ce correctif. La
  revue externe l'a ensuite approuvé et l'unique job CPU V3
  `decoder-candidate-guitarset-v3-cpu-20260809` a démarré à
  `2026-08-09T19:07:52Z` au commit exact `4ddc886…`. CPU forcé, limite murale
  `3 600 s`, verrou actif. Le job termine ensuite avec `exit_code=0` et
  `complete_non_authorizing` : 3 139 candidats supervisés (684 positifs,
  2 455 négatifs), 0 perte et 3 139 `event_id` uniques. La porte à 8 passe,
  dont GuitarSet positif `31/28/14`, mais `fit_authorized=false` et
  `locked_test_used=false` restent obligatoires. Aucune autre action
  scientifique n'est autorisée avant la revue du rapport terminal.
  Rapports :
  `readme/results/2026-08-09_decoder-candidate-guitarset-expansion-hypothesis.md`
  et `readme/results/2026-08-09_decoder-candidate-guitarset-protocol-binding-fix.md`,
  puis `readme/results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md`.
- Revue externe de `9d360816` : **approuvée**. V3 clôt le minage avec une porte
  de représentation passée et sans autoriser un fit. L'hypothèse suivante est
  donc préenregistrée, sans calcul : une régression logistique causale de 12
  entrées strictement pré-porte, entraînée seulement sur les 938 lignes fit du
  corpus V3, pondérée par famille/cible/groupe de fuite pour ne pas doubler les
  vues Guitar-TECHS. Dev choisira l'époque, calibration choisira seule un seuil
  éventuel ; validation historique et test verrouillé restent fermés. La revue
  externe de cette hypothèse est requise avant toute implémentation, et une
  revue distincte avant tout fit. La revue `e90321a1` a autorisé ensuite la
  seule implémentation sans exécution : préflight V3 avec octets hachés une fois,
  projection pré-porte à 12 dimensions, pondération locale fit/dev/calibration,
  BCE dev hors L2, seed `47`, ordre canonique et `shuffle=false`, plus parité
  de sauvegarde/rechargement sans écrasement. Les 42 tests synthétiques ciblés
  passent en `2,015 s`; `rg` confirme l'absence de tout appel `fit(` dans ce
  module. Aucun artefact V3 réel, fit, calibration, validation, export, live ou
  test verrouillé n'a été utilisé. Une nouvelle revue externe est obligatoire
  avant toute décision de fit. La revue de `76ebf937` approuve le protocole V1
  et autorise seulement un runner sans exécution. Ce runner n'accepte aucun
  poids ni hyperparamètre externe, exige l'accusé `DECODER_CANDIDATE_FIT_EXECUTE=1`,
  Git propre exact, CPU, artefacts V3 hachés et destination fraîche ; il limite
  l'entraînement à `fit`, évalue dev par inférence/BCE hors L2, ne calibre
  qu'après dev et persiste le standardiseur lié au modèle. Compilation,
  `git diff --check` et 47 tests synthétiques ciblés passent en `5,388 s`.
  Aucun job Mac, fit, calibration, validation, export, live ou test verrouillé
  n'a été lancé. Une revue externe supplémentaire du runner est obligatoire.
  La revue de `5de7f7ef` a ensuite demandé un correctif préalable, sans donnée
  projet : le runner convertit maintenant explicitement les entrées Keras
  `fit` en tableaux NumPy `float32`, persiste la courbe fit/dev par époque,
  la décomposition des poids par partition/famille/cible/groupe et le coût
  d'inférence par candidat. Un test Keras synthétique traverse une époque
  réelle avec ce même chemin et les 48 tests ciblés passent. Aucun artefact V3,
  fit réel, calibration, validation, export, live ou test verrouillé n'a été
  ouvert. Le prochain lancement, seulement après revue externe, devra passer
  exclusivement par `scripts/remote/mac_worker.sh start` sur CPU avec timeout
  externe de 900 s; jamais directement par le module Python. Rapport :
  `readme/results/2026-08-09_decoder-candidate-fit-runner-evidence-correction.md`.
  Rapports :
  `readme/results/2026-08-09_decoder-candidate-fit-hypothesis-v1.md`, puis
  `readme/results/2026-08-09_decoder-candidate-fit-protocol-implementation.md`,
  puis `readme/results/2026-08-09_decoder-candidate-fit-runner-implementation.md`.
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
- [2026-08-08 — préinscription bloquée par le chevauchement GAPS](results/2026-08-08_decoder-candidate-preregistration-blocked-by-gaps-leakage.md)
- [2026-08-09 — contrat de politique A pour le chevauchement GAPS](results/2026-08-09_decoder-candidate-gaps-policy-a-contract.md)
- [2026-08-09 — préinscription réelle Policy A](results/2026-08-09_decoder-candidate-policy-a-preregistration.md)
- [2026-08-09 — mineur borné de candidats du décodeur](results/2026-08-09_decoder-candidate-bounded-miner.md)
- [2026-08-09 — correctif du préflight du mineur borné](results/2026-08-09_decoder-candidate-bounded-miner-preflight-fix.md)
- [2026-08-09 — correctif CRLF/LF du préflight du mineur borné](results/2026-08-09_decoder-candidate-bounded-miner-eol-preflight-fix.md)
- [2026-08-09 — passe CPU du mineur borné Policy A](results/2026-08-09_decoder-candidate-bounded-mining-run.md)
- [2026-08-09 — contrat d'extension Policy A à six prises par cellule](results/2026-08-09_decoder-candidate-expanded-policy-a-contract.md)
- [2026-08-09 — passe CPU étendue Policy A, porte refusée](results/2026-08-09_decoder-candidate-extended-mining-run.md)
- [2026-08-09 — hypothèse d'extension GuitarSet canonique](results/2026-08-09_decoder-candidate-guitarset-expansion-hypothesis.md)
- [2026-08-09 — correctif de scellement du protocole GuitarSet v3](results/2026-08-09_decoder-candidate-guitarset-protocol-binding-fix.md)
- [2026-08-09 — minage CPU V3 GuitarSet, porte passée mais non autorisant](results/2026-08-09_decoder-candidate-guitarset-v3-mining-run.md)
- [2026-08-09 — hypothèse V1 de fit du filtre causal de candidats](results/2026-08-09_decoder-candidate-fit-hypothesis-v1.md)
- [2026-08-09 — implémentation V1 du protocole de fit causal](results/2026-08-09_decoder-candidate-fit-protocol-implementation.md)
- [2026-08-09 — implémentation du runner V1 de fit causal](results/2026-08-09_decoder-candidate-fit-runner-implementation.md)
- [2026-08-09 — correctif de transport et préinscription A/B historique V1](results/2026-08-09_causal-candidate-fit-v1-transport-and-validation-preregistration.md)
- [2026-08-09 — implémentation A/B historique du filtre causal V1](results/2026-08-09_causal-candidate-validation-ab-implementation.md)
- [2026-08-09 — contrat d'invocation A/B historique du filtre causal V1](results/2026-08-09_causal-candidate-validation-ab-invocation-contract.md)
- [2026-08-09 — correctif pré-métrique du contrat A/B historique](results/2026-08-09_causal-candidate-validation-ab-threshold-contract-fix.md)
- [2026-08-09 — relance CPU A/B historique V1, résultat non autorisant](results/2026-08-09_causal-candidate-validation-ab-v1-run.md)
- [2026-08-09 — hypothèse V2 de porte causale post-ranking](results/2026-08-09_causal-candidate-v2-post-ranking-hypothesis.md)
- [2026-08-09 — implémentation synthétique de la porte causale V2](results/2026-08-09_causal-candidate-v2-synthetic-implementation.md)
- [2026-08-09 — intégration A/B synthétique explicite de la porte V2](results/2026-08-09_causal-candidate-v2-synthetic-integration.md)
- [2026-08-09 — protocole du diagnostic V2 train-only dev](results/2026-08-09_causal-candidate-v2-train-dev-diagnostic-protocol.md)
- [2026-08-09 — implémentation du runner V2 train-only dev](results/2026-08-09_causal-candidate-v2-train-dev-diagnostic-runner-implementation.md)
- [2026-08-10 — anomalie de préflight V2, artefacts locaux Mac absents](results/2026-08-10_causal-candidate-v2-train-dev-preflight-missing-local-artifacts.md)
- [2026-08-10 — matérialisation V2 bloquée, octets sources absents](results/2026-08-10_causal-candidate-v2-artifact-materialization-blocked.md)
- [2026-08-10 — sources exactes V2 retrouvées, copie encore interdite](results/2026-08-10_causal-candidate-v2-artifact-source-recovered.md)
- [2026-08-10 — matérialisation binaire contrôlée des artefacts V2 scellés](results/2026-08-10_causal-candidate-v2-artifact-materialization.md)
- [2026-08-10 — diagnostic V2 train/dev CPU, résultat exploratoire non promotionnel](results/2026-08-10_causal-candidate-v2-train-dev-diagnostic-run.md)
- [2026-08-10 — contrat d'évaluation V2 indépendante GAPS/Guitar-TECHS, sans calcul](results/2026-08-10_causal-candidate-v2-independent-validation-contract.md)
- [2026-08-10 — runner/provenance synthétique de l'évaluation V2 indépendante](results/2026-08-10_causal-candidate-v2-independent-validation-runner-implementation.md)
- [2026-08-10 — contrat d'exécution déclaratif de l'évaluation V2 indépendante](results/2026-08-10_causal-candidate-v2-independent-validation-execution-contract.md)
- [2026-08-10 — frontière d'exécution directe de l'évaluation V2 indépendante](results/2026-08-10_causal-candidate-v2-independent-validation-runner-contract-only.md)

Les rapports détaillés restent des preuves horodatées. Le présent fichier est
le seul résumé global et doit toujours refléter l’étape courante et la suite.
