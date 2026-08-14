# H27 - contrat du futur creator revu du control bundle

La revue externe de `817f4c8ab2d51674d17eef968a907e519ac2cccf`
conclut `PASS`. Ce lot definit uniquement le contrat du futur creator one-shot.
Il lie l'artefact d'autorite, son seal, son binding et son binding seal aux 126
identites amont hors artefact et seal deja presents, soit 130 identites uniques
a rehasher avant le registre.

Dix controles statiques precedent toute ouverture du registre. La reservation
unique est le premier effet irreversible, la consommation atomique precede
toute observation du bundle, puis les treize etapes exactes sont executees une
seule fois. Tout echec apres reservation est terminal et interdit le retry.

Aucune implementation, ouverture de registre, reservation, consommation,
observation/creation de bundle, operation filesystem ou science n'est ouverte.

La premiere revue de `b9bb9ea725a9faaf224a5f40989ee29f70253e4e`
a conclu `FAIL` uniquement sur le schema byte-exact des records JSONL et la
source d'implementation implicite. La micro-correction definit onze champs,
onze regles de transition et une racine de controle distincte exacte.

Identites exactes apres micro-correction :

- contrat : `cee37fbececa8387266ba693ae915aeb8ce3ac4e` / `9920` octets /
  `8decca47ec6947951fddfb8becdaa550609fa50e2c12e310d7a4476210f583da` ;
- seal : `530e2f57c371165303846402392f09223b9ff43b` / `1283` octets /
  `b883b10ddc5757dc790aa250e43c377fdc1711e25ca22b2b1c64a3c8e697cf20`.

La verification a corrige avant commit le comptage transitive : les quatre
racines incluent deja artefact + seal, donc `4 + 126 = 130` paths uniques.
Validation locale : test cible `3/3`, suite H27 `415/415`, puis
`git diff --check` propre avant commit.
