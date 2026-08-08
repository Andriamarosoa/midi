# Protocole snapshot et étiquettes causales des candidats du décodeur

## Décision et périmètre

Cette étape applique uniquement la suite autorisée par la revue de
`bde4a72` : un protocole de préflight pour le futur minage train-only, sans
exécuter le mineur. Elle ne lance ni décodage sur les données du projet, ni
entraînement, validation officielle, export, live ou test verrouillé.

Les plans créés dans les tests sont temporaires et synthétiques. Aucun plan
réel n'a été préenregistré, aucun audio ou fichier de labels réel n'a été
ouvert, et aucun artefact candidat n'a été produit.

## Snapshot manifeste, plan immuable et contexte train-only

`load_manifest_snapshot()` lit une seule fois les octets du manifeste complet,
calcule leur SHA-256, puis construit depuis ce même buffer les objets complets
`ManifestItem` : identité, split, chemins audio/labels résolus, membre archive
et licence. Les chemins relatifs sont résolus depuis le répertoire du manifeste
plutôt que depuis le répertoire courant.

Le snapshot chargé est attesté par identité de processus. Une construction
manuelle, une structure ressemblante, ou une copie `dataclasses.replace()` qui
substitue les chemins audio/labels ne peut pas servir à construire ou valider un
plan. La capacité validée qui relie le plan au snapshot est attestée de la même
manière; un collecteur refuse une copie de cette capacité.

Le plan est sérialisé en JSON canonique et immuable : l'écriture refuse un
chemin déjà existant, la relecture vérifie les octets exacts, et le contexte
revérifie le digest du fichier avant de créer un collecteur, d'ouvrir une prise
ou d'agréger des labels. Un wrapper de plan construit à la main, un plan réécrit
ou une prise validation est refusé. Les groupes de fuite ne peuvent pas être
partagés entre train et validation pour cette voie candidate.

Le contexte `DecoderCandidateMiningContext` est le futur point de passage :

```text
snapshot manifeste attesté
  -> plan persistant relu et attesté
  -> capacité snapshot/plan validée
  -> même ManifestItem pour PolyphonicCorpus et collecteur
```

Cela lie les **chemins déclarés** dans le manifeste exact aux objets utilisés
plus tard. L'empreinte des octets d'audio/labels eux-mêmes reste une
précondition distincte à préenregistrer avant toute première ouverture réelle;
elle n'est pas calculée dans ce commit sans calcul et n'autorise donc aucun
minage.

## Cibles causales et population réellement apprise

La seule population entraînable reste :

```text
gate_eligible=True et emitted_noteon=True
```

Pour chaque événement retenu, l'horodatage est exactement
`(frame_index + 1) * hop_size / sample_rate`, identique à la convention de fin
de hop du décodeur. Le matcher partagé
`match_causal_note_ons()` applique l'association same-pitch, une-à-une,
strictement causale, avec une limite inclusive de 250 ms : une référence future
ne peut jamais rendre un NoteOn positif.

- une correspondance causale donne `causal_noteon_target=1` ;
- une prédiction non correspondante donne `causal_noteon_target=0` ;
- une frame invalide ou hors audio est comptée comme exclue, jamais transformée
  en négatif ;
- seules les notes de référence `note_evaluation_valid` avec une durée positive
  sont admissibles.

Les retriggers du chemin déjà-actif ne disposent pas d'une décision pré-porte :
ils sont donc exclus explicitement et comptés sous `retrigger`. Toute autre
NoteOn non instrumentée fait échouer le batch. Le mineur futur devra aussi
fournir explicitement le latch `decoder.candidate_collection_error`; une erreur
de collecte refuse les labels avant toute agrégation.

La projection `LabeledDecoderCandidateEvent.model_features()` est la seule
projection prévue pour un futur fit. Elle expose exactement `CAUSAL_FEATURES`
et exclut cible, match, latence, ID, provenance et métadonnées post-porte.

## Compteurs d'autorisation future

Chaque batch transporte le SHA du manifeste, le SHA du plan, l'identité
`(dataset_id, source_id, capture_id)` et la partition. L'agrégation refuse :

- pertes de buffer ;
- mélange de manifestes ou de plans ;
- même prise rejouée deux fois ;
- `event_id` entraînable dupliqué entre lots ;
- mélange de partitions ;
- sous-ensemble ou couverture incomplète par rapport à une partition
  préassignée.

Les compteurs conservent les tentatives, exclusions, NoteOn instrumentées/non
instrumentées par raison, cibles 0/1, références ratées, identités de prises et
répartition `dataset × partition × cible`. Ils constituent seulement un garde
de préflight en mémoire : ils ne produisent ni n'autorisent un artefact.

## Vérifications locales

Avant le commit, `py_compile` et `git diff --check` sont rejoués, puis la suite
Windows ciblée est exécutée depuis le worktree
`codex/independent-note-neural-v2` :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest \
  tests.test_decoder_candidate_snapshot_protocol \
  tests.test_decoder_candidate_labels \
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

Résultat : **128 tests réussis en 7,438 s**. Les tests couvrent notamment les
copies de snapshot/capacité validée, les chemins substitués, le plan non
persisté ou modifié, la fuite train/validation, l'horodatage frame zéro, les
bornes 250/251 ms, les références futures, les frames invalides, les retriggers,
les doublons inter-lots et la parité du décodeur instrumenté.

`locked_test_used=false`. Ces tests de contrat ne sont pas un calcul
scientifique et ne modifient aucun résultat précédemment archivé.

## Action conditionnelle suivante

Faire relire ce commit. Après approbation seulement, préenregistrer le plan
réel et la preuve d'actifs requise, les faire relire, puis demander une
autorisation distincte avant le premier minage train-only. Aucun seuil,
checkpoint ou résultat antérieur n'est promu par cette étape.
