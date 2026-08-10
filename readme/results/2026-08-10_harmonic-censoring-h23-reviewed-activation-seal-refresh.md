# H23 — nouveau couple contractuel activation + seal

## Autorisation

La revue externe approuve le correctif TOCTOU dormant :

```text
1025ac56706312718e93f9078fdf9c341276c8ea
```

Elle autorise uniquement la création d'un nouveau couple contractuel
activation + seal. L'injection OS, l'émission d'une capability et toute
exécution restent interdites.

## Seal

Le seal canonique lie :

```text
reviewed_execution_commit
1025ac56706312718e93f9078fdf9c341276c8ea

capability_source_blob
9bbe965c2115fd3360ff7d4d0adecbb895b5542f

runner_source_blob
c4f435a20f363adb75b831dc8b5526eaee42f46b

executor_claim_transcript_contract_raw_sha256
8126edc0a27fe43bbb41f0d8e874c1355e01f9f1185c1a71d70048fcaea661ef
```

Son `exact_changed_files` est le vrai diff-tree trié du commit approuvé :

```text
readme/README.md
readme/results/2026-08-10_harmonic-censoring-h23-preclaim-toctou-hardening.md
src/polyphonic/harmonic_censoring_h23_execution_capability.py
src/polyphonic/run_harmonic_censoring_h23_synthetic.py
tests/test_harmonic_censoring_h23_claim_transcript_implementation.py
```

Les quatre destinations one-shot sont distinctes sous
`tmp/h23_synthetic_execution_20260810/`, dont le transcript JSONL désormais
obligatoire.

SHA-256 brut du seal :

```text
381d83e5dd184a1ad72f29aa4f8450b3a1d066b582e8191ef2290640f7bd0899
```

## Activation

L'activation référence le chemin canonique du seal, son SHA brut, le commit
d'implémentation et les mêmes trois bindings source/contrat.

SHA-256 brut de l'activation :

```text
81d0f0d6739e082745ae646a57ad31b17a62b5007dd4c0f718701c03dfe25906
```

Les parseurs stricts valident les deux schémas et leur cross-binding.

## Dormance

```text
H23_AUTHORIZATION_ACTIVATION_COMMIT injecté  false
capability émise                             false
claim / marker                              absent
waveform                                    absente
P0 / P1 / P2                                non exécutés
population H17                              non utilisée
locked-test                                 non utilisé
```

La prochaine étape est uniquement la revue externe de ce couple. Même après
approbation documentaire, aucune injection ni exécution ne devra avoir lieu
sans une autorisation opérationnelle séparée.
