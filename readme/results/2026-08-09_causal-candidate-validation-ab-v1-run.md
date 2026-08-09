# Relance CPU A/B historique du filtre causal V1

Date : 2026-08-09  
Portée : unique validation historique A/B autorisée après le correctif
`17d94580`; aucun fit, recalibrage, export, live ni test verrouillé.

## Exécution et intégrité

La première invocation A/B au commit `4ab4f1ec` s'était arrêtée avant la boucle
des prises sur `KeyError: 'frame'`. La revue externe du correctif
`17d94580af0f293f66a05072388fa1df62f27a89` a donc autorisé cette unique
relance, avec un nouvel identifiant de job :

```text
job_id              causal-candidate-validation-ab-retry-cpu-20260809
commit              17d94580af0f293f66a05072388fa1df62f27a89
module              src.polyphonic.run_causal_candidate_validation
device              cpu
wall timeout        900 s
module arguments    aucun
started_utc         2026-08-09T22:47:13Z
finished_utc        2026-08-09T22:53:39Z
worker status       exited_zero / exit_code=0
runner status       complete_non_authorizing
```

Avant le lancement, le checkout Mac était propre et détaché au commit exact,
le script worker installé était identique au script Git, `active.lock` était
absent, et le job ID ainsi que la destination A/B étaient neufs. Le préflight
spécifique a confirmé CPU/900 s avant l'import TensorFlow. Après le job, le
verrou est absent et stderr est vide.

Le rapport brut récupéré depuis le Mac est conservé localement hors Git :

```text
Mac path    /Users/amcarene/midi-worker/repository/tmp/causal_candidate_validation_ab_v1_20260809/reports/validation_events_1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325_causal_candidate_fit_v1_ab.json
Local path  tmp/local/mac_results/causal-candidate-validation-ab-retry-cpu-20260809/causal_candidate_validation_ab_v1_20260809/reports/validation_events_1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325_causal_candidate_fit_v1_ab.json
bytes       372794
SHA-256     8f048ad173015c2a89d3cde5ca106cc45c6bad05f6023f36c92ba4e12c28d1c3
```

Le SHA-256 a été recalculé localement puis sur le Mac : les deux valeurs sont
identiques. Le JSON se charge complètement, comporte 12 rapports référence et
12 rapports candidats ayant les mêmes identités de capture, et ne signale
aucune erreur ou abandon partiel.

## Contrat scellé vérifié

```text
split                          validation
recordings                     12 (3 par corpus)
locked_test_used               false
single_inference_per_recording true
independent_decoder_state_after_gate_decisions true
audio evidence override        forbidden
```

Les empreintes archivées par le rapport sont :

```text
fit_report                b8148fade0d72c6d20d64f31fbaf9983b748997ba16f5664c525bcc41ae9b759
model                     b9320cd004ed686720e282e4338c4a6413c2ef3dd701d421de3533f710d8a59e
standardizer              0600aa1aa75eb008f04e299de3ffe9d7b6b0a722b177750b42e0967740df5e3b
manifest                  b28cb17cfb80a82860ab44635b2c6d05718243e027a8fc8199fe72e27f1b8ed7
selection                 8c3cf53c7f5dcf086b70767e28499c3164aa307059652a6d0a2fc87159f9dcbc
checkpoint                1ce8ac44ca7156d4bc058b5b37580805f2ab6536b380636c04b9a31b1a411325
evaluation_config         245285783eb395e1c16f9773cf9a15565510ba289467d63ad6a7d725bae19804
reference_decoder_config  c16be48271912c99c4237345e8406e39b88490b5565047757f6ca9e905615f96
policy                    750755910721fc5921f0507e794b20611d82b3f51ad07192d798ef369799f858
```

La branche référence utilise la configuration scellée sans porte candidate. La
branche B applique la tête causale V1 et son standardiseur scellés au seuil
préenregistré `0,31`, immédiatement avant sa porte et depuis son état causal
propre. Les prédictions de transcription et les masques audio sont partagés,
mais les deux décodeurs restent indépendants après leurs décisions de porte.

## Résultats A/B

Les deux branches ont produit exactement les mêmes événements MIDI finaux. Les
valeurs suivantes sont donc identiques pour A et B ; la colonne delta est
strictement `B - A`.

