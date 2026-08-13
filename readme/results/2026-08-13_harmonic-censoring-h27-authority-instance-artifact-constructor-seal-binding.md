# H27 - scellement du constructor d'artefact d'autorite effect-free

La revue externe de `6cbcf1c477770c0c5b05a6505146e20a0fcb137b`
conclut `PASS`. Ce lot ajoute uniquement le seal externe du module effect-free,
son identity binding administratif et le binding seal. Le module PASS et son
seal sont lies a 100 predecesseurs, soit 102 chemins uniques rehashes.

Aucune invocation, reservation, observation ou ecriture n'a lieu. Aucun
artefact ni instance reel n'existe; les huit edges restent fermes.

Identites exactes : module seal blob
`b838d6bb0ec7b3dd9671e7bd2b52a3af6453a2b5`, `1458` octets, SHA-256
`5a1fcd1ee6ff8d1eb4045707f80faf79323a2ebf524b92ca6f519e896b2b331f` ;
binding blob `628b9f5b358a153f06488282f7598ecb533d4996`, `3701` octets,
SHA-256 `5e5b4bd450eb2ada326a200acdf63ce645114303e4792daa03f62b2b5d937511` ;
binding seal blob `5e1566c809b05a9225ec2a6c50f7fc9f63672353`, `1787` octets,
SHA-256 `389d0bfc047451de746322af51ee10a95322c4d480a3486bfab3e5c66199d23f`.

Validation locale : `3/3` tests administratifs et `370/370` tests H27.
