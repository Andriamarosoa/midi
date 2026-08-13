# H27 — seal de revue du matérialiseur de production dormant

## Décision source

La revue externe du correctif `4a0fcadcfd82530212a7f9bc381cb678ff275bb2`
conclut `PASS`. Elle confirme que les onze helpers capables de synthétiser ou
publier passent tous par le refus inconditionnel, et que l'ordre futur de
publication est bien :

```text
write payload
→ reopen filesystem bytes
→ verify actual size and SHA-256
→ write population_index.json last
→ full post-index rehash
→ atomic no-replace publish
```

## Seal externe acyclique

Le nouveau fichier :

```text
configs/harmonic_censoring_h27_production_materializer_dormant_external_review_seal.json
Git blob ac2cdc907da3dc2de3ff3f60973f973fcb217ea9
2 318 octets
SHA-256 0d9730c78aa487a0d326d27a975ec0fe7f8b9566dc1900dec1092bc53c4cf3c2
```

lie exactement :

```text
implementation blob d3a903acfa67daf822d50aab005b88943a8c18fa
implementation SHA-256 1d4b0b651c2c916a1a1bcd71578aa263074290c90fd381be867b77ef46cc0a25
reviewed commit 4a0fcadcfd82530212a7f9bc381cb678ff275bb2
historical reference blob 394f25a51f854cf629ef184694c4dcf1a45904b8
```

Le seal ne contient ni son propre SHA ni un état activable. Il conserve
`activation_execution_target=false` et
`must_remain_unconditionally_refusing=true`.

## Contrat d'activation rebondi

Le contrat rebondi est :

```text
configs/harmonic_censoring_h27_materialization_activation_contract.json
Git blob 2df0e53637cc31d97c01e75b88cb47c2e866c187
11 131 octets
SHA-256 a1e679e4357552bd88640d3d67a6f17bd9feaad38e8f26e4ed68539f167980c4
```

Son seal externe rebondi est :

```text
configs/harmonic_censoring_h27_materialization_activation_contract_external_seal.json
Git blob 0ef61aa7ada69b619a8e7acd7138151a36496089
3 122 octets
SHA-256 2174570372df3e8349a425d62ce8e1d084238757fb944968ad8539d9dcabac9d
```

Le contrat possède désormais deux objets non confondus :

1. `reviewed_dormant_production_implementation`, existant et review-sealed,
   mais jamais cible d'activation ;
2. `future_production_materializer`, défini comme futur matérialiseur
   activation-capable distinct, actuellement absent, non implémenté, non
   autorisé et sans path/blob/SHA/seal.

Toute future issuance reste tenue d'échouer avant claim tant que le second
objet et son futur seal séparé n'existent pas.

## Validation et état terminal

Les tests vérifient les octets réels du module, du nouveau seal et du contrat,
leurs tailles et empreintes, ainsi que les états non activables. Les suites H27
restent administratives/fail-closed ; aucune fonction de synthèse n'est appelée.

```text
reviewed dormant implementation exists        true
review seal exists                            true
activation execution target                   false
future activation-capable implementation      absent
activation / authority / capability / claim   absent
population / index / payload read              absent
FFT / NNLS / engine / recomputer               non exécutés
P0 / P1 / P2                                  non exécutés
locked-test                                   non utilisé
training / calibration                        non exécutés
```

Prochaine action unique : revue externe de ce seal et du contrat rebondi.
L'implémentation d'une frontière activation-capable reste explicitement hors
portée jusqu'à une autorisation ultérieure.
