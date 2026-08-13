# H27 - implementation dormante du materialiseur activable

Ce lot implemente uniquement le futur module distinct demande apres la revue
`b8f6d904...`. Il ne cree aucun issuer, authority, activation, claim ou
capability utilisable et n'execute aucune donnee scientifique.

## Implementation

Le nouveau module est :

`src/polyphonic/harmonic_censoring_h27_activation_capable_production_materializer_dormant.py`

- blob Git apres hardening : `791514b32fa603ac59f0d59b48ee4feee936e804` ;
- taille : `32 243` octets ;
- SHA-256 : `bf8027ffc9473db40a44f60ddb65433fdc8a6151351b1bc78017a192480e5330`.

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
elle est le bound method natif `().__getitem__`, sans import de constructeur et
sans `__code__` modifiable. L'entree et les onze noms de helpers production pointent
sur cette meme barriere native et refusent avant tout argument, meme si les
anciens attributs de garde/publisher sont rebindes.
Un validateur administratif effectif compare aussi runtime complet (Python,
executable, NumPy, multiarray et OpenBLAS), environnement, HEAD/worktree,
claim/staging/final et identite module/seal avant toute future claim. Une
attestation runtime exige que le module charge, l'entree et les onze helpers
pointent exactement sur la barriere native attendue; fake module et rebinding
de callable critique sont testes.
L'identite future du module et son seal restent volontairement absents : le
module est donc non emissible et non activable.

## Validation

- `py_compile` : OK ;
- `git diff --check` : OK ;
- `64/64` tests H27 : OK ;
- dix-huit tests nouveaux couvrent les familles adversariales exercables sans
  issuer/claim, la derivation exacte des bindings et l'equivalence mecanique.
  Les familles claim/fsync/consommation/post-claim restent explicitement
  differees jusqu'a une portee issuer/claim separement autorisee; aucun claim
  factice n'est cree dans ce lot.

Etat final : aucun materializer invoque, aucune authority/capability/claim,
aucune population, aucun NumPy scientifique, aucun locked-test. Prochaine
action : revue externe de cette implementation dormante uniquement.
