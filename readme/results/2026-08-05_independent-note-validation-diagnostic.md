# Diagnostic validation-only de la garde `independent_note`

Date de fin : 2026-08-05T04:26:18Z. ExÃ©cution Mac M4 CPU,
commit `18db2bd7bc4968bd38b5a08edb44ea0f5ad5efe1`, 12 enregistrements du split
`validation`, aucun entraÃ®nement et aucun export. Le rapport brut est local,
sous `tmp/local/mac_results/independent-note-validation-20260805/reports/`.

Le checkpoint `independent_note_head.keras` transmet correctement la sortie
neurale au dÃ©codeur. Avec le seuil configurÃ© `0,01`, 709 candidats ont eu un
support harmonique suffisant pour Ãªtre soumis Ã  la garde, mais aucun n'a Ã©tÃ©
rejetÃ©. Leur probabilitÃ© minimale Ã©tait `0,48080769`, leur maximum
`0,99987316` et leur moyenne `0,96801894`.

Les Ã©vÃ©nements restent donc identiques au baseline : 858 appariements sur
3 639 rÃ©fÃ©rences, 3 389 faux NoteOn, 2 781 notes manquÃ©es, 160 retriggers et
F1 onset `0,21760081`. Cela invalide le seuil `0,01` hors de sa calibration
train-only, mais ne prouve pas encore qu'un seuil plus Ã©levÃ© est acceptable.

Suite autorisÃ©e : grille sÃ©quentielle CPU validation-only aux seuils fixes
`0,50`, `0,60`, `0,70`, `0,80`, `0,90`, comparÃ©e au baseline appariÃ©. Aucun
seuil ne peut Ãªtre promu si rappel/F1 rÃ©gressent, en particulier sur
Guitar-TECHS. Le test verrouillÃ© reste exclu.
