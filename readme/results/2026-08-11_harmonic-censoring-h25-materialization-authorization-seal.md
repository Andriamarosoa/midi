# H25 — seal d’autorisation de matérialisation

Le seal H25 est désormais un artefact Git revuable de dix champs, sans
`activation_commit` auto-référentiel. Il lie l’autorité revue au commit
`52337716cb80ed3e3937da7ca17575b357e77298`, son blob
`d58351b6fd363f1d843c7c43501eb0ecf49e57df`, le contrat authority brut, le
materializer approuvé et les cinq entrées scellées.

Octets du seal : `1173`; SHA-256 brut :
`1485998da12bfb775f2c8bc94bcaf971d52d8ed99d582f812458d0c190ec44d8`.

Cette étape ne positionne ni le SHA externe du seal ni le commit d’activation
dans l’environnement. Aucune authority/capability n’est émise ou consommée et
aucune population, waveform, donnée réelle, phase P0/P1/P2 ou locked-test n’est
utilisée. Le seal doit être relu avant toute activation OS séparée.
