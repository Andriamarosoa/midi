# H26 - correction fake-only du runner scientifique dormant

Le pilote externe a rejete C19 avec le verdict
`REJECTED_H26_C19_DORMANT_SCIENTIFIC_RUNNER_ARBITRARY_CALLABLE_EXECUTION_BOUNDARY`.
Le runner historique acceptait trois `Callable` arbitraires et ne pouvait donc
pas garantir honnetement l'absence de science reelle ou de locked-test.

R15 `2062affefa6096e2969e8ba8b76b3683c41e0064` remplace cette interface par
`H26FakeOnlySequence`, un objet de donnees inerte contenant uniquement une
identite `fake:`. La demonstration P0/P1/P2 est fixe et interne au module. Aucun
callback ni autre charge executable n'est accepte. Un objet callable arbitraire
est rejete avant son premier appel.

R16 lie C19 historique (blob `4382deb8...`) au runner effectif R15 (blob
`222b8acc...`) sans modifier le contrat scientifique C16, son seal C17, le
loader strict R13/R14 ou les regles P0/P1/P2. Aucun calcul scientifique,
population reelle, modele, entrainement, calibration ou locked-test n'a ete
execute.

Statut : `ADDITIVE_DORMANT_CORRECTION_PENDING_EXTERNAL_REVIEW`.
