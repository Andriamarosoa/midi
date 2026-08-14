# H27 - identity binding du contrat de source immutable du creator

La revue externe de `53607b623858b18064c23ab0a9772d4c36b48b90`
conclut `PASS`. Ce lot lie uniquement le contrat de source immutable, son seal
et les 134 identites amont, soit 136 paths uniques rehashes.

La racine finale/staging, les deux fichiers fermes, le manifest canonique, les
sept controles statiques, neuf etapes de publication et douze regles
fail-closed sont preserves. Aucune source n'est creee ou observee. Aucun
filesystem, registre, reservation, consommation, bundle, invocation ou science
n'est ouvert.

Identites exactes :

- binding : `9da5ef4409ac4e11c6941eb297dfa329f16ea78d` / `3751` octets /
  `4fe12fc45dcea22a7f9c9fe5886342c7ed9e5604d35adeaa775aca61615dd28c` ;
- seal : `49de9d84e93282fd7b11889fdbbae6b9b11401e3` / `1423` octets /
  `95a2e8619bb01b8ec2e8e37b6c38a1b962d05bc02380d7dbdffd4e949f8b807d`.

Validation locale sans calcul scientifique : test cible `3/3`, suite H27
`424/424`, puis `git diff --check` propre avant commit.
