# H12 — binding réel H7 et preflight zéro-science

## Statut

```text
provisional_resolution_age1_persistence_h12_real_execution_binding_sealed
```

H12 ne crée aucun marqueur et n'invoque pas le runner réel. Aucun audio/label
H8 n'est décodé/parsé, aucun modèle Keras chargé et aucun signal, target,
classe ou résultat scientifique n'est observé.

## Binding sans injection

Le point d'entrée futur est :

```text
src.polyphonic.provisional_resolution_age1_h12.run_real_h7_discovery()
```

Sa signature ne prend aucun argument. Il résout lui-même le contrat H11, la
cohorte H8, le manifeste, le plan, le registre, le checkpoint, le YAML, le
décoder et la politique audio. Il appelle directement
`evaluate_h7_synthetic_metrics`; aucun `metric_callable` externe n'est
possible.

Le contrat H12 fait `5802` octets, SHA-256 brut :

```text
d1f9e80227776c8d6c81fc91d7a2df8982425eaadf786b7406ca54f33fa41fce
```

## Identités scientifiques

```text
comportement historique decoder   4233186147c0946372ddb2e9e3dd3343daeb26eb
decoder instrumenté H9 exécuté    27026d368081fadc4fa282954428f0377020e723
implémentation H9                  22b93d2b5a6e2a3826eddc4aee0057d68fe34141
moteur métrique H10               a343c5057ec2a84f3e42c6be6e6e7b641c0f1a70
orchestrateur H11                 6ea9ba6637788552b5f3318b1f2dfac6fd52f71e
```

Le premier blob documente le comportement historique. Le second ajoute
l'interface passive H9 dont la neutralité événement/état a été revue en H9 ;
c'est lui qui sera exécuté. Resolver, porte causale et seuil independent-note
restent nuls.

Les APIs directes scellées sont `PassiveAge1SignalCollector`,
`require_no_pending_age1_at_end`, `extract_exact_causal_age1_targets`,
`join_age1_signals_and_targets` et `evaluate_h7_synthetic_metrics`.

## Adapter concret

`ConcreteH7ScientificAdapter` :

1. vérifie existence, taille et SHA raw de chaque actif ;
2. vérifie chaque membre GuitarSet dans l'archive dont les octets sont scellés ;
3. ouvre une prise via `PolyphonicCorpus` et un `ManifestItem` dérivé de H8 ;
4. utilise `PolyphonicSequence` et `predict_compat` avec checkpoint/YAML figés ;
5. calcule une fois l'évidence audio figée ;
6. exécute le décodeur instrumenté avec collecteur passif et toutes les portes
   de population désactivées ;
7. exige l'absence de pending age-1 ;
8. appelle directement l'extracteur H9 avec `truth_notes` historique.

Le preflight ne peut appeler aucune de ces opérations scientifiques.

## Preflight

Le mode explicite est :

```text
python -m src.polyphonic.provisional_resolution_age1_h12 --preflight-only
```

Il vérifie les SHA du contrat H11, H8, manifeste, plan, registre, checkpoint et
configs, les blobs Git, les 101 identités/31 groupes, les actifs comme octets,
les membres ZIP comme métadonnées et le runtime exact. Il exige l'absence du
marqueur, du `.claimed`, du résultat et du rapport d'échec. Il n'importe pas
TensorFlow : sa version `2.15.1` est lue via les métadonnées de paquet.

Le statut de réussite est `h7_real_execution_preflight_ready`, avec
`h8_discovery_consumed=false`.

### Preuve Mac zéro-science

Après synchronisation fast-forward du Mac sur
`d91548959df319f242c7f33fe8d578ed05dbffc6`, le seul mode exécuté a été :

```text
MIDI_FORCE_CPU=1
MIDI_DATA_ROOT=/Users/amcarene/midi-worker/data
python -m src.polyphonic.provisional_resolution_age1_h12 --preflight-only
```

Résultat canonique :

```json
{"execution_marker_created":false,"forbidden_groups":58,"h8_discovery_consumed":false,"h8_scientific_assets_opened":false,"leakage_groups":31,"real_metrics_computed":false,"real_signals_extracted":false,"real_targets_extracted":false,"recordings":101,"runtime":{"architecture":"arm64","darwin":"24.5.0","device":"cpu","macos":"15.5","numpy":"1.26.4","python":"3.11.9","tensorflow":"2.15.1"},"scientific_execution_authorized":false,"status":"h7_real_execution_preflight_ready"}
```

Le HEAD Mac est exactement `d9154895…`, le worktree est propre, et ces quatre
chemins sont absents après le preflight :

```text
tmp/local/provisional_resolution_age1_h7_discovery_authorization.json
tmp/local/provisional_resolution_age1_h7_discovery_authorization.json.claimed
tmp/local/provisional_resolution_age1_h7_discovery_result
tmp/local/provisional_resolution_age1_h7_discovery_result.failure.json
```

Cette opération a uniquement lu/haché les octets et métadonnées autorisés. Le
runner réel n'a pas été invoqué.

## Tests synthétiques

```powershell
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -m unittest `
  tests.test_provisional_resolution_age1_persistence_h7_contract `
  tests.test_provisional_resolution_age1_persistence_h8_preparation `
  tests.test_provisional_resolution_age1_h9_synthetic `
  tests.test_provisional_resolution_age1_h10_metrics `
  tests.test_provisional_resolution_age1_h11_orchestration `
  tests.test_provisional_resolution_age1_h12_binding
```

`61 tests` réussissent en `6,034 s`. Ils couvrent SHA H11/H8, reconstruction
101/31, impossibilité des overrides, blobs historique/instrumenté/H9/H10/H11,
runtime, corruption d'actif, configuration canonique, absence de toute
opération scientifique en preflight et marqueur absent.

## Flags

```text
scientific_execution_authorized=false
execution_marker_created=false
runner_invoked=false
h8_scientific_assets_opened=false
h8_discovery_consumed=false
real_targets_extracted=false
real_signals_extracted=false
real_metrics_computed=false
locked_test_used=false
consumed_v2_cohort_used=false
```

Le seul calcul autorisé après le commit est le preflight zéro-science. Le vrai
runner reste interdit sans nouvelle revue et marqueur séparé.
