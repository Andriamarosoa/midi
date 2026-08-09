# Attempt2 — échec d'infrastructure pré-métrique et demande attempt3

## Classification

La deuxième autorisation one-job a été consommée au commit exact :

```text
0a622e030d9be7add9ed4e2e78e0f1b7366683d3
```

Son approval externe canonique faisait `416` octets, SHA-256 :

```text
edc1f85a9f0a38ce33106fe718c0436bf9aed9a35a3660f6e009c03b4789c22e
```

Le marker attempt2 persistant a été créé et reste immuable, SHA-256 :

```text
36459c58011a6be2eded2adf3819c0eafddc5ffb36633276afeb928e55a754e8
```

Le runner s'est ensuite arrêté sur l'absence du fichier :

```text
/Users/amcarene/midi-worker/repository/tmp/local/
causal_candidate_v2_independent_validation_asset_evidence_20260810.json
```

L'arrêt a précédé la validation des 60 actifs, TensorFlow scientifique, le
chargement du modèle, l'ouverture audio/labels, l'inférence, les deux décodages
et toute métrique A/B. La destination attempt2 et le verrou lourd sont absents.
Attempt2 est donc classée `premetric_infrastructure_failure` : son autorisation
est consommée, mais la cohorte scientifique ne l'est pas.

## Matérialisation de l'infrastructure manquante

Le registre historique a ensuite été copié atomiquement, sans parsing ni
réécriture, vers le chemin exact attendu par le worker. Son SHA source et son
SHA destination sont identiques au SHA scellé :

```text
10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee
```

Cette matérialisation n'a lancé ni Python scientifique, ni TensorFlow, ni
audio/labels, ni modèle, ni inférence. Le marker attempt2 est resté présent, la
destination attempt2 est restée absente et aucun retry attempt2 n'a eu lieu.

## Demande attempt3

La nouvelle demande canonique est :

```text
configs/causal_candidate_v2_independent_validation_attempt3_authorization_request.json
SHA-256 8856fbf5a6f5a981395d0b74cf0b9128b7d24e03fbba88b800e9d315e8c5df5f
```

Elle scelle une identité entièrement distincte :

```text
job
causal-candidate-v2-independent-cpu-20260810-attempt3

destination
tmp/local/causal_candidate_v2_independent_validation_execution_20260810_attempt3

future approval
tmp/local/causal_candidate_v2_independent_validation_external_review_approval_20260810_attempt3.json

persistent marker
tmp/local/causal_candidate_v2_independent_validation_one_job_20260810_attempt3.claimed.json
```

Elle conserve sans modification le runner revu `c78b1e1c`, le contrat
d'exécution SHA-256 `269efb65f225cf2522eab895cf59c351bea6bb97bc20229160f611c5e3ae63ed`,
l'evidence SHA-256 `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee`,
CPU, `900 s`, arrêt après rapport, exécution unique, absence de retry et
`locked_test_used=false`.

Le préflight attempt3 vérifie désormais les octets du registre worker au chemin
exact avant de créer le marker persistant. Les tests synthétiques couvrent les
anciens markers/approvals sans autorité, l'approval attempt3 absent, le registre
absent ou altéré avant marker, le bon registre, le mauvais HEAD/diff/runner,
`O_EXCL`, la persistance du marker, la capability exacte et l'appel unique du
runner mocké.

## Portée

Ce commit ne modifie ni runner scientifique, evidence gate, contrat
d'exécution, protocole, modèle, checkpoint, seuil, features, cohorte ou registre.
Il ne crée aucun approval ou marker attempt3 et ne lance aucun job. Il demande
uniquement une nouvelle revue externe avant toute exécution.

Validation locale uniquement synthétique : `py_compile`, `67` tests ciblés
réussis en `4,604 s` avec l'environnement projet, et `git diff --check`.
