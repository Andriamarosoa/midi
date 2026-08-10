# H24 — contrat d'autorisation d'exécution scientifique

## Verdict opérationnel précédent

La population locale Mac `H24_SYNTHETIC_V1` a été matérialisée une seule fois,
puis auditée en lecture seule. L'audit administratif a confirmé :

- `175` fixtures uniques dans l'ordre scellé ;
- `525` fichiers fixture et `527` fichiers publiés au total ;
- `175` waveforms de `100352` octets, sans décodage scientifique pendant
  l'audit ;
- staging absent et success présent ;
- `scientific_tests_executed=0` et `locked_test_used=false`.

Les liaisons publiées sont :

- marker : `3185adfdba7615900062378d7a230d9b990913d3197c2e9d1b006abbc0e62b85d` ;
- terminal : `50ec58c81d1a0ae533599676536d141c7f98ac337686c1baf66517bc3e39c54eb` ;
- receipt : `8a8128dc97c61f4203a89e116787f9eae319e7c146fbcd06b4432c4108f92cd5` ;
- index : `b45b63c477a3db13d161779bb28067c0b2b6fa5c4cc80c985199e9347e1eff15` ;
- IDs ordonnés : `d4b23a898d8775f772e91933ace7c90c2e7b5a808e32bf9955088287bbe9670f`.

## Portée de ce commit

Ce commit applique uniquement
`AUTHORIZED_TO_DEFINE_H24_SCIENTIFIC_EXECUTION_AUTHORIZATION_CONTRACT_ONLY`.
Le nouveau contrat a le SHA-256 :

`63355a01d6edb58c8cb3d41bebcd18264314a6b19a6ad8de96650a59541e9f68`.

Il lie la population publiée aux contrats, manifests et sources H24 existants.
Il définit un futur mécanisme fail-closed, sans l'implémenter :

1. capability scientifique process-local distincte ;
2. seal et activation scientifique séparés et revus ;
3. binding OS exact et worktree propre ;
4. rehash administratif complet des `525` fichiers avant émission ;
5. claim scientifique `O_EXCL` distinct du marker de matérialisation ;
6. décodage des waveforms seulement après ce claim ;
7. ordre fermé `P0 (27) → P1 (35) → P2 (10)` avec kill rule ;
8. terminal atomique et aucun retry après consommation.

## Dormance

Ce commit ne crée ni capability scientifique, ni runner, ni seal, ni
activation, ni claim scientifique. Il ne lit pas les waveforms publiées, ne
lance aucun evaluator/oracle et n'exécute aucun P0/P1/P2. Il n'utilise ni
données réelles, ni H17, ni locked-test, ni modèle/checkpoint, ni training.

La population publiée est immutable : aucune réparation, régénération ou
seconde matérialisation n'est autorisée.

## Vérification

La suite contractuelle ciblée H24/H23/H20 réussit avec `181` tests en
`2,349 s`. `py_compile` et `git diff --check` réussissent également.

## Étape suivante

Uniquement la revue externe du commit contract-only exact. Une autorisation
séparée sera nécessaire avant toute implémentation dormante de capability ou de
runner scientifique. P0/P1/P2 restent interdits.
