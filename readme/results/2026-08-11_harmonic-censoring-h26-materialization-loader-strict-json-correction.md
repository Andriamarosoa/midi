# H26 - correction strict JSON du loader de materialisation

Le pilote a approuve la chaine runtime corrigee et C11/C12, puis rejete C13
avec le verdict
`REJECTED_H26_C13_MATERIALIZATION_SEAL_LOADER_NON_STRICT_JSON_PARSING`.

R11 `cbede10ed3925df09d1f8622eaa325ee37699621` modifie uniquement le loader
C13 et son test. Le parseur refuse maintenant les cles dupliquees, tout nombre
flottant et les constantes non-JSON `NaN`, `Infinity` et `-Infinity`. Il exige
aussi un objet JSON racine.

C13 historique et son blob `7b3f46cd...` restent la provenance initiale. La
correction d'immutabilite R1 et son blob `7a22bb7b...` restent historiques. Le
blob loader effectif R11 est
`86a5283036bf8b65b85eec55eb968bdca8a57835`.

R12 enregistre ces bindings dans un overlay additif. Aucun binding C12,
deep-freeze, comportement de materialisation, runtime, science ou locked-test
n'a change ou ete execute.

Prochaine action : revue R11/R12, puis reprise a C14 en cas d'approbation.
