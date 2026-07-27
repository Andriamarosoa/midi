# Run invalide — ne pas sélectionner

Ce run a été arrêté après l'époque 1.

La première implémentation de la tête `onset` partageait les features masquées
du modèle principal. Dans le dataset V6.0, `onset=1` coïncide avec
`visible_window=512`; le modèle pouvait donc apprendre la taille du masque au
lieu de l'attaque audio. Le `val_onset_auc_pr` artificiel de 99,99 % a révélé
cette fuite.

Les checkpoints de ce dossier ne doivent pas être utilisés. La correction
V6.2 isole la tête onset sur les 512 derniers échantillons audio et ne lui
donne pas accès à `time_mask`.
