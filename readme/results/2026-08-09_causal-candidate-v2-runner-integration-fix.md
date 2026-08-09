# Correctif d'intégration du diagnostic causal V2

Date : 2026-08-09
Branche : `codex/independent-note-neural-v2`
Base revue : `5553db15142ed8a9e763f894fe89daa7cef09463`
Statut : correctif d'infrastructure terminé, revue externe requise avant toute exécution réelle.

## Portée

Cette modification ferme uniquement deux écarts d'intégration signalés lors de
la revue du runner V2 train/dev. Elle ne lance aucun processus Mac, ne lit aucun
audio, label, checkpoint ou artefact V1 réel et ne produit aucun rapport de
métriques. Les 30 prises dev, les 12 prises validation historiques et le test
verrouillé n'ont pas été ouverts.

## 1. Invocation Mac V2 scellée

`MAC_WORKER.ps1` reconnaît maintenant exclusivement
`-CausalCandidateV2DiagnosticExecute` pour le module exact :

```text
src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic
```

Cette voie refuse avant SSH toute combinaison ne respectant pas simultanément :

- `Device=cpu` ;
- `WallTimeoutSeconds=900` ;
- aucun `ModuleArgs` ;
- `ExpectedCommit` à 40 caractères, égal au HEAD du worktree Windows ;
- un seul acknowledgement causal.

Le wrapper envoie seulement le littéral
`DECODER_CANDIDATE_V2_DIAGNOSTIC_EXECUTE=1`. Le préflight de
`scripts/remote/mac_worker.sh` revalide d'abord le commit demandé contre le
HEAD Git Mac, puis, avant TensorFlow, refuse l'absence de cet acknowledgement,
un device non CPU, un timeout autre que 900 secondes ou tout argument de module.
Le verrou exclusif et le superviseur externe existants restent inchangés.

## 2. Politique audio réellement utilisée

Le runner V2 ne se contente plus de déclarer le SHA-256 de
`configs/polyphonic_audio_evidence_adaptive_temporal.json`. Il lit les octets
une fois, calcule et compare leur SHA-256 scellé, puis parse ce même buffer. Le
JSON doit être un objet et doit imposer :

```json
{"onset_adapt_temporal_background": true}
```

La métadonnée interne résultante est la seule passée à `evaluate_events`. Le
nouveau paramètre scellé est réservé au chemin train-only attesté ; il exige un
objet `audio_evidence`, interdit de le combiner avec une métadonnée appelant et
reste indisponible hors de ce chemin. L'évidence audio est toujours calculée
une fois par prise, avant les deux décodages, puis les mêmes `activity_mask` et
`onset_mask` sont transmis à A et B. La porte V2 reste le seul changement
expérimental : post-ranking/pre-NoteOn, seuil V1 `0,31`, même tête et même
standardiseur.

## Vérifications locales

Commande exécutée depuis le worktree :

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -m py_compile `
  src\polyphonic\run_causal_candidate_v2_train_dev_diagnostic.py `
  src\polyphonic\evaluate_events.py `
  tests\test_mac_worker_transport_contract.py `
  tests\test_run_causal_candidate_v2_train_dev_diagnostic.py `
  tests\test_causal_candidate_validation.py

C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest `
  tests.test_mac_worker_transport_contract `
  tests.test_run_causal_candidate_v2_train_dev_diagnostic `
  tests.test_causal_candidate_validation `
  tests.test_causal_candidate_v2 `
  tests.test_causal_candidate_v2_protocol
```

Résultat : `46` tests réussis en `9,044 s`. Les tests couvrent notamment les
refus PowerShell avant SSH, le préflight Bash V2 avant TensorFlow, le timeout
et le CPU imposés, le SHA/audio JSON cohérent, le refus du défaut audio non
adaptatif, l'obligation de la métadonnée scellée et le refus d'un override
appelant. `bash -n scripts/remote/mac_worker.sh` et `git diff --check` sont
aussi passés avant livraison du commit.

## Limites et prochaine action

Cette preuve est strictement synthétique et d'infrastructure : elle ne mesure
ni faux NoteOn, ni rappel, ni latence audio réelle. Ne pas synchroniser le Mac
et ne pas lancer le diagnostic V2 avant une revue externe de ce commit. Si elle
est favorable, l'autorisation devra rester limitée à une unique passe CPU de
900 secondes sur les 30 prises train/dev V3, rapport-only, sans fit,
calibration, validation historique, export, live ou test verrouillé.
