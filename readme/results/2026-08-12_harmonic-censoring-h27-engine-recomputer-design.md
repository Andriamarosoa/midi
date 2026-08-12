# H27 — contrat de conception engine/recomputer dormant

## Portée

Ce lot est strictement contractuel. Il ajoute
`configs/harmonic_censoring_h27_engine_recomputer_contract.json` et ne modifie
ni les cinq blobs H27 déjà scellés, ni le loader/materializer dormant, ni un
fichier Python de science.

Le contrat lie le commit de clôture `44c2c33db4bc64c775bf1401812316d432905880`
et les cinq blobs H27 revus. Il conserve `H27_SYNTHETIC_V1`, les quatre rôles,
les quatre outcomes, les seuils H27 et les deux profils runtime préenregistrés.

## Frontières définies, non implémentées

Il définit un futur record (waveform `<f8`, masque role-major de 66 560 octets,
métadonnées, tailles, SHA et containment) et impose l’ordre : bindings puis
identité/bytes/mask/support, puis seulement classification role-aware, puis
éventuellement FFT/NNLS/certificats dans une phase future.

Le silence exact entièrement supporté n’est valide que pour `previous_short`
et `previous_long`. Un `current_*` nul ou sous le plancher est rejeté avant le
calcul scientifique. Le recomputer devra effectuer sa propre recomputation sans
arrays, caches, certificats, décision ou fonction scientifique interne de
l’engine ; tout mismatch est terminal.

## Interdictions conservées

Aucun engine, recomputer, stub scientifique, capability, runner, population,
waveform, mask, FFT, NNLS, P0/P1/P2, authority, claim, locked-test,
entraînement ou calibration n’existe ou n’est autorisé dans ce lot.

## Vérification autorisée

Seul le parsing JSON et la cohérence déclarative ont été exécutés : schéma,
identité, cinq bindings, enums, rôles, outcomes et flags à `false`.

## STOP

`H27_DORMANT_ENGINE_RECOMPUTER_DESIGN_CONTRACTED_PENDING_EXTERNAL_REVIEW_NO_IMPLEMENTATION_NO_MATERIALIZATION_NO_SCIENCE`

Une revue externe est obligatoire avant toute implémentation Python dormante.
