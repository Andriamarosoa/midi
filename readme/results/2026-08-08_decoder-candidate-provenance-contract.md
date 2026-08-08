# Contrat de provenance des candidats du décodeur

## Décision et périmètre

Cette étape remplace uniquement le contrat en mémoire de l'instrumentation
des candidats. Elle ne lance aucun décodeur, mineur, entraînement, validation
officielle, export, live ou test verrouillé. Aucun plan réel ni artefact
candidat n'a été produit.

Le point de départ approuvé est `a8cfdfe9a1aa85532b0e73425c209b2d807d6762`.
Le présent changement reste donc une étape de conception testée, soumise à une
nouvelle revue externe avant toute première collecte train-only.

## Provenance et partition préassignée

`src/polyphonic/decoder_candidate_provenance.py` centralise sans TensorFlow le
groupement corpus-aware déjà utilisé par le smoke `independent_note` :

- GuitarSet est groupé par joueur ; GAPS par joueur puis groupe de secours ;
  Guitar-TECHS direct/mic reste groupé par groupe commun ;
- le lecteur de manifeste lit toutes les lignes dans une seule lecture de
  bytes, calcule le SHA-256 de ces mêmes bytes, puis valide le CSV ;
- toute ligne `test` verrouillée est refusée, les lignes `validation` ne sont
  jamais placées dans les partitions train-only ;
- les groupes train reçoivent avant collecte une partition déterministe
  `fit`, `dev` ou `calibration` selon la politique
  `corpus_aware_leakage_group_hash_70_15_15` ;
- le plan v1 sérialisable persiste `source_id`, `dataset_id`, `group_id`,
  `capture_id`, clé de fuite et partition, avec `locked_test_used=false`.

Une identité de plan est maintenant `(dataset_id, source_id, capture_id)` :
plusieurs captures futures pour une même source ne sont pas écrasées. Tout
changement de groupe ou de clé de fuite est également comparé lorsque l'item
est résolu.

`validate_decoder_candidate_partition_plan_from_manifest()` compare un plan
au manifeste exact avant de produire `ValidatedDecoderCandidatePartition`.
`DecoderCandidateCollector` exige cet objet validé et un item du manifeste ; il
ne prend plus une partition libre. Ainsi une capture inconnue, une provenance
altérée ou une partition inventée échoue avant l'enregistrement d'une ligne.

Ce commit ne crée volontairement pas de plan sur les données réelles. Après
revue, le futur mineur devra construire, persister et revalider ce plan depuis
le manifeste train/validation exact **avant son premier décodage**.

## Unité d'apprentissage retenue

L'unité de la première expérience est un unique vrai NoteOn du décodeur :

```text
gate_eligible=True et emitted_noteon=True
```

`collapse_emitted_candidate_episodes()` est supprimé. Un NoteOn répété reste
une décision séparée et doit rester appariable séparément à la vérité causale.
Un `event_id` dupliqué est une erreur d'artefact fail-closed, pas une occasion
de sélectionner arbitrairement le score maximal.

Les IDs passent à `decoder-noteon-v2`. Ils sont dérivés de :

```text
dataset_id, source_id, group_id, capture_id, leakage_group_key,
frame_index, pitch
```

La partition est volontairement exclue : elle décrit l'usage train/dev/calib,
non l'identité physique de l'événement.

## Vérifications locales

La compilation Python et `git diff --check` ont réussi. La commande de tests
Windows suivante a réussi dans le worktree
`codex/independent-note-neural-v2` :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest \
  tests.test_decoder_candidate_provenance \
  tests.test_decoder_candidate_mining \
  tests.test_decoder_candidate_instrumentation \
  tests.test_polyphonic_decoder \
  tests.test_polyphonic_desktop_contract \
  tests.test_product_decoder \
  tests.test_polyphonic_validate_live_input_level \
  tests.test_ollama_team \
  tests.test_mac_worker_transport_contract \
  tests.test_polyphonic_smoke_neural_independent_note
```

Résultat : **107 tests réussis en 7,207 s**. Les tests ajoutés couvrent
notamment le plan stable malgré un ordre de manifeste inversé, le chargement et
SHA exact du fichier, le refus du test verrouillé, les cellules CSV invalides,
la dérive de capture/groupe, la provenance plan-vers-collecteur, la capture
multiple, les IDs v2 et l'absence de collapse temporel.

`locked_test_used=false`. Cette vérification unitaire n'est pas un calcul
scientifique et ne change aucun résultat de validation antérieur.

## Action conditionnelle suivante

Faire relire ce commit. Si et seulement si le contrat est approuvé, définir
le protocole de création et de persistance du premier plan réel, le faire
revoir, puis demander une autorisation distincte avant tout minage train-only.
