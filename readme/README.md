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

- Mise à jour : `2026-07-28T13:47:54.463449+00:00`
- Étape : `kaggle_smoke_offline_source_root_running`
- Statut : `en cours`
- Détail : Le smoke pathfix a échoué avant toute donnée ou entraînement à 155,5 s : Kaggle avait décompressé midi_source.tar.gz directement à la racine du dataset, sans dossier midi_source ni source_metadata.json ; le notebook ne reconnaissait donc pas le snapshot et lançait son ancien fallback git clone, qui a échoué car github.com est non résolvable dans le runtime. Correction commit 98d15cc : montage déterministe par slug du dataset source attaché, reconnaissance de la racine décompressée, suppression complète du fallback réseau et refus immédiat si le snapshot manque. Validation locale : notebook JSON valide, compileall réussi, git diff --check réussi et 9 tests cloud réussis. Le nouveau smoke privé tinahandriamarosoa/guitar-midi-polyphonic-smoke-offline-root-20260728 a été soumis une seule fois avec les 16 datasets plus le snapshot 6ce57898 ; statut Kaggle vérifié : RUNNING. Le notebook soumis contient le slug source injecté et aucune référence GitHub/git clone. Test verrouillé exclu ; aucun train complet lancé.

## Étapes suivantes

1. Surveiller le nouveau smoke hors ligne sans le relancer.
2. En cas d'erreur, récupérer le log exact avant toute correction ; en cas de réussite, télécharger et valider output_manifest.json, l'archive, locked_test_used=false, l'assemblage des 16 datasets et les métriques.
3. Présenter le résultat avant toute décision de train complet.
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
- 2026-07-28 — **en cours** — `kaggle_training_dataset_upload` : Le smoke pathfix a échoué avant toute donnée ou entraînement à 155,5 s : Kaggle avait décompressé midi_source.tar.gz directement à la racine du dataset, sans dossier midi_source ni source_metadata.json ; le notebook ne reconnaissait donc pas le snapshot et lançait son ancien fallback git clone, qui a échoué car github.com est non résolvable dans le runtime. Correction commit 98d15cc : montage déterministe par slug du dataset source attaché, reconnaissance de la racine décompressée, suppression complète du fallback réseau et refus immédiat si le snapshot manque. Validation locale : notebook JSON valide, compileall réussi, git diff --check réussi et 9 tests cloud réussis. Le nouveau smoke privé tinahandriamarosoa/guitar-midi-polyphonic-smoke-offline-root-20260728 a été soumis une seule fois avec les 16 datasets plus le snapshot 6ce57898 ; statut Kaggle vérifié : RUNNING. Le notebook soumis contient le slug source injecté et aucune référence GitHub/git clone. Test verrouillé exclu ; aucun train complet lancé.
<!-- PROJECT_TASK:kaggle_training_dataset_upload:END -->
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