| Mesure globale | Référence A | Candidate B | Delta |
|---|---:|---:|---:|
| Notes estimées | 4 247 | 4 247 | 0 |
| Notes appariées | 858 | 858 | 0 |
| Faux positifs onset | 3 389 | 3 389 | 0 |
| Notes manquantes | 2 781 | 2 781 | 0 |
| Précision onset | 0,20202496 | 0,20202496 | 0 |
| Rappel onset | 0,23577906 | 0,23577906 | 0 |
| F1 onset | 0,21760081 | 0,21760081 | 0 |
| F1 onset+offset | 0,08445346 | 0,08445346 | 0 |
| Faux NoteOn causaux | 2 073 | 2 073 | 0 |
| Faux NoteOn/min | 69,92376 | 69,92376 | 0 |
| Rappel causal à 250 ms | 0,59741687 | 0,59741687 | 0 |
| Latence causale p50 | 68,13091 ms | 68,13091 ms | 0 ms |
| Latence causale p90 | 162,38829 ms | 162,38829 ms | 0 ms |
| Retriggers | 160 | 160 | 0 |
| Fragments excédentaires | 197 | 197 | 0 |

Le sous-ensemble grave MIDI 40–51 est également inchangé : 868 faux positifs,
472 notes manquantes et F1 onset `0,17181706` dans les deux branches.

Par corpus, les F1 onset et métriques causales de B sont identiques à A :

| Corpus | F1 onset | Faux NoteOn causaux | Rappel causal | p50 / p90 causal |
|---|---:|---:|---:|---:|
| GAPS | 0,24722861 | 1 254 | 0,54422067 | 53,798 / 162,635 ms |
| Guitar-TECHS direct | 0,04992867 | 350 | 0,74461028 | 99,082 / 162,575 ms |
| Guitar-TECHS mic | 0,05313496 | 261 | 0,64251208 | 110,179 / 168,253 ms |
| GuitarSet | 0,54330709 | 208 | 0,63905325 | 22,017 / 105,909 ms |

Les résultats complets par prise, par corpus, onset, onset+offset, diagnostics,
métriques causales et MIDI 40–51 sont conservés dans le JSON brut haché.

## Observation de la porte V1 et décision

La tête a bien été appelée dans la branche B : 711 candidats internes étaient
éligibles et 9 ont été rejetés au seuil `0,31`.

| Corpus | Candidats éligibles | Rejets internes |
|---|---:|---:|
| GAPS | 561 | 3 |
| Guitar-TECHS direct | 97 | 4 |
| Guitar-TECHS mic | 23 | 2 |
| GuitarSet | 30 | 0 |
| **Total** | **711** | **9** |

Ces neuf rejets ne se traduisent par aucun changement dans les NoteOn finaux de
ce décodeur stateful sur la cohorte observée. Ils ne constituent donc pas une
réduction démontrée des faux NoteOn.

La policy exigeait au minimum une baisse de 1 faux positif. Cette seule règle
échoue (`0` au lieu de `≤ -1`). Toutes les règles de conservation passent par
égalité : rappel et F1, rappel causal, p50/p90, retriggers, fragmentation,
F1 des quatre corpus et F1 grave. Avec la règle « toutes les règles doivent
passer », le verdict mécanique est :

```text
all_rules_passed = false
status           = complete_non_authorizing
```

## Conclusion et suite bloquée

Cette passe est un résultat négatif propre et borné : le filtre V1 à `0,31` a
pris neuf décisions internes mais n'a apporté aucun gain événementiel mesuré
sur les 12 prises validation fixées. Elle ne justifie aucune promotion du
modèle, du standardiseur ou du seuil, ni une nouvelle relance de cette policy.

## Revue externe et clôture

La revue externe de `f893aa55e6e5b00eddda7b4833a8cf4775c9f511` approuve le
rapport et clôt formellement V1 comme variante non promue. Elle confirme que
les neuf rejets sont réels, mais que leur absence d'effet sur le MIDI est le
constat expérimental déterminant.

L'interprétation retenue est un décalage plausible de population : les cibles
du fit étaient les candidats ayant réellement émis un NoteOn, tandis que la
porte V1 voyait tous les candidats internes éligibles avant le ranking et la
sélection. La revue ne permet ni d'augmenter le seuil, ni de refaire le fit,
ni de rejouer l'A/B à partir de cette validation.

Une porte éventuelle placée **après ranking et sélection, juste avant
l'émission NoteOn**, constituerait une hypothèse architecturale distincte. Elle
devra être préenregistrée, revue et autorisée séparément : aucun code ni calcul
ne sont déclenchés par cette clôture. Le test verrouillé demeure fermé.
