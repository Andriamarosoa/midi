# H27 - implementation dormante du materialiseur activable

Ce lot implemente uniquement le futur module distinct demande apres la revue
`b8f6d904...`. Il ne cree aucun issuer, authority, activation, claim ou
capability utilisable et n'execute aucune donnee scientifique.

## Implementation

Le nouveau module est :

`src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py`

- blob Git : `969c7f9a1c8830a2d91f94654a06a833c492c8f7` ;
- taille : `27 951` octets ;
- SHA-256 : `a273c975e72a324d60e3c6413141098a547ce905f2fdcedecfcbd5a3f7ff4a7a`.

Les dix-huit fonctions de logique scientifique et de publication sont
mecaniquement identiques au module dormant revu `d3a903ac...`, a l'exception
du type nominal de capability. Les recettes, grilles, masks, ordre des 124
records, index et publication Darwin ne changent pas.

La frontiere ajoutee lie et revalide les octets exacts du contrat d'autorite,
de son seal, du contrat d'activation `2df0e536...` et de son seal
`0ef61aa7...`. Elle confirme les cinq inputs, le namespace, les comptages
`124/17/107` et les destinations fixes. Aucun override n'est expose.

La capability reste inconstructible, non copiable et non serialisable. Le
garde et le publisher utilises par l'entree sont captures hors des attributs
de module modifiables; rebinder `_require_capability` ou `_publish` ne peut pas
deverrouiller l'entree. Les onze helpers production sont enveloppes par le
garde fige et refusent les appels directs avant tout acces a leurs arguments.
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
