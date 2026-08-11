# H26 - runner scientifique dormant

Statut historique C19 :
`REJECTED_H26_C19_DORMANT_SCIENTIFIC_RUNNER_ARBITRARY_CALLABLE_EXECUTION_BOUNDARY`.

Le correctif additif R15 remplace les trois callbacks injectables par une entree
structurelle `H26FakeOnlySequence`. Elle contient uniquement une identite
`fake:` et ne peut transporter aucun code executable. Le runner execute une
demonstration P0/P1/P2 interne et fixe. Un callable arbitraire est rejete avant
son premier appel; les indicateurs `real_science_executed=false` et
`locked_test_used=false` sont donc garantis par construction.

Aucun moteur, recomputer, population reelle, P0/P1/P2 scientifique ou
locked-test n'est importe, lu ou execute. Statut R15 :
`ADDITIVE_DORMANT_CORRECTION_PENDING_EXTERNAL_REVIEW`.
