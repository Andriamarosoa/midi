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
- la source normative de ces bindings : le contrat d'activation blob
  `2df0e536...` (11 131 octets, SHA-256 `a1e679e4...`) et son seal blob
  `0ef61aa7...` (3 122 octets, SHA-256 `21745703...`) ; runtime, environnement,
  cinq inputs, namespace, comptages et destinations doivent en etre derives
  exactement, sans override ;
- une claim durable `O_EXCL` créée et fsync avant NumPy ou accès scientifique ;
- une capability process-local single-use, non constructible/copiable/
  sérialisable, attestée hors de l'objet ;
- le refus des monkeypatches, rebinding de module/garde/publisher et appels
  directs aux helpers ;
- quatorze classes de tests adversariaux obligatoires ;
- aucun retry après claim.

Contrat corrige apres revue : blob Git
`e7ff1b71bdd62adf8341dbd824302f1eb57e69c6`, 7 358 octets, SHA-256
`da96c338d4a99e848ab5fa63d717442c3af27fab6268bb9abae99c1f76321dab`.

Le seal externe est acyclique et ne contient pas son propre SHA. Toute valeur
opérationnelle reste `false`; aucune population ou donnée locked-test n'a été
lue. Validation locale apres correctif : `py_compile`, `git diff --check` et
`46/46` tests H27 reussis. Prochaine action : revue externe du contrat et du
seal uniquement.
