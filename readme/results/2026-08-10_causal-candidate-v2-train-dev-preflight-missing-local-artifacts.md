# Anomalie de préflight du diagnostic causal V2 train/dev

Horodatage brut de fin worker : `2026-08-10T01:02:26Z` (non réconcilié)
Branche : `codex/independent-note-neural-v2`
Commit exécuté : `ddd15be4fbf7e47205a0025f80821e2446ef9720`
Job : `causal-candidate-v2-train-dev-cpu-20260809`
Statut : `exited_nonzero`, code `1`, pré-métrique et non autorisant.

## Invocation approuvée

Le Mac a été synchronisé au commit exact approuvé, avec worktree propre et
script worker recopié depuis ce commit. Avant le lancement, le worker ne
signalait aucun job actif et le nouveau `JobId` n'existait pas.

L'unique invocation a utilisé exclusivement le wrapper scellé :

```text
module  = src.polyphonic.run_causal_candidate_v2_train_dev_diagnostic
device  = cpu
timeout = 900 s
args    = aucun
ack     = CausalCandidateV2DiagnosticExecute
commit  = ddd15be4fbf7e47205a0025f80821e2446ef9720
```

Le worker a enregistré les sorties suivantes :

```text
stdout = /Users/amcarene/midi-worker/logs/causal-candidate-v2-train-dev-cpu-20260809.stdout.log
stderr = /Users/amcarene/midi-worker/logs/causal-candidate-v2-train-dev-cpu-20260809.stderr.log
finished_utc = 2026-08-10T01:02:26Z (horodatage worker brut, non réconcilié)
```

## Échec constaté

Le stdout confirme que la nouvelle garde worker V2 a passé :

```text
OPEN_FILE_LIMIT soft=4096 requested=4096
REMOTE_SEALED_V2_DIAGNOSTIC_PREFLIGHT module=causal_candidate_v2_train_dev_diagnostic cpu=1 timeout=900
```

Le runner s'arrête ensuite dans
`load_sealed_v2_diagnostic_contract()` lors de la première vérification des
artefacts locaux :

```text
FileNotFoundError:
/Users/amcarene/midi-worker/repository/tmp/local
```

L'inspection minimale du Mac confirme que `repository/tmp` existe mais que
`repository/tmp/local` est absent. Ce sous-répertoire devait contenir les
artefacts locaux déjà scellés de la préinscription Policy A : le plan de
partition et le registre d'actifs. Leur absence empêche toute dérivation de la
cohorte V3 avant TensorFlow.

## Bornes de l'incident

L'appel fautif survient avant `configure_sealed_validation_cpu_tensorflow()`,
`keras.models.load_model()`, l'ouverture du checkpoint, l'ouverture des actifs
audio/labels et la boucle des 30 prises. Il n'y a donc eu :

- aucune inférence de transcription ;
- aucun événement MIDI ni métrique A/B ;
- aucun fit, calibration, export ou live ;
- aucune utilisation des 12 prises validation historiques ;
- aucun test verrouillé.

Après l'arrêt, la destination
`repository/tmp/causal_candidate_v2_train_dev_diagnostic_20260809` est absente
et `active.lock` est absent. Aucun processus n'est resté actif.

## Décision et prochaine action

Cette tentative ne produit pas de résultat expérimental et ne doit pas être
présentée comme une passe V2. Elle ne doit pas être relancée automatiquement.
La seule étape suivante est une revue de la manière de matérialiser et de
vérifier les deux artefacts locaux scellés sur le Mac, sans modifier leurs
octets ni les remplacer silencieusement. Toute reprise éventuelle devra être
autorisée explicitement après cette revue, avec un nouveau JobId et le même
protocole V2 non promotionnel.
