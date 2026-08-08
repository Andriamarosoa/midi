# Instrumentation des candidats du décodeur

## Périmètre

Point de départ approuvé :
`f9ed9d0230675284632765d7dc8aca7ae33ff1aa` sur
`codex/independent-note-neural-v2`.

Commit d'instrumentation vérifié :
`f7514228800d8ad15db7d047dcadfbf8640cf4ee`.

Cette étape ajoute uniquement un side-channel d'observation au décodeur. Elle
ne produit aucun artefact miné, ne change aucune décision MIDI et n'autorise ni
entraînement, validation officielle, export, live ou test verrouillé.

## Implémentation

- `candidate_collector=None` est le défaut de `PolyphonicDecoder`.
- Aucun objet de trace, dictionnaire de traces ou calcul NumPy supplémentaire
  n'est créé dans le chemin désactivé.
- Les voies legacy et causale figent les scalaires JSON natifs juste avant la
  porte éventuelle : frame, onset, score, raison, support harmonique, contexte
  d'onset audio, polyphonie active et éligibilité.
- Le score et la raison pré-porte ne sont pas écrasés lorsque le filtre
  harmonique réduit ensuite le score ou émet `harmonic_strong_frame`.
- Le rang est attaché après le classement réel; sélection et émission sont
  attachées après leurs décisions. L'ID n'est créé qu'après un vrai NoteOn.
- `PolyphonicMidiEvent` reste inchangé. L'ID externe est le SHA-256 d'un tuple
  canonique versionné contenant corpus, groupe de fuite, prise, frame et pitch.
- Le buffer est borné et atomiquement drainable. Chaque batch transporte ses
  nombres totaux et perdus; `require_complete()` refuse un batch ayant débordé.
- La provenance (`recording_key`, groupe, corpus) et la capacité sont en lecture
  seule après construction; elles ne peuvent donc pas dériver au milieu d'un
  batch et désynchroniser les IDs, le `deque` ou les compteurs d'overflow.
- Chaque observation est complétée localement après sa décision pertinente.
  Le batch entier n'est remis au collecteur qu'après toutes les décisions et
  émissions de la frame. Le verrou est acquis avec `blocking=False`; une
  contention invalide la collecte sans retarder le retour des événements MIDI.
- Une exception du collecteur est mémorisée dans
  `candidate_collection_error`, puis la collecte cesse sans bloquer le MIDI.
- Les codes de raisons sont centralisés en conservant exactement le contrat
  live existant : `model_onset=1`, `frame_attack=2`, `frame_fallback=3`,
  `harmonic_strong_frame=4`, `retrigger=5`, `legacy=6` et
  `chord_completion=7`. Les features pré-porte utilisent le sous-ensemble
  causal `1,2,3,6,7`.
- Les retriggers ne sont pas collectés : ils contournent la porte et le
  classement des candidats inactifs.

## Vérifications Windows

Commande ciblée :

```text
C:\Users\user\Desktop\midi\.venv\Scripts\python.exe -B -m unittest
tests.test_decoder_candidate_mining
tests.test_decoder_candidate_instrumentation
tests.test_polyphonic_decoder
tests.test_polyphonic_desktop_contract
tests.test_product_decoder
tests.test_polyphonic_validate_live_input_level
tests.test_ollama_team
tests.test_mac_worker_transport_contract
```

Résultat : **86/86 tests réussis**. La compilation syntaxique des six fichiers
touchés et `git diff --check` réussissent également.

Une comparaison dynamique en mémoire contre le fichier `decoder.py` du commit
approuvé `f9ed9d0` a rejoué 128 frames dans chacune de quatre combinaisons :

- porte `independent_note` inactive ou active;
- voie legacy sans onset audio ou voie causale avec onset audio.

Les **512/512 frames** ont rendu les mêmes événements dans le même ordre et le
même état interne, bit à bit pour les tableaux. Les sauts de hop, silence,
releases, retriggers, reset de continuité et panic sont inclus.


## Vérifications Mac M4

- Checkout propre sur `codex/independent-note-neural-v2`, au commit exact
  `f7514228800d8ad15db7d047dcadfbf8640cf4ee`.
- Python `3.11.9`, NumPy `1.26.4`.
- La même commande ciblée exécute **86 tests** en `0,604 s` : `OK`, avec deux
  tests Windows-only explicitement ignorés.
- La compilation syntaxique des six fichiers Python touchés réussit.
- Aucun processus scientifique, entraînement, minage, validation officielle,
  export, live ou test verrouillé n'a été lancé.

## Latence

Microbenchmark Windows borné, six répétitions alternées de 3 000 frames,
trois candidats directs par frame et panic après chaque frame :

| Variante | Médiane |
|---|---:|
| Décodeur approuvé `f9ed9d0` | 175,7718 µs/frame |
| Nouveau décodeur, collecte désactivée | 162,5279 µs/frame |
| Nouveau décodeur, collecte activée | 260,6392 µs/frame |

Le chemin désactivé diffère de `-13,2439 µs/frame`, donc aucune régression n'est
mesurable dans ce benchmark. Le side-channel activé ajoute `98,1113 µs/frame`,
soit `1,6901 %` du hop causal de `5,80499 ms`. Il n'ajoute aucun lookahead ni
délai algorithmique. Cette collecte reste destinée à l'offline et n'est pas
activée dans le live.

## Limites bloquant tout minage

1. Le futur artefact doit persister explicitement `source_id`, `group_id`,
   `capture_id` et la partition `fit/dev/calibration`, assignés par groupe avant
   le minage. Le buffer brut transporte seulement les équivalents transitoires
   `recording_key`/`leakage_group_key` et le corpus; `capture_id` et la partition
   manquent encore.
2. `collapse_emitted_candidate_episodes()` suppose plusieurs lignes émises
   partageant un `event_id`, alors que l'ID déterministe identifie désormais un
   vrai NoteOn unique et que les lignes non émises ne peuvent porter aucun ID.
   Le collapse devient donc un no-op dans le producteur actuel. Sa sémantique
   doit être redéfinie ou supprimée avant tout artefact miné.
3. Aucun producteur de dataset, aucune association à la vérité et aucun chemin
   d'entraînement n'est connecté dans ce commit.

## Décision

L'instrumentation-only est vérifiée sur Windows et Mac au commit exact; elle est
prête pour revue externe. `locked_test_used=false`. Aucun minage, entraînement,
validation, export ou live ne doit être lancé avant approbation explicite de
cette étape et correction des limites ci-dessus.
