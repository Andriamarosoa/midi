# Résumé unique — Guitar MIDI AI

> Dernière mise à jour manuelle : 2026-07-29
>
> Branche active : `codex/dual-stream-bass`
>
> Règle : ce fichier est le résumé chronologique unique du projet. Chaque
> étape terminée, active, suivante ou en anomalie doit y être inscrite.
## Objectif

Produire sur desktop un moteur causal audio de guitare vers MIDI, monophonique
et polyphonique, avec peu de notes fantômes, une latence compatible avec le
live et des entraînements reproductibles exécutés sur Kaggle ou Colab.

<!-- CURRENT_STATUS_START -->
## État courant

- Mise à jour : `2026-07-29T18:40:10.3086760+04:00`
- Étape : `dual_stream_bass_candidate`
- Statut : `en cours`
- Détail : L'échec de 12 heures est expliqué : le prétendu cache RAM de 8,78 Gio conservait 7,28 Gio de NPY en `memmap` sur `/kaggle/input`; un lot de 64 touchait en moyenne 59,44 enregistrements et provoquait environ 35 lectures NPY aléatoires, tandis que les 4 workers annoncés n'atteignaient pas Keras 3. Aucun problème CUDA n'a été trouvé. Le staging copie désormais uniquement les audio/labels train-validation vers le disque local Kaggle, avec contrôle d'espace, remplacement atomique et rejet du test avant toute copie. Le chargeur Keras 3 reçoit réellement ses workers et l'augmentation est pré-calculée, donc indépendante de l'ordre concurrent des lots. Le train écrit un `batch_progress.json` atomique et une ligne `BATCH_PROGRESS` toutes les 25 batches avec débit, projection, RSS et utilisation GPU. Le kernel train est séparé du classement/sélection/export et s'arrête proprement avant 600 minutes. Un smoke représentatif est préparé sur tous les enregistrements, 8 192 exemples train + 2 048 validation, budget 30 minutes. Les 34 tests ciblés passent. Le MCP officiel Kaggle est configuré par jeton d'environnement hors dépôt : il expose statut, log live et outputs; CLI conservé pour quota, publication P100 et gros téléchargements. Prochaine action : publier ce snapshot et lancer uniquement le smoke P100 chronométré; le train complet ne sera admis qu'après projection mesurée sûre et reprise intra-époque validée. Test verrouillé exclu.

## Étapes suivantes

1. Capturer la même suite live sans puis avec capodastre, au même niveau et avec WAV/trace complète : cordes graves isolées, accords ouverts/barrés, strums lents/rapides, octaves et harmoniques. Comparer énergie fondamentale/partiels, probabilités par hauteur, erreurs d'octave et notes manquantes. Cette capture servira au diagnostic, pas au test verrouillé.
2. Conserver le remplacement par transposition +12/−12 uniquement comme diagnostic offline désactivé ; ne pas confondre ce test négatif avec la future architecture à deux flux.
3. Valider le candidat causal à deux représentations par le smoke Kaggle, sans entraîner localement et sans utiliser le test verrouillé.
4. Si le smoke passe, entraîner ce seul changement d'architecture sur Kaggle, initialisé depuis V2.2, puis comparer sur validation les graves MIDI 40–51, les erreurs d'octave, les accords et chaque corpus.
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
- 2026-07-29 — **en cours** — `live_ab_adaptive_attack` : L'audit du train annulé confirme un goulot d'étranglement I/O, pas une erreur CUDA : les NPY restaient des `memmap` montés sur `/kaggle/input` et les workers n'étaient pas transmis à Keras 3. Les données train-validation sont maintenant matérialisées sur le disque local Kaggle avec garde d'espace et exclusion précoce du test; le chargeur est concurrent et déterministe par lot. Les logs donnent toutes les 25 batches le débit, la projection, la mémoire et l'utilisation GPU dans `batch_progress.json`. Train et post-train sont séparés, avec budgets 30 minutes pour le smoke représentatif 8 192/2 048 et 600 minutes pour le train. Le MCP officiel Kaggle est opérationnel via un jeton d'environnement non versionné et offre un second canal pour statut/log/outputs. Les 34 tests ciblés passent. Étape active : publier le snapshot puis exécuter seulement le smoke P100; aucun train complet avant mesure de débit et validation d'une reprise intra-époque exacte. Test verrouillé exclu.
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
