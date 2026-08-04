# Anomalie de lancement du smoke d'alignement

## Faits vérifiés

- Job Mac CPU : `independent-note-alignment-smoke-cpu-20260804`.
- Commit : `8c9fc4f9d6fdd38d016de1be082779856e4980bd`.
- Code de sortie : `1`; aucun processus actif ensuite.
- Erreur exacte : le garde du smoke impose `8192` exemples fit, `2048` dev et
  `4096` calibration; la tentative réduite `1024 / 256 / 512` est refusée
  avant entraînement.
- Aucun poids, rapport expérimental, export, live ou test verrouillé produit.

## Interprétation

Il s'agit d'un garde de protocole, pas d'une métrique négative ni d'un échec
du contrat fréquentiel. Le smoke reste borné mais ses tailles sont fixes pour
garantir une couverture corpus et une calibration comparables.

## Action bloquée

Aucune relance automatique. La prochaine commande devra employer les tailles
exigées par le garde, après revue explicite de cette anomalie.
