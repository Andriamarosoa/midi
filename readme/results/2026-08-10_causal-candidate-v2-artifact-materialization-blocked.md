# Matérialisation V2 bloquée : octets sources introuvables

Branche : `codex/independent-note-neural-v2`
État : aucune écriture ni transfert effectué ; reprise V2 toujours interdite.

## Autorisation examinée

Après la revue de l'anomalie pré-métrique `5aef80d`, la seule action autorisée
était de copier, sans les régénérer, les deux artefacts Policy A exacts déjà
préenregistrés vers :

```text
/Users/amcarene/midi-worker/repository/tmp/local/
  decoder_candidate_policy_a_preregistration_20260809/
    decoder_candidate_partition_plan_v2.json
    decoder_candidate_asset_evidence_v1.json
```

Les SHA requis étaient respectivement :

```text
a8347e4e6300dc59b48eab253186fd60ae21cd769fa21d647db4d7e0893685f4
12dd74f2c868d884f9189e1c8d07c1e7e1cec4e984fda5a68ce434c05e586507
```

## Vérifications réalisées en lecture seule

- recherche récursive par les deux noms sous
  `C:\Users\user\Desktop\midi` : aucun fichier trouvé ;
- recherche par les deux noms sous `/Users/amcarene/midi-worker` : aucun
  fichier trouvé ;
- `git ls-files --error-unmatch` pour les deux chemins attendus : échec pour
  chacun ;
- `.gitignore` contient `tmp/`, donc les octets originaux n'ont pas été
  transportés par le commit Git ;
- `MAC_WORKER.ps1 status` : aucun job actif.

Le Mac conserve seulement `repository/tmp`; le sous-répertoire
`repository/tmp/local` est toujours absent. Aucun dossier n'a été créé et aucun
fichier partiel, transfert SFTP/SCP, conversion de fin de ligne ou réécriture
JSON n'a été tenté.

## Décision

Il serait contraire au contrat de régénérer le plan ou le registre à partir du
manifeste actuel. Sans les deux fichiers sources dont les octets correspondent
aux SHA scellés, aucune comparaison source/Mac et donc aucune matérialisation
contrôlée n'est possible.

La prochaine entrée nécessaire est l'emplacement des deux originaux dans une
sauvegarde accessible, ou leur remise dans le worktree Windows. Après seulement,
une revue devra autoriser une copie binaire avec contrôles SHA source et Mac.
La reprise du diagnostic V2 de 30 prises reste interdite jusque-là.
