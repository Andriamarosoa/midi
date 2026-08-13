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

Il conserve exactement les payloads scellés du futur record : waveform `<f8`,
masque role-major de 66 560 octets et alternate `<f8` uniquement pour les
collisions. Le descriptor d'invocation reste en mémoire et n'ajoute aucun
`metadata.json`. L'ordre est : intégrité et support, exact-zero sur les samples,
puis FFT et plancher spectral pour les seules vues non nulles, puis seulement
bands/NNLS/certificats dans une phase future.

Le silence exact entièrement supporté n’est valide que pour `previous_short`
et `previous_long`. Un `current_*` exact-zero résout tôt vers `AMBIGUOUS`; une
vue non nulle sous le plancher ne peut être reconnue qu'après FFT, puis résout
elle aussi vers `AMBIGUOUS` sans atteindre bands/NNLS/certificats. Une entrée
corrompue reste une erreur terminale distincte. Le recomputer devra effectuer sa propre recomputation sans
arrays, caches, certificats, décision ou fonction scientifique interne de
l’engine ; tout mismatch est terminal.

Le contrat recopie désormais de façon autonome Hann, zéro-padding, rFFT,
puissance, bandes triangulaires à 35 cents, grille MIDI 24..96, base harmonique,
512 sweeps NNLS, résidus, onset, persistence et timbre borné à 0,8. Il ferme
aussi les champs d'entrée autorisés, les douze entrées oracle interdites et
leurs aliases, ainsi que les identités complètes des deux runtimes et leur
environnement exact.

La fermeture B6 scelle aussi explicitement l'exécutable primaire CPython 3.11.9
résolu sous `/Library/Frameworks/Python.framework/Versions/3.11/bin/python3.11` :
152 624 octets, SHA-256
`4e28e811a89aeac6eed668ae641c7f85f5831e42e8dc6cd9a85a3bcc032ec46a`.
Le profil primaire possède donc les mêmes champs chemin/taille/SHA que le
profil secondaire ; aucune sélection ou substitution runtime automatique
n'est permise.

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
