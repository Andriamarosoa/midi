# Primitives dormantes du codec et des identités d'exécution H26

Date : 2026-08-11

## Portée

Ce changement implémente uniquement les primitives pures autorisées après la
revue du contrat déclaratif H26. Il ne crée aucun issuer, authority, claim,
slot filesystem, preuve d'entrée, receipt ou record et n'appelle jamais
`observe_primary_runtime`. Aucun import NumPy, inspection BLAS, donnée réelle,
waveform, P0/P1/P2, modèle ou locked-test n'est utilisé.

Le module est lié aux identités approuvées suivantes :

```text
contrat d'exécution commit
e0e070b8b75e85fb8ef78c7d6950a13f2c69ceae

contrat d'exécution blob Git
5ab6ff43980c0dc0f32308d3f8cee14a90351ec7

contrat de qualification runtime commit / blob / SHA brut
89cc0659de3afb5194afcf8e7ea9ac6c300e1f92
c3a021872dfd3a99b6977fdef1302d5edc755fea
eec08691f12f673f86ed3839379865cbe6087e974a6745b1a4ef6cecea839736

qualificateur dormant commit / blob
25a08630d6ad99d5e3432a277b99b9603990458a
ef24d9ebdc4ae834b3b872175fb7e098330a68bf
```

## Primitives ajoutées

- loader fail-closed du seul contrat d'exécution au blob Git approuvé;
- sérialiseur JSON manuel ASCII-safe avec ordre Unicode logique des clés;
- parser qui refuse les octets sémantiquement équivalents mais non canoniques;
- rejet explicite des doublons, floats, NaN/Infinity, BOM, CR/CRLF, whitespace,
  échappements alternatifs et surrogates isolés;
- SHA-256 externe sur les octets exacts;
- validation syntaxique de l'`authority_id` et des SHA lowercase 64-hex;
- dérivation déterministe domain-separated de `claim_id` et de l'identité de
  slot identique;
- dérivation déterministe de l'ID et du slot observer-entry, avec contrôle que
  le claim appartient bien à l'authority fournie;
- validateurs purs des quatre keysets fermés du contrat.
- loader fail-closed du seal externe `d60df11a…` / blob `90819f50…`;
- vérification du SHA-256 brut `c7f6da69…` sur les octets Git LF exacts du
  contrat, avec équivalence contrôlée des checkouts LF et CRLF;
- rejet de tout seal altéré, mauvais binding public ou état opérationnel actif.
- SHA canonique purement mémoire de tout mapping artificiel;
- validation complète de l'authority artificielle et de ses bindings fixes;
- validation du claim artificiel après recalcul du SHA authority, inheritance
  exacte et redérivation de `claim_id`;
- validation de la preuve observer-entry artificielle après recalcul du SHA
  claim et redérivation complète de son ID.

## Validation dormante

Commande exécutée avec le virtualenv déjà présent dans le dépôt principal :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest tests.test_harmonic_censoring_h26_runtime_execution_primitives_dormant
```

Résultat final : `41 tests réussis`.

La suite couvre notamment tous les échappements prescrits, le rejet des formes
non canoniques, deux vecteurs SHA-256 calculés indépendamment, l'égalité
ID/slot, la liaison claim-authority, le loader du blob approuvé et les keysets
fermés.

La suite finale ajoute les cas seal exact, seal modifié, faux SHA brut,
ancienne/mauvaise identité de blob et parité LF/CRLF des octets Git canoniques.
Elle couvre aussi toutes les liaisons authority fixes, les SHA authority/claim,
l'inheritance du claim, les identités claim/evidence, l'ordinal d'entrée et
l'absence d'effet filesystem des validateurs.

## État terminal de cette étape

```text
implementation_scope = canonical codec and derived ID primitives only
runtime_execution_authorized = false
authority_exists = false
claim_exists = false
observer_invoked = false
observer_entry_evidence_exists = false
runtime_record_exists = false
receipt_exists = false
scientific_execution_authorized = false
locked_test_used = false
```

La prochaine action est une revue externe de ce commit dormant. Toute émission,
persistance, consommation, invocation runtime ou exécution scientifique exige
une autorisation séparée.
