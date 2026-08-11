# Clôture terminale et analyse forensique H25

## Verdict

L'unique exécution scientifique H25 autorisée s'est terminée proprement avec
le statut :

```text
H25_SYNTHETIC_HYPOTHESIS_KILLED
```

Ce statut est un échec scientifique contrôlé, pas une erreur opérationnelle.
Le processus a retourné `exit_code=0` parce que le protocole a publié son
terminal atomiquement. Le claim est consommé et H25 ne peut jamais être
rejoué.

La revue externe a approuvé successivement la clôture terminale sous le verdict
`APPROVED_H25_TERMINAL_CLOSURE — H25_SYNTHETIC_HYPOTHESIS_KILLED_AT_P0_004`,
puis l'analyse causale sous
`APPROVED_H25_P0_004_TERMINAL_FORENSIC_CAUSAL_ANALYSIS`.

## Exécution scellée

- commit et activation exécutés :
  `0baccdf7f3be293c2a6fd0bbdaf630b19339e206` ;
- point d'entrée public unique :
  `run_h25_scientific_execution(repository_root)` ;
- nombre d'invocations : `1` ;
- retry : aucun ;
- données réelles : non ;
- modèle, entraînement ou calibration : non ;
- test verrouillé : non (`locked_test_used=false`).

Les empreintes de population enregistrées dans le terminal sont :

```text
population index
814d8c368ac67ce65ed20c9e90e634ceffe706db1cc5e642cc3c61ff37ab5f53

population provenance
cadc154a84674f6e58cf412d71f73407d0c07388f3bf470fa2368a1b810825db

population receipt
dbab85910151ce25c186f478797c86604a94e6cf486dda7e0c4b7b8eeb4fddd9
```

## Artefacts de fermeture locaux

Les artefacts scientifiques restent sous `tmp/local` sur le worker Mac. Ils ne
sont ni copiés ni versionnés par ce commit documentaire. Les tailles et SHA-256
ci-dessous ont été vérifiés en lecture seule après l'exécution.

| Artefact | Taille | SHA-256 |
|---|---:|---|
| claim `harmonic_censoring_h25_scientific_v1.consumed.json` | 2 127 | `4632c23c31170bf0301aada5ab34dacdf511c5ecd12c675c43b28008e325bfa7` |
| terminal `harmonic_censoring_h25_scientific_v1.terminal.json` | 943 | `dc37219df59aee2a97e8cf1ad0e286d48a14cc0d46d96eac4858154afbbfa32e` |
| transcript `scientific_transcript.jsonl` | 9 932 | `900df30269ee8b2467a58d9d713a4eed7d693b0bfb6acee93d3326aef1d2560d` |
| evidence `00_H25-T-P0-001.json` | 253 332 | `32f491c94a33be4dd3349a5c92d0ef04fd7eb11255ed70ab10a490120ade01f7` |
| evidence `01_H25-T-P0-002.json` | 2 456 990 | `1b8cddb97c31ec11d9114b1e5edee3bb947189a902b4324623c76876caa19c8b` |
| evidence `02_H25-T-P0-003.json` | 22 936 | `c7735ddfa17589474fd73feffa7be5598883aa4e63fc8715b1b8d59e320f3c50` |
| evidence `03_H25-T-P0-004.json` | 1 234 050 | `ab20009696d9aae8c6fc1385808d3b72a048286231e0a8fe6ae12a1fd9b2adf5` |

Le terminal forensique et le staging sont absents, conformément à une fermeture
principale réussie. Aucun de ces fichiers, ni aucun `.part`, n'a été supprimé,
réécrit ou remplacé.

## Résultat des phases

Le transcript contient exactement `27` records chaînés : quatre
`EVIDENCE_PERSISTED`, puis vingt-trois `NOT_RUN_BY_KILL_RULE`.

```text
tests exécutés                 4
tests passés                   3
premier échec                  H25-T-P0-004
non exécutés par kill rule    23
erreurs opérationnelles        0
non exécutés pour erreur       0

P0 : 4 exécutés / 3 PASS / 1 FAIL
P1 : 0/9
P2 : 0/9
```

