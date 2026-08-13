# H27 - binding du contrat de l'autorite reelle one-shot

La revue externe de `9dcd506e95c74f03c0efe4a7e8117bbf7b841d86`
conclut `PASS` sur le contrat declaratif de la future autorite d'execution
reelle one-shot et son seal. Cette etape ajoute uniquement leur identity
binding administratif et le seal externe du binding.

Le binding lie le contrat PASS, son seal et ses 88 predecesseurs : 90 chemins
uniques sont recomposes et rehashes. Il preserve exactement le caractere
single-use, l'ordre `rehash 88 -> consume -> observe absence ->
create-exclusive`, la terminalite du succes et de l'echec post-consommation,
ainsi que l'interdiction de retry.

Aucune instance d'autorite n'est creee, accordee ou consommee. Aucun issuer
n'est invoque; aucune destination n'est observee et aucune operation filesystem,
materializer, population ou science n'est autorisee. Les huit edges historiques
restent fermes. `locked_test_used=false`; entrainement et calibration restent
interdits.

Identites avant commit : binding blob
`41bb902d99379c0a518181e97056b4232abbc143`, `3369` octets, SHA-256
`400a1010c4be36cbec585de0399137abca8b0b61f218946498d19fad23739e55` ;
seal blob `0b844d82a91ee25c2bd3a883ed2c52d33bf9f23c`, `1474` octets,
SHA-256
`fc171b26ce58f8a93c643ae5f430c572a247f37e2efab4313a394a3653b0ea99`.

Validation locale : `3/3` tests administratifs, `346/346` tests H27,
`py_compile` et `git diff --check` passent.
