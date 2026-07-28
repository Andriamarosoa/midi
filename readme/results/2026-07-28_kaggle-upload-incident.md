# Incident — publication du dataset privé Kaggle

> Date : 2026-07-28  
> Statut : cause identifiée, reconstruction du paquet requise  
> Branche de documentation : `codex/cleanup-cloud-training-docs`

## Objectif

Publier sur Kaggle un dataset privé contenant uniquement les données
polyphoniques de train et de validation, afin d’exécuter le smoke test GPU puis
l’entraînement long sans inclure le test verrouillé.

## Paquet préparé

Le paquet local a été construit et validé avant publication :

| Élément | Valeur |
|---|---:|
| Archive | `polyphonic_train_validation.tar` |
| Taille | 8 418 068 480 octets |
| Validation du paquet | réussie |
| Test verrouillé inclus | non |
| Handle prévu | `tinahandriamarosoa/guitar-midi-polyphonic-train-validation` |
| Visibilité prévue | privée |
| Licence | `CC-BY-4.0` |

Les fichiers de préparation étaient présents dans
`tmp/kaggle/polyphonic-train-validation-upload`.

## Déroulement de l’incident

1. `kaggle datasets list -m` a d’abord confirmé que le compte était joignable,
   mais qu’aucun dataset n’avait été créé.
2. Un petit dataset de test a ensuite été créé puis supprimé avec succès. Les
   permissions du compte et le droit de créer un dataset sont donc valides.
3. Le transfert de l’archive de 8 Go a atteint 100 %, mais l’appel final de
   création a rencontré une expiration ou une absence d’authentification.
4. Après reconnexion, une nouvelle tentative a brièvement fait apparaître le
   dataset comme en cours de traitement, puis la page Kaggle a disparu.
5. Le journal Kaggle a finalement fourni l’erreur déterminante :

   ```text
   Error during creation: An uploaded file or directory name contains an
   invalid character: undefined
   ```

6. Un scan local du paquet a trouvé 120 signalements liés au caractère `#` :

   - 40 noms de labels `.npz` dans le paquet ;
   - 40 noms de fichiers audio dans le ZIP GuitarSet ;
   - les mêmes 40 noms de labels à nouveau visibles dans le TAR final.

Exemples :

```text
00_Funk3-112-C#_comp.npz
00_Jazz2-187-F#_solo.npz
00_Funk3-112-C#_comp_mix.wav
00_Jazz2-187-F#_solo_mix.wav
```

## Cause racine

La publication échoue pendant la validation ou l’indexation côté Kaggle parce
que le paquet contient des noms internes avec `#`.

Le transfert des octets peut donc atteindre 100 % et être déclaré réussi sans
que le dataset soit finalement créé. Le statut de transfert ne doit plus être
considéré comme une preuve de publication.

## Correction retenue

Les sources destinées à Kaggle doivent être reconstruites avec des noms sûrs :

```text
C# -> Csharp
F# -> Fsharp
```

La correction doit rester cohérente sur les trois éléments suivants :

1. noms physiques des labels `.npz` ;
2. noms des membres audio dans le ZIP GuitarSet ;
3. références correspondantes du manifest, notamment `audio_member` et
   `labels_path`.

Un nouveau paquet et un nouveau TAR doivent ensuite être créés sous un chemin
distinct de l’ancien upload.

## Validation obligatoire avant le prochain upload

Avant toute nouvelle transmission de plusieurs gigaoctets :

- vérifier qu’aucun chemin du paquet ne contient `#` ;
- inspecter les noms des membres de tous les ZIP ;
- inspecter les noms de toutes les entrées du TAR ;
- confirmer que les chemins du manifest existent ;
- confirmer que chaque `audio_member` existe dans son ZIP ;
- conserver `locked_test_included: false` ;
- effectuer si possible un test Kaggle avec un paquet réduit.

Le résultat attendu du scan final est :

```text
Problèmes détectés : 0
Aucun caractère # dans le paquet.
Aucun caractère # dans les ZIP.
Aucun caractère # dans le TAR.
```

## Impact sur le code

Le modèle et le code d’entraînement ne nécessitent pas de modification si les
chemins sont toujours lus depuis le manifest corrigé.

En revanche, le pipeline de préparation doit être renforcé pour les futures
publications :

- normaliser ou rejeter les noms incompatibles avant la création du TAR ;
- valider les ZIP imbriqués ;
- arrêter le processus avant l’upload si un caractère interdit est détecté ;
- distinguer explicitement les états `transfert terminé`, `dataset créé` et
  `dataset indexé`.

Les fichiers principalement concernés sont :

- `scripts/cloud/prepare_kaggle_datasets.py`
- `scripts/cloud/publish_kaggle.py`
- `scripts/cloud/kaggle_upload_progress.py`

## État à la fin de l’analyse

La publication Kaggle reste bloquée. L’ancien TAR ne doit plus être utilisé.

La prochaine étape est de renommer les sources destinées à Kaggle, mettre à
jour le manifest, reconstruire un nouveau TAR validé, puis créer le dataset
privé et confirmer sa présence avec la liste des fichiers côté Kaggle.

## Preuves

- `tmp/kaggle/polyphonic-train-validation-upload/package_report.json`
- `tmp/kaggle/polyphonic-train-validation-upload/dataset-metadata.json`
- sortie de `scripts/cloud/kaggle_upload_progress.py`
- journal de création Kaggle contenant l’erreur de nom invalide
- scan local des noms du paquet, des ZIP et du TAR