Les trois premiers tests P0 ont passé. `H25-T-P0-004`, dont l'objectif est la
non-identifiabilité des collisions exactes, exigeait six résultats
`AMBIGUOUS`. Les résultats persistés sont :

| Fixture | Résultat |
|---|---|
| `H25-F-A01` | `AMBIGUOUS` |
| `H25-F-A02` | `AMBIGUOUS` |
| `H25-F-A03` | `AMBIGUOUS` |
| `H25-F-A04` | `NO_BIRTH` |
| `H25-F-A05` | `NO_BIRTH` |
| `H25-F-A06` | `AMBIGUOUS` |

La kill rule a donc arrêté le protocole avant `P0-005`, P1 et P2.

## Cause forensique

Le producer et le recomputer concordent. Pour les six fixtures, les deux
explications `OLD_HARMONIC_ONLY` et `PUTATIVE_NEW_FUNDAMENTAL` ont bien les
mêmes waveform, features et état causal. Il n'existe aucune corruption des
preuves.

La règle générale utilise `ATOL=1e-12`. Lorsque onset, nouveauté harmonique et
énergie nouvelle sont tous inférieurs ou égaux à cette tolérance, elle retourne
`NO_BIRTH` si le résidu d'explication par l'ancienne source est lui aussi
inférieur ou égal à la tolérance ; sinon elle retourne `AMBIGUOUS`.

Les valeurs discriminantes persistées sont :

| Fixture | Onset | Nouveauté | Énergie nouvelle | Résidu ancienne source | Décision |
|---|---:|---:|---:|---:|---|
| A01 | 0 | 0,0023280770338600675 | 0 | 0 | `AMBIGUOUS` |
| A02 | 0 | 0 | 0 | 0,49403117090173077 | `AMBIGUOUS` |
| A03 | 0 | 0 | 0 | 0,6459889355196363 | `AMBIGUOUS` |
| A04 | 0 | 0 | 0 | 0 | `NO_BIRTH` |
| A05 | 0 | 0 | 0 | 0 | `NO_BIRTH` |
| A06 | 0 | 0 | 0 | 0,000009551270904232673 | `AMBIGUOUS` |

A01 à A03 appartiennent à `EXACT_COLLISION_IDENTICAL` et ne synthétisent qu'un
partiel de l'ancienne source. A04 à A06 appartiennent à
`OVERLAP_WITHOUT_INDEPENDENT_EVIDENCE`; leurs spécifications fixent
`putative_new_waveform_gain=0.0` et le materializer ne synthétise que l'ancienne
source MIDI 40 avec ses harmoniques. La seconde cause reste donc une hypothèse
latente sans contribution physique indépendante.

La cause immédiate est la branche :

```text
aucune évidence nouvelle + explication parfaite par l'ancienne source
→ NO_BIRTH
```

Cette règle contredit l'oracle épistémique particulier de P0-004 : lorsque deux
causes autorisées sont observationnellement identiques, l'absence d'évidence
indépendante n'est pas une preuve négative d'absence. Le résultat doit rester
`AMBIGUOUS`. A06 ne reste ambigu que grâce à un petit résidu numérique ; il
n'est pas davantage identifiable que A04/A05.

## Décision

H25 est définitivement clos et rejeté dans sa forme scellée :

- aucune correction rétroactive ;
- aucun retry ;
- aucun P1/P2 ;
- aucune promotion vers données réelles, modèle ou décodeur ;
- aucun usage du test verrouillé.

Cette clôture ne prouve pas que la suppression générale des harmoniques fantômes
est impossible. Elle prouve que H25 ne satisfait pas sa propre condition
fondamentale de non-identifiabilité. Toute hypothèse successeur devra être
préenregistrée séparément et décider explicitement si l'absence de preuve
indépendante signifie `AMBIGUOUS` ou `NO_BIRTH`, avec des fixtures non
contradictoires. Ce rapport n'autorise ni ne définit ce successeur.
