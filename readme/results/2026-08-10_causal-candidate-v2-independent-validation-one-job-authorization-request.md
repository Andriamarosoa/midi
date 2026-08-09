# Demande d'autorisation one-job — validation indépendante V2

Le runner indépendant V2 est gelé et approuvé au commit
`6246ea18c49a6c3c3b8e2ce1303c9a6afffac6ee`. Cette étape ajoute uniquement la
couche d'autorisation séparée; le runner approuvé, le contrat d'exécution, le
protocole scientifique, l'evidence et les configurations scientifiques restent
inchangés.

La demande versionnée canonique fixe : CPU, timeout `900 s`, job
`causal-candidate-v2-independent-cpu-20260810`, destination fraîche, arrêt après
rapport, absence de retry/promotion et `locked_test_used=false`. Elle lie le
contrat SHA `269efb65…63ed` et l'evidence SHA `10307a64…aee` au runner revu.
Son propre SHA-256 est vérifié par le module d'autorisation TensorFlow-free.
Il vaut exactement
`3145330a5bcd57cffb218914d3c545779ca54ce6634f716d49fae742dd922808`.

L'exécution reste volontairement impossible. Le fichier externe suivant est
absent et n'est pas versionné :

`tmp/local/causal_candidate_v2_independent_validation_external_review_approval_20260810.json`

Après une future revue, ce fichier devra nommer le SHA exact du commit
d'autorisation. Avant toute capability, le module exigera ce HEAD, un worktree
propre, le diff exact de cette seule étape et le blob inchangé du runner revu.
Il créera ensuite atomiquement, avec `O_CREAT | O_EXCL`, le marqueur persistant :

`tmp/local/causal_candidate_v2_independent_validation_one_job_20260810.claimed.json`

Le marqueur est fsync avant poursuite et ne sera jamais supprimé, même après un
échec preflight, lease, TensorFlow, inférence ou rapport. Une capability exacte
ne sera construite et attestée qu'après ce claim. `MIDI_FORCE_CPU=1` sera fixé
avant l'unique appel du runner, sans retry automatique.

Les `92` tests réussis en `8,772 s` sont entièrement synthétiques/mockés : request/approval/Git/diff,
runner inchangé, `O_EXCL`, persistance après erreur, champs de capability,
ordre marker puis attestation, environnement CPU, absence de TensorFlow et
appel unique du runner. Aucun approval externe réel, marqueur réel, capability
réelle, worker, actif projet, TensorFlow scientifique, modèle, checkpoint,
inférence, métrique ou test verrouillé n'a été utilisé.

Cette étape attend une revue externe. Elle n'autorise pas encore le job.
