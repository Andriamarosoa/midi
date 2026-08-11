# H26 - correction additive d'immutabilite profonde du lot dormant

Statut : `ADDITIVE_CORRECTION_PENDING_EXTERNAL_REVIEW`.

Le rejet externe de C1 a identifie une immutabilite seulement superficielle :
les cinq loaders C1, C4, C9, C13 et C18 retournaient un `MappingProxyType` au
niveau racine, mais la mapping `current_state` restait mutable.

## R1

Le commit `35f269e0b0abb75d23fb22750a95a724ff794d61` applique uniquement un gel
recursif des valeurs JSON dans ces cinq loaders. Les mappings deviennent des
`MappingProxyType`, les listes deviennent des tuples et les scalaires restent
inchanges. Les cinq tests verifient la mutation racine, la mutation imbriquee
et la conversion d'une liste.

Validation R1 : `14/14` tests dormants cibles, `py_compile` et
`git diff --check`.

Validation finale au tip R2 : `31/31` tests du lot, stack historique dans un
interpreteur frais `29/29`, autres tests H26 dans un second interpreteur frais
`162/162`, JSON R2 strict avec cinq bindings, sans cle dupliquee ni nombre
flottant, et `git diff --check`.

## Overlay R2

Le fichier
`configs/harmonic_censoring_h26_dormant_batch_deep_immutability_correction.json`
conserve les commits et blobs historiques, puis designe les blobs R1 comme
implementations effectives pour toute revue ou execution future. Cela ne
modifie pas le binding historique de C2 vers l'ancien blob C1; il est
explicitement supersede pour l'usage futur par cet overlay additif.

Aucun ancien commit, contrat JSON scelle, regle scientifique, lifecycle ou
failure n'a ete modifie. Aucune activation, observation runtime,
materialisation, population, P0/P1/P2, science ou locked-test n'a ete executee.

Prochaine action : revue externe de R1 puis R2, avant de reprendre C2.
