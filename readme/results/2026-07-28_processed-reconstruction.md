# Résultat — reconstruction de `data/processed`

> Date : 2026-07-28
> Statut : réussi
> Branche de documentation : `codex/cleanup-cloud-training-docs`

## Objectif

Reconstruire toutes les données dérivées à partir des sources brutes
conservées dans :

- `data/GuitarSet`
- `data/GAPS`
- `data/Guitar-TECHS`
- `data/IDMT-SMT-Guitar`

Le script reproductible est `scripts/data/rebuild_processed.py`. Les prochains
traitements lourds et entraînements seront exécutés sur Kaggle ou Colab ; le
poste local reste destiné au live et aux tests légers.

## Commande

```bash
python scripts/data/rebuild_processed.py --workers 4
```

Le script extrait les archives nécessaires, produit les CSV harmoniques
GuitarSet, reconstruit les datasets polyphoniques, combine leurs manifests et
vérifie l’isolation des groupes.

## Résultats

| Élément | Résultat |
|---|---:|
| Taille de `data/processed` | 8,06 Go |
| Enregistrements combinés | 868 |
| Enregistrements train | 572 |
| Enregistrements validation | 182 |
| Enregistrements test verrouillé | 114 |
| Frames train | 12 343 995 |
| Frames validation | 4 501 083 |
| Frames test | 1 577 786 |
| Notes train | 284 023 |
| Notes validation | 58 071 |
| Notes test | 37 641 |
| Notes avec supervision harmonique | 62 476 |
| Fuites de groupes entre splits | 0 |

Répartition des 868 enregistrements :

- GuitarSet : 360 ;
- GAPS : 300 ;
- Guitar-TECHS direct : 104 ;
- Guitar-TECHS micro + ampli : 104.

## Décisions et limites

- Toutes les sorties audio et labels dérivés restent sous `data/processed`.
- IDMT-SMT-Guitar est conservé comme source brute et outil de diagnostic, mais
  n’entre pas dans le manifest combiné de cet entraînement.
- Le contenu généré de `data/processed` n’est pas versionné dans Git.
- Le jeu de test n’a servi ni à la reconstruction des seuils ni au choix du
  modèle.

## Preuves

- `data/processed/rebuild_report.json`
- `data/processed/polyphonic_v2_2_combined/manifest.csv`
- `data/processed/polyphonic_v2_2_combined/validation_report.json`
