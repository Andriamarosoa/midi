# H27 - identity binding de l'artefact d'autorite de creation du bundle

La revue externe de `f5f4b825b3103386ca3745c915beb20c05f78f0f`
conclut `PASS`. Ce lot lie uniquement l'artefact non consomme et son seal aux
126 identites amont, soit 128 paths uniques rehashes.

Les huit champs, l'identifiant canonique, le HEAD PASS, les six valeurs de
chaine, les trois valeurs de bundle, `single_use=true` et `consumed=false`
restent exacts.

Aucun bundle, observation, filesystem, registre, reservation, consommation,
invocation, destination, population ou science n'est ouvert.

Identites exactes :

- binding : `2c1d96a63ea76007f7ab3d59b044b5d38692b7af` / `3730` octets /
  `e39079c505b7a29b38d6fc1ba0dceede13ac5a23acdfcf182f84a4a129d8d5cb` ;
- seal : `47244bbd38147a3231f327e70a6dcde3f4343b40` / `1400` octets /
  `13ef586bf860984758ce030541a6fda7961bf37a93d27ab9cf3d2eb05609a9dc`.

Validation locale sans calcul scientifique : test cible `3/3`, suite H27
`412/412`, puis `git diff --check` propre avant commit.
