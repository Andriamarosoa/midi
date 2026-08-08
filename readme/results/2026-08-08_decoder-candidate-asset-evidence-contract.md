# Contrat d'empreintes des actifs — candidats du décodeur

## Périmètre

- Branche : `codex/independent-note-neural-v2`.
- Nature : code de provenance et tests synthétiques uniquement.
- Aucun manifeste réel, plan réel, audio projet, labels projet, modèle,
  décodeur, minage, entraînement, évaluation, export, live ou test verrouillé
  n'a été ouvert ou exécuté.

## Problème fermé par le contrat

Le snapshot précédent scellait les octets du CSV et les objets `ManifestItem`,
mais un fichier audio ou labels pouvait théoriquement changer entre la revue du
manifeste et son ouverture future. Le nouveau module
`decoder_candidate_asset_evidence.py` prépare la preuve nécessaire avant cette
première ouverture.

Pour chaque capture du split train, il enregistre de façon canonique :

- `dataset_id`, `source_id`, `capture_id` et partition préassignée ;
- `audio_member` ;
- taille et SHA-256 du conteneur audio ;
- taille et SHA-256 du fichier de labels.

Les chemins absolus ne sont pas sérialisés : le manifeste déjà hashé conserve
l'association aux chemins, ce qui maintient la portabilité Windows/Mac. Le
registre est lié aux SHA du manifeste et du plan de partition.

## Garde-fous

1. La preuve est écrite sans écrasement, relue en JSON canonique et attestée
   par une capacité émise uniquement par le chargeur.
2. Un wrapper construit manuellement, des octets modifiés, un autre manifeste,
   un autre plan, une capture absente ou une partition différente échouent fermé.
3. `DecoderCandidateMiningContext.open_recording()` refuse désormais toute
   ouverture sans preuve persistée. Avant `PolyphonicCorpus`, il vérifie à
   nouveau les octets audio et labels exacts de la capture demandée.
4. Les collecteurs restent inutilisables comme chemin de données : le futur
   replay officiel doit passer par ce contexte pour ouvrir le corpus.

## Validation locale

La compilation Python et `git diff --check` réussissent. La suite ciblée
contient les précédents tests de provenance, retriggers et instrumentation,
plus les nouveaux tests synthétiques d'actifs :

```text
Ran 134 tests in 9.429s
OK
```

Les nouveaux cas couvrent la couverture train-only complète, le rehash de
l'actif juste avant ouverture, une modification de labels, un wrapper persistant
forgé, la modification des octets du registre et un registre volontairement
incomplet. Les fichiers créés par les tests sont temporaires.

## Limite et décision

Ce commit ne préenregistre aucune empreinte réelle. Après revue externe, la
préinscription réelle devra se faire sur le Mac, puis le plan et le registre
résultants devront être revus avant toute collecte train-only.

`locked_test_used=false` reste inchangé.
