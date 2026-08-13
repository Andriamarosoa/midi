# H27 - implementation dormante du materialiseur activable

Ce lot implemente uniquement le futur module distinct demande apres la revue
`b8f6d904...`. Il ne cree aucun issuer, authority, activation, claim ou
capability utilisable et n'execute aucune donnee scientifique.

## Implementation

Le nouveau module est :

`src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py`

- blob Git apres hardening : `9bd10221dd620f5982e80edb215579245bb755a1` ;
- taille : `29 984` octets ;
- SHA-256 : `627f1993ee0c3f26624c72b32fea1ba524abe3058e47057cba58a7111bb82390`.

Les dix-huit fonctions de logique scientifique et de publication sont
mecaniquement identiques au module dormant revu `d3a903ac...`, a l'exception
du type nominal de capability. Les recettes, grilles, masks, ordre des 124
records, index et publication Darwin ne changent pas.

La frontiere ajoutee lie et revalide les octets exacts du contrat d'autorite,
de son seal, du contrat d'activation `2df0e536...` et de son seal
`0ef61aa7...`. Elle confirme les cinq inputs, le namespace, les comptages
`124/17/107` et les destinations fixes. Aucun override n'est expose.

La capability reste inconstructible, non copiable et non serialisable. Apres
revue adversariale, la barriere n'est plus un objet fonction Python mutable :
elle est un `mappingproxy.__getitem__` natif partiellement applique, sans
`__code__` modifiable. L'entree et les onze noms de helpers production pointent
sur cette meme barriere native et refusent avant tout argument, meme si les
anciens attributs de garde/publisher sont rebindes.
Un validateur administratif effectif compare aussi runtime, environnement,
HEAD/worktree, destinations et identite module/seal avant toute future claim.
L'identite future du module et son seal restent volontairement absents : le
module est donc non emissible et non activable.

## Validation

- `py_compile` : OK ;
- `git diff --check` : OK ;
- `62/62` tests H27 : OK ;
- seize tests nouveaux couvrent les quatorze familles adversariales, la
  derivation exacte des bindings et l'equivalence mecanique de la logique.

Etat final : aucun materializer invoque, aucune authority/capability/claim,
aucune population, aucun NumPy scientifique, aucun locked-test. Prochaine
action : revue externe de cette implementation dormante uniquement.
