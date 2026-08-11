# H26 — P0 inconclusif consommé

Date : 2026-08-12

## Verdict terminal

```text
terminal_status = H26_P0_INCONCLUSIVE_CONSUMED
documentary_state = H26_P0_EXECUTION_INCONCLUSIVE_CONSUMED_NO_RETRY_PENDING_FORENSIC_REVIEW
executed_commit = eaed599a5a051685288f1f71b3cb057db64392c2
scientific_runner_invocations = 1
retry_allowed = false
```

La publication durable de `claim.json` a consommé définitivement l'unique
autorisation P0. Aucune relance n'est autorisée ou effectuée.

## Artefacts publiés

```text
claim_sha256 = 0e519f04dfda4ca599355deb5849f5d8d4b6178591ecde54d75998645ed7db04

P0-001 = PASSED
P0-001 evidence_sha256 = e10cb9ecac9ce7179738b3efc864740663c4b90b37f0a39fe8d9a3019f09a439

P0-002 = NOT_COMPLETED_OPERATIONAL_EXCEPTION
error_type = ValueError
error_message = H26 spectrum total power invalid

transcript = absent
transcript_raw_sha256 = null

receipt_sha256 = 371e9eda666e1da4e18657e9724d56d568d55103434b55870736403fa8879b59
```

Le receipt archive également :

```text
scientific_runner_invocations = 1
retry_allowed = false
locked_test_used = false
p1_executed = false
p2_executed = false
```

## Qualification

P0-002 n'a pas rendu un résultat scientifique `FAILED`. L'évaluateur a levé
une exception opérationnelle avant de publier sa preuve. L'état n'est donc ni
`H26_PREREGISTRATION_OR_IDENTIFIABILITY_INVALID`, ni
`H26_P0_FAILED_KILL_STOP`, ni `H26_P0_PASSED_STOP_BEFORE_P1`.

P0-001 reste une preuve partielle archivée, mais elle ne permet aucune
conclusion P0 globale ni aucune conclusion sur l'hypothèse H26.

## État final vérifié

- un seul fichier evidence est présent : `001_H26-T-P0-001.json` ;
- `transcript.json` est absent ;
- aucun staging, `active.lock` ou processus P0 ne reste actif ;
- les deux checkouts Mac sont propres au commit exécuté ;
- aucun P1/P2, locked-test, entraînement, calibration, modèle ou checkpoint n'a
  été utilisé.

## Interdictions

- aucune nouvelle invocation H26 ;
- aucun retry ou nettoyage permettant un retry ;
- aucune rematérialisation ;
- aucun P1/P2, locked-test, entraînement ou calibration ;
- aucun changement de code, configuration ou lifecycle dans cette archive.

La seule suite envisageable après revue de cette archive est une analyse
forensique strictement read-only de la cause `spectrum total power invalid`,
avec une autorisation séparée.
