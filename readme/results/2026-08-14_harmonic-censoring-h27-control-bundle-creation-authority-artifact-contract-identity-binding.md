# H27 - identity binding du contrat d'artefact d'autorite de creation du bundle

La revue externe de `2f078c1bdc0ca57559c6ff803f2847cf7b68fb68`
conclut `PASS`. Ce lot lie uniquement le contrat corrige et son seal exacts aux
124 identites qu'ils referencent, soit 126 paths uniques rehashes.

Le schema futur reste strictement preserve : huit champs, identifiant derive
de sept champs canoniques, HEAD futur explicitement revu et scelle, six valeurs
exactes de chaine, trois valeurs exactes de bundle, single-use et terminalite.

Aucun artefact reel, bundle, observation, filesystem, registre, reservation,
consommation, invocation ou science n'est ouvert.

Identites exactes :

- binding : `30c076544f7a17a7c51232de446e407aaaf0227c` / `4229` octets /
  `d4b76a2a969c7ff37677b7f6bdaa97ae70f45a51e7262b475666775756d49d4f` ;
- seal : `8cf638d41d84a15f79dd449e321c67f1a2f8bab1` / `1455` octets /
  `f0c31cee3c8cdede10c209c5553d588bed3fd9b908179175063f466d899dd110`.

Validation locale sans calcul scientifique : test cible `3/3`, suite H27
`406/406`, puis `git diff --check` propre avant commit.
