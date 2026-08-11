# H26 - overlay correctif de l'ordre observer-entry

Statut : `ADDITIVE_DORMANT_CORRECTION_PENDING_EXTERNAL_REVIEW`.

Cet overlay R7 clot le correctif autorise apres le rejet de C7. Il conserve
C7, C8, C9, le correctif d'immutabilite R1 sur C9 et C10 comme artefacts
historiques. Il designe comme effectifs :

- R3 `01c3220f22974ebe8aa0cd3d49116a1d919dc26c` : contrat d'ordre corrige ;
- R4 `201fcbffadd8a4c3c3bfceaa9d821229cddb3ac6` : seal externe de R3 ;
- R5 `23889bc381a689328b4d7104ace45cf19313aafe` : loader strict et deep-frozen ;
- R6 `4552f38fcc9e91f7fd880649d4e595e5030f8452` : orchestrateur injecte corrige.

L'ordre futur effectif cree l'evidence a l'interieur de la boundary observer,
la valide avant l'unique tentative d'observation, puis valide le receipt. Les
arguments d'evidence preconstruite ont ete retires. Les tests restent factices,
injectes et en memoire.

Aucun ancien commit n'a ete reecrit. Aucun observateur reel, filesystem
runtime, NumPy, BLAS, `otool`, materializer, population, P0/P1/P2, science ou
locked-test n'a ete utilise.

Prochaine action : revue externe sequentielle R3 a R7, puis reprise a C8 si
l'overlay est approuve.
