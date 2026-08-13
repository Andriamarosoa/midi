# H27 - contrat declaratif d'autorisation d'issuance reelle

La revue externe de `962e169e25acb11758a70e87ada78ab4004acad2`
conclut `PASS` sur le scellement administratif du module issuer effect-free.
Cette etape ajoute uniquement un contrat declaratif et son seal externe pour
les preconditions d'une future autorisation reelle one-shot.

Le contrat lie la chaine issuer PASS/scellee : module, seal du module, identity
binding et seal du binding, puis les 80 predecesseurs administratifs et
transitifs. Les 84 identites uniques sont rehashees dans le test.

Identites avant commit : contrat blob
`4a4d106ddcf9da4fffb1b81121fff51d9a781846`, `5277` octets, SHA-256
`970df939c83ac25397b13ca5399f2a9d62fc9f51b719b6e495aef7e727cc8c27` ;
seal blob `3b1b1f2cd91553f6b2d31df18d660d8052910aaa`, `1518` octets,
SHA-256
`3b91c4dd062889bdcf713b39dd72fa733ae5986014ca3735a35f9263828325fb`.

La destination canonique reste une donnee declarative. Le contrat exige pour
une future etape distincte un rehash complet avant consommation, une preuve
d'absence de destination, une autorite one-shot consommee juste avant la
premiere observation, une creation exclusive, publication atomique et un etat
terminal sans retry. Il ne fournit aucune autorite et n'invoque jamais
l'issuer.

Validation locale : `3/3` tests administratifs, `337/337` tests H27,
`py_compile` et `git diff --check` passent.

Aucune issuance, authority, claim, capability, destination, operation
filesystem, connexion, materializer, population ou science n'est creee ou
autorisee. `locked_test_used=false`; entrainement et calibration restent
interdits. Le contrat et son seal attendent une revue externe.
