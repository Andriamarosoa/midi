# Demande d'autorisation attempt2 — validation indépendante V2

## Situation héritée

La première autorisation a été consommée par un
`premetric_infrastructure_failure`. Sa cohorte scientifique n'a pas été
consommée, mais son approval, sa capability et son marker ne peuvent jamais être
réutilisés. Le marker historique reste intact :

```text
tmp/local/causal_candidate_v2_independent_validation_one_job_20260810.claimed.json
SHA-256 c0b544e2faed44df45985ccb9abfd13ed067966e907fe4f0f4c2bb83433225eb
```

Le correctif execution-specific evidence gate a été approuvé au commit :

```text
c78b1e1cbcee8f7bf7fffe358ea8a19a4392e0b9
```

## Nouvelle demande, entièrement distincte

La demande canonique versionnée est :

```text
configs/causal_candidate_v2_independent_validation_attempt2_authorization_request.json
SHA-256 5c8a9ef2dc591d44395e761cda8967abf0cf5258504554af10166b1d42ea86ef
```

Elle fixe exactement :

```text
job_id
causal-candidate-v2-independent-cpu-20260810-attempt2

destination
tmp/local/causal_candidate_v2_independent_validation_execution_20260810_attempt2

future external approval
tmp/local/causal_candidate_v2_independent_validation_external_review_approval_20260810_attempt2.json

persistent marker
tmp/local/causal_candidate_v2_independent_validation_one_job_20260810_attempt2.claimed.json
```

Elle lie aussi :

- runner revu `c78b1e1cbcee8f7bf7fffe358ea8a19a4392e0b9` ;
- contrat d'exécution SHA-256
  `269efb65f225cf2522eab895cf59c351bea6bb97bc20229160f611c5e3ae63ed` ;
- evidence SHA-256
  `10307a642185b3ef64a15a1120ec44ea4460c5875018b02fdaa7a18512822aee` ;
- CPU, timeout `900 s`, arrêt après rapport ;
- exécution unique, retry automatique interdit, promotion automatique interdite ;
- `locked_test_used=false`.

## Séparation fail-closed

L'ancien approval ne peut pas autoriser attempt2 : le purpose, le SHA de la
demande, le runner revu et le chemin attendu sont différents. La présence de
l'ancien marker est acceptée comme preuve historique mais ne crée aucune
autorité attempt2.

Attempt2 exige son propre approval externe, encore absent. Après cet approval
seulement, son premier appel créera son propre marker avec `O_CREAT | O_EXCL`,
avant d'attester la capability. Ce marker ne sera jamais supprimé, même après
une erreur. Toute deuxième invocation échouera avant le runner.

## Portée actuelle

Ce commit ne crée pas l'approval attempt2, le marker attempt2 ou une capability
réelle. Il ne lance aucun worker et n'ouvre aucun actif scientifique. Il ne
modifie ni l'evidence gate approuvé, ni le runner scientifique, A/B, le seuil
`0,31`, les 12 features, le placement `post_ranking_pre_noteon`, le modèle, le
checkpoint, le décodeur, la cohorte, les protocoles scientifiques ou le contrat
d'exécution.

Les tests sont uniquement synthétiques/mockés : ancien marker présent, ancien
approval inutilisable, approval attempt2 absent, mauvais commit, marker
attempt2 `O_EXCL`, capability exacte et appel mocké unique du runner. Cette
demande attend une revue externe; elle n'autorise pas l'exécution attempt2.
`py_compile`, `76` tests ciblés réussis en `17,365 s` et `git diff --check`
constituent les seules validations de ce commit.
