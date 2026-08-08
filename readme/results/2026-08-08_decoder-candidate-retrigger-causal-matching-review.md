# Revue approuvée — correctif causal des retriggers candidats

## Périmètre

- Branche : `codex/independent-note-neural-v2`.
- Commit examiné : `9e666eb0f83d556a2b74809d0ffee47c51966fa1`.
- Nature : revue de code et rejeu local uniquement.
- Aucun plan réel, ouverture de données projet, minage, entraînement,
  évaluation, export, live ou test verrouillé n'a été exécuté.

## Verdict externe

La revue stricte transmise le 8 août 2026 approuve le commit sans bloqueur.
Elle confirme notamment :

1. tous les NoteOn valides du flux réel, y compris les retriggers, sont matchés
   causalement avant la projection vers les seuls candidats entraînables ;
2. les compteurs de matches du flux complet et ceux des positifs de fit sont
   séparés et réconciliés ;
3. un plan seulement en mémoire ou un wrapper persistant forgé ne peut pas
   donner une capacité de collecte ;
4. une modification des octets du plan avant `drain()` rend le lot inutilisable.

La revue maintient l'interdiction de minage : la préinscription du plan réel et
la preuve des actifs audio/labels sont une phase distincte à faire revoir.

## Vérification locale indépendante

Commande rejouée sous Windows avec
`C:\Users\user\Desktop\midi\.venv\Scripts\python.exe` :

```text
python -B -m py_compile src/polyphonic/data.py \
  src/polyphonic/decoder_candidate_provenance.py \
  src/polyphonic/decoder_candidate_mining.py \
  src/polyphonic/decoder_candidate_miner.py \
  src/polyphonic/decoder_candidate_labels.py

python -B -m unittest \
  tests.test_decoder_candidate_snapshot_protocol \
  tests.test_decoder_candidate_labels \
  tests.test_decoder_candidate_provenance \
  tests.test_decoder_candidate_mining \
  tests.test_decoder_candidate_instrumentation \
  tests.test_polyphonic_decoder \
  tests.test_polyphonic_desktop_contract \
  tests.test_product_decoder \
  tests.test_polyphonic_validate_live_input_level \
  tests.test_ollama_team \
  tests.test_mac_worker_transport_contract \
  tests.test_polyphonic_smoke_neural_independent_note
```

Résultat : `Ran 131 tests in 9.336s` puis `OK`. La compilation réussit aussi.
Les avertissements TensorFlow de dépréciation et la métrique synthétique du test
Ollama n'ont déclenché aucune erreur. Cette exécution est distincte de la
vérification historique du commit, qui avait mesuré 8,993 s.

## Décision

Le contrat de provenance et le correctif des retriggers sont clos. La prochaine
action autorisée est de concevoir puis préenregistrer le plan réel et la preuve
des actifs, sans lancer de collecte. Une revue séparée reste obligatoire avant
la première collecte train-only. `locked_test_used=false` demeure inchangé.
