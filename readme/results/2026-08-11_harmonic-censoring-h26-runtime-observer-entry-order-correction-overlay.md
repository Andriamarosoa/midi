# H26 - overlay correctif de l'ordre observer-entry

Statut : `ADDITIVE_DORMANT_CORRECTION_PENDING_EXTERNAL_REVIEW`.

Cet overlay R7 clot le correctif autorise apres le rejet de C7. Il conserve
C7, C8, C9, le correctif d'immutabilite R1 sur C9 et C10 comme artefacts
historiques. Il designe comme effectifs :

- R3 `01c3220f22974ebe8aa0cd3d49116a1d919dc26c` : contrat d'ordre corrige ;
- R4 `201fcbffadd8a4c3c3bfceaa9d821229cddb3ac6` : seal externe de R3 ;
- R5 `23889bc9480a6dd985d4fed56ab9b3d54528f98a` : loader deep-frozen historique,
  rejete car il acceptait encore les constantes non-JSON ;
- R9 `f208eba5fb054cff90ea3f1c5aca69f30d789cd4` : loader effectif strict qui
  rejette aussi `NaN`, `Infinity` et `-Infinity` ;
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

Correction additive R8 : le commit R7
`5906b3ebe0a8c7ee2fb95382c8b0382d44ee906f` developpait incorrectement le
prefixe R5. Le SHA complet ci-dessus est celui verifie par `git rev-parse`.
Aucun code ni binding de blob n'a change.

Correction additive R9/R10 : R9 ajoute uniquement `parse_constant` fail-closed
et trois cas de test. R10 conserve R5 comme provenance historique et designe
le blob loader R9 `8f8f603b2330b5684aa1c64cc50d41ccacf2eaba` comme effectif.
