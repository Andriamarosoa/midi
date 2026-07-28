# Résumé unique — Guitar MIDI AI

> Dernière mise à jour manuelle : 2026-07-28
>
> Branche active : `codex/cleanup-cloud-training-docs`
>
> Règle : ce fichier est le résumé chronologique unique du projet. Chaque
> étape terminée, active, suivante ou en anomalie doit y être inscrite.
## Objectif

Produire sur desktop un moteur causal audio de guitare vers MIDI, monophonique
et polyphonique, avec peu de notes fantômes, une latence compatible avec le
live et des entraînements reproductibles exécutés sur Kaggle ou Colab.

<!-- CURRENT_STATUS_START -->
## État courant

- Mise à jour : `2026-07-28T19:50:13.679747+00:00`
- Étape : `keras2_checkpoint_compatibility_fix_validated`
- Statut : `en cours`
- Détail : OAuth Kaggle rétabli et log exact de la version 1 récupéré. Échec à 81.48 s au premier checkpoint : TensorFlow 2.20/Keras 3 ne peut pas importer keras.src.engine.functional enregistré par Keras 2. Correction : détection des archives Keras 2, reconstruction de l'architecture causale depuis config.json et chargement de model.weights.h5 ; appliquée au classement et aux étapes polyphoniques aval. Parité sur epoch-01 : écart maximal 0.0 pour frame, onset, amplitude harmonique et offset. 19 tests passent. Le publisher peut maintenant limiter maximum_examples pour un probe validation-only.

## Étapes suivantes

1. Committer/pousser, publier un snapshot source privé, lancer un probe P100 rank sur 128 exemples avec un slug unique. Si le probe Keras 3 passe et locked_test_used=false, lancer le classement 60000 sans autre changement. Ne pas ouvrir le test verrouillé.
<!-- CURRENT_STATUS_END -->

## État technique consolidé
### Produit monophonique

- Périmètre accepté : guitare propre monophonique, MIDI 40–76.
- Parité TFLite et ONNX validée.
- Inférence compatible avec le live.
- Limite : une sortie softmax unique ne transcrit pas les accords.
### Produit polyphonique V2.2
- Entrée causale : 4096 échantillons à 44,1 kHz, hop 256.
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
fondamentale contre harmonique/résonance.
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
- 2026-07-28 — **en cours** — `checkpoint_validation_selection` : OAuth Kaggle rétabli et log exact de la version 1 récupéré. Échec à 81.48 s au premier checkpoint : TensorFlow 2.20/Keras 3 ne peut pas importer keras.src.engine.functional enregistré par Keras 2. Correction : détection des archives Keras 2, reconstruction de l'architecture causale depuis config.json et chargement de model.weights.h5 ; appliquée au classement et aux étapes polyphoniques aval. Parité sur epoch-01 : écart maximal 0.0 pour frame, onset, amplitude harmonique et offset. 19 tests passent. Le publisher peut maintenant limiter maximum_examples pour un probe validation-only.
<!-- PROJECT_TASK:checkpoint_validation_selection:END -->
<!-- PROJECT_TASK:skill_project_contract:START -->
- 2026-07-28 — **terminé** — `skill_project_contract` : skill
  guitar-audio-midi-researcher enrichi avec le contrat permanent du projet,
  puis rendu autonome : lecture complète obligatoire de `readme/README.md`,
  vérification Git/artifacts avant toute action, interrogation des compteurs
  réels à chaque demande de progression sans extrapolation, puis mise à jour
  de la même entrée de journal en fin d’étape ; validation réussie
<!-- PROJECT_TASK:skill_project_contract:END -->
<!-- JOURNAL_END -->
## Rapports détaillés

- [2026-07-22 — entraînement polyphonique multi-source](results/2026-07-22_polyphonic-training.md)
- [2026-07-27 — validation du décodeur desktop polyphonique](results/2026-07-27_polyphonic-desktop-validation.md)
- [2026-07-28 — état du produit desktop monophonique](results/2026-07-28_mono-desktop-release.md)
- [2026-07-28 — reconstruction de `data/processed`](results/2026-07-28_processed-reconstruction.md)
- [2026-07-28 — incident de publication Kaggle](results/2026-07-28_kaggle-upload-incident.md)

Les rapports détaillés restent des preuves horodatées. Le présent fichier est
le seul résumé global et doit toujours refléter l’étape courante et la suite.
