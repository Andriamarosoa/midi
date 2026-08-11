# H26 — loader dormant du seal externe d'autorité de matérialisation

Date : 2026-08-11

## Portée autorisée

```text
AUTHORIZED_TO_IMPLEMENT_H26_DORMANT_CORRECTED_MATERIALIZATION_AUTHORITY_CONTRACT_EXTERNAL_SEAL_LOADER_AND_RAW_SHA_BINDING_ONLY
```

Parent exact :

```text
eb058ed2297997bd709ab0802913a62c68d5c427
```

Cette étape ajoute uniquement un loader fail-closed du seal déclaratif et un
test artificiel ciblé. Elle ne crée ni issuer, authority, claim, destination,
receipt, runtime record, population ou autorisation scientifique.

## Bindings fail-closed

```text
seal externe commit                 eb058ed2297997bd709ab0802913a62c68d5c427
seal externe blob                   8f5ab4f2aba65104f27a3eb8e1281b5df9ce9e92
contrat corrigé commit              84d1a196635c6ace7f3ea5ec9b7e338f5da70300
contrat corrigé blob                94f255c583a52d660dc57f70df80b97173791296
contrat corrigé longueur            19310
contrat corrigé SHA-256 brut        a82b00cfe197dc927dcc7a34ee409b7ea8ab374f36b6e41ebdaea12710258002
clôture du validateur               0ff5f5e4dffa30605292c293ff4f3a367fb41852
validateur approuvé                 18b8d5a73e61ab9143b897cb68479ae571c62bca
module du validateur blob           fd5e40fb7307929e18fdc99d518692315b22f381
```

Le loader vérifie le blob exact du seal avant tout parsing JSON. Il impose le
schéma, la version, le statut, les bindings, `seal_contains_own_raw_sha256=false`
et l'objet exact des états opérationnels `false`/`null`.

Le contrat corrigé est relu et les checkouts CRLF sont ramenés uniquement aux
bytes Git LF attendus. Le loader vérifie ensuite le blob Git, la longueur et le
SHA-256 brut, puis vérifie le blob historique du module de preuve approuvé.

## Validation artificielle autorisée

Le test ciblé couvre : seal exact immutable, seal/schema/status/état modifiés,
faux blob du seal, faux blob du contrat, faux SHA-256, fausse longueur,
convergence LF/CRLF, faux blob ou fichier du validateur, absence de fichier
créé et absence de toute API opérationnelle, NumPy ou materializer.

Les seules validations permises sont `py_compile`, ce nouveau test dormant,
`git diff --check`, le scope exact et le worktree propre.

Résultats locaux :

```text
py_compile                                    OK
test dormant                                  9/9 OK
durée unittest                                0,063 s
git diff --check                              OK
```

## Frontière inchangée

Aucun builder, issuer, authority, claim, destination, runtime réel,
materializer, NumPy, BLAS, `otool`, P0, P1, P2, donnée, modèle, entraînement,
calibration, science ou locked-test n'est autorisé ou exécuté par ce loader.
Une revue externe est obligatoire avant toute autre portée.
