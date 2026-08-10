# H23 — émission administrative de la capability sur Mac

## Autorisation

La revue externe du commit
`31b116c03f535433dddeb5d800e3f48d09c138d7` conclut `APPROUVÉ` et autorise
uniquement :

```text
H23_AUTHORIZATION_ACTIVATION_COMMIT=31b116c03f535433dddeb5d800e3f48d09c138d7
→ preflight administratif
→ émission process-local de la capability
→ arrêt avant claim et science
```

Elle n’autorise ni claim, ni marker, ni waveform, ni P0/P1/P2.

## Exécution worker

Le workspace Mac a été synchronisé en detached HEAD exactement sur
`31b116c…`, avec worktree propre et aucun verrou/job actif. Le runtime observé
avant lancement était :

```text
CPython 3.11.9
arm64
NumPy 1.26.4
CPU
OMP/OPENBLAS/MKL/NUMEXPR threads = 1
```

Le worker mono-usage a lancé une seule fois :

```text
job_id              h23-admin-capability-31b116c
commit              31b116c03f535433dddeb5d800e3f48d09c138d7
device              cpu
wall_timeout_seconds 300
module              src.polyphonic.run_harmonic_censoring_h23_synthetic
module_args          aucun
```

## Résultat attendu du garde dormant

Le job termine avec :

```text
status    exited_nonzero
exit_code 1
finished  2026-08-10T22:45:48Z
```

Le traceback arrive dans `run_authorized_h23_synthetic_execution()` après :

```text
issue_h23_synthetic_execution_capability(repository)
require_attested_h23_synthetic_execution_capability(capability)
```

et s’arrête exactement sur :

```text
PermissionError: H23 runner is dormant: the production synthetic executor is
absent; the capability has not been claimed and no waveform was synthesized.
```

Ce point d’arrêt prouve que le seal, l’activation, le commit, les blobs, le
runtime, le plan et les chemins one-shot ont passé le preflight, puis que la
capability process-local a été émise et reconnue par son registre d’identité.
L’objet disparaît avec le processus ; il n’est ni sérialisé ni réutilisable.

## Preuves worker

```text
status.env
taille 188
SHA-256 d208eb665fe46e40c69a6bd96b2548e32b20212af927d6bc447184ec64cdf371

process.env
taille 174
SHA-256 42e5a2d589a9f8cb6725ee0588629b9c5c4ad15ff2b16bd4a70b4d08d93b1477

system-start.txt
taille 364
SHA-256 f7f6f23a8c8998afe733de8d09bbd183faf89d8b5d161c151c1ab9312c0b0711

system-finish.txt
taille 365
SHA-256 aeb903bd869b7e40b1961926bdbf912f8523373ff17b88379e3411fac12e095b

stdout
taille 41
SHA-256 a11534a431ef496411f1a9137f487d7d3c3d0a647ca8cbe5f7f9d7e042ba90b7

stderr
taille 849
SHA-256 a4af1c1902ffe02d5ad538938d6618eb4ff42f13dcd39f1cee2f7935e0859e86
```

Après terminaison :

```text
remote HEAD       31b116c03f535433dddeb5d800e3f48d09c138d7
remote dirty      false
active_lock       false
active_job        none
marker_exists     false
success_exists    false
terminal_exists   false
```

## État scientifique

```text
administrative_preflight_passed true
capability_issued_process_local true
capability_persisted            false
consumption_claimed             false
synthetic_population_consumed   false
authorization_marker_created    false
waveforms_synthesized           false
P0_P1_P2_executed               false
real_data_used                  false
model_or_checkpoint_loaded      false
H17_population_used             false
locked_test_used                false
training_authorized             false
```

La prochaine action est uniquement la revue externe de cette preuve. Le claim
et l’exécuteur scientifique restent non implémentés et non autorisés.
