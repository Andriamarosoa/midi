# Matérialisation binaire contrôlée des artefacts V2 scellés

Branche : `codex/independent-note-neural-v2`

État : matérialisation terminée et vérifiée ; aucune reprise V2 n'est autorisée
par cette étape.

## Préconditions vérifiées

Le worker Mac a retourné `No active job.` avant l'opération. Le verrou
`/Users/amcarene/midi-worker/active.lock` était absent. Le dossier destination
attendu n'existait pas encore, ce qui empêchait tout écrasement d'un artefact
antérieur.

Les sources historiques ont été lues uniquement pour leur taille et leur
SHA-256. Elles correspondaient déjà aux deux empreintes préenregistrées du
protocole V2.

## Copie binaire atomique et preuves

Pour chaque fichier, la copie est restée sur le Mac et sur le système de
fichiers final :

```text
source historique
→ destination/.<nom>.part.<pid>
→ taille + SHA-256 du .part
→ mv atomique dans le même dossier
→ taille + SHA-256 finale
```

| Fichier | Source | Octets source | SHA-256 source | Destination | Octets destination | SHA-256 destination |
|---|---|---:|---|---|---:|---|
| `decoder_candidate_partition_plan_v2.json` | `/Users/amcarene/midi/tmp/local/decoder_candidate_policy_a_preregistration_20260809/decoder_candidate_partition_plan_v2.json` | 145 859 | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` | `/Users/amcarene/midi-worker/repository/tmp/local/decoder_candidate_policy_a_preregistration_20260809/decoder_candidate_partition_plan_v2.json` | 145 859 | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` |
| `decoder_candidate_asset_evidence_v1.json` | `/Users/amcarene/midi/tmp/local/decoder_candidate_policy_a_preregistration_20260809/decoder_candidate_asset_evidence_v1.json` | 198 950 | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` | `/Users/amcarene/midi-worker/repository/tmp/local/decoder_candidate_policy_a_preregistration_20260809/decoder_candidate_asset_evidence_v1.json` | 198 950 | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` |

Les deux triplets `source = .part = destination` sont conformes aux SHA
scellés. Après le renommage, le contrôle confirme l'absence de fichier `.part`
résiduel et l'absence de verrou actif.

Un premier contrôle post-copie a rencontré le comportement normal de `zsh`
lorsqu'un glob sans correspondance est évalué ; il n'a modifié aucun fichier.
Le contrôle suivant, sans glob, a confirmé `residual_part_files=none` et
`worker_active_lock=absent`.

## Limites et prochaine action

Cette opération n'a pas parsé ou réécrit les JSON, et n'a lancé ni Python,
TensorFlow, runner V2, replay, audio, labels, modèle, checkpoint, inférence,
métrique, fit, calibration, validation, export, live ou test verrouillé.

Les deux artefacts requis sont maintenant à l'emplacement exact attendu par le
runner, mais les 30 prises V2 n'ont toujours pas été observées. La prochaine
action est exclusivement une revue externe de cette preuve de matérialisation.
Toute nouvelle invocation V2 reste interdite jusqu'à cette revue.
