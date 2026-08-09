# Sources historiques V2 retrouvées et vérifiées

Branche : `codex/independent-note-neural-v2`

État : preuve de source terminée ; aucune copie ni reprise V2 autorisée avant
revue.

## Recherche

Les fichiers étaient absents du worktree Windows et de
`/Users/amcarene/midi-worker`, mais une recherche en lecture seule dans les
checkouts Mac antérieurs les a retrouvés sous :

```text
/Users/amcarene/midi/tmp/local/
  decoder_candidate_policy_a_preregistration_20260809/
    decoder_candidate_partition_plan_v2.json
    decoder_candidate_asset_evidence_v1.json
```

Ce sont des fichiers locaux ignorés par Git ; leur provenance repose donc sur
leurs octets et non sur un commit les contenant.

## Empreintes source vérifiées

Les commandes de lecture seule `stat -f %z` et `shasum -a 256` ont produit :

| Fichier | Taille | SHA-256 | SHA scellé |
|---|---:|---|---|
| `decoder_candidate_partition_plan_v2.json` | 145 859 octets | `a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4` | conforme |
| `decoder_candidate_asset_evidence_v1.json` | 198 950 octets | `12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507` | conforme |

Les deux valeurs correspondent exactement à celles gelées par le protocole V2
et par la revue de matérialisation. Aucun contenu JSON n'a été lu, modifié ou
reconstruit.

## Limites et prochaine action

Cette étape n'a créé aucun dossier sous
`/Users/amcarene/midi-worker/repository/tmp/local`, n'a transféré aucun octet,
n'a lancé ni Python ni le worker V2 et n'a ouvert aucun audio, label, modèle ou
checkpoint. Le Mac reste sans job lourd actif.

La prochaine action proposée est une revue externe de cette preuve. Si elle est
favorable, la seule opération autorisable sera une copie locale binaire et
atomique des deux fichiers source vers le chemin exact attendu par le runner,
suivie de la comparaison de leurs tailles et SHA-256 côté destination. Toute
reprise des 30 prises V2 reste interdite jusque-là.
