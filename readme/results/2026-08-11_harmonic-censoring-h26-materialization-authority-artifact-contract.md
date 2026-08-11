# H26 — contrat canonique du futur artefact d'autorité de matérialisation

Date : 2026-08-11

## Portée

Cette étape est exclusivement déclarative. Elle définit les octets, le schéma,
l'identité et la validation du futur artefact d'autorité de matérialisation
H26. Elle ne crée ni issuer, authority, seal d'authority, claim, destination,
runtime record, population ou calcul.

Le parent exact est `f51eac200ca83d02a2c6fd750e2ac4c90cf6865d`. Les seuls
fichiers autorisés sont le nouveau contrat JSON, le présent rapport et le
README.

## Chaîne approuvée

Le contrat lie sans fallback :

```text
contrat corrigé  84d1a196635c6ace7f3ea5ec9b7e338f5da70300
blob             94f255c583a52d660dc57f70df80b97173791296
bytes            19310
SHA256           a82b00cfe197dc927dcc7a34ee409b7ea8ab374f36b6e41ebdaea12710258002
seal externe     eb058ed2297997bd709ab0802913a62c68d5c427 / 8f5ab4f2aba65104f27a3eb8e1281b5df9ce9e92
loader approuvé  88593f7f065e7492af566e2ca90577c09916923e / 39316388a777ea34fb6b2b560809f2b679475732
clôture loader   f51eac200ca83d02a2c6fd750e2ac4c90cf6865d
```

Les bindings scientifiques, runtime et materializer du contrat corrigé sont
recopiés comme égalités structurelles. La future preuve runtime doit être une
seule projection complète à neuf champs produite par le validateur approuvé,
avec le seul terminal acceptable
`H26_MATERIALIZATION_RUNTIME_QUALIFIED`.

## Artefact futur fermé

Le futur objet contient exactement les 36 champs déjà préenregistrés, sans
champ additionnel. Le type de chaque champ est fixé. Les commits/blobs sont des
hex lowercase de 40 caractères; les SHA-256 des hex lowercase de 64 caractères.

`issued_at` devra être un UTC RFC3339 exact `YYYY-MM-DDTHH:MM:SSZ`, sans
fraction ni offset. `issuer_identity` devra être un identifiant ASCII de 1 à
128 caractères, sans espace ni placeholder. La destination future est un
chemin POSIX absolu unique, fixé avant claim, sans segment vide, `.` ou `..`,
et sans fallback de suffixe.

## Octets canoniques et identité

L'encodage est le codec canonique H26 déjà approuvé : UTF-8 ASCII-safe, clés
triées, séparateurs `,` et `:`, aucun whitespace extérieur aux strings, aucun
float, échappement unique et exactement un LF terminal. Une représentation
sémantiquement équivalente mais byte-différente est refusée, pas normalisée.

```text
payload = objet authority exact, sans la clé authority_id
preimage = ASCII("H26_MATERIALIZATION_AUTHORITY_ID_V1")
           || 0x00
           || canonical_json_bytes(payload)
authority_id = "h26-materialization-authority-v1-"
               || lowercase_hex(SHA256(preimage))
```

Le champ dérivé est ensuite inséré, puis l'objet complet de 36 champs est
canonisé. Son `authority_raw_sha256` est calculé extérieurement et n'apparaît
jamais dans l'authority.

## Seal externe séparé

Le futur seal d'authority reste un autre artefact à cinq champs exactement :
`seal_schema_identity`, `seal_schema_version`, `authority_raw_sha256`,
`authority_contract_raw_sha256`, `approved_authority_contract_commit`.
Ni l'authority ni le seal ne contient son propre SHA.

## État présent

```text
issuer / validator / authority / seal / claim    absents
absolute_destination                              null
runtime_execution_authorized                      false
materialization_authorized / executed             false / false
population_exists                                 false
P0 / P1 / P2                                      false / false / false
scientific_execution_authorized                   false
locked_test_used                                  false
```

La validation permise pour ce commit est limitée au parsing JSON strict, aux
contrôles statiques des keysets/types/bindings et à `git diff --check`. Aucun
module, test, issuer, validator, materializer ou runner n'est ajouté.

Validation locale effectuée :

```text
parsing JSON strict et clés dupliquées refusées   OK
absence de float                                 OK
keyset authority                                 36/36 exact
types déclarés                                   36/36 exact
contraintes fixes                                24 vérifiées
états présents                                   28 false/null
fichiers modifiés                                3/3 autorisés
git diff --check                                 OK
```

## Prochaine porte

Revue externe de ce contrat déclaratif uniquement. Une autorisation séparée
sera nécessaire avant toute implémentation d'un validateur dormant d'authority.
