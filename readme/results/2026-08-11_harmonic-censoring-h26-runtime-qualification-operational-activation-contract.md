# H26 - contrat dormant d'activation operationnelle du runtime

Date : 2026-08-11

## Objet

Ce commit ferme declarativement la frontiere entre la pile runtime dormante
approuvee et une eventuelle qualification reelle future. Il ne cree aucune
activation, issuer, capability, authority, claim, racine administrative,
evidence, record ou receipt et n'invoque pas `observe_primary_runtime()`.

Le parent exact est `1145048d8b68842f55fea890cc6c006ff2ecd67e`.

## Bindings

Le contrat lie exactement :

```text
runtime execution contract
e0e070b8b75e85fb8ef78c7d6950a13f2c69ceae
5ab6ff43980c0dc0f32308d3f8cee14a90351ec7
c7f6da697d74f710b957ab7ad32bef0fc184bb4f16ffaef16d2e2e1abafc63f9

runtime qualifier
25a08630d6ad99d5e3432a277b99b9603990458a
ef24d9ebdc4ae834b3b872175fb7e098330a68bf

authority/claim/evidence validators
10d3ee0525790279bce299492d89cec4002ab931
1c1777ad7c4493e66674d1daf63508778874df04

terminal receipt validator
09ef74cd537392d76eab1ed09082bf04e0214f16
9721a41eca9e3f2bfa1ef8150ff39bf34ccf5fce

runtime validation closure
b1b13048efeb73b468cb7fbb0f1ccff4c00ff0d0
f26262b28e9d00e5d5c270461dd72c04e16bbaf9

downstream materialization proof validator
18b8d5a73e61ab9143b897cb68479ae571c62bca
fd5e40fb7307929e18fdc99d518692315b22f381
```

## Frontiere future definie

L'objet d'activation futur possede un keyset exact de 26 champs, des types
fermes, les bindings fixes et les limites `1 authority / 1 claim / 1 observer`.
L'issuer, la capability, l'ID d'activation, sa date et la racine restent des
valeurs futures. Le contrat n'autorise pas leur construction.

L'activation est la future capability single-use. Son ID est derive de facon
unique des 25 autres champs canoniques avec le domaine
`H26_RUNTIME_QUALIFICATION_OPERATIONAL_ACTIVATION_ID_V1`. Le codec administratif
approuve est reutilise : JSON ASCII-safe, cles triees, aucun float, aucun
whitespace et un unique LF terminal. Le SHA complet reste externe et non
recursif.

La racine future doit etre un chemin POSIX absolu canonique et absent. Tous les
chemins sont derives sans choix du caller :

```text
authority/{authority_id}.json
claim/{claim_id}.json
observer-entry/{observer_entry_evidence_id}.json
runtime-record/{claim_id}.json
receipt/{claim_id}.json
```

Chaque chemin de staging est egalement determine. Aucun suffixe temporel,
aleatoire, numerique ou fallback de collision n'est permis.

L'ordre futur est ferme : authority durable, claim create-exclusive qui
consomme l'authority, evidence create-exclusive depuis l'interieur de l'entree
observer, une seule observation, record atomique eventuel, puis receipt
terminal publie en dernier.

Avant l'entree observer, un echec apres tentative de claim laisse authority et
claim consommes sans receipt. Apres l'entree observer, un echec doit produire
un receipt `H26_MATERIALIZATION_RUNTIME_QUALIFICATION_INCONCLUSIVE_CONSUMED`,
sans record et sans retry. Une terminaison QUALIFIED ou DISQUALIFIED exige
record puis receipt.

## Etat present

Tous les champs operationnels sont encore `false`, `null` ou zero : aucune
activation, issuer, capability, racine, authority, claim, evidence, invocation,
record ou receipt. Materialisation, population, P0, P1, P2, science et
locked-test restent interdits.

## Validation permise

Uniquement parsing JSON strict, controles statiques de keysets/types/bindings,
chemins, ordre, semantique d'echec, etats dormants, `git diff --check`, portee
exacte de trois fichiers et worktree propre.

La prochaine etape est la revue externe de ce contrat declaratif. Aucune
implementation ou activation n'est autorisee par ce commit.
