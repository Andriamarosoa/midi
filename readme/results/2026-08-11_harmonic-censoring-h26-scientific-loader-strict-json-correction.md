# H26 - correction strict JSON du loader scientifique

Le pilote a approuve C14 a C17, puis rejete C18 avec le verdict
`REJECTED_H26_C18_SCIENTIFIC_SEAL_LOADER_NON_STRICT_JSON_PARSING`.

R13 `41995848f68d5e31ea38d78181b0c51d452f666c` modifie uniquement le loader
scientifique C18 et son test. Le meme parseur fail-closed est employe pour le
seal et le contrat : rejet des cles dupliquees, de tout float, de `NaN`,
`Infinity`, `-Infinity`, et racine obligatoirement objet JSON.

C18 historique et son blob `0728b24a...` restent provenance. R1-C18 et son
blob deep-freeze `81fc7819...` restent historiques. Le blob loader effectif
R13 est `d2dae5004e30343172040c08ab76bb7bb88ba2f9`.

R14 enregistre ces bindings sans changer le contrat C16, le seal C17, le
deep-freeze, les regles scientifiques ou les etats dormants. Aucun P0/P1/P2,
science reelle ou locked-test n'a ete execute.

Prochaine action : revue R13/R14, puis reprise a C19 en cas d'approbation.
