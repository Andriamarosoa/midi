# H27 — contrat de frontière d'autorité du futur matérialiseur activable

Le lot est exclusivement contractuel. Il ne crée aucun module activable,
issuer, authority, capability, claim, activation, population ou calcul.

Le contrat fixe :

- le blob dormant revu `d3a903ac…` comme logique scientifique immuable et
  jamais cible d'activation ;
- un futur module distinct, actuellement `exists=false` et
  `implementation_authorized=false` ;
- comme seule différence autorisée, le plumbing de frontière d'autorité ;
- les bindings exacts activation, authority, runtime, Git, cinq inputs H27,
  destinations et blob/seal futur ;
- une claim durable `O_EXCL` créée et fsync avant NumPy ou accès scientifique ;
- une capability process-local single-use, non constructible/copiable/
  sérialisable, attestée hors de l'objet ;
- le refus des monkeypatches, rebinding de module/garde/publisher et appels
  directs aux helpers ;
- quatorze classes de tests adversariaux obligatoires ;
- aucun retry après claim.

Contrat proposé : blob Git `5b44b716d44c3313f99fd773f07c70649a981482`,
5 958 octets, SHA-256
`830050fc580a7957336d3cdb7aa41a49a7e069df5da55366b41b007e3678cc01`.

Le seal externe est acyclique et ne contient pas son propre SHA. Toute valeur
opérationnelle reste `false`; aucune population ou donnée locked-test n'a été
lue. Prochaine action : revue externe du contrat et du seal uniquement.
