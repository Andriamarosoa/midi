# Organisation des données

Le dossier `data` sépare strictement les sources externes des résultats
reproductibles générés par le projet.

## Sources brutes

Ces dossiers sont des entrées et ne doivent jamais recevoir de fichiers
générés :

- `data/GuitarSet`
- `data/GAPS`
- `data/Guitar-TECHS`
- `data/IDMT-SMT-Guitar`

Leurs README, licences et archives restent dans leurs dossiers d'origine.

## Sorties de traitement

Toutes les sorties de préparation ou d'analyse audio doivent être écrites sous
`data/processed` :

- datasets NPZ et manifests ;
- labels et features harmoniques dérivés ;
- rapports de validation des datasets ;
- fichiers audio diagnostiques intermédiaires.

Les chemins par défaut du code et des configurations suivent désormais ce
contrat. Le contenu généré de `data/processed` est ignoré par Git ; seul le
dossier vide est conservé. Après une suppression, les données dérivées doivent
être reconstruites à partir des quatre sources brutes ci-dessus.

Les modèles, checkpoints et rapports d'expériences ne sont pas des données
prétraitées : ils restent respectivement dans `artifacts/` et `runs/`.

## Reconstruction V2.2

Depuis la racine du projet :

```powershell
.\.venv\Scripts\python.exe scripts\data\rebuild_processed.py --workers 4
```

La commande est reprenable. Elle extrait seulement les sources nécessaires,
recrée les 360 CSV harmoniques GuitarSet, reconstruit GuitarSet, GAPS et
Guitar-TECHS, puis produit et valide
`data/processed/polyphonic_v2_2_combined/manifest.csv`.
