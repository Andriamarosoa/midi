# H27 — contrat et implémentation dormante engine/recomputer

## Portée

Ce lot a commencé par un contrat strictement documentaire. Après fermeture de
B1–B6 et autorisation externe séparée, il ajoute uniquement une capability
scientifique inémissible, l'engine dormant, le recomputer dormant indépendant
et leurs tests fail-before-capability. Il ne modifie ni les cinq blobs H27 déjà
scellés ni le loader/materializer dormant.

Le contrat lie le commit de clôture `44c2c33db4bc64c775bf1401812316d432905880`
et les cinq blobs H27 revus. Il conserve `H27_SYNTHETIC_V1`, les quatre rôles,
les quatre outcomes, les seuils H27 et les deux profils runtime préenregistrés.

## Frontières implémentées, non exécutables

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

L'engine et le recomputer lisent chacun les payloads scellés depuis leurs
chemins bornés, vérifient topologie, tailles, SHA, dtype, finitude et masque,
puis implémentent séparément la classification role-aware, Hann/rFFT, bandes,
NNLS fixe, certificats et décision. Le recomputer n'importe aucune fonction de
l'engine et ne reçoit ses résultats qu'au comparateur terminal, après sa propre
recomputation. NumPy reste injecté par le futur appelant et n'est pas importé au
chargement des modules.

La capability process-local n'a aucun constructeur, issuer, factory, registre
ou hook mutable d'autorisation. Son garde est un refus inconditionnel : forger
le type par `object.__new__` puis ajouter ou réassigner un faux registre de
module ne peut autoriser aucune frontière.

La revue de `0c2296d2` a aussi fermé le descriptor librement constructible. Les
deux implémentations exigent désormais un `H27SealedRecordBinding` nominal sans
constructeur ni loader dans ce lot. Son schéma fermé lie l'index de population
et son SHA, le SHA de la ligne canonique, l'identité, le chemin dérivé, la
topologie et les SHA payload, la présence de l'alternate, les coordonnées
causales, les pitches et les paramètres P2 `cents/B`. Son garde est lui aussi un
refus inconditionnel. Un futur loader d'index et son autorité devront donc être
introduits ensemble dans un commit séparément revu ; aucun caller ne peut
assembler les champs scientifiques dans ce lot.

Enfin, `engine_contract.result_field_order` et `result_schema` déclarent
exactement les 17 champs des deux dataclasses, y compris `mask_counts`,
`pitch_dilution_curve` et `maximum_sample_read`. Un test structurel exige
l'identité de l'ordre contractuel, des deux dataclasses et la couverture
exhaustive/disjointe du comparateur exact ou numérique.

## Interdictions conservées

Aucune capability émise, aucun runner, population, waveform, mask, FFT, NNLS,
P0/P1/P2, authority, claim, locked-test, entraînement ou calibration n'existe
ou n'est autorisé dans ce lot. L'existence du code dormant ne vaut aucune
autorité d'exécution.

## Vérification autorisée

Le parsing JSON, `py_compile`, les contrôles de blobs, les tests statiques et
les mocks d'échec avant capability sont autorisés. `19` tests H27
engine/recomputer/materializer réussissent en `2,893 s`, avec
`git diff --check`. Ils ne passent aucun objet scientifique valide aux kernels
et n'exécutent ni FFT ni NNLS.

## STOP

`H27_DORMANT_ENGINE_RECOMPUTER_IMPLEMENTED_PENDING_EXTERNAL_REVIEW_NO_MATERIALIZATION_NO_SCIENCE`

Une revue externe est obligatoire avant toute population, capability émissible
ou exécution scientifique.
