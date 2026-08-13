# H27 - contrat declaratif d'autorisation d'issuance reelle

La revue externe de `962e169e25acb11758a70e87ada78ab4004acad2`
conclut `PASS` sur le scellement administratif du module issuer effect-free.
Cette etape ajoute uniquement un contrat declaratif et son seal externe pour
les preconditions d'une future autorisation reelle one-shot.

Le contrat lie la chaine issuer PASS/scellee : module, seal du module, identity
binding et seal du binding, puis les 80 predecesseurs administratifs et
transitifs. Les 84 identites uniques sont rehashees dans le test.

L'identite initiale du contrat refuse etait blob `4a4d106d...`, `5277`
octets, SHA-256 `970df939...`. L'identite corrigee avant commit est blob
`b7bc9462aee81c0ee985bbfd0f1df54092b4d9af`, `5571` octets, SHA-256
`b838875140762ee795700f155ea46e35e576d2db81f3e64b48a00b6c006d4f66`.
Le seal corrige est blob `24f6858a499afb5088fe25e064a5559934210cbf`,
`1518` octets, SHA-256
`e39f4d755df9378cfde4a872238a6e25b7256901aa7d742ad175f7f7f766f3a6`.

La premiere revue conclut `FAIL` sur un ordre contradictoire qui demandait une
preuve d'absence avant consommation tout en interdisant toute observation avant
consommation. La correction fixe l'ordre normatif unique : rehash complet,
consommation one-shot, premiere observation qui sonde l'absence, puis creation
exclusive sans overwrite. La destination canonique reste une donnee
declarative; publication atomique et etat terminal sans retry restent requis.
Le contrat ne fournit aucune autorite et n'invoque jamais l'issuer.

Validation locale : `3/3` tests administratifs, `337/337` tests H27,
`py_compile` et `git diff --check` passent.

Aucune issuance, authority, claim, capability, destination, operation
filesystem, connexion, materializer, population ou science n'est creee ou
autorisee. `locked_test_used=false`; entrainement et calibration restent
interdits. Le contrat et son seal attendent une revue externe.
